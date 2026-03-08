"""Tests for the multi-provider BTC/USD price service (services/price.py)."""

import time
from unittest.mock import patch, MagicMock

from bitcoin_api.services import price


def _reset_cache():
    """Clear the price cache between tests."""
    with price._price_lock:
        price._price_usd = None
        price._price_time = 0
        price._price_source = None


def _make_providers(*specs):
    """Build a _PROVIDERS list from (name, return_value) tuples."""
    providers = []
    for name, val in specs:
        fn = MagicMock(return_value=val)
        fn.__name__ = f"_fetch_from_{name}"
        providers.append((name, fn))
    return providers


# ---------------------------------------------------------------------------
# fetch_btc_price — provider fallback chain
# ---------------------------------------------------------------------------


def test_fetch_first_provider_wins():
    """First provider success short-circuits the chain."""
    _reset_cache()
    providers = _make_providers(("coingecko", 95000.0), ("coinbase", 95100.0))
    with patch.object(price, "_PROVIDERS", providers):
        result, source = price.fetch_btc_price()
    assert result == 95000.0
    assert source == "coingecko"
    providers[1][1].assert_not_called()


def test_fetch_falls_through_to_second():
    """When first provider fails, second is tried."""
    _reset_cache()
    providers = _make_providers(("coingecko", None), ("coinbase", 94500.0), ("kraken", 94600.0))
    with patch.object(price, "_PROVIDERS", providers):
        result, source = price.fetch_btc_price()
    assert result == 94500.0
    assert source == "coinbase"
    providers[2][1].assert_not_called()


def test_fetch_falls_through_to_third():
    """When first two fail, third is tried."""
    _reset_cache()
    providers = _make_providers(("coingecko", None), ("coinbase", None), ("kraken", 93000.0))
    with patch.object(price, "_PROVIDERS", providers):
        result, source = price.fetch_btc_price()
    assert result == 93000.0
    assert source == "kraken"


def test_fetch_all_fail():
    """All providers failing returns (None, None)."""
    _reset_cache()
    providers = _make_providers(("coingecko", None), ("coinbase", None), ("kraken", None))
    with patch.object(price, "_PROVIDERS", providers):
        result, source = price.fetch_btc_price()
    assert result is None
    assert source is None


def test_fetch_rejects_zero_price():
    """A provider returning 0 is treated as failure."""
    _reset_cache()
    providers = _make_providers(("coingecko", 0), ("coinbase", 95000.0))
    with patch.object(price, "_PROVIDERS", providers):
        result, source = price.fetch_btc_price()
    assert result == 95000.0
    assert source == "coinbase"


def test_fetch_rejects_negative_price():
    """A provider returning negative is treated as failure."""
    _reset_cache()
    providers = _make_providers(("coingecko", -1.0), ("coinbase", 95000.0))
    with patch.object(price, "_PROVIDERS", providers):
        result, source = price.fetch_btc_price()
    assert result == 95000.0
    assert source == "coinbase"


# ---------------------------------------------------------------------------
# get_cached_price — caching + stale fallback
# ---------------------------------------------------------------------------


def test_cached_price_fresh():
    """Fresh cache returns without fetching."""
    _reset_cache()
    with price._price_lock:
        price._price_usd = 90000.0
        price._price_time = time.time()
        price._price_source = "coingecko"
    result = price.get_cached_price()
    assert result == 90000.0


def test_cached_price_expired_refetch():
    """Expired cache triggers a new fetch."""
    _reset_cache()
    with price._price_lock:
        price._price_usd = 90000.0
        price._price_time = time.time() - 120  # expired
        price._price_source = "coingecko"
    with patch.object(price, "fetch_btc_price", return_value=(95000.0, "coinbase")):
        result = price.get_cached_price()
    assert result == 95000.0


def test_cached_price_stale_fallback():
    """When all providers fail, stale price is returned."""
    _reset_cache()
    with price._price_lock:
        price._price_usd = 88000.0
        price._price_time = time.time() - 300  # very stale
        price._price_source = "kraken"
    with patch.object(price, "fetch_btc_price", return_value=(None, None)):
        result = price.get_cached_price()
    assert result == 88000.0


def test_cached_price_no_history():
    """No cached price + all providers fail returns None."""
    _reset_cache()
    with patch.object(price, "fetch_btc_price", return_value=(None, None)):
        result = price.get_cached_price()
    assert result is None


# ---------------------------------------------------------------------------
# get_price_status — diagnostics
# ---------------------------------------------------------------------------


def test_price_status_empty():
    """Status with no cached price."""
    _reset_cache()
    status = price.get_price_status()
    assert status["price_usd"] is None
    assert status["source"] is None
    assert status["age_seconds"] is None
    assert status["stale"] is False
    assert len(status["providers"]) == 3


def test_price_status_with_data():
    """Status with cached price."""
    _reset_cache()
    with price._price_lock:
        price._price_usd = 95000.0
        price._price_time = time.time() - 10
        price._price_source = "coinbase"
    status = price.get_price_status()
    assert status["price_usd"] == 95000.0
    assert status["source"] == "coinbase"
    assert 9 <= status["age_seconds"] <= 12
    assert status["stale"] is False


def test_price_status_stale():
    """Status correctly identifies stale price."""
    _reset_cache()
    with price._price_lock:
        price._price_usd = 95000.0
        price._price_time = time.time() - 120
        price._price_source = "coingecko"
    status = price.get_price_status()
    assert status["stale"] is True
