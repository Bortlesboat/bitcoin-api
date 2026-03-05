"""Mempool endpoints: /mempool, /mempool/info, /mempool/tx/{txid}."""

import math

from fastapi import APIRouter, Depends, Path

from bitcoinlib_rpc import BitcoinRPC

from ..cache import cached_blockchain_info, cached_mempool_analysis
from ..dependencies import get_rpc
from ..models import envelope

router = APIRouter(prefix="/mempool", tags=["Mempool"])

_MEMPOOL_ANALYSIS_EXAMPLE = {
    200: {
        "description": "Full mempool analysis with fee buckets and congestion",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "size": 14832,
                        "bytes": 7482910,
                        "congestion": "medium",
                        "next_block_min_fee": 8.2,
                        "fee_buckets": [
                            {"range": "1-5 sat/vB", "count": 3201, "total_vsize": 1540000},
                            {"range": "5-10 sat/vB", "count": 4512, "total_vsize": 2180000},
                            {"range": "10-25 sat/vB", "count": 3890, "total_vsize": 1920000},
                            {"range": "25-50 sat/vB", "count": 2105, "total_vsize": 1100000},
                            {"range": "50+ sat/vB", "count": 1124, "total_vsize": 742910},
                        ],
                    },
                    "meta": {
                        "timestamp": "2026-03-05T12:00:00+00:00",
                        "node_height": 939462,
                        "chain": "main",
                    },
                }
            }
        },
    }
}

_MEMPOOL_INFO_EXAMPLE = {
    200: {
        "description": "Raw mempool info from Bitcoin Core",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "loaded": True,
                        "size": 14832,
                        "bytes": 7482910,
                        "usage": 52830720,
                        "total_fee": 1.28453,
                        "maxmempool": 300000000,
                        "mempoolminfee": 0.00001,
                        "minrelaytxfee": 0.00001,
                        "incrementalrelayfee": 0.00001,
                        "unbroadcastcount": 0,
                        "fullrbf": True,
                    },
                    "meta": {
                        "timestamp": "2026-03-05T12:00:00+00:00",
                        "node_height": 939462,
                        "chain": "main",
                    },
                }
            }
        },
    }
}

_MEMPOOL_ENTRY_EXAMPLE = {
    200: {
        "description": "Mempool entry for a specific transaction",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "fees": {
                            "base": 0.00001410,
                            "modified": 0.00001410,
                            "ancestor": 0.00001410,
                            "descendant": 0.00001410,
                        },
                        "vsize": 141,
                        "weight": 561,
                        "time": 1741176000,
                        "height": 939460,
                        "descendantcount": 1,
                        "descendantsize": 141,
                        "ancestorcount": 1,
                        "ancestorsize": 141,
                        "depends": [],
                        "spentby": [],
                        "bip125-replaceable": True,
                        "unbroadcast": False,
                    },
                    "meta": {
                        "timestamp": "2026-03-05T12:00:00+00:00",
                        "node_height": 939462,
                        "chain": "main",
                    },
                }
            }
        },
    }
}


def _sanitize_for_json(obj):
    """Replace inf/nan floats that JSON can't serialize."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isinf(obj) or math.isnan(obj)):
        return None
    return obj


@router.get("", responses=_MEMPOOL_ANALYSIS_EXAMPLE)
def mempool_analysis(rpc: BitcoinRPC = Depends(get_rpc)):
    """Full mempool analysis: fee buckets, congestion level, next-block minimum fee."""
    summary = cached_mempool_analysis(rpc)
    info = cached_blockchain_info(rpc)
    data = _sanitize_for_json(summary.model_dump(mode="json"))
    return envelope(data, height=info["blocks"], chain=info["chain"])


@router.get("/info", responses=_MEMPOOL_INFO_EXAMPLE)
def mempool_info(rpc: BitcoinRPC = Depends(get_rpc)):
    """Raw mempool info from getmempoolinfo RPC."""
    mpi = rpc.call("getmempoolinfo")
    info = cached_blockchain_info(rpc)
    return envelope(mpi, height=info["blocks"], chain=info["chain"])


@router.get("/tx/{txid}", responses=_MEMPOOL_ENTRY_EXAMPLE)
def mempool_entry(
    txid: str = Path(description="Transaction ID currently in the mempool"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Get mempool entry for a specific transaction."""
    entry = rpc.call("getmempoolentry", txid)
    info = cached_blockchain_info(rpc)
    return envelope(entry, height=info["blocks"], chain=info["chain"])
