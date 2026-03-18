"""Async wrapper for synchronous Bitcoin RPC calls.

The bitcoinlib-rpc library uses synchronous HTTP (urllib) under the hood.
Calling rpc.call() directly from an async route handler blocks the event loop,
preventing other requests from being served concurrently.

This module provides async_rpc_call() which runs the synchronous RPC call in a
thread pool executor, freeing the event loop to handle other requests while
waiting for the Bitcoin node to respond.

Usage in route handlers:
    from ..rpc_async import async_rpc_call

    @router.get("/example")
    async def example(rpc: BitcoinRPC = Depends(get_rpc)):
        result = await async_rpc_call(rpc, "getblockcount")
        return rpc_envelope(result, rpc)

Migration guide for converting remaining sync routes:
    1. Change `def endpoint(...)` to `async def endpoint(...)`
    2. Replace `rpc.call("method", *args)` with `await async_rpc_call(rpc, "method", *args)`
    3. Replace `cached_xyz(rpc)` with `await async_cached_xyz(rpc)` (see cache_async.py when added)
    4. Any calls to bitcoinlib-rpc helpers (analyze_transaction, analyze_block, etc.)
       should also be wrapped: `await async_rpc_exec(rpc, analyze_transaction, rpc, txid)`
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

# 4 workers matches typical Bitcoin Core RPC thread count (-rpcthreads default=4).
# Increase if your node is configured with more RPC threads.
_rpc_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="rpc")


async def async_rpc_call(rpc: Any, method: str, *args: Any) -> Any:
    """Run a synchronous rpc.call() in a thread pool executor.

    This prevents blocking the async event loop while waiting for the
    Bitcoin Core RPC response (which can take 100ms-60s depending on method).
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_rpc_executor, rpc.call, method, *args)


async def async_rpc_exec(func: Callable[..., Any], *args: Any) -> Any:
    """Run any synchronous function (e.g. bitcoinlib-rpc helpers) in the RPC thread pool.

    Example:
        from bitcoinlib_rpc.transactions import analyze_transaction
        result = await async_rpc_exec(analyze_transaction, rpc, txid)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_rpc_executor, func, *args)
