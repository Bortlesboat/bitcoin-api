"""Analytics query helpers — shared logic for the analytics router."""

from __future__ import annotations

from ..db import get_db

_PERIOD_MAP = {
    "1h": "-1 hours",
    "6h": "-6 hours",
    "24h": "-24 hours",
    "7d": "-7 days",
    "30d": "-30 days",
}

_INTERVAL_MAP = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "6h": 21600,
    "1d": 86400,
}


def period_sql(period: str) -> str:
    """Convert period string to SQLite datetime offset."""
    return _PERIOD_MAP.get(period, "-24 hours")


def interval_secs(interval: str) -> int:
    """Convert interval string to seconds."""
    return _INTERVAL_MAP.get(interval, 3600)


def query_rows(sql: str, params: tuple = ()) -> list[dict]:
    """Execute SQL and return results as list of dicts."""
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    """Execute SQL and return first row as dict, or None."""
    conn = get_db()
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def query_scalar(sql: str, params: tuple = ()) -> int | float | None:
    """Execute SQL and return first column of first row."""
    conn = get_db()
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def query_column(sql: str, params: tuple = (), *, column: int = 0) -> list:
    """Execute SQL and return a single column as a flat list."""
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    return [r[column] for r in rows]
