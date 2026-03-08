"""Transaction endpoints: /tx/{txid}, /tx/{txid}/raw, /tx/{txid}/hex, /tx/{txid}/status, /tx/{txid}/outspends, /utxo/{txid}/{vout}."""

import re

from fastapi import APIRouter, Depends, HTTPException, Path
from starlette.requests import Request
from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.transactions import analyze_transaction

from ..cache import cached_blockchain_info
from ..dependencies import get_rpc
from ..models import (
    ApiResponse, BroadcastData, BroadcastRequest, DecodeRequest,
    TransactionAnalysisData, envelope,
)
from ..services.transactions import check_outspends, broadcast_with_validation

_TXID_RE = re.compile(r"^[a-fA-F0-9]{64}$")

router = APIRouter(tags=["Transactions"])


@router.get(
    "/tx/{txid}",
    response_model=ApiResponse[TransactionAnalysisData],
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
    "/tx/{txid}/status",
    response_model=ApiResponse[dict],
    responses={
        200: {
            "description": "Transaction confirmation status",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "confirmed": True,
                            "block_height": 881234,
                            "block_hash": "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670",
                            "confirmations": 5000,
                        },
                        "meta": {"node_height": 886234, "chain": "main"},
                    }
                }
            },
        },
        422: {"description": "Invalid txid format"},
    },
)
def get_tx_status(
    txid: str = Path(description="Transaction ID (hex)"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Check confirmation status of a transaction."""
    if not _TXID_RE.match(txid):
        raise HTTPException(status_code=422, detail="Invalid txid: must be 64 hex characters")
    raw = rpc.call("getrawtransaction", txid, True)
    info = cached_blockchain_info(rpc)
    confirmed = "blockhash" in raw
    data = {
        "confirmed": confirmed,
        "block_height": raw.get("blockheight"),
        "block_hash": raw.get("blockhash"),
        "confirmations": raw.get("confirmations", 0),
    }
    return envelope(data, height=info["blocks"], chain=info["chain"])


@router.get(
    "/tx/{txid}/hex",
    response_model=ApiResponse[str],
    responses={
        200: {
            "description": "Raw transaction hex string",
            "content": {
                "application/json": {
                    "example": {
                        "data": "0200000001abcdef...",
                        "meta": {"node_height": 881234, "chain": "main"},
                    }
                }
            },
        },
        422: {"description": "Invalid txid format"},
    },
)
def get_tx_hex(
    txid: str = Path(description="Transaction ID (hex)"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Raw transaction as a hex string (not decoded)."""
    if not _TXID_RE.match(txid):
        raise HTTPException(status_code=422, detail="Invalid txid: must be 64 hex characters")
    hex_str = rpc.call("getrawtransaction", txid, False)
    info = cached_blockchain_info(rpc)
    return envelope(hex_str, height=info["blocks"], chain=info["chain"])


@router.get(
    "/tx/{txid}/outspends",
    response_model=ApiResponse[list[dict]],
    responses={
        200: {
            "description": "Spending status of each transaction output",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {"vout": 0, "spent": True},
                            {"vout": 1, "spent": False, "value": 0.5, "scriptPubKey_type": "witness_v0_keyhash"},
                        ],
                        "meta": {"node_height": 881234, "chain": "main"},
                    }
                }
            },
        },
        422: {"description": "Invalid txid format"},
    },
)
def get_tx_outspends(
    txid: str = Path(description="Transaction ID (hex)"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Check spending status of each output in a transaction."""
    if not _TXID_RE.match(txid):
        raise HTTPException(status_code=422, detail="Invalid txid: must be 64 hex characters")
    raw = rpc.call("getrawtransaction", txid, True)
    info = cached_blockchain_info(rpc)
    result = check_outspends(rpc, txid, raw.get("vout", []))
    return envelope(result, height=info["blocks"], chain=info["chain"])


@router.get(
    "/tx/{txid}/merkle-proof",
    response_model=ApiResponse[dict],
    responses={
        200: {
            "description": "Merkle proof for a confirmed transaction",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "proof_hex": "0100000001...",
                            "block_hash": "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670",
                        },
                        "meta": {"node_height": 881234, "chain": "main"},
                    }
                }
            },
        },
        404: {"description": "Transaction unconfirmed or not found"},
        422: {"description": "Invalid txid format"},
    },
)
def get_merkle_proof(
    txid: str = Path(description="Transaction ID (hex)"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Merkle proof for a confirmed transaction (gettxoutproof)."""
    if not _TXID_RE.match(txid):
        raise HTTPException(status_code=422, detail="Invalid txid: must be 64 hex characters")

    # Get block hash from the transaction
    raw = rpc.call("getrawtransaction", txid, True)
    block_hash = raw.get("blockhash")
    if not block_hash:
        raise HTTPException(status_code=404, detail="Transaction is unconfirmed — merkle proof requires a confirmed transaction")

    proof_hex = rpc.call("gettxoutproof", [txid], block_hash)
    info = cached_blockchain_info(rpc)
    return envelope(
        {"proof_hex": proof_hex, "block_hash": block_hash},
        height=info["blocks"],
        chain=info["chain"],
    )


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
    vout: int = Path(description="Output index", ge=0),
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
    request: Request,
    body: DecodeRequest,
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Decode a raw transaction hex string without broadcasting."""
    tier = getattr(request.state, "tier", "anonymous")
    if tier == "anonymous":
        raise HTTPException(status_code=403, detail="API key required for POST endpoints. Register a free key: POST /api/v1/register")
    if not _HEX_RE.match(body.hex):
        raise HTTPException(status_code=422, detail="Invalid hex string")
    decoded = rpc.call("decoderawtransaction", body.hex)
    info = cached_blockchain_info(rpc)
    return envelope(decoded, height=info["blocks"], chain=info["chain"])


_BROADCAST_EXAMPLE = {
    200: {
        "description": "Transaction broadcast successfully",
        "content": {
            "application/json": {
                "example": {
                    "data": {"txid": "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d"},
                    "meta": {"height": 883000, "chain": "main"},
                }
            }
        },
    },
    422: {"description": "Invalid hex"},
}


@router.post("/broadcast", response_model=ApiResponse[BroadcastData], responses=_BROADCAST_EXAMPLE)
def broadcast_transaction(
    request: Request,
    body: BroadcastRequest,
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Broadcast a signed raw transaction to the network."""
    tier = getattr(request.state, "tier", "anonymous")
    if tier == "anonymous":
        raise HTTPException(status_code=403, detail="API key required for POST endpoints. Register a free key: POST /api/v1/register")
    if not _HEX_RE.match(body.hex):
        raise HTTPException(status_code=422, detail="Invalid hex string")

    txid = broadcast_with_validation(rpc, body.hex)
    info = cached_blockchain_info(rpc)
    return envelope({"txid": txid}, height=info["blocks"], chain=info["chain"])
