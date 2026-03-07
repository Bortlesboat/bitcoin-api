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
    sql_files = sorted(f for f in _MIGRATIONS_DIR.glob("*.sql") if not f.stem.endswith(".down"))
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


def rollback_last(conn: sqlite3.Connection) -> str | None:
    """Rollback the most recently applied migration if a .down.sql file exists.

    Returns the rolled-back version name, or None if nothing to rollback.
    """
    _ensure_migrations_table(conn)
    row = conn.execute(
        "SELECT version FROM schema_migrations ORDER BY applied_at DESC, version DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None

    version = row[0]
    down_file = _MIGRATIONS_DIR / f"{version}.down.sql"
    if not down_file.exists():
        log.warning("No rollback file for %s (expected %s)", version, down_file.name)
        return None

    sql = down_file.read_text(encoding="utf-8")
    try:
        conn.executescript(sql)
        conn.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
        conn.commit()
        log.info("Rolled back migration: %s", version)
        return version
    except Exception:
        log.error("Failed to rollback migration: %s", version, exc_info=True)
        raise


def get_migration_status(conn: sqlite3.Connection) -> list[dict]:
    """Return list of applied migrations with rollback availability."""
    _ensure_migrations_table(conn)
    rows = conn.execute(
        "SELECT version, applied_at FROM schema_migrations ORDER BY version"
    ).fetchall()
    result = []
    for version, applied_at in rows:
        down_file = _MIGRATIONS_DIR / f"{version}.down.sql"
        result.append({
            "version": version,
            "applied_at": applied_at,
            "has_rollback": down_file.exists(),
        })
    return result


def validate_migrations() -> list[str]:
    """Check that migration files are sequential and well-formed. Returns list of warnings."""
    warnings = []
    sql_files = sorted(f for f in _MIGRATIONS_DIR.glob("*.sql") if not f.stem.endswith(".down"))

    for i, f in enumerate(sql_files):
        prefix = f.stem.split("_")[0]
        try:
            num = int(prefix)
            if num != i + 1:
                warnings.append(f"{f.name}: expected prefix {i+1:03d}, got {prefix}")
        except ValueError:
            warnings.append(f"{f.name}: prefix '{prefix}' is not a number")

        content = f.read_text(encoding="utf-8").strip()
        if not content:
            warnings.append(f"{f.name}: file is empty")

    return warnings
