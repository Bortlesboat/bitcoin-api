"""Tests for API key registration and authentication."""

from unittest.mock import patch


def test_auth_invalid_key_returns_401(client):
    """Providing an invalid API key should return 401, not silent downgrade."""
    resp = client.get(
        "/api/v1/network", headers={"X-API-Key": "invalid-key-that-doesnt-exist"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["status"] == 401


def test_auth_valid_key_upgrades_tier(client, mock_rpc):
    """Valid API key should upgrade tier."""
    import hashlib
    from bitcoin_api.db import get_db

    raw_key = "test-api-key-12345"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    conn = get_db()
    conn.execute(
        "INSERT INTO api_keys (key_hash, prefix, tier, label, active) VALUES (?, ?, ?, ?, ?)",
        (key_hash, "test-", "pro", "Test Key", 1),
    )
    conn.commit()

    resp = client.get("/api/v1/network", headers={"X-API-Key": raw_key})
    assert resp.status_code == 200
    assert resp.headers.get("X-Auth-Tier") == "pro"


def test_query_param_api_key_deprecation(client, mock_rpc):
    """API key via query param should return deprecation headers."""
    import hashlib
    from bitcoin_api.db import get_db

    raw_key = "deprecation-test-key"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    conn = get_db()
    conn.execute(
        "INSERT INTO api_keys (key_hash, prefix, tier, label, active) VALUES (?, ?, ?, ?, ?)",
        (key_hash, "dep-", "free", "Deprecation Test", 1),
    )
    conn.commit()

    resp = client.get(f"/api/v1/network?api_key={raw_key}")
    assert resp.status_code == 200
    assert resp.headers.get("Deprecation") == "true"
    assert "X-Deprecation-Notice" in resp.headers


def test_cache_control_no_store_on_register(authed_client):
    """Register endpoint should have Cache-Control: no-store."""
    resp = authed_client.post(
        "/api/v1/register",
        json={"email": "test@example.com", "label": "test"},
    )
    # May get 200 or 429 or other status, but header should be set
    assert "Cache-Control" in resp.headers
    assert "no-store" in resp.headers["Cache-Control"]


def test_error_help_url_on_401(client):
    """401 errors should include help_url pointing to the guide."""
    resp = client.get("/api/v1/fees", headers={"X-API-Key": "invalid-key-12345"})
    assert resp.status_code == 401
    error = resp.json()["error"]
    assert error["help_url"] == "/api/v1/guide"
    assert "POST /api/v1/register" in error["detail"]


def test_register_calls_send_welcome_email(client):
    """Registration endpoint calls send_welcome_email."""
    with patch("bitcoin_api.routers.keys.send_welcome_email") as mock_email:
        resp = client.post("/api/v1/register", json={
            "email": "welcome@example.com",
            "agreed_to_terms": True,
        })
    assert resp.status_code == 200
    mock_email.assert_called_once()
    args = mock_email.call_args[0]
    assert args[0] == "welcome@example.com"  # to_email
    assert args[1].startswith("btc_")  # api_key


def test_register_calls_track_registration(client):
    """Registration endpoint calls track_registration."""
    with patch("bitcoin_api.routers.keys.track_registration") as mock_track:
        resp = client.post("/api/v1/register", json={
            "email": "track@example.com",
            "agreed_to_terms": True,
        })
    assert resp.status_code == 200
    mock_track.assert_called_once()
    args = mock_track.call_args[0]
    assert args[0] == "track@example.com"
    assert args[1] == "free"


def test_register_succeeds_when_email_fails(client):
    """Registration returns 200 even when send_welcome_email returns False (email failed internally)."""
    with patch("bitcoin_api.routers.keys.send_welcome_email", return_value=False):
        resp = client.post("/api/v1/register", json={
            "email": "fail-email@example.com",
            "agreed_to_terms": True,
        })
    assert resp.status_code == 200
    assert "api_key" in resp.json()["data"]


def test_register_succeeds_when_posthog_fails(client):
    """Registration returns 200 even when track_registration returns None (analytics failed internally)."""
    with patch("bitcoin_api.routers.keys.track_registration", return_value=None):
        resp = client.post("/api/v1/register", json={
            "email": "fail-posthog@example.com",
            "agreed_to_terms": True,
        })
    assert resp.status_code == 200
    assert "api_key" in resp.json()["data"]


def test_register_captures_utm_params(client):
    """Registration should store UTM params in api_keys table."""
    with patch("bitcoin_api.routers.keys.send_welcome_email"), \
         patch("bitcoin_api.routers.keys.track_registration"):
        resp = client.post("/api/v1/register", json={
            "email": "utm-test@example.com",
            "agreed_to_terms": True,
            "utm_source": "reddit",
            "utm_medium": "social",
            "utm_campaign": "launch-2026",
        })
    assert resp.status_code == 200

    from bitcoin_api.db import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT utm_source, utm_medium, utm_campaign FROM api_keys WHERE email = ?",
        ("utm-test@example.com",),
    ).fetchone()
    assert row is not None
    assert row["utm_source"] == "reddit"
    assert row["utm_medium"] == "social"
    assert row["utm_campaign"] == "launch-2026"


def test_require_api_key_anonymous_rejected():
    """require_api_key raises 403 for anonymous tier."""
    from unittest.mock import MagicMock
    from fastapi import HTTPException
    from bitcoin_api.auth import require_api_key
    import pytest

    mock_request = MagicMock()
    mock_request.state.tier = "anonymous"
    with pytest.raises(HTTPException) as exc_info:
        require_api_key(mock_request, "test endpoint")
    assert exc_info.value.status_code == 403
    assert "test endpoint" in exc_info.value.detail


def test_cap_blocks_param_unit():
    """Unit test cap_blocks_param for all tiers."""
    from bitcoin_api.auth import cap_blocks_param
    assert cap_blocks_param(500, "anonymous") == 144
    assert cap_blocks_param(500, "free") == 144
    assert cap_blocks_param(500, "pro") == 500
    assert cap_blocks_param(2000, "pro") == 1008
    assert cap_blocks_param(2016, "enterprise") == 2016
    assert cap_blocks_param(100, "unknown_tier") == 100  # under default cap


def test_authed_blocks_cap(authed_client):
    """Free tier with blocks=2016 gets capped to 144."""
    resp = authed_client.get("/api/v1/mining/revenue?blocks=2016")
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["max_blocks"] == 144
    assert body["data"]["blocks_analyzed"] <= 144
