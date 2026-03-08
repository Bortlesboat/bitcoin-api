"""Address query service for the indexer."""

from __future__ import annotations

import logging

from ..db import get_pool

log = logging.getLogger(__name__)


async def get_address_balance(address: str) -> dict | None:
    """Get balance and stats for an address from the index."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM address_summary WHERE address = $1", address,
        )
        if row is None:
            return None
        return {
            "address": address,
            "total_received": row["total_received"],
            "total_sent": row["total_sent"],
            "balance": row["total_received"] - row["total_sent"],
            "tx_count": row["tx_count"],
            "first_seen_height": row["first_seen"],
            "last_seen_height": row["last_seen"],
        }


async def get_address_history(
    address: str, *, offset: int = 0, limit: int = 25,
) -> dict:
    """Get paginated transaction history for an address.

    Returns transactions where the address appears as input or output,
    with the net value change for each.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        # Count total transactions
        total = await conn.fetchval(
            """SELECT COUNT(DISTINCT t.txid) FROM transactions t
               WHERE t.txid IN (
                   SELECT txid FROM tx_outputs WHERE address = $1
                   UNION
                   SELECT ti.txid FROM tx_inputs ti
                   JOIN tx_outputs to2 ON ti.prev_txid = to2.txid AND ti.prev_vout = to2.vout
                   WHERE to2.address = $1
               )""",
            address,
        )

        # Get transactions with net value change
        rows = await conn.fetch(
            """WITH addr_txids AS (
                   SELECT txid FROM tx_outputs WHERE address = $1
                   UNION
                   SELECT ti.txid FROM tx_inputs ti
                   JOIN tx_outputs to2 ON ti.prev_txid = to2.txid AND ti.prev_vout = to2.vout
                   WHERE to2.address = $1
               )
               SELECT t.txid, t.block_height, t.tx_index, t.fee, b.timestamp,
                      COALESCE((SELECT SUM(value) FROM tx_outputs WHERE txid = t.txid AND address = $1), 0)
                      - COALESCE((SELECT SUM(to3.value) FROM tx_inputs ti2
                                  JOIN tx_outputs to3 ON ti2.prev_txid = to3.txid AND ti2.prev_vout = to3.vout
                                  WHERE ti2.txid = t.txid AND to3.address = $1), 0) AS value_change
               FROM transactions t
               JOIN blocks b ON t.block_height = b.height
               WHERE t.txid IN (SELECT txid FROM addr_txids)
               ORDER BY t.block_height DESC, t.tx_index DESC
               OFFSET $2 LIMIT $3""",
            address, offset, limit,
        )

        transactions = []
        for row in rows:
            transactions.append({
                "txid": row["txid"].hex(),
                "block_height": row["block_height"],
                "tx_index": row["tx_index"],
                "value_change": row["value_change"],
                "fee": row["fee"],
                "timestamp": row["timestamp"],
            })

        return {
            "address": address,
            "transactions": transactions,
            "total": total or 0,
            "offset": offset,
            "limit": limit,
        }
