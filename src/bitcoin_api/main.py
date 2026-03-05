"""Bitcoin API — FastAPI application."""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from bitcoinlib_rpc.rpc import RPCError

from .auth import authenticate
from .config import settings
from .db import get_db, log_usage, prune_old_logs
from .models import ErrorResponse, ErrorDetail
from .rate_limit import check_rate_limit, check_daily_limit
from .routers import status, blocks, transactions, mempool, fees, mining, network


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB + prune old logs
    get_db()
    prune_old_logs()
    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title="Satoshi API",
    description="Developer-friendly REST API for Bitcoin node data. "
    "Powered by bitcoinlib-rpc — analyzed data, not raw RPC.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key"],
)

# Paths exempt from rate limiting
_RATE_LIMIT_SKIP = {"/docs", "/redoc", "/openapi.json", "/api/v1/health"}


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
                )
            ).model_dump(),
        )
        resp.headers["X-RateLimit-Limit"] = str(result.limit)
        resp.headers["X-RateLimit-Remaining"] = "0"
        resp.headers["X-RateLimit-Reset"] = str(int(result.reset))
        log_usage(key_info.key_hash, request.url.path, 429)
        return resp

    # Daily rate limit
    daily_result = check_daily_limit(key_info.key_hash or bucket, key_info.tier)
    if not daily_result.allowed:
        resp = JSONResponse(
            status_code=429,
            content=ErrorResponse(
                error=ErrorDetail(
                    status=429,
                    title="Daily Rate Limit Exceeded",
                    detail=f"Daily limit: {daily_result.limit} requests for {key_info.tier} tier",
                )
            ).model_dump(),
        )
        resp.headers["X-RateLimit-Daily-Limit"] = str(daily_result.limit)
        resp.headers["X-RateLimit-Daily-Remaining"] = "0"
        log_usage(key_info.key_hash, request.url.path, 429)
        return resp

    response = await call_next(request)

    # Add request ID and auth tier headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Auth-Tier"] = key_info.tier

    # Add per-minute rate limit headers
    response.headers["X-RateLimit-Limit"] = str(result.limit)
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    response.headers["X-RateLimit-Reset"] = str(int(result.reset))

    # Add daily rate limit headers
    response.headers["X-RateLimit-Daily-Limit"] = str(daily_result.limit)
    response.headers["X-RateLimit-Daily-Remaining"] = str(daily_result.remaining)

    # Log usage
    log_usage(key_info.key_hash, request.url.path, response.status_code)

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


# --- Routers ---

PREFIX = "/api/v1"
app.include_router(status.router, prefix=PREFIX)
app.include_router(blocks.router, prefix=PREFIX)
app.include_router(transactions.router, prefix=PREFIX)
app.include_router(mempool.router, prefix=PREFIX)
app.include_router(fees.router, prefix=PREFIX)
app.include_router(mining.router, prefix=PREFIX)
app.include_router(network.router, prefix=PREFIX)


# --- Root redirect ---

@app.get("/", include_in_schema=False)
def root():
    return {
        "name": "Satoshi API",
        "version": "0.1.0",
        "docs": "/docs",
        "api": "/api/v1/health",
    }


def cli():
    import uvicorn
    uvicorn.run(
        "bitcoin_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )
