"""Tests for health, root, status, and process-alive endpoints."""

from pathlib import Path
from unittest.mock import patch, MagicMock

from bitcoin_api import static_routes
from bitcoin_api.config import settings


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Satoshi API" in resp.text


def test_root_returns_404_when_landing_page_is_missing(client, monkeypatch):
    monkeypatch.setattr(static_routes, "_LANDING_PAGE", Path("missing-index.html"))
    resp = client.get("/")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("text/html")
    assert "Page Not Found" in resp.text


def test_health_returns_envelope(client):
    """Health endpoint should return standard envelope format."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    assert body["data"]["status"] == "ok"
    assert body["data"]["chain"] == "main"
    assert body["data"]["blocks"] == 880000
    assert body["meta"]["node_height"] == 880000


def test_status(client, mock_rpc):
    with patch("bitcoin_api.routers.status.cached_status") as mock_cached:
        mock_status = MagicMock()
        mock_status.model_dump.return_value = {
            "chain": "main",
            "blocks": 880000,
            "headers": 880000,
            "verification_progress": 0.9999,
            "size_on_disk": 650000000000,
            "pruned": False,
            "connections": 125,
            "version": 270000,
            "subversion": "/Satoshi:27.0.0/",
            "network_name": "mainnet",
        }
        mock_cached.return_value = mock_status

        resp = client.get("/api/v1/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert body["meta"]["node_height"] == 880000


def test_health_no_rate_limit(client):
    """Health endpoint should never return 429."""
    for _ in range(50):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
    # No rate limit headers on health (it's skipped)
    assert "X-RateLimit-Limit" not in resp.headers


def test_docs_accessible(client):
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_api_docs_redirects_to_live_docs(client):
    resp = client.get("/api-docs", follow_redirects=False)
    assert resp.status_code == 308
    assert resp.headers["location"] == "/docs"


def test_well_known_llms_txt_redirects_to_llms_txt(client):
    resp = client.get("/.well-known/llms.txt", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["location"] == "/llms.txt"


def test_envelope_format(client):
    with patch("bitcoin_api.routers.status.cached_status") as mock_cached:
        mock_status = MagicMock()
        mock_status.model_dump.return_value = {"chain": "main", "blocks": 880000}
        mock_cached.return_value = mock_status

        resp = client.get("/api/v1/status")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "timestamp" in body["meta"]


def test_version_in_root(client):
    """Root endpoint should show product name."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Satoshi" in resp.text


def test_healthz_no_rpc(client):
    """Process-alive healthcheck should work without RPC."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_history_nav_hidden_when_history_explorer_disabled(client):
    original = settings.enable_history_explorer
    try:
        settings.enable_history_explorer = False
        resp = client.get("/")
    finally:
        settings.enable_history_explorer = original

    assert resp.status_code == 200
    assert 'href="/history"' not in resp.text


def test_root_csp_allows_configured_analytics_scripts(client):
    resp = client.get("/")
    assert resp.status_code == 200
    csp = resp.headers["content-security-policy"]
    assert "https://us.i.posthog.com" in csp


def test_health_deep(authed_client):
    """GET /health/deep should return health check data for authenticated users."""
    with (
        patch(
            "bitcoin_api.routers.health_deep.get_job_health",
            return_value={"fee_collector": "ok"},
        ),
        patch("bitcoin_api.routers.health_deep.usage_buffer") as mock_buf,
    ):
        mock_buf.pending_count = 0
        resp = authed_client.get("/api/v1/health/deep")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    data = body["data"]
    assert data["rpc"]["ok"] is True
    assert data["rpc"]["height"] == 880000
    assert data["db"]["ok"] is True
    assert "sync_progress" in data
    assert "uptime_seconds" in data


def test_health_deep_requires_auth(client):
    """GET /health/deep should reject anonymous users with 403."""
    resp = client.get("/api/v1/health/deep")
    assert resp.status_code == 403


def test_visualizer_page(client):
    """Visualizer page returns HTML."""
    resp = client.get("/visualizer")
    assert resp.status_code == 200
    assert "ECharts" in resp.text or "echarts" in resp.text
