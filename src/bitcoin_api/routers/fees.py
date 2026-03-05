"""Fee endpoints: /fees, /fees/recommended, /fees/{target}."""

from fastapi import APIRouter, Depends, Path

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.fees import get_fee_estimates
from bitcoinlib_rpc.utils import fee_recommendation

from ..dependencies import get_rpc
from ..models import envelope

router = APIRouter(prefix="/fees", tags=["Fees"])


@router.get("")
def fees(rpc: BitcoinRPC = Depends(get_rpc)):
    """Fee estimates for standard confirmation targets (1, 3, 6, 25, 144 blocks)."""
    estimates = get_fee_estimates(rpc)
    info = rpc.call("getblockchaininfo")
    return envelope(
        [e.model_dump() for e in estimates],
        height=info["blocks"],
        chain=info["chain"],
    )


@router.get("/recommended")
def fees_recommended(rpc: BitcoinRPC = Depends(get_rpc)):
    """Human-readable fee recommendation."""
    estimates = get_fee_estimates(rpc)
    fee_dict = {e.conf_target: e.fee_rate_sat_vb for e in estimates}
    recommendation = fee_recommendation(fee_dict)
    info = rpc.call("getblockchaininfo")
    return envelope(
        {
            "recommendation": recommendation,
            "estimates": {e.conf_target: e.fee_rate_sat_vb for e in estimates},
        },
        height=info["blocks"],
        chain=info["chain"],
    )


@router.get("/{target}")
def fee_for_target(
    target: int = Path(description="Confirmation target in blocks", ge=1, le=1008),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Fee estimate for a specific confirmation target."""
    result = rpc.call("estimatesmartfee", target)
    info = rpc.call("getblockchaininfo")

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
