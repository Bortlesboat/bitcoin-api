"""Tests for RPC failover — primary → fallback node switching."""

from unittest.mock import patch

import pytest

from bitcoin_api.circuit_breaker import CircuitBreaker, CircuitState
from bitcoin_api.dependencies import (
    _create_fallback_rpc,
    get_fallback_status,
    is_using_fallback,
)


class TestFallbackConfig:
    """Test fallback RPC configuration."""

    def test_fallback_not_configured_by_default(self):
        status = get_fallback_status()
        assert status["configured"] is False
        assert status["active"] is False

    @patch("bitcoin_api.dependencies.settings")
    def test_fallback_configured_shows_host(self, mock_settings):
        mock_settings.bitcoin_rpc_fallback_host = "192.168.1.87"
        mock_settings.bitcoin_rpc_fallback_port = 8332
        status = get_fallback_status()
        assert status["configured"] is True
        assert status["host"] == "192.168.1.87"
        assert status["port"] == 8332

    @patch("bitcoin_api.dependencies.settings")
    def test_create_fallback_rpc_returns_none_when_not_configured(self, mock_settings):
        mock_settings.bitcoin_rpc_fallback_host = None
        result = _create_fallback_rpc()
        assert result is None


class TestFailoverLogic:
    """Test circuit-breaker-driven failover."""

    def test_not_using_fallback_initially(self):
        assert is_using_fallback() is False

    def test_circuit_breaker_state_transitions(self):
        """Verify circuit breaker states that drive failover."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED  # Below threshold

        cb.record_failure()
        assert cb.state == CircuitState.OPEN  # Hit threshold

        cb.record_success()
        assert cb.state == CircuitState.CLOSED  # Manual recovery


class TestHealthDeepFallback:
    """Test that /health/deep includes fallback status."""

    def test_health_deep_includes_fallback_node(self, authed_client):
        with patch("bitcoin_api.routers.health_deep.get_job_health", return_value={"fee_collector": "ok"}), \
             patch("bitcoin_api.routers.health_deep.usage_buffer") as mock_buf:
            mock_buf.pending_count = 0
            resp = authed_client.get("/api/v1/health/deep")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "fallback_node" in data
        assert data["fallback_node"]["configured"] is False
        assert data["fallback_node"]["active"] is False
