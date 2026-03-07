"""Test fixtures for bitcoin-api."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

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
            "bestblockhash": "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670",
            "difficulty": 110_000_000_000_000,
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
        "getrawtransaction": (
            # verbose=False returns hex string, verbose=True returns dict
            # args[0] = txid, args[1] = verbose (True/False)
            "0200000001abcdef0123456789abcdef0123456789"
            if len(args) >= 2 and args[1] is False
            else {
                "txid": "abc" * 21 + "a",
                "hash": "abc" * 21 + "a",
                "version": 2,
                "size": 225,
                "vsize": 166,
                "weight": 661,
                "locktime": 0,
                "vin": [{"txid": "def" * 21 + "d", "vout": 0}],
                "vout": [{"value": 0.5, "n": 0}, {"value": 0.3, "n": 1}],
                "blockhash": "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670",
                "blockheight": 879000,
                "confirmations": 1000,
            }
        ),
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
        "getrawmempool": (
            # verbose=True returns dict, verbose=False returns list
            {
                "aaa" * 21 + "a": {
                    "fees": {"base": 0.0001},
                    "vsize": 200,
                    "weight": 800,
                    "time": 1709654500,
                    "height": 880000,
                },
                "bbb" * 21 + "b": {
                    "fees": {"base": 0.00005},
                    "vsize": 141,
                    "weight": 561,
                    "time": 1709654400,
                    "height": 880000,
                },
            }
            if args and args[0] is True
            else ["aaa" * 21 + "a", "bbb" * 21 + "b"]
        ),
        "getblock": (
            # verbosity=2 returns full txs, verbosity=1 returns txids as strings
            {
                "hash": "abc" * 21 + "a",
                "height": 880000,
                "tx": (
                    [
                        {"txid": "tx1" + "0" * 61, "size": 200, "vsize": 150, "vin": [], "vout": [{"value": 50.0, "n": 0}]},
                        {"txid": "tx2" + "0" * 61, "size": 300, "vsize": 250, "vin": [], "vout": [{"value": 0.5, "n": 0}]},
                    ]
                    if args and len(args) > 1 and args[1] == 2
                    else ["tx1" + "0" * 61, "tx2" + "0" * 61]
                ),
                "size": 1500,
                "weight": 4000,
                "nTx": 2,
            }
        ),
        "getblockheader": (
            # verbose=False returns hex string
            "0100000000000000000000000000000000000000000000000000000000000000"
            "000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa"
            "4b1e5e4a29ab5f49ffff001d1dac2b7c"
            if args and len(args) > 1 and args[1] is False
            else {
                "hash": args[0] if args else "abc" * 21 + "a",
                "confirmations": 880000,
                "height": 0,
                "version": 1,
                "nTx": 1,
            }
        ),
        "validateaddress": {
            "isvalid": True,
            "address": args[0] if args else "bc1qtest",
            "scriptPubKey": "0014751e76e8199196d454941c45d1b3a323f1433bd6",
            "isscript": False,
            "iswitness": True,
            "witness_version": 0,
            "witness_program": "751e76e8199196d454941c45d1b3a323f1433bd6",
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
        "sendrawtransaction": "abc" * 21 + "a",
        "scantxoutset": {
            "success": True,
            "txouts_searched": 180000000,
            "total_amount": 0.05,
            "unspents": [
                {
                    "txid": "aaa" * 21 + "a",
                    "vout": 0,
                    "scriptPubKey": "0014751e76e8199196d454941c45d1b3a323f1433bd6",
                    "amount": 0.03,
                    "height": 870000,
                    "coinbase": False,
                },
                {
                    "txid": "bbb" * 21 + "b",
                    "vout": 1,
                    "scriptPubKey": "0014751e76e8199196d454941c45d1b3a323f1433bd6",
                    "amount": 0.02,
                    "height": 875000,
                    "coinbase": False,
                },
            ],
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
        _recent_block_cache, _nextblock_cache, _hash_to_height,
        _mempool_snapshots, _raw_mempool_cache,
    )
    _fee_cache.clear()
    _mempool_cache.clear()
    _status_cache.clear()
    _blockchain_info_cache.clear()
    _block_count_cache.clear()
    _block_cache.clear()
    _recent_block_cache.clear()
    _nextblock_cache.clear()
    _hash_to_height.clear()
    _mempool_snapshots.clear()
    _raw_mempool_cache.clear()


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


@pytest.fixture
def authed_client(mock_rpc, use_temp_db):
    """Client with a valid free-tier API key pre-seeded."""
    import hashlib
    from bitcoin_api.db import get_db

    key = "test-authed-key-fixture"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO api_keys (key_hash, prefix, tier, label, active) VALUES (?, ?, 'free', 'test', 1)",
        (key_hash, key[:8]),
    )
    db.commit()

    app.dependency_overrides[get_rpc] = lambda: mock_rpc
    with TestClient(app, headers={"X-API-Key": key}) as c:
        yield c
    app.dependency_overrides.clear()
