"""Sliding-window rate limiter (Redis or in-memory) + daily limits (DB-backed)."""

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from uuid import uuid4

from .config import settings

logger = logging.getLogger("bitcoin_api.rate_limit")

_lock = threading.Lock()


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset: float = 0.0  # unix timestamp when window resets


TIER_LIMITS: dict[str, int] = {}  # populated at startup

DAILY_LIMITS: dict[str, int] = {
    "anonymous": 1000,
    "free": 10000,
    "pro": 100000,
    "enterprise": 0,  # 0 = unlimited
}

# In-memory backend state
_windows: dict[str, list[float]] = defaultdict(list)

WINDOW_SECONDS = 60.0

# Redis backend state
_redis_client = None


def _load_tier_limits() -> dict[str, int]:
    return {
        "anonymous": settings.rate_limit_anonymous,
        "free": settings.rate_limit_free,
        "pro": settings.rate_limit_pro,
        "enterprise": settings.rate_limit_enterprise,
    }


def init_redis():
    """Initialize Upstash Redis client if configured. Call during app startup."""
    global _redis_client
    if settings.rate_limit_backend == "redis" and settings.upstash_redis_url:
        try:
            from upstash_redis import Redis
            _redis_client = Redis(
                url=settings.upstash_redis_url,
                token=settings.upstash_redis_token.get_secret_value() if settings.upstash_redis_token else "",
            )
            # Verify connectivity with a ping
            _redis_client.ping()
            logger.info("Rate limiting using Upstash Redis")
        except Exception as e:
            logger.warning("Failed to init Upstash Redis, falling back to memory: %s", e)
            _redis_client = None
    else:
        logger.info("Rate limiting using in-memory backend")


def _check_rate_limit_redis(bucket_key: str, limit: int, window: int = 60) -> RateLimitResult:
    """Sliding window rate limit using Redis sorted sets.

    Check count BEFORE adding — only zadd if under limit to prevent
    unbounded set growth from rejected requests.
    """
    now = time.time()
    window_start = now - window
    key = f"rl:{bucket_key}"

    # Phase 1: prune expired + check count
    pipe = _redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    results = pipe.exec()

    count = results[1]  # zcard after prune
    reset = int(now) + window

    if count >= limit:
        return RateLimitResult(allowed=False, limit=limit, remaining=0, reset=reset)

    # Phase 2: under limit — record this request
    member = f"{now}:{uuid4().hex[:8]}"
    pipe2 = _redis_client.pipeline()
    pipe2.zadd(key, {member: now})
    pipe2.expire(key, window + 1)
    pipe2.exec()

    remaining = max(0, limit - count - 1)
    return RateLimitResult(allowed=True, limit=limit, remaining=remaining, reset=reset)


def _check_rate_limit_memory(bucket_key: str, limit: int) -> RateLimitResult:
    """Original in-memory sliding window rate limiter."""
    now = time.time()
    cutoff = now - WINDOW_SECONDS

    # Prune expired timestamps
    timestamps = _windows[bucket_key]
    _windows[bucket_key] = timestamps = [t for t in timestamps if t > cutoff]

    remaining = max(0, limit - len(timestamps))
    reset = (timestamps[0] + WINDOW_SECONDS) if timestamps else (now + WINDOW_SECONDS)

    if len(timestamps) >= limit:
        return RateLimitResult(allowed=False, limit=limit, remaining=0, reset=reset)

    timestamps.append(now)

    # Clean up stale buckets to prevent memory leak
    if len(_windows) > 10000:
        stale = [k for k, v in _windows.items() if not v or v[-1] < cutoff]
        for k in stale:
            del _windows[k]

    return RateLimitResult(allowed=True, limit=limit, remaining=remaining - 1, reset=reset)


def check_rate_limit(bucket_key: str, tier: str) -> RateLimitResult:
    global TIER_LIMITS
    with _lock:
        if not TIER_LIMITS:
            TIER_LIMITS = _load_tier_limits()

        limit = TIER_LIMITS.get(tier, TIER_LIMITS["anonymous"])

        if _redis_client:
            try:
                return _check_rate_limit_redis(bucket_key, limit)
            except Exception as e:
                logger.warning("Redis rate limit failed, falling back to memory: %s", e)

        return _check_rate_limit_memory(bucket_key, limit)


def check_daily_limit(bucket_key: str, tier: str) -> RateLimitResult:
    daily_limit = DAILY_LIMITS.get(tier, DAILY_LIMITS["anonymous"])

    # Unlimited
    if daily_limit == 0:
        return RateLimitResult(allowed=True, limit=0, remaining=0)

    from .db import count_daily_usage
    used = count_daily_usage(bucket_key)
    remaining = max(0, daily_limit - used)

    if used >= daily_limit:
        return RateLimitResult(allowed=False, limit=daily_limit, remaining=0)

    return RateLimitResult(allowed=True, limit=daily_limit, remaining=remaining)
