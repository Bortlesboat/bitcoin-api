"""Unit tests for auth module — key lookup, extraction, hashing, tier caps."""

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from bitcoin_api.auth import (
    ApiKeyInfo,
    authenticate,
    cap_blocks_param,
    clear_auth_cache,
    extract_api_key,
    hash_key,
    require_api_key,
    require_api_key_hash,
    _cached_lookup,
    BLOCKS_CAP,
)
from fastapi import HTTPException


def _make_request(headers=None, query_params=None, state_attrs=None):
    """Build a mock Request with optional headers, query params, and state."""
    req = MagicMock()
    req.headers = headers or {}
    req.query_params = query_params or {}
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    state = MagicMock()
    for k, v in (state_attrs or {}).items():
        setattr(state, k, v)
    # Default state values
    if state_attrs is None or "tier" not in state_attrs:
        state.tier = "anonymous"
    if state_attrs is None or "key_hash" not in state_attrs:
        state.key_hash = None
    req.state = state
    return req


class TestExtractApiKey:
    def test_key_from_header(self):
        req = _make_request(headers={"X-API-Key": "my-secret-key"})
        key, via_query = extract_api_key(req)
        assert key == "my-secret-key"
        assert via_query is False

    def test_key_from_query_param(self):
        req = _make_request(query_params={"api_key": "query-key"})
        key, via_query = extract_api_key(req)
        assert key == "query-key"
        assert via_query is True

    def test_header_takes_precedence_over_query(self):
        req = _make_request(
            headers={"X-API-Key": "header-key"},
            query_params={"api_key": "query-key"},
        )
        key, via_query = extract_api_key(req)
        assert key == "header-key"
        assert via_query is False

    def test_no_key_returns_none(self):
        req = _make_request()
        key, via_query = extract_api_key(req)
        assert key is None
        assert via_query is False


class TestHashKey:
    def test_hash_is_sha256(self):
        raw = "test-key-123"
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert hash_key(raw) == expected

    def test_hash_is_deterministic(self):
        assert hash_key("same") == hash_key("same")

    def test_different_keys_different_hashes(self):
        assert hash_key("key-a") != hash_key("key-b")


class TestAuthenticate:
    @patch("bitcoin_api.auth._cached_lookup")
    def test_no_key_returns_anonymous(self, mock_lookup):
        req = _make_request()
        result = authenticate(req)
        assert result.tier == "anonymous"
        assert result.key_hash is None
        mock_lookup.assert_not_called()

    @patch("bitcoin_api.auth._cached_lookup")
    def test_valid_active_key_returns_tier(self, mock_lookup):
        mock_lookup.return_value = {
            "key_hash": "abc123hash",
            "tier": "pro",
            "active": True,
            "label": "test-label",
        }
        req = _make_request(headers={"X-API-Key": "my-key"})
        result = authenticate(req)
        assert result.tier == "pro"
        assert result.key_hash == "abc123hash"
        assert result.label == "test-label"

    @patch("bitcoin_api.auth._cached_lookup")
    def test_unknown_key_returns_invalid(self, mock_lookup):
        mock_lookup.return_value = None
        req = _make_request(headers={"X-API-Key": "bad-key"})
        result = authenticate(req)
        assert result.tier == "invalid"

    @patch("bitcoin_api.auth._cached_lookup")
    def test_inactive_key_returns_invalid(self, mock_lookup):
        mock_lookup.return_value = {
            "key_hash": "abc123hash",
            "tier": "free",
            "active": False,
        }
        req = _make_request(headers={"X-API-Key": "disabled-key"})
        result = authenticate(req)
        assert result.tier == "invalid"

    @patch("bitcoin_api.auth._cached_lookup")
    def test_query_param_key_sets_flag(self, mock_lookup):
        mock_lookup.return_value = {
            "key_hash": "qhash",
            "tier": "free",
            "active": True,
        }
        req = _make_request(query_params={"api_key": "query-key"})
        result = authenticate(req)
        assert result.query_param_used is True


class TestRequireApiKey:
    def test_anonymous_raises_403(self):
        req = _make_request(state_attrs={"tier": "anonymous"})
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(req)
        assert exc_info.value.status_code == 403
        assert "API key required" in exc_info.value.detail

    def test_free_tier_passes(self):
        req = _make_request(state_attrs={"tier": "free"})
        assert require_api_key(req) == "free"

    def test_pro_tier_passes(self):
        req = _make_request(state_attrs={"tier": "pro"})
        assert require_api_key(req) == "pro"


class TestRequireApiKeyHash:
    def test_anonymous_raises_403(self):
        req = _make_request(state_attrs={"tier": "anonymous", "key_hash": None})
        with pytest.raises(HTTPException) as exc_info:
            require_api_key_hash(req)
        assert exc_info.value.status_code == 403

    def test_missing_key_hash_raises_403(self):
        req = _make_request(state_attrs={"tier": "free", "key_hash": None})
        with pytest.raises(HTTPException) as exc_info:
            require_api_key_hash(req)
        assert exc_info.value.status_code == 403
        assert "Invalid" in exc_info.value.detail

    def test_valid_key_hash_returned(self):
        req = _make_request(state_attrs={"tier": "free", "key_hash": "abc123"})
        assert require_api_key_hash(req) == "abc123"


class TestCapBlocksParam:
    def test_anonymous_cap(self):
        assert cap_blocks_param(500, "anonymous") == 144

    def test_free_cap(self):
        assert cap_blocks_param(500, "free") == 144

    def test_pro_cap(self):
        assert cap_blocks_param(2000, "pro") == 1008

    def test_enterprise_cap(self):
        assert cap_blocks_param(5000, "enterprise") == 2016

    def test_below_cap_unchanged(self):
        assert cap_blocks_param(50, "pro") == 50

    def test_unknown_tier_defaults_to_144(self):
        assert cap_blocks_param(500, "unknown_tier") == 144
