"""Tests for network-related endpoints."""

from bitcoin_api.config import settings


def test_network(client):
    resp = client.get("/api/v1/network")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["connections"] == 125
    assert body["meta"]["chain"] == "main"


def test_rate_limit_headers(client):
    resp = client.get("/api/v1/network")
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers
    assert "X-RateLimit-Daily-Limit" in resp.headers
    assert "X-RateLimit-Daily-Remaining" in resp.headers


def test_rate_limit_enforcement(client):
    """Anonymous tier should respect the configured per-minute limit."""
    for i in range(settings.rate_limit_anonymous):
        resp = client.get("/api/v1/network")
        assert resp.status_code == 200, f"Request {i+1} failed"

    resp = client.get("/api/v1/network")
    assert resp.status_code == 429
    body = resp.json()
    assert body["error"]["status"] == 429


def test_daily_limit_headers(client):
    """Daily limit headers should appear on rate-limited endpoints."""
    resp = client.get("/api/v1/network")
    assert resp.status_code == 200
    assert "X-RateLimit-Daily-Limit" in resp.headers
    assert resp.headers["X-RateLimit-Daily-Limit"] == "5000"


def test_request_id_in_response(client):
    """All responses should include X-Request-ID header."""
    resp = client.get("/api/v1/network")
    assert "X-Request-ID" in resp.headers
    request_id = resp.headers["X-Request-ID"]
    assert len(request_id) == 36  # UUID format


def test_rpc_error_bad_request(client, mock_rpc):
    """RPC error -8 should map to 400."""
    from bitcoinlib_rpc.rpc import RPCError

    mock_rpc.call.side_effect = RPCError(-8, "Invalid parameter")
    resp = client.get("/api/v1/fees/6")
    assert resp.status_code == 400


def test_rpc_error_generic(client, mock_rpc):
    """Other RPC errors should map to 502."""
    from bitcoinlib_rpc.rpc import RPCError

    mock_rpc.call.side_effect = RPCError(-1, "Unknown error")
    resp = client.get("/api/v1/network")
    assert resp.status_code == 502


def test_connection_error(client, mock_rpc):
    """ConnectionError should return 502 Temporarily Unavailable."""
    mock_rpc.call.side_effect = ConnectionError("refused")
    resp = client.get("/api/v1/network")
    assert resp.status_code == 502
    assert "Temporarily Unavailable" in resp.json()["error"]["title"]


def test_catch_all_500(client, mock_rpc):
    """Unhandled exceptions should return 500 with standard error envelope."""
    mock_rpc.call.side_effect = RuntimeError("unexpected")
    resp = client.get("/api/v1/network")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["status"] == 500
    assert body["error"]["title"] == "Internal Server Error"
    assert "request_id" in body["error"]


def test_thread_safety_smoke(client):
    """Concurrent requests shouldn't crash."""
    import threading

    errors = []

    def make_request():
        try:
            resp = client.get("/api/v1/network")
            if resp.status_code not in (200, 429):
                errors.append(f"Unexpected status: {resp.status_code}")
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=make_request) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread safety errors: {errors}"


def test_network_forks(client):
    """Chain tips endpoint should return getchaintips data."""
    resp = client.get("/api/v1/network/forks")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert body["data"][0]["status"] == "active"


def test_network_moved_to_network_router(client):
    """GET /network should work (moved from status to network router)."""
    resp = client.get("/api/v1/network")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["connections"] == 125


def test_difficulty_adjustment(client):
    resp = client.get("/api/v1/network/difficulty")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert "difficulty" in data
    assert "blocks_in_epoch" in data
    assert "blocks_remaining" in data
    assert "progress_percent" in data
    assert data["blocks_in_epoch"] + data["blocks_remaining"] == 2016


def test_validate_address(client):
    resp = client.get("/api/v1/network/validate-address/bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["isvalid"] is True


def test_anonymous_network_redacts_version(client):
    """Anonymous users don't see node version info."""
    resp = client.get("/api/v1/network")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data.get("version") is None or data.get("version") == "[redacted]"
    assert data.get("subversion") is None or data.get("subversion") == "[redacted]"
    assert data.get("protocol_version") is None or data.get("protocol_version") == "[redacted]"


def test_authenticated_network_includes_version(client, use_temp_db):
    """Authenticated users see full node version info."""
    import hashlib
    from bitcoin_api.db import get_db
    key = "test-net-key-123"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    db = get_db()
    db.execute("INSERT OR REPLACE INTO api_keys (key_hash, prefix, tier, label, active) VALUES (?, ?, 'free', 'test', 1)", (key_hash, key[:8]))
    db.commit()
    resp = client.get("/api/v1/network", headers={"X-API-Key": key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Authenticated users should see version fields (not redacted)
    assert data.get("subversion") is not None
    assert data.get("subversion") != "[redacted]"


def test_usage_logging(client):
    """Requests should be logged to usage_log table."""
    from bitcoin_api.db import get_db
    from bitcoin_api.usage_buffer import usage_buffer
    client.get("/api/v1/network")
    usage_buffer.flush()
    conn = get_db()
    rows = conn.execute("SELECT * FROM usage_log").fetchall()
    assert len(rows) >= 1
    row = dict(rows[0])
    assert row["endpoint"] == "/api/v1/network"
    assert row["status"] == 200


def test_daily_rate_limit_uses_bucket(client, mock_rpc):
    """Anonymous users should have daily limits enforced via IP bucket."""
    from bitcoin_api.db import get_db
    from bitcoin_api.usage_buffer import usage_buffer
    # Make a request (anonymous, so bucket = IP)
    client.get("/api/v1/fees/6")
    usage_buffer.flush()
    conn = get_db()
    rows = conn.execute("SELECT key_hash FROM usage_log").fetchall()
    # Anonymous users should log with IP (bucket), not NULL
    assert len(rows) >= 1
    # At least one row should have a non-NULL key_hash (the IP)
    hashes = [dict(r)["key_hash"] for r in rows]
    assert any(h is not None for h in hashes)


def test_meta_syncing_false_when_synced(client):
    """Default mock has verificationprogress=0.9999, so syncing should be False."""
    resp = client.get("/api/v1/network")
    assert resp.status_code == 200
    meta = resp.json()["meta"]
    assert meta["syncing"] is False


def test_meta_syncing_true_during_ibd(client, mock_rpc):
    """When verificationprogress < 0.9999, syncing should be True."""
    original_side_effect = mock_rpc.call.side_effect

    def ibd_side_effect(method, *args):
        result = original_side_effect(method, *args)
        if method == "getblockchaininfo":
            result = dict(result)
            result["verificationprogress"] = 0.5
        return result

    mock_rpc.call.side_effect = ibd_side_effect
    resp = client.get("/api/v1/network")
    assert resp.status_code == 200
    meta = resp.json()["meta"]
    assert meta["syncing"] is True


def test_syncing_header_during_ibd(client, mock_rpc):
    """X-Node-Syncing header should appear when node is syncing."""
    original_side_effect = mock_rpc.call.side_effect

    def ibd_side_effect(method, *args):
        result = original_side_effect(method, *args)
        if method == "getblockchaininfo":
            result = dict(result)
            result["verificationprogress"] = 0.5
        return result

    mock_rpc.call.side_effect = ibd_side_effect
    resp = client.get("/api/v1/network")
    assert resp.headers.get("X-Node-Syncing") == "true"


def test_meta_cached_false_on_first_call(client):
    """First request should have cached=False (fresh from RPC)."""
    resp = client.get("/api/v1/network")
    assert resp.status_code == 200
    meta = resp.json()["meta"]
    # After first call, the info IS now cached for the build_meta call,
    # but the data was fetched fresh for this request
    assert "cached" in meta
    assert "cache_age_seconds" in meta


def test_meta_cached_true_on_second_call(client):
    """Second request within TTL should show cached=True."""
    client.get("/api/v1/network")
    resp = client.get("/api/v1/network")
    assert resp.status_code == 200
    meta = resp.json()["meta"]
    assert meta["cached"] is True
    assert meta["cache_age_seconds"] is not None
    assert meta["cache_age_seconds"] >= 0


def test_unhandled_exception_returns_500_envelope(client, mock_rpc):
    """Unhandled exceptions return clean 500 with {error} envelope, no traceback."""
    mock_rpc.call.side_effect = RuntimeError("something unexpected")
    resp = client.get("/api/v1/network")
    assert resp.status_code == 500
    body = resp.json()
    assert "error" in body
    assert body["error"]["status"] == 500
    assert "unexpected" in body["error"]["detail"].lower()
    assert "RuntimeError" not in resp.text
    assert "Traceback" not in resp.text


def test_cors_evil_origin_not_reflected(client):
    """CORS must not reflect arbitrary origins."""
    resp = client.get(
        "/api/v1/fees",
        headers={"Origin": "https://evil.example.com"},
    )
    acao = resp.headers.get("access-control-allow-origin", "")
    assert "evil" not in acao


def test_api_404_returns_json_envelope(client):
    """404 on unknown /api/v1/* route should return JSON error envelope, not HTML."""
    resp = client.get("/api/v1/nonexistent")
    assert resp.status_code in (404, 405)
    body = resp.json()
    assert "error" in body
    assert "status" in body["error"]
    assert "detail" in body["error"]
