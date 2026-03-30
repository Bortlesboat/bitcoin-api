#!/usr/bin/env python3
"""Founder-demo rehearsal script.

Runs the key sales-demo flow against the local app via TestClient and checks
that the historical proof story, live planner path, guide, MCP setup, and
premium x402 finish still line up.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from bitcoin_api.main import app


ROOT = Path(__file__).resolve().parent.parent
FALLBACK_JSON = ROOT / "docs" / "demo-assets" / "merchant-payout-batch-march-2026.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    client = TestClient(app)

    proof = client.get("/best-time-to-send-bitcoin")
    require(proof.status_code == 200, "Proof page did not load")
    require("March 19, 2026 at 1:54 PM EDT" in proof.text, "Proof page lost the fixed decision timestamp")
    require("76.3%" in proof.text, "Proof page lost the flagship savings number")

    plan = client.get("/api/v1/fees/plan?profile=merchant_payout_batch&currency=usd")
    require(plan.status_code == 200, "Planner endpoint did not load")
    plan_data = plan.json()["data"]
    require(plan_data["profile"] == "merchant_payout_batch", "Planner lost the merchant payout demo profile")
    require("delay_savings_pct" in plan_data, "Planner lost delay savings output")

    guide = client.get("/api/v1/guide?use_case=fees&lang=curl")
    require(guide.status_code == 200, "Guide endpoint did not load")
    require(
        "/api/v1/fees/plan?profile=merchant_payout_batch&currency=usd" in guide.text,
        "Guide no longer promotes the hosted planner path",
    )

    mcp = client.get("/mcp-setup")
    require(mcp.status_code == 200, "MCP setup page did not load")
    require("plan_transaction" in mcp.text, "MCP setup no longer leads with plan_transaction")
    require("default hosted demo path" in mcp.text.lower(), "MCP setup lost the hosted demo framing")

    x402 = client.get("/api/v1/x402-info")
    require(x402.status_code == 200, "x402 info endpoint did not load")
    require("fees/landscape" in json.dumps(x402.json()), "x402 info no longer references the premium fee lane")

    require(FALLBACK_JSON.exists(), "Fallback JSON asset is missing")
    fallback = json.loads(FALLBACK_JSON.read_text(encoding="utf-8"))
    require(fallback["slug"] == "merchant-payout-batch-march-2026", "Fallback JSON slug mismatch")
    require(fallback["savings"]["percent"] == 76.3, "Fallback JSON savings drifted")

    print("Founder demo rehearsal passed:")
    print("- proof story intact")
    print("- hosted planner intact")
    print("- guide curl example intact")
    print("- MCP setup intact")
    print("- x402 premium finish intact")
    print("- fallback JSON intact")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Founder demo rehearsal failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
