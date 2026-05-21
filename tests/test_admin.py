"""Tests for admin dashboard, analytics, and metrics endpoints."""

import pytest
from pydantic import SecretStr


@pytest.fixture
def admin_client(mock_rpc):
    from bitcoin_api.main import app
    from bitcoin_api.dependencies import get_rpc
    from bitcoin_api.config import settings

    original = settings.admin_api_key
    settings.admin_api_key = SecretStr("test-admin-secret")
    app.dependency_overrides[get_rpc] = lambda: mock_rpc
    from fastapi.testclient import TestClient
    with TestClient(app, headers={"X-Admin-Key": "test-admin-secret"}) as c:
        yield c
    settings.admin_api_key = original
    app.dependency_overrides.clear()


# --- Analytics Access Control ---


def test_analytics_overview_requires_admin_key(client):
    """Analytics endpoints should return 403 without admin key."""
    resp = client.get("/api/v1/analytics/overview")
    assert resp.status_code == 403


def test_analytics_overview_rejects_wrong_key(client):
    """Analytics endpoints should reject an invalid admin key."""
    resp = client.get("/api/v1/analytics/overview", headers={"X-Admin-Key": "wrong"})
    assert resp.status_code == 403


# --- Analytics Endpoints ---


def test_analytics_overview_with_admin_key(admin_client):
    """Analytics overview should return 200 with valid admin key."""
    resp = admin_client.get("/api/v1/analytics/overview")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "requests_24h" in data
    assert "unique_keys_24h" in data
    assert "error_rate_24h" in data
    assert "avg_latency_ms_24h" in data


def test_analytics_requests_with_admin_key(admin_client):
    """Analytics requests should return time-series data."""
    resp = admin_client.get("/api/v1/analytics/requests?period=24h&interval=1h")
    assert resp.status_code == 200
    assert "data" in resp.json()
    assert isinstance(resp.json()["data"], list)


def test_analytics_endpoints_with_admin_key(admin_client):
    """Analytics endpoints should return top endpoints."""
    resp = admin_client.get("/api/v1/analytics/endpoints?period=24h&limit=10")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_analytics_errors_with_admin_key(admin_client):
    """Analytics errors should return error breakdown by status and type."""
    resp = admin_client.get("/api/v1/analytics/errors?period=24h")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, dict)
    assert isinstance(data["by_status"], list)
    assert isinstance(data["by_type"], list)


def test_analytics_user_agents_with_admin_key(admin_client):
    """Analytics user-agents should return top user agents."""
    resp = admin_client.get("/api/v1/analytics/user-agents?period=24h")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_analytics_latency_with_admin_key(admin_client):
    """Analytics latency should return percentiles."""
    resp = admin_client.get("/api/v1/analytics/latency?period=24h")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "p50" in data
    assert "p95" in data
    assert "p99" in data
    assert "count" in data


def test_analytics_keys_with_admin_key(admin_client):
    """Analytics keys should return per-key usage data."""
    resp = admin_client.get("/api/v1/analytics/keys?period=24h")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_analytics_keys_requires_admin(client):
    """Analytics keys should return 403 without admin key."""
    resp = client.get("/api/v1/analytics/keys")
    assert resp.status_code == 403


def test_analytics_growth_with_admin_key(admin_client):
    """Analytics growth should return DoD and WoW metrics."""
    resp = admin_client.get("/api/v1/analytics/growth")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "requests_today" in data
    assert "requests_wow_pct" in data
    assert "keys_today" in data


def test_analytics_slow_endpoints_with_admin_key(admin_client):
    """Analytics slow-endpoints should return p95 latency data."""
    resp = admin_client.get("/api/v1/analytics/slow-endpoints?period=24h&limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_analytics_retention_with_admin_key(admin_client):
    """Analytics retention should return active key counts."""
    resp = admin_client.get("/api/v1/analytics/retention")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "total_registered_keys" in data
    assert "active_24h" in data
    assert "retention_7d_pct" in data


def test_analytics_client_types_with_admin_key(admin_client):
    """Analytics client-types should return 200 with breakdown data."""
    resp = admin_client.get("/api/v1/analytics/client-types?period=7d")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "total" in data
    assert "breakdown" in data
    assert isinstance(data["breakdown"], list)


def test_analytics_client_types_requires_admin(client):
    """Analytics client-types should return 403 without admin key."""
    resp = client.get("/api/v1/analytics/client-types")
    assert resp.status_code == 403


def test_analytics_mcp_funnel_with_admin_key(admin_client):
    """Analytics mcp-funnel should return 200 with funnel data."""
    resp = admin_client.get("/api/v1/analytics/mcp-funnel?period=7d")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "total_requests" in data
    assert "unique_api_keys" in data
    assert "top_endpoints" in data
    assert isinstance(data["top_endpoints"], list)


def test_analytics_mcp_funnel_requires_admin(client):
    """Analytics mcp-funnel should return 403 without admin key."""
    resp = client.get("/api/v1/analytics/mcp-funnel")
    assert resp.status_code == 403


def test_analytics_referrers_with_admin_key(admin_client):
    """Analytics referrers should return 200 with list of referrers."""
    resp = admin_client.get("/api/v1/analytics/referrers?period=7d")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)


def test_analytics_referrers_requires_admin(client):
    """Analytics referrers should return 403 without admin key."""
    resp = client.get("/api/v1/analytics/referrers")
    assert resp.status_code == 403


def test_analytics_funnel_with_admin_key(admin_client):
    """Analytics funnel should return 200 with funnel data."""
    resp = admin_client.get("/api/v1/analytics/funnel?period=7d")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "registered" in data
    assert "made_api_call" in data
    assert "activation_rate_pct" in data
    assert "engaged_10plus_calls" in data
    assert "top_sources" in data
    assert isinstance(data["top_sources"], list)


def test_analytics_funnel_requires_admin(client):
    """Analytics funnel should return 403 without admin key."""
    resp = client.get("/api/v1/analytics/funnel")
    assert resp.status_code == 403


def test_analytics_founder_with_admin_key(admin_client):
    """Founder analytics should return curated growth and traffic quality data."""
    resp = admin_client.get("/api/v1/analytics/founder?period=7d")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "summary" in data
    assert "funnel" in data
    assert "growth" in data
    assert "top_real_endpoints" in data
    assert "likely_testers" in data
    assert "recent_signups" in data
    assert "recent_real_signups" in data
    assert "recent_real_users" in data
    assert "top_signup_sources" in data
    assert "top_external_referrers" in data
    assert "top_signup_landing_pages" in data
    assert "top_signup_campaigns" in data
    assert "notes" in data
    if data["recent_signups"]:
        signup = data["recent_signups"][0]
        assert "source_guess" in signup
        assert "first_landing_path" in signup
        assert "is_likely_test" in signup
        assert "test_reason" in signup


def test_analytics_founder_requires_admin(client):
    """Founder analytics should return 403 without admin key."""
    resp = client.get("/api/v1/analytics/founder")
    assert resp.status_code == 403


def test_analytics_endpoint_backlog_requires_admin(client):
    """Endpoint backlog analytics should be admin-only."""
    resp = client.get("/api/v1/analytics/endpoint-backlog")
    assert resp.status_code == 403


def test_analytics_endpoint_backlog_rejects_wrong_key(client):
    """Endpoint backlog analytics should reject invalid admin keys."""
    resp = client.get("/api/v1/analytics/endpoint-backlog", headers={"X-Admin-Key": "wrong"})
    assert resp.status_code == 403


def test_analytics_endpoint_backlog_returns_aggregate_safe_candidates(admin_client):
    """Endpoint backlog should rank aggregate demand without exposing raw actors."""
    from bitcoin_api.db import get_db

    db = get_db()
    raw_address = "bc1q" + "a" * 38
    raw_endpoint = f"/api/v1/address/{raw_address}/balance?debug=true"
    key_hash = "".join(["sensitive-key", "-hash-should-not-leak"])
    raw_ip = "redacted-client-ip"
    raw_user_agent = "redacted-sensitive-user-agent"
    raw_referrer = "redacted-referrer-session"
    raw_payment_id = "payment-id-should-not-leak"
    raw_pay_to = "0x" + "b" * 40

    db.executemany(
        "INSERT INTO usage_log "
        "(key_hash, endpoint, status, method, response_time_ms, user_agent, client_type, referrer, client_ip, error_type, ts) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '-1 hour'))",
        [
            (key_hash, raw_endpoint, 404, "GET", 121.5, raw_user_agent, "ai-agent", raw_referrer, raw_ip, "not_found"),
            (None, raw_endpoint, 402, "GET", 98.0, raw_user_agent, "bitcoin-mcp", raw_referrer, raw_ip, "payment_required"),
        ],
    )
    db.executemany(
        "INSERT INTO x402_payments "
        "(endpoint, price_usd, payment_status, pay_to, client_ip_hash, payment_id, user_agent, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', '-1 hour'))",
        [
            (raw_endpoint, "$0.05", "challenged", raw_pay_to, "hashed-client-ip", raw_payment_id, raw_user_agent),
            (raw_endpoint, "$0.05", "paid", raw_pay_to, "hashed-client-ip", raw_payment_id, raw_user_agent),
            (raw_endpoint, "$0.05", "failed", raw_pay_to, "hashed-client-ip", raw_payment_id, raw_user_agent),
        ],
    )
    db.commit()

    resp = admin_client.get("/api/v1/analytics/endpoint-backlog?period=7d&limit=5")
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["period"] == "7d"
    assert "summary" in data
    assert "candidates" in data
    assert data["summary"]["total_candidates"] >= 1

    candidate = data["candidates"][0]
    assert candidate["endpoint_pattern"] == "/api/v1/address/{address}/balance"
    assert candidate["request_count"] == 2
    assert candidate["x402_challenges"] == 1
    assert candidate["x402_paid"] == 1
    assert candidate["x402_failed"] == 1
    assert candidate["estimated_revenue_usd"] == 0.05
    assert candidate["agent_request_count"] == 2
    assert candidate["anonymous_request_count"] == 1
    assert isinstance(candidate["leverage_score"], (int, float))
    assert candidate["leverage_score"] > 0

    serialized = resp.text
    forbidden_values = [
        raw_address,
        key_hash,
        raw_ip,
        raw_user_agent,
        raw_referrer,
        raw_payment_id,
        raw_pay_to,
        "hashed-client-ip",
    ]
    for value in forbidden_values:
        assert value not in serialized

    forbidden_fields = [
        "client_ip",
        "client_ip_hash",
        "user_agent",
        "referrer",
        "payment_id",
        "pay_to",
        "key_hash",
        "raw_rows",
    ]
    for field in forbidden_fields:
        assert field not in serialized


def test_analytics_endpoint_backlog_ranks_conversion_and_exposes_safe_funnel(admin_client):
    """Endpoint backlog should prioritize proven paid demand and expose aggregate funnel hooks."""
    from bitcoin_api.db import get_db

    db = get_db()
    fee_endpoint = "/api/v1/fees/landscape"
    high_challenge_endpoint = "/api/v1/ai/explain/transaction/" + "c" * 64
    sensitive_user_agent = "redacted-sensitive-user-agent"
    sensitive_referrer = "redacted-private-referrer-session"
    sensitive_ip = "redacted-sensitive-client-ip"
    sensitive_payment_id = "payment-proof-should-not-leak"
    sensitive_pay_to = "0x" + "d" * 40
    repeat_actor_hash = "repeat-client-ip-hash-should-not-leak"

    usage_rows = []
    usage_rows.extend(
        (None, "/api/v1/x402-info", 200, "GET", 20.0, sensitive_user_agent, "ai-agent", sensitive_referrer, sensitive_ip, None)
        for _ in range(12)
    )
    usage_rows.extend(
        (None, fee_endpoint, 402, "GET", 45.0, sensitive_user_agent, "ai-agent", sensitive_referrer, sensitive_ip, "payment_required")
        for _ in range(4)
    )
    usage_rows.extend(
        (None, high_challenge_endpoint, 402, "GET", 55.0, sensitive_user_agent, "ai-agent", sensitive_referrer, sensitive_ip, "payment_required")
        for _ in range(40)
    )
    db.executemany(
        "INSERT INTO usage_log "
        "(key_hash, endpoint, status, method, response_time_ms, user_agent, client_type, referrer, client_ip, error_type, ts) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '-10 minutes'))",
        usage_rows,
    )

    payment_rows = []
    payment_rows.extend(
        (fee_endpoint, "$0.005", "challenged", sensitive_pay_to, repeat_actor_hash, sensitive_payment_id, sensitive_user_agent)
        for _ in range(3)
    )
    payment_rows.extend(
        (fee_endpoint, "$0.005", "paid", sensitive_pay_to, repeat_actor_hash, sensitive_payment_id, sensitive_user_agent)
        for _ in range(2)
    )
    payment_rows.append((fee_endpoint, "$0.005", "failed", sensitive_pay_to, repeat_actor_hash, sensitive_payment_id, sensitive_user_agent))
    payment_rows.extend(
        (high_challenge_endpoint, "$0.01", "challenged", sensitive_pay_to, "other-hash-should-not-leak", sensitive_payment_id, sensitive_user_agent)
        for _ in range(40)
    )
    payment_rows.extend(
        (high_challenge_endpoint, "$0.01", "failed", sensitive_pay_to, "other-hash-should-not-leak", sensitive_payment_id, sensitive_user_agent)
        for _ in range(8)
    )
    db.executemany(
        "INSERT INTO x402_payments "
        "(endpoint, price_usd, payment_status, pay_to, client_ip_hash, payment_id, user_agent, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', '-10 minutes'))",
        payment_rows,
    )
    db.commit()

    resp = admin_client.get("/api/v1/analytics/endpoint-backlog?period=24h&limit=10")
    assert resp.status_code == 200
    data = resp.json()["data"]

    candidates = {candidate["endpoint_pattern"]: candidate for candidate in data["candidates"]}
    fee = candidates["/api/v1/fees/landscape"]
    high_challenge = candidates["/api/v1/ai/explain/transaction/{txid}"]

    assert fee["priority_score"] > high_challenge["priority_score"]
    assert [candidate["endpoint_pattern"] for candidate in data["candidates"]].index("/api/v1/fees/landscape") < [
        candidate["endpoint_pattern"] for candidate in data["candidates"]
    ].index("/api/v1/ai/explain/transaction/{txid}")
    assert fee["stage_counts"] == {
        "discovery": 0,
        "challenge": 3,
        "failure": 1,
        "paid": 2,
        "repeat": 1,
    }
    assert fee["conversion_rate_pct"] == 66.67
    assert fee["failure_rate_pct"] == 25.0
    assert "paid_x402_calls" in fee["evidence"]
    assert "repeat_paid_use" in fee["evidence"]

    funnel = data["summary"]["funnel"]
    assert funnel["discovery_requests"] == 12
    assert funnel["challenge_requests"] == 43
    assert funnel["payment_failures"] == 9
    assert funnel["paid_calls"] == 2
    assert funnel["repeat_paid_actors"] == 1

    serialized = resp.text
    for sensitive in [
        sensitive_user_agent,
        sensitive_referrer,
        sensitive_ip,
        sensitive_payment_id,
        sensitive_pay_to,
        repeat_actor_hash,
        "other-hash-should-not-leak",
    ]:
        assert sensitive not in serialized


# --- Admin Dashboard ---


def test_admin_dashboard_requires_key(client):
    """Admin dashboard should return 403 without key."""
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 403


def test_admin_dashboard_rejects_wrong_key(client):
    """Admin dashboard should reject invalid key."""
    resp = client.get("/admin/dashboard?key=wrong")
    assert resp.status_code == 403


def test_admin_dashboard_with_valid_key(admin_client):
    """Admin dashboard should return HTML with valid key."""
    from bitcoin_api.config import settings
    resp = admin_client.get(f"/admin/dashboard?key={settings.admin_api_key.get_secret_value()}")
    assert resp.status_code == 200
    assert "Admin Dashboard" in resp.text


def test_founder_dashboard_requires_key(client):
    """Founder dashboard should return 403 without key."""
    resp = client.get("/admin/founder")
    assert resp.status_code == 403


def test_founder_dashboard_with_valid_key(admin_client):
    """Founder dashboard should return HTML with valid key."""
    from bitcoin_api.config import settings
    resp = admin_client.get(f"/admin/founder?key={settings.admin_api_key.get_secret_value()}")
    assert resp.status_code == 200
    assert "Founder Analytics" in resp.text
    assert "Campaign Links" in resp.text
    assert "Real Candidate Signups" in resp.text
    assert "Traffic Origins" in resp.text


def test_admin_dashboard_missing_file_returns_404(client, monkeypatch):
    """Admin dashboard should return 404 HTML when static file is missing."""
    from pathlib import Path
    from bitcoin_api.config import settings
    from pydantic import SecretStr
    from bitcoin_api import static_routes

    original_key = settings.admin_api_key
    settings.admin_api_key = SecretStr("test-admin-secret")
    real_path = static_routes._STATIC_DIR / "admin-dashboard.html"
    monkeypatch.setattr(static_routes, "_STATIC_DIR",
                        Path("nonexistent-dir-that-does-not-exist"))
    try:
        resp = client.get("/admin/dashboard?key=test-admin-secret")
        assert resp.status_code == 404
        assert resp.headers["content-type"].startswith("text/html")
    finally:
        settings.admin_api_key = original_key
        monkeypatch.setattr(static_routes, "_STATIC_DIR", real_path.parent)


def test_founder_dashboard_missing_file_returns_404(client, monkeypatch):
    """Founder dashboard should return 404 HTML when static file is missing."""
    from pathlib import Path
    from bitcoin_api.config import settings
    from pydantic import SecretStr
    from bitcoin_api import static_routes

    original_key = settings.admin_api_key
    settings.admin_api_key = SecretStr("test-admin-secret")
    real_path = static_routes._STATIC_DIR / "founder-dashboard.html"
    monkeypatch.setattr(static_routes, "_STATIC_DIR",
                        Path("nonexistent-dir-that-does-not-exist"))
    try:
        resp = client.get("/admin/founder?key=test-admin-secret")
        assert resp.status_code == 404
        assert resp.headers["content-type"].startswith("text/html")
    finally:
        settings.admin_api_key = original_key
        monkeypatch.setattr(static_routes, "_STATIC_DIR", real_path.parent)


# --- Prometheus /metrics ---


def test_metrics_endpoint_returns_prometheus_format(client):
    """GET /metrics should return Prometheus text exposition format."""
    from bitcoin_api.config import settings
    original = settings.admin_api_key
    settings.admin_api_key = SecretStr("test-admin-secret")
    try:
        resp = client.get("/metrics", headers={"X-Admin-Key": "test-admin-secret"})
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")
        text = resp.text
        assert "http_requests_total" in text or "http_request_duration_seconds" in text or "bitcoin_block_height" in text
    finally:
        settings.admin_api_key = original


def test_metrics_is_rate_limited(client):
    """Metrics endpoint should be rate limited (security: prevent admin key brute-force)."""
    from bitcoin_api.config import settings
    original = settings.admin_api_key
    settings.admin_api_key = SecretStr("test-admin-secret")
    try:
        got_429 = False
        for _ in range(35):
            resp = client.get("/metrics", headers={"X-Admin-Key": "test-admin-secret"})
            if resp.status_code == 429:
                got_429 = True
                break
        assert got_429, "Metrics endpoint should be rate limited"
    finally:
        settings.admin_api_key = original


def test_metrics_request_count_increments(client):
    """After hitting an endpoint, http_requests_total should increment."""
    from bitcoin_api.config import settings
    original = settings.admin_api_key
    settings.admin_api_key = SecretStr("test-admin-secret")
    try:
        client.get("/api/v1/fees")
        resp = client.get("/metrics", headers={"X-Admin-Key": "test-admin-secret"})
        text = resp.text
        assert "http_requests_total" in text
    finally:
        settings.admin_api_key = original


def test_metrics_latency_histogram_present(client):
    """Latency histogram should be present after requests."""
    from bitcoin_api.config import settings
    original = settings.admin_api_key
    settings.admin_api_key = SecretStr("test-admin-secret")
    try:
        client.get("/api/v1/fees")
        resp = client.get("/metrics", headers={"X-Admin-Key": "test-admin-secret"})
        text = resp.text
        assert "http_request_duration_seconds" in text
    finally:
        settings.admin_api_key = original


def test_metrics_block_height_gauge(client):
    """bitcoin_block_height gauge should be present."""
    from bitcoin_api.config import settings
    original = settings.admin_api_key
    settings.admin_api_key = SecretStr("test-admin-secret")
    try:
        resp = client.get("/metrics", headers={"X-Admin-Key": "test-admin-secret"})
        assert "bitcoin_block_height" in resp.text
    finally:
        settings.admin_api_key = original


def test_metrics_job_errors_counter(client):
    """background_job_errors_total counter should be present."""
    from bitcoin_api.config import settings
    original = settings.admin_api_key
    settings.admin_api_key = SecretStr("test-admin-secret")
    try:
        resp = client.get("/metrics", headers={"X-Admin-Key": "test-admin-secret"})
        assert "background_job_errors_total" in resp.text
    finally:
        settings.admin_api_key = original
