"""SSE stream endpoints: /stream/blocks, /stream/fees."""

import asyncio
import json
import time

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from bitcoinlib_rpc import BitcoinRPC

from ..auth import require_api_key
from ..cache import cached_block_count, cached_fee_estimates, cached_blockchain_info
from ..dependencies import get_rpc

router = APIRouter(prefix="/stream", tags=["Streams"])

_active_whale_streams: int = 0
_MAX_WHALE_STREAMS: int = 20


async def _block_event_generator(rpc: BitcoinRPC):
    """Yield SSE events when new blocks are detected."""
    last_height = cached_block_count(rpc)
    keepalive_interval = 60
    poll_interval = 5
    last_keepalive = time.time()

    yield f"event: connected\ndata: {json.dumps({'height': last_height})}\n\n"

    while True:
        await asyncio.sleep(poll_interval)

        try:
            current_height = cached_block_count(rpc)
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': 'Node temporarily unavailable'})}\n\n"
            current_height = last_height

        if current_height > last_height:
            info = cached_blockchain_info(rpc)
            for h in range(last_height + 1, current_height + 1):
                event_data = {
                    "height": h,
                    "chain": info.get("chain", "main"),
                    "timestamp": int(time.time()),
                }
                yield f"event: block\ndata: {json.dumps(event_data)}\n\n"
            last_height = current_height

        if time.time() - last_keepalive >= keepalive_interval:
            yield ": keepalive\n\n"
            last_keepalive = time.time()


async def _fee_event_generator(rpc: BitcoinRPC):
    """Yield SSE fee updates every 30 seconds."""
    keepalive_interval = 60
    fee_interval = 30
    last_keepalive = time.time()

    yield f"event: connected\ndata: {json.dumps({'status': 'ok'})}\n\n"

    while True:
        await asyncio.sleep(fee_interval)

        try:
            estimates = cached_fee_estimates(rpc)
            info = cached_blockchain_info(rpc)
            fee_data = {
                "timestamp": int(time.time()),
                "height": info.get("blocks"),
                "fees": {str(e.conf_target): e.fee_rate_sat_vb for e in estimates},
            }
            yield f"event: fees\ndata: {json.dumps(fee_data)}\n\n"
        except Exception:
            yield f"event: error\ndata: {json.dumps({'error': 'fee_fetch_failed'})}\n\n"

        if time.time() - last_keepalive >= keepalive_interval:
            yield ": keepalive\n\n"
            last_keepalive = time.time()


@router.get("/blocks")
async def stream_blocks(rpc: BitcoinRPC = Depends(get_rpc)):
    """SSE stream of new block events. Connect with `curl -N`."""
    return StreamingResponse(
        _block_event_generator(rpc),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/fees")
async def stream_fees(rpc: BitcoinRPC = Depends(get_rpc)):
    """SSE stream of fee rate updates every 30 seconds. Connect with `curl -N`."""
    return StreamingResponse(
        _fee_event_generator(rpc),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _whale_tx_generator(rpc: BitcoinRPC, min_btc: float):
    """Yield SSE events for large mempool transactions."""
    seen_txids: set[str] = set()
    poll_interval = 10
    keepalive_interval = 60
    last_keepalive = time.time()
    max_seen = 50_000

    yield f"event: connected\ndata: {json.dumps({'min_btc': min_btc})}\n\n"

    while True:
        await asyncio.sleep(poll_interval)

        try:
            raw_mempool = rpc.call("getrawmempool", False)
        except Exception:
            yield f"event: error\ndata: {json.dumps({'error': 'mempool_fetch_failed'})}\n\n"
            continue

        for txid in raw_mempool:
            if txid in seen_txids:
                continue
            try:
                tx = rpc.call("getrawtransaction", txid, True)
                total_value = sum(vout.get("value", 0) for vout in tx.get("vout", []))
                if total_value >= min_btc:
                    event_data = {
                        "txid": txid,
                        "value_btc": round(total_value, 8),
                        "vsize": tx.get("vsize", 0),
                        "timestamp": int(time.time()),
                    }
                    yield f"event: whale_tx\ndata: {json.dumps(event_data)}\n\n"
            except Exception:
                pass  # tx may have been confirmed between mempool list and fetch
            seen_txids.add(txid)

        # Prevent unbounded memory growth
        if len(seen_txids) > max_seen:
            seen_txids.clear()

        if time.time() - last_keepalive >= keepalive_interval:
            yield ": keepalive\n\n"
            last_keepalive = time.time()


async def _tracked_whale_generator(rpc: BitcoinRPC, min_btc: float):
    global _active_whale_streams
    _active_whale_streams += 1
    try:
        async for event in _whale_tx_generator(rpc, min_btc):
            yield event
    finally:
        _active_whale_streams -= 1


@router.get("/whale-txs")
async def stream_whale_txs(
    request: Request,
    min_btc: float = Query(10.0, ge=0.1, le=10000, description="Minimum BTC value to alert on"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """SSE stream of whale transactions (large value txs entering the mempool)."""
    require_api_key(request, "whale transaction stream")
    global _active_whale_streams
    if _active_whale_streams >= _MAX_WHALE_STREAMS:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"error": {"status": 503, "title": "Service Unavailable", "detail": "Max whale stream connections reached. Try again later."}},
        )
    return StreamingResponse(
        _tracked_whale_generator(rpc, min_btc),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
