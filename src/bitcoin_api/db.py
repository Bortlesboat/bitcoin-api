"""SQLite database for API keys and usage tracking."""

import sqlite3
from pathlib import Path

from .config import settings

_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    key_hash   TEXT PRIMARY KEY,
    prefix     TEXT NOT NULL,
    tier       TEXT NOT NULL DEFAULT 'free',
    label      TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    active     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS usage_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash   TEXT,
    endpoint   TEXT NOT NULL,
    status     INTEGER NOT NULL,
    ts         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_usage_ts ON usage_log(ts);
CREATE INDEX IF NOT EXISTS idx_usage_key ON usage_log(key_hash);
CREATE INDEX IF NOT EXISTS idx_usage_key_ts ON usage_log(key_hash, ts);
"""


def get_db(db_path: Path | None = None) -> sqlite3.Connection:
    global _conn
    if _conn is None:
        path = db_path or settings.api_db_path
        _conn = sqlite3.connect(str(path), check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
    return _conn


def log_usage(key_hash: str | None, endpoint: str, status_code: int) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO usage_log (key_hash, endpoint, status) VALUES (?, ?, ?)",
        (key_hash, endpoint, status_code),
    )
    conn.commit()


def count_daily_usage(key_hash: str) -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) FROM usage_log WHERE key_hash = ? AND ts >= date('now')",
        (key_hash,),
    ).fetchone()
    return row[0] if row else 0


def prune_old_logs(days: int = 90) -> int:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM usage_log WHERE ts < datetime('now', ?)",
        (f"-{days} days",),
    )
    conn.commit()
    return cursor.rowcount


def lookup_key(key_hash: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT key_hash, prefix, tier, label, active FROM api_keys WHERE key_hash = ?",
        (key_hash,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)
