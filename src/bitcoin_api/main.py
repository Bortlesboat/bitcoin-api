"""Bitcoin API — FastAPI application."""

import logging
import threading
import time
import uuid
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response

from bitcoinlib_rpc.rpc import RPCError

from .auth import authenticate
from .config import settings
from .db import get_db, log_usage, prune_old_logs, record_fee_snapshot, prune_fee_history
from .cache import record_mempool_snapshot, get_sync_progress
from .models import ErrorResponse, ErrorDetail
from .rate_limit import check_rate_limit, check_daily_limit
from . import __version__
from .routers import status, blocks, transactions, mempool, fees, mining, network, prices, keys, stream, exchanges, address

access_log = logging.getLogger("bitcoin_api.access")


log = logging.getLogger("bitcoin_api")

_bg_stop = threading.Event()


def _background_fee_collector():
    """Background thread: snapshot mempool every 5 min for trend analysis + fee history."""
    from .dependencies import get_rpc as _get_rpc_dep

    while not _bg_stop.is_set():
        try:
            rpc = _get_rpc_dep()
            # Record to circular buffer (for /fees/landscape trend)
            record_mempool_snapshot(rpc)

            # Record to DB (for /fees/history)
            info = rpc.call("getmempoolinfo")
            fees_1 = rpc.call("estimatesmartfee", 1)
            fees_6 = rpc.call("estimatesmartfee", 6)
            fees_144 = rpc.call("estimatesmartfee", 144)

            next_block_fee = (fees_1.get("feerate", 0) or 0) * 100_000
            median_fee = (fees_6.get("feerate", 0) or 0) * 100_000
            low_fee = (fees_144.get("feerate", 0) or 0) * 100_000
            mempool_size = info.get("size", 0)
            mempool_vsize = info.get("bytes", 0)

            # Simple congestion classification
            if mempool_vsize < 1_000_000:
                congestion = "low"
            elif mempool_vsize < 10_000_000:
                congestion = "normal"
            elif mempool_vsize < 50_000_000:
                congestion = "elevated"
            else:
                congestion = "high"

            record_fee_snapshot(
                next_block_fee=round(next_block_fee, 2),
                median_fee=round(median_fee, 2),
                low_fee=round(low_fee, 2),
                mempool_size=mempool_size,
                mempool_vsize=mempool_vsize,
                congestion=congestion,
            )
        except Exception:
            log.debug("Background fee collector: snapshot failed", exc_info=True)

        _bg_stop.wait(300)  # 5 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB + prune old logs
    get_db()
    prune_old_logs()
    prune_fee_history()
    log.info("Satoshi API starting on %s:%s", settings.api_host, settings.api_port)

    # Start background fee collector
    _bg_stop.clear()
    bg_thread = threading.Thread(target=_background_fee_collector, daemon=True, name="fee-collector")
    bg_thread.start()

    yield

    # Shutdown
    _bg_stop.set()
    bg_thread.join(timeout=5)
    log.info("Satoshi API shutting down")


app = FastAPI(
    title="Satoshi API",
    description="Developer-friendly REST API for Bitcoin node data. "
    "Powered by bitcoinlib-rpc — analyzed data, not raw RPC.",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- Security headers middleware ---
_DOCS_PATHS = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Skip CSP for docs pages — Swagger UI / ReDoc load assets from cdn.jsdelivr.net
    if request.url.path not in _DOCS_PATHS:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https://raw.githubusercontent.com; "
            "connect-src 'self' https://bitcoinsapi.com https://cloudflareinsights.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    progress = get_sync_progress()
    if progress is not None and progress < 0.9999:
        response.headers["X-Node-Syncing"] = "true"
    return response


_cors_origins = [o.strip() for o in settings.cors_origins.split(",")]
if "*" in _cors_origins:
    log.warning("CORS_ORIGINS contains '*' — all origins allowed. Not recommended for production.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key"],
)

# Paths exempt from rate limiting
_RATE_LIMIT_SKIP = {
    "/", "/docs", "/redoc", "/openapi.json", "/api/v1/health", "/healthz", "/api/v1/register",
    "/api/v1/stream/blocks", "/api/v1/stream/fees",
    "/robots.txt", "/sitemap.xml",
    "/vs-mempool", "/vs-blockcypher", "/best-bitcoin-api-for-developers",
    "/bitcoin-api-for-ai-agents", "/self-hosted-bitcoin-api",
    "/bitcoin-fee-api", "/bitcoin-mempool-api",
}


# --- Middleware: auth + rate limiting + usage logging ---

@app.middleware("http")
async def auth_and_rate_limit(request: Request, call_next):
    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Skip rate limiting for docs and health
    if request.url.path in _RATE_LIMIT_SKIP:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        # Log health requests but don't rate limit them
        if request.url.path == "/api/v1/health":
            key_info = authenticate(request)
            log_usage(key_info.key_hash, request.url.path, response.status_code)
        return response

    key_info = authenticate(request)

    request.state.tier = key_info.tier

    # Invalid key: provided but not found/active → 401
    if key_info.tier == "invalid":
        resp = JSONResponse(
            status_code=401,
            content=ErrorResponse(
                error=ErrorDetail(
                    status=401,
                    title="Unauthorized",
                    detail="API key not found or inactive",
                    request_id=request_id,
                )
            ).model_dump(),
        )
        resp.headers["X-Request-ID"] = request_id
        return resp

    # Bucket by API key hash or client IP
    bucket = key_info.key_hash or request.client.host if request.client else "unknown"

    # Per-minute rate limit
    result = check_rate_limit(bucket, key_info.tier)
    if not result.allowed:
        resp = JSONResponse(
            status_code=429,
            content=ErrorResponse(
                error=ErrorDetail(
                    status=429,
                    title="Rate Limit Exceeded",
                    detail=f"Limit: {result.limit} req/min for {key_info.tier} tier",
                    request_id=request_id,
                )
            ).model_dump(),
        )
        resp.headers["X-Request-ID"] = request_id
        resp.headers["X-RateLimit-Limit"] = str(result.limit)
        resp.headers["X-RateLimit-Remaining"] = "0"
        resp.headers["X-RateLimit-Reset"] = str(int(result.reset))
        log_usage(bucket, request.url.path, 429)
        return resp

    # Daily rate limit
    daily_result = check_daily_limit(bucket, key_info.tier)
    if not daily_result.allowed:
        resp = JSONResponse(
            status_code=429,
            content=ErrorResponse(
                error=ErrorDetail(
                    status=429,
                    title="Daily Rate Limit Exceeded",
                    detail=f"Daily limit: {daily_result.limit} requests for {key_info.tier} tier",
                    request_id=request_id,
                )
            ).model_dump(),
        )
        resp.headers["X-Request-ID"] = request_id
        resp.headers["X-RateLimit-Daily-Limit"] = str(daily_result.limit)
        resp.headers["X-RateLimit-Daily-Remaining"] = "0"
        log_usage(bucket, request.url.path, 429)
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
                    status=500,
                    title="Internal Server Error",
                    detail="An unexpected error occurred",
                    request_id=request_id,
                )
            ).model_dump(),
        )
        resp.headers["X-Request-ID"] = request_id
        log_usage(bucket, request.url.path, 500)
        return resp

    # Add request ID and auth tier headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Auth-Tier"] = key_info.tier

    # Deprecation warning for query param API key
    if key_info.query_param_used:
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "2026-09-01"
        response.headers["X-Deprecation-Notice"] = "Pass API key via X-API-Key header instead of ?api_key= query param"

    # Add per-minute rate limit headers
    response.headers["X-RateLimit-Limit"] = str(result.limit)
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    response.headers["X-RateLimit-Reset"] = str(int(result.reset))

    # Add daily rate limit headers
    response.headers["X-RateLimit-Daily-Limit"] = str(daily_result.limit)
    response.headers["X-RateLimit-Daily-Remaining"] = str(daily_result.remaining)

    # Log usage (use bucket so anonymous users are tracked by IP)
    log_usage(bucket, request.url.path, response.status_code)

    # Structured access logging
    client_ip = request.client.host if request.client else "unknown"
    tier = key_info.tier
    log_level = logging.WARNING if response.status_code in (401, 429) else logging.INFO
    access_log.log(log_level, "%s %s %s %d %s %s", client_ip, request.method, request.url.path, response.status_code, tier, request_id)

    return response


# --- Exception handlers ---

@app.exception_handler(RPCError)
async def rpc_error_handler(request: Request, exc: RPCError):
    request_id = getattr(request.state, "request_id", None)
    # Map RPC error codes to HTTP status
    if exc.code == -5:  # txid/block not found
        http_status = 404
        title = "Not Found"
    elif exc.code == -8:  # invalid parameter
        http_status = 400
        title = "Bad Request"
    elif exc.code == -25:  # tx already in mempool / missing inputs
        http_status = 409
        title = "Transaction Already in Mempool"
    elif exc.code == -26:  # tx policy rejection
        http_status = 422
        title = "Transaction Failed Policy Checks"
    elif exc.code == -27:  # tx already confirmed
        http_status = 409
        title = "Transaction Already Confirmed"
    else:
        http_status = 502
        title = "Node Error"

    resp = JSONResponse(
        status_code=http_status,
        content=ErrorResponse(
            error=ErrorDetail(
                status=http_status, title=title, detail=exc.message, request_id=request_id,
            )
        ).model_dump(),
    )
    if request_id:
        resp.headers["X-Request-ID"] = request_id
    return resp


@app.exception_handler(ConnectionError)
async def connection_error_handler(request: Request, exc: ConnectionError):
    from .dependencies import reset_rpc
    reset_rpc()
    request_id = getattr(request.state, "request_id", None)
    resp = JSONResponse(
        status_code=502,
        content=ErrorResponse(
            error=ErrorDetail(
                status=502,
                title="Node Unreachable",
                detail="Cannot connect to Bitcoin Core. Is the node running?",
                request_id=request_id,
            )
        ).model_dump(),
    )
    if request_id:
        resp.headers["X-Request-ID"] = request_id
    return resp


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    details = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
    )
    resp = JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error=ErrorDetail(
                status=422,
                title="Validation Error",
                detail=details,
                request_id=request_id,
            )
        ).model_dump(),
    )
    if request_id:
        resp.headers["X-Request-ID"] = request_id
    return resp


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", None)
    resp = JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                status=exc.status_code,
                title="Error",
                detail=str(exc.detail),
                request_id=request_id,
            )
        ).model_dump(),
    )
    if request_id:
        resp.headers["X-Request-ID"] = request_id
    return resp


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    log.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    resp = JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(
                status=500,
                title="Internal Server Error",
                detail="An unexpected error occurred.",
                request_id=request_id,
            )
        ).model_dump(),
    )
    if request_id:
        resp.headers["X-Request-ID"] = request_id
    return resp




# --- Routers ---

PREFIX = "/api/v1"
app.include_router(status.router, prefix=PREFIX)
app.include_router(blocks.router, prefix=PREFIX)
app.include_router(transactions.router, prefix=PREFIX)
app.include_router(mempool.router, prefix=PREFIX)
app.include_router(fees.router, prefix=PREFIX)
app.include_router(mining.router, prefix=PREFIX)
app.include_router(network.router, prefix=PREFIX)
app.include_router(prices.router, prefix=PREFIX)
app.include_router(keys.router, prefix=PREFIX)
app.include_router(stream.router, prefix=PREFIX)
app.include_router(address.router, prefix=PREFIX)
if settings.enable_exchange_compare:
    app.include_router(exchanges.router, prefix=PREFIX)


# --- Root redirect ---

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"
_LANDING_PAGE = _STATIC_DIR / "index.html"


@app.get("/", include_in_schema=False)
def root():
    if _LANDING_PAGE.exists():
        return HTMLResponse(_LANDING_PAGE.read_text(encoding="utf-8"))
    return {
        "name": "Satoshi API",
        "version": __version__,
        "docs": "/docs",
        "api": "/api/v1/health",
    }


@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    p = _STATIC_DIR / "robots.txt"
    if p.exists():
        return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
    return Response("User-agent: *\nAllow: /\n", media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    p = _STATIC_DIR / "sitemap.xml"
    if p.exists():
        return Response(p.read_text(encoding="utf-8"), media_type="application/xml")
    return Response(status_code=404)


@app.get("/healthz", include_in_schema=False)
def healthz():
    """Process-alive check (no RPC call). Use for container healthchecks."""
    return {"status": "ok"}


@app.get("/{page}", include_in_schema=False)
def static_page(page: str):
    """Serve decision/comparison pages and IndexNow key from static directory."""
    allowed = {
        "vs-mempool", "vs-blockcypher", "best-bitcoin-api-for-developers",
        "bitcoin-api-for-ai-agents", "self-hosted-bitcoin-api",
        "bitcoin-fee-api", "bitcoin-mempool-api",
    }
    if page in allowed:
        p = _STATIC_DIR / f"{page}.html"
        if p.exists():
            return HTMLResponse(p.read_text(encoding="utf-8"))
    # Serve IndexNow verification key files ({key}.txt)
    if page.endswith(".txt") and len(page) == 36:  # 32 hex + .txt
        p = _STATIC_DIR / page
        if p.exists():
            return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
    return Response(status_code=404)


def cli():
    import uvicorn
    uvicorn.run(
        "bitcoin_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        timeout_graceful_shutdown=30,
    )


if __name__ == "__main__":
    cli()
