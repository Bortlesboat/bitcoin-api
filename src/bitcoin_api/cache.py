"""TTL caching for expensive RPC calls — with cache registry."""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field

log = logging.getLogger("bitcoin_api.cache")

from cachetools import LRUCache, TTLCache


# --- Cache registry ---

@dataclass
class CacheEntry:
    cache: TTLCache | LRUCache
    lock: threading.Lock = field(default_factory=threading.Lock)

_registry: dict[str, CacheEntry] = {}


def create_cache(name: str, cache: TTLCache | LRUCache) -> CacheEntry:
    """Register a named cache with its own lock."""
    entry = CacheEntry(cache=cache)
    _registry[name] = entry
    return entry


def clear_all_caches():
    """Clear every registered cache (used by tests)."""
    for entry in _registry.values():
        with entry.lock:
            entry.cache.clear()
    with _snapshot_lock:
        _mempool_snapshots.clear()


def get_all_cache_stats() -> dict[str, dict]:
    """Return size/maxsize for every registered cache."""
    stats = {}
    for name, entry in _registry.items():
        with entry.lock:
            c = entry.cache
            stats[name] = {
                "size": len(c),
                "maxsize": c.maxsize,
            }
    return stats


# --- Cache instances ---

# Mutable data — short TTL
_fee = create_cache("fee", TTLCache(maxsize=1, ttl=10))
_mempool = create_cache("mempool", TTLCache(maxsize=1, ttl=5))
_status = create_cache("status", TTLCache(maxsize=1, ttl=30))
_blockchain_info = create_cache("blockchain_info", TTLCache(maxsize=1, ttl=10))
_block_count = create_cache("block_count", TTLCache(maxsize=1, ttl=5))
_nextblock = create_cache("nextblock", TTLCache(maxsize=1, ttl=20))
_raw_mempool = create_cache("raw_mempool", TTLCache(maxsize=1, ttl=5))
_utxo_set = create_cache("utxo_set", TTLCache(maxsize=1, ttl=300))  # 5 min cache

# Immutable data — confirmed blocks never change (deep confirmations)
_block = create_cache("block", TTLCache(maxsize=64, ttl=3600))
# Recent blocks near tip — short TTL to handle reorgs
_recent_block = create_cache("recent_block", TTLCache(maxsize=8, ttl=30))
# Block hash → height mapping for cache lookups (bounded to prevent memory leak)
_hash_to_height = create_cache("hash_to_height", LRUCache(maxsize=256))

REORG_SAFE_DEPTH = 6

# Mempool snapshot circular buffer for trend analysis (fee landscape)
_snapshot_lock = threading.Lock()
_mempool_snapshots: deque = deque(maxlen=6)  # 6 snapshots x 5 min = 30 min window


def feerate_to_sat_vb(raw: dict) -> float:
    """Convert estimatesmartfee result to sat/vB."""
    return (raw.get("feerate", 0) or 0) * 100_000


def record_mempool_snapshot(rpc, *, mempool_info: dict | None = None,
                            next_block_fee: float | None = None,
                            low_fee: float | None = None) -> None:
    """Take a mempool + fee snapshot and append to circular buffer.

    If mempool_info/fees are provided (from caller), reuses them to avoid duplicate RPC calls.
    """
    try:
        info = mempool_info or rpc.call("getmempoolinfo")
        if next_block_fee is None:
            next_block_fee = feerate_to_sat_vb(rpc.call("estimatesmartfee", 1))
        if low_fee is None:
            low_fee = feerate_to_sat_vb(rpc.call("estimatesmartfee", 144))

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
    except Exception as e:
        log.warning("Failed to record mempool snapshot: %s", e)


def get_mempool_snapshots() -> list[dict]:
    """Return copy of mempool snapshot buffer."""
    with _snapshot_lock:
        return list(_mempool_snapshots)


def _cached_rpc(entry: CacheEntry, rpc, fetcher, cache_key: str = "_"):
    """Generic cache-through: check cache → miss → fetch → store → return."""
    with entry.lock:
        if cache_key in entry.cache:
            return entry.cache[cache_key]
    result = fetcher(rpc)
    with entry.lock:
        entry.cache[cache_key] = result
    return result


_info_fetched_at: float | None = None


def cached_blockchain_info(rpc):
    global _info_fetched_at
    key = "info"
    with _blockchain_info.lock:
        if key in _blockchain_info.cache:
            return _blockchain_info.cache[key]
    result = rpc.call("getblockchaininfo")
    with _blockchain_info.lock:
        _blockchain_info.cache[key] = result
        _info_fetched_at = time.time()
    return result


def get_cached_node_info() -> tuple[int | None, str | None]:
    """Return (height, chain) from cached blockchain info, or (None, None)."""
    with _blockchain_info.lock:
        info = _blockchain_info.cache.get("info")
    if info is None:
        return None, None
    return info.get("blocks"), info.get("chain")


def get_sync_progress() -> float | None:
    """Return verificationprogress from cached blockchain info, or None if not cached."""
    with _blockchain_info.lock:
        info = _blockchain_info.cache.get("info")
    if info is None:
        return None
    return info.get("verificationprogress")


def get_cache_state() -> tuple[bool, int | None]:
    """Return (is_cached, age_seconds) for blockchain info cache."""
    with _blockchain_info.lock:
        is_cached = "info" in _blockchain_info.cache
    if not is_cached or _info_fetched_at is None:
        return False, None
    return True, int(time.time() - _info_fetched_at)


def cached_block_count(rpc):
    return _cached_rpc(_block_count, rpc, lambda r: r.call("getblockcount"))


def cached_fee_estimates(rpc):
    from bitcoinlib_rpc.fees import get_fee_estimates
    return _cached_rpc(_fee, rpc, lambda r: get_fee_estimates(r))


def cached_mempool_analysis(rpc):
    from bitcoinlib_rpc.mempool import analyze_mempool
    return _cached_rpc(_mempool, rpc, lambda r: analyze_mempool(r))


def cached_status(rpc):
    from bitcoinlib_rpc.status import get_status
    return _cached_rpc(_status, rpc, lambda r: get_status(r))


def cached_raw_mempool(rpc):
    """Cache getrawmempool(True) for 5 seconds — used by mempool/recent and fees/mempool-blocks."""
    return _cached_rpc(_raw_mempool, rpc, lambda r: r.call("getrawmempool", True))


def cached_utxo_set_info(rpc):
    """Cache gettxoutsetinfo for 5 minutes — this RPC takes 30-60s."""
    return _cached_rpc(_utxo_set, rpc, lambda r: r.call("gettxoutsetinfo"))


def cached_block_analysis(rpc, height: int):
    from bitcoinlib_rpc.blocks import analyze_block

    tip = cached_block_count(rpc)

    if (tip - height) < REORG_SAFE_DEPTH:
        with _recent_block.lock:
            if height in _recent_block.cache:
                return _recent_block.cache[height]
        result = analyze_block(rpc, height)
        with _recent_block.lock:
            _recent_block.cache[height] = result
        return result

    with _block.lock:
        if height in _block.cache:
            return _block.cache[height]
    result = analyze_block(rpc, height)
    with _block.lock:
        _block.cache[height] = result
    return result


def cached_block_by_hash(rpc, block_hash: str):
    """Analyze a block by hash, caching the result by resolved height."""
    from bitcoinlib_rpc.blocks import analyze_block

    with _block.lock:
        height = _hash_to_height.cache.get(block_hash)
        if height is not None:
            if height in _block.cache:
                return _block.cache[height]
            if height in _recent_block.cache:
                return _recent_block.cache[height]

    result = analyze_block(rpc, block_hash)
    data = result.model_dump() if hasattr(result, "model_dump") else result
    resolved_height = data.get("height")

    if resolved_height is not None:
        with _block.lock:
            _hash_to_height.cache[block_hash] = resolved_height
            _block.cache[resolved_height] = result

    return result


def cached_next_block(rpc):
    from bitcoinlib_rpc.nextblock import analyze_next_block
    return _cached_rpc(_nextblock, rpc, lambda r: analyze_next_block(r))
