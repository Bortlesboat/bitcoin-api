"""Transaction endpoints: /tx/{txid}, /tx/{txid}/raw, /utxo/{txid}/{vout}."""

import re

from fastapi import APIRouter, Depends, HTTPException, Path

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.transactions import analyze_transaction

from ..cache import cached_blockchain_info
from ..dependencies import get_rpc
from ..models import ApiResponse, DecodeRequest, envelope

_TXID_RE = re.compile(r"^[a-fA-F0-9]{64}$")

router = APIRouter(tags=["Transactions"])


@router.get(
    "/tx/{txid}",
    response_model=ApiResponse[dict],
    responses={
        200: {
            "description": "Full transaction analysis",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "txid": "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
                            "size": 259,
                            "vsize": 177,
                            "weight": 706,
                            "fee_sat": 14000,
                            "fee_rate_sat_vb": 79.1,
                            "is_segwit": True,
                            "is_taproot": False,
                            "has_inscription": False,
                            "input_count": 1,
                            "output_count": 2,
                        },
                        "meta": {"height": 883000, "chain": "main"},
                    }
                }
            },
        },
        422: {"description": "Invalid txid format"},
    },
)
def get_transaction(
    txid: str = Path(description="Transaction ID (hex)"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Full transaction analysis: inputs, outputs, fees, SegWit/Taproot flags, inscription detection."""
    if not _TXID_RE.match(txid):
        raise HTTPException(status_code=422, detail="Invalid txid: must be 64 hex characters")
    analysis = analyze_transaction(rpc, txid)
    info = cached_blockchain_info(rpc)
    return envelope(analysis.model_dump(), height=info["blocks"], chain=info["chain"])


@router.get(
    "/tx/{txid}/raw",
    response_model=ApiResponse[dict],
    responses={
        200: {
            "description": "Raw decoded transaction",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "txid": "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
                            "hash": "b759d39a8596b70b3a46700b83e1edb247e17ba58df305421864fe7a9ac142ea",
                            "version": 2,
                            "size": 259,
                            "vsize": 177,
                            "weight": 706,
                            "locktime": 0,
                            "vin": [{"txid": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16", "vout": 0}],
                            "vout": [{"value": 0.5, "n": 0, "scriptPubKey": {"type": "witness_v0_keyhash"}}],
                            "blockhash": "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a68cd",
                            "confirmations": 50000,
                            "blocktime": 1700000000,
                        },
                        "meta": {"height": 883000, "chain": "main"},
                    }
                }
            },
        },
        422: {"description": "Invalid txid format"},
    },
)
def get_raw_transaction(
    txid: str = Path(description="Transaction ID (hex)"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Raw decoded transaction from getrawtransaction."""
    if not _TXID_RE.match(txid):
        raise HTTPException(status_code=422, detail="Invalid txid: must be 64 hex characters")
    raw = rpc.call("getrawtransaction", txid, True)
    info = cached_blockchain_info(rpc)
    return envelope(raw, height=info["blocks"], chain=info["chain"])


@router.get(
    "/utxo/{txid}/{vout}",
    response_model=ApiResponse[dict],
    responses={
        200: {
            "description": "UTXO lookup result",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "bestblock": "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a68cd",
                            "confirmations": 120000,
                            "value": 0.01234567,
                            "scriptPubKey": {
                                "asm": "OP_0 a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
                                "hex": "0014a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
                                "type": "witness_v0_keyhash",
                            },
                            "coinbase": False,
                        },
                        "meta": {"height": 883000, "chain": "main"},
                    }
                }
            },
        },
        422: {"description": "Invalid txid format"},
    },
)
def get_utxo(
    txid: str = Path(description="Transaction ID (hex)"),
    vout: int = Path(description="Output index"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Check if a UTXO is unspent (gettxout)."""
    if not _TXID_RE.match(txid):
        raise HTTPException(status_code=422, detail="Invalid txid: must be 64 hex characters")
    result = rpc.call("gettxout", txid, vout)
    info = cached_blockchain_info(rpc)
    if result is None:
        return envelope(
            {
                "in_utxo_set": False,
                "txid": txid,
                "vout": vout,
                "note": "UTXO not found — may be spent, never existed, or pruned",
            },
            height=info["blocks"],
            chain=info["chain"],
        )
    return envelope(result, height=info["blocks"], chain=info["chain"])


_HEX_RE = re.compile(r"^[a-fA-F0-9]+$")

_DECODE_EXAMPLE = {
    200: {
        "description": "Decoded raw transaction",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "txid": "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
                        "version": 2,
                        "size": 225,
                        "vsize": 166,
                        "weight": 661,
                        "locktime": 0,
                        "vin": [{"txid": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16", "vout": 0}],
                        "vout": [{"value": 0.5, "n": 0}],
                    },
                    "meta": {"height": 883000, "chain": "main"},
                }
            }
        },
    },
    422: {"description": "Invalid hex"},
}


@router.post("/decode", response_model=ApiResponse[dict], responses=_DECODE_EXAMPLE)
def decode_transaction(
    body: DecodeRequest,
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Decode a raw transaction hex string without broadcasting."""
    if not _HEX_RE.match(body.hex):
        raise HTTPException(status_code=422, detail="Invalid hex string")
    decoded = rpc.call("decoderawtransaction", body.hex)
    info = cached_blockchain_info(rpc)
    return envelope(decoded, height=info["blocks"], chain=info["chain"])
