"""Transaction endpoints: /tx/{txid}, /tx/{txid}/raw, /utxo/{txid}/{vout}."""

from fastapi import APIRouter, Depends, Path

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.transactions import analyze_transaction

from ..dependencies import get_rpc
from ..models import envelope

router = APIRouter(tags=["Transactions"])


@router.get("/tx/{txid}")
def get_transaction(
    txid: str = Path(description="Transaction ID (hex)"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Full transaction analysis: inputs, outputs, fees, SegWit/Taproot flags, inscription detection."""
    analysis = analyze_transaction(rpc, txid)
    info = rpc.call("getblockchaininfo")
    return envelope(analysis.model_dump(), height=info["blocks"], chain=info["chain"])


@router.get("/tx/{txid}/raw")
def get_raw_transaction(
    txid: str = Path(description="Transaction ID (hex)"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Raw decoded transaction from getrawtransaction."""
    raw = rpc.call("getrawtransaction", txid, True)
    info = rpc.call("getblockchaininfo")
    return envelope(raw, height=info["blocks"], chain=info["chain"])


@router.get("/utxo/{txid}/{vout}")
def get_utxo(
    txid: str = Path(description="Transaction ID (hex)"),
    vout: int = Path(description="Output index"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Check if a UTXO is unspent (gettxout)."""
    result = rpc.call("gettxout", txid, vout)
    info = rpc.call("getblockchaininfo")
    if result is None:
        return envelope({"spent": True, "txid": txid, "vout": vout}, height=info["blocks"], chain=info["chain"])
    return envelope(result, height=info["blocks"], chain=info["chain"])
