"""Address endpoints: /address/{address}, /address/{address}/utxos."""

import re

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from starlette.requests import Request
from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.rpc import RPCError

from ..cache import cached_blockchain_info
from ..dependencies import get_rpc
from ..models import ApiResponse, envelope

router = APIRouter(prefix="/address", tags=["Address"])

# Basic address format check — let Bitcoin Core do the real validation
_ADDR_RE = re.compile(r"^[a-zA-Z0-9]{25,90}$")


def _validate_address(address: str, rpc: BitcoinRPC) -> dict:
    """Validate address and return properties. Raises 422 on invalid format, 400 on invalid address."""
    if not _ADDR_RE.match(address):
        raise HTTPException(status_code=422, detail="Invalid address format")
    result = rpc.call("validateaddress", address)
    if not result.get("isvalid"):
        raise HTTPException(status_code=400, detail=f"Invalid Bitcoin address: {address}")
    return result


def _scan_address(address: str, rpc: BitcoinRPC) -> dict:
    """Scan UTXO set for address. Returns scantxoutset result."""
    descriptor = f"addr({address})"
    try:
        result = rpc.call("scantxoutset", "start", [descriptor])
    except RPCError as exc:
        if exc.code == -8:
            raise HTTPException(status_code=400, detail=f"Address not scannable: {exc.message}")
        raise
    if not result or not result.get("success", False):
        raise HTTPException(status_code=502, detail="UTXO set scan failed — node may be busy")
    return result


_SUMMARY_EXAMPLE = {
    200: {
        "description": "Address balance and UTXO summary",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
                        "type": "witness_v0_keyhash",
                        "balance_btc": 0.01234567,
                        "balance_sats": 1234567,
                        "utxo_count": 3,
                        "is_witness": True,
                        "witness_version": 0,
                    },
                    "meta": {"node_height": 939673, "chain": "main"},
                }
            }
        },
    },
}


@router.get(
    "/{address}",
    response_model=ApiResponse[dict],
    responses=_SUMMARY_EXAMPLE,
)
def address_summary(
    request: Request,
    address: str = Path(description="Bitcoin address (any format: legacy, segwit, taproot)"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Address balance and UTXO summary via UTXO set scan.

    Returns confirmed balance only (unspent outputs currently in the UTXO set).
    Does not include mempool/unconfirmed transactions.
    """
    addr_info = _validate_address(address, rpc)
    scan = _scan_address(address, rpc)
    info = cached_blockchain_info(rpc)

    balance_btc = scan.get("total_amount", 0)
    utxos = scan.get("unspents", [])

    data = {
        "address": address,
        "type": addr_info.get("scriptPubKey", {}).get("type") if isinstance(addr_info.get("scriptPubKey"), dict) else None,
        "script_pub_key": addr_info.get("scriptPubKey"),
        "is_witness": addr_info.get("iswitness", False),
        "witness_version": addr_info.get("witness_version"),
        "balance_btc": balance_btc,
        "balance_sats": int(round(balance_btc * 1e8)),
        "utxo_count": len(utxos),
        "total_input_value_btc": scan.get("total_amount", 0),
        "searched_items": scan.get("txouts_searched", 0),
    }
    return envelope(data, height=info["blocks"], chain=info["chain"])


_UTXOS_EXAMPLE = {
    200: {
        "description": "List of UTXOs for an address",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
                        "utxo_count": 2,
                        "balance_btc": 0.01234567,
                        "balance_sats": 1234567,
                        "utxos": [
                            {
                                "txid": "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
                                "vout": 0,
                                "value_btc": 0.01,
                                "value_sats": 1000000,
                                "height": 800000,
                                "coinbase": False,
                            },
                            {
                                "txid": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
                                "vout": 1,
                                "value_btc": 0.00234567,
                                "value_sats": 234567,
                                "height": 810000,
                                "coinbase": False,
                            },
                        ],
                    },
                    "meta": {"node_height": 939673, "chain": "main"},
                }
            }
        },
    },
}


@router.get(
    "/{address}/utxos",
    response_model=ApiResponse[dict],
    responses=_UTXOS_EXAMPLE,
)
def address_utxos(
    request: Request,
    address: str = Path(description="Bitcoin address (any format: legacy, segwit, taproot)"),
    limit: int = Query(default=50, ge=1, le=500, description="Max UTXOs to return"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """List unspent transaction outputs (UTXOs) for an address.

    Returns confirmed UTXOs from the UTXO set scan.
    Results are sorted by value (largest first). Use limit to control response size.
    """
    _validate_address(address, rpc)
    scan = _scan_address(address, rpc)
    info = cached_blockchain_info(rpc)

    raw_utxos = scan.get("unspents", [])
    balance_btc = scan.get("total_amount", 0)

    # Sort by value descending and apply limit
    raw_utxos.sort(key=lambda u: u.get("amount", 0), reverse=True)
    limited = raw_utxos[:limit]

    utxos = []
    for u in limited:
        val = u.get("amount", 0)
        utxos.append({
            "txid": u.get("txid"),
            "vout": u.get("vout"),
            "value_btc": val,
            "value_sats": int(round(val * 1e8)),
            "height": u.get("height"),
            "coinbase": u.get("coinbase", False),
            "script_pub_key": u.get("scriptPubKey"),
        })

    data = {
        "address": address,
        "utxo_count": len(raw_utxos),
        "returned": len(utxos),
        "balance_btc": balance_btc,
        "balance_sats": int(round(balance_btc * 1e8)),
        "utxos": utxos,
    }
    return envelope(data, height=info["blocks"], chain=info["chain"])
