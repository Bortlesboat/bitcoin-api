"""In-process pub/sub hub for WebSocket event distribution."""

import asyncio
import logging
import threading
from typing import Any

log = logging.getLogger("bitcoin_api.pubsub")

CHANNELS = {"new_block", "new_fees", "mempool_update"}


class PubSubHub:
    """Thread-safe pub/sub hub. Background threads publish, async consumers subscribe."""

    def __init__(self, maxsize: int = 50):
        self._maxsize = maxsize
        self._lock = threading.Lock()
        # channel -> set of asyncio.Queue
        self._subscribers: dict[str, set[asyncio.Queue]] = {ch: set() for ch in CHANNELS}

    def subscribe(self, channel: str) -> asyncio.Queue:
        if channel not in CHANNELS:
            raise ValueError(f"Unknown channel: {channel}")
        q: asyncio.Queue = asyncio.Queue(maxsize=self._maxsize)
        with self._lock:
            self._subscribers[channel].add(q)
        return q

    def unsubscribe(self, channel: str, q: asyncio.Queue) -> None:
        with self._lock:
            self._subscribers.get(channel, set()).discard(q)

    def publish(self, channel: str, data: dict[str, Any]) -> None:
        """Publish from any thread. Drops messages if a subscriber queue is full."""
        with self._lock:
            subscribers = list(self._subscribers.get(channel, set()))
        for q in subscribers:
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                log.debug("Dropped message on full queue for channel %s", channel)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return sum(len(subs) for subs in self._subscribers.values())


hub = PubSubHub()
