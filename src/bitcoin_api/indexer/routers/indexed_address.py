"""Indexed address endpoints — transaction history and balance from the index."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from starlette.responses import JSONResponse

from bitcoin_api.auth import require_api_key
from bitcoin_api.models import ApiResponse, build_meta

from ..models import IndexedAddressBalance, IndexedAddressHistory
from ..services.address import get_address_balance, get_address_history
from ..db import get_pool

router = APIRouter(prefix="/indexed/address", tags=["Indexed Address"])


@router.get(
    "/{address}/balance",
    response_model=ApiResponse[IndexedAddressBalance],
    summary="Get indexed address balance",
)
async def address_balance(address: str, request: Request):
    """Balance and statistics for an address from the blockchain index."""
    require_api_key(request, "Indexed address balance")

    result = await get_address_balance(address)
    if result is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"status": 404, "title": "Not Found", "detail": f"Address {address} not found in index"}},
        )

    # Get indexed height for meta
    pool = get_pool()
    async with pool.acquire() as conn:
        state = await conn.fetchrow("SELECT tip_height FROM indexer_state WHERE id = 1")

    meta = build_meta(height=state["tip_height"] if state else None)
    return {"data": result, "meta": meta.model_dump()}


@router.get(
    "/{address}/txs",
    response_model=ApiResponse[IndexedAddressHistory],
    summary="Get indexed address transaction history",
)
async def address_txs(
    address: str,
    request: Request,
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(25, ge=1, le=100, description="Results per page"),
):
    """Paginated transaction history for an address from the blockchain index."""
    require_api_key(request, "Indexed address history")

    result = await get_address_history(address, offset=offset, limit=limit)

    pool = get_pool()
    async with pool.acquire() as conn:
        state = await conn.fetchrow("SELECT tip_height FROM indexer_state WHERE id = 1")

    meta = build_meta(height=state["tip_height"] if state else None)
    return {"data": result, "meta": meta.model_dump()}
