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
    }.get(method, {})

    return mock


@pytest.fixture
def mock_rpc():
    return make_mock_rpc()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Clear rate limit state between tests."""
    from bitcoin_api.rate_limit import _windows
    _windows.clear()


@pytest.fixture
def client(mock_rpc):
    app.dependency_overrides[get_rpc] = lambda: mock_rpc
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
