"""Block endpoints: /blocks/latest, /blocks/{id}, /blocks/{id}/stats, /blocks/{hash}/txids, /blocks/{hash}/txs, /blocks/tip/*."""

import re

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from bitcoinlib_rpc import BitcoinRPC

from ..cache import cached_blockchain_info, cached_block_count, cached_block_analysis, cached_block_by_hash
from ..dependencies import get_rpc
from ..models import ApiResponse, BlockAnalysisData, envelope

_HASH_RE = re.compile(r"^[a-fA-F0-9]{64}$")

router = APIRouter(prefix="/blocks", tags=["Blocks"])


def _serialize_block(data: dict) -> dict:
    # Map bitcoinlib-rpc field names to API field names
    if "fee_rate_median" in data:
        data.setdefault("median_fee_rate", data.pop("fee_rate_median"))
    if "total_fee_btc" in data:
        data.setdefault("total_fee", data.pop("total_fee_btc"))
    if data.get("top_fee_txids"):
        data["top_fee_txids"] = [
            {"txid": t[0], "fee_rate": t[1]} if isinstance(t, (list, tuple)) else t
            for t in data["top_fee_txids"]
        ]
    return data


@router.get(
    "/latest",
    response_model=ApiResponse[BlockAnalysisData],
    responses={
        200: {
            "description": "Latest block analysis",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "hash": "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670",
                            "height": 881234,
                            "tx_count": 3421,
                            "size": 1543287,
                            "weight": 3993148,
                            "median_fee_rate": 12.5,
                            "total_fee": 0.28431562,
                            "top_fee_txids": [],
                        },
                        "meta": {"height": 881234, "chain": "main"},
                    }
                }
            },
        }
    },
)
def latest_block(rpc: BitcoinRPC = Depends(get_rpc)):
    """Analyze the most recent block."""
    height = cached_block_count(rpc)
    analysis = cached_block_analysis(rpc, height)
    data = _serialize_block(analysis.model_dump())
    info = cached_blockchain_info(rpc)
    return envelope(data, height=height, chain=info["chain"])


@router.get(
    "/tip/height",
    response_model=ApiResponse[int],
    responses={
        200: {
            "description": "Current chain tip height",
            "content": {
                "application/json": {
                    "example": {
                        "data": 881234,
                        "meta": {"node_height": 881234, "chain": "main"},
                    }
                }
            },
        }
    },
)
def tip_height(rpc: BitcoinRPC = Depends(get_rpc)):
    """Current chain tip height."""
    height = cached_block_count(rpc)
    info = cached_blockchain_info(rpc)
    return envelope(height, height=height, chain=info["chain"])


@router.get(
    "/tip/hash",
    response_model=ApiResponse[str],
    responses={
        200: {
            "description": "Current chain tip block hash",
            "content": {
                "application/json": {
                    "example": {
                        "data": "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670",
                        "meta": {"node_height": 881234, "chain": "main"},
                    }
                }
            },
        }
    },
)
def tip_hash(rpc: BitcoinRPC = Depends(get_rpc)):
    """Current chain tip block hash."""
    info = cached_blockchain_info(rpc)
    return envelope(info["bestblockhash"], height=info["blocks"], chain=info["chain"])


@router.get(
    "/{height_or_hash}",
    response_model=ApiResponse[BlockAnalysisData],
    responses={
        200: {
            "description": "Block analysis by height or hash",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "hash": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
                            "height": 0,
                            "tx_count": 1,
                            "size": 285,
                            "weight": 816,
                            "median_fee_rate": 0,
                            "total_fee": 0,
                            "top_fee_txids": [],
                        },
                        "meta": {"height": 881234, "chain": "main"},
                    }
                }
            },
        },
        422: {
            "description": "Invalid block hash format",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "status": 422,
                            "title": "Error",
                            "detail": "Invalid block hash: must be 64 hex characters",
                            "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        }
                    }
                }
            },
        },
    },
)
def get_block(
    height_or_hash: str = Path(description="Block height (integer) or block hash (hex)"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Analyze a block by height or hash."""
    try:
        identifier: int | str = int(height_or_hash)
    except ValueError:
        identifier = height_or_hash

    if isinstance(identifier, int) and identifier < 0:
        raise HTTPException(status_code=422, detail="Block height must be non-negative")
    if isinstance(identifier, str) and not _HASH_RE.match(identifier):
        raise HTTPException(status_code=422, detail="Invalid block hash: must be 64 hex characters")

    # Use cache for both height and hash lookups
    if isinstance(identifier, int):
        analysis = cached_block_analysis(rpc, identifier)
    else:
        analysis = cached_block_by_hash(rpc, identifier)

    data = _serialize_block(analysis.model_dump())
    info = cached_blockchain_info(rpc)
    return envelope(data, height=info["blocks"], chain=info["chain"])


@router.get(
    "/{height}/stats",
    response_model=ApiResponse[dict],
    responses={
        200: {
            "description": "Raw block statistics from getblockstats",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "avgfee": 8312,
                            "avgfeerate": 14,
                            "avgtxsize": 534,
                            "blockhash": "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670",
                            "height": 881234,
                            "ins": 9432,
                            "maxfee": 1250000,
                            "maxfeerate": 621,
                            "medianfee": 3520,
                            "mediantime": 1741187234,
                            "minfee": 192,
                            "minfeerate": 1,
                            "outs": 8921,
                            "subsidy": 312500000,
                            "totalfee": 28431562,
                            "txs": 3421,
                        },
                        "meta": {"height": 881234, "chain": "main"},
                    }
                }
            },
        }
    },
)
def block_stats(
    height: int = Path(description="Block height", ge=0),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Raw block statistics from getblockstats RPC."""
    stats = rpc.call("getblockstats", height)
    info = cached_blockchain_info(rpc)
    return envelope(stats, height=info["blocks"], chain=info["chain"])


@router.get(
    "/{block_hash}/txids",
    response_model=ApiResponse[list[str]],
    responses={
        200: {
            "description": "Transaction IDs in a block",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
                            "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
                        ],
                        "meta": {"node_height": 881234, "chain": "main"},
                    }
                }
            },
        },
        422: {"description": "Invalid block hash format"},
    },
)
def block_txids(
    block_hash: str = Path(description="Block hash (64 hex characters)"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """List all transaction IDs in a block."""
    if not _HASH_RE.match(block_hash):
        raise HTTPException(status_code=422, detail="Invalid block hash: must be 64 hex characters")
    block = rpc.call("getblock", block_hash, 1)
    info = cached_blockchain_info(rpc)
    return envelope(block["tx"], height=info["blocks"], chain=info["chain"])


@router.get(
    "/{block_hash}/txs",
    response_model=ApiResponse[list[dict]],
    responses={
        200: {
            "description": "Full transactions in a block (paginated)",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "txid": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
                                "size": 204,
                                "vsize": 177,
                                "vin": [],
                                "vout": [{"value": 50.0, "n": 0}],
                            }
                        ],
                        "meta": {"node_height": 881234, "chain": "main"},
                    }
                }
            },
        },
        422: {"description": "Invalid block hash format"},
    },
)
def block_txs(
    block_hash: str = Path(description="Block hash (64 hex characters)"),
    start: int = Query(0, ge=0, description="Start index for pagination"),
    limit: int = Query(25, ge=1, le=100, description="Number of transactions to return"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Full transactions in a block, paginated. Default 25 per page, max 100."""
    if not _HASH_RE.match(block_hash):
        raise HTTPException(status_code=422, detail="Invalid block hash: must be 64 hex characters")
    block = rpc.call("getblock", block_hash, 2)
    txs = block.get("tx", [])[start:start + limit]
    info = cached_blockchain_info(rpc)
    return envelope(txs, height=info["blocks"], chain=info["chain"])
