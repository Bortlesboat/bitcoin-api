"""Exchange comparison business logic — extracted from routers/exchanges.py.

BTC/USD price fetching is delegated to services.price (multi-provider fallback).
This module re-exports get_cached_price for backwards compatibility.
"""

import logging

from .price import get_cached_price  # noqa: F401 — re-exported for consumers

log = logging.getLogger("bitcoin_api.exchanges")


def calculate_net_btc(amount_usd: float, exchange: dict, btc_price: float) -> dict:
    """Calculate net BTC received after all fees for a given exchange."""
    trading_fee = amount_usd * (exchange["trading_fee_pct"] / 100)
    spread_cost = amount_usd * (exchange["spread_pct"] / 100)
    effective_usd = amount_usd - trading_fee - spread_cost

    gross_btc = effective_usd / btc_price
    gross_sats = round(gross_btc * 1e8)

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


def rank_exchanges(exchange_fees: dict, amount_usd: float, btc_price: float) -> tuple[list[dict], str | None]:
    """Compare exchanges and rank by net sats received.

    Args:
        exchange_fees: dict of exchange_key -> exchange data
        amount_usd: USD amount to convert
        btc_price: current BTC/USD price

    Returns:
        (sorted results list, best exchange name or None)
    """
    results = []
    for key, exchange in exchange_fees.items():
        if amount_usd < exchange["min_usd"]:
            continue
        results.append(calculate_net_btc(amount_usd, exchange, btc_price))

    results.sort(key=lambda x: x["net_sats"], reverse=True)
    best = results[0]["exchange"] if results else None
    return results, best
