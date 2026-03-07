"""Chain statistics services: output classification, OP_RETURN parsing."""

# Map Bitcoin Core script types to human-readable labels
SCRIPT_TYPE_MAP: dict[str, str] = {
    "pubkeyhash": "P2PKH",
    "scripthash": "P2SH",
    "witness_v0_keyhash": "P2WPKH",
    "witness_v0_scripthash": "P2WSH",
    "witness_v1_taproot": "P2TR",
    "pubkey": "P2PK",
    "multisig": "Multisig",
    "nulldata": "OP_RETURN",
    "nonstandard": "Non-standard",
    "witness_unknown": "Witness Unknown",
}


def classify_output_type(script_type: str) -> str:
    """Map a Bitcoin Core script type string to a human-readable label."""
    return SCRIPT_TYPE_MAP.get(script_type, script_type)


def classify_outputs(block_data: dict) -> dict[str, int]:
    """Count outputs by type from a verbosity-2 block."""
    counts: dict[str, int] = {}
    for tx in block_data.get("tx", []):
        for vout in tx.get("vout", []):
            spk = vout.get("scriptPubKey", {})
            script_type = spk.get("type", "unknown")
            label = classify_output_type(script_type)
            counts[label] = counts.get(label, 0) + 1
    return counts


def parse_op_returns(block_data: dict) -> list[dict]:
    """Extract OP_RETURN outputs from a verbosity-2 block."""
    op_returns = []
    for tx in block_data.get("tx", []):
        for vout in tx.get("vout", []):
            spk = vout.get("scriptPubKey", {})
            if spk.get("type") == "nulldata":
                hex_data = spk.get("hex", "")
                op_returns.append({
                    "txid": tx.get("txid", ""),
                    "hex": hex_data,
                    "size_bytes": len(hex_data) // 2,
                })
    return op_returns
