#!/usr/bin/env bash
# Daily SQLite backup for Satoshi API
# Keeps last 7 backups, uses sqlite3 .backup when available (WAL-safe)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DB_PATH="$PROJECT_DIR/data/bitcoin_api.db"
BACKUP_DIR="$PROJECT_DIR/data/backups"
DATE=$(date +%Y-%m-%d)
BACKUP_PATH="$BACKUP_DIR/bitcoin_api_${DATE}.db"

# Create backups directory if needed
mkdir -p "$BACKUP_DIR"

# Check source DB exists
if [ ! -f "$DB_PATH" ]; then
    echo "[$(date -Iseconds)] ERROR: Database not found at $DB_PATH"
    exit 1
fi

# Backup using sqlite3 .backup (WAL-safe) or fall back to cp
if command -v sqlite3 &>/dev/null; then
    sqlite3 "$DB_PATH" ".backup '$BACKUP_PATH'"
    echo "[$(date -Iseconds)] OK: Backed up via sqlite3 .backup → $BACKUP_PATH"
else
    cp "$DB_PATH" "$BACKUP_PATH"
    echo "[$(date -Iseconds)] OK: Backed up via cp (sqlite3 not available) → $BACKUP_PATH"
fi

# Prune backups older than 7 days (keep only the 7 most recent)
cd "$BACKUP_DIR"
ls -1t bitcoin_api_*.db 2>/dev/null | tail -n +8 | while read -r old; do
    rm -f "$old"
    echo "[$(date -Iseconds)] PRUNED: $old"
done

echo "[$(date -Iseconds)] DONE: $(ls -1 bitcoin_api_*.db 2>/dev/null | wc -l) backup(s) retained"
