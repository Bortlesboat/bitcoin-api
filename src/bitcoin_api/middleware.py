"""HTTP middleware: security headers, CORS setup, auth + rate limiting."""

import json
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .auth import authenticate
from .cache import get_cache_state, get_sync_progress
from .circuit_breaker import CircuitOpenError, rpc_breaker
from .config import settings
from .db import log_usage
from .exceptions import ERROR_TYPES, _GUIDE_URL
from .models import ErrorResponse, ErrorDetail
from .metrics import REQUEST_COUNT, REQUEST_LATENCY, normalize_endpoint
from .rate_limit import check_rate_limit, check_rate_limit_raw, check_daily_limit

access_log = logging.getLogger("bitcoin_api.access")
log = logging.getLogger("bitcoin_api")


# ---------------------------------------------------------------------------
# Helper functions (extracted from auth_and_rate_limit)
# ---------------------------------------------------------------------------

def _get_client_ip(request: Request) -> str:
    """Extract the real client IP, preferring Cloudflare's header."""
    return (request.headers.get("CF-Connecting-IP")
            or (request.client.host if request.client else "unknown"))


def _error_response(status: int, title: str, detail: str, request_id: str,
                    *, error_type_key: str,
                    extra_headers: dict | None = None,
                    retry_after_seconds: int | None = None) -> JSONResponse:
    """Build a standardised JSON error response with X-Request-ID."""
    resp = JSONResponse(
        status_code=status,
        content=ErrorResponse(
            error=ErrorDetail(
                type=ERROR_TYPES[error_type_key],
                status=status,
                title=title,
                detail=detail,
                request_id=request_id,
                help_url=_GUIDE_URL,
                retry_after_seconds=retry_after_seconds,
            )
        ).model_dump(),
    )
    resp.headers["X-Request-ID"] = request_id
    if extra_headers:
        for k, v in extra_headers.items():
            resp.headers[k] = v
    return resp


def _log_and_respond(bucket, path: str, status: int, *, request_id: str,
                     start_time: float, method: str, user_agent: str,
                     client_type: str, referrer: str,
                     response: JSONResponse,
                     record_metrics: bool = True,
                     tier: str = "unknown",
                     client_ip: str = "",
                     error_type: str = "") -> JSONResponse:
    """Calculate elapsed time, log usage, optionally record Prometheus metrics, return response."""
    elapsed_ms = (time.monotonic() - start_time) * 1000
    log_usage(bucket, path, status,
              method=method, response_time_ms=elapsed_ms, user_agent=user_agent,
              client_type=client_type, referrer=referrer,
              client_ip=client_ip, error_type=error_type)
    if record_metrics:
        _norm = normalize_endpoint(path)
        REQUEST_COUNT.labels(
            method=method, endpoint=_norm, status=str(status), tier=tier,
        ).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=_norm).observe(elapsed_ms / 1000)
    return response


def _emit_access_log(client_ip: str, method: str, path: str, status: int,
                     tier: str, request_id: str, elapsed_ms: float) -> None:
    """Write a structured or plain-text access log entry."""
    log_level = logging.WARNING if status in (401, 429) else logging.INFO
    if settings.log_format == "json":
        access_log.log(log_level, json.dumps({
            "client_ip": client_ip, "method": method, "path": path,
            "status": status, "tier": tier,
            "request_id": request_id, "latency_ms": round(elapsed_ms, 1),
        }))
    else:
        access_log.log(log_level, "%s %s %s %d %s %s",
                       client_ip, method, path, status, tier, request_id)


# ---------------------------------------------------------------------------
# Client classification
# ---------------------------------------------------------------------------

_AI_AGENT_PATTERNS = ("claude", "openai", "anthropic", "langchain", "autogpt")
_SDK_PATTERNS = ("python-requests", "httpx", "axios", "node-fetch", "curl")
_BROWSER_PATTERNS = ("mozilla", "chrome", "safari", "firefox")


def classify_client(user_agent: str) -> str:
    """Classify a request's client type from its User-Agent header."""
    ua = user_agent.lower()
    if "bitcoin-mcp" in ua:
        return "bitcoin-mcp"
    if any(p in ua for p in _AI_AGENT_PATTERNS):
        return "ai-agent"
    if any(p in ua for p in _SDK_PATTERNS):
        return "sdk"
    if any(p in ua for p in _BROWSER_PATTERNS):
        return "browser"
    return "unknown"

_DOCS_PATHS = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json", "/admin/dashboard", "/admin/founder", "/visualizer"}

_PAGEVIEW_LOG_PATHS = {
    "/", "/docs", "/redoc", "/admin/dashboard", "/admin/founder",
    "/vs-mempool", "/vs-blockcypher", "/best-bitcoin-api-for-developers",
    "/bitcoin-api-for-ai-agents", "/self-hosted-bitcoin-api",
    "/bitcoin-fee-api", "/bitcoin-mempool-api", "/bitcoin-mcp-setup-guide",
    "/terms", "/privacy", "/disclaimer", "/about", "/pricing", "/mcp-setup", "/guide",
}

_RATE_LIMIT_SKIP = {
    "/", "/docs", "/redoc", "/openapi.json", "/api/v1/health", "/api/v1/guide", "/healthz",
    "/api/v1/stream/blocks", "/api/v1/stream/fees",
    "/robots.txt", "/sitemap.xml", "/favicon.ico",
    "/vs-mempool", "/vs-blockcypher", "/best-bitcoin-api-for-developers",
    "/bitcoin-api-for-ai-agents", "/self-hosted-bitcoin-api",
    "/bitcoin-fee-api", "/bitcoin-mempool-api", "/bitcoin-mcp-setup-guide",
    "/terms", "/privacy", "/disclaimer", "/about", "/pricing",
    "/admin/dashboard", "/admin/founder",
    "/metrics",
    "/api/v1/ws",
    "/api/v1/billing/webhook",
}


def register_middleware(app: FastAPI):
    """Register all middleware in correct order (last registered runs first)."""

    # --- Auth + rate limiting (outermost — runs first) ---
    @app.middleware("http")
    async def auth_and_rate_limit(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.monotonic()
        req_method = request.method
        req_user_agent = request.headers.get("user-agent", "")
        req_client_type = classify_client(req_user_agent)
        req_referrer = request.headers.get("referer", "")
        _common = dict(request_id=request_id, start_time=start_time, method=req_method,
                       user_agent=req_user_agent, client_type=req_client_type, referrer=req_referrer)

        # --- MCP path: basic IP rate limit only (no auth/daily/circuit breaker) ---
        if request.url.path.startswith("/mcp"):
            client_ip = _get_client_ip(request)
            mcp_result = check_rate_limit_raw(f"mcp:{client_ip}", 60)
            if not mcp_result.allowed:
                retry_after = max(1, int(mcp_result.reset - time.time()))
                return _error_response(
                    429, "Rate Limit Exceeded",
                    f"MCP rate limit: {mcp_result.limit} req/min per IP",
                    request_id, error_type_key="rate_limit",
                    retry_after_seconds=retry_after,
                    extra_headers={
                        "X-RateLimit-Limit": str(mcp_result.limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(mcp_result.reset)),
                        "Retry-After": str(retry_after),
                    })
            response = await call_next(request)
            # Log MCP usage and record Prometheus metrics
            mcp_path = request.url.path
            elapsed_ms = (time.monotonic() - start_time) * 1000
            log_usage(f"mcp:{client_ip}", mcp_path, response.status_code,
                      method=req_method, response_time_ms=elapsed_ms,
                      user_agent=req_user_agent, client_type=req_client_type,
                      referrer=req_referrer, client_ip=client_ip, error_type="")
            _norm = normalize_endpoint(mcp_path)
            REQUEST_COUNT.labels(method=req_method, endpoint=_norm,
                                 status=str(response.status_code), tier="mcp").inc()
            REQUEST_LATENCY.labels(method=req_method, endpoint=_norm).observe(elapsed_ms / 1000)
            _emit_access_log(client_ip, req_method, mcp_path, response.status_code,
                             "mcp", request_id, elapsed_ms)
            return response
        if request.url.path in _RATE_LIMIT_SKIP:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            if request.url.path == "/api/v1/health":
                key_info = authenticate(request)
                _log_and_respond(key_info.key_hash, request.url.path, response.status_code,
                                 response=response, record_metrics=False, **_common)
            elif request.url.path in _PAGEVIEW_LOG_PATHS:
                client_ip = _get_client_ip(request)
                _log_and_respond(client_ip, request.url.path, response.status_code,
                                 response=response, record_metrics=False, tier="unknown",
                                 client_ip=client_ip, error_type="", **_common)
            # Record skipped-path metrics for Prometheus visibility
            _norm = normalize_endpoint(request.url.path)
            elapsed_ms = (time.monotonic() - start_time) * 1000
            REQUEST_COUNT.labels(method=req_method, endpoint=_norm,
                                 status=str(response.status_code), tier="unknown").inc()
            REQUEST_LATENCY.labels(method=req_method, endpoint=_norm).observe(elapsed_ms / 1000)
            return response

        # --- Authentication ---
        key_info = authenticate(request)
        request.state.tier = key_info.tier

        if key_info.tier == "invalid":
            resp = _error_response(401, "Unauthorized",
                                   "API key not found or inactive. Get a free key: POST /api/v1/register",
                                   request_id, error_type_key="unauthorized")
            _norm = normalize_endpoint(request.url.path)
            REQUEST_COUNT.labels(method=req_method, endpoint=_norm, status="401", tier="invalid").inc()
            REQUEST_LATENCY.labels(method=req_method, endpoint=_norm).observe(time.monotonic() - start_time)
            return resp

        client_ip = _get_client_ip(request)
        bucket = key_info.key_hash or client_ip

        # --- Per-minute rate limit ---
        result = check_rate_limit(bucket, key_info.tier)
        if not result.allowed:
            retry_after = max(1, int(result.reset - time.time()))
            detail_msg = f"Limit: {result.limit} req/min for {key_info.tier} tier"
            if key_info.tier == "anonymous":
                detail_msg += ". Upgrade: POST /api/v1/register"
            resp = _error_response(429, "Rate Limit Exceeded", detail_msg, request_id,
                                   error_type_key="rate_limit",
                                   retry_after_seconds=retry_after,
                                   extra_headers={
                                       "X-RateLimit-Limit": str(result.limit),
                                       "X-RateLimit-Remaining": "0",
                                       "X-RateLimit-Reset": str(int(result.reset)),
                                       "Retry-After": str(retry_after),
                                   })
            return _log_and_respond(bucket, request.url.path, 429,
                                    response=resp, record_metrics=False,
                                    client_ip=client_ip, error_type="rate_limited",
                                    **_common)

        # --- Broadcast-specific rate limit (tighter, applies to all tiers) ---
        BROADCAST_PATH = "/api/v1/transactions/broadcast"
        BROADCAST_LIMIT_PER_MIN = 5
        if request.url.path == BROADCAST_PATH:
            broadcast_bucket = f"broadcast:{bucket}"
            broadcast_result = check_rate_limit_raw(broadcast_bucket, BROADCAST_LIMIT_PER_MIN)
            if not broadcast_result.allowed:
                broadcast_retry = max(1, int(broadcast_result.reset - time.time()))
                resp = _error_response(
                    429, "Rate Limit Exceeded",
                    "Broadcast rate limit exceeded. Maximum 5 transactions per minute.",
                    request_id, error_type_key="rate_limit",
                    retry_after_seconds=broadcast_retry,
                    extra_headers={
                        "X-RateLimit-Limit": str(BROADCAST_LIMIT_PER_MIN),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(broadcast_result.reset)),
                        "Retry-After": str(broadcast_retry),
                    })
                return _log_and_respond(bucket, request.url.path, 429,
                                        response=resp, record_metrics=False,
                                        client_ip=client_ip, error_type="rate_limited",
                                        **_common)

        # --- Daily rate limit ---
        daily_result = check_daily_limit(bucket, key_info.tier)
        if not daily_result.allowed:
            daily_detail = f"Daily limit: {daily_result.limit} requests for {key_info.tier} tier"
            if key_info.tier == "anonymous":
                daily_detail += ". Upgrade: POST /api/v1/register"
            resp = _error_response(429, "Daily Rate Limit Exceeded", daily_detail, request_id,
                                   error_type_key="rate_limit",
                                   retry_after_seconds=3600,
                                   extra_headers={
                                       "X-RateLimit-Daily-Limit": str(daily_result.limit),
                                       "X-RateLimit-Daily-Remaining": "0",
                                       "Retry-After": "3600",
                                   })
            return _log_and_respond(bucket, request.url.path, 429,
                                    response=resp, record_metrics=False,
                                    client_ip=client_ip, error_type="rate_limited",
                                    **_common)

        # --- Circuit breaker: fast-fail for RPC-dependent endpoints ---
        path = request.url.path
        _is_rpc_path = (
            path.startswith("/api/v1/")
            and not path.startswith("/api/v1/health")
            and not path.startswith("/api/v1/keys")
            and not path.startswith("/api/v1/register")
            and not path.startswith("/api/v1/analytics")
            and not path.startswith("/api/v1/guide")
            and not path.startswith("/api/v1/billing")
            and not path.startswith("/api/v1/ws")
        )
        if _is_rpc_path:
            try:
                rpc_breaker.before_call()
            except CircuitOpenError:
                remaining = rpc_breaker._recovery_timeout - (time.time() - rpc_breaker._last_failure_time)
                resp = _error_response(503, "Temporarily Unavailable",
                                       "Bitcoin node data is temporarily unavailable. Please retry shortly.",
                                       request_id, error_type_key="circuit_open",
                                       extra_headers={"Retry-After": str(max(1, int(remaining)))})
                return _log_and_respond(bucket, path, 503,
                                        response=resp, record_metrics=False,
                                        client_ip=client_ip, error_type="circuit_open",
                                        **_common)

        # --- Call downstream ---
        try:
            response = await call_next(request)
        except Exception:
            log.exception("Unhandled exception: %s %s [%s]", request.method, path, request_id)
            resp = _error_response(500, "Internal Server Error", "An unexpected error occurred",
                                   request_id, error_type_key="internal")
            return _log_and_respond(bucket, path, 500,
                                    response=resp, record_metrics=False,
                                    client_ip=client_ip, error_type="server_error",
                                    **_common)

        # Circuit breaker: record success for RPC paths with 2xx responses
        if _is_rpc_path and 200 <= response.status_code < 300:
            rpc_breaker.record_success()

        # --- Prometheus metrics ---
        elapsed_s = time.monotonic() - start_time
        _endpoint = normalize_endpoint(path)
        REQUEST_COUNT.labels(method=req_method, endpoint=_endpoint,
                             status=str(response.status_code), tier=key_info.tier).inc()
        REQUEST_LATENCY.labels(method=req_method, endpoint=_endpoint).observe(elapsed_s)

        # --- Response headers ---
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Auth-Tier"] = key_info.tier

        if key_info.query_param_used:
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = "2026-09-01"
            response.headers["X-Deprecation-Notice"] = "Pass API key via X-API-Key header instead of ?api_key= query param"

        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(int(result.reset))
        response.headers["X-RateLimit-Daily-Limit"] = str(daily_result.limit)
        response.headers["X-RateLimit-Daily-Remaining"] = str(daily_result.remaining)

        # --- Log usage + access log ---
        elapsed_ms = (time.monotonic() - start_time) * 1000
        _error_type = ""
        if response.status_code >= 500:
            _error_type = "server_error"
        elif response.status_code == 404:
            _error_type = "not_found"
        elif response.status_code == 403:
            _error_type = "forbidden"
        elif response.status_code == 422:
            _error_type = "validation_error"
        elif response.status_code >= 400:
            _error_type = "client_error"
        # Append RPC method name for /api/v1/rpc requests
        _log_path = path
        if path == "/api/v1/rpc":
            _rpc_method = getattr(request.state, "rpc_method", "")
            if _rpc_method:
                _log_path = f"/api/v1/rpc:{_rpc_method}"
        log_usage(bucket, _log_path, response.status_code,
                  method=req_method, response_time_ms=elapsed_ms, user_agent=req_user_agent,
                  client_type=req_client_type, referrer=req_referrer,
                  client_ip=client_ip, error_type=_error_type)
        _emit_access_log(client_ip, request.method, _log_path, response.status_code,
                         key_info.tier, request_id, elapsed_ms)
        return response

    # --- CORS (middle layer) ---
    _cors_origins = [o.strip() for o in settings.cors_origins.split(",")]
    if "*" in _cors_origins and settings.api_host != "127.0.0.1":
        raise ValueError("CORS_ORIGINS='*' is not allowed when API_HOST is not 127.0.0.1. Refusing to start.")
    if "*" in _cors_origins:
        log.warning("CORS_ORIGINS contains '*' — all origins allowed (localhost only).")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["X-API-Key"],
    )

    # --- Response compression (runs before security headers on response) ---
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # --- Security headers (innermost — runs last) ---
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if request.url.path not in _DOCS_PATHS:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://us-assets.i.posthog.com https://us.i.posthog.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https://raw.githubusercontent.com; "
                "connect-src 'self' https://bitcoinsapi.com https://us.i.posthog.com; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        progress = get_sync_progress()
        if progress is not None and progress < 0.9999:
            response.headers["X-Node-Syncing"] = "true"

        path = request.url.path
        if path.startswith("/api/v1/"):
            response.headers["X-Data-Disclaimer"] = "For informational purposes only. Not financial advice. See /terms"
        if "Cache-Control" not in response.headers:
            if path.startswith("/api/v1/fees") or path.startswith("/api/v1/mempool") or path.startswith("/api/v1/prices"):
                response.headers["Cache-Control"] = "public, max-age=10"
            elif path.startswith("/api/v1/blocks/"):
                response.headers["Cache-Control"] = "public, max-age=3600"
            elif path in ("/api/v1/health", "/healthz"):
                response.headers["Cache-Control"] = "no-cache"
            elif path == "/api/v1/register":
                response.headers["Cache-Control"] = "no-store"

        # HTTP Age header for cached responses (RFC 7234)
        is_cached, cache_age = get_cache_state()
        if is_cached and cache_age is not None:
            response.headers["Age"] = str(cache_age)

        return response
