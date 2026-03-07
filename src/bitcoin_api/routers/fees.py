"""Fee endpoints: /fees, /fees/recommended, /fees/mempool-blocks, /fees/{target}."""

from fastapi import APIRouter, Depends, Path

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.utils import fee_recommendation

from ..cache import cached_blockchain_info, cached_fee_estimates
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
