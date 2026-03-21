"""x402 payment analytics endpoint."""

from fastapi import APIRouter

from ..db import get_x402_stats

router = APIRouter(tags=["x402"])


@router.get(
    "/x402-stats",
    summary="x402 payment analytics",
    description="Aggregated statistics for x402 stablecoin micropayments.",
)
def x402_stats():
    return get_x402_stats()
