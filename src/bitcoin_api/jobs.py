"""Background jobs: fee collector thread with health monitoring."""

import logging
import threading
import time

from .db import record_fee_snapshot, prune_fee_history, prune_old_logs
from .cache import record_mempool_snapshot
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


def get_job_health() -> dict:
    """Return background job health metrics."""
    return {
        "last_run": _last_run_time,
        "last_success": _last_success_time,
        "run_count": _run_count,
        "error_count": _error_count,
        "last_error": _last_error,
        "thread_alive": _bg_thread.is_alive() if _bg_thread else False,
    }


_last_prune: float = 0.0


def _fee_collector():
    """Background thread: snapshot mempool every 5 min for trend analysis + fee history."""
    global _last_run_time, _last_success_time, _run_count, _error_count, _last_error, _last_prune
    from .dependencies import get_rpc as _get_rpc_dep

    while not _bg_stop.is_set():
        _last_run_time = time.time()
        _run_count += 1
        try:
            rpc = _get_rpc_dep()
            record_mempool_snapshot(rpc)

            info = rpc.call("getmempoolinfo")
            fees_1 = rpc.call("estimatesmartfee", 1)
            fees_6 = rpc.call("estimatesmartfee", 6)
            fees_144 = rpc.call("estimatesmartfee", 144)

            next_block_fee = (fees_1.get("feerate", 0) or 0) * 100_000
            median_fee = (fees_6.get("feerate", 0) or 0) * 100_000
            low_fee = (fees_144.get("feerate", 0) or 0) * 100_000
            mempool_size = info.get("size", 0)
            mempool_vsize = info.get("bytes", 0)

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
        except Exception as exc:
            _error_count += 1
            _last_error = str(exc)
            JOB_ERRORS.inc()
            log.warning("Background fee collector failed (attempt %d, errors %d): %s",
                        _run_count, _error_count, exc)

        _bg_stop.wait(300)


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
