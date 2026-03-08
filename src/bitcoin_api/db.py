"""SQLite database for API keys and usage tracking."""

import sqlite3
import threading
from pathlib import Path

from .config import settings

_local = threading.local()
_db_path: Path | None = None
_initialized = False
_init_lock = threading.Lock()


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
                # Run migrations (creates tables + indexes)
                from .migrations.runner import run_pending
                run_pending(conn)
                conn.close()
                _initialized = True

    # Each thread gets its own connection
    conn = getattr(_local, "conn", None)
    if conn is None:
        _local.conn = _make_conn(_db_path)
        conn = _local.conn
    return conn


def close_db() -> None:
    """Close the thread-local DB connection if open."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _local.conn = None


def log_usage(
    key_hash: str | None,
    endpoint: str,
    status_code: int,
    method: str | None = None,
    response_time_ms: float | None = None,
    user_agent: str | None = None,
    client_type: str = "unknown",
    referrer: str = "",
    client_ip: str = "",
    error_type: str = "",
) -> None:
    """Buffer a usage log entry for batch insertion."""
    from .usage_buffer import usage_buffer
    usage_buffer.log(key_hash, endpoint, status_code, method, response_time_ms, user_agent, client_type, referrer,
                     client_ip=client_ip, error_type=error_type)


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


