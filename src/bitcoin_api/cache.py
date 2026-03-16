"""TTL caching for expensive RPC calls — with cache registry and stale fallback."""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field

from cachetools import LRUCache, TTLCache

log = logging.getLogger("bitcoin_api.cache")


# --- Stale cache: last-known-good values that survive TTL expiry ---

MAX_STALE_AGE = 3600  # seconds — refuse to serve data older than 1 hour
_STALE_STORE_MAXSIZE = 256  # bound memory usage

_stale_store: LRUCache = LRUCache(maxsize=_STALE_STORE_MAXSIZE)
_stale_lock = threading.Lock()
_stale_timestamps: dict[str, float] = {}  # track when each entry was stored


def _save_stale(cache_name: str, key: str, value: object) -> None:
    """Save a value to the stale store for fallback when node is down."""
    compound_key = f"{cache_name}:{key}"
    with _stale_lock:
        _stale_store[compound_key] = value
        _stale_timestamps[compound_key] = time.time()


def get_stale(cache_name: str, key: str = "_") -> tuple[object, float] | None:
    """Get a stale cached value and its age in seconds.

    Returns None if no stale data or if data exceeds MAX_STALE_AGE.
    """
    compound_key = f"{cache_name}:{key}"
    with _stale_lock:
        value = _stale_store.get(compound_key)
        timestamp = _stale_timestamps.get(compound_key)
    if value is None or timestamp is None:
        return None
    age = time.time() - timestamp
    if age > MAX_STALE_AGE:
        return None  # too old — don't serve dangerously stale financial data
    return value, age


def clear_stale_store():
    """Clear the stale store (used by tests)."""
    with _stale_lock:
        _stale_store.clear()
        _stale_timestamps.clear()


# --- Cache registry ---

@dataclass
class CacheEntry:
    name: str
    cache: TTLCache | LRUCache
    lock: threading.Lock = field(default_factory=threading.Lock)

_registry: dict[str, CacheEntry] = {}


def create_cache(name: str, cache: TTLCache | LRUCache) -> CacheEntry:
    """Register a named cache with its own lock."""
    entry = CacheEntry(name=name, cache=cache)
    _registry[name] = entry
    return entry


def clear_all_caches():
    """Clear every registered cache (used by tests)."""
    for entry in _registry.values():
        with entry.lock:
            entry.cache.clear()
    with _snapshot_lock:
        _mempool_snapshots.clear()
    clear_stale_store()


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
_fee = create_cache("fee", TTLCache(maxsize=1, ttl=30))
_mempool = create_cache("mempool", TTLCache(maxsize=1, ttl=5))
_mempool_info = create_cache("mempool_info", TTLCache(maxsize=1, ttl=10))
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


# Errors that indicate node is unavailable (not application bugs).
# RPCError included because node returns RPC errors during startup ("Loading block index").
try:
    from bitcoinlib_rpc.rpc import RPCError as _RPCError
    _NODE_ERRORS = (ConnectionError, TimeoutError, OSError, _RPCError)
except ImportError:
    _NODE_ERRORS = (ConnectionError, TimeoutError, OSError)

def _cached_rpc(entry: CacheEntry, rpc, fetcher, cache_key: str = "_"):
    """Generic cache-through with single-flight and stale fallback.

    Holds the lock during fetch to prevent cache stampede — concurrent threads
    wait for the first fetcher instead of all hitting RPC simultaneously.

    On RPC/connection failure, returns stale cached data (if available) instead
    of raising, so the API degrades gracefully when the node is temporarily down.
    Only catches connection-level errors — application bugs still propagate.
    """
    from .metrics import CACHE_HITS, CACHE_MISSES, STALE_CACHE_SERVED
    with entry.lock:
        if cache_key in entry.cache:
            CACHE_HITS.labels(cache_name=entry.name).inc()
            return entry.cache[cache_key]
        CACHE_MISSES.labels(cache_name=entry.name).inc()
        try:
            result = fetcher(rpc)
        except _NODE_ERRORS:
            # RPC/connection failed — try stale fallback
            stale = get_stale(entry.name, cache_key)
            if stale is not None:
                value, age = stale
                log.warning("Serving stale %s data (%.0fs old) — node unavailable", entry.name, age)
                STALE_CACHE_SERVED.labels(cache_name=entry.name).inc()
                return value
            raise  # No stale data available, propagate the error
        entry.cache[cache_key] = result
        _save_stale(entry.name, cache_key, result)
        return result


_info_fetched_at: float | None = None


def cached_blockchain_info(rpc):
    from .metrics import CACHE_HITS, CACHE_MISSES, STALE_CACHE_SERVED
    global _info_fetched_at
    key = "info"
    with _blockchain_info.lock:
        if key in _blockchain_info.cache:
            CACHE_HITS.labels(cache_name="blockchain_info").inc()
            return _blockchain_info.cache[key]
        CACHE_MISSES.labels(cache_name="blockchain_info").inc()
        try:
            result = rpc.call("getblockchaininfo")
        except _NODE_ERRORS:
            stale = get_stale("blockchain_info", key)
            if stale is not None:
                value, age = stale
                log.warning("Serving stale blockchain_info (%.0fs old) — node unavailable", age)
                STALE_CACHE_SERVED.labels(cache_name="blockchain_info").inc()
                return value
            raise
        _blockchain_info.cache[key] = result
        _info_fetched_at = time.time()
        _save_stale("blockchain_info", key, result)
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


def cached_mempool_info(rpc):
    """Cache getmempoolinfo for 10 seconds — lightweight RPC, prevents hammering."""
    return _cached_rpc(_mempool_info, rpc, lambda r: r.call("getmempoolinfo"))


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
    from .metrics import CACHE_HITS, CACHE_MISSES

    from .metrics import STALE_CACHE_SERVED
    try:
        tip = cached_block_count(rpc)
    except _NODE_ERRORS:
        # Can't get tip — try stale block cache
        stale = get_stale("block", str(height))
        if stale is not None:
            value, age = stale
            log.warning("Serving stale block %d (%.0fs old) — node unavailable", height, age)
            STALE_CACHE_SERVED.labels(cache_name="block").inc()
            return value
        raise

    if (tip - height) < REORG_SAFE_DEPTH:
        with _recent_block.lock:
            if height in _recent_block.cache:
                CACHE_HITS.labels(cache_name="recent_block").inc()
                return _recent_block.cache[height]
            CACHE_MISSES.labels(cache_name="recent_block").inc()
            result = analyze_block(rpc, height)
            _recent_block.cache[height] = result
            _save_stale("block", str(height), result)
            return result

    with _block.lock:
        if height in _block.cache:
            CACHE_HITS.labels(cache_name="block").inc()
            return _block.cache[height]
        CACHE_MISSES.labels(cache_name="block").inc()
        result = analyze_block(rpc, height)
        _block.cache[height] = result
        _save_stale("block", str(height), result)
        return result


def cached_block_by_hash(rpc, block_hash: str):
    """Analyze a block by hash, caching the result by resolved height."""
    from bitcoinlib_rpc.blocks import analyze_block
    from .metrics import CACHE_HITS, CACHE_MISSES, STALE_CACHE_SERVED

    with _block.lock:
        height = _hash_to_height.cache.get(block_hash)
        if height is not None:
            if height in _block.cache:
                CACHE_HITS.labels(cache_name="block").inc()
                return _block.cache[height]
            if height in _recent_block.cache:
                CACHE_HITS.labels(cache_name="recent_block").inc()
                return _recent_block.cache[height]

        CACHE_MISSES.labels(cache_name="block").inc()
        try:
            result = analyze_block(rpc, block_hash)
        except _NODE_ERRORS:
            stale = get_stale("block_hash", block_hash)
            if stale is not None:
                value, age = stale
                log.warning("Serving stale block %s (%.0fs old) — node unavailable", block_hash[:16], age)
                STALE_CACHE_SERVED.labels(cache_name="block").inc()
                return value
            raise
        data = result.model_dump() if hasattr(result, "model_dump") else result
        resolved_height = data.get("height")

        if resolved_height is not None:
            _hash_to_height.cache[block_hash] = resolved_height
            _block.cache[resolved_height] = result
            _save_stale("block", str(resolved_height), result)
            _save_stale("block_hash", block_hash, result)

    return result


def cached_next_block(rpc):
    from bitcoinlib_rpc.nextblock import analyze_next_block
    return _cached_rpc(_nextblock, rpc, lambda r: analyze_next_block(r))


_network_info = create_cache("network_info", TTLCache(maxsize=1, ttl=30))


def cached_network_info(rpc):
    return _cached_rpc(_network_info, rpc, lambda r: r.call("getnetworkinfo"))


# --- Pre-computed market data bundle (updated by fast ticker thread) ---

_market_data_lock = threading.Lock()
_market_data: dict | None = None
_market_data_time: float = 0


def set_market_data(data: dict) -> None:
    """Store pre-computed market data bundle (called by fast ticker thread)."""
    global _market_data, _market_data_time
    with _market_data_lock:
        _market_data = data
        _market_data_time = time.time()


def get_market_data() -> tuple[dict | None, float]:
    """Return (pre-computed market data, age_seconds). None if never computed."""
    with _market_data_lock:
        if _market_data is None:
            return None, 0
        return _market_data, time.time() - _market_data_time
