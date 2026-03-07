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


@router.get("/keys", dependencies=[Depends(_require_admin)])
def analytics_keys(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
    limit: int = Query(20, ge=1, le=100),
):
    """Per-key usage: hits, avg latency, error rate, last seen."""
    conn = get_db()
    offset = _period_sql(period)

    rows = conn.execute(
        "SELECT u.key_hash, k.prefix, COUNT(*) as hits, "
        "AVG(u.response_time_ms) as avg_ms, "
        "SUM(CASE WHEN u.status >= 400 THEN 1 ELSE 0 END) as errors, "
        "MAX(u.ts) as last_seen "
        "FROM usage_log u LEFT JOIN api_keys k ON u.key_hash = k.key_hash "
        "WHERE u.ts >= datetime('now', ?) "
        "GROUP BY u.key_hash ORDER BY hits DESC LIMIT ?",
        (offset, limit),
    ).fetchall()

    return {
        "data": [
            {
                "key_hash_short": (r["key_hash"] or "anonymous")[:8],
                "prefix": r["prefix"],
                "hits": r["hits"],
                "avg_latency_ms": round(r["avg_ms"], 2) if r["avg_ms"] else None,
                "error_rate": round(r["errors"] / r["hits"], 4) if r["hits"] else 0.0,
                "last_seen": r["last_seen"],
            }
            for r in rows
        ]
    }


@router.get("/growth", dependencies=[Depends(_require_admin)])
def analytics_growth():
    """Day-over-day and week-over-week request & key growth."""
    conn = get_db()

    today = conn.execute(
        "SELECT COUNT(*) FROM usage_log WHERE ts >= datetime('now', '-24 hours')"
    ).fetchone()[0]
    yesterday = conn.execute(
        "SELECT COUNT(*) FROM usage_log WHERE ts >= datetime('now', '-48 hours') AND ts < datetime('now', '-24 hours')"
    ).fetchone()[0]

    this_week = conn.execute(
        "SELECT COUNT(*) FROM usage_log WHERE ts >= datetime('now', '-7 days')"
    ).fetchone()[0]
    last_week = conn.execute(
        "SELECT COUNT(*) FROM usage_log WHERE ts >= datetime('now', '-14 days') AND ts < datetime('now', '-7 days')"
    ).fetchone()[0]

    keys_today = conn.execute(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log WHERE ts >= datetime('now', '-24 hours')"
    ).fetchone()[0]
    keys_yesterday = conn.execute(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log WHERE ts >= datetime('now', '-48 hours') AND ts < datetime('now', '-24 hours')"
    ).fetchone()[0]

    def pct_change(current, previous):
        if previous == 0:
            return None
        return round((current - previous) / previous * 100, 2)

    return {
        "data": {
            "requests_today": today,
            "requests_yesterday": yesterday,
            "requests_dod_pct": pct_change(today, yesterday),
            "requests_this_week": this_week,
            "requests_last_week": last_week,
            "requests_wow_pct": pct_change(this_week, last_week),
            "keys_today": keys_today,
            "keys_yesterday": keys_yesterday,
            "keys_dod_pct": pct_change(keys_today, keys_yesterday),
        }
    }


@router.get("/slow-endpoints", dependencies=[Depends(_require_admin)])
def analytics_slow_endpoints(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
    limit: int = Query(10, ge=1, le=50),
):
    """Top N endpoints by p95 latency."""
    conn = get_db()
    offset = _period_sql(period)

    rows = conn.execute(
        "SELECT endpoint, response_time_ms FROM usage_log "
        "WHERE ts >= datetime('now', ?) AND response_time_ms IS NOT NULL",
        (offset,),
    ).fetchall()

    # Group by endpoint and compute p95
    from collections import defaultdict
    by_endpoint: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        by_endpoint[r["endpoint"]].append(r["response_time_ms"])

    results = []
    for ep, latencies in by_endpoint.items():
        latencies.sort()
        n = len(latencies)
        p95_idx = int(0.95 * (n - 1))
        p95 = latencies[p95_idx] if n > 0 else 0
        results.append({
            "endpoint": ep,
            "p95_ms": round(p95, 2),
            "avg_ms": round(sum(latencies) / n, 2),
            "sample_count": n,
        })

    results.sort(key=lambda x: x["p95_ms"], reverse=True)
    return {"data": results[:limit]}


@router.get("/retention", dependencies=[Depends(_require_admin)])
def analytics_retention():
    """Active keys in 24h/7d/30d vs total registered."""
    conn = get_db()

    total_keys = conn.execute("SELECT COUNT(*) FROM api_keys WHERE active = 1").fetchone()[0]

    active_24h = conn.execute(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log WHERE ts >= datetime('now', '-24 hours') AND key_hash IS NOT NULL"
    ).fetchone()[0]
    active_7d = conn.execute(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log WHERE ts >= datetime('now', '-7 days') AND key_hash IS NOT NULL"
    ).fetchone()[0]
    active_30d = conn.execute(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log WHERE ts >= datetime('now', '-30 days') AND key_hash IS NOT NULL"
    ).fetchone()[0]

    def rate(active, total):
        return round(active / total * 100, 2) if total > 0 else 0.0

    return {
        "data": {
            "total_registered_keys": total_keys,
            "active_24h": active_24h,
            "active_7d": active_7d,
            "active_30d": active_30d,
            "retention_24h_pct": rate(active_24h, total_keys),
            "retention_7d_pct": rate(active_7d, total_keys),
            "retention_30d_pct": rate(active_30d, total_keys),
        }
    }
