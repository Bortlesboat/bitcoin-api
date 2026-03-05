"""Block endpoints: /blocks/latest, /blocks/{id}, /blocks/{id}/stats."""

import re

from fastapi import APIRouter, Depends, HTTPException, Path

_HASH_RE = re.compile(r"^[a-fA-F0-9]{64}$")

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.blocks import analyze_block

from ..cache import cached_blockchain_info, cached_block_count, cached_block_analysis
from ..dependencies import get_rpc
from ..models import ApiResponse, envelope

router = APIRouter(prefix="/blocks", tags=["Blocks"])


def _serialize_block(data: dict) -> dict:
    if data.get("top_fee_txids"):
        data["top_fee_txids"] = [
            {"txid": t[0], "fee_rate": t[1]} if isinstance(t, (list, tuple)) else t
            for t in data["top_fee_txids"]
        ]
    return data


@router.get(
    "/latest",
    response_model=ApiResponse[dict],
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
                        "meta": {"height": 881234, "chain": None},
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
    return envelope(data, height=height, chain=None)


@router.get(
    "/{height_or_hash}",
    response_model=ApiResponse[dict],
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
                        "detail": "Invalid block hash: must be 64 hex characters"
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

    if isinstance(identifier, str) and not _HASH_RE.match(identifier):
        raise HTTPException(status_code=422, detail="Invalid block hash: must be 64 hex characters")

    # Use cache for integer heights, direct call for hashes
    if isinstance(identifier, int):
        analysis = cached_block_analysis(rpc, identifier)
    else:
        analysis = analyze_block(rpc, identifier)

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
    height: int = Path(description="Block height"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Raw block statistics from getblockstats RPC."""
    stats = rpc.call("getblockstats", height)
    info = cached_blockchain_info(rpc)
    return envelope(stats, height=info["blocks"], chain=info["chain"])
