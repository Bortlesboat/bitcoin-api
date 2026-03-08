"""Bitcoin API — FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db import get_db, close_db, prune_old_logs, prune_fee_history
from .exceptions import register_exception_handlers
from .jobs import start_background_jobs, stop_background_jobs
from .middleware import register_middleware
from .notifications import init_notifications
from .rate_limit import init_redis
from .static_routes import register_static_routes
from . import __version__
from .routers import status, blocks, transactions, mempool, fees, mining, network, prices, keys, stream, exchanges, address, health_deep, guide, metrics as metrics_router, websocket as ws_router, billing as billing_router, supply, stats

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

    yield

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
    description="Developer-friendly REST API for Bitcoin node data. "
    "Powered by bitcoinlib-rpc — analyzed data, not raw RPC.",
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

from .routers.analytics import router as _analytics_router  # noqa: E402
app.include_router(_analytics_router, prefix=PREFIX)

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
}
for flag, router in _FEATURE_ROUTERS.items():
    if settings.feature_flags.get(flag, False):
        app.include_router(router, prefix=PREFIX)

# Blockchain indexer routers (conditional — only if enabled)
if settings.enable_indexer:
    from .indexer.routers import indexed_address, indexed_tx, indexer_status
    app.include_router(indexed_address.router, prefix=PREFIX)
    app.include_router(indexed_tx.router, prefix=PREFIX)
    app.include_router(indexer_status.router, prefix=PREFIX)

register_static_routes(app)


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
