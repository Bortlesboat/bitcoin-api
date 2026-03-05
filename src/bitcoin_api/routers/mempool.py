"""Mempool endpoints: /mempool, /mempool/info, /mempool/tx/{txid}."""

import math

from fastapi import APIRouter, Depends, Path

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.mempool import analyze_mempool

from ..dependencies import get_rpc
from ..models import envelope

router = APIRouter(prefix="/mempool", tags=["Mempool"])


def _sanitize_for_json(obj):
    """Replace inf/nan floats that JSON can't serialize."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isinf(obj) or math.isnan(obj)):
        return None
    return obj


@router.get("")
def mempool_analysis(rpc: BitcoinRPC = Depends(get_rpc)):
    """Full mempool analysis: fee buckets, congestion level, next-block minimum fee."""
    summary = analyze_mempool(rpc)
    info = rpc.call("getblockchaininfo")
    data = _sanitize_for_json(summary.model_dump(mode="json"))
    return envelope(data, height=info["blocks"], chain=info["chain"])


@router.get("/info")
def mempool_info(rpc: BitcoinRPC = Depends(get_rpc)):
    """Raw mempool info from getmempoolinfo RPC."""
    mpi = rpc.call("getmempoolinfo")
    info = rpc.call("getblockchaininfo")
    return envelope(mpi, height=info["blocks"], chain=info["chain"])


@router.get("/tx/{txid}")
def mempool_entry(
    txid: str = Path(description="Transaction ID currently in the mempool"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Get mempool entry for a specific transaction."""
    entry = rpc.call("getmempoolentry", txid)
    info = rpc.call("getblockchaininfo")
    return envelope(entry, height=info["blocks"], chain=info["chain"])
