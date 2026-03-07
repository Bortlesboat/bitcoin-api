"""TTL caching for expensive RPC calls."""

import threading
import time
from collections import deque

from cachetools import LRUCache, TTLCache

# Per-cache locks to avoid cross-cache contention
_info_lock = threading.Lock()
_count_lock = threading.Lock()
_fee_lock = threading.Lock()
_mempool_lock = threading.Lock()
_status_lock = threading.Lock()
_block_lock = threading.Lock()
_nextblock_lock = threading.Lock()

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
# Block hash → height mapping for cache lookups (bounded to prevent memory leak)
_hash_to_height: LRUCache = LRUCache(maxsize=256)

REORG_SAFE_DEPTH = 6

# Mempool snapshot circular buffer for trend analysis (fee landscape)
_snapshot_lock = threading.Lock()
_mempool_snapshots: deque = deque(maxlen=6)  # 6 snapshots x 5 min = 30 min window


def record_mempool_snapshot(rpc) -> None:
    """Take a mempool + fee snapshot and append to circular buffer."""
    try:
        info = rpc.call("getmempoolinfo")
        fees = rpc.call("estimatesmartfee", 1)
        next_block_fee = (fees.get("feerate", 0) or 0) * 100_000  # sat/vB
        low_fees = rpc.call("estimatesmartfee", 144)
        low_fee = (low_fees.get("feerate", 0) or 0) * 100_000

        snapshot = {
            "timestamp": time.time(),
            "mempool_size": info.get("size", 0),
            "mempool_bytes": info.get("bytes", 0),
            "mempool_vsize": info.get("bytes", 0),  # approx
            "next_block_fee": round(next_block_fee, 2),
            "low_fee": round(low_fee, 2),
            "total_fee": info.get("total_fee", 0),
        }
        with _snapshot_lock:
            _mempool_snapshots.append(snapshot)
    except Exception:
        pass  # Don't crash background thread


def get_mempool_snapshots() -> list[dict]:
    """Return copy of mempool snapshot buffer."""
    with _snapshot_lock:
        return list(_mempool_snapshots)


_info_fetched_at: float | None = None


def cached_blockchain_info(rpc):
    global _info_fetched_at
    key = "info"
    with _info_lock:
        if key in _blockchain_info_cache:
            return _blockchain_info_cache[key]
    result = rpc.call("getblockchaininfo")
    with _info_lock:
        _blockchain_info_cache[key] = result
        _info_fetched_at = time.time()
    return result


def get_sync_progress() -> float | None:
    """Return verificationprogress from cached blockchain info, or None if not cached."""
    with _info_lock:
        info = _blockchain_info_cache.get("info")
    if info is None:
        return None
    return info.get("verificationprogress")


def get_cache_state() -> tuple[bool, int | None]:
    """Return (is_cached, age_seconds) for blockchain info cache."""
    with _info_lock:
        is_cached = "info" in _blockchain_info_cache
    if not is_cached or _info_fetched_at is None:
        return False, None
    return True, int(time.time() - _info_fetched_at)


def cached_block_count(rpc):
    key = "count"
    with _count_lock:
        if key in _block_count_cache:
            return _block_count_cache[key]
    result = rpc.call("getblockcount")
    with _count_lock:
        _block_count_cache[key] = result
    return result


def cached_fee_estimates(rpc):
    from bitcoinlib_rpc.fees import get_fee_estimates

    key = "fees"
    with _fee_lock:
        if key in _fee_cache:
            return _fee_cache[key]
    result = get_fee_estimates(rpc)
    with _fee_lock:
        _fee_cache[key] = result
    return result


def cached_mempool_analysis(rpc):
    from bitcoinlib_rpc.mempool import analyze_mempool

    key = "mempool"
    with _mempool_lock:
        if key in _mempool_cache:
            return _mempool_cache[key]
    result = analyze_mempool(rpc)
    with _mempool_lock:
        _mempool_cache[key] = result
    return result


def cached_status(rpc):
    from bitcoinlib_rpc.status import get_status

    key = "status"
    with _status_lock:
        if key in _status_cache:
            return _status_cache[key]
    result = get_status(rpc)
    with _status_lock:
        _status_cache[key] = result
    return result


def cached_block_analysis(rpc, height: int):
    from bitcoinlib_rpc.blocks import analyze_block

    tip = cached_block_count(rpc)

    # Blocks near tip use short-TTL cache (reorg safety)
    if (tip - height) < REORG_SAFE_DEPTH:
        with _block_lock:
            if height in _recent_block_cache:
                return _recent_block_cache[height]
        result = analyze_block(rpc, height)
        with _block_lock:
            _recent_block_cache[height] = result
        return result

    # Deep blocks use long-TTL cache
    with _block_lock:
        if height in _block_cache:
            return _block_cache[height]
    result = analyze_block(rpc, height)
    with _block_lock:
        _block_cache[height] = result
    return result


def cached_block_by_hash(rpc, block_hash: str):
    """Analyze a block by hash, caching the result by resolved height."""
    from bitcoinlib_rpc.blocks import analyze_block

    # Check if we already know this hash's height
    with _block_lock:
        height = _hash_to_height.get(block_hash)
        if height is not None:
            if height in _block_cache:
                return _block_cache[height]
            if height in _recent_block_cache:
                return _recent_block_cache[height]

    result = analyze_block(rpc, block_hash)
    data = result.model_dump() if hasattr(result, "model_dump") else result
    resolved_height = data.get("height")

    if resolved_height is not None:
        with _block_lock:
            _hash_to_height[block_hash] = resolved_height
            _block_cache[resolved_height] = result

    return result


def cached_next_block(rpc):
    from bitcoinlib_rpc.nextblock import analyze_next_block

    key = "nextblock"
    with _nextblock_lock:
        if key in _nextblock_cache:
            return _nextblock_cache[key]
    result = analyze_next_block(rpc)
    with _nextblock_lock:
        _nextblock_cache[key] = result
    return result
