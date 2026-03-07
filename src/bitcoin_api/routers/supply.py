"""Supply endpoints: /supply — circulating supply, inflation, halving schedule."""

from fastapi import APIRouter, Depends

from bitcoinlib_rpc import BitcoinRPC

from ..cache import cached_blockchain_info
from ..dependencies import get_rpc
from ..models import ApiResponse, envelope

router = APIRouter(prefix="/supply", tags=["Supply"])

INITIAL_SUBSIDY = 50.0  # BTC per block at genesis
HALVING_INTERVAL = 210_000  # blocks between halvings
TOTAL_SUPPLY = 21_000_000.0  # hard cap

_SUPPLY_EXAMPLE = {
    200: {
        "description": "Bitcoin supply breakdown with halving and inflation data",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "circulating_supply_btc": 19828125.0,
                        "total_possible_btc": 21000000,
                        "percent_mined": 94.4196,
                        "current_block_subsidy_btc": 3.125,
                        "halvings_completed": 4,
                        "next_halving_height": 1050000,
                        "blocks_until_halving": 110538,
                        "annual_inflation_rate_pct": 0.8281,
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


def _circulating_supply(height: int) -> float:
    """Calculate circulating supply from block height using the halving schedule."""
    supply = 0.0
    subsidy = INITIAL_SUBSIDY
    remaining = height

    while remaining > 0 and subsidy > 0:
        era_blocks = min(remaining, HALVING_INTERVAL)
        supply += era_blocks * subsidy
        remaining -= era_blocks
        subsidy /= 2

    return supply


@router.get("", response_model=ApiResponse[dict], responses=_SUPPLY_EXAMPLE)
def supply_summary(rpc: BitcoinRPC = Depends(get_rpc)):
    """Bitcoin supply breakdown: circulating supply, inflation rate, halving countdown.

    Pure math from block height — uses the deterministic halving schedule.
    """
    info = cached_blockchain_info(rpc)
    height = info["blocks"]

    halvings_completed = height // HALVING_INTERVAL
    current_subsidy = INITIAL_SUBSIDY / (2 ** halvings_completed)
    circulating = _circulating_supply(height)
    next_halving_height = (halvings_completed + 1) * HALVING_INTERVAL
    blocks_until_halving = next_halving_height - height

    # ~144 blocks/day * 365.25 days/year
    annual_new_supply = current_subsidy * 6 * 24 * 365.25
    annual_inflation_rate = (annual_new_supply / circulating) * 100 if circulating > 0 else 0.0

    data = {
        "circulating_supply_btc": round(circulating, 8),
        "total_possible_btc": TOTAL_SUPPLY,
        "percent_mined": round((circulating / TOTAL_SUPPLY) * 100, 4),
        "current_block_subsidy_btc": current_subsidy,
        "halvings_completed": halvings_completed,
        "next_halving_height": next_halving_height,
        "blocks_until_halving": blocks_until_halving,
        "annual_inflation_rate_pct": round(annual_inflation_rate, 4),
    }
    return envelope(data, height=height, chain=info["chain"])
