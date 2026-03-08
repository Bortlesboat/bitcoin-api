"""API key authentication."""

import hashlib
import logging
from dataclasses import dataclass

from cachetools import TTLCache
from fastapi import HTTPException, Request

from .db import lookup_key

log = logging.getLogger(__name__)

# Cache DB lookups for 60s to avoid per-request queries
_auth_cache: TTLCache = TTLCache(maxsize=256, ttl=60)


def _cached_lookup(key_hash: str) -> dict | None:
    """Lookup key with TTL cache layer."""
    cached = _auth_cache.get(key_hash)
    if cached is not None:
        return cached
    result = lookup_key(key_hash)
    if result is not None:
        _auth_cache[key_hash] = result
    return result


def clear_auth_cache() -> None:
    """Clear the auth lookup cache (call after key mutations)."""
    _auth_cache.clear()

# Block-walking parameter caps per tier
BLOCKS_CAP = {"anonymous": 144, "free": 144, "pro": 1008, "enterprise": 2016}


def require_api_key(request: Request, endpoint_name: str = "this endpoint") -> str:
    """Require at least a free-tier API key. Returns the tier string."""
    tier = getattr(request.state, "tier", "anonymous")
    if tier == "anonymous":
        raise HTTPException(
            status_code=403,
            detail=f"API key required for {endpoint_name}. Register a free key: POST /api/v1/register",
        )
    return tier


def cap_blocks_param(blocks: int, tier: str) -> int:
    """Cap block-walking parameter based on user tier."""
    max_blocks = BLOCKS_CAP.get(tier, 144)
    return min(blocks, max_blocks)


@dataclass
class ApiKeyInfo:
    tier: str  # "anonymous", "free", "pro", "enterprise", "invalid"
    key_hash: str | None = None
    label: str | None = None
    query_param_used: bool = False


def extract_api_key(request: Request) -> tuple[str | None, bool]:
    key = request.headers.get("X-API-Key")
    if key is not None:
        return key, False
    key = request.query_params.get("api_key")
    if key is not None:
        return key, True
    return None, False


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def authenticate(request: Request) -> ApiKeyInfo:
    raw_key, via_query = extract_api_key(request)
    if raw_key is None:
        return ApiKeyInfo(tier="anonymous")

    if via_query:
        log.warning("API key passed via query param (deprecated) from %s", request.client.host if request.client else "unknown")

    key_hash = hash_key(raw_key)
    record = _cached_lookup(key_hash)

    if record is None or not record["active"]:
        return ApiKeyInfo(tier="invalid", query_param_used=via_query)

    return ApiKeyInfo(
        tier=record["tier"],
        key_hash=record["key_hash"],
        label=record.get("label"),
        query_param_used=via_query,
    )
