"""HTTP middleware: security headers, CORS setup, auth + rate limiting."""

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
from .exceptions import ERROR_TYPES, _GUIDE_URL, _guide_help_url
from .models import ErrorResponse, ErrorDetail
from .rate_limit import check_rate_limit, check_daily_limit

access_log = logging.getLogger("bitcoin_api.access")
log = logging.getLogger("bitcoin_api")

_DOCS_PATHS = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json", "/admin/dashboard"}

_RATE_LIMIT_SKIP = {
    "/", "/docs", "/redoc", "/openapi.json", "/api/v1/health", "/api/v1/guide", "/healthz",
    "/api/v1/stream/blocks", "/api/v1/stream/fees",
    "/robots.txt", "/sitemap.xml", "/favicon.ico",
    "/vs-mempool", "/vs-blockcypher", "/best-bitcoin-api-for-developers",
    "/bitcoin-api-for-ai-agents", "/self-hosted-bitcoin-api",
    "/bitcoin-fee-api", "/bitcoin-mempool-api", "/bitcoin-mcp-setup-guide",
    "/terms", "/privacy",
    "/api/v1/analytics/overview", "/api/v1/analytics/requests",
    "/api/v1/analytics/endpoints", "/api/v1/analytics/errors",
    "/api/v1/analytics/user-agents", "/api/v1/analytics/latency",
    "/api/v1/analytics/keys", "/api/v1/analytics/growth",
    "/api/v1/analytics/slow-endpoints", "/api/v1/analytics/retention",
    "/admin/dashboard",
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

        if request.url.path in _RATE_LIMIT_SKIP:
            response = await call_next(request)
            elapsed_ms = (time.monotonic() - start_time) * 1000
            response.headers["X-Request-ID"] = request_id
            if request.url.path == "/api/v1/health":
                key_info = authenticate(request)
                log_usage(key_info.key_hash, request.url.path, response.status_code,
                          method=req_method, response_time_ms=elapsed_ms, user_agent=req_user_agent)
            return response

        key_info = authenticate(request)
        request.state.tier = key_info.tier

        if key_info.tier == "invalid":
            resp = JSONResponse(
                status_code=401,
                content=ErrorResponse(
                    error=ErrorDetail(
                        type=ERROR_TYPES["unauthorized"],
                        status=401,
                        title="Unauthorized",
                        detail="API key not found or inactive. Get a free key: POST /api/v1/register",
                        request_id=request_id,
                        help_url=_GUIDE_URL,
                    )
                ).model_dump(),
            )
            resp.headers["X-Request-ID"] = request_id
            return resp

        bucket = key_info.key_hash or request.client.host if request.client else "unknown"

        result = check_rate_limit(bucket, key_info.tier)
        if not result.allowed:
            retry_after = max(1, int(result.reset - time.time()))
            detail_msg = f"Limit: {result.limit} req/min for {key_info.tier} tier"
            if key_info.tier == "anonymous":
                detail_msg += ". Upgrade: POST /api/v1/register"
            resp = JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    error=ErrorDetail(
                        type=ERROR_TYPES["rate_limit"],
                        status=429,
                        title="Rate Limit Exceeded",
                        detail=detail_msg,
                        request_id=request_id,
                        help_url=_GUIDE_URL,
                    )
                ).model_dump(),
            )
            resp.headers["X-Request-ID"] = request_id
            resp.headers["X-RateLimit-Limit"] = str(result.limit)
            resp.headers["X-RateLimit-Remaining"] = "0"
            resp.headers["X-RateLimit-Reset"] = str(int(result.reset))
            resp.headers["Retry-After"] = str(retry_after)
            elapsed_ms = (time.monotonic() - start_time) * 1000
            log_usage(bucket, request.url.path, 429,
                      method=req_method, response_time_ms=elapsed_ms, user_agent=req_user_agent)
            return resp

        daily_result = check_daily_limit(bucket, key_info.tier)
        if not daily_result.allowed:
            daily_detail = f"Daily limit: {daily_result.limit} requests for {key_info.tier} tier"
            if key_info.tier == "anonymous":
                daily_detail += ". Upgrade: POST /api/v1/register"
            resp = JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    error=ErrorDetail(
                        type=ERROR_TYPES["rate_limit"],
                        status=429,
                        title="Daily Rate Limit Exceeded",
                        detail=daily_detail,
                        request_id=request_id,
                        help_url=_GUIDE_URL,
                    )
                ).model_dump(),
            )
            resp.headers["X-Request-ID"] = request_id
            resp.headers["X-RateLimit-Daily-Limit"] = str(daily_result.limit)
            resp.headers["X-RateLimit-Daily-Remaining"] = "0"
            resp.headers["Retry-After"] = "3600"
            elapsed_ms = (time.monotonic() - start_time) * 1000
            log_usage(bucket, request.url.path, 429,
                      method=req_method, response_time_ms=elapsed_ms, user_agent=req_user_agent)
            return resp

        # Circuit breaker: fast-fail for RPC-dependent endpoints
        path = request.url.path
        _is_rpc_path = (
            path.startswith("/api/v1/")
            and not path.startswith("/api/v1/health")
            and not path.startswith("/api/v1/keys")
            and not path.startswith("/api/v1/register")
            and not path.startswith("/api/v1/analytics")
            and not path.startswith("/api/v1/guide")
        )
        if _is_rpc_path:
            try:
                rpc_breaker.before_call()
            except CircuitOpenError:
                remaining = rpc_breaker._recovery_timeout - (time.time() - rpc_breaker._last_failure_time)
                retry_after = str(max(1, int(remaining)))
                resp = JSONResponse(
                    status_code=503,
                    content=ErrorResponse(
                        error=ErrorDetail(
                            type=ERROR_TYPES["circuit_open"],
                            status=503,
                            title="Service Unavailable",
                            detail="Circuit breaker OPEN -- Bitcoin node unavailable. Fast-failing to avoid delays.",
                            request_id=request_id,
                        )
                    ).model_dump(),
                )
                resp.headers["X-Request-ID"] = request_id
                resp.headers["Retry-After"] = retry_after
                elapsed_ms = (time.monotonic() - start_time) * 1000
                log_usage(bucket, request.url.path, 503,
                          method=req_method, response_time_ms=elapsed_ms, user_agent=req_user_agent)
                return resp

        try:
            response = await call_next(request)
        except Exception:
            logging.getLogger("bitcoin_api").exception(
                "Unhandled exception: %s %s [%s]", request.method, request.url.path, request_id
            )
            resp = JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error=ErrorDetail(
                        type=ERROR_TYPES["internal"],
                        status=500,
                        title="Internal Server Error",
                        detail="An unexpected error occurred",
                        request_id=request_id,
                    )
                ).model_dump(),
            )
            resp.headers["X-Request-ID"] = request_id
            elapsed_ms = (time.monotonic() - start_time) * 1000
            log_usage(bucket, request.url.path, 500,
                      method=req_method, response_time_ms=elapsed_ms, user_agent=req_user_agent)
            return resp

        # Circuit breaker: record success for RPC paths with 2xx responses
        if _is_rpc_path and 200 <= response.status_code < 300:
            rpc_breaker.record_success()

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

        elapsed_ms = (time.monotonic() - start_time) * 1000
        log_usage(bucket, request.url.path, response.status_code,
                  method=req_method, response_time_ms=elapsed_ms, user_agent=req_user_agent)

        client_ip = request.client.host if request.client else "unknown"
        tier = key_info.tier
        log_level = logging.WARNING if response.status_code in (401, 429) else logging.INFO
        if settings.log_format == "json":
            import json
            access_log.log(log_level, json.dumps({
                "client_ip": client_ip,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "tier": tier,
                "request_id": request_id,
                "latency_ms": round(elapsed_ms, 1),
            }))
        else:
            access_log.log(log_level, "%s %s %s %d %s %s", client_ip, request.method, request.url.path, response.status_code, tier, request_id)

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
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https://raw.githubusercontent.com; "
                "connect-src 'self' https://bitcoinsapi.com; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
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
