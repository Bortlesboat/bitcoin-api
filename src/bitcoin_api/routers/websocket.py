"""WebSocket subscription endpoint for real-time Bitcoin events."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..auth import hash_key
from ..config import settings
from ..db import lookup_key
from ..metrics import WS_CONNECTIONS_ACTIVE
from ..pubsub import hub, CHANNELS

log = logging.getLogger("bitcoin_api.websocket")

router = APIRouter(tags=["WebSocket"])

_active_connections: set[WebSocket] = set()

# Public channels available to all connections (authenticated or not)
PUBLIC_CHANNELS = {"new_block", "new_fees", "mempool_update"}

# Premium channels requiring a valid API key (empty for now; add channel names to gate them)
PREMIUM_CHANNELS: set[str] = set()


def _validate_ws_api_key(raw_key: str) -> str | None:
    """Validate an API key for WebSocket auth. Returns tier or None if invalid."""
    key_hash = hash_key(raw_key)
    record = lookup_key(key_hash)
    if record is None or not record["active"]:
        return None
    return record["tier"]


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    if len(_active_connections) >= settings.ws_max_connections:
        await ws.close(code=1013, reason="Max connections reached")
        return

    # Authenticate via query parameter before accepting
    raw_key = ws.query_params.get("api_key")
    authenticated = False
    if raw_key is not None:
        tier = _validate_ws_api_key(raw_key)
        if tier is None:
            await ws.close(code=4001, reason="Invalid API key")
            return
        authenticated = True

    await ws.accept()
    _active_connections.add(ws)
    WS_CONNECTIONS_ACTIVE.inc()
    subscriptions: dict[str, asyncio.Queue] = {}

    async def _send_events(channel: str, q: asyncio.Queue):
        try:
            while True:
                data = await q.get()
                msg = {"channel": channel, **data}
                await ws.send_json(msg)
        except (WebSocketDisconnect, RuntimeError):
            pass

    tasks: dict[str, asyncio.Task] = {}

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            action = msg.get("action")
            channel = msg.get("channel")

            if action == "subscribe":
                if channel not in CHANNELS:
                    await ws.send_json({"type": "error", "detail": f"Unknown channel: {channel}. Available: {sorted(CHANNELS)}"})
                    continue
                if channel in PREMIUM_CHANNELS and not authenticated:
                    await ws.send_json({"type": "error", "detail": f"Channel '{channel}' requires authentication. Reconnect with ?api_key=YOUR_KEY"})
                    continue
                if channel in subscriptions:
                    await ws.send_json({"type": "error", "detail": f"Already subscribed to {channel}"})
                    continue
                q = hub.subscribe(channel)
                subscriptions[channel] = q
                task = asyncio.create_task(_send_events(channel, q))
                tasks[channel] = task
                await ws.send_json({"type": "subscribed", "channel": channel})

            elif action == "unsubscribe":
                if channel not in subscriptions:
                    await ws.send_json({"type": "error", "detail": f"Not subscribed to {channel}"})
                    continue
                hub.unsubscribe(channel, subscriptions.pop(channel))
                task = tasks.pop(channel, None)
                if task:
                    task.cancel()
                await ws.send_json({"type": "unsubscribed", "channel": channel})

            elif action == "ping":
                await ws.send_json({"type": "pong"})

            else:
                await ws.send_json({"type": "error", "detail": f"Unknown action: {action}. Use subscribe/unsubscribe/ping"})

    except WebSocketDisconnect:
        pass
    finally:
        _active_connections.discard(ws)
        WS_CONNECTIONS_ACTIVE.dec()
        for ch, q in subscriptions.items():
            hub.unsubscribe(ch, q)
        for task in tasks.values():
            task.cancel()
