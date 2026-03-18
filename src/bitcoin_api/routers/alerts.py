"""Fee alert webhook endpoints: register/list/delete fee alerts and transaction watches."""

import ipaddress
import logging
import socket
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field, HttpUrl

from ..auth import require_api_key_hash
from ..db import get_db
from ..models import envelope
from ..validators import validate_txid

log = logging.getLogger("bitcoin_api.routers.alerts")

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def _validate_webhook_url(url: str) -> None:
    """Reject webhook URLs pointing to private/internal IPs (SSRF protection)."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=422, detail="Invalid webhook URL")
    try:
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for _, _, _, _, sockaddr in resolved:
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise HTTPException(
                    status_code=422,
                    detail="Webhook URL must not point to a private or internal IP address",
                )
    except socket.gaierror:
        raise HTTPException(status_code=422, detail="Could not resolve webhook URL hostname")


# --- DB setup (idempotent) ---

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS fee_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key_hash TEXT NOT NULL,
    webhook_url TEXT NOT NULL,
    condition TEXT NOT NULL DEFAULT 'below',
    threshold_sat_vb REAL NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    last_triggered_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS tx_watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key_hash TEXT NOT NULL,
    txid TEXT NOT NULL,
    webhook_url TEXT NOT NULL,
    target_confirmations INTEGER NOT NULL DEFAULT 1,
    current_confirmations INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    last_checked_at TEXT,
    triggered_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _ensure_tables():
    """Create alert tables if they don't exist. Safe to call multiple times."""
    db = get_db()
    # Use IF NOT EXISTS — idempotent and safe across test resets
    db.executescript(_SCHEMA_SQL)
    db.commit()


# --- Request/Response models ---


class FeeAlertRequest(BaseModel):
    webhook_url: HttpUrl = Field(description="URL to POST when condition is met")
    threshold_sat_vb: float = Field(gt=0, description="Fee rate threshold in sat/vB")
    condition: Literal["below", "above"] = Field(default="below", description="Trigger when fees go below or above threshold")


class TxWatchRequest(BaseModel):
    webhook_url: HttpUrl = Field(description="URL to POST when confirmations reached")
    target_confirmations: int = Field(default=1, ge=1, le=100, description="Number of confirmations to wait for")


# --- Endpoints ---


@router.post("/fees")
def create_fee_alert(
    req: FeeAlertRequest,
    key_hash: str = Depends(require_api_key_hash),
):
    """Register a webhook to be called when fees cross a threshold.

    The webhook URL will receive a POST with JSON body containing
    current fee data when the condition is met.
    """
    _validate_webhook_url(str(req.webhook_url))
    _ensure_tables()
    db = get_db()

    # Limit: max 10 active alerts per key
    count = db.execute(
        "SELECT COUNT(*) FROM fee_alerts WHERE api_key_hash = ? AND active = 1",
        (key_hash,),
    ).fetchone()[0]
    if count >= 10:
        raise HTTPException(status_code=429, detail="Maximum 10 active fee alerts per API key")

    cursor = db.execute(
        "INSERT INTO fee_alerts (api_key_hash, webhook_url, condition, threshold_sat_vb) VALUES (?, ?, ?, ?)",
        (key_hash, str(req.webhook_url), req.condition, req.threshold_sat_vb),
    )
    db.commit()

    return envelope({
        "id": cursor.lastrowid,
        "webhook_url": str(req.webhook_url),
        "condition": req.condition,
        "threshold_sat_vb": req.threshold_sat_vb,
        "active": True,
    })


@router.get("/fees")
def list_fee_alerts(
    key_hash: str = Depends(require_api_key_hash),
):
    """List all fee alerts for the authenticated API key."""
    _ensure_tables()
    db = get_db()
    rows = db.execute(
        "SELECT id, webhook_url, condition, threshold_sat_vb, active, last_triggered_at, created_at "
        "FROM fee_alerts WHERE api_key_hash = ? ORDER BY created_at DESC",
        (key_hash,),
    ).fetchall()

    alerts = [
        {
            "id": r[0], "webhook_url": r[1], "condition": r[2],
            "threshold_sat_vb": r[3], "active": bool(r[4]),
            "last_triggered_at": r[5], "created_at": r[6],
        }
        for r in rows
    ]
    return envelope(alerts)


@router.delete("/fees/{alert_id}")
def delete_fee_alert(
    alert_id: int = Path(description="Alert ID to deactivate"),
    key_hash: str = Depends(require_api_key_hash),
):
    """Deactivate a fee alert."""
    _ensure_tables()
    db = get_db()
    result = db.execute(
        "UPDATE fee_alerts SET active = 0 WHERE id = ? AND api_key_hash = ?",
        (alert_id, key_hash),
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return envelope({"id": alert_id, "active": False})


@router.post("/tx/watch/{txid}")
def create_tx_watch(
    req: TxWatchRequest,
    txid: str = Path(description="Transaction ID to watch"),
    key_hash: str = Depends(require_api_key_hash),
):
    """Register a webhook to fire when a transaction reaches N confirmations."""
    validate_txid(txid)
    _validate_webhook_url(str(req.webhook_url))
    _ensure_tables()
    db = get_db()

    # Limit: max 20 active watches per key
    count = db.execute(
        "SELECT COUNT(*) FROM tx_watches WHERE api_key_hash = ? AND active = 1",
        (key_hash,),
    ).fetchone()[0]
    if count >= 20:
        raise HTTPException(status_code=429, detail="Maximum 20 active transaction watches per API key")

    cursor = db.execute(
        "INSERT INTO tx_watches (api_key_hash, txid, webhook_url, target_confirmations) VALUES (?, ?, ?, ?)",
        (key_hash, txid, str(req.webhook_url), req.target_confirmations),
    )
    db.commit()

    return envelope({
        "id": cursor.lastrowid,
        "txid": txid,
        "webhook_url": str(req.webhook_url),
        "target_confirmations": req.target_confirmations,
        "active": True,
    })


@router.get("/tx")
def list_tx_watches(
    key_hash: str = Depends(require_api_key_hash),
):
    """List all transaction watches for the authenticated API key."""
    _ensure_tables()
    db = get_db()
    rows = db.execute(
        "SELECT id, txid, webhook_url, target_confirmations, current_confirmations, active, triggered_at, created_at "
        "FROM tx_watches WHERE api_key_hash = ? ORDER BY created_at DESC",
        (key_hash,),
    ).fetchall()

    watches = [
        {
            "id": r[0], "txid": r[1], "webhook_url": r[2],
            "target_confirmations": r[3], "current_confirmations": r[4],
            "active": bool(r[5]), "triggered_at": r[6], "created_at": r[7],
        }
        for r in rows
    ]
    return envelope(watches)


@router.delete("/tx/{watch_id}")
def delete_tx_watch(
    watch_id: int = Path(description="Watch ID to deactivate"),
    key_hash: str = Depends(require_api_key_hash),
):
    """Deactivate a transaction watch."""
    _ensure_tables()
    db = get_db()
    result = db.execute(
        "UPDATE tx_watches SET active = 0 WHERE id = ? AND api_key_hash = ?",
        (watch_id, key_hash),
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Watch not found")
    return envelope({"id": watch_id, "active": False})
