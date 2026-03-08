"""Circuit breaker for Bitcoin Core RPC -- fast-fail when node is down."""

import logging
import threading
import time
from enum import Enum

from .metrics import CIRCUIT_BREAKER_STATE, CIRCUIT_BREAKER_TRIPS

log = logging.getLogger("bitcoin_api.circuit_breaker")

_STATE_VALUES = {"closed": 0, "half_open": 1, "open": 2}


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when circuit is open -- node is considered unavailable."""


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._state = CircuitState.CLOSED
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """Read-only snapshot of current state (no side effects)."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self._recovery_timeout:
                    return CircuitState.HALF_OPEN
            return self._state

    def _check_and_transition(self) -> CircuitState:
        """Check state and perform OPEN→HALF_OPEN transition if recovery timeout elapsed."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    CIRCUIT_BREAKER_STATE.set(_STATE_VALUES["half_open"])
                    log.info("Circuit breaker -> HALF_OPEN (probing node)")
            return self._state

    def before_call(self):
        """Call before RPC. Raises CircuitOpenError if circuit is open."""
        state = self._check_and_transition()
        if state == CircuitState.OPEN:
            remaining = self._recovery_timeout - (time.time() - self._last_failure_time)
            raise CircuitOpenError(
                f"Circuit breaker OPEN -- Bitcoin node unavailable. "
                f"Retry in {max(1, int(remaining))}s"
            )

    def record_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                log.info("Circuit breaker -> CLOSED (node recovered)")
            self._failure_count = 0
            self._state = CircuitState.CLOSED
            CIRCUIT_BREAKER_STATE.set(_STATE_VALUES["closed"])

    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self._failure_threshold:
                if self._state != CircuitState.OPEN:
                    log.warning(
                        "Circuit breaker -> OPEN after %d failures",
                        self._failure_count,
                    )
                    CIRCUIT_BREAKER_TRIPS.inc()
                self._state = CircuitState.OPEN
                CIRCUIT_BREAKER_STATE.set(_STATE_VALUES["open"])

    def get_status(self) -> dict:
        """Return circuit breaker status for health/diagnostics."""
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self._failure_threshold,
            "recovery_timeout_seconds": self._recovery_timeout,
        }


# Module-level singleton
rpc_breaker = CircuitBreaker()
