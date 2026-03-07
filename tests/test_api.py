"""Tests for bitcoin-api endpoints."""

from unittest.mock import patch, MagicMock



def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Satoshi API"
    assert "docs" in data


def test_health_returns_envelope(client):
    """Health endpoint should return standard envelope format."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    assert body["data"]["status"] == "ok"
    assert body["data"]["chain"] == "main"
    assert body["data"]["blocks"] == 880000
    assert body["meta"]["node_height"] == 880000


def test_status(client, mock_rpc):
    with patch("bitcoin_api.routers.status.cached_status") as mock_cached:
        mock_status = MagicMock()
        mock_status.model_dump.return_value = {
            "chain": "main",
            "blocks": 880000,
            "headers": 880000,
            "verification_progress": 0.9999,
            "size_on_disk": 650000000000,
            "pruned": False,
            "connections": 125,
            "version": 270000,
            "subversion": "/Satoshi:27.0.0/",
            "network_name": "mainnet",
        }
        mock_cached.return_value = mock_status

        resp = client.get("/api/v1/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert body["meta"]["node_height"] == 880000


def test_network(client):
    resp = client.get("/api/v1/network")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["connections"] == 125
    assert body["meta"]["chain"] == "main"


def test_mempool_info(client):
    resp = client.get("/api/v1/mempool/info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["size"] == 15000


def test_fee_for_target(client):
    resp = client.get("/api/v1/fees/6")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["conf_target"] == 6
    assert body["data"]["fee_rate_sat_vb"] == 12.0


def test_utxo_spent(client):
    """gettxout returns None for spent outputs."""
    client.app.dependency_overrides.clear()
    mock_rpc = MagicMock()
    mock_rpc.call.side_effect = lambda method, *args: {
        "gettxout": None,
        "getblockchaininfo": {"chain": "main", "blocks": 880000},
    }.get(method)

    from bitcoin_api.dependencies import get_rpc
    client.app.dependency_overrides[get_rpc] = lambda: mock_rpc

    txid = "a" * 64
    resp = client.get(f"/api/v1/utxo/{txid}/0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["in_utxo_set"] is False
    assert "note" in body["data"]

    client.app.dependency_overrides.clear()


def test_rate_limit_headers(client):
    resp = client.get("/api/v1/network")
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers
    assert "X-RateLimit-Daily-Limit" in resp.headers
    assert "X-RateLimit-Daily-Remaining" in resp.headers


def test_health_no_rate_limit(client):
    """Health endpoint should never return 429."""
    for _ in range(50):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
    # No rate limit headers on health (it's skipped)
    assert "X-RateLimit-Limit" not in resp.headers


def test_rate_limit_enforcement(client):
    """Anonymous tier should be limited to 30 req/min."""
    for i in range(30):
        resp = client.get("/api/v1/network")
        assert resp.status_code == 200, f"Request {i+1} failed"

    resp = client.get("/api/v1/network")
    assert resp.status_code == 429
    body = resp.json()
    assert body["error"]["status"] == 429


def test_docs_accessible(client):
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_envelope_format(client):
    with patch("bitcoin_api.routers.status.cached_status") as mock_cached:
        mock_status = MagicMock()
        mock_status.model_dump.return_value = {"chain": "main", "blocks": 880000}
        mock_cached.return_value = mock_status

        resp = client.get("/api/v1/status")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "timestamp" in body["meta"]


def test_usage_logging(client):
    """Requests should be logged to usage_log table."""
    from bitcoin_api.db import get_db
    client.get("/api/v1/network")
    conn = get_db()
    rows = conn.execute("SELECT * FROM usage_log").fetchall()
    assert len(rows) >= 1
    row = dict(rows[0])
    assert row["endpoint"] == "/api/v1/network"
    assert row["status"] == 200


def test_caching_reduces_rpc_calls(client, mock_rpc):
    """Second request should hit cache, not RPC again."""
    client.get("/api/v1/fees/6")
    first_call_count = mock_rpc.call.call_count

    client.get("/api/v1/fees/6")
    second_call_count = mock_rpc.call.call_count

    # getblockchaininfo should be cached on second call
    # So second call should make fewer RPC calls than first
    added_calls = second_call_count - first_call_count
    # Only estimatesmartfee should be called (not getblockchaininfo again)
    assert added_calls < first_call_count


def test_mining_summary(client):
    resp = client.get("/api/v1/mining")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    assert body["data"]["difficulty"] == 110_000_000_000_000
    assert body["data"]["blocks_until_retarget"] > 0


def test_mining_nextblock(client):
    resp = client.get("/api/v1/mining/nextblock")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert body["data"]["height"] == 880001
    assert body["data"]["tx_count"] == 3
    # top_5 should be serialized as dicts
    assert isinstance(body["data"]["top_5"][0], dict)
    assert "txid" in body["data"]["top_5"][0]


def test_daily_limit_headers(client):
    """Daily limit headers should appear on rate-limited endpoints."""
    resp = client.get("/api/v1/network")
    assert resp.status_code == 200
    assert "X-RateLimit-Daily-Limit" in resp.headers
    assert resp.headers["X-RateLimit-Daily-Limit"] == "1000"


# --- Sprint 2 tests ---


def test_blocks_latest(client, mock_rpc):
    """Latest block endpoint should return block analysis."""
    with patch("bitcoin_api.routers.blocks.cached_block_analysis") as mock_ba:
        mock_analysis = MagicMock()
        mock_analysis.model_dump.return_value = {
            "height": 880000, "hash": "a" * 64,
            "tx_count": 3500, "size": 1500000, "weight": 3993000,
            "top_fee_txids": [],
        }
        mock_ba.return_value = mock_analysis
        resp = client.get("/api/v1/blocks/latest")
        assert resp.status_code == 200
        assert resp.json()["data"]["height"] == 880000


def test_blocks_by_height(client, mock_rpc):
    """Block by height should use cached analysis."""
    with patch("bitcoin_api.routers.blocks.cached_block_analysis") as mock_ba:
        mock_analysis = MagicMock()
        mock_analysis.model_dump.return_value = {
            "height": 800000, "hash": "b" * 64,
            "tx_count": 2000, "size": 1000000, "weight": 3000000,
            "top_fee_txids": [],
        }
        mock_ba.return_value = mock_analysis
        resp = client.get("/api/v1/blocks/800000")
        assert resp.status_code == 200
        assert resp.json()["data"]["height"] == 800000


def test_blocks_by_hash(client, mock_rpc):
    """Block by hash should use cached_block_by_hash."""
    block_hash = "a" * 64
    with patch("bitcoin_api.routers.blocks.cached_block_by_hash") as mock_ab:
        mock_analysis = MagicMock()
        mock_analysis.model_dump.return_value = {
            "height": 800000, "hash": block_hash,
            "tx_count": 2000, "size": 1000000, "weight": 3000000,
            "top_fee_txids": [],
        }
        mock_ab.return_value = mock_analysis
        resp = client.get(f"/api/v1/blocks/{block_hash}")
        assert resp.status_code == 200


def test_blocks_invalid_hash(client):
    """Invalid block hash should return 422."""
    resp = client.get("/api/v1/blocks/not-a-valid-hash")
    assert resp.status_code == 422


def test_block_stats(client):
    """Block stats endpoint."""
    resp = client.get("/api/v1/blocks/880000/stats")
    assert resp.status_code == 200
    assert resp.json()["data"]["height"] == 880000


def test_transaction_analysis(client, mock_rpc):
    """Transaction analysis endpoint."""
    txid = "a" * 64
    with patch("bitcoin_api.routers.transactions.analyze_transaction") as mock_at:
        mock_analysis = MagicMock()
        mock_analysis.model_dump.return_value = {
            "txid": txid, "version": 2, "size": 225,
            "fee_sats": 5000, "is_segwit": True,
        }
        mock_at.return_value = mock_analysis
        resp = client.get(f"/api/v1/tx/{txid}")
        assert resp.status_code == 200
        assert resp.json()["data"]["txid"] == txid


def test_transaction_invalid_txid(client):
    """Invalid txid should return 422."""
    resp = client.get("/api/v1/tx/not-a-txid")
    assert resp.status_code == 422


def test_raw_transaction(client):
    """Raw transaction endpoint."""
    txid = "a" * 64
    resp = client.get(f"/api/v1/tx/{txid}/raw")
    assert resp.status_code == 200


def test_raw_transaction_invalid_txid(client):
    """Invalid txid on raw endpoint should return 422."""
    resp = client.get("/api/v1/tx/xyz/raw")
    assert resp.status_code == 422


def test_mempool_analysis(client, mock_rpc):
    """Full mempool analysis endpoint."""
    with patch("bitcoin_api.routers.mempool.cached_mempool_analysis") as mock_ma:
        mock_summary = MagicMock()
        mock_summary.model_dump.return_value = {
            "size": 15000, "bytes": 8500000, "fee_histogram": [],
            "congestion": "normal",
        }
        mock_ma.return_value = mock_summary
        resp = client.get("/api/v1/mempool")
        assert resp.status_code == 200
        assert resp.json()["data"]["size"] == 15000


def test_mempool_tx(client):
    """Mempool entry for specific tx."""
    txid = "a" * 64
    resp = client.get(f"/api/v1/mempool/tx/{txid}")
    assert resp.status_code == 200


def test_fees_recommended(client, mock_rpc):
    """Fee recommendation endpoint."""
    with patch("bitcoin_api.routers.fees.cached_fee_estimates") as mock_fe:
        mock_est = MagicMock()
        mock_est.conf_target = 6
        mock_est.fee_rate_sat_vb = 12.0
        mock_est.model_dump.return_value = {
            "conf_target": 6, "fee_rate_btc_kvb": 0.00012, "fee_rate_sat_vb": 12.0,
        }
        mock_fe.return_value = [mock_est]
        with patch("bitcoin_api.routers.fees.fee_recommendation", return_value="Normal fees"):
            resp = client.get("/api/v1/fees/recommended")
            assert resp.status_code == 200
            assert "recommendation" in resp.json()["data"]


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


def test_request_id_in_response(client):
    """All responses should include X-Request-ID header."""
    resp = client.get("/api/v1/network")
    assert "X-Request-ID" in resp.headers
    request_id = resp.headers["X-Request-ID"]
    assert len(request_id) == 36  # UUID format


def test_rpc_error_not_found(client, mock_rpc):
    """RPC error -5 should map to 404."""
    from bitcoinlib_rpc.rpc import RPCError

    with patch(
        "bitcoin_api.routers.transactions.analyze_transaction",
        side_effect=RPCError(-5, "Transaction not found"),
    ):
        resp = client.get("/api/v1/tx/" + "a" * 64)
        assert resp.status_code == 404
        assert resp.json()["error"]["title"] == "Not Found"


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
    """ConnectionError should return 502 Node Unreachable."""
    mock_rpc.call.side_effect = ConnectionError("refused")
    resp = client.get("/api/v1/network")
    assert resp.status_code == 502
    assert "Node Unreachable" in resp.json()["error"]["title"]


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


# --- Sprint 3 tests ---


def test_network_forks(client):
    """Chain tips endpoint should return getchaintips data."""
    resp = client.get("/api/v1/network/forks")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert body["data"][0]["status"] == "active"


def test_decode_transaction(authed_client):
    """POST /decode should decode raw tx hex."""
    resp = authed_client.post("/api/v1/decode", json={"hex": "0200000001"})
    assert resp.status_code == 200
    body = resp.json()
    assert "txid" in body["data"]


def test_decode_invalid_hex(authed_client):
    """POST /decode with non-hex should return 422."""
    resp = authed_client.post("/api/v1/decode", json={"hex": "not-hex!"})
    assert resp.status_code == 422


# --- Sprint 4 tests ---


def test_negative_block_height(client):
    """Negative block height should return 422."""
    resp = client.get("/api/v1/blocks/-1")
    assert resp.status_code == 422


def test_negative_block_stats_height(client):
    """Negative height on stats should return 422."""
    resp = client.get("/api/v1/blocks/-1/stats")
    assert resp.status_code == 422


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


def test_mempool_tx_invalid_txid(client):
    """Invalid txid on mempool entry should return 422."""
    resp = client.get("/api/v1/mempool/tx/bad-txid")
    assert resp.status_code == 422


def test_unified_error_format_422(client):
    """FastAPI validation errors should use our ErrorResponse format."""
    resp = client.get("/api/v1/fees/notanumber")
    assert resp.status_code == 422
    body = resp.json()
    assert "error" in body
    assert body["error"]["status"] == 422
    assert body["error"]["title"] == "Validation Error"
    assert "request_id" in body["error"]


def test_version_in_root(client):
    """Root endpoint should show version."""
    resp = client.get("/")
    body = resp.json()
    assert "version" in body
    assert body["version"]  # not empty


# --- Sprint 5 tests ---


def test_healthz_no_rpc(client):
    """Process-alive healthcheck should work without RPC."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_catch_all_500(client, mock_rpc):
    """Unhandled exceptions should return 500 with standard error envelope."""
    mock_rpc.call.side_effect = RuntimeError("unexpected")
    resp = client.get("/api/v1/network")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["status"] == 500
    assert body["error"]["title"] == "Internal Server Error"
    assert "request_id" in body["error"]


def test_429_has_request_id(client):
    """Rate limit 429 responses should include request_id in error body."""
    for _ in range(30):
        client.get("/api/v1/fees/6")
    resp = client.get("/api/v1/fees/6")
    assert resp.status_code == 429
    body = resp.json()
    assert body["error"]["request_id"] is not None
    assert "X-Request-ID" in resp.headers


def test_broadcast_transaction(authed_client):
    """POST /broadcast should return txid."""
    resp = authed_client.post("/api/v1/broadcast", json={"hex": "0200000001"})
    assert resp.status_code == 200
    body = resp.json()
    assert "txid" in body["data"]


def test_broadcast_invalid_hex(authed_client):
    """POST /broadcast with non-hex should return 422."""
    resp = authed_client.post("/api/v1/broadcast", json={"hex": "not-hex!"})
    assert resp.status_code == 422


def test_vout_negative(client):
    """Negative vout should return 422."""
    txid = "a" * 64
    resp = client.get(f"/api/v1/utxo/{txid}/-1")
    assert resp.status_code == 422


def test_blocks_latest_has_chain(client, mock_rpc):
    """Latest block should have chain in meta (not None)."""
    with patch("bitcoin_api.routers.blocks.cached_block_analysis") as mock_ba:
        mock_analysis = MagicMock()
        mock_analysis.model_dump.return_value = {
            "height": 880000, "hash": "a" * 64,
            "tx_count": 3500, "size": 1500000, "weight": 3993000,
            "top_fee_txids": [],
        }
        mock_ba.return_value = mock_analysis
        resp = client.get("/api/v1/blocks/latest")
        assert resp.status_code == 200
        assert resp.json()["meta"]["chain"] == "main"


def test_network_moved_to_network_router(client):
    """GET /network should work (moved from status to network router)."""
    resp = client.get("/api/v1/network")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["connections"] == 125


def test_daily_rate_limit_uses_bucket(client, mock_rpc):
    """Anonymous users should have daily limits enforced via IP bucket."""
    from bitcoin_api.db import get_db
    # Make a request (anonymous, so bucket = IP)
    client.get("/api/v1/fees/6")
    conn = get_db()
    rows = conn.execute("SELECT key_hash FROM usage_log").fetchall()
    # Anonymous users should log with IP (bucket), not NULL
    assert len(rows) >= 1
    # At least one row should have a non-NULL key_hash (the IP)
    hashes = [dict(r)["key_hash"] for r in rows]
    assert any(h is not None for h in hashes)


# --- Phase 1 Security Tests ---

def test_anonymous_post_broadcast_rejected(client):
    """Anonymous users cannot broadcast transactions."""
    resp = client.post("/api/v1/broadcast", json={"hex": "0200000001"})
    assert resp.status_code == 403
    assert "API key required" in resp.json()["error"]["detail"]

def test_anonymous_post_decode_rejected(client):
    """Anonymous users cannot decode transactions."""
    resp = client.post("/api/v1/decode", json={"hex": "0200000001"})
    assert resp.status_code == 403
    assert "API key required" in resp.json()["error"]["detail"]

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


# --- v0.2 endpoints ---


def test_mempool_txids(client):
    resp = client.get("/api/v1/mempool/txids")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 2


def test_mempool_recent(client):
    resp = client.get("/api/v1/mempool/recent?count=5")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert isinstance(data, list)
    assert len(data) == 2  # only 2 in mock mempool
    # Should be sorted by time descending
    assert data[0]["time"] >= data[1]["time"]
    assert "fee_rate" in data[0]
    assert "vsize" in data[0]


def test_mempool_recent_max_count(client):
    resp = client.get("/api/v1/mempool/recent?count=200")
    assert resp.status_code == 200
    # Should cap at 100, but we only have 2 in mock


def test_block_tip_height(client):
    resp = client.get("/api/v1/blocks/tip/height")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == 880000


def test_block_tip_hash(client):
    resp = client.get("/api/v1/blocks/tip/hash")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670"


def test_block_txids(client):
    block_hash = "abc" * 21 + "a"
    resp = client.get(f"/api/v1/blocks/{block_hash}/txids")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 2


def test_block_txids_invalid_hash(client):
    resp = client.get("/api/v1/blocks/not-a-hash/txids")
    assert resp.status_code == 422


def test_block_txs(client):
    block_hash = "abc" * 21 + "a"
    resp = client.get(f"/api/v1/blocks/{block_hash}/txs?start=0&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)


def test_block_txs_invalid_hash(client):
    resp = client.get("/api/v1/blocks/xyz/txs")
    assert resp.status_code == 422


def test_tx_status(client):
    txid = "abc" * 21 + "a"
    resp = client.get(f"/api/v1/tx/{txid}/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["confirmed"] is True
    assert body["data"]["confirmations"] == 1000
    assert body["data"]["block_height"] == 879000


def test_tx_status_invalid_txid(client):
    resp = client.get("/api/v1/tx/not-a-txid/status")
    assert resp.status_code == 422


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


# --- v0.2.1 endpoints ---


def test_tx_hex(client):
    txid = "a" * 64
    resp = client.get(f"/api/v1/tx/{txid}/hex")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], str)
    assert len(body["data"]) > 0


def test_tx_hex_invalid_txid(client):
    resp = client.get("/api/v1/tx/bad/hex")
    assert resp.status_code == 422


def test_tx_outspends(client):
    txid = "abc" * 21 + "a"
    resp = client.get(f"/api/v1/tx/{txid}/outspends")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 2  # mock has 2 vouts
    assert "spent" in body["data"][0]
    assert "vout" in body["data"][0]


def test_tx_outspends_invalid_txid(client):
    resp = client.get("/api/v1/tx/xyz/outspends")
    assert resp.status_code == 422


def test_block_header(client):
    block_hash = "abc" * 21 + "a"
    resp = client.get(f"/api/v1/blocks/{block_hash}/header")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], str)
    assert len(body["data"]) > 0


def test_block_header_invalid_hash(client):
    resp = client.get("/api/v1/blocks/not-a-hash/header")
    assert resp.status_code == 422


def test_fees_mempool_blocks(client):
    resp = client.get("/api/v1/fees/mempool-blocks")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    # With 2 mock mempool txs, should produce at least 1 block
    if len(body["data"]) > 0:
        block = body["data"][0]
        assert "block_index" in block
        assert "min_fee_rate" in block
        assert "tx_count" in block
        assert "total_weight" in block


def test_validate_address(client):
    resp = client.get("/api/v1/network/validate-address/bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["isvalid"] is True


def test_prices(client):
    from unittest.mock import patch
    mock_price = {
        "USD": 92000.0, "EUR": 84000.0, "GBP": 72000.0,
        "JPY": 13800000.0, "CAD": 126000.0, "AUD": 141000.0,
        "change_24h_pct": 2.5,
    }
    with patch("bitcoin_api.routers.prices._get_cached_price", return_value=mock_price):
        resp = client.get("/api/v1/prices")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["USD"] == 92000.0
        assert "change_24h_pct" in body["data"]
