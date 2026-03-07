"""Bitcoin API — FastAPI application."""

import logging
import uuid
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from bitcoinlib_rpc.rpc import RPCError

from .auth import authenticate
from .config import settings
from .db import get_db, log_usage, prune_old_logs
from .models import ErrorResponse, ErrorDetail
from .rate_limit import check_rate_limit, check_daily_limit
from . import __version__
from .routers import status, blocks, transactions, mempool, fees, mining, network, prices, keys

access_log = logging.getLogger("bitcoin_api.access")


log = logging.getLogger("bitcoin_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB + prune old logs
    get_db()
    prune_old_logs()
    log.info("Satoshi API starting on %s:%s", settings.api_host, settings.api_port)
    yield
    # Shutdown: close DB connections
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
_RATE_LIMIT_SKIP = {"/", "/docs", "/redoc", "/openapi.json", "/api/v1/health", "/healthz", "/api/v1/register"}


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


# --- Root redirect ---

_LANDING_PAGE = Path(__file__).resolve().parent.parent.parent / "static" / "index.html"


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


@app.get("/healthz", include_in_schema=False)
def healthz():
    """Process-alive check (no RPC call). Use for container healthchecks."""
    return {"status": "ok"}


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
