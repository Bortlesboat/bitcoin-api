"""Price endpoint: /prices, /market-data — BTC price from external APIs."""

import time
import logging
import threading

from fastapi import APIRouter, Depends, HTTPException

from bitcoinlib_rpc import BitcoinRPC

from ..cache import cached_fee_estimates, cached_mempool_info, get_market_data
from ..dependencies import get_rpc
from ..models import ApiResponse, envelope, rpc_envelope

router = APIRouter(tags=["Prices"])

log = logging.getLogger("bitcoin_api.prices")

# Simple TTL cache for price data (refresh every 60 seconds)
_price_cache: dict | None = None
_price_cache_time: float = 0
_price_cache_lock = threading.Lock()
_PRICE_TTL = 60  # seconds


def _fetch_price() -> dict:
    """Fetch BTC price from CoinGecko (free, no API key required)."""
    import urllib.request
    import json

    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,eur,gbp,jpy,cad,aud&include_24hr_change=true"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "SatoshiAPI/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read(65536).decode())
    btc = data.get("bitcoin", {})
    return {
        "USD": btc.get("usd"),
        "EUR": btc.get("eur"),
        "GBP": btc.get("gbp"),
        "JPY": btc.get("jpy"),
        "CAD": btc.get("cad"),
        "AUD": btc.get("aud"),
        "change_24h_pct": btc.get("usd_24h_change"),
    }


def _get_cached_price() -> dict:
    """Return cached price or fetch fresh data."""
    global _price_cache, _price_cache_time
    with _price_cache_lock:
        if _price_cache is not None and (time.time() - _price_cache_time) < _PRICE_TTL:
            return _price_cache
    try:
        price = _fetch_price()
        with _price_cache_lock:
            _price_cache = price
            _price_cache_time = time.time()
        return price
    except Exception as e:
        log.warning("Failed to fetch BTC price: %s", e)
        with _price_cache_lock:
            if _price_cache is not None:
                return _price_cache
        raise HTTPException(status_code=503, detail="BTC price service temporarily unavailable")


_PRICES_EXAMPLE = {
    200: {
        "description": "Current BTC price in multiple currencies",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "USD": 92150.0,
                        "EUR": 84500.0,
                        "GBP": 72300.0,
                        "JPY": 13850000.0,
                        "CAD": 126500.0,
                        "AUD": 141200.0,
                        "change_24h_pct": 2.35,
                    },
                    "meta": {"source": "coingecko"},
                }
            }
        },
    }
}


@router.get("/prices", response_model=ApiResponse[dict], responses=_PRICES_EXAMPLE)
def get_prices():
    """Current BTC price in USD, EUR, GBP, JPY, CAD, AUD with 24h change. Cached for 60s. Data provided by CoinGecko."""
    price = {**_get_cached_price(), "attribution": "Price data provided by CoinGecko (https://www.coingecko.com)"}
    return envelope(price)


_MARKET_DATA_EXAMPLE = {
    200: {
        "description": "Combined BTC market data: price, mempool, and fee estimates in a single call",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "price": {"USD": 92150.0, "change_24h_pct": 2.35},
                        "mempool": {"size": 14832, "bytes": 7482910, "total_fee": 1.28},
                        "fees": {
                            "estimates": {"1": 25.0, "3": 18.0, "6": 12.0, "25": 8.0, "144": 5.0},
                        },
                    },
                    "meta": {"node_height": 939462, "chain": "main"},
                }
            }
        },
    }
}


@router.get("/market-data", response_model=ApiResponse[dict], responses=_MARKET_DATA_EXAMPLE)
def get_market_data_endpoint(rpc: BitcoinRPC = Depends(get_rpc)):
    """Pre-computed BTC market snapshot: price, mempool info, and fee estimates.

    Designed for trading bots and 15-minute window strategies. A background thread
    refreshes this data every 5 seconds, so this endpoint returns instantly (<1ms)
    with no RPC calls or external API hits on the request path.

    For even lower latency, subscribe to the `market_data` WebSocket channel
    at /api/v1/ws — data is pushed every 5 seconds with zero HTTP overhead.

    Falls back to live assembly if the background ticker hasn't started yet.
    """
    # Fast path: serve pre-computed bundle from background ticker
    bundle, age = get_market_data()
    if bundle is not None and age < 15:
        return rpc_envelope(bundle, rpc)

    # Fallback: assemble live (cold start or ticker crashed)
    price_data = {}
    try:
        price_data = _get_cached_price()
    except HTTPException:
        pass

    mempool_data = {}
    try:
        mempool_data = cached_mempool_info(rpc)
    except Exception:
        pass

    fee_data = {}
    try:
        estimates = cached_fee_estimates(rpc)
        fee_data = {"estimates": {e.conf_target: e.fee_rate_sat_vb for e in estimates}}
    except Exception:
        pass

    return rpc_envelope(
        {"price": price_data, "mempool": mempool_data, "fees": fee_data},
        rpc,
    )
