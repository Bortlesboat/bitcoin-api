"""Exception handlers for the FastAPI application."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from bitcoinlib_rpc.rpc import RPCError

from .models import ErrorResponse, ErrorDetail

log = logging.getLogger("bitcoin_api")


def register_exception_handlers(app: FastAPI):
    """Register all exception handlers on the app."""

    @app.exception_handler(RPCError)
    async def rpc_error_handler(request: Request, exc: RPCError):
        request_id = getattr(request.state, "request_id", None)
        if exc.code == -5:
            http_status = 404
            title = "Not Found"
        elif exc.code == -8:
            http_status = 400
            title = "Bad Request"
        elif exc.code == -25:
            http_status = 409
            title = "Transaction Already in Mempool"
        elif exc.code == -26:
            http_status = 422
            title = "Transaction Failed Policy Checks"
        elif exc.code == -27:
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
