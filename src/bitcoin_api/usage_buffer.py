"""Batch usage logging — buffers writes and flushes periodically or at threshold."""

import threading
import time


class UsageBuffer:
    FLUSH_SIZE = 50
    FLUSH_INTERVAL = 30  # seconds

    def __init__(self):
        self._buffer: list[tuple] = []
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def log(self, key_hash, endpoint, status_code, method=None, response_time_ms=None, user_agent=None):
        with self._lock:
            self._buffer.append((key_hash, endpoint, status_code, method, response_time_ms, user_agent, time.time()))
            if len(self._buffer) >= self.FLUSH_SIZE:
                self._flush_locked()
            elif self._timer is None:
                self._start_timer()

    def _start_timer(self):
        self._timer = threading.Timer(self.FLUSH_INTERVAL, self._timer_flush)
        self._timer.daemon = True
        self._timer.start()

    def _timer_flush(self):
        with self._lock:
            self._timer = None
            self._flush_locked()

    def _flush_locked(self):
        """Flush buffer to DB. Must be called with _lock held."""
        if not self._buffer:
            return
        batch = self._buffer[:]
        self._buffer.clear()
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

        # Release lock before DB write
        try:
            self._write_batch(batch)
        except Exception:
            pass  # Don't crash on DB errors

    @staticmethod
    def _write_batch(batch: list[tuple]):
        from .db import get_db
        conn = get_db()
        conn.executemany(
            "INSERT INTO usage_log (key_hash, endpoint, status, method, response_time_ms, user_agent) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(row[0], row[1], row[2], row[3], row[4], row[5]) for row in batch],
        )
        conn.commit()

    def flush(self):
        """Public flush for shutdown — ensures all buffered entries are written."""
        with self._lock:
            self._flush_locked()

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._buffer)


# Module-level singleton
usage_buffer = UsageBuffer()
