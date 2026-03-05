"""Fee endpoints: /fees, /fees/recommended, /fees/{target}."""

from fastapi import APIRouter, Depends, Path

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.utils import fee_recommendation

from ..cache import cached_blockchain_info, cached_fee_estimates
from ..dependencies import get_rpc
from ..models import envelope

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


@router.get("", responses=_FEES_EXAMPLE)
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


@router.get("/recommended", responses=_FEES_RECOMMENDED_EXAMPLE)
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


@router.get("/{target}", responses=_FEE_TARGET_EXAMPLE)
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
