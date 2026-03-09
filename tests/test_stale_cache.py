"""Tests for stale cache fallback — graceful degradation when node is down."""

import time
from unittest.mock import MagicMock

import pytest

from bitcoin_api.cache import (
    MAX_STALE_AGE,
    _save_stale,
    clear_all_caches,
    clear_stale_store,
    get_stale,
    _cached_rpc,
    create_cache,
)
from cachetools import TTLCache


@pytest.fixture(autouse=True)
def clean_stale():
    """Clear stale store before and after each test."""
    clear_stale_store()
    yield
    clear_stale_store()


# --- Unit tests for _save_stale / get_stale ---


def test_save_and_get_stale():
    """Saved stale data can be retrieved."""
    _save_stale("fee", "_", {"rate": 5.0})
    result = get_stale("fee", "_")
    assert result is not None
    value, age = result
    assert value == {"rate": 5.0}
    assert age < 1.0  # just saved


def test_get_stale_missing():
    """Returns None for keys that were never saved."""
    assert get_stale("nonexistent", "_") is None


def test_get_stale_default_key():
    """Default key parameter works."""
    _save_stale("status", "_", {"ok": True})
    result = get_stale("status")
    assert result is not None
    assert result[0] == {"ok": True}


def test_stale_age_increases():
    """Stale data age reflects time since it was stored."""
    _save_stale("fee", "_", {"rate": 5.0})
    time.sleep(0.05)
    result = get_stale("fee", "_")
    assert result is not None
    _, age = result
    assert age >= 0.04


def test_stale_max_age_enforced():
    """Data older than MAX_STALE_AGE is not returned."""
    _save_stale("fee", "_", {"rate": 5.0})
    # Manually backdate the timestamp
    from bitcoin_api.cache import _stale_timestamps, _stale_lock
    with _stale_lock:
        _stale_timestamps["fee:_"] = time.time() - MAX_STALE_AGE - 1
    assert get_stale("fee", "_") is None


def test_stale_just_under_max_age():
    """Data just under MAX_STALE_AGE is still returned."""
    _save_stale("fee", "_", {"rate": 5.0})
    from bitcoin_api.cache import _stale_timestamps, _stale_lock
    with _stale_lock:
        _stale_timestamps["fee:_"] = time.time() - MAX_STALE_AGE + 10
    result = get_stale("fee", "_")
    assert result is not None


def test_clear_stale_store():
    """clear_stale_store removes all entries."""
    _save_stale("fee", "_", {"rate": 5.0})
    _save_stale("mempool", "_", {"size": 100})
    clear_stale_store()
    assert get_stale("fee", "_") is None
    assert get_stale("mempool", "_") is None


def test_clear_all_caches_clears_stale():
    """clear_all_caches also clears the stale store."""
    _save_stale("fee", "_", {"rate": 5.0})
    clear_all_caches()
    assert get_stale("fee", "_") is None


def test_stale_store_overwrites():
    """Saving to the same key overwrites the old value."""
    _save_stale("fee", "_", {"rate": 5.0})
    _save_stale("fee", "_", {"rate": 10.0})
    result = get_stale("fee", "_")
    assert result is not None
    assert result[0] == {"rate": 10.0}


# --- Integration tests for _cached_rpc with stale fallback ---


def _make_entry(name):
    """Create a fresh cache entry for testing."""
    return create_cache(name, TTLCache(maxsize=1, ttl=1))


def test_cached_rpc_saves_to_stale_on_success():
    """Successful RPC calls save data to the stale store."""
    entry = _make_entry("test_save")
    mock_rpc = MagicMock()
    result = _cached_rpc(entry, mock_rpc, lambda r: {"result": 42})

    assert result == {"result": 42}
    stale = get_stale("test_save", "_")
    assert stale is not None
    assert stale[0] == {"result": 42}


def test_cached_rpc_serves_stale_on_connection_error():
    """ConnectionError falls back to stale data."""
    entry = _make_entry("test_conn")
    _save_stale("test_conn", "_", {"cached": True})

    mock_rpc = MagicMock()
    fetcher = MagicMock(side_effect=ConnectionError("refused"))
    result = _cached_rpc(entry, mock_rpc, fetcher)
    assert result == {"cached": True}


def test_cached_rpc_serves_stale_on_timeout():
    """TimeoutError falls back to stale data."""
    entry = _make_entry("test_timeout")
    _save_stale("test_timeout", "_", {"cached": True})

    mock_rpc = MagicMock()
    fetcher = MagicMock(side_effect=TimeoutError("timed out"))
    result = _cached_rpc(entry, mock_rpc, fetcher)
    assert result == {"cached": True}


def test_cached_rpc_serves_stale_on_os_error():
    """OSError falls back to stale data."""
    entry = _make_entry("test_os")
    _save_stale("test_os", "_", {"cached": True})

    mock_rpc = MagicMock()
    fetcher = MagicMock(side_effect=OSError("network down"))
    result = _cached_rpc(entry, mock_rpc, fetcher)
    assert result == {"cached": True}


def test_cached_rpc_raises_when_no_stale():
    """ConnectionError propagates when no stale data exists."""
    entry = _make_entry("test_no_stale")
    mock_rpc = MagicMock()
    fetcher = MagicMock(side_effect=ConnectionError("refused"))
    with pytest.raises(ConnectionError):
        _cached_rpc(entry, mock_rpc, fetcher)


def test_cached_rpc_does_not_catch_app_bugs():
    """Non-connection errors (e.g. KeyError) are NOT caught — they propagate."""
    entry = _make_entry("test_bug")
    _save_stale("test_bug", "_", {"stale": True})

    mock_rpc = MagicMock()
    fetcher = MagicMock(side_effect=KeyError("missing_field"))
    with pytest.raises(KeyError):
        _cached_rpc(entry, mock_rpc, fetcher)


def test_cached_rpc_does_not_catch_value_error():
    """ValueError (application bug) propagates even with stale data available."""
    entry = _make_entry("test_valerr")
    _save_stale("test_valerr", "_", {"stale": True})

    mock_rpc = MagicMock()
    fetcher = MagicMock(side_effect=ValueError("bad data"))
    with pytest.raises(ValueError):
        _cached_rpc(entry, mock_rpc, fetcher)


def test_cached_rpc_stale_expired_raises():
    """Stale data past MAX_STALE_AGE is not served — error propagates."""
    entry = _make_entry("test_expired")
    _save_stale("test_expired", "_", {"old": True})

    # Backdate the stale entry
    from bitcoin_api.cache import _stale_timestamps, _stale_lock
    with _stale_lock:
        _stale_timestamps["test_expired:_"] = time.time() - MAX_STALE_AGE - 1

    mock_rpc = MagicMock()
    fetcher = MagicMock(side_effect=ConnectionError("refused"))
    with pytest.raises(ConnectionError):
        _cached_rpc(entry, mock_rpc, fetcher)


# --- Prometheus metric test ---


def test_stale_cache_served_metric_exists():
    """STALE_CACHE_SERVED Prometheus counter exists with cache_name label."""
    from bitcoin_api.metrics import STALE_CACHE_SERVED
    assert "stale_cache_served" in STALE_CACHE_SERVED._name


# --- MAX_STALE_AGE constant test ---


def test_max_stale_age_is_one_hour():
    """MAX_STALE_AGE is 3600 seconds (1 hour)."""
    assert MAX_STALE_AGE == 3600
