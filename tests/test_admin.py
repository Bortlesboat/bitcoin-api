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


def test_metrics_no_rate_limit(client):
    """Metrics endpoint should not be rate limited."""
    from bitcoin_api.config import settings
    original = settings.admin_api_key
    settings.admin_api_key = SecretStr("test-admin-secret")
    try:
        for _ in range(35):
            resp = client.get("/metrics", headers={"X-Admin-Key": "test-admin-secret"})
            assert resp.status_code == 200
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
