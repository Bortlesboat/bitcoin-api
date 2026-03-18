"""BTC/USD price service — multi-provider with fallback chain.

Architecture:
    Providers are tried in order until one succeeds. The result is cached
    for 60 seconds. If all providers fail, the last successful price is
    returned (stale-is-better-than-nothing). If no price has ever been
    fetched, returns None.

Providers (in order):
    1. Binance     — api.binance.com (free, no key, 1200 req/min)
    2. CoinGecko   — api.coingecko.com (free, no key)
    3. Coinbase     — api.coinbase.com (free, no key)
    4. Kraken       — api.kraken.com (free, no key)

Adding a new provider:
    1. Write a function: def _fetch_from_xxx() -> float | None
    2. Add it to the _PROVIDERS list
    3. That's it — the fallback chain picks it up automatically

Consumers:
    - services/exchanges.py  (exchange comparison)
    - routers/fees.py        (currency=usd on /fees/plan and /fees/savings)
    - routers/prices.py      (has its own cache — could be migrated here later)

Note: Bitcoin nodes have no concept of fiat prices. This data comes
entirely from external exchange APIs. The fee endpoints work without
it — USD fields are simply omitted when price is unavailable.
"""

import json
import logging
import threading
import time
import urllib.request

log = logging.getLogger("bitcoin_api.price")

# ---------------------------------------------------------------------------
# Async price fetching (httpx) — preferred path when called from async context
# ---------------------------------------------------------------------------

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False
    log.info("httpx not installed — async price fetching unavailable, using sync urllib fallback")

_HEADERS = {"Accept": "application/json", "User-Agent": "SatoshiAPI/1.0"}

# Shared async client (reuses connections). Created lazily on first async call.
_async_client: "httpx.AsyncClient | None" = None
_async_client_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Cache (thread-safe)
# ---------------------------------------------------------------------------

_price_usd: float | None = None
_price_time: float = 0
_price_source: str | None = None
_price_lock = threading.Lock()
_PRICE_TTL = 10  # seconds — reduced for 15-min trading strategy freshness


# ---------------------------------------------------------------------------
# Providers — each returns float | None, never raises
# ---------------------------------------------------------------------------

def _fetch_from_binance() -> float | None:
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "SatoshiAPI/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read(65536).decode())
        return float(data["price"])
    except Exception:
        return None


def _fetch_from_coingecko() -> float | None:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "SatoshiAPI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read(65536).decode())
        return data["bitcoin"]["usd"]
    except Exception:
        return None


def _fetch_from_coinbase() -> float | None:
    url = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "SatoshiAPI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read(65536).decode())
        return float(data["data"]["amount"])
    except Exception:
        return None


def _fetch_from_kraken() -> float | None:
    url = "https://api.kraken.com/0/public/Ticker?pair=XBTUSD"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "SatoshiAPI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read(65536).decode())
        # Kraken returns last trade price as first element of "c" array
        return float(data["result"]["XXBTZUSD"]["c"][0])
    except Exception:
        return None


# Ordered fallback chain — first success wins
_PROVIDERS = [
    ("binance", _fetch_from_binance),
    ("coingecko", _fetch_from_coingecko),
    ("coinbase", _fetch_from_coinbase),
    ("kraken", _fetch_from_kraken),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_btc_price() -> tuple[float | None, str | None]:
    """Try each provider in order, return (price, source_name) on first success.

    Returns (None, None) if all providers fail.
    """
    for name, fetcher in _PROVIDERS:
        price = fetcher()
        if price is not None and 0 < price < 10_000_000:
            return price, name
    return None, None


def get_cached_price() -> float | None:
    """Return cached BTC/USD price, fetching fresh if TTL expired.

    Fallback behavior:
        - Cache hit (< 60s old): return cached price
        - Cache miss: try all providers in order
        - All providers fail: return last known price (stale)
        - No price ever fetched: return None
    """
    global _price_usd, _price_time, _price_source
    with _price_lock:
        if _price_usd is not None and (time.time() - _price_time) < _PRICE_TTL:
            return _price_usd

    price, source = fetch_btc_price()
    if price is not None:
        with _price_lock:
            _price_usd = price
            _price_time = time.time()
            _price_source = source
        log.debug("BTC price updated: $%.2f via %s", price, source)
        return price

    # All providers failed — return stale price if we have one
    with _price_lock:
        if _price_usd is not None:
            age = time.time() - _price_time
            log.warning("All price providers failed, serving stale price (%.0fs old) from %s", age, _price_source)
        return _price_usd


def get_price_status() -> dict:
    """Return current price cache state (for health checks / diagnostics)."""
    with _price_lock:
        age = round(time.time() - _price_time, 1) if _price_time > 0 else None
        return {
            "price_usd": _price_usd,
            "source": _price_source,
            "age_seconds": age,
            "stale": age is not None and age > _PRICE_TTL,
            "providers": [name for name, _ in _PROVIDERS],
        }


# ---------------------------------------------------------------------------
# Async price fetching — non-blocking alternative to fetch_btc_price()
# ---------------------------------------------------------------------------

def _get_async_client() -> "httpx.AsyncClient":
    """Lazy singleton for the shared httpx.AsyncClient."""
    global _async_client
    if _async_client is None:
        with _async_client_lock:
            if _async_client is None:
                _async_client = httpx.AsyncClient(headers=_HEADERS, timeout=5.0)
    return _async_client


async def _async_fetch_binance() -> float | None:
    try:
        resp = await _get_async_client().get(
            "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=3.0)
        resp.raise_for_status()
        return float(resp.json()["price"])
    except Exception:
        return None


async def _async_fetch_coingecko() -> float | None:
    try:
        resp = await _get_async_client().get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
        resp.raise_for_status()
        return resp.json()["bitcoin"]["usd"]
    except Exception:
        return None


async def _async_fetch_coinbase() -> float | None:
    try:
        resp = await _get_async_client().get(
            "https://api.coinbase.com/v2/prices/BTC-USD/spot")
        resp.raise_for_status()
        return float(resp.json()["data"]["amount"])
    except Exception:
        return None


async def _async_fetch_kraken() -> float | None:
    try:
        resp = await _get_async_client().get(
            "https://api.kraken.com/0/public/Ticker?pair=XBTUSD")
        resp.raise_for_status()
        return float(resp.json()["result"]["XXBTZUSD"]["c"][0])
    except Exception:
        return None


_ASYNC_PROVIDERS = [
    ("binance", _async_fetch_binance),
    ("coingecko", _async_fetch_coingecko),
    ("coinbase", _async_fetch_coinbase),
    ("kraken", _async_fetch_kraken),
]


async def async_fetch_btc_price() -> tuple[float | None, str | None]:
    """Async version of fetch_btc_price() — tries each provider in order.

    Requires httpx. Falls back to sync fetch_btc_price() via run_in_executor
    if httpx is not installed.
    """
    if not _HTTPX_AVAILABLE:
        # Fallback: run sync version in executor to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fetch_btc_price)

    for name, fetcher in _ASYNC_PROVIDERS:
        price = await fetcher()
        if price is not None and 0 < price < 10_000_000:
            return price, name
    return None, None


async def async_get_cached_price() -> float | None:
    """Async version of get_cached_price() — non-blocking price fetch.

    Uses the same shared cache as the sync version.
    """
    global _price_usd, _price_time, _price_source
    with _price_lock:
        if _price_usd is not None and (time.time() - _price_time) < _PRICE_TTL:
            return _price_usd

    price, source = await async_fetch_btc_price()
    if price is not None:
        with _price_lock:
            _price_usd = price
            _price_time = time.time()
            _price_source = source
        log.debug("BTC price updated (async): $%.2f via %s", price, source)
        return price

    with _price_lock:
        if _price_usd is not None:
            age = time.time() - _price_time
            log.warning("All async price providers failed, serving stale price (%.0fs old) from %s", age, _price_source)
        return _price_usd
