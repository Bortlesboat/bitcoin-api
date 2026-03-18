"""Fee Observatory endpoints — multi-source fee estimate comparison and accuracy scoring."""

import logging
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from ..config import settings
from ..models import build_meta

log = logging.getLogger("bitcoin_api")

router = APIRouter(prefix="/fees/observatory", tags=["Fee Observatory"])

# ---------------------------------------------------------------------------
# Lazy read-only connection to observatory DB
# ---------------------------------------------------------------------------

_obs_conn: sqlite3.Connection | None = None


def _get_obs_conn() -> sqlite3.Connection:
    """Return a read-only connection to the observatory DB (lazy singleton)."""
    global _obs_conn
    if _obs_conn is not None:
        return _obs_conn

    db_path = Path(settings.observatory_db_path).expanduser()
    if not db_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Fee Observatory database not available",
        )

    _obs_conn = sqlite3.connect(
        f"file:{db_path}?mode=ro", uri=True, check_same_thread=False,
    )
    _obs_conn.row_factory = sqlite3.Row
    _obs_conn.execute("PRAGMA journal_mode=WAL")
    return _obs_conn


# ---------------------------------------------------------------------------
# Query helpers (inlined to avoid hard dependency on fee_observatory package)
# ---------------------------------------------------------------------------

def _query_scoreboard(conn: sqlite3.Connection, hours: float) -> list[dict]:
    from datetime import datetime, timedelta, timezone

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
    rows = conn.execute(
        """SELECT
            source,
            COUNT(*) as total_outcomes,
            SUM(would_have_confirmed) as confirmed_count,
            ROUND(100.0 * SUM(would_have_confirmed) / COUNT(*), 1) as accuracy_pct,
            ROUND(AVG(CASE WHEN would_have_confirmed = 1
                       THEN estimate_sat_vb - actual_min_feerate
                       ELSE NULL END), 2) as avg_overpayment,
            ROUND(AVG(estimate_sat_vb), 2) as avg_estimate
        FROM confirmation_outcomes
        WHERE estimate_timestamp >= ?
        GROUP BY source
        ORDER BY accuracy_pct DESC, avg_overpayment ASC""",
        (cutoff,),
    ).fetchall()
    return [dict(r) for r in rows]


def _query_block_fee_stats(conn: sqlite3.Connection, limit: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM block_fee_stats ORDER BY height DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def _query_fee_estimates_multi(
    conn: sqlite3.Connection, hours: float, source: str | None, limit: int,
) -> list[dict]:
    from datetime import datetime, timedelta, timezone

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
    if source:
        rows = conn.execute(
            "SELECT * FROM fee_estimates_multi WHERE timestamp >= ? AND source = ? ORDER BY timestamp DESC LIMIT ?",
            (cutoff, source, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM fee_estimates_multi WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
            (cutoff, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/scoreboard")
def observatory_scoreboard(
    hours: float = Query(168, ge=1, le=720, description="Lookback window in hours (default 7 days)"),
):
    """Per-source accuracy ranking with overpayment stats.

    Compares fee estimates from multiple sources against actual block inclusion
    to rank which estimators are most accurate and which overpay the most.
    """
    conn = _get_obs_conn()
    data = _query_scoreboard(conn, hours)
    meta = build_meta()
    return {"data": data, "meta": meta.model_dump()}


@router.get("/block-stats")
def observatory_block_stats(
    limit: int = Query(50, ge=1, le=144, description="Number of recent blocks"),
):
    """Per-block fee statistics (percentiles, min/max/median feerate).

    Returns computed fee stats for recent blocks, useful for understanding
    fee market dynamics at the block level.
    """
    conn = _get_obs_conn()
    data = _query_block_fee_stats(conn, limit)
    meta = build_meta()
    return {"data": data, "meta": meta.model_dump()}


@router.get("/estimates")
def observatory_estimates(
    hours: float = Query(24, ge=1, le=168, description="Lookback window in hours"),
    source: str | None = Query(None, description="Filter by source (e.g. 'core', 'mempool')"),
    limit: int = Query(5000, ge=1, le=10000, description="Max rows"),
):
    """Multi-source fee estimate time series.

    Returns raw fee estimates from all tracked sources over the specified
    time window. Use the `source` parameter to filter to a single estimator.
    """
    conn = _get_obs_conn()
    data = _query_fee_estimates_multi(conn, hours, source, limit)
    meta = build_meta()
    return {"data": data, "meta": meta.model_dump()}
