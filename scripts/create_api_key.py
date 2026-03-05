"""CLI to generate API keys."""

import argparse
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bitcoin_api.auth import hash_key
from bitcoin_api.db import get_db


def generate_key() -> str:
    return "btc_" + secrets.token_hex(16)


def main():
    parser = argparse.ArgumentParser(description="Create a Bitcoin API key")
    parser.add_argument("--tier", choices=["free", "pro", "enterprise"], default="free")
    parser.add_argument("--label", help="Optional label for this key")
    args = parser.parse_args()

    raw_key = generate_key()
    key_hash = hash_key(raw_key)
    prefix = raw_key[:8]

    db = get_db()
    db.execute(
        "INSERT INTO api_keys (key_hash, prefix, tier, label) VALUES (?, ?, ?, ?)",
        (key_hash, prefix, args.tier, args.label),
    )
    db.commit()

    print(f"API Key created:")
    print(f"  Key:    {raw_key}")
    print(f"  Tier:   {args.tier}")
    print(f"  Label:  {args.label or '(none)'}")
    print(f"  Prefix: {prefix}")
    print()
    print("Store this key securely — it cannot be recovered.")


if __name__ == "__main__":
    main()
