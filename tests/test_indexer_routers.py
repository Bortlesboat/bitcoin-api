"""Tests for indexer router endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class _AsyncCtxManager:
    """Helper async context manager for mocking pool.acquire()."""

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


_SENTINEL = object()


def _make_mock_pool(fetchrow_return=_SENTINEL):
    """Create a mock pool with proper async context manager support."""
    pool = MagicMock()
    conn = AsyncMock()
    ret = {"tip_height": 880000} if fetchrow_return is _SENTINEL else fetchrow_return
    conn.fetchrow = AsyncMock(return_value=ret)
    pool.acquire.return_value = _AsyncCtxManager(conn)
    return pool


@pytest.fixture
def authed_request():
    request = MagicMock()
    request.state.tier = "free"
    return request


@pytest.fixture
def anon_request():
    request = MagicMock()
    request.state.tier = "anonymous"
    return request


# --- Address Balance ---

@pytest.mark.asyncio
@patch("bitcoin_api.indexer.routers.indexed_address.get_pool")
@patch("bitcoin_api.indexer.routers.indexed_address.get_address_balance")
async def test_address_balance_found(mock_balance, mock_gp, authed_request):
    from bitcoin_api.indexer.routers.indexed_address import address_balance
    mock_gp.return_value = _make_mock_pool()
    mock_balance.return_value = {
        "address": "bc1qtest",
        "total_received": 100000000,
        "total_sent": 50000000,
        "balance": 50000000,
        "tx_count": 5,
        "first_seen_height": 700000,
        "last_seen_height": 880000,
    }
    result = await address_balance("bc1qtest", authed_request)
    assert result["data"]["address"] == "bc1qtest"
    assert result["data"]["balance"] == 50000000


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.routers.indexed_address.get_pool")
@patch("bitcoin_api.indexer.routers.indexed_address.get_address_balance")
async def test_address_balance_not_found(mock_balance, mock_gp, authed_request):
    from bitcoin_api.indexer.routers.indexed_address import address_balance
    mock_gp.return_value = _make_mock_pool()
    mock_balance.return_value = None
    result = await address_balance("bc1qunknown", authed_request)
    assert result.status_code == 404


@pytest.mark.asyncio
async def test_address_balance_no_auth(anon_request):
    from bitcoin_api.indexer.routers.indexed_address import address_balance
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await address_balance("bc1qtest", anon_request)
    assert exc_info.value.status_code == 403


# --- Address History ---

@pytest.mark.asyncio
@patch("bitcoin_api.indexer.routers.indexed_address.get_pool")
@patch("bitcoin_api.indexer.routers.indexed_address.get_address_history")
async def test_address_history(mock_history, mock_gp, authed_request):
    from bitcoin_api.indexer.routers.indexed_address import address_txs
    mock_gp.return_value = _make_mock_pool()
    mock_history.return_value = {
        "address": "bc1qtest",
        "transactions": [
            {"txid": "aa" * 32, "block_height": 880000, "tx_index": 0, "value_change": 50000000, "fee": 1000, "timestamp": 1700000000},
        ],
        "total": 1,
        "offset": 0,
        "limit": 25,
    }
    result = await address_txs("bc1qtest", authed_request)
    assert result["data"]["total"] == 1
    assert len(result["data"]["transactions"]) == 1


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.routers.indexed_address.get_pool")
@patch("bitcoin_api.indexer.routers.indexed_address.get_address_history")
async def test_address_history_empty(mock_history, mock_gp, authed_request):
    from bitcoin_api.indexer.routers.indexed_address import address_txs
    mock_gp.return_value = _make_mock_pool()
    mock_history.return_value = {
        "address": "bc1qempty",
        "transactions": [],
        "total": 0,
        "offset": 0,
        "limit": 25,
    }
    result = await address_txs("bc1qempty", authed_request)
    assert result["data"]["total"] == 0
    assert result["data"]["transactions"] == []


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.routers.indexed_address.get_pool")
@patch("bitcoin_api.indexer.routers.indexed_address.get_address_history")
async def test_address_history_pagination(mock_history, mock_gp, authed_request):
    from bitcoin_api.indexer.routers.indexed_address import address_txs
    mock_gp.return_value = _make_mock_pool()
    mock_history.return_value = {
        "address": "bc1qtest",
        "transactions": [{"txid": "bb" * 32, "block_height": 879990, "tx_index": 1, "value_change": -10000, "fee": 500, "timestamp": 1699999000}],
        "total": 50,
        "offset": 10,
        "limit": 10,
    }
    result = await address_txs("bc1qtest", authed_request, offset=10, limit=10)
    assert result["data"]["offset"] == 10
    assert result["data"]["limit"] == 10
    assert result["data"]["total"] == 50


# --- Transaction Detail ---

@pytest.mark.asyncio
@patch("bitcoin_api.indexer.routers.indexed_tx.get_pool")
@patch("bitcoin_api.indexer.routers.indexed_tx.get_transaction")
async def test_tx_found(mock_tx, mock_gp, authed_request):
    from bitcoin_api.indexer.routers.indexed_tx import indexed_tx
    mock_gp.return_value = _make_mock_pool()
    mock_tx.return_value = {
        "txid": "aa" * 32,
        "block_height": 880000,
        "block_hash": "bb" * 32,
        "tx_index": 1,
        "version": 2,
        "size": 225,
        "vsize": 166,
        "weight": 661,
        "locktime": 0,
        "fee": 10000,
        "is_coinbase": False,
        "input_count": 1,
        "output_count": 2,
        "inputs": [],
        "outputs": [],
    }
    result = await indexed_tx("aa" * 32, authed_request)
    assert result["data"]["txid"] == "aa" * 32


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.routers.indexed_tx.get_pool")
@patch("bitcoin_api.indexer.routers.indexed_tx.get_transaction")
async def test_tx_not_found(mock_tx, mock_gp, authed_request):
    from bitcoin_api.indexer.routers.indexed_tx import indexed_tx
    mock_gp.return_value = _make_mock_pool()
    mock_tx.return_value = None
    result = await indexed_tx("aa" * 32, authed_request)
    assert result.status_code == 404


@pytest.mark.asyncio
async def test_tx_invalid_length(authed_request):
    from bitcoin_api.indexer.routers.indexed_tx import indexed_tx
    result = await indexed_tx("short", authed_request)
    assert result.status_code == 400


@pytest.mark.asyncio
async def test_tx_invalid_hex(authed_request):
    from bitcoin_api.indexer.routers.indexed_tx import indexed_tx
    result = await indexed_tx("zz" * 32, authed_request)
    assert result.status_code == 400


@pytest.mark.asyncio
async def test_tx_no_auth(anon_request):
    from bitcoin_api.indexer.routers.indexed_tx import indexed_tx
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await indexed_tx("aa" * 32, anon_request)
    assert exc_info.value.status_code == 403


# --- Indexer Status ---

@pytest.mark.asyncio
@patch("bitcoin_api.indexer.routers.indexer_status.get_pool")
async def test_status_basic(mock_gp):
    from bitcoin_api.indexer.routers.indexer_status import indexer_status
    mock_gp.return_value = _make_mock_pool(fetchrow_return={
        "tip_height": 800000,
        "tip_hash": bytes.fromhex("aa" * 32),
        "started_at": None,
        "last_block_at": None,
        "blocks_per_sec": 50.0,
    })

    with patch("bitcoin_api.indexer.routers.indexer_status.indexer_settings") as mock_settings:
        mock_settings.enabled = True
        result = await indexer_status()
        assert result["data"]["enabled"] is True
        assert result["data"]["indexed_height"] == 800000


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.routers.indexer_status.get_pool")
async def test_status_no_auth_required(mock_gp):
    """Status endpoint should not require authentication."""
    from bitcoin_api.indexer.routers.indexer_status import indexer_status
    mock_gp.return_value = _make_mock_pool(fetchrow_return=None)

    with patch("bitcoin_api.indexer.routers.indexer_status.indexer_settings") as mock_settings:
        mock_settings.enabled = False
        result = await indexer_status()
        assert "data" in result


# --- ENABLE_INDEXER=false test ---

def test_indexer_routes_absent_when_disabled():
    """When ENABLE_INDEXER=false, /indexed/* routes should not be registered (404)."""
    from bitcoin_api.config import settings
    # The default is enable_indexer=False, so the main app won't register indexer routes
    assert settings.enable_indexer is False, "Test assumes ENABLE_INDEXER defaults to False"
    from fastapi.testclient import TestClient
    from bitcoin_api.main import app
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/indexed/status")
    assert resp.status_code == 404
