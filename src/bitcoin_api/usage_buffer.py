"""Batch usage logging — buffers writes and flushes periodically or at threshold."""

import logging
import threading
import time

log = logging.getLogger("bitcoin_api.usage")


class UsageBuffer:
    FLUSH_SIZE = 50
    FLUSH_INTERVAL = 30  # seconds

    def __init__(self):
        self._buffer: list[tuple] = []
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def log(self, key_hash, endpoint, status_code, method=None, response_time_ms=None, user_agent=None, client_type="unknown", referrer=""):
        batch = None
        with self._lock:
            self._buffer.append((key_hash, endpoint, status_code, method, response_time_ms, user_agent, client_type, referrer, time.time()))
            if len(self._buffer) >= self.FLUSH_SIZE:
                batch = self._flush_locked()
            elif self._timer is None:
                self._start_timer()
        if batch:
            try:
                self._write_batch(batch)
            except Exception as e:
                log.error("Usage buffer flush failed (%d entries lost): %s", len(batch), e)

    def _start_timer(self):
        self._timer = threading.Timer(self.FLUSH_INTERVAL, self._timer_flush_write)
        self._timer.daemon = True
        self._timer.start()

    def _flush_locked(self):
        """Drain buffer under lock, then write to DB without holding the lock."""
        if not self._buffer:
            return
        batch = self._buffer[:]
        self._buffer.clear()
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        return batch

    def _timer_flush_write(self):
        """Timer callback: drain under lock, then write outside lock."""
        with self._lock:
            self._timer = None
            batch = self._flush_locked()
        if batch:
            try:
                self._write_batch(batch)
            except Exception as e:
                log.error("Usage buffer flush failed (%d entries lost): %s", len(batch), e)

    @staticmethod
    def _write_batch(batch: list[tuple]):
        from .db import get_db
        conn = get_db()
        conn.executemany(
            "INSERT INTO usage_log (key_hash, endpoint, status, method, response_time_ms, user_agent, client_type, referrer, ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime(?, 'unixepoch'))",
            [(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]) for row in batch],
        )
        conn.commit()

    def flush(self):
        """Public flush for shutdown — ensures all buffered entries are written."""
        with self._lock:
            batch = self._flush_locked()
        if batch:
            try:
                self._write_batch(batch)
            except Exception as e:
                log.error("Usage buffer shutdown flush failed (%d entries lost): %s", len(batch), e)

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._buffer)


# Module-level singleton
usage_buffer = UsageBuffer()
