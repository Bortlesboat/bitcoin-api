"""Deep health endpoint — checks RPC, DB, cache state, sync progress."""

import time

from fastapi import APIRouter, Depends, Request

from bitcoinlib_rpc import BitcoinRPC

from ..cache import get_cache_state, get_sync_progress, get_all_cache_stats
from ..dependencies import get_rpc
from ..jobs import get_job_health
from ..models import envelope
from ..usage_buffer import usage_buffer

router = APIRouter(tags=["Status"])

_start_time = time.time()


@router.get("/health/deep")
def health_deep(request: Request, rpc: BitcoinRPC = Depends(get_rpc)):
    """Deep health check: RPC, DB, cache, sync, usage buffer. Requires API key (free+)."""
    tier = getattr(request.state, "tier", "anonymous")
    if tier == "anonymous":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="API key required for deep health check")

    # RPC check
    rpc_ok = False
    rpc_height = None
    try:
        rpc_height = rpc.call("getblockcount")
        rpc_ok = True
    except Exception:
        pass

    # DB check
    db_ok = False
    try:
        from ..db import get_db
        conn = get_db()
        conn.execute("SELECT 1").fetchone()
        db_ok = True
    except Exception:
        pass

    # Cache state
    cache_cached, cache_age = get_cache_state()
    cache_stats = get_all_cache_stats()

    # Sync progress
    sync = get_sync_progress()

    data = {
        "rpc": {"ok": rpc_ok, "height": rpc_height},
        "db": {"ok": db_ok},
        "cache": {
            "blockchain_info_cached": cache_cached,
            "blockchain_info_age_seconds": cache_age,
            "caches": cache_stats,
        },
        "sync_progress": sync,
        "background_jobs": get_job_health(),
        "usage_buffer_pending": usage_buffer.pending_count,
        "uptime_seconds": int(time.time() - _start_time),
    }

    return envelope(data, height=rpc_height, chain=None)
