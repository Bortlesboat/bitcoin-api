"""API key authentication."""

import hashlib
import logging
from dataclasses import dataclass

from fastapi import Request

from .db import lookup_key

log = logging.getLogger(__name__)


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
    record = lookup_key(key_hash)

    if record is None or not record["active"]:
        return ApiKeyInfo(tier="invalid", query_param_used=via_query)

    return ApiKeyInfo(
        tier=record["tier"],
        key_hash=record["key_hash"],
        label=record.get("label"),
        query_param_used=via_query,
    )
