"""Mempool endpoints: /mempool, /mempool/info, /mempool/tx/{txid}."""

from fastapi import APIRouter, Depends, Path

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.mempool import analyze_mempool

from ..dependencies import get_rpc
from ..models import envelope

router = APIRouter(prefix="/mempool", tags=["Mempool"])


@router.get("")
def mempool_analysis(rpc: BitcoinRPC = Depends(get_rpc)):
    """Full mempool analysis: fee buckets, congestion level, next-block minimum fee."""
    summary = analyze_mempool(rpc)
    info = rpc.call("getblockchaininfo")
    return envelope(summary.model_dump(), height=info["blocks"], chain=info["chain"])


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
