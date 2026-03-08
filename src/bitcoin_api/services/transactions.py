"""Transaction business logic — extracted from routers/transactions.py."""

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.rpc import RPCError
from fastapi import HTTPException

BROADCAST_ERRORS = {
    -25: (409, "Transaction already in mempool or missing inputs"),
    -26: (422, "Transaction failed policy checks (e.g. insufficient fee, non-standard)"),
    -27: (409, "Transaction already confirmed in a block"),
}


def check_outspends(rpc: BitcoinRPC, txid: str, outputs: list[dict]) -> list[dict]:
    """Check spending status of each output in a transaction.

    Args:
        rpc: BitcoinRPC instance
        txid: transaction ID
        outputs: list of vout dicts from getrawtransaction

    Returns:
        list of {vout, spent, value?, scriptPubKey_type?} dicts
    """
    result = []
    for out in outputs:
        vout_index = out["n"]
        utxo = rpc.call("gettxout", txid, vout_index)
        entry = {"vout": vout_index, "spent": utxo is None}
        if utxo is not None:
            entry["value"] = utxo.get("value")
            entry["scriptPubKey_type"] = utxo.get("scriptPubKey", {}).get("type")
        result.append(entry)
    return result


def broadcast_with_validation(rpc: BitcoinRPC, hex_data: str) -> str:
    """Decode, validate, and broadcast a raw transaction.

    Args:
        rpc: BitcoinRPC instance
        hex_data: raw transaction hex string

    Returns:
        txid of the broadcast transaction

    Raises:
        HTTPException on decode failure or broadcast error
    """
    # Pre-validate: decode first to catch malformed hex before broadcast
    try:
        rpc.call("decoderawtransaction", hex_data)
    except RPCError:
        raise HTTPException(status_code=422, detail="Transaction could not be decoded — malformed hex")

    # Broadcast with human-readable error mapping
    try:
        txid = rpc.call("sendrawtransaction", hex_data)
    except RPCError as exc:
        if exc.code in BROADCAST_ERRORS:
            status, detail = BROADCAST_ERRORS[exc.code]
            raise HTTPException(status_code=status, detail=detail)
        raise HTTPException(status_code=502, detail=f"Node rejected transaction: {exc.message}")

    return txid
