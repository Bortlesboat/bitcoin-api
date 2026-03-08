"""Tests for indexer reorg detection and rollback."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from bitcoin_api.indexer.reorg import detect_reorg, rollback_to_height
from bitcoin_api.indexer.parser import ParsedBlock


def _make_parsed_block(height=100, hash_hex="aa" * 32, prev_hash_hex="bb" * 32):
    """Create a minimal ParsedBlock for testing."""
    return ParsedBlock(
        height=height,
        hash=bytes.fromhex(hash_hex),
        prev_hash=bytes.fromhex(prev_hash_hex),
        timestamp=1700000000,
        tx_count=1,
        size=1000,
        weight=4000,
        transactions=[],
    )


@pytest.fixture
def mock_conn():
    """Create a mock asyncpg connection."""
    conn = AsyncMock()
    return conn


# --- detect_reorg tests ---

@pytest.mark.asyncio
async def test_no_reorg_matching_hash(mock_conn):
    """No reorg when prev_hash matches stored block."""
    parent_hash = bytes.fromhex("bb" * 32)
    mock_conn.fetchrow.return_value = {"hash": parent_hash}
    block = _make_parsed_block(height=100, prev_hash_hex="bb" * 32)
    result = await detect_reorg(mock_conn, block)
    assert result is None


@pytest.mark.asyncio
async def test_reorg_detected_mismatched_hash(mock_conn):
    """Reorg detected when prev_hash doesn't match."""
    mock_conn.fetchrow.return_value = {"hash": bytes.fromhex("cc" * 32)}
    block = _make_parsed_block(height=100, prev_hash_hex="bb" * 32)
    result = await detect_reorg(mock_conn, block)
    assert result is not None
    assert isinstance(result, int)


@pytest.mark.asyncio
async def test_no_reorg_genesis(mock_conn):
    """No reorg check for genesis block."""
    block = _make_parsed_block(height=0)
    result = await detect_reorg(mock_conn, block)
    assert result is None
    mock_conn.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_no_reorg_parent_not_in_db(mock_conn):
    """No reorg when parent block not found (initial sync)."""
    mock_conn.fetchrow.return_value = None
    block = _make_parsed_block(height=500)
    result = await detect_reorg(mock_conn, block)
    assert result is None


# --- rollback_to_height tests ---

@pytest.mark.asyncio
async def test_rollback_restores_spent_outputs(mock_conn):
    """Rollback restores spent_txid=NULL on previously spent outputs."""
    undo_data = {
        "height": 101,
        "spent_updates": [{"txid": "aa" * 32, "vout": 0}],
        "address_deltas": {},
    }
    mock_conn.fetch.return_value = [
        {"height": 101, "undo_data": undo_data}
    ]
    mock_conn.fetchrow.return_value = {"height": 100, "hash": bytes.fromhex("bb" * 32)}
    mock_conn.execute.return_value = "DELETE 1"

    await rollback_to_height(mock_conn, 100)

    # Verify spent output restoration
    calls = [str(c) for c in mock_conn.execute.call_args_list]
    assert any("spent_txid = NULL" in c for c in calls)


@pytest.mark.asyncio
async def test_rollback_reverses_address_deltas(mock_conn):
    """Rollback decrements address_summary counters."""
    undo_data = {
        "height": 101,
        "spent_updates": [],
        "address_deltas": {
            "bc1qtest": {"received": 50000000, "sent": 0, "tx_count": 1}
        },
    }
    mock_conn.fetch.return_value = [
        {"height": 101, "undo_data": undo_data}
    ]
    mock_conn.fetchrow.return_value = {"height": 100, "hash": bytes.fromhex("bb" * 32)}
    mock_conn.execute.return_value = "DELETE 1"

    await rollback_to_height(mock_conn, 100)

    calls = [str(c) for c in mock_conn.execute.call_args_list]
    assert any("total_received = total_received" in c for c in calls)


@pytest.mark.asyncio
async def test_rollback_deletes_blocks(mock_conn):
    """Rollback deletes blocks above target height."""
    mock_conn.fetch.return_value = []
    mock_conn.fetchrow.return_value = {"height": 100, "hash": bytes.fromhex("bb" * 32)}
    mock_conn.execute.return_value = "DELETE 1"

    await rollback_to_height(mock_conn, 100)

    calls = [str(c) for c in mock_conn.execute.call_args_list]
    assert any("DELETE FROM blocks" in c for c in calls)


@pytest.mark.asyncio
async def test_rollback_updates_indexer_state(mock_conn):
    """Rollback updates indexer_state to target height."""
    mock_conn.fetch.return_value = []
    mock_conn.fetchrow.return_value = {"height": 100, "hash": bytes.fromhex("bb" * 32)}
    mock_conn.execute.return_value = "DELETE 1"

    await rollback_to_height(mock_conn, 100)

    calls = [str(c) for c in mock_conn.execute.call_args_list]
    assert any("indexer_state" in c for c in calls)


@pytest.mark.asyncio
async def test_rollback_no_undo_data(mock_conn):
    """Rollback with no undo data still deletes blocks."""
    mock_conn.fetch.return_value = []
    mock_conn.fetchrow.return_value = {"height": 50, "hash": bytes.fromhex("cc" * 32)}
    mock_conn.execute.return_value = "DELETE 0"

    await rollback_to_height(mock_conn, 50)
    # Should not raise


@pytest.mark.asyncio
async def test_rollback_cleans_zero_tx_addresses(mock_conn):
    """Rollback removes addresses with tx_count <= 0."""
    undo_data = {
        "height": 101,
        "spent_updates": [],
        "address_deltas": {
            "bc1qonce": {"received": 10000, "sent": 0, "tx_count": 1}
        },
    }
    mock_conn.fetch.return_value = [
        {"height": 101, "undo_data": undo_data}
    ]
    mock_conn.fetchrow.return_value = {"height": 100, "hash": bytes.fromhex("bb" * 32)}
    mock_conn.execute.return_value = "DELETE 1"

    await rollback_to_height(mock_conn, 100)

    calls = [str(c) for c in mock_conn.execute.call_args_list]
    assert any("tx_count <= 0" in c for c in calls)


@pytest.mark.asyncio
async def test_rollback_to_zero(mock_conn):
    """Rollback to height 0 when no blocks remain."""
    mock_conn.fetch.return_value = []
    mock_conn.fetchrow.return_value = None  # No block at height 0
    mock_conn.execute.return_value = "DELETE 1"

    await rollback_to_height(mock_conn, 0)

    calls = [str(c) for c in mock_conn.execute.call_args_list]
    assert any("tip_height = 0" in c for c in calls)


@pytest.mark.asyncio
async def test_rollback_multiple_blocks(mock_conn):
    """Rollback multiple blocks reverses all of them."""
    undo_data_102 = {
        "height": 102,
        "spent_updates": [{"txid": "dd" * 32, "vout": 0}],
        "address_deltas": {"bc1q102": {"received": 100, "sent": 0, "tx_count": 1}},
    }
    undo_data_101 = {
        "height": 101,
        "spent_updates": [{"txid": "ee" * 32, "vout": 1}],
        "address_deltas": {"bc1q101": {"received": 200, "sent": 0, "tx_count": 1}},
    }
    mock_conn.fetch.return_value = [
        {"height": 102, "undo_data": undo_data_102},
        {"height": 101, "undo_data": undo_data_101},
    ]
    mock_conn.fetchrow.return_value = {"height": 100, "hash": bytes.fromhex("bb" * 32)}
    mock_conn.execute.return_value = "DELETE 2"

    await rollback_to_height(mock_conn, 100)

    # Should have processed both undo entries
    calls = [str(c) for c in mock_conn.execute.call_args_list]
    spent_restores = [c for c in calls if "spent_txid = NULL" in c]
    assert len(spent_restores) == 2


# --- detect_reorg with RPC (fork point detection) ---

@pytest.mark.asyncio
async def test_detect_reorg_finds_fork_point_with_rpc(mock_conn):
    """detect_reorg walks back with RPC to find actual fork point."""
    # Height 100: mismatch (reorg). Height 99: mismatch. Height 98: match.
    stored_hashes = {
        99: bytes.fromhex("cc" * 32),  # different from node
        98: bytes.fromhex("dd" * 32),  # matches node
    }
    mock_conn.fetchrow.side_effect = [
        {"hash": bytes.fromhex("cc" * 32)},  # parent check at 99 — mismatch triggers reorg
        {"hash": stored_hashes[99]},          # walk-back check at 99
        {"hash": stored_hashes[98]},          # walk-back check at 98
    ]

    rpc = MagicMock()
    rpc.call.side_effect = lambda method, h: {
        99: "aa" * 32,  # different from stored cc*32
        98: "dd" * 32,  # matches stored dd*32
    }.get(h, "00" * 32)

    block = _make_parsed_block(height=100, prev_hash_hex="bb" * 32)
    result = await detect_reorg(mock_conn, block, rpc=rpc)
    assert result == 98


@pytest.mark.asyncio
async def test_detect_reorg_without_rpc_falls_back(mock_conn):
    """Without RPC, detect_reorg falls back to parent_height - 1."""
    mock_conn.fetchrow.side_effect = [
        {"hash": bytes.fromhex("cc" * 32)},  # mismatch
        {"hash": bytes.fromhex("dd" * 32)},  # walk-back (no RPC to verify)
    ]
    block = _make_parsed_block(height=100, prev_hash_hex="bb" * 32)
    result = await detect_reorg(mock_conn, block, rpc=None)
    assert result == 98  # parent_height - 1


# --- rollback first_seen/last_seen recalculation ---

@pytest.mark.asyncio
async def test_rollback_recalculates_first_last_seen(mock_conn):
    """After rollback, first_seen/last_seen are recalculated from remaining txs."""
    undo_data = {
        "height": 101,
        "spent_updates": [],
        "address_deltas": {
            "bc1qrecalc": {"received": 50000000, "sent": 0, "tx_count": 1}
        },
    }
    mock_conn.fetch.return_value = [
        {"height": 101, "undo_data": undo_data}
    ]
    mock_conn.fetchrow.return_value = {"height": 100, "hash": bytes.fromhex("bb" * 32)}
    mock_conn.execute.return_value = "DELETE 1"

    await rollback_to_height(mock_conn, 100)

    calls = [str(c) for c in mock_conn.execute.call_args_list]
    # Should recalculate first_seen/last_seen via subquery
    recalc_calls = [c for c in calls if "min_height" in c.lower() or "MIN(t.block_height)" in c]
    assert len(recalc_calls) >= 1, f"Expected recalculation query, got: {calls}"
