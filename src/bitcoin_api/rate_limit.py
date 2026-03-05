"""Sliding-window rate limiter (in-memory) + daily limits (DB-backed)."""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field

from .config import settings

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

# bucket_key -> list of timestamps
_windows: dict[str, list[float]] = defaultdict(list)

WINDOW_SECONDS = 60.0


def _load_tier_limits() -> dict[str, int]:
    return {
        "anonymous": settings.rate_limit_anonymous,
        "free": settings.rate_limit_free,
        "pro": settings.rate_limit_pro,
        "enterprise": settings.rate_limit_enterprise,
    }


def check_rate_limit(bucket_key: str, tier: str) -> RateLimitResult:
    global TIER_LIMITS
    with _lock:
        if not TIER_LIMITS:
            TIER_LIMITS = _load_tier_limits()

        limit = TIER_LIMITS.get(tier, TIER_LIMITS["anonymous"])
        now = time.monotonic()
        cutoff = now - WINDOW_SECONDS

        # Prune expired timestamps
        timestamps = _windows[bucket_key]
        _windows[bucket_key] = timestamps = [t for t in timestamps if t > cutoff]

        remaining = max(0, limit - len(timestamps))
        reset = (timestamps[0] + WINDOW_SECONDS) if timestamps else (now + WINDOW_SECONDS)

        if len(timestamps) >= limit:
            return RateLimitResult(allowed=False, limit=limit, remaining=0, reset=reset)

        timestamps.append(now)

        # Clean up empty buckets to prevent memory leak (prune stale keys)
        if len(_windows) > 10000:
            stale = [k for k, v in _windows.items() if not v]
            for k in stale:
                del _windows[k]

        return RateLimitResult(allowed=True, limit=limit, remaining=remaining - 1, reset=reset)


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
