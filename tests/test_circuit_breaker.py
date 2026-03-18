"""Tests for the circuit breaker module."""

import time
from unittest.mock import patch

import pytest

from bitcoin_api.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


@pytest.fixture
def cb():
    """Circuit breaker with low threshold and short timeout for fast tests."""
    return CircuitBreaker(failure_threshold=3, recovery_timeout=0.2)


class TestCircuitBreakerStates:
    def test_initial_state_is_closed(self, cb):
        assert cb.state == CircuitState.CLOSED

    def test_before_call_succeeds_when_closed(self, cb):
        cb.before_call()  # Should not raise

    def test_single_failure_stays_closed(self, cb):
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_failures_below_threshold_stay_closed(self, cb):
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.before_call()  # Still works

    def test_reaching_threshold_opens_circuit(self, cb):
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_before_call_raises_when_open(self, cb):
        for _ in range(3):
            cb.record_failure()
        with pytest.raises(CircuitOpenError) as exc_info:
            cb.before_call()
        assert "temporarily unavailable" in str(exc_info.value).lower()

    def test_open_transitions_to_half_open_after_timeout(self, cb):
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.25)  # Wait past recovery_timeout
        assert cb.state == CircuitState.HALF_OPEN

    def test_before_call_succeeds_in_half_open(self, cb):
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.25)
        cb.before_call()  # Should not raise — half-open allows probe

    def test_success_in_half_open_closes_circuit(self, cb):
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.25)
        cb.before_call()  # Transitions to half-open
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_failure_in_half_open_reopens_circuit(self, cb):
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.25)
        cb.before_call()  # Transitions to half-open
        cb.record_failure()  # Failure count now 4, >= threshold
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self, cb):
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        # After success, failure count is 0 — need 3 more failures to open
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_get_status_returns_dict(self, cb):
        status = cb.get_status()
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["failure_threshold"] == 3
        assert status["recovery_timeout_seconds"] == 0.2

    def test_get_status_reflects_open(self, cb):
        for _ in range(3):
            cb.record_failure()
        status = cb.get_status()
        assert status["state"] == "open"
        assert status["failure_count"] == 3

    def test_custom_threshold(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
