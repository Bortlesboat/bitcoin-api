"""Exchange fee comparison: /tools/exchange-compare — net BTC after fees."""

from fastapi import APIRouter, Query

from ..models import ApiResponse, envelope
from ..services.exchanges import get_cached_price, rank_exchanges

router = APIRouter(prefix="/tools", tags=["Tools"])

# ---------------------------------------------------------------------------
# Fee schedules (updated periodically — these change infrequently)
# ---------------------------------------------------------------------------

EXCHANGE_FEES = {
    "coinbase": {
        "name": "Coinbase",
        "trading_fee_pct": 0.60,
        "spread_pct": 0.50,
        "withdrawal_fee_sats": 0,
        "min_usd": 1,
        "notes": "Fees vary by payment method; shown is debit card rate. Coinbase Advanced: 0.08% maker / 0.12% taker.",
        "last_updated": "2026-03-06",
    },
    "coinbase_advanced": {
        "name": "Coinbase Advanced",
        "trading_fee_pct": 0.12,
        "spread_pct": 0.0,
        "withdrawal_fee_sats": 0,
        "min_usd": 1,
        "notes": "Taker fee for <$10K monthly volume. No spread — uses order book.",
        "last_updated": "2026-03-06",
    },
    "kraken": {
        "name": "Kraken",
        "trading_fee_pct": 0.26,
        "spread_pct": 0.0,
        "withdrawal_fee_sats": 10000,
        "min_usd": 10,
        "notes": "Taker fee for <$50K monthly volume. Pro interface. Withdrawal fee ~0.0001 BTC.",
        "last_updated": "2026-03-06",
    },
    "river": {
        "name": "River",
        "trading_fee_pct": 0.0,
        "spread_pct": 1.50,
        "withdrawal_fee_sats": 0,
        "min_usd": 10,
        "notes": "Zero explicit fee; revenue from spread. Auto-DCA friendly. Free withdrawals.",
        "last_updated": "2026-03-06",
    },
    "strike": {
        "name": "Strike",
        "trading_fee_pct": 0.0,
        "spread_pct": 0.99,
        "withdrawal_fee_sats": 0,
        "min_usd": 1,
        "notes": "No trading fee; revenue from spread (~0.99%). Lightning withdrawals free.",
        "last_updated": "2026-03-06",
    },
    "swan": {
        "name": "Swan Bitcoin",
        "trading_fee_pct": 0.99,
        "spread_pct": 0.0,
        "withdrawal_fee_sats": 0,
        "min_usd": 10,
        "notes": "DCA-focused. Fee drops to 0.49% at $50K+ cumulative. Auto-withdrawal to own wallet.",
        "last_updated": "2026-03-06",
    },
    "cash_app": {
        "name": "Cash App",
        "trading_fee_pct": 0.0,
        "spread_pct": 1.50,
        "withdrawal_fee_sats": 0,
        "min_usd": 1,
        "notes": "No explicit fee; spread ~1.5%. Simple UI. Free on-chain withdrawals.",
        "last_updated": "2026-03-06",
    },
    "robinhood": {
        "name": "Robinhood",
        "trading_fee_pct": 0.0,
        "spread_pct": 0.50,
        "withdrawal_fee_sats": 0,
        "min_usd": 1,
        "notes": "No commission; revenue from spread. Crypto withdrawals available.",
        "last_updated": "2026-03-06",
    },
}

# ---------------------------------------------------------------------------
# OpenAPI example
# ---------------------------------------------------------------------------

_EXCHANGE_COMPARE_EXAMPLE = {
    200: {
        "description": "Exchange fee comparison for a given USD amount",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "amount_usd": 100,
                        "btc_price_usd": 92000,
                        "exchanges": [
                            {
                                "exchange": "Strike",
                                "amount_usd": 100,
                                "trading_fee_usd": 0.0,
                                "spread_cost_usd": 0.99,
                                "withdrawal_fee_sats": 0,
                                "withdrawal_fee_usd": 0.0,
                                "total_fee_usd": 0.99,
                                "total_fee_pct": 0.99,
                                "gross_sats": 107620,
                                "net_sats": 107620,
                                "net_btc": 0.00107620,
                                "notes": "No trading fee; revenue from spread (~0.99%). Lightning withdrawals free.",
                                "last_updated": "2026-03-06",
                            }
                        ],
                        "best_value": "Strike",
                    },
                    "meta": {"source": "satoshi-api"},
                }
            }
        },
    }
}


@router.get(
    "/exchange-compare",
    response_model=ApiResponse[dict],
    responses=_EXCHANGE_COMPARE_EXAMPLE,
)
def compare_exchanges(
    amount_usd: float = Query(
        default=100,
        ge=1,
        le=1_000_000,
        description="USD amount to convert to BTC",
    ),
):
    """Compare how much BTC you receive across exchanges after all fees.

    Shows trading fees, spread costs, and withdrawal fees for each exchange,
    then ranks by net sats received in your wallet.
    """
    btc_price = get_cached_price()
    if btc_price is None:
        return envelope(
            {"error": "BTC price temporarily unavailable. Try again shortly."}
        )

    results, best = rank_exchanges(EXCHANGE_FEES, amount_usd, btc_price)

    return envelope(
        {
            "amount_usd": amount_usd,
            "btc_price_usd": btc_price,
            "exchanges": results,
            "best_value": best,
        }
    )
