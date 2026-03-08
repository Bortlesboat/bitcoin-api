"""Background jobs: fee collector thread with health monitoring."""

import logging
import threading
import time

from .db import record_fee_snapshot, prune_fee_history, prune_old_logs
from .cache import record_mempool_snapshot, feerate_to_sat_vb
from .metrics import BLOCK_HEIGHT, JOB_ERRORS
from .pubsub import hub

log = logging.getLogger("bitcoin_api")

_bg_stop = threading.Event()
_bg_thread: threading.Thread | None = None

# Health monitoring — exposed to /health/deep
_last_run_time: float | None = None
_last_success_time: float | None = None
_run_count: int = 0
_error_count: int = 0
_last_error: str | None = None
_restart_count: int = 0


def get_job_health(tier: str = "free") -> dict:
    """Return background job health metrics.

    Raw error details are only exposed to admin/pro tiers.
    Free-tier users see a generic message to avoid leaking internals.
    """
    if _last_error is not None and tier in ("admin", "pro", "enterprise"):
        error_detail = _last_error
    elif _last_error is not None:
        error_detail = "Node communication error"
    else:
        error_detail = None

    return {
        "last_run": _last_run_time,
        "last_success": _last_success_time,
        "run_count": _run_count,
        "error_count": _error_count,
        "last_error": error_detail,
        "restart_count": _restart_count,
        "thread_alive": _bg_thread.is_alive() if _bg_thread else False,
    }


_last_prune: float = 0.0


def _fee_collector():
    """Background thread: snapshot mempool every 5 min for trend analysis + fee history.

    Outer loop auto-restarts after unhandled exceptions with exponential backoff.
    """
    global _last_run_time, _last_success_time, _run_count, _error_count, _last_error, _last_prune, _restart_count
    from .dependencies import get_rpc as _get_rpc_dep

    backoff = 10  # seconds, doubles on consecutive crashes, max 300

    while not _bg_stop.is_set():
        try:
            while not _bg_stop.is_set():
                _last_run_time = time.time()
                _run_count += 1
                try:
                    rpc = _get_rpc_dep()

                    # Fetch RPC data once, share with snapshot recorder
                    info = rpc.call("getmempoolinfo")
                    next_block_fee = feerate_to_sat_vb(rpc.call("estimatesmartfee", 1))
                    median_fee = feerate_to_sat_vb(rpc.call("estimatesmartfee", 6))
                    low_fee = feerate_to_sat_vb(rpc.call("estimatesmartfee", 144))
                    mempool_size = info.get("size", 0)
                    mempool_vsize = info.get("bytes", 0)

                    # Reuse fetched data — avoids duplicate RPC calls
                    record_mempool_snapshot(rpc, mempool_info=info,
                                           next_block_fee=next_block_fee, low_fee=low_fee)

                    if mempool_vsize < 1_000_000:
                        congestion = "low"
                    elif mempool_vsize < 10_000_000:
                        congestion = "normal"
                    elif mempool_vsize < 50_000_000:
                        congestion = "elevated"
                    else:
                        congestion = "high"

                    record_fee_snapshot(
                        next_block_fee=round(next_block_fee, 2),
                        median_fee=round(median_fee, 2),
                        low_fee=round(low_fee, 2),
                        mempool_size=mempool_size,
                        mempool_vsize=mempool_vsize,
                        congestion=congestion,
                    )
                    _last_success_time = time.time()

                    # Update Prometheus gauge
                    block_count = rpc.call("getblockcount")
                    BLOCK_HEIGHT.set(block_count)

                    # Publish events to WebSocket subscribers
                    hub.publish("new_fees", {
                        "next_block_fee": round(next_block_fee, 2),
                        "median_fee": round(median_fee, 2),
                        "low_fee": round(low_fee, 2),
                        "congestion": congestion,
                        "timestamp": int(time.time()),
                    })
                    hub.publish("mempool_update", {
                        "size": mempool_size,
                        "vsize": mempool_vsize,
                        "congestion": congestion,
                        "timestamp": int(time.time()),
                    })
                    if hasattr(_fee_collector, "_last_block") and _fee_collector._last_block != block_count:
                        hub.publish("new_block", {
                            "height": block_count,
                            "timestamp": int(time.time()),
                        })
                    _fee_collector._last_block = block_count

                    # Auto-prune old data once per 24h
                    if time.time() - _last_prune > 86400:
                        try:
                            pruned_logs = prune_old_logs(90)
                            pruned_fees = prune_fee_history(30)
                            _last_prune = time.time()
                            log.info("Auto-prune: removed %d usage logs (>90d) and %d fee rows (>30d)",
                                     pruned_logs, pruned_fees)
                        except Exception as prune_exc:
                            log.warning("Auto-prune failed: %s", prune_exc)

                    # Reset backoff after a successful iteration
                    backoff = 10
                except Exception as exc:
                    _error_count += 1
                    _last_error = str(exc)
                    JOB_ERRORS.inc()
                    log.warning("Background fee collector failed (attempt %d, errors %d): %s",
                                _run_count, _error_count, exc)

                _bg_stop.wait(300)

        except BaseException as fatal:
            if _bg_stop.is_set():
                break
            _restart_count += 1
            _error_count += 1
            _last_error = f"FATAL restart #{_restart_count}: {fatal}"
            JOB_ERRORS.inc()
            log.error("Fee collector crashed (restart #%d, backoff %ds): %s",
                      _restart_count, backoff, fatal, exc_info=True)
            _bg_stop.wait(backoff)
            backoff = min(backoff * 2, 300)


def start_background_jobs():
    """Start all background threads."""
    global _bg_thread
    _bg_stop.clear()
    _bg_thread = threading.Thread(target=_fee_collector, daemon=True, name="fee-collector")
    _bg_thread.start()


def stop_background_jobs():
    """Signal all background threads to stop and wait."""
    _bg_stop.set()
    if _bg_thread is not None:
        _bg_thread.join(timeout=5)
