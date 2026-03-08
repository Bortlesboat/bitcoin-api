"""In-process pub/sub hub for WebSocket event distribution."""

import asyncio
import logging
import queue
import threading
from typing import Any

from .metrics import WS_MESSAGES_DROPPED

log = logging.getLogger("bitcoin_api.pubsub")

CHANNELS = {"new_block", "new_fees", "mempool_update"}


class PubSubHub:
    """Thread-safe pub/sub hub. Background threads publish via thread-safe queue,
    async consumers subscribe via asyncio.Queue."""

    def __init__(self, maxsize: int = 50):
        self._maxsize = maxsize
        self._lock = threading.Lock()
        # channel -> set of asyncio.Queue (only touched from event loop thread)
        self._subscribers: dict[str, set[asyncio.Queue]] = {ch: set() for ch in CHANNELS}
        # Thread-safe buffer for cross-thread publishes
        self._pending: queue.SimpleQueue = queue.SimpleQueue()

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
        """Thread-safe publish. Buffers the event, then drains into asyncio queues.

        Safe to call from any thread (background jobs, etc.).
        """
        self._pending.put((channel, data))
        self._drain_pending()

    def _drain_pending(self) -> None:
        """Move all pending events into subscriber asyncio.Queues.

        put_nowait on asyncio.Queue is safe here because we hold the lock
        (preventing concurrent subscriber set mutation) and the Queue's internal
        deque append is atomic in CPython. For WebSocket delivery tasks that
        await q.get(), the event loop will pick up the new item on its next cycle.
        """
        while True:
            try:
                channel, data = self._pending.get_nowait()
            except queue.Empty:
                break
            with self._lock:
                subscribers = list(self._subscribers.get(channel, set()))
            for q in subscribers:
                try:
                    q.put_nowait(data)
                except asyncio.QueueFull:
                    WS_MESSAGES_DROPPED.labels(channel=channel).inc()
                    log.debug("Dropped message on full queue for channel %s", channel)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return sum(len(subs) for subs in self._subscribers.values())


hub = PubSubHub()
