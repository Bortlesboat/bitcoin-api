"""Bitcoin API — FastAPI application."""

import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db import get_db, close_db, prune_old_logs, prune_fee_history, prune_x402_payments, log_x402_payment
from .exceptions import register_exception_handlers
from .jobs import start_background_jobs, stop_background_jobs
from .middleware import register_middleware
from .notifications import init_notifications
from .rate_limit import init_redis
from .static_routes import register_static_routes
from . import __version__
from .routers import status, blocks, transactions, mempool, fees, mining, network, prices, keys, stream, exchanges, address, health_deep, guide, metrics as metrics_router, websocket as ws_router, billing as billing_router, supply, stats, rpc_proxy, psbt as psbt_router

log = logging.getLogger("bitcoin_api")


def _init_api_key_gauge():
    """Set the API key gauge to the current count from DB."""
    from .metrics import API_KEYS_REGISTERED
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM api_keys").fetchone()[0]
    API_KEYS_REGISTERED.set(count)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_db()
    prune_old_logs()
    prune_fee_history()
    prune_x402_payments()
    _init_api_key_gauge()
    init_redis()
    init_notifications()
    log.info("Satoshi API starting on %s:%s", settings.api_host, settings.api_port)
    start_background_jobs()

    # Start indexer worker if enabled
    _indexer_task = None
    if settings.enable_indexer:
        try:
            from .indexer.db import init_pool, close_pool
            from .indexer.worker import start_worker, request_shutdown
            await init_pool()
            _indexer_task = asyncio.create_task(start_worker())

            def _on_worker_done(task: asyncio.Task):
                if task.cancelled():
                    return
                exc = task.exception()
                if exc:
                    log.error("Indexer worker crashed: %s", exc, exc_info=exc)

            _indexer_task.add_done_callback(_on_worker_done)
            log.info("Blockchain indexer started")
        except Exception:
            log.exception("Failed to start indexer — continuing without it")

    # Start MCP session manager for streamable-http transport
    _mcp_cm = None
    try:
        from .routers.mcp_server import mcp as _mcp_server
        if _mcp_server._session_manager is not None:
            _mcp_cm = _mcp_server._session_manager.run()
            await _mcp_cm.__aenter__()
            log.info("MCP session manager started")
    except Exception:
        log.exception("Failed to start MCP session manager")
        _mcp_cm = None

    yield

    # Shutdown MCP session manager
    if _mcp_cm is not None:
        try:
            await _mcp_cm.__aexit__(None, None, None)
        except Exception:
            pass
        log.info("MCP session manager stopped")

    # Shutdown indexer
    if _indexer_task is not None:
        from .indexer.worker import request_shutdown
        from .indexer.db import close_pool
        request_shutdown()
        _indexer_task.cancel()
        try:
            await _indexer_task
        except asyncio.CancelledError:
            pass
        await close_pool()
        log.info("Blockchain indexer stopped")

    stop_background_jobs()
    from .usage_buffer import usage_buffer
    usage_buffer.flush()

    # Flush PostHog analytics before shutdown
    if settings.posthog_enabled and settings.posthog_api_key:
        try:
            import posthog
            posthog.flush()
            posthog.shutdown()
        except Exception:
            pass

    close_db()
    log.info("Satoshi API shutting down")


app = FastAPI(
    title="Satoshi API",
    description="Bitcoin fee intelligence API. Know when to send and save money "
    "on every transaction. MCP-native, self-hostable, open source.",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "Satoshi API Support", "email": "api@bitcoinsapi.com", "url": "https://bitcoinsapi.com"},
    license_info={"name": "Apache-2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
    terms_of_service="https://bitcoinsapi.com/terms",
    servers=[
        {"url": "https://bitcoinsapi.com", "description": "Production"},
        {"url": "http://localhost:9332", "description": "Local development"},
    ],
)

register_middleware(app)
register_exception_handlers(app)

# --- x402 stablecoin micropayments (optional extension, off by default) ---
if settings.enable_x402:
    try:
        from bitcoin_api_x402 import enable_x402, set_payment_logger
        enable_x402(app, pay_to=settings.x402_pay_to_address)
        set_payment_logger(log_x402_payment)
        log.info("x402 stablecoin payments enabled (pay_to=%s)", settings.x402_pay_to_address[:10] + "..." if settings.x402_pay_to_address else "NOT SET")
    except ImportError:
        log.warning("ENABLE_X402=true but bitcoin-api-x402 not installed — run: pip install -e ../bitcoin-api-x402")

# --- Routers ---
PREFIX = "/api/v1"

app.include_router(status.router, prefix=PREFIX)
app.include_router(blocks.router, prefix=PREFIX)
app.include_router(transactions.router, prefix=PREFIX)
app.include_router(fees.router, prefix=PREFIX)
app.include_router(mempool.router, prefix=PREFIX)
app.include_router(mining.router, prefix=PREFIX)
app.include_router(network.router, prefix=PREFIX)
app.include_router(stream.router, prefix=PREFIX)
app.include_router(keys.router, prefix=PREFIX)
app.include_router(health_deep.router, prefix=PREFIX)
app.include_router(guide.router, prefix=PREFIX)
app.include_router(rpc_proxy.router, prefix=PREFIX)

from .routers.analytics import router as _analytics_router  # noqa: E402
app.include_router(_analytics_router, prefix=PREFIX)

from .routers.x402_stats import router as _x402_stats_router  # noqa: E402
app.include_router(_x402_stats_router, prefix=PREFIX)

# Prometheus metrics (no prefix — served at /metrics)
app.include_router(metrics_router.router)

# WebSocket
app.include_router(ws_router.router, prefix=PREFIX)

# Stripe billing (always registered — returns 503 if not configured)
app.include_router(billing_router.router, prefix=PREFIX)

# Extended (toggleable via feature flags)
_FEATURE_ROUTERS = {
    "prices_router": prices.router,
    "address_router": address.router,
    "exchange_compare": exchanges.router,
    "supply_router": supply.router,
    "stats_router": stats.router,
    "psbt_router": psbt_router.router,  # PSBT security analysis (off by default)
}
for flag, router in _FEATURE_ROUTERS.items():
    if settings.feature_flags.get(flag, False):
        app.include_router(router, prefix=PREFIX)

# Fee/tx alert webhooks (always registered — requires API key)
from .routers.alerts import router as _alerts_router
app.include_router(_alerts_router, prefix=PREFIX)

# AI endpoints (conditional — requires ENABLE_AI_FEATURES=true + provider config)
if settings.enable_ai_features:
    from .routers.ai import router as _ai_router
    app.include_router(_ai_router, prefix=PREFIX)
    log.info("AI features enabled (provider will be resolved on first request)")

# Fee Observatory (conditional — reads observatory.db read-only)
if settings.enable_observatory:
    from .routers.observatory import router as _observatory_router
    app.include_router(_observatory_router, prefix=PREFIX)
    log.info("Fee Observatory endpoints enabled")

# History Explorer (conditional — siloed feature)
if settings.enable_history_explorer:
    from .routers.history import router as _history_router
    app.include_router(_history_router, prefix=PREFIX)
    log.info("History Explorer enabled")

# Blockchain indexer routers (conditional — only if enabled)
if settings.enable_indexer:
    from .indexer.routers import indexed_address, indexed_tx, indexer_status
    app.include_router(indexed_address.router, prefix=PREFIX)
    app.include_router(indexed_tx.router, prefix=PREFIX)
    app.include_router(indexer_status.router, prefix=PREFIX)

# --- MCP server (streamable-http transport at /mcp) ---
try:
    from .routers.mcp_server import create_mcp_app
    mcp_app = create_mcp_app()
    app.mount("/mcp", mcp_app)
    log.info("MCP server mounted at /mcp (streamable-http)")
except Exception:
    log.exception("Failed to mount MCP server — continuing without it")

# --- x402 machine-readable discovery (.well-known/x402) ---
@app.get("/.well-known/x402", include_in_schema=False)
def well_known_x402():
    """Machine-readable x402 discovery for AI agents and automated clients.

    Format follows the x402scan Discovery Spec:
    https://www.x402scan.com/discovery
    """
    try:
        from bitcoin_api_x402.pricing import ENDPOINT_PRICES
        # Strip regex anchors (^ $) from patterns for clean paths.
        # broadcast is POST, everything else is GET.
        resources = []
        for ep in ENDPOINT_PRICES:
            clean = re.sub(r"[$^]", "", ep.pattern)
            method = "POST" if "broadcast" in clean else "GET"
            resources.append(f"{method} {clean}")
        return {"version": 1, "resources": resources}
    except ImportError:
        return {"version": 1, "resources": []}


# --- Inject x-payment-info into OpenAPI schema for x402scan discovery ---
def _patch_openapi_x402(app_ref):  # type: ignore[no-untyped-def]
    """Add x-payment-info extensions to paid endpoints in the OpenAPI schema.

    x402scan prefers OpenAPI-based discovery with x-payment-info on each
    monetized operation.  See: https://www.x402scan.com/discovery
    """
    try:
        from bitcoin_api_x402.pricing import ENDPOINT_PRICES
    except ImportError:
        return  # x402 package not installed — nothing to patch

    original_openapi = app_ref.openapi

    def patched_openapi():  # type: ignore[no-untyped-def]
        schema = original_openapi()
        paths = schema.get("paths", {})
        for ep in ENDPOINT_PRICES:
            # Match OpenAPI paths against pricing regex patterns
            compiled = re.compile(ep.pattern)
            for path_key, path_item in paths.items():
                if compiled.search(path_key):
                    for _method, operation in path_item.items():
                        if isinstance(operation, dict):
                            operation["x-payment-info"] = {
                                "protocols": ["x402"],
                                "price": {
                                    "mode": "fixed",
                                    "currency": "USD",
                                    "amount": ep.price_usd.lstrip("$"),
                                },
                            }
        return schema

    app_ref.openapi = patched_openapi


_patch_openapi_x402(app)


# --- Redirect aliases for commonly-guessed singular endpoint paths ---
from fastapi.responses import RedirectResponse as _RR  # noqa: E402


@app.get(f"{PREFIX}/price", include_in_schema=False)
def redirect_price():
    return _RR(url=f"{PREFIX}/prices", status_code=308)


@app.get(f"{PREFIX}/block/latest", include_in_schema=False)
def redirect_block_latest():
    return _RR(url=f"{PREFIX}/blocks/latest", status_code=308)


@app.get(f"{PREFIX}/block/tip", include_in_schema=False)
def redirect_block_tip():
    return _RR(url=f"{PREFIX}/blocks/tip/height", status_code=308)


register_static_routes(app)


def cli():
    import uvicorn
    uvicorn.run(
        "bitcoin_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        timeout_graceful_shutdown=30,
        workers=1,
    )


if __name__ == "__main__":
    cli()
