"""Admin analytics endpoints for API usage monitoring."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..db import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])

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


def _require_admin(request: Request):
    import secrets
    from ..config import settings
    if not settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Analytics not configured")
    key = request.headers.get("X-Admin-Key", "")
    if not secrets.compare_digest(key, settings.admin_api_key):
        raise HTTPException(status_code=403, detail="Invalid admin key")


def _period_sql(period: str) -> str:
    return _PERIOD_MAP.get(period, "-24 hours")


@router.get("/overview", dependencies=[Depends(_require_admin)])
def analytics_overview():
    conn = get_db()
    result = {}
    for label, offset in [("24h", "-24 hours"), ("7d", "-7 days"), ("30d", "-30 days")]:
        row = conn.execute(
            "SELECT COUNT(*) FROM usage_log WHERE ts >= datetime('now', ?)", (offset,)
        ).fetchone()
        result[f"requests_{label}"] = row[0]

    row = conn.execute(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log WHERE ts >= datetime('now', '-24 hours')"
    ).fetchone()
    result["unique_keys_24h"] = row[0]

    total = result["requests_24h"]
    if total > 0:
        errors = conn.execute(
            "SELECT COUNT(*) FROM usage_log WHERE ts >= datetime('now', '-24 hours') AND status >= 400"
        ).fetchone()[0]
        result["error_rate_24h"] = round(errors / total, 4)
    else:
        result["error_rate_24h"] = 0.0

    row = conn.execute(
        "SELECT AVG(response_time_ms) FROM usage_log WHERE ts >= datetime('now', '-24 hours') AND response_time_ms IS NOT NULL"
    ).fetchone()
    result["avg_latency_ms_24h"] = round(row[0], 2) if row[0] else None

    return {"data": result}


@router.get("/requests", dependencies=[Depends(_require_admin)])
def analytics_requests(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
    interval: str = Query("1h", pattern="^(1m|5m|15m|1h|6h|1d)$"),
):
    conn = get_db()
    offset = _period_sql(period)
    interval_secs = _INTERVAL_MAP.get(interval, 3600)

    rows = conn.execute(
        "SELECT strftime('%s', ts) as epoch, COUNT(*) as cnt "
        "FROM usage_log WHERE ts >= datetime('now', ?) "
        "GROUP BY CAST(strftime('%s', ts) AS INTEGER) / ? "
        "ORDER BY epoch",
        (offset, interval_secs),
    ).fetchall()

    return {"data": [{"timestamp": int(r[0]), "count": r[1]} for r in rows]}


@router.get("/endpoints", dependencies=[Depends(_require_admin)])
def analytics_endpoints(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
    limit: int = Query(20, ge=1, le=100),
):
    conn = get_db()
    offset = _period_sql(period)

    rows = conn.execute(
        "SELECT endpoint, COUNT(*) as hits, AVG(response_time_ms) as avg_ms "
        "FROM usage_log WHERE ts >= datetime('now', ?) "
        "GROUP BY endpoint ORDER BY hits DESC LIMIT ?",
        (offset, limit),
    ).fetchall()

    return {
        "data": [
            {
                "endpoint": r[0],
                "hits": r[1],
                "avg_latency_ms": round(r[2], 2) if r[2] else None,
            }
            for r in rows
        ]
    }


@router.get("/errors", dependencies=[Depends(_require_admin)])
def analytics_errors(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
):
    conn = get_db()
    offset = _period_sql(period)

    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt "
        "FROM usage_log WHERE ts >= datetime('now', ?) AND status >= 400 "
        "GROUP BY status ORDER BY cnt DESC",
        (offset,),
    ).fetchall()

    return {"data": [{"status": r[0], "count": r[1]} for r in rows]}


@router.get("/user-agents", dependencies=[Depends(_require_admin)])
def analytics_user_agents(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
    limit: int = Query(20, ge=1, le=100),
):
    conn = get_db()
    offset = _period_sql(period)

    rows = conn.execute(
        "SELECT user_agent, COUNT(*) as cnt "
        "FROM usage_log WHERE ts >= datetime('now', ?) AND user_agent IS NOT NULL AND user_agent != '' "
        "GROUP BY user_agent ORDER BY cnt DESC LIMIT ?",
        (offset, limit),
    ).fetchall()

    return {"data": [{"user_agent": r[0], "count": r[1]} for r in rows]}


@router.get("/latency", dependencies=[Depends(_require_admin)])
def analytics_latency(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
):
    conn = get_db()
    offset = _period_sql(period)

    rows = conn.execute(
        "SELECT response_time_ms FROM usage_log "
        "WHERE ts >= datetime('now', ?) AND response_time_ms IS NOT NULL "
        "ORDER BY response_time_ms",
        (offset,),
    ).fetchall()

    if not rows:
        return {"data": {"p50": None, "p95": None, "p99": None, "count": 0}}

    values = [r[0] for r in rows]
    n = len(values)

    def percentile(vs, p):
        idx = int(p / 100 * (len(vs) - 1))
        return round(vs[idx], 2)

    return {
        "data": {
            "p50": percentile(values, 50),
            "p95": percentile(values, 95),
            "p99": percentile(values, 99),
            "count": n,
        }
    }
