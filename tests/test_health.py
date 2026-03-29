"""Tests for health, root, status, and process-alive endpoints."""

from pathlib import Path
from unittest.mock import patch, MagicMock

from bitcoin_api import static_routes
from bitcoin_api.config import settings


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Satoshi API" in resp.text
    assert 'href="/fees"' in resp.text


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


def test_fee_observatory_redirects_to_fees(client):
    resp = client.get("/fee-observatory", follow_redirects=False)
    assert resp.status_code == 308
    assert resp.headers["location"] == "/fees"


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
    assert "https://static.cloudflareinsights.com" in csp
    assert "'nonce-" in csp
    assert 'nonce="' in resp.text


def test_core_marketing_pages_load_shared_site_helper(client):
    for path in ["/", "/guide", "/pricing", "/mcp-setup", "/vs-mempool", "/history"]:
        resp = client.get(path)
        assert resp.status_code == 200
        assert '/static/js/site-helpers.js' in resp.text


def test_shared_site_helper_asset_is_served(client):
    resp = client.get("/static/js/site-helpers.js")
    assert resp.status_code == 200
    assert "processTree(document);" in resp.text


def test_key_agent_pages_drop_google_font_chain(client):
    for path in ["/", "/fees", "/mcp-setup", "/bitcoin-api-for-ai-agents"]:
        resp = client.get(path)
        assert resp.status_code == 200
        assert "fonts.googleapis.com" not in resp.text
        assert "fonts.gstatic.com" not in resp.text


def test_root_register_form_no_longer_relies_on_inline_submit_handler(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'onsubmit=' not in resp.text


def test_docs_surface_is_noindex(client):
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert resp.headers["X-Robots-Tag"] == "noindex, follow"


def test_visualizer_page_is_noindex(client):
    resp = client.get("/visualizer")
    assert resp.status_code == 200
    assert resp.headers["X-Robots-Tag"] == "noindex, follow"


def test_x402_page_is_indexable(client):
    resp = client.get("/x402")
    assert resp.status_code == 200
    assert "X-Robots-Tag" not in resp.headers


def test_ai_playground_is_noindex(client):
    resp = client.get("/ai")
    assert resp.status_code == 200
    assert resp.headers["X-Robots-Tag"] == "noindex, follow"


def test_history_index_has_canonical(client):
    resp = client.get("/history")
    assert resp.status_code == 200
    assert '<link rel="canonical" href="https://bitcoinsapi.com/history">' in resp.text


def test_history_detail_pages_are_noindex(client):
    for path in ["/history/block", "/history/tx", "/history/address"]:
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.headers["X-Robots-Tag"] == "noindex, follow"


def test_robots_txt_explicitly_allows_major_ai_crawlers(client):
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    body = resp.text
    assert "GPTBot" in body
    assert "ChatGPT-User" in body
    assert "OAI-SearchBot" in body
    assert "ClaudeBot" in body
    assert "anthropic-ai" in body


def test_public_discovery_and_web_paths_do_not_emit_rate_limit_headers(client):
    for path in ["/fees", "/mcp-setup", "/x402", "/llms.txt", "/llms-full.txt", "/.well-known/mcp/server-card.json"]:
        resp = client.get(path)
        assert resp.status_code == 200
        assert "X-RateLimit-Limit" not in resp.headers


def test_llms_docs_explain_keyed_and_premium_access(client):
    llms = client.get("/llms.txt")
    assert llms.status_code == 200
    assert "Best starting points" in llms.text
    assert "https://bitcoinsapi.com/best-time-to-send-bitcoin" in llms.text
    assert "API-Key Endpoints" in llms.text
    assert "Paid Endpoints (x402 or Pro/Enterprise tier)" in llms.text
    assert "/api/v1/mining/pools - Mining pool distribution" in llms.text
    assert "/api/v1/rpc - Hosted Bitcoin Core JSON-RPC proxy" in llms.text
    assert "Direct access requires a free API key." in llms.text
    assert "No API key required." not in llms.text

    llms_full = client.get("/llms-full.txt")
    assert llms_full.status_code == 200
    assert "/mining/pools | Mining pool distribution (API key required)" in llms_full.text
    assert "/stats/utxo-set | UTXO set statistics (API key required)" in llms_full.text
    assert "Direct access to `/api/v1/rpc` requires an API key." in llms_full.text
    assert "An API key is not required but recommended for higher limits." not in llms_full.text


def test_mcp_server_card_description_matches_fee_intelligence_positioning(client):
    resp = client.get("/.well-known/mcp/server-card.json")
    assert resp.status_code == 200
    body = resp.json()
    description = body["serverInfo"]["description"].lower()
    assert "fee-intelligence" in description
    assert "x402" in description


def test_best_time_to_send_page_is_positioned_as_send_or_wait_wedge(client):
    resp = client.get("/best-time-to-send-bitcoin")
    assert resp.status_code == 200
    assert "Should You Send Bitcoin" in resp.text
    assert "See Live Verdict" in resp.text
    assert "5,000 requests/day anonymously" in resp.text


def test_root_supports_head(client):
    resp = client.head("/")
    assert resp.status_code == 200


def test_api_docs_supports_head_redirect(client):
    resp = client.head("/api-docs", follow_redirects=False)
    assert resp.status_code == 308
    assert resp.headers["location"] == "/docs"


def test_mcp_server_card_supports_head(client):
    resp = client.head("/.well-known/mcp/server-card.json")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")


def test_health_deep(authed_client):
    """GET /health/deep should return health check data for authenticated users."""
    with patch("bitcoin_api.routers.health_deep.get_job_health", return_value={"fee_collector": "ok"}), \
         patch("bitcoin_api.routers.health_deep.usage_buffer") as mock_buf:
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
