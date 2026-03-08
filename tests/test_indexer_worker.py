"""Tests for indexer sync worker functions."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _AsyncCtxManager:
    """Helper async context manager for mocking pool.acquire()."""

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


class _AsyncTxnCtxManager:
    """Helper async context manager for mocking conn.transaction()."""

    async def __aenter__(self):
        return None

    async def __aexit__(self, *args):
        pass


def _make_mock_pool(fetchrow_return=None):
    """Create a mock pool whose acquire() yields an AsyncMock connection."""
    pool = MagicMock()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    conn.execute = AsyncMock()
    # transaction() must be a regular (non-async) method returning an async ctx manager
    conn.transaction = MagicMock(return_value=_AsyncTxnCtxManager())
    pool.acquire.return_value = _AsyncCtxManager(conn)
    return pool, conn


# ---------------------------------------------------------------------------
# Parser dataclass stubs (mirrors bitcoin_api.indexer.parser)
# ---------------------------------------------------------------------------

@dataclass
class ParsedOutput:
    vout: int
    value_sat: int
    script_type: str | None
    address: str | None


@dataclass
class ParsedInput:
    vin: int
    prev_txid: bytes
    prev_vout: int


@dataclass
class ParsedTransaction:
    txid: bytes
    tx_index: int
    version: int
    size: int
    vsize: int
    weight: int
    locktime: int
    fee_sat: int | None
    is_coinbase: bool
    outputs: list[ParsedOutput] = field(default_factory=list)
    inputs: list[ParsedInput] = field(default_factory=list)


@dataclass
class ParsedBlock:
    height: int
    hash: bytes
    prev_hash: bytes
    timestamp: int
    tx_count: int
    size: int
    weight: int
    transactions: list[ParsedTransaction] = field(default_factory=list)


def _coinbase_tx(txid: bytes = b"\x01" * 32) -> ParsedTransaction:
    """A minimal coinbase transaction with one output, no inputs."""
    return ParsedTransaction(
        txid=txid,
        tx_index=0,
        version=2,
        size=200,
        vsize=150,
        weight=600,
        locktime=0,
        fee_sat=0,
        is_coinbase=True,
        outputs=[ParsedOutput(vout=0, value_sat=625_000_000, script_type="witness_v1_taproot", address="bc1pminer")],
        inputs=[],
    )


def _regular_tx(txid: bytes = b"\x02" * 32) -> ParsedTransaction:
    """A minimal non-coinbase transaction with one input and one output."""
    return ParsedTransaction(
        txid=txid,
        tx_index=1,
        version=2,
        size=250,
        vsize=170,
        weight=680,
        locktime=0,
        fee_sat=1500,
        is_coinbase=False,
        outputs=[ParsedOutput(vout=0, value_sat=50_000, script_type="witness_v0_keyhash", address="bc1qrecv")],
        inputs=[ParsedInput(vin=0, prev_txid=b"\xaa" * 32, prev_vout=0)],
    )


def _sample_block(height: int = 800_000, txs=None) -> ParsedBlock:
    """Build a ParsedBlock with sensible defaults."""
    if txs is None:
        txs = [_coinbase_tx()]
    return ParsedBlock(
        height=height,
        hash=b"\xbb" * 32,
        prev_hash=b"\xcc" * 32,
        timestamp=1700000000,
        tx_count=len(txs),
        size=1_000_000,
        weight=4_000_000,
        transactions=txs,
    )


# ===================================================================
# _create_rpc
# ===================================================================

@patch("bitcoin_api.config.settings")
def test_create_rpc_returns_object(mock_settings):
    """_create_rpc() should construct a BitcoinRPC from main config settings."""
    mock_settings.bitcoin_rpc_host = "127.0.0.1"
    mock_settings.bitcoin_rpc_port = 8332
    mock_settings.bitcoin_rpc_user = "user"
    mock_settings.bitcoin_rpc_password = MagicMock()
    mock_settings.bitcoin_rpc_password.get_secret_value.return_value = "pass"
    mock_settings.bitcoin_datadir = None
    mock_settings.rpc_timeout = 30

    with patch("bitcoinlib_rpc.BitcoinRPC") as mock_rpc_cls:
        mock_rpc_cls.return_value = MagicMock(name="rpc_instance")
        from bitcoin_api.indexer.worker import _create_rpc
        result = _create_rpc()

    assert result is not None
    mock_rpc_cls.assert_called_once()


# ===================================================================
# _get_indexed_tip
# ===================================================================

@pytest.mark.asyncio
async def test_get_indexed_tip_returns_height_and_hash():
    """When the DB has a state row, return (tip_height, tip_hash)."""
    from bitcoin_api.indexer.worker import _get_indexed_tip

    tip_hash = b"\xab" * 32
    pool, conn = _make_mock_pool({"tip_height": 800_000, "tip_hash": tip_hash})
    height, h = await _get_indexed_tip(pool)
    assert height == 800_000
    assert h == tip_hash


@pytest.mark.asyncio
async def test_get_indexed_tip_returns_zero_when_empty():
    """When there is no state row, return (0, None)."""
    from bitcoin_api.indexer.worker import _get_indexed_tip

    pool, conn = _make_mock_pool(None)
    height, h = await _get_indexed_tip(pool)
    assert height == 0
    assert h is None


# ===================================================================
# _rpc_call_with_retry
# ===================================================================

@patch("bitcoin_api.indexer.worker.time")
def test_rpc_retry_succeeds_first_try(mock_time):
    """Should return the RPC result without sleeping when call succeeds."""
    from bitcoin_api.indexer.worker import _rpc_call_with_retry

    rpc = MagicMock()
    rpc.call.return_value = 800_000
    result = _rpc_call_with_retry(rpc, "getblockcount")
    assert result == 800_000
    rpc.call.assert_called_once_with("getblockcount")
    mock_time.sleep.assert_not_called()


@patch("bitcoin_api.indexer.worker.time")
def test_rpc_retry_succeeds_after_failures(mock_time):
    """Should retry on failure and eventually return the result."""
    from bitcoin_api.indexer.worker import _rpc_call_with_retry

    rpc = MagicMock()
    rpc.call.side_effect = [ConnectionError("down"), ConnectionError("down"), 800_000]
    result = _rpc_call_with_retry(rpc, "getblockcount", max_retries=5)
    assert result == 800_000
    assert rpc.call.call_count == 3
    assert mock_time.sleep.call_count == 2


@patch("bitcoin_api.indexer.worker.time")
def test_rpc_retry_raises_after_max_retries(mock_time):
    """Should raise after exhausting all retries."""
    from bitcoin_api.indexer.worker import _rpc_call_with_retry

    rpc = MagicMock()
    rpc.call.side_effect = ConnectionError("permanently down")
    with pytest.raises(ConnectionError, match="permanently down"):
        _rpc_call_with_retry(rpc, "getblockcount", max_retries=3)
    assert rpc.call.call_count == 3
    assert mock_time.sleep.call_count == 2


# ===================================================================
# sync_blocks
# ===================================================================

@pytest.mark.asyncio
@patch("bitcoin_api.indexer.worker._rpc_call_with_retry")
@patch("bitcoin_api.indexer.worker._get_indexed_tip", new_callable=AsyncMock)
@patch("bitcoin_api.indexer.worker.get_pool")
async def test_sync_blocks_noop_when_tip_equals_node(mock_gp, mock_tip, mock_rpc_retry):
    """sync_blocks returns 0 when indexed tip >= node height."""
    from bitcoin_api.indexer.worker import sync_blocks

    pool, _ = _make_mock_pool()
    mock_gp.return_value = pool
    mock_tip.return_value = (800_000, b"\xbb" * 32)
    mock_rpc_retry.return_value = 800_000  # node height same as tip

    rpc = MagicMock()
    result = await sync_blocks(rpc)
    assert result == 0


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.worker._index_block", new_callable=AsyncMock)
@patch("bitcoin_api.indexer.worker.detect_reorg", new_callable=AsyncMock)
@patch("bitcoin_api.indexer.worker.parse_block")
@patch("bitcoin_api.indexer.worker._rpc_call_with_retry")
@patch("bitcoin_api.indexer.worker._get_indexed_tip", new_callable=AsyncMock)
@patch("bitcoin_api.indexer.worker.get_pool")
async def test_sync_blocks_indexes_n_blocks(mock_gp, mock_tip, mock_rpc_retry, mock_parse, mock_reorg, mock_idx):
    """sync_blocks should index blocks from tip+1 to node height."""
    from bitcoin_api.indexer.worker import sync_blocks

    pool, conn = _make_mock_pool()
    mock_gp.return_value = pool
    mock_tip.return_value = (100, b"\xaa" * 32)

    # getblockcount returns 103 => 3 blocks to sync (101, 102, 103)
    mock_rpc_retry.side_effect = lambda rpc, method, *a, **kw: {
        "getblockcount": 103,
        "getblockhash": "hash_" + str(a[0]) if a else "hash",
        "getblock": {"height": a[0] if len(a) >= 1 else 0},
    }.get(method, None)

    mock_parse.return_value = _sample_block()
    mock_reorg.return_value = None  # no reorg
    mock_idx.return_value = {}

    rpc = MagicMock()
    result = await sync_blocks(rpc)
    assert result == 3
    assert mock_idx.await_count == 3


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.worker._index_block", new_callable=AsyncMock)
@patch("bitcoin_api.indexer.worker.detect_reorg", new_callable=AsyncMock)
@patch("bitcoin_api.indexer.worker.parse_block")
@patch("bitcoin_api.indexer.worker._rpc_call_with_retry")
@patch("bitcoin_api.indexer.worker._get_indexed_tip", new_callable=AsyncMock)
@patch("bitcoin_api.indexer.worker.get_pool")
async def test_sync_blocks_respects_shutdown(mock_gp, mock_tip, mock_rpc_retry, mock_parse, mock_reorg, mock_idx):
    """sync_blocks should stop early when shutdown event is set."""
    from bitcoin_api.indexer.worker import sync_blocks, _shutdown

    pool, conn = _make_mock_pool()
    mock_gp.return_value = pool
    mock_tip.return_value = (100, b"\xaa" * 32)
    mock_rpc_retry.side_effect = lambda rpc, method, *a, **kw: 200 if method == "getblockcount" else "hash"
    mock_parse.return_value = _sample_block()
    mock_reorg.return_value = None
    mock_idx.return_value = {}

    # Set shutdown before sync
    _shutdown.set()
    try:
        rpc = MagicMock()
        result = await sync_blocks(rpc)
        assert result == 0
    finally:
        _shutdown.clear()


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.worker._index_block", new_callable=AsyncMock)
@patch("bitcoin_api.indexer.worker.rollback_to_height", new_callable=AsyncMock)
@patch("bitcoin_api.indexer.worker.detect_reorg", new_callable=AsyncMock)
@patch("bitcoin_api.indexer.worker.parse_block")
@patch("bitcoin_api.indexer.worker._rpc_call_with_retry")
@patch("bitcoin_api.indexer.worker._get_indexed_tip", new_callable=AsyncMock)
@patch("bitcoin_api.indexer.worker.get_pool")
async def test_sync_blocks_detects_reorg(mock_gp, mock_tip, mock_rpc_retry, mock_parse, mock_reorg, mock_rollback, mock_idx):
    """sync_blocks should detect a reorg and trigger rollback."""
    from bitcoin_api.indexer.worker import sync_blocks

    pool, conn = _make_mock_pool()
    mock_gp.return_value = pool
    mock_tip.return_value = (100, b"\xaa" * 32)

    mock_rpc_retry.side_effect = lambda rpc, method, *a, **kw: {
        "getblockcount": 101,
        "getblockhash": "hash_reorg",
        "getblock": {"height": 101},
    }.get(method, None)

    mock_parse.return_value = _sample_block(height=101)
    # First call detects reorg at height 99, second call (after rollback re-fetch) returns None
    mock_reorg.side_effect = [99, None]
    mock_idx.return_value = {}

    rpc = MagicMock()
    result = await sync_blocks(rpc)
    assert result == 1
    mock_rollback.assert_awaited_once_with(conn, 99)


# ===================================================================
# _index_block
# ===================================================================

@pytest.mark.asyncio
@patch("bitcoin_api.indexer.worker.indexer_settings")
async def test_index_block_inserts_block_txs_outputs(mock_isettings):
    """_index_block should INSERT block, transactions, and outputs."""
    from bitcoin_api.indexer.worker import _index_block

    mock_isettings.reorg_depth = 100
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)  # no prev output found for inputs

    block = _sample_block(height=500, txs=[_coinbase_tx(), _regular_tx()])
    rpc = MagicMock()

    await _index_block(conn, block, rpc)

    # Block insert + 2 txs + 2 outputs + 1 input + spent-output-update +
    # address_summary upserts + undo insert + prune + indexer_state update
    assert conn.execute.await_count > 0
    # Verify block insert was first call
    first_call_sql = conn.execute.call_args_list[0][0][0]
    assert "INSERT INTO blocks" in first_call_sql


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.worker.indexer_settings")
async def test_index_block_updates_address_summary(mock_isettings):
    """_index_block should upsert address_summary for addresses seen in outputs."""
    from bitcoin_api.indexer.worker import _index_block

    mock_isettings.reorg_depth = 100
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)

    block = _sample_block(height=500, txs=[_coinbase_tx()])
    rpc = MagicMock()

    await _index_block(conn, block, rpc)

    # Find the address_summary upsert call
    sql_calls = [call[0][0] for call in conn.execute.call_args_list]
    assert any("address_summary" in s for s in sql_calls)


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.worker.indexer_settings")
async def test_index_block_stores_undo_data(mock_isettings):
    """_index_block should store undo data in block_undo."""
    from bitcoin_api.indexer.worker import _index_block

    mock_isettings.reorg_depth = 100
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)

    block = _sample_block(height=500, txs=[_coinbase_tx()])
    rpc = MagicMock()

    result = await _index_block(conn, block, rpc)

    assert isinstance(result, dict)
    assert result["height"] == 500
    sql_calls = [call[0][0] for call in conn.execute.call_args_list]
    assert any("block_undo" in s for s in sql_calls)


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.worker.indexer_settings")
async def test_index_block_handles_coinbase_no_inputs(mock_isettings):
    """Coinbase tx has no inputs — _index_block should not insert any tx_inputs rows."""
    from bitcoin_api.indexer.worker import _index_block

    mock_isettings.reorg_depth = 100
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)

    block = _sample_block(height=500, txs=[_coinbase_tx()])
    rpc = MagicMock()

    await _index_block(conn, block, rpc)

    sql_calls = [call[0][0] for call in conn.execute.call_args_list]
    assert not any("INSERT INTO tx_inputs" in s for s in sql_calls)


@pytest.mark.asyncio
@patch("bitcoin_api.indexer.worker.indexer_settings")
async def test_index_block_marks_spent_outputs(mock_isettings):
    """When a regular tx spends an output, _index_block should UPDATE tx_outputs to set spent_txid."""
    from bitcoin_api.indexer.worker import _index_block

    mock_isettings.reorg_depth = 100
    conn = AsyncMock()
    # Simulate finding the spent output with an address and value
    conn.fetchrow = AsyncMock(return_value={"address": "bc1qspent", "value": 100_000})

    block = _sample_block(height=500, txs=[_coinbase_tx(), _regular_tx()])
    rpc = MagicMock()

    undo = await _index_block(conn, block, rpc)

    # The fetchrow call is the UPDATE ... RETURNING for marking spent
    fetchrow_calls = [call[0][0] for call in conn.fetchrow.call_args_list]
    assert any("UPDATE tx_outputs SET spent_txid" in s for s in fetchrow_calls)
    # Undo data should record the spent update
    assert len(undo["spent_updates"]) == 1


# ===================================================================
# _check_node_version
# ===================================================================

def test_check_node_version_warns_old(caplog):
    """Should log a warning when Bitcoin Core version < 220000."""
    from bitcoin_api.indexer.worker import _check_node_version

    rpc = MagicMock()
    rpc.call.return_value = {"version": 210000}

    with caplog.at_level(logging.WARNING, logger="bitcoin_api.indexer.worker"):
        _check_node_version(rpc)

    assert any("below 220000" in msg for msg in caplog.messages)


def test_check_node_version_info_new(caplog):
    """Should log info (not warning) when Bitcoin Core version >= 220000."""
    from bitcoin_api.indexer.worker import _check_node_version

    rpc = MagicMock()
    rpc.call.return_value = {"version": 270000}

    with caplog.at_level(logging.INFO, logger="bitcoin_api.indexer.worker"):
        _check_node_version(rpc)

    assert any("270000" in msg for msg in caplog.messages)
    assert not any("below 220000" in msg for msg in caplog.messages)


def test_check_node_version_handles_rpc_failure(caplog):
    """Should log a warning and not raise when RPC call fails."""
    from bitcoin_api.indexer.worker import _check_node_version

    rpc = MagicMock()
    rpc.call.side_effect = ConnectionError("node unreachable")

    with caplog.at_level(logging.WARNING, logger="bitcoin_api.indexer.worker"):
        _check_node_version(rpc)  # should not raise

    assert any("Could not check" in msg for msg in caplog.messages)


# ===================================================================
# request_shutdown
# ===================================================================

def test_request_shutdown_sets_event():
    """request_shutdown() should set the module-level _shutdown event."""
    from bitcoin_api.indexer.worker import request_shutdown, _shutdown

    _shutdown.clear()
    assert not _shutdown.is_set()
    request_shutdown()
    assert _shutdown.is_set()
    _shutdown.clear()  # clean up
