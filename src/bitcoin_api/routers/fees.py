"""Fee endpoints: /fees, /fees/recommended, /fees/mempool-blocks, /fees/landscape, /fees/estimate-tx, /fees/history, /fees/{target}."""

from fastapi import APIRouter, Depends, Path, Query

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.utils import fee_recommendation

from ..cache import cached_blockchain_info, cached_fee_estimates, get_mempool_snapshots
from ..db import get_fee_history
from ..dependencies import get_rpc
from ..models import ApiResponse, FeeEstimateData, FeeRecommendationData, envelope

# Max block weight (4 million weight units)
_MAX_BLOCK_WEIGHT = 4_000_000

router = APIRouter(prefix="/fees", tags=["Fees"])

_FEES_EXAMPLE = {
    200: {
        "description": "Fee estimates for standard targets",
        "content": {
            "application/json": {
                "example": {
                    "data": [
                        {"conf_target": 1, "fee_rate_btc_kvb": 0.00025, "fee_rate_sat_vb": 25.0},
                        {"conf_target": 6, "fee_rate_btc_kvb": 0.00012, "fee_rate_sat_vb": 12.0},
                        {"conf_target": 144, "fee_rate_btc_kvb": 0.00005, "fee_rate_sat_vb": 5.0},
                    ],
                    "meta": {
                        "timestamp": "2026-03-05T12:00:00+00:00",
                        "node_height": 939462,
                        "chain": "main",
                    },
                }
            }
        },
    }
}


@router.get("", response_model=ApiResponse[list[FeeEstimateData]], responses=_FEES_EXAMPLE)
def fees(rpc: BitcoinRPC = Depends(get_rpc)):
    """Fee estimates for standard confirmation targets (1, 3, 6, 25, 144 blocks)."""
    estimates = cached_fee_estimates(rpc)
    info = cached_blockchain_info(rpc)
    return envelope(
        [e.model_dump() for e in estimates],
        height=info["blocks"],
        chain=info["chain"],
    )


_FEES_RECOMMENDED_EXAMPLE = {
    200: {
        "description": "Human-readable fee recommendation with all estimates",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "recommendation": "Fees are moderate. For next-block confirmation use 25 sat/vB. If you can wait 1 hour, 12 sat/vB should suffice.",
                        "estimates": {
                            "1": 25.0,
                            "3": 18.0,
                            "6": 12.0,
                            "25": 8.0,
                            "144": 5.0,
                        },
                    },
                    "meta": {
                        "timestamp": "2026-03-05T12:00:00+00:00",
                        "node_height": 939462,
                        "chain": "main",
                    },
                }
            }
        },
    }
}

_FEE_TARGET_EXAMPLE = {
    200: {
        "description": "Fee estimate for a specific confirmation target",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "conf_target": 6,
                        "fee_rate_btc_kvb": 0.00012,
                        "fee_rate_sat_vb": 12.0,
                        "errors": [],
                    },
                    "meta": {
                        "timestamp": "2026-03-05T12:00:00+00:00",
                        "node_height": 939462,
                        "chain": "main",
                    },
                }
            }
        },
    }
}


@router.get("/recommended", response_model=ApiResponse[FeeRecommendationData], responses=_FEES_RECOMMENDED_EXAMPLE)
def fees_recommended(rpc: BitcoinRPC = Depends(get_rpc)):
    """Human-readable fee recommendation."""
    estimates = cached_fee_estimates(rpc)
    fee_dict = {e.conf_target: e.fee_rate_sat_vb for e in estimates}
    recommendation = fee_recommendation(fee_dict)
    info = cached_blockchain_info(rpc)
    return envelope(
        {
            "recommendation": recommendation,
            "estimates": {e.conf_target: e.fee_rate_sat_vb for e in estimates},
        },
        height=info["blocks"],
        chain=info["chain"],
    )


_MEMPOOL_BLOCKS_EXAMPLE = {
    200: {
        "description": "Projected next blocks from mempool, grouped by fee rate",
        "content": {
            "application/json": {
                "example": {
                    "data": [
                        {
                            "block_index": 0,
                            "min_fee_rate": 15.0,
                            "max_fee_rate": 250.0,
                            "median_fee_rate": 25.0,
                            "tx_count": 2800,
                            "total_weight": 3990000,
                            "total_fees_sat": 8500000,
                        },
                    ],
                    "meta": {"node_height": 881234, "chain": "main"},
                }
            }
        },
    }
}


@router.get("/mempool-blocks", response_model=ApiResponse[list[dict]], responses=_MEMPOOL_BLOCKS_EXAMPLE)
def fees_mempool_blocks(rpc: BitcoinRPC = Depends(get_rpc)):
    """Project the next N blocks from the current mempool, sorted by fee rate descending."""
    raw = rpc.call("getrawmempool", True)
    info = cached_blockchain_info(rpc)

    # Build list of (fee_rate, weight, fee_sat) per tx
    txs = []
    for txid, entry in raw.items():
        fee_sat = entry.get("fees", {}).get("base", 0) * 1e8
        weight = entry.get("weight", entry.get("vsize", 0) * 4)
        if weight > 0:
            fee_rate = fee_sat / (weight / 4)  # sat/vB
            txs.append((fee_rate, weight, fee_sat))

    # Sort by fee rate descending (miners pick highest first)
    txs.sort(key=lambda x: x[0], reverse=True)

    blocks = []
    block_weight = 0
    block_txs = []

    for fee_rate, weight, fee_sat in txs:
        if block_weight + weight > _MAX_BLOCK_WEIGHT:
            # Finalize current block
            if block_txs:
                rates = [t[0] for t in block_txs]
                blocks.append({
                    "block_index": len(blocks),
                    "min_fee_rate": round(min(rates), 2),
                    "max_fee_rate": round(max(rates), 2),
                    "median_fee_rate": round(sorted(rates)[len(rates) // 2], 2),
                    "tx_count": len(block_txs),
                    "total_weight": block_weight,
                    "total_fees_sat": round(sum(t[2] for t in block_txs)),
                })
            block_weight = 0
            block_txs = []
            if len(blocks) >= 8:
                break
        block_weight += weight
        block_txs.append((fee_rate, weight, fee_sat))

    # Don't forget the last partial block
    if block_txs and len(blocks) < 8:
        rates = [t[0] for t in block_txs]
        blocks.append({
            "block_index": len(blocks),
            "min_fee_rate": round(min(rates), 2),
            "max_fee_rate": round(max(rates), 2),
            "median_fee_rate": round(sorted(rates)[len(rates) // 2], 2),
            "tx_count": len(block_txs),
            "total_weight": block_weight,
            "total_fees_sat": round(sum(t[2] for t in block_txs)),
        })

    return envelope(blocks, height=info["blocks"], chain=info["chain"])


# --- Transaction size/weight constants by script type ---
_TX_OVERHEAD = 10.5  # version(4) + marker(0.25) + flag(0.25) + locktime(4) + vin_count(1) + vout_count(1)
_INPUT_WEIGHTS = {
    "p2pkh": 592,     # 148 bytes * 4
    "p2wpkh": 272,    # 68 vB * 4 (41 non-witness + 27 witness weight)
    "p2sh": 700,      # ~175 bytes * 4 (varies with script)
    "p2wsh": 400,     # ~100 vB * 4
    "p2tr": 230,      # ~57.5 vB * 4 (key-path spend)
}
_OUTPUT_WEIGHTS = {
    "p2pkh": 136,     # 34 bytes * 4
    "p2wpkh": 124,    # 31 bytes * 4
    "p2sh": 128,      # 32 bytes * 4
    "p2wsh": 172,     # 43 bytes * 4
    "p2tr": 172,      # 43 bytes * 4
}


@router.get("/landscape")
def fees_landscape(rpc: BitcoinRPC = Depends(get_rpc)):
    """Should I send now or wait? Fee landscape with trend analysis and actionable recommendation."""
    estimates = cached_fee_estimates(rpc)
    info = cached_blockchain_info(rpc)
    fee_dict = {e.conf_target: e.fee_rate_sat_vb for e in estimates}
    next_block = fee_dict.get(1, 0)
    six_block = fee_dict.get(6, 0)
    day_fee = fee_dict.get(144, 0)

    # Trend analysis from snapshot buffer
    snapshots = get_mempool_snapshots()
    trend = "unknown"
    trend_pct = 0.0
    if len(snapshots) >= 2:
        oldest = snapshots[0]
        newest = snapshots[-1]
        old_size = oldest.get("mempool_bytes", 0)
        new_size = newest.get("mempool_bytes", 0)
        if old_size > 0:
            trend_pct = round(((new_size - old_size) / old_size) * 100, 1)
        if trend_pct > 5:
            trend = "rising"
        elif trend_pct < -5:
            trend = "falling"
        else:
            trend = "stable"

    # Decision logic
    typical_vsize = 140  # P2WPKH 1-in-2-out
    if next_block <= 5:
        recommendation = "send"
        confidence = "high"
        reasoning = f"Fees are very low at {next_block} sat/vB. Great time to send."
    elif next_block <= 20:
        if trend == "falling":
            recommendation = "send"
            confidence = "medium"
            reasoning = f"Fees are moderate at {next_block} sat/vB and falling ({trend_pct}%). Good time to send."
        else:
            recommendation = "send"
            confidence = "medium"
            reasoning = f"Fees are moderate at {next_block} sat/vB. Acceptable to send now."
    elif next_block <= 50:
        if trend == "falling":
            recommendation = "send"
            confidence = "medium"
            reasoning = (
                f"Fees are elevated at {next_block} sat/vB but mempool is draining ({trend_pct}%). "
                f"Waiting could save ~{round((1 - day_fee / next_block) * 100)}% if you can wait."
            )
        else:
            recommendation = "wait"
            confidence = "medium"
            savings_pct = round((1 - day_fee / next_block) * 100) if next_block > 0 else 0
            reasoning = (
                f"Fees are elevated at {next_block} sat/vB. "
                f"Waiting for low-priority could save ~{savings_pct}%."
            )
    else:
        recommendation = "urgent_only"
        confidence = "high"
        savings_pct = round((1 - day_fee / next_block) * 100) if next_block > 0 else 0
        reasoning = (
            f"Fees are high at {next_block} sat/vB. Only send if urgent. "
            f"Waiting could save ~{savings_pct}%."
        )

    scenarios = {
        "send_now": {
            "fee_rate": next_block,
            "total_sats": round(next_block * typical_vsize),
            "total_btc": round(next_block * typical_vsize / 1e8, 8),
            "target": "next block",
        },
        "wait_1hr": {
            "fee_rate": six_block,
            "total_sats": round(six_block * typical_vsize),
            "total_btc": round(six_block * typical_vsize / 1e8, 8),
            "target": "~6 blocks (~1 hour)",
        },
        "wait_low": {
            "fee_rate": day_fee,
            "total_sats": round(day_fee * typical_vsize),
            "total_btc": round(day_fee * typical_vsize / 1e8, 8),
            "target": "~144 blocks (~1 day)",
        },
    }
    if next_block > 0 and day_fee > 0:
        scenarios["wait_low"]["savings_vs_now_pct"] = round((1 - day_fee / next_block) * 100, 1)
    if next_block > 0 and six_block > 0:
        scenarios["wait_1hr"]["savings_vs_now_pct"] = round((1 - six_block / next_block) * 100, 1)

    return envelope(
        {
            "recommendation": recommendation,
            "confidence": confidence,
            "reasoning": reasoning,
            "trend": {
                "direction": trend,
                "mempool_change_pct": trend_pct,
                "snapshots_available": len(snapshots),
            },
            "current_fees": {
                "next_block": next_block,
                "six_blocks": six_block,
                "one_day": day_fee,
            },
            "scenarios": scenarios,
        },
        height=info["blocks"],
        chain=info["chain"],
    )


@router.get("/estimate-tx")
def fees_estimate_tx(
    rpc: BitcoinRPC = Depends(get_rpc),
    inputs: int = Query(default=1, ge=1, le=100, description="Number of inputs"),
    outputs: int = Query(default=2, ge=1, le=100, description="Number of outputs"),
    input_type: str = Query(default="p2wpkh", description="Input script type (p2pkh, p2wpkh, p2sh, p2wsh, p2tr)"),
    output_type: str = Query(default="p2wpkh", description="Output script type (p2pkh, p2wpkh, p2sh, p2wsh, p2tr)"),
):
    """Estimate transaction size and fee cost without building a transaction."""
    estimates = cached_fee_estimates(rpc)
    info = cached_blockchain_info(rpc)

    in_weight = _INPUT_WEIGHTS.get(input_type, _INPUT_WEIGHTS["p2wpkh"])
    out_weight = _OUTPUT_WEIGHTS.get(output_type, _OUTPUT_WEIGHTS["p2wpkh"])

    total_weight = round(_TX_OVERHEAD * 4) + (inputs * in_weight) + (outputs * out_weight)
    estimated_vsize = (total_weight + 3) // 4  # ceil division

    fee_dict = {e.conf_target: e.fee_rate_sat_vb for e in estimates}
    targets = {
        "next_block": (1, "~10 min"),
        "3_blocks": (3, "~30 min"),
        "6_blocks": (6, "~1 hour"),
        "1_day": (144, "~1 day"),
    }
    fee_scenarios = {}
    for label, (target, desc) in targets.items():
        rate = fee_dict.get(target, 0)
        total_sats = round(rate * estimated_vsize)
        fee_scenarios[label] = {
            "fee_rate_sat_vb": rate,
            "total_fee_sats": total_sats,
            "total_fee_btc": round(total_sats / 1e8, 8),
            "conf_target": target,
            "estimated_time": desc,
        }

    return envelope(
        {
            "estimated_vsize": estimated_vsize,
            "estimated_weight": total_weight,
            "inputs": inputs,
            "outputs": outputs,
            "input_type": input_type,
            "output_type": output_type,
            "breakdown": {
                "overhead_weight": round(_TX_OVERHEAD * 4),
                "per_input_weight": in_weight,
                "per_output_weight": out_weight,
                "total_input_weight": inputs * in_weight,
                "total_output_weight": outputs * out_weight,
            },
            "fee_scenarios": fee_scenarios,
        },
        height=info["blocks"],
        chain=info["chain"],
    )


@router.get("/history")
def fees_history(
    hours: int = Query(default=24, ge=1, le=720, description="Hours of history to return"),
    interval: str = Query(default="10m", description="Interval (e.g. 5m, 10m, 30m, 1h)"),
):
    """Historical fee rates and mempool size. Returns time-series data with summary stats."""
    # Parse interval
    interval_str = interval.lower().strip()
    if interval_str.endswith("h"):
        interval_minutes = int(interval_str[:-1]) * 60
    elif interval_str.endswith("m"):
        interval_minutes = int(interval_str[:-1])
    else:
        interval_minutes = 10

    interval_minutes = max(1, min(interval_minutes, 360))

    rows = get_fee_history(hours=hours, interval_minutes=interval_minutes)

    if not rows:
        return envelope(
            {"datapoints": [], "summary": None, "interval": interval, "hours": hours},
        )

    # Compute summary
    fees = [r["next_block_fee"] for r in rows if r.get("next_block_fee")]
    if fees:
        min_fee = min(fees)
        max_fee = max(fees)
        avg_fee = round(sum(fees) / len(fees), 2)
        # Find cheapest hour
        cheapest_row = min(rows, key=lambda r: r.get("next_block_fee") or float("inf"))
        cheapest_ts = cheapest_row.get("ts")
    else:
        min_fee = max_fee = avg_fee = 0
        cheapest_ts = None

    summary = {
        "min_next_block_fee": min_fee,
        "max_next_block_fee": max_fee,
        "avg_next_block_fee": avg_fee,
        "cheapest_time_utc": cheapest_ts,
        "datapoints_count": len(rows),
    }

    return envelope(
        {"datapoints": rows, "summary": summary, "interval": interval, "hours": hours},
    )


@router.get("/{target}", response_model=ApiResponse[FeeEstimateData], responses=_FEE_TARGET_EXAMPLE)
def fee_for_target(
    target: int = Path(description="Confirmation target in blocks", ge=1, le=1008),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Fee estimate for a specific confirmation target."""
    result = rpc.call("estimatesmartfee", target)
    info = cached_blockchain_info(rpc)

    fee_rate_btc_kvb = result.get("feerate", 0)
    fee_rate_sat_vb = fee_rate_btc_kvb * 100_000 if fee_rate_btc_kvb else 0

    return envelope(
        {
            "conf_target": target,
            "fee_rate_btc_kvb": fee_rate_btc_kvb,
            "fee_rate_sat_vb": round(fee_rate_sat_vb, 2),
            "errors": result.get("errors", []),
        },
        height=info["blocks"],
        chain=info["chain"],
    )
