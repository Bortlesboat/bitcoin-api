#!/usr/bin/env python3
"""Portable fee alert + tx watch worker.

Checks fee alerts and transaction watches, fires matching webhooks.
Designed to run as:
- Azure Function timer trigger (every 60s)
- GMKtec cron job (fallback after credits expire)
- Manual one-shot: python scripts/fee_alert_worker.py

Requires: requests, sqlite3 (stdlib)
Config via env vars:
  SATOSHI_API_URL  — API base URL (default: http://localhost:9332)
  SATOSHI_DB_PATH  — SQLite DB path (default: data/bitcoin_api.db)
"""

import json
import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fee_alert_worker")

API_URL = os.environ.get("SATOSHI_API_URL", "http://localhost:9332")
DB_PATH = os.environ.get("SATOSHI_DB_PATH", "data/bitcoin_api.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_current_fees() -> dict:
    """Fetch current fee estimates from the API."""
    resp = requests.get(f"{API_URL}/api/v1/fees/recommended", timeout=10)
    resp.raise_for_status()
    return resp.json()["data"]


def get_tx_confirmations(txid: str) -> int | None:
    """Get confirmation count for a transaction. Returns None if not found."""
    try:
        resp = requests.get(f"{API_URL}/api/v1/tx/{txid}", timeout=10)
        if resp.status_code == 404:
            return 0  # Not yet in a block
        resp.raise_for_status()
        data = resp.json()["data"]
        return data.get("confirmations", 0)
    except Exception as exc:
        log.warning("Failed to check tx %s: %s", txid[:16], exc)
        return None


def fire_webhook(url: str, payload: dict) -> bool:
    """POST payload to webhook URL. Returns True on success."""
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code < 300:
            log.info("Webhook fired: %s -> %d", url[:60], resp.status_code)
            return True
        log.warning("Webhook failed: %s -> %d", url[:60], resp.status_code)
        return False
    except Exception as exc:
        log.warning("Webhook error: %s -> %s", url[:60], exc)
        return False


def process_fee_alerts(db: sqlite3.Connection):
    """Check all active fee alerts and fire matching webhooks."""
    alerts = db.execute(
        "SELECT id, webhook_url, condition, threshold_sat_vb FROM fee_alerts WHERE active = 1"
    ).fetchall()

    if not alerts:
        return

    fees_data = get_current_fees()
    estimates = fees_data.get("estimates", {})
    next_block_fee = estimates.get("1", 0)

    if next_block_fee <= 0:
        log.warning("No valid fee data, skipping alerts")
        return

    now = datetime.now(timezone.utc).isoformat()

    for alert in alerts:
        triggered = False
        if alert["condition"] == "below" and next_block_fee < alert["threshold_sat_vb"]:
            triggered = True
        elif alert["condition"] == "above" and next_block_fee > alert["threshold_sat_vb"]:
            triggered = True

        if triggered:
            payload = {
                "alert_id": alert["id"],
                "condition": alert["condition"],
                "threshold_sat_vb": alert["threshold_sat_vb"],
                "current_fee_sat_vb": next_block_fee,
                "triggered_at": now,
            }
            if fire_webhook(alert["webhook_url"], payload):
                db.execute(
                    "UPDATE fee_alerts SET last_triggered_at = ? WHERE id = ?",
                    (now, alert["id"]),
                )

    db.commit()
    log.info("Processed %d fee alerts (next_block=%.1f sat/vB)", len(alerts), next_block_fee)


def process_tx_watches(db: sqlite3.Connection):
    """Check all active tx watches and fire matching webhooks."""
    watches = db.execute(
        "SELECT id, txid, webhook_url, target_confirmations FROM tx_watches WHERE active = 1"
    ).fetchall()

    if not watches:
        return

    now = datetime.now(timezone.utc).isoformat()

    for watch in watches:
        confs = get_tx_confirmations(watch["txid"])
        if confs is None:
            continue

        db.execute(
            "UPDATE tx_watches SET current_confirmations = ?, last_checked_at = ? WHERE id = ?",
            (confs, now, watch["id"]),
        )

        if confs >= watch["target_confirmations"]:
            payload = {
                "watch_id": watch["id"],
                "txid": watch["txid"],
                "confirmations": confs,
                "target_confirmations": watch["target_confirmations"],
                "triggered_at": now,
            }
            if fire_webhook(watch["webhook_url"], payload):
                db.execute(
                    "UPDATE tx_watches SET active = 0, triggered_at = ? WHERE id = ?",
                    (now, watch["id"]),
                )

    db.commit()
    log.info("Processed %d tx watches", len(watches))


def main():
    if not os.path.exists(DB_PATH):
        log.error("Database not found at %s", DB_PATH)
        sys.exit(1)

    db = get_db()
    try:
        process_fee_alerts(db)
        process_tx_watches(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
