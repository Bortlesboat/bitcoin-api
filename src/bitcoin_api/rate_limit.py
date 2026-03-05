"""Sliding-window rate limiter (in-memory)."""

import time
from collections import defaultdict
from dataclasses import dataclass, field

from .config import settings


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset: float  # unix timestamp when window resets


TIER_LIMITS: dict[str, int] = {}  # populated at startup


def _load_tier_limits() -> dict[str, int]:
    return {
        "anonymous": settings.rate_limit_anonymous,
        "free": settings.rate_limit_free,
        "pro": settings.rate_limit_pro,
        "enterprise": settings.rate_limit_enterprise,
    }


# bucket_key -> list of timestamps
_windows: dict[str, list[float]] = defaultdict(list)

WINDOW_SECONDS = 60.0


def check_rate_limit(bucket_key: str, tier: str) -> RateLimitResult:
    global TIER_LIMITS
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
    return RateLimitResult(allowed=True, limit=limit, remaining=remaining - 1, reset=reset)
