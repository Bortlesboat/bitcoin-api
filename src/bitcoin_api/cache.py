"""TTL caching for expensive RPC calls."""

import threading

from cachetools import TTLCache

_lock = threading.Lock()

# Mutable data — short TTL
_fee_cache: TTLCache = TTLCache(maxsize=1, ttl=10)
_mempool_cache: TTLCache = TTLCache(maxsize=1, ttl=5)
_status_cache: TTLCache = TTLCache(maxsize=1, ttl=30)
_blockchain_info_cache: TTLCache = TTLCache(maxsize=1, ttl=10)
_block_count_cache: TTLCache = TTLCache(maxsize=1, ttl=5)
_nextblock_cache: TTLCache = TTLCache(maxsize=1, ttl=20)

# Immutable data — confirmed blocks never change (deep confirmations)
_block_cache: TTLCache = TTLCache(maxsize=64, ttl=3600)
# Recent blocks near tip — short TTL to handle reorgs
_recent_block_cache: TTLCache = TTLCache(maxsize=8, ttl=30)

REORG_SAFE_DEPTH = 6


def cached_blockchain_info(rpc):
    key = "info"
    with _lock:
        if key in _blockchain_info_cache:
            return _blockchain_info_cache[key]
    result = rpc.call("getblockchaininfo")
    with _lock:
        _blockchain_info_cache[key] = result
    return result


def cached_block_count(rpc):
    key = "count"
    with _lock:
        if key in _block_count_cache:
            return _block_count_cache[key]
    result = rpc.call("getblockcount")
    with _lock:
        _block_count_cache[key] = result
    return result


def cached_fee_estimates(rpc):
    from bitcoinlib_rpc.fees import get_fee_estimates

    key = "fees"
    with _lock:
        if key in _fee_cache:
            return _fee_cache[key]
    result = get_fee_estimates(rpc)
    with _lock:
        _fee_cache[key] = result
    return result


def cached_mempool_analysis(rpc):
    from bitcoinlib_rpc.mempool import analyze_mempool

    key = "mempool"
    with _lock:
        if key in _mempool_cache:
            return _mempool_cache[key]
    result = analyze_mempool(rpc)
    with _lock:
        _mempool_cache[key] = result
    return result


def cached_status(rpc):
    from bitcoinlib_rpc.status import get_status

    key = "status"
    with _lock:
        if key in _status_cache:
            return _status_cache[key]
    result = get_status(rpc)
    with _lock:
        _status_cache[key] = result
    return result


def cached_block_analysis(rpc, height: int):
    from bitcoinlib_rpc.blocks import analyze_block

    tip = cached_block_count(rpc)

    # Blocks near tip use short-TTL cache (reorg safety)
    if (tip - height) < REORG_SAFE_DEPTH:
        with _lock:
            if height in _recent_block_cache:
                return _recent_block_cache[height]
        result = analyze_block(rpc, height)
        with _lock:
            _recent_block_cache[height] = result
        return result

    # Deep blocks use long-TTL cache
    with _lock:
        if height in _block_cache:
            return _block_cache[height]
    result = analyze_block(rpc, height)
    with _lock:
        _block_cache[height] = result
    return result


def cached_next_block(rpc):
    from bitcoinlib_rpc.nextblock import analyze_next_block

    key = "nextblock"
    with _lock:
        if key in _nextblock_cache:
            return _nextblock_cache[key]
    result = analyze_next_block(rpc)
    with _lock:
        _nextblock_cache[key] = result
    return result
