"""Block endpoints: /blocks/latest, /blocks/{id}, /blocks/{id}/stats."""

from fastapi import APIRouter, Depends, Path

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.blocks import analyze_block

from ..dependencies import get_rpc
from ..models import envelope

router = APIRouter(prefix="/blocks", tags=["Blocks"])


@router.get("/latest")
def latest_block(rpc: BitcoinRPC = Depends(get_rpc)):
    """Analyze the most recent block."""
    height = rpc.call("getblockcount")
    analysis = analyze_block(rpc, height)
    data = analysis.model_dump()
    # Convert tuples in top_fee_txids to dicts
    if data.get("top_fee_txids"):
        data["top_fee_txids"] = [
            {"txid": t[0], "fee_rate": t[1]} if isinstance(t, (list, tuple)) else t
            for t in data["top_fee_txids"]
        ]
    return envelope(data, height=height, chain=None)


@router.get("/{height_or_hash}")
def get_block(
    height_or_hash: str = Path(description="Block height (integer) or block hash (hex)"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Analyze a block by height or hash."""
    # Try parsing as integer height
    try:
        identifier: int | str = int(height_or_hash)
    except ValueError:
        identifier = height_or_hash

    analysis = analyze_block(rpc, identifier)
    data = analysis.model_dump()
    if data.get("top_fee_txids"):
        data["top_fee_txids"] = [
            {"txid": t[0], "fee_rate": t[1]} if isinstance(t, (list, tuple)) else t
            for t in data["top_fee_txids"]
        ]
    info = rpc.call("getblockchaininfo")
    return envelope(data, height=info["blocks"], chain=info["chain"])


@router.get("/{height}/stats")
def block_stats(
    height: int = Path(description="Block height"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Raw block statistics from getblockstats RPC."""
    stats = rpc.call("getblockstats", height)
    info = rpc.call("getblockchaininfo")
    return envelope(stats, height=info["blocks"], chain=info["chain"])
