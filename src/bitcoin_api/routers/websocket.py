"""WebSocket subscription endpoint for real-time Bitcoin events."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import settings
from ..pubsub import hub, CHANNELS

log = logging.getLogger("bitcoin_api.websocket")

router = APIRouter(tags=["WebSocket"])

_active_connections: set[WebSocket] = set()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    if len(_active_connections) >= settings.ws_max_connections:
        await ws.close(code=1013, reason="Max connections reached")
        return

    await ws.accept()
    _active_connections.add(ws)
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
        for ch, q in subscriptions.items():
            hub.unsubscribe(ch, q)
        for task in tasks.values():
            task.cancel()
