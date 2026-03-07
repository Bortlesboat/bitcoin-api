"""Self-serve API key registration."""

import secrets
import time
import threading

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import hash_key
from ..cache import get_cached_node_info
from ..db import get_db
from ..models import envelope

router = APIRouter(tags=["Keys"])

# Per-IP registration rate limiter: max 5 registrations per hour
_reg_attempts: dict[str, list[float]] = {}
_reg_lock = threading.Lock()
_REG_WINDOW = 3600  # 1 hour
_REG_MAX = 5


def _check_reg_rate_limit(ip: str) -> bool:
    """Return True if allowed, False if rate limited."""
    now = time.monotonic()
    with _reg_lock:
        timestamps = _reg_attempts.get(ip, [])
        timestamps = [t for t in timestamps if now - t < _REG_WINDOW]
        if len(timestamps) >= _REG_MAX:
            _reg_attempts[ip] = timestamps
            return False
        timestamps.append(now)
        _reg_attempts[ip] = timestamps
    return True


class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=254)
    label: str | None = Field(None, max_length=100)
    agreed_to_terms: bool = False


@router.post("/register")
def register(body: RegisterRequest, request: Request):
    if not body.agreed_to_terms:
        raise HTTPException(
            status_code=422,
            detail="You must agree to the Terms of Service (agreed_to_terms: true). See https://bitcoinsapi.com/terms",
        )

    # Per-IP rate limit on registration
    client_ip = request.client.host if request.client else "unknown"
    if not _check_reg_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many registration attempts. Try again later.")

    email = body.email.strip().lower()
    if "@" not in email or "." not in email or len(email) < 5:
        raise HTTPException(status_code=422, detail="Invalid email address")

    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM api_keys WHERE email = ?", (email,)
    ).fetchone()[0]
    if count >= 3:
        raise HTTPException(status_code=429, detail="Registration limit reached. Contact api@bitcoinsapi.com if you need additional keys.")

    raw_key = "btc_" + secrets.token_hex(16)
    key_hash = hash_key(raw_key)
    prefix = raw_key[:8]

    conn.execute(
        "INSERT INTO api_keys (key_hash, prefix, tier, label, email) VALUES (?, ?, 'free', ?, ?)",
        (key_hash, prefix, body.label, email),
    )
    conn.commit()

    height, chain = get_cached_node_info()
    return envelope({"api_key": raw_key, "tier": "free", "label": body.label}, height=height, chain=chain)
