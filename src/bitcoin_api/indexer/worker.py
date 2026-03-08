"""Indexer sync worker — fetches blocks from Bitcoin Core and indexes them into Postgres."""

from __future__ import annotations

import asyncio
import json
import logging
import time

from .config import indexer_settings
from .db import get_pool
from .parser import parse_block
from .reorg import detect_reorg, rollback_to_height

log = logging.getLogger(__name__)

# Shutdown signal
_shutdown = asyncio.Event()


def _create_rpc():
    """Create a dedicated RPC connection for the indexer."""
    from bitcoin_api.config import settings
    from bitcoinlib_rpc import BitcoinRPC
    return BitcoinRPC(
        host=settings.bitcoin_rpc_host,
        port=settings.bitcoin_rpc_port,
        user=settings.bitcoin_rpc_user,
        password=settings.bitcoin_rpc_password.get_secret_value() if settings.bitcoin_rpc_password else None,
        datadir=settings.bitcoin_datadir,
        timeout=settings.rpc_timeout,
    )


async def _get_indexed_tip(pool) -> tuple[int, bytes | None]:
    """Read current indexed tip from Postgres."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT tip_height, tip_hash FROM indexer_state WHERE id = 1")
        if row:
            return row["tip_height"], row["tip_hash"]
        return 0, None


async def _index_block(conn, parsed_block, rpc) -> dict:
    """Index a single parsed block within an existing transaction.

    Returns undo_data dict for reorg rollback.
    """
    undo_data = {"height": parsed_block.height, "spent_updates": [], "address_deltas": {}}

    # Insert block
    await conn.execute(
        """INSERT INTO blocks (height, hash, prev_hash, timestamp, tx_count, size, weight)
           VALUES ($1, $2, $3, $4, $5, $6, $7)
           ON CONFLICT (height) DO NOTHING""",
        parsed_block.height, parsed_block.hash, parsed_block.prev_hash,
        parsed_block.timestamp, parsed_block.tx_count, parsed_block.size, parsed_block.weight,
    )

    address_deltas: dict[str, dict] = {}

    for tx in parsed_block.transactions:
        # Insert transaction
        await conn.execute(
            """INSERT INTO transactions (txid, block_height, tx_index, version, size, vsize, weight, locktime, fee, is_coinbase)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
               ON CONFLICT DO NOTHING""",
            tx.txid, parsed_block.height, tx.tx_index, tx.version,
            tx.size, tx.vsize, tx.weight, tx.locktime, tx.fee_sat, tx.is_coinbase,
        )

        # Track which addresses are involved in this tx
        tx_addresses: set[str] = set()

        # Insert outputs
        for out in tx.outputs:
            await conn.execute(
                """INSERT INTO tx_outputs (txid, vout, value, script_type, address)
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT DO NOTHING""",
                tx.txid, out.vout, out.value_sat, out.script_type, out.address,
            )
            if out.address:
                tx_addresses.add(out.address)
                delta = address_deltas.setdefault(out.address, {"received": 0, "sent": 0, "txids": set()})
                delta["received"] += out.value_sat
                delta["txids"].add(tx.txid)

        # Insert inputs and mark spent outputs
        for inp in tx.inputs:
            await conn.execute(
                """INSERT INTO tx_inputs (txid, vin, prev_txid, prev_vout)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT DO NOTHING""",
                tx.txid, inp.vin, inp.prev_txid, inp.prev_vout,
            )
            # Mark the referenced output as spent
            prev_row = await conn.fetchrow(
                """UPDATE tx_outputs SET spent_txid = $1, spent_vin = $2
                   WHERE txid = $3 AND vout = $4 AND spent_txid IS NULL
                   RETURNING address, value""",
                tx.txid, inp.vin, inp.prev_txid, inp.prev_vout,
            )
            if prev_row and prev_row["address"]:
                addr = prev_row["address"]
                tx_addresses.add(addr)
                delta = address_deltas.setdefault(addr, {"received": 0, "sent": 0, "txids": set()})
                delta["sent"] += prev_row["value"]
                delta["txids"].add(tx.txid)
                undo_data["spent_updates"].append({
                    "txid": inp.prev_txid.hex(),
                    "vout": inp.prev_vout,
                })

    # Update address_summary
    for addr, delta in address_deltas.items():
        tx_count = len(delta["txids"])
        await conn.execute(
            """INSERT INTO address_summary (address, total_received, total_sent, tx_count, first_seen, last_seen)
               VALUES ($1, $2, $3, $4, $5, $5)
               ON CONFLICT (address) DO UPDATE SET
                   total_received = address_summary.total_received + $2,
                   total_sent = address_summary.total_sent + $3,
                   tx_count = address_summary.tx_count + $4,
                   first_seen = LEAST(address_summary.first_seen, $5),
                   last_seen = GREATEST(address_summary.last_seen, $5)""",
            addr, delta["received"], delta["sent"], tx_count, parsed_block.height,
        )
        undo_data["address_deltas"][addr] = {
            "received": delta["received"],
            "sent": delta["sent"],
            "tx_count": tx_count,
        }

    # Store undo data (serialize sets as lists for JSON)
    undo_json = json.dumps(undo_data, default=lambda o: o.hex() if isinstance(o, bytes) else list(o) if isinstance(o, set) else o)
    await conn.execute(
        """INSERT INTO block_undo (height, undo_data) VALUES ($1, $2::jsonb)
           ON CONFLICT (height) DO UPDATE SET undo_data = $2::jsonb""",
        parsed_block.height, undo_json,
    )

    # Prune old undo data beyond reorg_depth
    prune_below = parsed_block.height - indexer_settings.reorg_depth
    if prune_below > 0:
        await conn.execute("DELETE FROM block_undo WHERE height < $1", prune_below)

    # Update indexer state
    await conn.execute(
        """UPDATE indexer_state SET tip_height = $1, tip_hash = $2, last_block_at = NOW()
           WHERE id = 1""",
        parsed_block.height, parsed_block.hash,
    )

    return undo_data


def _rpc_call_with_retry(rpc, method: str, *args, max_retries: int = 5) -> object:
    """Call RPC with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return rpc.call(method, *args)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = min(2 ** attempt, 16)
            log.warning("RPC %s failed (attempt %d/%d): %s — retrying in %ds",
                        method, attempt + 1, max_retries, e, wait)
            time.sleep(wait)


async def sync_blocks(rpc) -> int:
    """Sync blocks from current tip to node tip. Returns number of blocks synced."""
    pool = get_pool()
    tip_height, tip_hash = await _get_indexed_tip(pool)

    node_height = _rpc_call_with_retry(rpc, "getblockcount")
    if tip_height >= node_height:
        return 0

    batch_size = indexer_settings.batch_size
    synced = 0
    start_time = time.monotonic()
    start_height = tip_height + 1

    for batch_start in range(start_height, node_height + 1, batch_size):
        if _shutdown.is_set():
            break

        batch_end = min(batch_start + batch_size, node_height + 1)

        for height in range(batch_start, batch_end):
            if _shutdown.is_set():
                break

            block_hash = _rpc_call_with_retry(rpc, "getblockhash", height)
            block_data = _rpc_call_with_retry(rpc, "getblock", block_hash, 2)
            parsed = parse_block(block_data)

            async with pool.acquire() as conn:
                async with conn.transaction():
                    # Check for reorg
                    if height > 0:
                        reorg_height = await detect_reorg(conn, parsed, rpc)
                        if reorg_height is not None:
                            log.warning("Reorg detected at height %d, rolling back to %d", height, reorg_height)
                            await rollback_to_height(conn, reorg_height)
                            # Re-fetch after rollback
                            block_hash = _rpc_call_with_retry(rpc, "getblockhash", reorg_height + 1)
                            block_data = _rpc_call_with_retry(rpc, "getblock", block_hash, 2)
                            parsed = parse_block(block_data)

                    await _index_block(conn, parsed, rpc)
                    synced += 1

            # Progress logging
            if synced > 0 and synced % 1000 == 0:
                elapsed = time.monotonic() - start_time
                rate = synced / elapsed if elapsed > 0 else 0
                remaining = (node_height - (start_height + synced)) / rate if rate > 0 else 0
                log.info(
                    "Indexed %d blocks (%d → %d), %.1f blocks/sec, ~%.0f min remaining",
                    synced, start_height, start_height + synced - 1, rate, remaining / 60,
                )
                # Update rate in state
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE indexer_state SET blocks_per_sec = $1 WHERE id = 1", rate,
                    )

    elapsed = time.monotonic() - start_time
    if synced > 0:
        rate = synced / elapsed if elapsed > 0 else 0
        log.info("Sync batch complete: %d blocks in %.1fs (%.1f blocks/sec)", synced, elapsed, rate)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE indexer_state SET blocks_per_sec = $1 WHERE id = 1", rate)

    return synced


async def _zmq_listener():
    """Listen for ZMQ hashblock notifications and trigger sync."""
    try:
        import zmq
        import zmq.asyncio
    except ImportError:
        log.warning("pyzmq not installed — falling back to polling only")
        return

    rpc = _create_rpc()
    backoff = 1

    while not _shutdown.is_set():
        ctx = zmq.asyncio.Context()
        sock = ctx.socket(zmq.SUB)
        try:
            sock.connect(indexer_settings.zmq_endpoint)
            sock.subscribe(b"hashblock")
            log.info("ZMQ listener connected to %s", indexer_settings.zmq_endpoint)
            backoff = 1  # reset on successful connect

            while not _shutdown.is_set():
                try:
                    if await asyncio.wait_for(sock.recv_multipart(), timeout=10.0):
                        log.debug("ZMQ hashblock notification received")
                        await sync_blocks(rpc)
                        backoff = 1  # reset on successful message
                except asyncio.TimeoutError:
                    await sync_blocks(rpc)
        except Exception:
            log.exception("ZMQ listener error — reconnecting in %ds", backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
        finally:
            sock.close()
            ctx.term()


async def _polling_loop():
    """Fallback polling loop when ZMQ is unavailable."""
    rpc = _create_rpc()
    log.info("Starting polling sync loop (10s interval)")

    while not _shutdown.is_set():
        try:
            await sync_blocks(rpc)
        except Exception:
            log.exception("Sync error in polling loop")
        await asyncio.sleep(10)


def _check_node_version(rpc) -> None:
    """Log a warning if Bitcoin Core is older than v22.0 (missing fee data in verbosity=2)."""
    try:
        info = rpc.call("getnetworkinfo")
        version = info.get("version", 0)
        if version < 220000:
            log.warning(
                "Bitcoin Core version %d is below 220000 (v22.0). "
                "Fee data in verbosity=2 blocks may be unavailable.", version,
            )
        else:
            log.info("Bitcoin Core version: %d", version)
    except Exception:
        log.warning("Could not check Bitcoin Core version")


async def start_worker():
    """Start the indexer worker. Initial sync + ZMQ/polling listener."""
    pool = get_pool()

    # Mark sync start
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE indexer_state SET started_at = NOW() WHERE id = 1",
        )

    rpc = _create_rpc()
    _check_node_version(rpc)

    log.info("Starting initial sync...")
    try:
        await sync_blocks(rpc)
    except Exception:
        log.exception("Initial sync failed — will retry in live mode")
    log.info("Initial sync complete, switching to live mode")

    # Try ZMQ, fall back to polling
    try:
        import zmq  # noqa: F401
        await _zmq_listener()
    except ImportError:
        await _polling_loop()


def request_shutdown():
    """Signal the worker to stop."""
    _shutdown.set()
