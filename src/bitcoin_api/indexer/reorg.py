"""Reorg detection and rollback for the indexer."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg

from .parser import ParsedBlock

log = logging.getLogger(__name__)


async def detect_reorg(conn: asyncpg.Connection, parsed_block: ParsedBlock, rpc=None) -> int | None:
    """Check if the new block's prev_hash matches our stored tip.

    If rpc is provided, walks back to find the actual fork point by comparing
    stored hashes against the node's chain. Otherwise falls back to
    parent_height - 1.

    Returns:
        Fork height to rollback to, or None if no reorg detected.
    """
    if parsed_block.height == 0:
        return None

    parent_height = parsed_block.height - 1
    row = await conn.fetchrow(
        "SELECT hash FROM blocks WHERE height = $1", parent_height,
    )

    if row is None:
        # We don't have the parent block — might be starting from scratch
        return None

    stored_hash = row["hash"]
    if stored_hash == parsed_block.prev_hash:
        return None  # No reorg

    # Reorg detected — find fork point
    log.warning(
        "Reorg detected at height %d: expected prev_hash %s, got %s",
        parsed_block.height, stored_hash.hex(), parsed_block.prev_hash.hex(),
    )

    if rpc is not None:
        # Walk back, comparing our stored hashes to the node's chain
        check_height = parent_height
        while check_height >= max(0, parent_height - 100):
            row = await conn.fetchrow("SELECT hash FROM blocks WHERE height = $1", check_height)
            if row is None:
                break
            try:
                node_hash = rpc.call("getblockhash", check_height)
                if row["hash"] == bytes.fromhex(node_hash):
                    # Found the fork point — this height is still valid
                    return check_height
            except Exception:
                log.warning("RPC failed during reorg walk-back at height %d", check_height)
                break
            check_height -= 1

    # Fallback: rollback to parent - 1
    return parent_height - 1


async def rollback_to_height(conn: asyncpg.Connection, target_height: int) -> None:
    """Rollback the index to target_height, restoring spent outputs.

    Uses block_undo data to reverse address_summary changes and
    restore spent_txid/spent_vin on outputs. After rolling back,
    recalculates first_seen/last_seen from remaining data.
    """
    # Get all blocks above target
    rows = await conn.fetch(
        "SELECT height, undo_data FROM block_undo WHERE height > $1 ORDER BY height DESC",
        target_height,
    )

    affected_addresses: set[str] = set()

    for row in rows:
        height = row["height"]
        undo = json.loads(row["undo_data"]) if isinstance(row["undo_data"], str) else row["undo_data"]

        log.info("Rolling back block %d", height)

        # Restore spent outputs
        for spent in undo.get("spent_updates", []):
            await conn.execute(
                """UPDATE tx_outputs SET spent_txid = NULL, spent_vin = NULL
                   WHERE txid = $1 AND vout = $2""",
                bytes.fromhex(spent["txid"]), spent["vout"],
            )

        # Reverse address_summary deltas
        for addr, delta in undo.get("address_deltas", {}).items():
            affected_addresses.add(addr)
            await conn.execute(
                """UPDATE address_summary SET
                       total_received = total_received - $2,
                       total_sent = total_sent - $3,
                       tx_count = tx_count - $4
                   WHERE address = $1""",
                addr, delta["received"], delta["sent"], delta["tx_count"],
            )
            # Clean up addresses with zero tx_count
            await conn.execute(
                "DELETE FROM address_summary WHERE address = $1 AND tx_count <= 0",
                addr,
            )

    # Delete blocks above target (CASCADE handles txs, outputs, inputs, undo)
    deleted = await conn.execute("DELETE FROM blocks WHERE height > $1", target_height)
    log.info("Rolled back to height %d (%s)", target_height, deleted)

    # Recalculate first_seen/last_seen for affected addresses from remaining data
    for addr in affected_addresses:
        await conn.execute(
            """UPDATE address_summary SET
                   first_seen = sub.min_height,
                   last_seen = sub.max_height
               FROM (
                   SELECT MIN(t.block_height) AS min_height, MAX(t.block_height) AS max_height
                   FROM transactions t
                   WHERE t.txid IN (
                       SELECT txid FROM tx_outputs WHERE address = $1
                       UNION
                       SELECT ti.txid FROM tx_inputs ti
                       JOIN tx_outputs to2 ON ti.prev_txid = to2.txid AND ti.prev_vout = to2.vout
                       WHERE to2.address = $1
                   )
               ) sub
               WHERE address = $1""",
            addr,
        )

    # Update indexer state
    tip_row = await conn.fetchrow(
        "SELECT height, hash FROM blocks WHERE height = $1", target_height,
    )
    if tip_row:
        await conn.execute(
            "UPDATE indexer_state SET tip_height = $1, tip_hash = $2 WHERE id = 1",
            tip_row["height"], tip_row["hash"],
        )
    else:
        await conn.execute(
            "UPDATE indexer_state SET tip_height = 0, tip_hash = NULL WHERE id = 1",
        )
