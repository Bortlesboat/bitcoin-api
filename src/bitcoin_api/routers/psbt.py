"""PSBT security analysis — detect mempool sniping vulnerability in ordinals listings.

POST /api/v1/psbt/analyze

Analyzes a BIP 174 PSBT and determines whether an ordinals inscription listing is
vulnerable to mempool sniping. A listing is vulnerable when it uses
SIGHASH_SINGLE|ANYONECANPAY without a 2-of-2 multisig locking step, allowing an
attacker to front-run the transaction and steal the inscription.

No Bitcoin node required — analysis is pure PSBT parsing.
"""

from __future__ import annotations

import binascii
import struct
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import require_api_key
from ..models import envelope

router = APIRouter(prefix="/psbt", tags=["PSBT"])

# ---------------------------------------------------------------------------
# PSBT constants (BIP 174)
# ---------------------------------------------------------------------------

_PSBT_MAGIC = b"\x70\x73\x62\x74\xff"

# Per-input key types
_KEY_PARTIAL_SIG = b"\x02"
_KEY_SIGHASH_TYPE = b"\x03"
_KEY_WITNESS_SCRIPT = b"\x05"

SIGHASH_NAMES: dict[int, str] = {
    0x01: "SIGHASH_ALL",
    0x02: "SIGHASH_NONE",
    0x03: "SIGHASH_SINGLE",
    0x81: "SIGHASH_ALL|ANYONECANPAY",
    0x82: "SIGHASH_NONE|ANYONECANPAY",
    0x83: "SIGHASH_SINGLE|ANYONECANPAY",
}

_SIGHASH_VULNERABLE = 0x83  # SINGLE|ANYONECANPAY without multisig lock = snipeable

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PsbtAnalyzeRequest(BaseModel):
    psbt_hex: str = Field(..., description="Hex-encoded PSBT (BIP 174 / BIP 370 v0)", max_length=100_000)


class PsbtInputAnalysis(BaseModel):
    index: int
    sighash_type: int | None = None
    sighash_name: str | None = None
    has_witness_script: bool = False
    is_2of2_multisig: bool = False
    partial_sig_count: int = 0
    sighash_types_from_sigs: list[str] = []
    vulnerability: Literal["vulnerable", "protected", "not_applicable", "unknown"] = "unknown"


class PsbtAnalysisResult(BaseModel):
    input_count: int
    overall_risk: Literal["vulnerable", "protected", "not_inscription_listing", "unknown"]
    inputs: list[PsbtInputAnalysis]
    recommendation: str
    explanation: str


# ---------------------------------------------------------------------------
# PSBT parsing (pure Python — no external deps)
# ---------------------------------------------------------------------------


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    """Read a Bitcoin compact-size uint. Returns (value, new_offset)."""
    first = data[offset]
    if first < 0xFD:
        return first, offset + 1
    elif first == 0xFD:
        return int.from_bytes(data[offset + 1 : offset + 3], "little"), offset + 3
    elif first == 0xFE:
        return int.from_bytes(data[offset + 1 : offset + 5], "little"), offset + 5
    else:
        return int.from_bytes(data[offset + 1 : offset + 9], "little"), offset + 9


def _parse_map(data: bytes, offset: int) -> tuple[dict[bytes, bytes], int]:
    """Parse a PSBT key-value map until the 0x00 separator byte."""
    kv: dict[bytes, bytes] = {}
    while offset < len(data):
        key_len, offset = _read_varint(data, offset)
        if key_len == 0:
            break
        key = data[offset : offset + key_len]
        offset += key_len
        val_len, offset = _read_varint(data, offset)
        val = data[offset : offset + val_len]
        offset += val_len
        kv[key] = val
    return kv, offset


def _input_count_from_unsigned_tx(raw_tx: bytes) -> int:
    """Extract input count from a raw unsigned Bitcoin transaction."""
    # Skip 4-byte version, then read varint input count.
    count, _ = _read_varint(raw_tx, 4)
    return count


def _is_2of2_multisig_script(script: bytes) -> bool:
    """Return True if the witness script is a standard 2-of-2 P2WSH multisig.

    Expected layout (71 bytes):
        OP_2  OP_PUSH33 <pubkey1_33b>  OP_PUSH33 <pubkey2_33b>  OP_2  OP_CHECKMULTISIG
        [0]   [1]       [2..34]        [35]       [36..68]       [69]  [70]
        0x52  0x21                     0x21                      0x52  0xae
    """
    if len(script) != 71:
        return False
    return (
        script[0] == 0x52   # OP_2
        and script[1] == 0x21   # OP_PUSH 33
        and script[35] == 0x21  # OP_PUSH 33 (after first pubkey)
        and script[69] == 0x52  # OP_2
        and script[70] == 0xAE  # OP_CHECKMULTISIG
    )


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def _analyze_psbt(psbt_bytes: bytes) -> PsbtAnalysisResult:
    """Parse a PSBT and return a vulnerability assessment."""
    if not psbt_bytes.startswith(_PSBT_MAGIC):
        raise ValueError("Invalid PSBT: missing magic bytes (expected 70736274ff)")

    offset = 5  # skip magic

    # --- Global map ---
    global_map, offset = _parse_map(psbt_bytes, offset)

    raw_tx = global_map.get(b"\x00")  # PSBT_GLOBAL_UNSIGNED_TX
    if raw_tx is None:
        raise ValueError("Invalid PSBT: missing unsigned transaction (BIP 174 v0 required)")

    input_count = _input_count_from_unsigned_tx(raw_tx)

    # --- Per-input maps ---
    inputs: list[PsbtInputAnalysis] = []
    for i in range(input_count):
        input_map, offset = _parse_map(psbt_bytes, offset)

        # Sighash type from explicit PSBT_IN_SIGHASH_TYPE field (key 0x03)
        sighash_type: int | None = None
        if _KEY_SIGHASH_TYPE in input_map:
            raw = input_map[_KEY_SIGHASH_TYPE]
            sighash_type = int.from_bytes(raw[:4].ljust(4, b"\x00"), "little")

        # Sighash types extracted from partial signature last bytes (key prefix 0x02)
        sig_sighash_names: list[str] = []
        for key, val in input_map.items():
            if key and key[:1] == _KEY_PARTIAL_SIG and len(val) >= 1:
                sig_sh = val[-1]
                sig_sighash_names.append(SIGHASH_NAMES.get(sig_sh, f"0x{sig_sh:02x}"))
                if sighash_type is None:
                    sighash_type = sig_sh

        sighash_name = SIGHASH_NAMES.get(sighash_type, f"0x{sighash_type:02x}") if sighash_type is not None else None

        # Witness script
        witness_script = input_map.get(_KEY_WITNESS_SCRIPT)
        has_ws = witness_script is not None
        is_multisig = _is_2of2_multisig_script(witness_script) if has_ws else False

        # Per-input vulnerability
        vuln: Literal["vulnerable", "protected", "not_applicable", "unknown"] = "unknown"
        if sighash_type == _SIGHASH_VULNERABLE:
            vuln = "protected" if is_multisig else "vulnerable"
        elif sighash_type is not None:
            vuln = "not_applicable"

        inputs.append(
            PsbtInputAnalysis(
                index=i,
                sighash_type=sighash_type,
                sighash_name=sighash_name,
                has_witness_script=has_ws,
                is_2of2_multisig=is_multisig,
                partial_sig_count=len(sig_sighash_names),
                sighash_types_from_sigs=sig_sighash_names,
                vulnerability=vuln,
            )
        )

    # --- Overall risk ---
    vulns = [inp.vulnerability for inp in inputs]

    if "vulnerable" in vulns:
        overall_risk: Literal["vulnerable", "protected", "not_inscription_listing", "unknown"] = "vulnerable"
        recommendation = (
            "This listing is vulnerable to mempool sniping. Lock the inscription into a "
            "2-of-2 P2WSH multisig (seller + marketplace pubkeys) before broadcasting the "
            "sale. The marketplace must co-sign with SIGHASH_ALL to prevent any transaction "
            "modification."
        )
        explanation = (
            "One or more inputs use SIGHASH_SINGLE|ANYONECANPAY without a 2-of-2 multisig "
            "locking step. A mempool observer can substitute inputs and redirect the inscription "
            "to themselves without invalidating the seller's signature."
        )
    elif "protected" in vulns:
        overall_risk = "protected"
        recommendation = "No action needed — this listing uses the 2-of-2 multisig protection pattern."
        explanation = (
            "The inscription is locked in a 2-of-2 P2WSH multisig output. Both the seller "
            "(SIGHASH_SINGLE|ANYONECANPAY) and marketplace (SIGHASH_ALL) must co-sign. The "
            "marketplace's SIGHASH_ALL prevents any modification of the transaction structure, "
            "blocking mempool sniping attacks."
        )
    elif all(v == "not_applicable" for v in vulns):
        overall_risk = "not_inscription_listing"
        recommendation = "This does not appear to be an ordinals inscription listing transaction."
        explanation = "No inputs use SIGHASH_SINGLE|ANYONECANPAY, which is the sighash type required for ordinals listings."
    else:
        overall_risk = "unknown"
        recommendation = (
            "Could not determine vulnerability. Ensure the PSBT includes explicit sighash type "
            "information (PSBT_IN_SIGHASH_TYPE) or partial signatures."
        )
        explanation = "Sighash types were not set or detectable in the provided PSBT."

    return PsbtAnalysisResult(
        input_count=input_count,
        overall_risk=overall_risk,
        inputs=inputs,
        recommendation=recommendation,
        explanation=explanation,
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/analyze")
def analyze_psbt(body: PsbtAnalyzeRequest, request: Request):
    """Analyze a PSBT for inscription listing mempool sniping vulnerability.

    Detects whether an ordinals inscription listing is vulnerable to front-running.
    A listing is vulnerable when it uses **SIGHASH_SINGLE|ANYONECANPAY** without a
    2-of-2 multisig locking step — allowing an attacker to redirect the inscription
    before confirmation without invalidating the seller's signature.

    Returns per-input sighash analysis, overall risk level, and remediation guidance.
    No Bitcoin node required — analysis is local PSBT parsing.

    Requires a free-tier API key or above.
    """
    require_api_key(request, "PSBT analysis")

    try:
        psbt_bytes = binascii.unhexlify(body.psbt_hex.strip())
    except (ValueError, binascii.Error):
        raise HTTPException(status_code=422, detail="psbt_hex is not valid hex")

    try:
        result = _analyze_psbt(psbt_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return envelope(result.model_dump())
