"""Self-serve API key registration."""

import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..auth import hash_key
from ..db import get_db
from ..models import envelope

router = APIRouter(tags=["Keys"])


class RegisterRequest(BaseModel):
    email: str
    label: str | None = None


@router.post("/register")
def register(body: RegisterRequest):
    email = body.email.strip().lower()
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=422, detail="Invalid email address")

    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM api_keys WHERE email = ?", (email,)
    ).fetchone()[0]
    if count >= 3:
        raise HTTPException(status_code=429, detail="Maximum 3 keys per email")

    raw_key = "btc_" + secrets.token_hex(16)
    key_hash = hash_key(raw_key)
    prefix = raw_key[:8]

    conn.execute(
        "INSERT INTO api_keys (key_hash, prefix, tier, label, email) VALUES (?, ?, 'free', ?, ?)",
        (key_hash, prefix, body.label, email),
    )
    conn.commit()

    return envelope({"api_key": raw_key, "tier": "free", "label": body.label})
