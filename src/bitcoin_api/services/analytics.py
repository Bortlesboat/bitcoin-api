"""Analytics query helpers — shared logic for the analytics router."""

from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import urlsplit

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


_BTC_ADDRESS_RE = re.compile(r"^(bc1|tb1|[13])[A-Za-z0-9]{20,90}$")
_HEX_64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_HEX_ADDRESS_RE = re.compile(r"^(0x)?[0-9a-fA-F]{40}$")
_OPAQUE_ID_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_-]{24,}$")


def _endpoint_pattern(endpoint: str | None) -> str:
    """Return an aggregate-safe endpoint pattern with query strings and IDs removed."""
    if not endpoint:
        return "unknown"

    value = endpoint.strip()
    if value.startswith(("http://", "https://")):
        path = urlsplit(value).path
    else:
        path = value.split("?", 1)[0]

    if not path:
        return "/"
    if not path.startswith("/"):
        path = f"/{path}"

    parts = []
    previous = ""
    for part in path.split("/"):
        if not part:
            continue
        lowered = part.lower()
        if _BTC_ADDRESS_RE.match(part) or _HEX_ADDRESS_RE.match(part):
            parts.append("{address}")
        elif _HEX_64_RE.match(part):
            parts.append("{txid}")
        elif part.isdigit():
            parts.append("{height}" if previous in {"block", "blocks", "height"} else "{id}")
        elif _OPAQUE_ID_RE.match(part):
            parts.append("{id}")
        else:
            parts.append(part)
        previous = lowered

    return "/" + "/".join(parts)


def _money_to_float(value: str | int | float | None) -> float:
    """Parse stored x402 price strings such as '$0.05' without exposing raw rows."""
    if value is None:
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    cleaned = "".join(ch for ch in str(value) if ch.isdigit() or ch == "." or ch == "-")
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def build_endpoint_backlog(period: str = "7d", limit: int = 10) -> dict:
    """Build aggregate, privacy-safe endpoint demand candidates."""
    offset = period_sql(period)
    limit = max(1, min(limit, 50))

    candidates = defaultdict(lambda: {
        "endpoint_pattern": "unknown",
        "request_count": 0,
        "agent_request_count": 0,
        "anonymous_request_count": 0,
        "http_402_count": 0,
        "http_404_count": 0,
        "x402_challenges": 0,
        "x402_paid": 0,
        "x402_failed": 0,
        "repeat_paid_actors": 0,
        "estimated_revenue_usd": 0.0,
    })
    discovery_patterns = {
        "/x402/start",
        "/x402/analytics",
        "/api/v1/x402-info",
        "/api/v1/x402-demo",
        "/api/v1/x402-stats",
        "/.well-known/x402",
        "/openapi.json",
        "/llms.txt",
    }
    discovery_requests = 0

    usage_rows = query_rows(
        "SELECT endpoint, status, method, client_type, COUNT(*) AS cnt, "
        "SUM(CASE WHEN key_hash IS NULL OR key_hash = '' THEN 1 ELSE 0 END) AS anonymous_cnt "
        "FROM usage_log WHERE ts >= datetime('now', ?) "
        "GROUP BY endpoint, status, method, client_type",
        (offset,),
    )
    for row in usage_rows:
        pattern = _endpoint_pattern(row.get("endpoint"))
        count = int(row.get("cnt") or 0)
        if pattern in discovery_patterns:
            discovery_requests += count
        candidate = candidates[pattern]
        candidate["endpoint_pattern"] = pattern
        candidate["request_count"] += count
        candidate["anonymous_request_count"] += int(row.get("anonymous_cnt") or 0)
        client_type = (row.get("client_type") or "").lower()
        if "agent" in client_type or "mcp" in client_type:
            candidate["agent_request_count"] += count
        status = int(row.get("status") or 0)
        if status == 402:
            candidate["http_402_count"] += count
        elif status == 404:
            candidate["http_404_count"] += count

    payment_rows = query_rows(
        "SELECT endpoint, payment_status, price_usd, COUNT(*) AS cnt "
        "FROM x402_payments WHERE timestamp >= datetime('now', ?) "
        "GROUP BY endpoint, payment_status, price_usd",
        (offset,),
    )
    for row in payment_rows:
        pattern = _endpoint_pattern(row.get("endpoint"))
        candidate = candidates[pattern]
        candidate["endpoint_pattern"] = pattern
        count = int(row.get("cnt") or 0)
        status = (row.get("payment_status") or "").lower()
        if status in {"challenged", "challenge", "payment_required"}:
            candidate["x402_challenges"] += count
        elif status in {"paid", "settled", "success"}:
            candidate["x402_paid"] += count
            candidate["estimated_revenue_usd"] += _money_to_float(row.get("price_usd")) * count
        elif status in {"failed", "failure", "error", "settlement_failed", "invalid"}:
            candidate["x402_failed"] += count

    repeat_actor_rows = query_rows(
        "SELECT endpoint, client_ip_hash, COUNT(*) AS cnt "
        "FROM x402_payments WHERE timestamp >= datetime('now', ?) "
        "AND LOWER(COALESCE(payment_status, '')) IN ('paid', 'settled', 'success') "
        "AND client_ip_hash IS NOT NULL AND client_ip_hash != '' "
        "GROUP BY endpoint, client_ip_hash HAVING COUNT(*) > 1",
        (offset,),
    )
    for row in repeat_actor_rows:
        pattern = _endpoint_pattern(row.get("endpoint"))
        candidate = candidates[pattern]
        candidate["endpoint_pattern"] = pattern
        repeat_paid_actors = int(candidate["repeat_paid_actors"] or 0)
        candidate["repeat_paid_actors"] = repeat_paid_actors + 1

    rows = []
    for candidate in candidates.values():
        challenges = candidate["x402_challenges"]
        paid = candidate["x402_paid"]
        failed = candidate["x402_failed"]
        request_count = candidate["request_count"]
        conversion_rate = round((paid / challenges) * 100, 2) if challenges else 0.0
        failure_rate = round((failed / (challenges + failed)) * 100, 2) if challenges or failed else 0.0
        leverage_score = round(
            request_count
            + candidate["agent_request_count"] * 2
            + candidate["http_402_count"] * 3
            + candidate["http_404_count"] * 1.5
            + challenges * 4
            + paid * 10
            + failed * 3
            + candidate["estimated_revenue_usd"] * 100,
            2,
        )

        repeat_paid_actors = int(candidate["repeat_paid_actors"] or 0)
        stage_counts = {
            "discovery": request_count if candidate["endpoint_pattern"] in discovery_patterns else 0,
            "challenge": challenges,
            "failure": failed,
            "paid": paid,
            "repeat": repeat_paid_actors,
        }
        priority_score = round(
            paid * 100
            + repeat_paid_actors * 75
            + conversion_rate * 2
            + candidate["estimated_revenue_usd"] * 1000
            + challenges
            + candidate["agent_request_count"]
            - failed * 2,
            2,
        )

        if paid:
            action = "improve_repeat_use"
        elif challenges or candidate["http_402_count"]:
            action = "reduce_payment_friction"
        elif candidate["http_404_count"]:
            action = "evaluate_missing_endpoint"
        else:
            action = "monitor"

        evidence = []
        if candidate["agent_request_count"]:
            evidence.append("agent_or_mcp_requests")
        if challenges:
            evidence.append("x402_challenges")
        if paid:
            evidence.append("paid_x402_calls")
        if repeat_paid_actors:
            evidence.append("repeat_paid_use")
        if failed:
            evidence.append("payment_failures")
        if candidate["http_404_count"]:
            evidence.append("not_found_requests")

        estimated_revenue = round(float(candidate["estimated_revenue_usd"] or 0.0), 4)

        rows.append({
            **candidate,
            "estimated_revenue_usd": estimated_revenue,
            "stage_counts": stage_counts,
            "conversion_rate_pct": conversion_rate,
            "failure_rate_pct": failure_rate,
            "leverage_score": leverage_score,
            "priority_score": priority_score,
            "recommended_action": action,
            "evidence": evidence,
        })

    rows.sort(key=lambda item: (item["priority_score"], item["leverage_score"], item["estimated_revenue_usd"], item["request_count"]), reverse=True)
    rows = rows[:limit]

    return {
        "period": period,
        "summary": {
            "total_candidates": len(rows),
            "total_requests": sum(row["request_count"] for row in rows),
            "total_x402_challenges": sum(row["x402_challenges"] for row in rows),
            "total_x402_paid": sum(row["x402_paid"] for row in rows),
            "total_x402_failed": sum(row["x402_failed"] for row in rows),
            "estimated_revenue_usd": round(sum(row["estimated_revenue_usd"] for row in rows), 4),
            "funnel": {
                "discovery_requests": discovery_requests,
                "challenge_requests": sum(row["stage_counts"]["challenge"] for row in rows),
                "payment_failures": sum(row["stage_counts"]["failure"] for row in rows),
                "paid_calls": sum(row["stage_counts"]["paid"] for row in rows),
                "repeat_paid_actors": sum(row["stage_counts"]["repeat"] for row in rows),
            },
        },
        "candidates": rows,
    }
