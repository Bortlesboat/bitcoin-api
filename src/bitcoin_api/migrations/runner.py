"""Database migration runner — applies .sql files in order, tracks in schema_migrations."""

import logging
import sqlite3
from pathlib import Path

log = logging.getLogger("bitcoin_api.migrations")

_MIGRATIONS_DIR = Path(__file__).parent


def _ensure_migrations_table(conn: sqlite3.Connection):
    """Create the schema_migrations table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def _get_applied(conn: sqlite3.Connection) -> set[str]:
    """Return set of already-applied migration versions."""
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {row[0] for row in rows}


def _get_pending(conn: sqlite3.Connection) -> list[Path]:
    """Return sorted list of .sql migration files not yet applied."""
    applied = _get_applied(conn)
    sql_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
    return [f for f in sql_files if f.stem not in applied]


def run_pending(conn: sqlite3.Connection) -> list[str]:
    """Run all pending migrations. Returns list of applied migration names."""
    _ensure_migrations_table(conn)
    pending = _get_pending(conn)
    applied = []

    for migration_file in pending:
        version = migration_file.stem
        sql = migration_file.read_text(encoding="utf-8")
        try:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (version,),
            )
            conn.commit()
            applied.append(version)
            log.info("Applied migration: %s", version)
        except Exception:
            log.error("Failed to apply migration: %s", version, exc_info=True)
            raise

    return applied
