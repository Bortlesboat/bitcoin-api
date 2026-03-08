"""Indexed transaction endpoint — enriched tx lookup from the index."""

from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from bitcoin_api.auth import require_api_key
from bitcoin_api.models import ApiResponse, build_meta

from ..models import IndexedTransactionDetail
from ..services.transaction import get_transaction
from ..db import get_pool

router = APIRouter(prefix="/indexed/tx", tags=["Indexed Transaction"])


@router.get(
    "/{txid}",
    response_model=ApiResponse[IndexedTransactionDetail],
    summary="Get indexed transaction",
)
async def indexed_tx(txid: str, request: Request):
    """Enriched transaction detail from the blockchain index."""
    require_api_key(request, "Indexed transaction")

    # Validate txid format
    if len(txid) != 64:
        return JSONResponse(
            status_code=400,
            content={"error": {"status": 400, "title": "Bad Request", "detail": "txid must be 64 hex characters"}},
        )
    try:
        bytes.fromhex(txid)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": {"status": 400, "title": "Bad Request", "detail": "txid must be valid hex"}},
        )

    result = await get_transaction(txid)
    if result is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"status": 404, "title": "Not Found", "detail": f"Transaction {txid} not found in index"}},
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        state = await conn.fetchrow("SELECT tip_height FROM indexer_state WHERE id = 1")

    meta = build_meta(height=state["tip_height"] if state else None)
    return {"data": result, "meta": meta.model_dump()}
