"""Indexer status endpoint — sync progress and health."""

from __future__ import annotations

from fastapi import APIRouter

from bitcoin_api.models import ApiResponse, build_meta

from ..config import indexer_settings
from ..models import IndexerStatus
from ..db import get_pool

router = APIRouter(prefix="/indexed", tags=["Indexer"])


@router.get(
    "/status",
    response_model=ApiResponse[IndexerStatus],
    summary="Get indexer sync status",
)
async def indexer_status():
    """Current indexer sync progress, speed, and ETA."""
    pool = get_pool()
    async with pool.acquire() as conn:
        state = await conn.fetchrow("SELECT * FROM indexer_state WHERE id = 1")

    if state is None:
        data = IndexerStatus(
            enabled=indexer_settings.enabled,
            syncing=False,
            indexed_height=0,
            progress_pct=0.0,
        )
    else:
        indexed_height = state["tip_height"]
        # We don't have node_height readily available without RPC,
        # so we report what we know
        node_height = None
        progress = 0.0
        eta = None

        # Try to get node height via direct RPC call
        try:
            from bitcoin_api.dependencies import _create_rpc
            rpc = _create_rpc()
            node_height = rpc.call("getblockcount")
            if node_height and node_height > 0:
                progress = min(100.0, (indexed_height / node_height) * 100)
                if state["blocks_per_sec"] and state["blocks_per_sec"] > 0:
                    remaining_blocks = node_height - indexed_height
                    remaining_secs = remaining_blocks / state["blocks_per_sec"]
                    hours = int(remaining_secs // 3600)
                    mins = int((remaining_secs % 3600) // 60)
                    eta = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        except Exception:
            pass

        data = IndexerStatus(
            enabled=indexer_settings.enabled,
            syncing=indexed_height < (node_height or indexed_height),
            indexed_height=indexed_height,
            node_height=node_height,
            progress_pct=round(progress, 2),
            blocks_per_sec=round(state["blocks_per_sec"], 1) if state["blocks_per_sec"] else None,
            estimated_completion=eta,
            started_at=state["started_at"].isoformat() if state["started_at"] else None,
            last_block_at=state["last_block_at"].isoformat() if state["last_block_at"] else None,
        )

    meta = build_meta()
    return {"data": data.model_dump(), "meta": meta.model_dump()}
