"""Parse Bitcoin Core getblock (verbosity=2) into indexer-friendly structures."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class ParsedOutput:
    vout: int
    value_sat: int
    script_type: str | None
    address: str | None


@dataclass
class ParsedInput:
    vin: int
    prev_txid: bytes
    prev_vout: int


@dataclass
class ParsedTransaction:
    txid: bytes
    tx_index: int
    version: int
    size: int
    vsize: int
    weight: int
    locktime: int
    fee_sat: int | None
    is_coinbase: bool
    outputs: list[ParsedOutput] = field(default_factory=list)
    inputs: list[ParsedInput] = field(default_factory=list)


@dataclass
class ParsedBlock:
    height: int
    hash: bytes
    prev_hash: bytes
    timestamp: int
    tx_count: int
    size: int
    weight: int
    transactions: list[ParsedTransaction] = field(default_factory=list)


def _sat(btc_value: float) -> int:
    """Convert BTC float to satoshis (integer)."""
    return round(btc_value * 100_000_000)


def _hex_to_bytes(hex_str: str) -> bytes:
    """Convert hex string to bytes."""
    return bytes.fromhex(hex_str)


def parse_block(block_data: dict) -> ParsedBlock:
    """Parse a getblock verbosity=2 response into a ParsedBlock.

    Args:
        block_data: Raw JSON response from getblock with verbosity=2.

    Returns:
        ParsedBlock with all transactions, inputs, and outputs extracted.
    """
    block = ParsedBlock(
        height=block_data["height"],
        hash=_hex_to_bytes(block_data["hash"]),
        prev_hash=_hex_to_bytes(block_data.get("previousblockhash", "00" * 32)),
        timestamp=block_data["time"],
        tx_count=block_data["nTx"],
        size=block_data["size"],
        weight=block_data["weight"],
    )

    for tx_index, tx_data in enumerate(block_data["tx"]):
        is_coinbase = "coinbase" in tx_data["vin"][0] if tx_data["vin"] else False

        # Fee: available in verbosity=2 for non-coinbase txs (Bitcoin Core 22+)
        fee_sat = None
        if "fee" in tx_data:
            fee_sat = _sat(tx_data["fee"])

        parsed_tx = ParsedTransaction(
            txid=_hex_to_bytes(tx_data["txid"]),
            tx_index=tx_index,
            version=tx_data["version"],
            size=tx_data["size"],
            vsize=tx_data["vsize"],
            weight=tx_data["weight"],
            locktime=tx_data["locktime"],
            fee_sat=fee_sat,
            is_coinbase=is_coinbase,
        )

        # Parse outputs
        for vout_data in tx_data["vout"]:
            script_pub_key = vout_data.get("scriptPubKey", {})
            address = script_pub_key.get("address")
            script_type = script_pub_key.get("type")

            parsed_tx.outputs.append(ParsedOutput(
                vout=vout_data["n"],
                value_sat=_sat(vout_data["value"]),
                script_type=script_type,
                address=address,
            ))

        # Parse inputs (skip coinbase)
        if not is_coinbase:
            for vin_index, vin_data in enumerate(tx_data["vin"]):
                parsed_tx.inputs.append(ParsedInput(
                    vin=vin_index,
                    prev_txid=_hex_to_bytes(vin_data["txid"]),
                    prev_vout=vin_data["vout"],
                ))

        block.transactions.append(parsed_tx)

    return block
