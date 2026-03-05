"""API key authentication."""

import hashlib
from dataclasses import dataclass

from fastapi import Request

from .db import lookup_key


@dataclass
class ApiKeyInfo:
    tier: str  # "anonymous", "free", "pro", "enterprise"
    key_hash: str | None = None
    label: str | None = None


def extract_api_key(request: Request) -> str | None:
    key = request.headers.get("X-API-Key")
    if key is None:
        key = request.query_params.get("api_key")
    return key


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def authenticate(request: Request) -> ApiKeyInfo:
    raw_key = extract_api_key(request)
    if raw_key is None:
        return ApiKeyInfo(tier="anonymous")

    key_hash = hash_key(raw_key)
    record = lookup_key(key_hash)

    if record is None or not record["active"]:
        return ApiKeyInfo(tier="anonymous")

    return ApiKeyInfo(
        tier=record["tier"],
        key_hash=record["key_hash"],
        label=record.get("label"),
    )
