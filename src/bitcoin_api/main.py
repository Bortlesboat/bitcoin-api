"""Bitcoin API — FastAPI application."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from bitcoinlib_rpc.rpc import RPCError

from .auth import authenticate
from .config import settings
from .db import get_db
from .models import ErrorResponse, ErrorDetail
from .rate_limit import check_rate_limit
from .routers import status, blocks, transactions, mempool, fees


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB
    get_db()
    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title="Bitcoin API",
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
    allow_methods=["GET"],
    allow_headers=["X-API-Key"],
)


# --- Middleware: auth + rate limiting ---

@app.middleware("http")
async def auth_and_rate_limit(request: Request, call_next):
    # Skip rate limiting for docs
    if request.url.path in ("/docs", "/redoc", "/openapi.json"):
        return await call_next(request)

    key_info = authenticate(request)

    # Bucket by API key hash or client IP
    bucket = key_info.key_hash or request.client.host if request.client else "unknown"
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
        return resp

    response = await call_next(request)

    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = str(result.limit)
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    response.headers["X-RateLimit-Reset"] = str(int(result.reset))

    return response


# --- Exception handlers ---

@app.exception_handler(RPCError)
async def rpc_error_handler(request: Request, exc: RPCError):
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

    return JSONResponse(
        status_code=http_status,
        content=ErrorResponse(
            error=ErrorDetail(status=http_status, title=title, detail=exc.message)
        ).model_dump(),
    )


@app.exception_handler(ConnectionError)
async def connection_error_handler(request: Request, exc: ConnectionError):
    return JSONResponse(
        status_code=502,
        content=ErrorResponse(
            error=ErrorDetail(
                status=502,
                title="Node Unreachable",
                detail="Cannot connect to Bitcoin Core. Is the node running?",
            )
        ).model_dump(),
    )


# --- Routers ---

PREFIX = "/api/v1"
app.include_router(status.router, prefix=PREFIX)
app.include_router(blocks.router, prefix=PREFIX)
app.include_router(transactions.router, prefix=PREFIX)
app.include_router(mempool.router, prefix=PREFIX)
app.include_router(fees.router, prefix=PREFIX)


# --- Root redirect ---

@app.get("/", include_in_schema=False)
def root():
    return {
        "name": "Bitcoin API",
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
        reload=True,
    )
