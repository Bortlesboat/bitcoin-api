"""Exchange comparison business logic — extracted from routers/exchanges.py."""

import json
import logging
import threading
import time
import urllib.request

log = logging.getLogger("bitcoin_api.exchanges")

# ---------------------------------------------------------------------------
# BTC price cache (thread-safe)
# ---------------------------------------------------------------------------

_btc_price_usd: float | None = None
_btc_price_time: float = 0
_btc_price_lock = threading.Lock()
_PRICE_TTL = 60  # seconds


def fetch_btc_price() -> float | None:
    """Fetch current BTC/USD price from CoinGecko."""
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


def get_cached_price() -> float | None:
    """Return cached BTC/USD price or fetch fresh."""
    global _btc_price_usd, _btc_price_time
    with _btc_price_lock:
        if _btc_price_usd is not None and (time.time() - _btc_price_time) < _PRICE_TTL:
            return _btc_price_usd
    price = fetch_btc_price()
    if price is not None:
        with _btc_price_lock:
            _btc_price_usd = price
            _btc_price_time = time.time()
    else:
        with _btc_price_lock:
            return _btc_price_usd  # stale is better than None
    return price


def calculate_net_btc(amount_usd: float, exchange: dict, btc_price: float) -> dict:
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
