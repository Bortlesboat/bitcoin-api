"""Mempool endpoints: /mempool, /mempool/info, /mempool/tx/{txid}, /mempool/txids, /mempool/recent."""

from fastapi import APIRouter, Depends, Path, Query

from bitcoinlib_rpc import BitcoinRPC

from ..cache import cached_mempool_analysis, cached_mempool_info, cached_raw_mempool
from ..dependencies import get_rpc
from ..models import ApiResponse, MempoolAnalysisData, rpc_envelope
from ..services.serializers import sanitize_for_json
from ..validators import validate_txid

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


@router.get("", response_model=ApiResponse[MempoolAnalysisData], responses=_MEMPOOL_ANALYSIS_EXAMPLE)
def mempool_analysis(rpc: BitcoinRPC = Depends(get_rpc)):
    """Full mempool analysis: fee buckets, congestion level, next-block minimum fee."""
    summary = cached_mempool_analysis(rpc)
    raw = summary.model_dump(mode="json")
    # Map bitcoinlib-rpc field names to API field names
    if "total_bytes" in raw:
        raw.setdefault("bytes", raw.pop("total_bytes"))
    if "buckets" in raw:
        raw.setdefault("fee_buckets", raw.pop("buckets"))
    data = sanitize_for_json(raw)
    return rpc_envelope(data, rpc)


@router.get("/info", response_model=ApiResponse[dict], responses=_MEMPOOL_INFO_EXAMPLE)
def mempool_info(rpc: BitcoinRPC = Depends(get_rpc)):
    """Raw mempool info from getmempoolinfo RPC. Cached for 10 seconds."""
    mpi = cached_mempool_info(rpc)
    return rpc_envelope(mpi, rpc)


@router.get("/tx/{txid}", response_model=ApiResponse[dict], responses=_MEMPOOL_ENTRY_EXAMPLE)
def mempool_entry(
    txid: str = Path(description="Transaction ID currently in the mempool"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Get mempool entry for a specific transaction."""
    validate_txid(txid)
    entry = rpc.call("getmempoolentry", txid)
    return rpc_envelope(entry, rpc)


@router.get(
    "/txids",
    response_model=ApiResponse[list[str]],
    responses={
        200: {
            "description": "Transaction IDs in the mempool (default limit=100, use limit=0 for all)",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
                            "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
                        ],
                        "meta": {"node_height": 939462, "chain": "main"},
                    }
                }
            },
        }
    },
)
def mempool_txids(
    limit: int = Query(100, ge=1, le=5000, description="Max txids to return (default 100, max 5000). Use 0 for all."),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """List transaction IDs in the mempool. Returns first `limit` txids (default 100).

    Set `limit=0` to return all (warning: can be 10K-50K+ items).
    """
    txids = rpc.call("getrawmempool", False)
    if limit > 0:
        txids = txids[:limit]
    return rpc_envelope(txids, rpc)


@router.get(
    "/recent",
    response_model=ApiResponse[list[dict]],
    responses={
        200: {
            "description": "Most recent transactions entering the mempool",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "txid": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
                                "vsize": 141,
                                "fee_rate": 12.5,
                                "time": 1741176000,
                            }
                        ],
                        "meta": {"node_height": 939462, "chain": "main"},
                    }
                }
            },
        }
    },
)
def mempool_recent(
    count: int = Query(10, ge=1, le=100),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Most recent transactions entering the mempool, sorted by entry time (newest first).

    Query parameter `count` controls how many to return (default 10, max 100).
    """
    if count > 100:
        count = 100
    # getrawmempool with verbose=True returns dict of txid -> entry details
    raw = cached_raw_mempool(rpc)
    # Sort by entry time descending, take most recent
    entries = sorted(raw.items(), key=lambda x: x[1].get("time", 0), reverse=True)[:count]
    result = []
    for txid, entry in entries:
        fee_sat = entry.get("fees", {}).get("base", 0) * 1e8
        vsize = entry.get("vsize", 0)
        result.append({
            "txid": txid,
            "vsize": vsize,
            "fee_rate": round(fee_sat / vsize, 2) if vsize > 0 else 0,
            "time": entry.get("time", 0),
        })
    return rpc_envelope(result, rpc)
