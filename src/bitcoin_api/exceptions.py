"""Exception handlers for the FastAPI application."""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from bitcoinlib_rpc.rpc import RPCError

from .circuit_breaker import CircuitOpenError, rpc_breaker
from .models import ErrorResponse, ErrorDetail

log = logging.getLogger("bitcoin_api")

_GUIDE_URL = "/api/v1/guide"

_PATH_PREFIXES = [
    ("/api/v1/fees", "fees"),
    ("/api/v1/blocks", "blocks"),
    ("/api/v1/tx", "transactions"),
    ("/api/v1/decode", "transactions"),
    ("/api/v1/broadcast", "transactions"),
    ("/api/v1/utxo", "transactions"),
    ("/api/v1/mempool", "mempool"),
    ("/api/v1/mining", "mining"),
    ("/api/v1/network", "network"),
    ("/api/v1/stream", "streams"),
    ("/api/v1/prices", "prices"),
    ("/api/v1/address", "address"),
    ("/api/v1/tools", "tools"),
]


def _path_to_use_case(path: str) -> str | None:
    """Map a request path to a guide use_case category."""
    for prefix, use_case in _PATH_PREFIXES:
        if path.startswith(prefix):
            return use_case
    return None


def _guide_help_url(path: str) -> str:
    """Build a help_url pointing to the guide, optionally filtered by use_case."""
    use_case = _path_to_use_case(path)
    if use_case:
        return f"{_GUIDE_URL}?use_case={use_case}"
    return _GUIDE_URL


# RFC 7807 error type URIs
_ERROR_BASE = "https://bitcoinsapi.com/errors"
ERROR_TYPES = {
    "not_found": f"{_ERROR_BASE}/not-found",
    "bad_request": f"{_ERROR_BASE}/bad-request",
    "conflict": f"{_ERROR_BASE}/conflict",
    "validation": f"{_ERROR_BASE}/validation-error",
    "policy": f"{_ERROR_BASE}/policy-violation",
    "node_error": f"{_ERROR_BASE}/node-error",
    "node_unreachable": f"{_ERROR_BASE}/node-unreachable",
    "unauthorized": f"{_ERROR_BASE}/unauthorized",
    "rate_limit": f"{_ERROR_BASE}/rate-limit-exceeded",
    "internal": f"{_ERROR_BASE}/internal-error",
    "circuit_open": f"{_ERROR_BASE}/circuit-open",
}


def register_exception_handlers(app: FastAPI):
    """Register all exception handlers on the app."""

    @app.exception_handler(CircuitOpenError)
    async def circuit_open_handler(request: Request, exc: CircuitOpenError):
        request_id = getattr(request.state, "request_id", None)
        remaining = rpc_breaker._recovery_timeout - (time.time() - rpc_breaker._last_failure_time)
        retry_after = str(max(1, int(remaining)))
        resp = JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error=ErrorDetail(
                    type=ERROR_TYPES["circuit_open"],
                    status=503,
                    title="Service Unavailable",
                    detail=str(exc),
                    request_id=request_id,
                )
            ).model_dump(),
        )
        resp.headers["Retry-After"] = retry_after
        if request_id:
            resp.headers["X-Request-ID"] = request_id
        return resp

    @app.exception_handler(RPCError)
    async def rpc_error_handler(request: Request, exc: RPCError):
        request_id = getattr(request.state, "request_id", None)
        if exc.code == -5:
            http_status, title, err_type = 404, "Not Found", ERROR_TYPES["not_found"]
        elif exc.code == -8:
            http_status, title, err_type = 400, "Bad Request", ERROR_TYPES["bad_request"]
        elif exc.code == -25:
            http_status, title, err_type = 409, "Transaction Already in Mempool", ERROR_TYPES["conflict"]
        elif exc.code == -26:
            http_status, title, err_type = 422, "Transaction Failed Policy Checks", ERROR_TYPES["policy"]
        elif exc.code == -27:
            http_status, title, err_type = 409, "Transaction Already Confirmed", ERROR_TYPES["conflict"]
        else:
            http_status, title, err_type = 502, "Node Error", ERROR_TYPES["node_error"]

        # Circuit breaker: 502 = node-level failure, others = node responded fine
        if http_status == 502:
            rpc_breaker.record_failure()
        else:
            rpc_breaker.record_success()

        resp = JSONResponse(
            status_code=http_status,
            content=ErrorResponse(
                error=ErrorDetail(
                    type=err_type, status=http_status, title=title, detail=exc.message, request_id=request_id,
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
        rpc_breaker.record_failure()
        request_id = getattr(request.state, "request_id", None)
        resp = JSONResponse(
            status_code=502,
            content=ErrorResponse(
                error=ErrorDetail(
                    type=ERROR_TYPES["node_unreachable"],
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
                    type=ERROR_TYPES["validation"],
                    status=422,
                    title="Validation Error",
                    detail=details,
                    request_id=request_id,
                    help_url=_guide_help_url(request.url.path),
                )
            ).model_dump(),
        )
        if request_id:
            resp.headers["X-Request-ID"] = request_id
        return resp

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
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
                    type=ERROR_TYPES["internal"],
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
