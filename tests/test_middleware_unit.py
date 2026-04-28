"""Unit tests for middleware — security headers, request ID, client classification, rate limit skips."""

from bitcoin_api.middleware import classify_client, _RATE_LIMIT_SKIP


class TestClassifyClient:
    def test_bitcoin_mcp_agent(self):
        assert classify_client("bitcoin-mcp/0.5.1 python-httpx/0.27") == "bitcoin-mcp"

    def test_ai_agent_claude(self):
        assert classify_client("Claude-Agent/1.0") == "ai-agent"

    def test_ai_agent_openai(self):
        assert classify_client("OpenAI-GPT/4.0") == "ai-agent"

    def test_ai_agent_anthropic(self):
        assert classify_client("Anthropic-Client/2.0") == "ai-agent"

    def test_ai_agent_langchain(self):
        assert classify_client("LangChain/0.1.0") == "ai-agent"

    def test_sdk_python_requests(self):
        assert classify_client("python-requests/2.31.0") == "sdk"

    def test_sdk_httpx(self):
        assert classify_client("httpx/0.27.0") == "sdk"

    def test_sdk_curl(self):
        assert classify_client("curl/8.4.0") == "sdk"

    def test_browser_chrome(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0"
        assert classify_client(ua) == "browser"

    def test_browser_firefox(self):
        assert classify_client("Mozilla/5.0 Firefox/123.0") == "browser"

    def test_unknown_agent(self):
        assert classify_client("MyCustomTool/1.0") == "unknown"

    def test_empty_user_agent(self):
        assert classify_client("") == "unknown"

    def test_bitcoin_mcp_takes_priority_over_sdk(self):
        # bitcoin-mcp UA includes "httpx" but should classify as bitcoin-mcp
        assert classify_client("bitcoin-mcp/0.5 python-httpx/0.27") == "bitcoin-mcp"


class TestSecurityHeaders:
    """Integration tests for security headers via the full app client."""

    def test_x_content_type_options(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client):
        resp = client.get("/api/v1/health")
        assert "camera=()" in resp.headers.get("Permissions-Policy", "")

    def test_xss_protection_removed(self, client):
        """X-XSS-Protection header should be absent (deprecated, can introduce vulnerabilities)."""
        resp = client.get("/api/v1/health")
        assert "X-XSS-Protection" not in resp.headers

    def test_csp_on_api_path(self, client):
        resp = client.get("/api/v1/health")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp

    def test_no_csp_on_docs_path(self, client):
        resp = client.get("/docs")
        # Docs paths are excluded from CSP to allow Swagger UI JS
        assert "Content-Security-Policy" not in resp.headers


class TestRequestId:
    def test_request_id_present_on_api_response(self, client):
        resp = client.get("/api/v1/mempool/info")
        assert "X-Request-ID" in resp.headers
        # UUID format check
        rid = resp.headers["X-Request-ID"]
        assert len(rid) == 36  # UUID with hyphens

    def test_request_id_on_health_endpoint(self, client):
        resp = client.get("/api/v1/health")
        assert "X-Request-ID" in resp.headers


class TestX402TierPreservation:
    def test_paid_x402_tier_survives_anonymous_auth(self):
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        from bitcoin_api.auth import require_api_key
        from bitcoin_api.middleware import register_middleware

        test_app = FastAPI()
        register_middleware(test_app)

        @test_app.get("/paid")
        def paid_endpoint(tier: str = Depends(require_api_key)):
            return {"tier": tier}

        class PrepaidScopeWrapper:
            def __init__(self, app):
                self.app = app

            async def __call__(self, scope, receive, send):
                if scope["type"] == "http":
                    scope.setdefault("state", {})
                    scope["state"]["tier"] = "pro"
                    scope["state"]["key_hash"] = "x402-paid"
                await self.app(scope, receive, send)

        with TestClient(PrepaidScopeWrapper(test_app)) as test_client:
            resp = test_client.get("/paid")

        assert resp.status_code == 200
        assert resp.json() == {"tier": "pro"}


class TestRateLimitSkipPaths:
    def test_health_is_skipped(self):
        assert "/api/v1/health" in _RATE_LIMIT_SKIP

    def test_docs_is_skipped(self):
        assert "/docs" in _RATE_LIMIT_SKIP

    def test_guide_is_skipped(self):
        assert "/api/v1/guide" in _RATE_LIMIT_SKIP

    def test_api_openapi_json_is_skipped(self):
        assert "/api/openapi.json" in _RATE_LIMIT_SKIP

    def test_robots_txt_is_skipped(self):
        assert "/robots.txt" in _RATE_LIMIT_SKIP


class TestCacheControlHeaders:
    def test_fee_endpoint_has_short_cache(self, client):
        resp = client.get("/api/v1/fees/recommended")
        cc = resp.headers.get("Cache-Control", "")
        assert "max-age=10" in cc

    def test_health_has_no_cache(self, client):
        resp = client.get("/api/v1/health")
        cc = resp.headers.get("Cache-Control", "")
        assert "no-cache" in cc
