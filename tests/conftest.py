"""Test fixtures for bitcoin-api."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from bitcoin_api.main import app
from bitcoin_api.dependencies import get_rpc


def make_mock_rpc():
    """Create a mock BitcoinRPC that returns plausible data."""
    mock = MagicMock()

    mock.call.side_effect = lambda method, *args: {
        "getblockchaininfo": {
            "chain": "main",
            "blocks": 880000,
            "headers": 880000,
            "verificationprogress": 0.9999,
            "size_on_disk": 650_000_000_000,
            "pruned": False,
        },
        "getblockcount": 880000,
        "getnetworkinfo": {
            "version": 270000,
            "subversion": "/Satoshi:27.0.0/",
            "protocolversion": 70016,
            "connections": 125,
            "connections_in": 80,
            "connections_out": 45,
            "relayfee": 0.00001,
            "incrementalfee": 0.00001,
            "networks": [
                {"name": "ipv4", "reachable": True},
                {"name": "ipv6", "reachable": True},
                {"name": "onion", "reachable": True},
            ],
        },
        "getmempoolinfo": {
            "loaded": True,
            "size": 15000,
            "bytes": 8500000,
            "usage": 45000000,
            "total_fee": 1.5,
            "maxmempool": 300000000,
            "mempoolminfee": 0.00001,
            "minrelaytxfee": 0.00001,
        },
        "estimatesmartfee": {
            "feerate": 0.00012,
            "blocks": args[0] if args else 6,
        },
        "getmininginfo": {
            "blocks": 880000,
            "difficulty": 110_000_000_000_000,
            "networkhashps": 800_000_000_000_000_000_000,
            "chain": "main",
        },
        "getrawtransaction": {
            "txid": "abc" * 21 + "a",
            "hash": "abc" * 21 + "a",
            "version": 2,
            "size": 225,
            "vsize": 166,
            "weight": 661,
            "locktime": 0,
            "vin": [{"txid": "def" * 21 + "d", "vout": 0}],
            "vout": [{"value": 0.5, "n": 0}],
        },
        "gettxout": (
            {
                "bestblock": "abc123",
                "confirmations": 10,
                "value": 0.5,
                "scriptPubKey": {"type": "witness_v1_taproot"},
            }
            if args
            else None
        ),
        "getmempoolentry": {
            "fees": {"base": 0.00001},
            "vsize": 166,
            "weight": 661,
            "time": 1709654400,
            "height": 880000,
        },
        "getblockstats": {
            "height": 880000,
            "total_fee": 25000000,
            "txs": 3500,
            "avgfee": 7142,
            "avgfeerate": 15,
        },
        "getchaintips": [
            {
                "height": 880000,
                "hash": "abc" * 21 + "a",
                "branchlen": 0,
                "status": "active",
            }
        ],
        "decoderawtransaction": {
            "txid": "abc" * 21 + "a",
            "hash": "abc" * 21 + "a",
            "version": 2,
            "size": 225,
            "vsize": 166,
            "weight": 661,
            "locktime": 0,
            "vin": [],
            "vout": [],
        },
    }.get(method, {})

    # getblocktemplate is called via rpc.getblocktemplate() not rpc.call()
    mock.getblocktemplate.return_value = {
        "height": 880001,
        "transactions": [
            {"txid": "abc123", "weight": 1000, "fee": 5000},
            {"txid": "def456", "weight": 800, "fee": 8000},
            {"txid": "ghi789", "weight": 600, "fee": 3000},
        ],
    }

    return mock


@pytest.fixture
def mock_rpc():
    return make_mock_rpc()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Clear rate limit state between tests."""
    from bitcoin_api.rate_limit import _windows
    _windows.clear()


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all TTL caches between tests."""
    from bitcoin_api.cache import (
        _fee_cache, _mempool_cache, _status_cache,
        _blockchain_info_cache, _block_count_cache, _block_cache,
        _recent_block_cache, _nextblock_cache,
    )
    _fee_cache.clear()
    _mempool_cache.clear()
    _status_cache.clear()
    _blockchain_info_cache.clear()
    _block_count_cache.clear()
    _block_cache.clear()
    _recent_block_cache.clear()
    _nextblock_cache.clear()


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path):
    """Use a temporary database for each test."""
    from bitcoin_api import db
    # Reset thread-local state and initialization flag
    db._initialized = False
    db._local = __import__("threading").local()
    db.get_db(tmp_path / "test.db")
    yield
    db._initialized = False
    db._local = __import__("threading").local()


@pytest.fixture
def client(mock_rpc):
    app.dependency_overrides[get_rpc] = lambda: mock_rpc
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
