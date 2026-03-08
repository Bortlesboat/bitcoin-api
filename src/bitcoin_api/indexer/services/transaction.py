"""Transaction query service for the indexer."""

from __future__ import annotations

import logging

from ..db import get_pool

log = logging.getLogger(__name__)


async def get_transaction(txid_hex: str) -> dict | None:
    """Get enriched transaction detail from the index."""
    pool = get_pool()
    txid_bytes = bytes.fromhex(txid_hex)

    async with pool.acquire() as conn:
        # Get transaction
        tx_row = await conn.fetchrow(
            """SELECT t.*, b.hash as block_hash, b.timestamp
               FROM transactions t
               JOIN blocks b ON t.block_height = b.height
               WHERE t.txid = $1""",
            txid_bytes,
        )
        if tx_row is None:
            return None

        # Get outputs
        output_rows = await conn.fetch(
            """SELECT vout, value, script_type, address, spent_txid IS NOT NULL as spent
               FROM tx_outputs WHERE txid = $1 ORDER BY vout""",
            txid_bytes,
        )

        # Get inputs with resolved addresses/values
        input_rows = await conn.fetch(
            """SELECT ti.vin, ti.prev_txid, ti.prev_vout, to2.address, to2.value
               FROM tx_inputs ti
               LEFT JOIN tx_outputs to2 ON ti.prev_txid = to2.txid AND ti.prev_vout = to2.vout
               WHERE ti.txid = $1 ORDER BY ti.vin""",
            txid_bytes,
        )

        inputs = [
            {
                "prev_txid": row["prev_txid"].hex(),
                "prev_vout": row["prev_vout"],
                "address": row["address"],
                "value": row["value"],
            }
            for row in input_rows
        ]

        outputs = [
            {
                "vout": row["vout"],
                "value": row["value"],
                "address": row["address"],
                "script_type": row["script_type"],
                "spent": row["spent"],
            }
            for row in output_rows
        ]

        return {
            "txid": txid_hex,
            "block_height": tx_row["block_height"],
            "block_hash": tx_row["block_hash"].hex(),
            "tx_index": tx_row["tx_index"],
            "version": tx_row["version"],
            "size": tx_row["size"],
            "vsize": tx_row["vsize"],
            "weight": tx_row["weight"],
            "locktime": tx_row["locktime"],
            "fee": tx_row["fee"],
            "is_coinbase": tx_row["is_coinbase"],
            "input_count": len(inputs),
            "output_count": len(outputs),
            "inputs": inputs,
            "outputs": outputs,
        }
