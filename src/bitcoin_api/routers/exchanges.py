"""Exchange fee comparison: /tools/exchange-compare — net BTC after fees."""

import logging
import time
import threading

from fastapi import APIRouter, Query

from ..models import ApiResponse, envelope

router = APIRouter(prefix="/tools", tags=["Tools"])

log = logging.getLogger("bitcoin_api.exchanges")

# ---------------------------------------------------------------------------
# Fee schedules (updated periodically — these change infrequently)
# ---------------------------------------------------------------------------
# Each exchange entry contains:
#   - trading_fee_pct: percentage fee on trade amount
#   - spread_pct: typical bid-ask spread markup
#   - withdrawal_fee_sats: flat withdrawal fee in satoshis (on-chain)
#   - min_usd: minimum purchase amount (0 = no minimum)
#   - notes: human-readable caveats
#   - last_updated: when fee data was last verified
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
# BTC price cache (reuse pattern from prices.py)
# ---------------------------------------------------------------------------

_btc_price_usd: float | None = None
_btc_price_time: float = 0
_btc_price_lock = threading.Lock()
_PRICE_TTL = 60  # seconds


def _fetch_btc_price() -> float | None:
    """Fetch current BTC/USD price from CoinGecko."""
    import urllib.request
    import json

    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    req = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "SatoshiAPI/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data["bitcoin"]["usd"]
    except Exception as e:
        log.warning("Failed to fetch BTC price for exchange comparison: %s", e)
        return None


def _get_btc_price() -> float | None:
    """Return cached BTC/USD price or fetch fresh."""
    global _btc_price_usd, _btc_price_time
    with _btc_price_lock:
        if _btc_price_usd is not None and (time.time() - _btc_price_time) < _PRICE_TTL:
            return _btc_price_usd
    price = _fetch_btc_price()
    if price is not None:
        with _btc_price_lock:
            _btc_price_usd = price
            _btc_price_time = time.time()
    else:
        with _btc_price_lock:
            return _btc_price_usd  # stale is better than None
    return price


def _calculate_net_btc(amount_usd: float, exchange: dict, btc_price: float) -> dict:
    """Calculate net BTC received after all fees for a given exchange."""
    trading_fee = amount_usd * (exchange["trading_fee_pct"] / 100)
    spread_cost = amount_usd * (exchange["spread_pct"] / 100)
    effective_usd = amount_usd - trading_fee - spread_cost

    gross_btc = effective_usd / btc_price
    gross_sats = int(gross_btc * 1e8)

    withdrawal_fee_sats = exchange["withdrawal_fee_sats"]
    net_sats = max(0, gross_sats - withdrawal_fee_sats)
    net_btc = net_sats / 1e8

    total_fee_usd = trading_fee + spread_cost + (withdrawal_fee_sats / 1e8 * btc_price)
    total_fee_pct = (total_fee_usd / amount_usd * 100) if amount_usd > 0 else 0

    return {
        "exchange": exchange["name"],
        "amount_usd": amount_usd,
        "trading_fee_usd": round(trading_fee, 2),
        "spread_cost_usd": round(spread_cost, 2),
        "withdrawal_fee_sats": withdrawal_fee_sats,
        "withdrawal_fee_usd": round(withdrawal_fee_sats / 1e8 * btc_price, 2),
        "total_fee_usd": round(total_fee_usd, 2),
        "total_fee_pct": round(total_fee_pct, 2),
        "gross_sats": gross_sats,
        "net_sats": net_sats,
        "net_btc": round(net_btc, 8),
        "notes": exchange["notes"],
        "last_updated": exchange["last_updated"],
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
    btc_price = _get_btc_price()
    if btc_price is None:
        return envelope(
            {"error": "BTC price temporarily unavailable. Try again shortly."}
        )

    results = []
    for key, exchange in EXCHANGE_FEES.items():
        if amount_usd < exchange["min_usd"]:
            continue
        results.append(_calculate_net_btc(amount_usd, exchange, btc_price))

    # Sort by net sats descending (best deal first)
    results.sort(key=lambda x: x["net_sats"], reverse=True)

    best = results[0]["exchange"] if results else None

    return envelope(
        {
            "amount_usd": amount_usd,
            "btc_price_usd": btc_price,
            "exchanges": results,
            "best_value": best,
        }
    )
