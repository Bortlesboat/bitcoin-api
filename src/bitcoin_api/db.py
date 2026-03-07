"""SQLite database for API keys and usage tracking."""

import sqlite3
import threading
from pathlib import Path

from .config import settings

_local = threading.local()
_db_path: Path | None = None
_initialized = False
_init_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    key_hash   TEXT PRIMARY KEY,
    prefix     TEXT NOT NULL,
    tier       TEXT NOT NULL DEFAULT 'free',
    label      TEXT,
    email      TEXT,
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

CREATE TABLE IF NOT EXISTS fee_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL DEFAULT (datetime('now')),
    next_block_fee  REAL,
    median_fee      REAL,
    low_fee         REAL,
    mempool_size    INTEGER,
    mempool_vsize   INTEGER,
    congestion      TEXT
);

CREATE INDEX IF NOT EXISTS idx_fee_history_ts ON fee_history(ts);

"""


def _make_conn(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def get_db(db_path: Path | None = None) -> sqlite3.Connection:
    global _db_path, _initialized

    # First call initializes the path and schema
    if not _initialized:
        with _init_lock:
            if not _initialized:
                _db_path = db_path or settings.api_db_path
                _db_path.parent.mkdir(parents=True, exist_ok=True)
                conn = _make_conn(_db_path)
                conn.executescript(SCHEMA)
                # Migration: add email column if missing
                cols = [r[1] for r in conn.execute("PRAGMA table_info(api_keys)").fetchall()]
                if "email" not in cols:
                    conn.execute("ALTER TABLE api_keys ADD COLUMN email TEXT")
                    conn.commit()
                # Migration: add analytics columns to usage_log
                usage_cols = [r[1] for r in conn.execute("PRAGMA table_info(usage_log)").fetchall()]
                if "method" not in usage_cols:
                    conn.execute("ALTER TABLE usage_log ADD COLUMN method TEXT")
                    conn.execute("ALTER TABLE usage_log ADD COLUMN response_time_ms REAL")
                    conn.execute("ALTER TABLE usage_log ADD COLUMN user_agent TEXT")
                    conn.commit()
                conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_endpoint ON usage_log(endpoint)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_status ON usage_log(status)")
                conn.commit()
                conn.close()
                _initialized = True

    # Each thread gets its own connection
    conn = getattr(_local, "conn", None)
    if conn is None:
        _local.conn = _make_conn(_db_path)
        conn = _local.conn
    return conn


def log_usage(
    key_hash: str | None,
    endpoint: str,
    status_code: int,
    method: str | None = None,
    response_time_ms: float | None = None,
    user_agent: str | None = None,
) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO usage_log (key_hash, endpoint, status, method, response_time_ms, user_agent) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (key_hash, endpoint, status_code, method, response_time_ms, user_agent),
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


def record_fee_snapshot(
    next_block_fee: float,
    median_fee: float,
    low_fee: float,
    mempool_size: int,
    mempool_vsize: int,
    congestion: str,
) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO fee_history (next_block_fee, median_fee, low_fee, mempool_size, mempool_vsize, congestion) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (next_block_fee, median_fee, low_fee, mempool_size, mempool_vsize, congestion),
    )
    conn.commit()


def get_fee_history(hours: int = 24, interval_minutes: int = 10) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT ts, next_block_fee, median_fee, low_fee, mempool_size, mempool_vsize, congestion "
        "FROM fee_history WHERE ts >= datetime('now', ?) ORDER BY ts ASC",
        (f"-{hours} hours",),
    ).fetchall()
    if not rows:
        return []

    # Downsample to requested interval
    results = []
    last_ts = None
    for row in rows:
        d = dict(row)
        if last_ts is None or _ts_diff_minutes(last_ts, d["ts"]) >= interval_minutes:
            results.append(d)
            last_ts = d["ts"]
    return results


def _ts_diff_minutes(ts1: str, ts2: str) -> float:
    from datetime import datetime
    fmt = "%Y-%m-%d %H:%M:%S"
    t1 = datetime.strptime(ts1, fmt)
    t2 = datetime.strptime(ts2, fmt)
    return abs((t2 - t1).total_seconds()) / 60


def prune_fee_history(days: int = 30) -> int:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM fee_history WHERE ts < datetime('now', ?)",
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


