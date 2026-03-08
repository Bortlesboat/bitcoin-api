"""Fee endpoints: /fees, /fees/recommended, /fees/mempool-blocks, /fees/landscape, /fees/estimate-tx, /fees/history, /fees/{target}."""

from fastapi import APIRouter, Depends, Path, Query

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.utils import fee_recommendation

from ..cache import cached_fee_estimates, cached_raw_mempool, get_mempool_snapshots
from ..db import get_fee_history
from ..dependencies import get_rpc
from ..models import ApiResponse, FeeEstimateData, FeeRecommendationData, envelope, rpc_envelope
from ..services.exchanges import get_cached_price
from ..services.fees import (
    PROFILES,
    analyze_mempool_blocks,
    calculate_fee_landscape,
    estimate_tx_fees,
    plan_transaction,
    simulate_fee_savings,
    summarize_fee_history,
)

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
    return rpc_envelope([e.model_dump() for e in estimates], rpc)


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
    return rpc_envelope(
        {
            "recommendation": recommendation,
            "estimates": {e.conf_target: e.fee_rate_sat_vb for e in estimates},
        },
        rpc,
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
    raw = cached_raw_mempool(rpc)
    blocks = analyze_mempool_blocks(raw)
    return rpc_envelope(blocks, rpc)



@router.get("/landscape", response_model=ApiResponse[dict])
def fees_landscape(rpc: BitcoinRPC = Depends(get_rpc)):
    """Should I send now or wait? Fee landscape with trend analysis and actionable recommendation."""
    estimates = cached_fee_estimates(rpc)
    fee_dict = {e.conf_target: e.fee_rate_sat_vb for e in estimates}
    snapshots = get_mempool_snapshots()
    data = calculate_fee_landscape(fee_dict, snapshots)
    return rpc_envelope(data, rpc)


@router.get("/estimate-tx", response_model=ApiResponse[dict])
def fees_estimate_tx(
    rpc: BitcoinRPC = Depends(get_rpc),
    inputs: int = Query(default=1, ge=1, le=100, description="Number of inputs"),
    outputs: int = Query(default=2, ge=1, le=100, description="Number of outputs"),
    input_type: str = Query(default="p2wpkh", description="Input script type (p2pkh, p2wpkh, p2sh, p2wsh, p2tr)"),
    output_type: str = Query(default="p2wpkh", description="Output script type (p2pkh, p2wpkh, p2sh, p2wsh, p2tr)"),
):
    """Estimate transaction size and fee cost without building a transaction."""
    estimates = cached_fee_estimates(rpc)
    fee_dict = {e.conf_target: e.fee_rate_sat_vb for e in estimates}
    data = estimate_tx_fees(fee_dict, inputs, outputs, input_type, output_type)
    return rpc_envelope(data, rpc)


@router.get("/history", response_model=ApiResponse[dict])
def fees_history(
    hours: int = Query(default=24, ge=1, le=720, description="Hours of history to return"),
    interval: str = Query(default="10m", description="Interval (e.g. 5m, 10m, 30m, 1h)"),
):
    """Historical fee rates and mempool size. Returns time-series data with summary stats."""
    # Parse interval (e.g. "10m", "1h")
    interval_str = interval.lower().strip()
    try:
        if interval_str.endswith("h"):
            interval_minutes = int(interval_str[:-1]) * 60
        elif interval_str.endswith("m"):
            interval_minutes = int(interval_str[:-1])
        else:
            interval_minutes = 10
    except (ValueError, IndexError):
        interval_minutes = 10

    interval_minutes = max(1, min(interval_minutes, 360))

    rows = get_fee_history(hours=hours, interval_minutes=interval_minutes)

    if not rows:
        return envelope(
            {"datapoints": [], "summary": None, "interval": interval, "hours": hours},
        )

    summary = summarize_fee_history(rows)
    return envelope(
        {"datapoints": rows, "summary": summary, "interval": interval, "hours": hours},
    )


@router.get("/plan", response_model=ApiResponse[dict])
def fees_plan(
    rpc: BitcoinRPC = Depends(get_rpc),
    profile: str | None = Query(default=None, description="Preset profile: simple_send, exchange_withdrawal, batch_payout, consolidation"),
    inputs: int | None = Query(default=None, ge=1, le=100, description="Number of inputs (overrides profile)"),
    outputs: int | None = Query(default=None, ge=1, le=100, description="Number of outputs (overrides profile)"),
    address_type: str = Query(default="segwit", description="Address type: segwit, taproot, legacy"),
    currency: str = Query(default="sats", description="Include USD values: sats (default), usd (adds USD fields)"),
):
    """Transaction cost planner — estimate costs across urgency tiers with wait recommendation.

    Call with no params for a standard SegWit transaction, or use a profile preset.
    Add currency=usd to include USD equivalents (requires BTC price from CoinGecko).
    Returns cost at 4 urgency tiers, delay savings %, trend analysis, and historical comparison.
    """
    estimates = cached_fee_estimates(rpc)
    fee_dict = {e.conf_target: e.fee_rate_sat_vb for e in estimates}
    snapshots = get_mempool_snapshots()
    history_rows = get_fee_history(hours=24, interval_minutes=10)
    btc_price = None
    if currency.lower() == "usd":
        btc_price = get_cached_price()
    data = plan_transaction(
        fee_dict, snapshots, history_rows,
        profile=profile, inputs=inputs, outputs=outputs, address_type=address_type,
        btc_price=btc_price,
    )
    if currency.lower() == "usd" and btc_price is None:
        data["currency_note"] = "USD values unavailable — BTC price service temporarily unreachable. Sats and BTC values are still accurate."
    return rpc_envelope(data, rpc)


@router.get("/savings", response_model=ApiResponse[dict])
def fees_savings(
    hours: int = Query(default=168, ge=1, le=720, description="Hours of history to analyze (default: 168 = 7 days)"),
    currency: str = Query(default="sats", description="Include USD values: sats (default), usd (adds USD fields)"),
):
    """Fee savings simulation — how much you'd save with optimal timing.

    Compares average fee cost vs. optimal timing over the requested period.
    Add currency=usd to include USD equivalents. Returns savings per transaction,
    monthly projection, and fee range stats.
    """
    rows = get_fee_history(hours=hours, interval_minutes=5)
    btc_price = None
    if currency.lower() == "usd":
        btc_price = get_cached_price()
    data = simulate_fee_savings(rows, days=hours // 24 if hours >= 24 else None, btc_price=btc_price)
    if currency.lower() == "usd" and btc_price is None:
        data["currency_note"] = "USD values unavailable — BTC price service temporarily unreachable. Sats and BTC values are still accurate."
    return envelope(data)


@router.get("/{target}", response_model=ApiResponse[FeeEstimateData], responses=_FEE_TARGET_EXAMPLE)
def fee_for_target(
    target: int = Path(description="Confirmation target in blocks", ge=1, le=1008),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Fee estimate for a specific confirmation target."""
    result = rpc.call("estimatesmartfee", target)

    fee_rate_btc_kvb = result.get("feerate", 0)
    fee_rate_sat_vb = fee_rate_btc_kvb * 100_000 if fee_rate_btc_kvb else 0

    return rpc_envelope(
        {
            "conf_target": target,
            "fee_rate_btc_kvb": fee_rate_btc_kvb,
            "fee_rate_sat_vb": round(fee_rate_sat_vb, 2),
            "errors": result.get("errors", []),
        },
        rpc,
    )
