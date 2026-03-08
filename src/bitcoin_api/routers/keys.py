"""Self-serve API key registration."""

import re
import secrets
import time
import threading

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..auth import hash_key, clear_auth_cache
from ..cache import get_cached_node_info
from ..db import get_db
from ..exceptions import ERROR_TYPES, _GUIDE_URL
from ..metrics import API_KEYS_REGISTERED
from ..models import ErrorResponse, ErrorDetail, envelope
from ..notifications import send_welcome_email, track_registration

router = APIRouter(tags=["Keys"])

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

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
    utm_source: str | None = Field(None, max_length=100)
    utm_medium: str | None = Field(None, max_length=100)
    utm_campaign: str | None = Field(None, max_length=100)


@router.post("/register")
def register(body: RegisterRequest, request: Request, background_tasks: BackgroundTasks):
    if not body.agreed_to_terms:
        raise HTTPException(
            status_code=422,
            detail="You must agree to the Terms of Service (agreed_to_terms: true). See https://bitcoinsapi.com/terms",
        )

    # Per-IP rate limit on registration
    client_ip = request.client.host if request.client else "unknown"
    if not _check_reg_rate_limit(client_ip):
        request_id = getattr(request.state, "request_id", None)
        resp = JSONResponse(
            status_code=429,
            content=ErrorResponse(
                error=ErrorDetail(
                    type=ERROR_TYPES["rate_limit"],
                    status=429,
                    title="Too Many Requests",
                    detail="Too many registration attempts. Try again later.",
                    request_id=request_id,
                    help_url=_GUIDE_URL,
                )
            ).model_dump(),
        )
        resp.headers["Retry-After"] = "3600"
        if request_id:
            resp.headers["X-Request-ID"] = request_id
        return resp

    email = body.email.strip().lower()
    if not _EMAIL_RE.match(email) or len(email) > 254:
        raise HTTPException(status_code=422, detail="Invalid email format. Example: you@example.com")

    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM api_keys WHERE email = ?", (email,)
    ).fetchone()[0]
    if count >= 3:
        raise HTTPException(status_code=429, detail="Registration limit reached. Contact api@bitcoinsapi.com if you need additional keys.")

    raw_key = "btc_" + secrets.token_hex(16)
    key_hash = hash_key(raw_key)
    prefix = raw_key[:8]

    # Capture registration source for funnel tracking
    reg_referrer = request.headers.get("referer", "")
    conn.execute(
        "INSERT INTO api_keys (key_hash, prefix, tier, label, email, "
        "registration_referrer, utm_source, utm_medium, utm_campaign) "
        "VALUES (?, ?, 'free', ?, ?, ?, ?, ?, ?)",
        (key_hash, prefix, body.label, email,
         reg_referrer, body.utm_source or "", body.utm_medium or "", body.utm_campaign or ""),
    )
    conn.commit()
    clear_auth_cache()
    API_KEYS_REGISTERED.inc()

    # Send welcome email as background task (non-blocking)
    background_tasks.add_task(send_welcome_email, email, raw_key, body.label or "default")

    # PostHog server-side registration event as background task
    background_tasks.add_task(track_registration, email, "free", body.label or "default")

    height, chain = get_cached_node_info()
    return envelope({"api_key": raw_key, "tier": "free", "label": body.label}, height=height, chain=chain)


@router.post("/unsubscribe")
def unsubscribe_emails(request: Request, api_key: str = Header(alias="X-API-Key")):
    """Opt out of usage alert emails."""
    key_hash = hash_key(api_key)
    conn = get_db()
    row = conn.execute("SELECT key_hash FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="API key not found")
    conn.execute("UPDATE api_keys SET email_opt_out = 1 WHERE key_hash = ?", (key_hash,))
    conn.commit()
    height, chain = get_cached_node_info()
    return envelope({"unsubscribed": True}, height=height, chain=chain)
