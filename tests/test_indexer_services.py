"""Tests for the indexer service functions (address + transaction)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class _AsyncCtxManager:
    """Async context manager that yields a mock connection."""

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _make_mock_pool(conn):
    pool = MagicMock()
    pool.acquire.return_value = _AsyncCtxManager(conn)
    return pool


# ---------------------------------------------------------------------------
# address – get_address_balance
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("bitcoin_api.indexer.services.address.get_pool")
async def test_get_address_balance_known(mock_get_pool):
    """Returns correct shape for a known address."""
    from bitcoin_api.indexer.services.address import get_address_balance

    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "total_received": 500_000,
        "total_sent": 200_000,
        "tx_count": 7,
        "first_seen": 100,
        "last_seen": 800,
    }
    mock_get_pool.return_value = _make_mock_pool(conn)

    result = await get_address_balance("bc1qtest")

    assert result is not None
    assert result["address"] == "bc1qtest"
    assert result["total_received"] == 500_000
    assert result["total_sent"] == 200_000
    assert result["balance"] == 300_000
    assert result["tx_count"] == 7
    assert result["first_seen_height"] == 100
    assert result["last_seen_height"] == 800


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.services.address.get_pool")
async def test_get_address_balance_unknown(mock_get_pool):
    """Returns None for an unknown address."""
    from bitcoin_api.indexer.services.address import get_address_balance

    conn = AsyncMock()
    conn.fetchrow.return_value = None
    mock_get_pool.return_value = _make_mock_pool(conn)

    result = await get_address_balance("bc1qunknown")
    assert result is None


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.services.address.get_pool")
async def test_get_address_balance_calculates_balance(mock_get_pool):
    """balance == total_received - total_sent."""
    from bitcoin_api.indexer.services.address import get_address_balance

    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "total_received": 1_000_000,
        "total_sent": 750_000,
        "tx_count": 3,
        "first_seen": 50,
        "last_seen": 400,
    }
    mock_get_pool.return_value = _make_mock_pool(conn)

    result = await get_address_balance("bc1qmath")
    assert result["balance"] == 250_000


# ---------------------------------------------------------------------------
# address – get_address_history
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("bitcoin_api.indexer.services.address.get_pool")
async def test_get_address_history_paginated(mock_get_pool):
    """Returns paginated results with correct structure."""
    from bitcoin_api.indexer.services.address import get_address_history

    conn = AsyncMock()
    conn.fetchval.return_value = 2
    conn.fetch.return_value = [
        {
            "txid": bytes.fromhex("aa" * 32),
            "block_height": 800,
            "tx_index": 1,
            "value_change": 50_000,
            "fee": 1_000,
            "timestamp": 1700000000,
        },
        {
            "txid": bytes.fromhex("bb" * 32),
            "block_height": 790,
            "tx_index": 0,
            "value_change": -30_000,
            "fee": 500,
            "timestamp": 1699990000,
        },
    ]
    mock_get_pool.return_value = _make_mock_pool(conn)

    result = await get_address_history("bc1qpaged")

    assert result["address"] == "bc1qpaged"
    assert result["total"] == 2
    assert result["offset"] == 0
    assert result["limit"] == 25
    assert len(result["transactions"]) == 2
    assert result["transactions"][0]["txid"] == "aa" * 32
    assert result["transactions"][1]["value_change"] == -30_000


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.services.address.get_pool")
async def test_get_address_history_empty(mock_get_pool):
    """Empty address returns total=0 and empty list."""
    from bitcoin_api.indexer.services.address import get_address_history

    conn = AsyncMock()
    conn.fetchval.return_value = 0
    conn.fetch.return_value = []
    mock_get_pool.return_value = _make_mock_pool(conn)

    result = await get_address_history("bc1qempty")

    assert result["total"] == 0
    assert result["transactions"] == []


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.services.address.get_pool")
async def test_get_address_history_respects_offset_limit(mock_get_pool):
    """offset and limit are forwarded to query and echoed in result."""
    from bitcoin_api.indexer.services.address import get_address_history

    conn = AsyncMock()
    conn.fetchval.return_value = 50
    conn.fetch.return_value = [
        {
            "txid": bytes.fromhex("cc" * 32),
            "block_height": 500,
            "tx_index": 2,
            "value_change": 10_000,
            "fee": 200,
            "timestamp": 1699000000,
        },
    ]
    mock_get_pool.return_value = _make_mock_pool(conn)

    result = await get_address_history("bc1qpaged", offset=10, limit=5)

    assert result["offset"] == 10
    assert result["limit"] == 5
    # Verify the SQL received the right offset/limit args
    call_args = conn.fetch.call_args
    assert call_args[0][1] == "bc1qpaged"
    assert call_args[0][2] == 10
    assert call_args[0][3] == 5


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.services.address.get_pool")
async def test_get_address_history_offset_beyond_total(mock_get_pool):
    """Offset beyond total returns empty transaction list."""
    from bitcoin_api.indexer.services.address import get_address_history

    conn = AsyncMock()
    conn.fetchval.return_value = 3
    conn.fetch.return_value = []
    mock_get_pool.return_value = _make_mock_pool(conn)

    result = await get_address_history("bc1qfew", offset=100, limit=25)

    assert result["total"] == 3
    assert result["transactions"] == []
    assert result["offset"] == 100


# ---------------------------------------------------------------------------
# transaction – get_transaction
# ---------------------------------------------------------------------------

SAMPLE_TXID = "ab" * 32
SAMPLE_BLOCK_HASH = "cd" * 32


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.services.transaction.get_pool")
async def test_get_transaction_enriched(mock_get_pool):
    """Returns enriched transaction detail with correct structure."""
    from bitcoin_api.indexer.services.transaction import get_transaction

    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "block_height": 700_000,
        "block_hash": bytes.fromhex(SAMPLE_BLOCK_HASH),
        "tx_index": 5,
        "version": 2,
        "size": 250,
        "vsize": 166,
        "weight": 661,
        "locktime": 0,
        "fee": 1_500,
        "is_coinbase": False,
        "timestamp": 1700000000,
    }
    conn.fetch.side_effect = [
        # outputs
        [
            {"vout": 0, "value": 100_000, "address": "bc1qout0", "script_type": "witness_v0_keyhash", "spent": True},
            {"vout": 1, "value": 50_000, "address": "bc1qout1", "script_type": "witness_v0_keyhash", "spent": False},
        ],
        # inputs
        [
            {"vin": 0, "prev_txid": bytes.fromhex("ee" * 32), "prev_vout": 1, "address": "bc1qin0", "value": 151_500},
        ],
    ]
    mock_get_pool.return_value = _make_mock_pool(conn)

    result = await get_transaction(SAMPLE_TXID)

    assert result is not None
    assert result["txid"] == SAMPLE_TXID
    assert result["block_height"] == 700_000
    assert result["block_hash"] == SAMPLE_BLOCK_HASH
    assert result["fee"] == 1_500
    assert result["is_coinbase"] is False
    assert result["input_count"] == 1
    assert result["output_count"] == 2


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.services.transaction.get_pool")
async def test_get_transaction_unknown(mock_get_pool):
    """Returns None for an unknown txid."""
    from bitcoin_api.indexer.services.transaction import get_transaction

    conn = AsyncMock()
    conn.fetchrow.return_value = None
    mock_get_pool.return_value = _make_mock_pool(conn)

    result = await get_transaction("ff" * 32)
    assert result is None


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.services.transaction.get_pool")
async def test_get_transaction_resolved_inputs(mock_get_pool):
    """Input rows include resolved addresses and values from prev outputs."""
    from bitcoin_api.indexer.services.transaction import get_transaction

    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "block_height": 600_000,
        "block_hash": bytes.fromhex("dd" * 32),
        "tx_index": 2,
        "version": 2,
        "size": 300,
        "vsize": 200,
        "weight": 800,
        "locktime": 0,
        "fee": 2_000,
        "is_coinbase": False,
        "timestamp": 1690000000,
    }
    conn.fetch.side_effect = [
        # outputs
        [{"vout": 0, "value": 80_000, "address": "bc1qo", "script_type": "witness_v0_keyhash", "spent": False}],
        # inputs – two inputs with resolved addresses
        [
            {"vin": 0, "prev_txid": bytes.fromhex("11" * 32), "prev_vout": 0, "address": "bc1qsender1", "value": 50_000},
            {"vin": 1, "prev_txid": bytes.fromhex("22" * 32), "prev_vout": 3, "address": "bc1qsender2", "value": 32_000},
        ],
    ]
    mock_get_pool.return_value = _make_mock_pool(conn)

    result = await get_transaction(SAMPLE_TXID)

    assert len(result["inputs"]) == 2
    assert result["inputs"][0]["address"] == "bc1qsender1"
    assert result["inputs"][0]["value"] == 50_000
    assert result["inputs"][0]["prev_txid"] == "11" * 32
    assert result["inputs"][1]["address"] == "bc1qsender2"
    assert result["inputs"][1]["prev_vout"] == 3


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.services.transaction.get_pool")
async def test_get_transaction_spent_outputs(mock_get_pool):
    """Outputs correctly reflect spent status."""
    from bitcoin_api.indexer.services.transaction import get_transaction

    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "block_height": 650_000,
        "block_hash": bytes.fromhex("ee" * 32),
        "tx_index": 0,
        "version": 2,
        "size": 200,
        "vsize": 150,
        "weight": 600,
        "locktime": 0,
        "fee": 500,
        "is_coinbase": False,
        "timestamp": 1695000000,
    }
    conn.fetch.side_effect = [
        # outputs: one spent, one unspent
        [
            {"vout": 0, "value": 40_000, "address": "bc1qspent", "script_type": "witness_v0_keyhash", "spent": True},
            {"vout": 1, "value": 60_000, "address": "bc1qutxo", "script_type": "witness_v0_keyhash", "spent": False},
        ],
        # inputs
        [{"vin": 0, "prev_txid": bytes.fromhex("33" * 32), "prev_vout": 0, "address": "bc1qfrom", "value": 100_500}],
    ]
    mock_get_pool.return_value = _make_mock_pool(conn)

    result = await get_transaction(SAMPLE_TXID)

    assert result["outputs"][0]["spent"] is True
    assert result["outputs"][1]["spent"] is False


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.services.transaction.get_pool")
async def test_get_transaction_coinbase(mock_get_pool):
    """Coinbase transaction has no inputs."""
    from bitcoin_api.indexer.services.transaction import get_transaction

    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "block_height": 700_001,
        "block_hash": bytes.fromhex("ff" * 32),
        "tx_index": 0,
        "version": 2,
        "size": 200,
        "vsize": 173,
        "weight": 692,
        "locktime": 0,
        "fee": 0,
        "is_coinbase": True,
        "timestamp": 1700001000,
    }
    conn.fetch.side_effect = [
        # outputs (block reward)
        [{"vout": 0, "value": 312_500_000, "address": "bc1qminer", "script_type": "witness_v1_taproot", "spent": False}],
        # inputs: empty (coinbase has no real inputs in our schema)
        [],
    ]
    mock_get_pool.return_value = _make_mock_pool(conn)

    result = await get_transaction("cb" * 32)

    assert result["is_coinbase"] is True
    assert result["input_count"] == 0
    assert result["inputs"] == []
    assert result["output_count"] == 1
    assert result["fee"] == 0
