"""Shared validation helpers for API endpoints."""

import re

from fastapi import HTTPException

_HEX64_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def validate_hex64(value: str, label: str = "hash") -> str:
    """Validate that a string is exactly 64 hex characters. Returns the value or raises 422."""
    if not _HEX64_RE.match(value):
        raise HTTPException(status_code=422, detail=f"Invalid {label}: must be 64 hex characters")
    return value


def validate_txid(txid: str) -> str:
    return validate_hex64(txid, "txid")


def validate_block_hash(block_hash: str) -> str:
    return validate_hex64(block_hash, "block hash")
