"""Initialize the SQLite database schema."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bitcoin_api.db import get_db


def main():
    db = get_db()
    print(f"Database initialized at {db}")
    # Verify tables
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    for t in tables:
        print(f"  Table: {t['name']}")


if __name__ == "__main__":
    main()
