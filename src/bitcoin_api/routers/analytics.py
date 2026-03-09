"""Admin analytics endpoints for API usage monitoring."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..services.analytics import (
    interval_secs,
    period_sql,
    query_column,
    query_rows,
    query_scalar,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _require_admin(request: Request):
    import secrets
    from ..config import settings
    if not settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Analytics not configured")
    key = request.headers.get("X-Admin-Key", "")
    if not secrets.compare_digest(key, settings.admin_api_key.get_secret_value()):
        raise HTTPException(status_code=403, detail="Invalid admin key")


@router.get("/public")
def analytics_public():
    """Public stats for social proof on the landing page. No auth required."""
    total_keys = query_scalar("SELECT COUNT(*) FROM api_keys WHERE active = 1")
    total_requests = query_scalar("SELECT COUNT(*) FROM usage_log")

    min_ts = query_scalar("SELECT MIN(ts) FROM usage_log")
    if min_ts:
        import datetime
        first_ts = datetime.datetime.fromisoformat(min_ts)
        now = datetime.datetime.now(datetime.timezone.utc)
        if first_ts.tzinfo is None:
            first_ts = first_ts.replace(tzinfo=datetime.timezone.utc)
        uptime_days = max(1, (now - first_ts).days)
    else:
        uptime_days = 0

    return {
        "data": {
            "total_keys": total_keys,
            "total_requests": total_requests,
            "uptime_days": uptime_days,
        }
    }


@router.get("/overview", dependencies=[Depends(_require_admin)])
def analytics_overview():
    result = {}
    for label, offset in [("24h", "-24 hours"), ("7d", "-7 days"), ("30d", "-30 days")]:
        result[f"requests_{label}"] = query_scalar(
            "SELECT COUNT(*) FROM usage_log WHERE ts >= datetime('now', ?)", (offset,)
        )

    result["unique_keys_24h"] = query_scalar(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log WHERE ts >= datetime('now', '-24 hours')"
    )

    total = result["requests_24h"]
    if total > 0:
        errors = query_scalar(
            "SELECT COUNT(*) FROM usage_log WHERE ts >= datetime('now', '-24 hours') AND status >= 400"
        )
        result["error_rate_24h"] = round(errors / total, 4)
    else:
        result["error_rate_24h"] = 0.0

    avg_latency = query_scalar(
        "SELECT AVG(response_time_ms) FROM usage_log "
        "WHERE ts >= datetime('now', '-24 hours') AND response_time_ms IS NOT NULL"
    )
    result["avg_latency_ms_24h"] = round(avg_latency, 2) if avg_latency else None

    return {"data": result}


@router.get("/requests", dependencies=[Depends(_require_admin)])
def analytics_requests(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
    interval: str = Query("1h", pattern="^(1m|5m|15m|1h|6h|1d)$"),
):
    offset = period_sql(period)
    isecs = interval_secs(interval)

    rows = query_rows(
        "SELECT (CAST(strftime('%s', ts) AS INTEGER) / ?) * ? as epoch, COUNT(*) as cnt "
        "FROM usage_log WHERE ts >= datetime('now', ?) "
        "GROUP BY CAST(strftime('%s', ts) AS INTEGER) / ? "
        "ORDER BY epoch",
        (isecs, isecs, offset, isecs),
    )

    return {"data": [{"timestamp": int(r["epoch"]), "count": r["cnt"]} for r in rows]}


@router.get("/endpoints", dependencies=[Depends(_require_admin)])
def analytics_endpoints(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
    limit: int = Query(20, ge=1, le=100),
):
    offset = period_sql(period)

    rows = query_rows(
        "SELECT endpoint, COUNT(*) as hits, AVG(response_time_ms) as avg_ms "
        "FROM usage_log WHERE ts >= datetime('now', ?) "
        "GROUP BY endpoint ORDER BY hits DESC LIMIT ?",
        (offset, limit),
    )

    return {
        "data": [
            {
                "endpoint": r["endpoint"],
                "hits": r["hits"],
                "avg_latency_ms": round(r["avg_ms"], 2) if r["avg_ms"] else None,
            }
            for r in rows
        ]
    }


@router.get("/errors", dependencies=[Depends(_require_admin)])
def analytics_errors(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
):
    offset = period_sql(period)

    rows = query_rows(
        "SELECT status, COUNT(*) as cnt "
        "FROM usage_log WHERE ts >= datetime('now', ?) AND status >= 400 "
        "GROUP BY status ORDER BY cnt DESC",
        (offset,),
    )

    type_rows = query_rows(
        "SELECT error_type, COUNT(*) as cnt "
        "FROM usage_log WHERE ts >= datetime('now', ?) AND status >= 400 AND error_type != '' "
        "GROUP BY error_type ORDER BY cnt DESC",
        (offset,),
    )

    return {
        "data": {
            "by_status": [{"status": r["status"], "count": r["cnt"]} for r in rows],
            "by_type": [{"error_type": r["error_type"], "count": r["cnt"]} for r in type_rows],
        }
    }


@router.get("/user-agents", dependencies=[Depends(_require_admin)])
def analytics_user_agents(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
    limit: int = Query(20, ge=1, le=100),
):
    offset = period_sql(period)

    rows = query_rows(
        "SELECT user_agent, COUNT(*) as cnt "
        "FROM usage_log WHERE ts >= datetime('now', ?) "
        "AND user_agent IS NOT NULL AND user_agent != '' "
        "GROUP BY user_agent ORDER BY cnt DESC LIMIT ?",
        (offset, limit),
    )

    return {"data": [{"user_agent": r["user_agent"], "count": r["cnt"]} for r in rows]}


@router.get("/latency", dependencies=[Depends(_require_admin)])
def analytics_latency(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
):
    offset = period_sql(period)

    values = query_column(
        "SELECT response_time_ms FROM usage_log "
        "WHERE ts >= datetime('now', ?) AND response_time_ms IS NOT NULL "
        "ORDER BY response_time_ms",
        (offset,),
    )

    if not values:
        return {"data": {"p50": None, "p95": None, "p99": None, "count": 0}}

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
    offset = period_sql(period)

    rows = query_rows(
        "SELECT u.key_hash, k.prefix, COUNT(*) as hits, "
        "AVG(u.response_time_ms) as avg_ms, "
        "SUM(CASE WHEN u.status >= 400 THEN 1 ELSE 0 END) as errors, "
        "MAX(u.ts) as last_seen "
        "FROM usage_log u LEFT JOIN api_keys k ON u.key_hash = k.key_hash "
        "WHERE u.ts >= datetime('now', ?) "
        "GROUP BY u.key_hash ORDER BY hits DESC LIMIT ?",
        (offset, limit),
    )

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
def analytics_growth(
    client_type: str | None = Query(None, description="Filter by client type (e.g. bitcoin-mcp, ai-agent, sdk, browser, unknown)"),
):
    """Day-over-day and week-over-week request & key growth."""
    client_filter = ""
    client_params: tuple = ()
    if client_type:
        client_filter = " AND client_type = ?"
        client_params = (client_type,)

    today = query_scalar(
        f"SELECT COUNT(*) FROM usage_log WHERE ts >= datetime('now', '-24 hours'){client_filter}",
        client_params,
    )
    yesterday = query_scalar(
        "SELECT COUNT(*) FROM usage_log "
        f"WHERE ts >= datetime('now', '-48 hours') AND ts < datetime('now', '-24 hours'){client_filter}",
        client_params,
    )

    this_week = query_scalar(
        f"SELECT COUNT(*) FROM usage_log WHERE ts >= datetime('now', '-7 days'){client_filter}",
        client_params,
    )
    last_week = query_scalar(
        "SELECT COUNT(*) FROM usage_log "
        f"WHERE ts >= datetime('now', '-14 days') AND ts < datetime('now', '-7 days'){client_filter}",
        client_params,
    )

    keys_today = query_scalar(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log "
        f"WHERE ts >= datetime('now', '-24 hours'){client_filter}",
        client_params,
    )
    keys_yesterday = query_scalar(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log "
        f"WHERE ts >= datetime('now', '-48 hours') AND ts < datetime('now', '-24 hours'){client_filter}",
        client_params,
    )

    def pct_change(current, previous):
        if previous == 0:
            return None
        return round((current - previous) / previous * 100, 2)

    return {
        "data": {
            "client_type": client_type,
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
    offset = period_sql(period)

    rows = query_rows(
        "SELECT endpoint, response_time_ms FROM usage_log "
        "WHERE ts >= datetime('now', ?) AND response_time_ms IS NOT NULL LIMIT 100000",
        (offset,),
    )

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


@router.get("/client-types", dependencies=[Depends(_require_admin)])
def analytics_client_types(
    period: str = Query("7d", pattern="^(1h|6h|24h|7d|30d)$"),
):
    """Breakdown of requests by client_type over a configurable period."""
    offset = period_sql(period)

    rows = query_rows(
        "SELECT client_type, COUNT(*) as cnt "
        "FROM usage_log WHERE ts >= datetime('now', ?) "
        "GROUP BY client_type ORDER BY cnt DESC",
        (offset,),
    )

    total = sum(r["cnt"] for r in rows)
    return {
        "data": {
            "total": total,
            "breakdown": [
                {
                    "client_type": r["client_type"] or "unknown",
                    "count": r["cnt"],
                    "pct": round(r["cnt"] / total * 100, 2) if total > 0 else 0.0,
                }
                for r in rows
            ],
        }
    }


@router.get("/mcp-funnel", dependencies=[Depends(_require_admin)])
def analytics_mcp_funnel(
    period: str = Query("7d", pattern="^(1h|6h|24h|7d|30d)$"),
):
    """MCP-specific metrics: total requests, unique keys, top endpoints."""
    offset = period_sql(period)

    total = query_scalar(
        "SELECT COUNT(*) FROM usage_log "
        "WHERE ts >= datetime('now', ?) AND client_type = 'bitcoin-mcp'",
        (offset,),
    )

    unique_keys = query_scalar(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log "
        "WHERE ts >= datetime('now', ?) AND client_type = 'bitcoin-mcp' AND key_hash IS NOT NULL",
        (offset,),
    )

    top_endpoints = query_rows(
        "SELECT endpoint, COUNT(*) as hits "
        "FROM usage_log WHERE ts >= datetime('now', ?) AND client_type = 'bitcoin-mcp' "
        "GROUP BY endpoint ORDER BY hits DESC LIMIT 10",
        (offset,),
    )

    return {
        "data": {
            "total_requests": total,
            "unique_api_keys": unique_keys,
            "top_endpoints": [
                {"endpoint": r["endpoint"], "hits": r["hits"]}
                for r in top_endpoints
            ],
        }
    }


@router.get("/retention", dependencies=[Depends(_require_admin)])
def analytics_retention(
    client_type: str | None = Query(None, description="Filter by client type (e.g. bitcoin-mcp, ai-agent, sdk, browser, unknown)"),
):
    """Active keys in 24h/7d/30d vs total registered."""
    total_keys = query_scalar("SELECT COUNT(*) FROM api_keys WHERE active = 1")

    client_filter = ""
    client_params: tuple = ()
    if client_type:
        client_filter = " AND client_type = ?"
        client_params = (client_type,)

    active_24h = query_scalar(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log "
        f"WHERE ts >= datetime('now', '-24 hours') AND key_hash IS NOT NULL{client_filter}",
        client_params,
    )
    active_7d = query_scalar(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log "
        f"WHERE ts >= datetime('now', '-7 days') AND key_hash IS NOT NULL{client_filter}",
        client_params,
    )
    active_30d = query_scalar(
        "SELECT COUNT(DISTINCT key_hash) FROM usage_log "
        f"WHERE ts >= datetime('now', '-30 days') AND key_hash IS NOT NULL{client_filter}",
        client_params,
    )

    def rate(active, total):
        return round(active / total * 100, 2) if total > 0 else 0.0

    return {
        "data": {
            "total_registered_keys": total_keys,
            "client_type": client_type,
            "active_24h": active_24h,
            "active_7d": active_7d,
            "active_30d": active_30d,
            "retention_24h_pct": rate(active_24h, total_keys),
            "retention_7d_pct": rate(active_7d, total_keys),
            "retention_30d_pct": rate(active_30d, total_keys),
        }
    }


@router.get("/referrers", dependencies=[Depends(_require_admin)])
def analytics_referrers(
    period: str = Query("7d", pattern="^(1h|6h|24h|7d|30d)$"),
    limit: int = Query(20, ge=1, le=100),
):
    """Top traffic referrers by request count."""
    offset = period_sql(period)

    rows = query_rows(
        "SELECT referrer, COUNT(*) as cnt, COUNT(DISTINCT key_hash) as unique_keys "
        "FROM usage_log WHERE ts >= datetime('now', ?) "
        "AND referrer IS NOT NULL AND referrer != '' "
        "GROUP BY referrer ORDER BY cnt DESC LIMIT ?",
        (offset, limit),
    )

    return {
        "data": [
            {
                "referrer": r["referrer"],
                "hits": r["cnt"],
                "unique_keys": r["unique_keys"],
            }
            for r in rows
        ]
    }


@router.get("/funnel", dependencies=[Depends(_require_admin)])
def analytics_funnel(
    period: str = Query("7d", pattern="^(1h|6h|24h|7d|30d)$"),
    client_type: str | None = Query(None, description="Filter by client type (e.g. bitcoin-mcp, ai-agent, sdk, browser, unknown)"),
):
    """Registration-to-usage conversion funnel."""
    offset = period_sql(period)

    client_filter = ""
    client_params: tuple = ()
    if client_type:
        client_filter = " AND u.client_type = ?"
        client_params = (client_type,)

    # Total registrations in period
    total_registered = query_scalar(
        "SELECT COUNT(*) FROM api_keys WHERE created_at >= datetime('now', ?)",
        (offset,),
    )

    # Of those, how many made at least one API call?
    active_new_keys = query_scalar(
        "SELECT COUNT(DISTINCT k.key_hash) FROM api_keys k "
        "INNER JOIN usage_log u ON k.key_hash = u.key_hash "
        f"WHERE k.created_at >= datetime('now', ?){client_filter}",
        (offset,) + client_params,
    )

    # Of those, how many made 10+ calls (engaged)?
    engaged_keys = query_scalar(
        "SELECT COUNT(*) FROM ("
        "  SELECT u.key_hash, COUNT(*) as calls FROM api_keys k "
        "  INNER JOIN usage_log u ON k.key_hash = u.key_hash "
        f"  WHERE k.created_at >= datetime('now', ?){client_filter} "
        "  GROUP BY u.key_hash HAVING calls >= 10"
        ")",
        (offset,) + client_params,
    )

    # Registration sources (utm_source breakdown)
    sources = query_rows(
        "SELECT utm_source, COUNT(*) as cnt FROM api_keys "
        "WHERE created_at >= datetime('now', ?) AND utm_source != '' "
        "GROUP BY utm_source ORDER BY cnt DESC LIMIT 10",
        (offset,),
    )

    def rate(part, whole):
        return round(part / whole * 100, 2) if whole > 0 else 0.0

    return {
        "data": {
            "period": period,
            "client_type": client_type,
            "registered": total_registered,
            "made_api_call": active_new_keys,
            "activation_rate_pct": rate(active_new_keys, total_registered),
            "engaged_10plus_calls": engaged_keys,
            "engagement_rate_pct": rate(engaged_keys, total_registered),
            "top_sources": [
                {"source": r["utm_source"], "count": r["cnt"]}
                for r in sources
            ],
        }
    }


@router.get("/users", dependencies=[Depends(_require_admin)])
def analytics_users(
    active_only: bool = Query(False),
):
    """List all registered API key users."""
    sql = (
        "SELECT prefix, tier, label, email, created_at, active, email_opt_out "
        "FROM api_keys"
    )

    if active_only:
        sql += " WHERE active = 1"

    sql += " ORDER BY created_at DESC"

    rows = query_rows(sql)

    return {
        "data": [
            {
                "prefix": r["prefix"],
                "tier": r["tier"],
                "label": r["label"],
                "email": r["email"],
                "created_at": r["created_at"],
                "active": bool(r["active"]),
                "email_opt_out": bool(r["email_opt_out"]),
            }
            for r in rows
        ]
    }
