"""Tests for Redis rate limiting path and tier limits."""

from unittest.mock import patch, MagicMock

import bitcoin_api.rate_limit as rl
from bitcoin_api.config import settings
from bitcoin_api.rate_limit import (
    init_redis,
    check_rate_limit,
)


def test_init_redis_success():
    """Mock upstash_redis.Redis, verify ping() called and _redis_client set."""
    mock_redis_cls = MagicMock()
    mock_redis_instance = MagicMock()
    mock_redis_cls.return_value = mock_redis_instance

    mock_module = MagicMock()
    mock_module.Redis = mock_redis_cls

    with (
        patch.object(settings, "rate_limit_backend", "redis"),
        patch.object(settings, "upstash_redis_url", "https://redis.example.com"),
        patch.object(settings, "upstash_redis_token", None),
        patch.dict("sys.modules", {"upstash_redis": mock_module}),
    ):
        init_redis()

    mock_redis_instance.ping.assert_called_once()
    assert rl._redis_client is mock_redis_instance

    # Cleanup
    rl._redis_client = None


def test_init_redis_failure():
    """Mock Redis to raise on ping, verify _redis_client stays None."""
    mock_redis_cls = MagicMock()
    mock_redis_instance = MagicMock()
    mock_redis_instance.ping.side_effect = ConnectionError("refused")
    mock_redis_cls.return_value = mock_redis_instance

    mock_module = MagicMock()
    mock_module.Redis = mock_redis_cls

    rl._redis_client = None

    with (
        patch.object(settings, "rate_limit_backend", "redis"),
        patch.object(settings, "upstash_redis_url", "https://redis.example.com"),
        patch.object(settings, "upstash_redis_token", None),
        patch.dict("sys.modules", {"upstash_redis": mock_module}),
    ):
        init_redis()

    assert rl._redis_client is None


def test_check_rate_limit_redis_path():
    """Set _redis_client to mock, verify pipeline operations are called."""
    # Phase 1 pipe: zremrangebyscore + zcard (returns count under limit)
    mock_pipe1 = MagicMock()
    mock_pipe1.exec.return_value = [None, 1]  # zrem result, zcard=1

    # Phase 2 pipe: zadd + expire
    mock_pipe2 = MagicMock()
    mock_pipe2.exec.return_value = [None, None]

    mock_client = MagicMock()
    mock_client.pipeline.side_effect = [mock_pipe1, mock_pipe2]

    rl._redis_client = mock_client
    rl.TIER_LIMITS = {"anonymous": 30, "free": 100, "pro": 500, "enterprise": 2000}

    try:
        result = check_rate_limit("test-bucket", "free")
        assert result.allowed is True
        assert result.limit == 100
        assert mock_client.pipeline.call_count == 2
        mock_pipe1.zremrangebyscore.assert_called_once()
        mock_pipe1.zcard.assert_called_once()
        mock_pipe2.zadd.assert_called_once()
        mock_pipe2.expire.assert_called_once()
    finally:
        rl._redis_client = None
        rl.TIER_LIMITS.clear()


def test_check_rate_limit_redis_fallback():
    """Mock pipeline to raise, verify memory fallback used."""
    mock_client = MagicMock()
    mock_client.pipeline.side_effect = RuntimeError("Redis exploded")

    rl._redis_client = mock_client
    rl.TIER_LIMITS = {"anonymous": 30, "free": 100, "pro": 500, "enterprise": 2000}

    try:
        result = check_rate_limit("fallback-bucket", "free")
        # Should succeed via memory fallback
        assert result.allowed is True
        assert result.limit == 100
    finally:
        rl._redis_client = None
        rl.TIER_LIMITS.clear()


def test_check_rate_limit_memory_basic():
    """Basic memory rate limit: allow up to limit, then deny."""
    rl.TIER_LIMITS = {"anonymous": 3, "free": 3, "pro": 500, "enterprise": 2000}
    rl._redis_client = None

    try:
        # First 3 should pass
        for i in range(3):
            result = check_rate_limit("mem-test", "free")
            assert result.allowed is True, f"Request {i+1} should be allowed"

        # 4th should be denied
        result = check_rate_limit("mem-test", "free")
        assert result.allowed is False
        assert result.remaining == 0
    finally:
        rl.TIER_LIMITS.clear()


def test_tier_limits_populated():
    """Verify TIER_LIMITS matches settings values after population."""
    rl.TIER_LIMITS.clear()
    rl._redis_client = None

    try:
        # Trigger lazy population by calling check_rate_limit
        check_rate_limit("tier-test", "anonymous")

        assert rl.TIER_LIMITS["anonymous"] == settings.rate_limit_anonymous
        assert rl.TIER_LIMITS["free"] == settings.rate_limit_free
        assert rl.TIER_LIMITS["pro"] == settings.rate_limit_pro
        assert rl.TIER_LIMITS["enterprise"] == settings.rate_limit_enterprise
    finally:
        rl.TIER_LIMITS.clear()
