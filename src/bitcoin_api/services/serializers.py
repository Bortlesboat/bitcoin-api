"""Shared serialization helpers — extracted from routers/blocks.py and routers/mempool.py."""

import math


def serialize_block(data: dict) -> dict:
    """Map bitcoinlib-rpc field names to API field names for block data."""
    if "fee_rate_median" in data:
        data.setdefault("median_fee_rate", data.pop("fee_rate_median"))
    if "total_fee_btc" in data:
        data.setdefault("total_fee", data.pop("total_fee_btc"))
    if data.get("top_fee_txids"):
        data["top_fee_txids"] = [
            {"txid": t[0], "fee_rate": t[1]} if isinstance(t, (list, tuple)) else t
            for t in data["top_fee_txids"]
        ]
    return data


def sanitize_for_json(obj):
    """Replace inf/nan floats that JSON can't serialize."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isinf(obj) or math.isnan(obj)):
        return None
    return obj
