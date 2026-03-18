"""Tests for shared validation helpers."""

import pytest
from fastapi import HTTPException

from bitcoin_api.validators import validate_hex64, validate_txid, validate_block_hash


# --- validate_hex64 ---

class TestValidateHex64:
    def test_valid_lowercase_hex(self):
        val = "a" * 64
        assert validate_hex64(val) == val

    def test_valid_uppercase_hex(self):
        val = "A" * 64
        assert validate_hex64(val) == val

    def test_valid_mixed_case_hex(self):
        val = "aAbBcCdDeEfF0011223344556677889900aabbccddeeff001122334455667788"
        assert validate_hex64(val) == val

    def test_valid_all_digits(self):
        val = "0" * 64
        assert validate_hex64(val) == val

    def test_valid_realistic_block_hash(self):
        val = "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670"
        assert validate_hex64(val) == val

    def test_too_short(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_hex64("a" * 63)
        assert exc_info.value.status_code == 422
        assert "hash" in exc_info.value.detail

    def test_too_long(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_hex64("a" * 65)
        assert exc_info.value.status_code == 422

    def test_empty_string(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_hex64("")
        assert exc_info.value.status_code == 422

    def test_non_hex_characters(self):
        val = "g" * 64  # 'g' is not hex
        with pytest.raises(HTTPException):
            validate_hex64(val)

    def test_spaces_in_string(self):
        val = " " * 64
        with pytest.raises(HTTPException):
            validate_hex64(val)

    def test_hex_with_0x_prefix(self):
        val = "0x" + "a" * 62
        with pytest.raises(HTTPException):
            validate_hex64(val)

    def test_custom_label_in_error(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_hex64("bad", label="widget_id")
        assert "widget_id" in exc_info.value.detail

    def test_default_label_is_hash(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_hex64("bad")
        assert "hash" in exc_info.value.detail


# --- validate_txid ---

class TestValidateTxid:
    def test_valid_txid(self):
        txid = "a" * 64
        assert validate_txid(txid) == txid

    def test_invalid_txid_short(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_txid("abc123")
        assert exc_info.value.status_code == 422
        assert "txid" in exc_info.value.detail

    def test_invalid_txid_not_hex(self):
        with pytest.raises(HTTPException):
            validate_txid("z" * 64)


# --- validate_block_hash ---

class TestValidateBlockHash:
    def test_valid_block_hash(self):
        bh = "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670"
        assert validate_block_hash(bh) == bh

    def test_invalid_block_hash_short(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_block_hash("0000")
        assert exc_info.value.status_code == 422
        assert "block hash" in exc_info.value.detail

    def test_invalid_block_hash_special_chars(self):
        with pytest.raises(HTTPException):
            validate_block_hash("!" * 64)
