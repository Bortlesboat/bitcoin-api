"""SQLite database for API keys and usage tracking."""

import hashlib
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


def _hash_ip(ip: str) -> str:
    """Hash an IP address for privacy-safe storage."""
    if not ip:
        return ""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def prune_x402_payments(days: int = 180) -> int:
    """Delete x402 payment records older than *days*."""
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM x402_payments WHERE timestamp < datetime('now', ?)",
        (f"-{days} days",),
    )
    conn.commit()
    return cursor.rowcount


def log_x402_payment(
    endpoint: str,
    price_usd: str,
    status: str,
    client_ip: str = "",
    payment_id: str = "",
    user_agent: str = "",
) -> None:
    """Log an x402 payment event to the database."""
    conn = get_db()
    conn.execute(
        "INSERT INTO x402_payments (endpoint, price_usd, payment_status, client_ip_hash, payment_id, user_agent) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (endpoint, price_usd, status, _hash_ip(client_ip), payment_id, (user_agent or "")[:256]),
    )
    conn.commit()


def get_x402_stats() -> dict:
    """Return aggregated x402 payment statistics."""
    conn = get_db()

    # Totals by status
    rows = conn.execute(
        "SELECT payment_status, COUNT(*) as cnt FROM x402_payments GROUP BY payment_status"
    ).fetchall()
    totals = {row["payment_status"]: row["cnt"] for row in rows}

    # Total revenue (sum of price_usd for paid transactions)
    rev_row = conn.execute(
        "SELECT COALESCE(SUM(CAST(REPLACE(price_usd, '$', '') AS REAL)), 0) as total "
        "FROM x402_payments WHERE payment_status = 'paid'"
    ).fetchone()
    total_revenue = rev_row["total"] if rev_row else 0.0

    # Top endpoints
    top_endpoints = conn.execute(
        "SELECT endpoint, "
        "SUM(CASE WHEN payment_status = 'challenged' THEN 1 ELSE 0 END) as challenges, "
        "SUM(CASE WHEN payment_status = 'paid' THEN 1 ELSE 0 END) as paid "
        "FROM x402_payments GROUP BY endpoint ORDER BY challenges DESC LIMIT 10"
    ).fetchall()

    # Recent payments (last 20, no client IP)
    recent = conn.execute(
        "SELECT timestamp, endpoint, payment_status, price_usd, payment_id "
        "FROM x402_payments ORDER BY timestamp DESC LIMIT 20"
    ).fetchall()

    # Last 24 hours
    last_24h_rows = conn.execute(
        "SELECT payment_status, COUNT(*) as cnt FROM x402_payments "
        "WHERE timestamp >= datetime('now', '-1 day') GROUP BY payment_status"
    ).fetchall()
    last_24h = {row["payment_status"]: row["cnt"] for row in last_24h_rows}

    # Hourly breakdown for charting (last 7 days)
    hourly = conn.execute(
        "SELECT strftime('%Y-%m-%dT%H:00:00Z', timestamp) as hour, payment_status, COUNT(*) as cnt "
        "FROM x402_payments WHERE timestamp >= datetime('now', '-7 days') "
        "GROUP BY hour, payment_status ORDER BY hour"
    ).fetchall()

    # Conversion rate (paid / challenged, handle div by zero)
    total_challenges = totals.get("challenged", 0)
    total_paid = totals.get("paid", 0)
    conversion_rate = (total_paid / total_challenges * 100) if total_challenges > 0 else 0.0

    # Daily revenue breakdown
    daily_revenue_rows = conn.execute(
        "SELECT date(timestamp) as day, "
        "COALESCE(SUM(CAST(REPLACE(price_usd, '$', '') AS REAL)), 0) as revenue "
        "FROM x402_payments WHERE payment_status = 'paid' "
        "GROUP BY day ORDER BY day"
    ).fetchall()

    # Unique payers (distinct client_ip_hash where paid)
    unique_row = conn.execute(
        "SELECT COUNT(DISTINCT client_ip_hash) as cnt "
        "FROM x402_payments WHERE payment_status = 'paid' AND client_ip_hash != ''"
    ).fetchone()
    unique_payers = unique_row["cnt"] if unique_row else 0

    return {
        "total_challenges": total_challenges,
        "total_paid": total_paid,
        "total_failed": totals.get("failed", 0),
        "total_revenue_usd": f"{total_revenue:.2f}",
        "conversion_rate": round(conversion_rate, 1),
        "unique_payers": unique_payers,
        "daily_revenue": [
            {"date": r["day"], "revenue_usd": f"{r['revenue']:.2f}"}
            for r in daily_revenue_rows
        ],
        "top_endpoints": [
            {"endpoint": r["endpoint"], "challenges": r["challenges"], "paid": r["paid"]}
            for r in top_endpoints
        ],
        "recent_payments": [
            {
                "timestamp": r["timestamp"],
                "endpoint": r["endpoint"],
                "status": r["payment_status"],
                "price": r["price_usd"],
                "payment_id": r["payment_id"] or "",
            }
            for r in recent
        ],
        "last_24h": {
            "challenges": last_24h.get("challenged", 0),
            "paid": last_24h.get("paid", 0),
            "failed": last_24h.get("failed", 0),
        },
        "hourly": [
            {"hour": r["hour"], "status": r["payment_status"], "count": r["cnt"]}
            for r in hourly
        ],
    }


