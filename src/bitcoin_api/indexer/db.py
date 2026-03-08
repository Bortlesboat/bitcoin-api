"""Asyncpg connection pool and migration runner for the indexer."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .config import indexer_settings

if TYPE_CHECKING:
    import asyncpg

log = logging.getLogger(__name__)

_pool: Any = None  # asyncpg.Pool | None — typed as Any to avoid runtime import

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def init_pool() -> Any:
    """Create the asyncpg connection pool and run migrations."""
    import asyncpg as _asyncpg

    global _pool
    _pool = await _asyncpg.create_pool(
        indexer_settings.postgres_dsn,
        min_size=2,
        max_size=10,
    )
    await run_migrations()
    log.info("Indexer database pool initialized")
    return _pool


def get_pool() -> Any:
    """Return the active connection pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError("Indexer database pool not initialized — call init_pool() first")
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        log.info("Indexer database pool closed")


async def run_migrations() -> None:
    """Execute SQL migration files in order."""
    pool = get_pool()
    migration_files = sorted(
        MIGRATIONS_DIR.glob("*.sql"),
        key=lambda f: int(f.name.split("_")[0]),
    )
    async with pool.acquire() as conn:
        for mf in migration_files:
            log.info("Running indexer migration: %s", mf.name)
            sql = mf.read_text()
            await conn.execute(sql)
    log.info("Indexer migrations complete (%d files)", len(migration_files))
