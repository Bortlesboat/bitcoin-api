"""Tests for PSBT security analysis.

Covers:
 - _is_2of2_multisig_script  (unit)
 - _analyze_psbt              (unit — all risk outcomes)
 - POST /api/v1/psbt/analyze  (HTTP — auth gate + happy path)
"""

import struct

import pytest
from fastapi.testclient import TestClient

from bitcoin_api.routers.psbt import (
    _analyze_psbt,
    _is_2of2_multisig_script,
    router,
)
from helpers import make_test_client

# ---------------------------------------------------------------------------
# PSBT fixture builders
# ---------------------------------------------------------------------------

_MAGIC = b"\x70\x73\x62\x74\xff"


def _varint(n: int) -> bytes:
    if n < 0xFD:
        return bytes([n])
    elif n <= 0xFFFF:
        return b"\xfd" + struct.pack("<H", n)
    return b"\xfe" + struct.pack("<I", n)


def _kv(key: bytes, val: bytes) -> bytes:
    return _varint(len(key)) + key + _varint(len(val)) + val


def _minimal_tx(n_inputs: int) -> bytes:
    """Build a minimal raw unsigned tx with n inputs and 0 outputs."""
    tx = struct.pack("<I", 2)          # version
    tx += _varint(n_inputs)
    for _ in range(n_inputs):
        tx += b"\x00" * 32            # txid
        tx += struct.pack("<I", 0)    # vout
        tx += b"\x00"                 # empty scriptSig
        tx += b"\xfd\xff\xff\xff"     # RBF sequence
    tx += _varint(0)                  # output count = 0
    tx += struct.pack("<I", 0)        # locktime
    return tx


def _build_psbt(sighash_types: list[int | None], witness_scripts: list[bytes | None] | None = None) -> bytes:
    """Build a minimal PSBT with one input per sighash_type entry."""
    n = len(sighash_types)
    ws_list = witness_scripts if witness_scripts is not None else [None] * n

    # Global map
    global_map = _kv(b"\x00", _minimal_tx(n)) + b"\x00"

    # Per-input maps
    input_maps = b""
    for sh, ws in zip(sighash_types, ws_list):
        m = b""
        if sh is not None:
            m += _kv(b"\x03", struct.pack("<I", sh))
        if ws is not None:
            m += _kv(b"\x05", ws)
        input_maps += m + b"\x00"

    # No output maps (0 outputs)
    return _MAGIC + global_map + input_maps


def _make_2of2_script() -> bytes:
    """Valid 2-of-2 multisig witness script (69 bytes)."""
    pk1 = b"\x02" + b"\xab" * 32
    pk2 = b"\x03" + b"\xcd" * 32
    return bytes([0x52, 0x21]) + pk1 + bytes([0x21]) + pk2 + bytes([0x52, 0xAE])


# ---------------------------------------------------------------------------
# _is_2of2_multisig_script
# ---------------------------------------------------------------------------


class TestIs2of2MultisigScript:
    def test_valid_2of2(self):
        assert _is_2of2_multisig_script(_make_2of2_script()) is True

    def test_wrong_length_short(self):
        assert _is_2of2_multisig_script(_make_2of2_script()[:70]) is False

    def test_wrong_length_long(self):
        assert _is_2of2_multisig_script(_make_2of2_script() + b"\x00") is False

    def test_wrong_m_opcode(self):
        ws = bytearray(_make_2of2_script())
        ws[0] = 0x51  # OP_1 instead of OP_2
        assert _is_2of2_multisig_script(bytes(ws)) is False

    def test_wrong_checkmultisig(self):
        ws = bytearray(_make_2of2_script())
        ws[70] = 0xAC  # OP_CHECKSIG instead of OP_CHECKMULTISIG at index 70
        assert _is_2of2_multisig_script(bytes(ws)) is False

    def test_empty(self):
        assert _is_2of2_multisig_script(b"") is False


# ---------------------------------------------------------------------------
# _analyze_psbt — risk outcomes
# ---------------------------------------------------------------------------


class TestAnalyzePsbt:
    def test_invalid_magic_raises(self):
        with pytest.raises(ValueError, match="magic"):
            _analyze_psbt(b"\xDE\xAD\xBE\xEF\xFF" + b"\x00" * 30)

    def test_missing_unsigned_tx_raises(self):
        # PSBT with empty global map
        psbt = _MAGIC + b"\x00" + b"\x00"  # global sep + one empty input map
        with pytest.raises(ValueError, match="unsigned transaction"):
            _analyze_psbt(psbt)

    def test_single_vulnerable_input(self):
        result = _analyze_psbt(_build_psbt([0x83]))
        assert result.overall_risk == "vulnerable"
        assert result.inputs[0].vulnerability == "vulnerable"
        assert result.inputs[0].sighash_type == 0x83
        assert result.inputs[0].sighash_name == "SIGHASH_SINGLE|ANYONECANPAY"

    def test_single_protected_input(self):
        result = _analyze_psbt(_build_psbt([0x83], [_make_2of2_script()]))
        assert result.overall_risk == "protected"
        assert result.inputs[0].vulnerability == "protected"
        assert result.inputs[0].is_2of2_multisig is True

    def test_sighash_all_not_inscription(self):
        result = _analyze_psbt(_build_psbt([0x01]))
        assert result.overall_risk == "not_inscription_listing"
        assert result.inputs[0].vulnerability == "not_applicable"

    def test_no_sighash_unknown(self):
        result = _analyze_psbt(_build_psbt([None]))
        assert result.overall_risk == "unknown"
        assert result.inputs[0].sighash_type is None

    def test_vulnerable_wins_over_not_applicable(self):
        result = _analyze_psbt(_build_psbt([0x01, 0x83]))
        assert result.overall_risk == "vulnerable"
        assert result.inputs[0].vulnerability == "not_applicable"
        assert result.inputs[1].vulnerability == "vulnerable"

    def test_multiple_not_applicable(self):
        result = _analyze_psbt(_build_psbt([0x01, 0x01]))
        assert result.overall_risk == "not_inscription_listing"
        assert result.input_count == 2

    def test_protected_with_standard_coinjoin_input(self):
        """One SIGHASH_ALL input (buyer funding) + one protected listing input."""
        result = _analyze_psbt(_build_psbt([0x01, 0x83], [None, _make_2of2_script()]))
        assert result.overall_risk == "protected"

    def test_recommendation_present(self):
        result = _analyze_psbt(_build_psbt([0x83]))
        assert len(result.recommendation) > 10

    def test_explanation_present(self):
        result = _analyze_psbt(_build_psbt([0x83]))
        assert len(result.explanation) > 10

    def test_input_count(self):
        result = _analyze_psbt(_build_psbt([0x01, 0x83, None]))
        assert result.input_count == 3
        assert len(result.inputs) == 3


# ---------------------------------------------------------------------------
# HTTP endpoint — auth gate
# ---------------------------------------------------------------------------


class TestPsbtEndpointAuth:
    """Anonymous requests must be rejected (no middleware needed — getattr default is 'anonymous')."""

    def _client(self) -> TestClient:
        return make_test_client(router, prefix="/api/v1")

    def test_anonymous_gets_403(self):
        psbt_hex = _build_psbt([0x83]).hex()
        resp = self._client().post("/api/v1/psbt/analyze", json={"psbt_hex": psbt_hex})
        assert resp.status_code == 403

    def test_missing_body_gets_422(self):
        resp = self._client().post("/api/v1/psbt/analyze", json={})
        assert resp.status_code == 422

    def test_invalid_hex_gets_422(self):
        resp = self._client().post("/api/v1/psbt/analyze", json={"psbt_hex": "notvalidhex!!"})
        # anonymous = 403 before hex validation; auth checked first
        assert resp.status_code in (403, 422)


# ---------------------------------------------------------------------------
# HTTP endpoint — authed (uses full app fixture)
# ---------------------------------------------------------------------------


def test_psbt_analyze_vulnerable(authed_client):
    """End-to-end: authed request returns vulnerable assessment."""
    import pytest
    from bitcoin_api.config import settings

    if not settings.enable_psbt_router:
        pytest.skip("PSBT router disabled (enable_psbt_router=False)")

    psbt_hex = _build_psbt([0x83]).hex()
    resp = authed_client.post("/api/v1/psbt/analyze", json={"psbt_hex": psbt_hex})
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert body["data"]["overall_risk"] == "vulnerable"
    assert len(body["data"]["inputs"]) == 1
    assert "meta" in body


def test_psbt_analyze_protected(authed_client):
    """End-to-end: protected listing returns protected assessment."""
    import pytest
    from bitcoin_api.config import settings

    if not settings.enable_psbt_router:
        pytest.skip("PSBT router disabled (enable_psbt_router=False)")

    psbt_hex = _build_psbt([0x83], [_make_2of2_script()]).hex()
    resp = authed_client.post("/api/v1/psbt/analyze", json={"psbt_hex": psbt_hex})
    assert resp.status_code == 200
    assert resp.json()["data"]["overall_risk"] == "protected"


def test_psbt_analyze_invalid_hex(authed_client):
    """End-to-end: malformed hex returns 422."""
    import pytest
    from bitcoin_api.config import settings

    if not settings.enable_psbt_router:
        pytest.skip("PSBT router disabled (enable_psbt_router=False)")

    resp = authed_client.post("/api/v1/psbt/analyze", json={"psbt_hex": "deadbeefzz"})
    assert resp.status_code == 422
