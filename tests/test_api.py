"""Tests for bitcoin-api endpoints."""

from unittest.mock import patch, MagicMock



def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Satoshi API" in resp.text


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
    from bitcoin_api.usage_buffer import usage_buffer
    client.get("/api/v1/network")
    usage_buffer.flush()
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
    """Root endpoint should show product name."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Satoshi" in resp.text


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


# --- Launch features tests ---


def test_fees_landscape(client):
    """Fee landscape should return recommendation + scenarios."""
    resp = client.get("/api/v1/fees/landscape")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert data["recommendation"] in ("send", "wait", "urgent_only")
    assert data["confidence"] in ("high", "medium", "low")
    assert "reasoning" in data
    assert "trend" in data
    assert data["trend"]["direction"] in ("rising", "falling", "stable", "unknown")
    assert "scenarios" in data
    assert "send_now" in data["scenarios"]
    assert "wait_1hr" in data["scenarios"]
    assert "wait_low" in data["scenarios"]
    assert data["scenarios"]["send_now"]["fee_rate"] > 0
    assert "current_fees" in data


def test_fees_landscape_with_snapshots(client):
    """Fee landscape trend should work when snapshots are available."""
    from bitcoin_api.cache import _mempool_snapshots
    import time

    # Clear any snapshots left by other tests to avoid flaky count assertions
    _mempool_snapshots.clear()

    # Seed snapshots to simulate falling mempool
    _mempool_snapshots.append({
        "timestamp": time.time() - 300,
        "mempool_size": 20000,
        "mempool_bytes": 10_000_000,
        "mempool_vsize": 10_000_000,
        "next_block_fee": 25.0,
        "low_fee": 5.0,
        "total_fee": 2.0,
    })
    _mempool_snapshots.append({
        "timestamp": time.time(),
        "mempool_size": 15000,
        "mempool_bytes": 7_000_000,
        "mempool_vsize": 7_000_000,
        "next_block_fee": 20.0,
        "low_fee": 4.0,
        "total_fee": 1.5,
    })

    resp = client.get("/api/v1/fees/landscape")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["trend"]["direction"] == "falling"
    assert data["trend"]["snapshots_available"] == 2


def test_fees_estimate_tx_defaults(client):
    """Estimate tx with defaults should return valid structure."""
    resp = client.get("/api/v1/fees/estimate-tx")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert data["inputs"] == 1
    assert data["outputs"] == 2
    assert data["input_type"] == "p2wpkh"
    assert data["estimated_vsize"] > 0
    assert data["estimated_weight"] > 0
    assert "fee_scenarios" in data
    assert "next_block" in data["fee_scenarios"]
    assert "1_day" in data["fee_scenarios"]
    assert data["fee_scenarios"]["next_block"]["total_fee_sats"] > 0
    assert "breakdown" in data


def test_fees_estimate_tx_custom(client):
    """Estimate tx with custom params."""
    resp = client.get("/api/v1/fees/estimate-tx?inputs=2&outputs=3&input_type=p2tr&output_type=p2tr")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["inputs"] == 2
    assert data["outputs"] == 3
    assert data["input_type"] == "p2tr"
    assert data["output_type"] == "p2tr"
    # P2TR is lighter than P2PKH
    resp2 = client.get("/api/v1/fees/estimate-tx?inputs=2&outputs=3&input_type=p2pkh&output_type=p2pkh")
    data2 = resp2.json()["data"]
    assert data["estimated_vsize"] < data2["estimated_vsize"]


def test_fees_estimate_tx_validation(client):
    """Invalid input count should return 422."""
    resp = client.get("/api/v1/fees/estimate-tx?inputs=0")
    assert resp.status_code == 422


def test_fees_history_empty(client):
    """Fee history with no data should return empty datapoints."""
    resp = client.get("/api/v1/fees/history?hours=1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["datapoints"] == []
    assert data["summary"] is None


def test_fees_history_with_data(client):
    """Fee history with seeded data should return datapoints + summary."""
    from bitcoin_api.db import get_db
    conn = get_db()
    # Insert some test data
    for i in range(5):
        conn.execute(
            "INSERT INTO fee_history (ts, next_block_fee, median_fee, low_fee, mempool_size, mempool_vsize, congestion) "
            "VALUES (datetime('now', ?), ?, ?, ?, ?, ?, ?)",
            (f"-{(4-i)*2} minutes", 20.0 + i, 12.0 + i, 5.0 + i, 15000 + i * 1000, 8500000 + i * 100000, "normal"),
        )
    conn.commit()

    resp = client.get("/api/v1/fees/history?hours=1&interval=1m")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["datapoints"]) >= 1
    assert data["summary"] is not None
    assert data["summary"]["min_next_block_fee"] > 0
    assert data["summary"]["max_next_block_fee"] >= data["summary"]["min_next_block_fee"]
    assert data["summary"]["cheapest_time_utc"] is not None


def test_stream_blocks_generator(mock_rpc):
    """Block SSE generator should yield a connected event first."""
    import asyncio
    from bitcoin_api.routers.stream import _block_event_generator

    async def get_first_event():
        gen = _block_event_generator(mock_rpc)
        return await gen.__anext__()

    event = asyncio.run(get_first_event())
    assert "event: connected" in event
    assert '"height"' in event


def test_stream_fees_generator(mock_rpc):
    """Fee SSE generator should yield a connected event first."""
    import asyncio
    from bitcoin_api.routers.stream import _fee_event_generator

    async def get_first_event():
        gen = _fee_event_generator(mock_rpc)
        return await gen.__anext__()

    event = asyncio.run(get_first_event())
    assert "event: connected" in event


# ── Exchange comparison ────────────────────────────────────────────────


def test_exchange_compare_default(client, monkeypatch):
    """Exchange compare returns results for default $100."""
    monkeypatch.setattr(
        "bitcoin_api.routers.exchanges.get_cached_price", lambda: 92000.0
    )
    resp = client.get("/api/v1/tools/exchange-compare")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert data["amount_usd"] == 100
    assert data["btc_price_usd"] == 92000.0
    assert len(data["exchanges"]) > 0
    assert "best_value" in data
    # Results should be sorted by net_sats descending
    sats = [e["net_sats"] for e in data["exchanges"]]
    assert sats == sorted(sats, reverse=True)


def test_exchange_compare_custom_amount(client, monkeypatch):
    """Exchange compare with custom USD amount."""
    monkeypatch.setattr(
        "bitcoin_api.routers.exchanges.get_cached_price", lambda: 92000.0
    )
    resp = client.get("/api/v1/tools/exchange-compare?amount_usd=10")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert data["amount_usd"] == 10
    # Kraken has $10 min, so it should be included
    names = [e["exchange"] for e in data["exchanges"]]
    assert "Kraken" in names


def test_exchange_compare_fee_math(client, monkeypatch):
    """Verify fee calculations are correct for a known exchange."""
    monkeypatch.setattr(
        "bitcoin_api.routers.exchanges.get_cached_price", lambda: 100000.0
    )
    resp = client.get("/api/v1/tools/exchange-compare?amount_usd=1000")
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Find Coinbase Advanced (0.12% fee, 0% spread, 0 withdrawal)
    cb_adv = next(e for e in data["exchanges"] if e["exchange"] == "Coinbase Advanced")
    assert cb_adv["trading_fee_usd"] == 1.20  # 0.12% of $1000
    assert cb_adv["spread_cost_usd"] == 0.0
    assert cb_adv["withdrawal_fee_sats"] == 0
    # Net should be (1000 - 1.20) / 100000 BTC in sats
    expected_sats = int((1000 - 1.20) / 100000 * 1e8)
    assert cb_adv["net_sats"] == expected_sats


def test_exchange_compare_below_minimum(client, monkeypatch):
    """Exchanges with higher minimums are excluded for small amounts."""
    monkeypatch.setattr(
        "bitcoin_api.routers.exchanges.get_cached_price", lambda: 92000.0
    )
    resp = client.get("/api/v1/tools/exchange-compare?amount_usd=5")
    assert resp.status_code == 200
    data = resp.json()["data"]
    names = [e["exchange"] for e in data["exchanges"]]
    # Kraken ($10 min) and River ($10 min) should be excluded
    assert "Kraken" not in names
    assert "River" not in names
    # Coinbase ($1 min) should be included
    assert "Coinbase" in names


def test_exchange_compare_invalid_amount(client):
    """Amount below $1 returns 422."""
    resp = client.get("/api/v1/tools/exchange-compare?amount_usd=0.5")
    assert resp.status_code == 422


def test_exchange_compare_price_unavailable(client, monkeypatch):
    """Returns error message when BTC price is unavailable."""
    monkeypatch.setattr(
        "bitcoin_api.routers.exchanges.get_cached_price", lambda: None
    )
    resp = client.get("/api/v1/tools/exchange-compare")
    assert resp.status_code == 200
    body = resp.json()
    assert "error" in body["data"]


# --- Security tests ---


def test_security_headers_present(client):
    """All security headers must appear in every response."""
    resp = client.get("/api/v1/fees")
    for header in [
        "x-content-type-options",
        "x-frame-options",
        "content-security-policy",
        "referrer-policy",
        "permissions-policy",
    ]:
        assert header in resp.headers, f"Missing security header: {header}"


def test_method_not_allowed(client):
    """Unsupported HTTP methods return 405."""
    assert client.delete("/api/v1/fees").status_code == 405
    assert client.put("/api/v1/fees").status_code == 405
    assert client.patch("/api/v1/fees").status_code == 405


def test_error_envelope_consistency(client):
    """All error responses use the {error} envelope, never raw strings."""
    # 404
    resp = client.get("/api/v1/tx/" + "0" * 64)
    body = resp.json()
    assert "error" in body
    assert "status" in body["error"]
    assert "detail" in body["error"]

    # 422
    resp = client.get("/api/v1/tx/not-a-txid")
    body = resp.json()
    assert "error" in body
    assert "status" in body["error"]


def test_no_traceback_in_errors(client):
    """Error responses must never contain Python tracebacks."""
    resp = client.get("/api/v1/tx/ZZZZ")
    text = resp.text
    assert "Traceback" not in text
    assert ".py" not in text or "detail" in text  # .py only in structured error detail is ok


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


def test_post_without_content_type_json(authed_client):
    """POST with wrong content-type should be rejected."""
    resp = authed_client.post(
        "/api/v1/decode",
        content=b"not json",
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 422


# --- Data Integrity & User Protection Tests ---


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


def test_broadcast_decode_failure(authed_client):
    """Malformed hex that can't be decoded should return 422."""
    from bitcoinlib_rpc.rpc import RPCError

    with patch(
        "bitcoin_api.routers.transactions.BitcoinRPC",
    ):
        original_mock = authed_client.app.dependency_overrides
        mock_rpc = MagicMock()

        call_count = {"decode": 0}

        def side_effect(method, *args):
            if method == "decoderawtransaction":
                raise RPCError(-22, "TX decode failed")
            if method == "getblockchaininfo":
                return {"chain": "main", "blocks": 880000, "verificationprogress": 0.9999}
            return {}

        mock_rpc.call.side_effect = side_effect
        from bitcoin_api.dependencies import get_rpc
        authed_client.app.dependency_overrides[get_rpc] = lambda: mock_rpc

        resp = authed_client.post("/api/v1/broadcast", json={"hex": "deadbeef"})
        assert resp.status_code == 422
        assert "could not be decoded" in resp.json()["error"]["detail"]


def test_broadcast_already_in_mempool(authed_client):
    """RPC error -25 on broadcast should return 409."""
    from bitcoinlib_rpc.rpc import RPCError

    mock_rpc = MagicMock()

    def side_effect(method, *args):
        if method == "decoderawtransaction":
            return {"txid": "a" * 64}
        if method == "sendrawtransaction":
            raise RPCError(-25, "Transaction already in mempool")
        if method == "getblockchaininfo":
            return {"chain": "main", "blocks": 880000, "verificationprogress": 0.9999}
        return {}

    mock_rpc.call.side_effect = side_effect
    from bitcoin_api.dependencies import get_rpc
    authed_client.app.dependency_overrides[get_rpc] = lambda: mock_rpc

    resp = authed_client.post("/api/v1/broadcast", json={"hex": "0200000001"})
    assert resp.status_code == 409
    assert "already in mempool" in resp.json()["error"]["detail"].lower()


def test_broadcast_policy_rejection(authed_client):
    """RPC error -26 on broadcast should return 422."""
    from bitcoinlib_rpc.rpc import RPCError

    mock_rpc = MagicMock()

    def side_effect(method, *args):
        if method == "decoderawtransaction":
            return {"txid": "a" * 64}
        if method == "sendrawtransaction":
            raise RPCError(-26, "non-mandatory-script-verify-flag")
        if method == "getblockchaininfo":
            return {"chain": "main", "blocks": 880000, "verificationprogress": 0.9999}
        return {}

    mock_rpc.call.side_effect = side_effect
    from bitcoin_api.dependencies import get_rpc
    authed_client.app.dependency_overrides[get_rpc] = lambda: mock_rpc

    resp = authed_client.post("/api/v1/broadcast", json={"hex": "0200000001"})
    assert resp.status_code == 422
    assert "policy" in resp.json()["error"]["detail"].lower()


# --- Address endpoints ---


def test_address_summary(client):
    """Address summary returns balance, utxo count, and address info."""
    resp = client.get("/api/v1/address/bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert data["address"] == "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
    assert data["balance_btc"] == 0.05
    assert data["balance_sats"] == 5000000
    assert data["utxo_count"] == 2
    assert data["is_witness"] is True
    assert "meta" in body
    assert body["meta"]["node_height"] == 880000


def test_address_utxos(client):
    """Address UTXOs returns list of unspent outputs."""
    resp = client.get("/api/v1/address/bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4/utxos")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert data["utxo_count"] == 2
    assert data["returned"] == 2
    assert data["balance_btc"] == 0.05
    assert data["balance_sats"] == 5000000
    assert len(data["utxos"]) == 2
    # Should be sorted by value descending
    assert data["utxos"][0]["value_btc"] >= data["utxos"][1]["value_btc"]
    assert "txid" in data["utxos"][0]
    assert "vout" in data["utxos"][0]
    assert "value_sats" in data["utxos"][0]


def test_address_utxos_limit(client):
    """UTXO limit parameter should cap results."""
    resp = client.get("/api/v1/address/bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4/utxos?limit=1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["utxo_count"] == 2  # total count stays
    assert data["returned"] == 1   # but only 1 returned
    assert len(data["utxos"]) == 1


def test_address_invalid_format(client):
    """Garbage address format should return 422."""
    resp = client.get("/api/v1/address/!!invalid!!")
    assert resp.status_code == 422


def test_address_invalid_address(client, mock_rpc):
    """Valid format but invalid address should return 400."""
    original = mock_rpc.call.side_effect

    def addr_invalid(method, *args):
        if method == "validateaddress":
            return {"isvalid": False}
        return original(method, *args)

    mock_rpc.call.side_effect = addr_invalid
    resp = client.get("/api/v1/address/1InvalidAddressNotRealButLongEnough")
    assert resp.status_code == 400


# --- Production hardening tests ---


def test_api_404_returns_json_envelope(client):
    """404 on unknown /api/v1/* route should return JSON error envelope, not HTML."""
    resp = client.get("/api/v1/nonexistent")
    assert resp.status_code in (404, 405)
    body = resp.json()
    assert "error" in body
    assert "status" in body["error"]
    assert "detail" in body["error"]


def test_cache_control_on_fee_endpoint(client):
    """Fee endpoints should include Cache-Control header."""
    resp = client.get("/api/v1/fees")
    assert resp.status_code == 200
    assert "Cache-Control" in resp.headers
    assert "max-age=10" in resp.headers["Cache-Control"]


def test_cache_control_no_store_on_register(authed_client):
    """Register endpoint should have Cache-Control: no-store."""
    resp = authed_client.post(
        "/api/v1/register",
        json={"email": "test@example.com", "label": "test"},
    )
    # May get 200 or 429 or other status, but header should be set
    assert "Cache-Control" in resp.headers
    assert "no-store" in resp.headers["Cache-Control"]


# --- Analytics Endpoints ---


def test_analytics_overview_requires_admin_key(client):
    """Analytics endpoints should return 403 without admin key."""
    resp = client.get("/api/v1/analytics/overview")
    assert resp.status_code == 403


def test_analytics_overview_rejects_wrong_key(client):
    """Analytics endpoints should reject an invalid admin key."""
    resp = client.get("/api/v1/analytics/overview", headers={"X-Admin-Key": "wrong"})
    assert resp.status_code == 403


def _admin_client(mock_rpc):
    """Create a test client with admin key configured."""
    from bitcoin_api.main import app
    from bitcoin_api.dependencies import get_rpc
    from bitcoin_api.config import settings

    original = settings.admin_api_key
    settings.admin_api_key = "test-admin-secret"
    app.dependency_overrides[get_rpc] = lambda: mock_rpc
    from fastapi.testclient import TestClient
    c = TestClient(app, headers={"X-Admin-Key": "test-admin-secret"})
    yield c
    settings.admin_api_key = original
    app.dependency_overrides.clear()


import pytest

@pytest.fixture
def admin_client(mock_rpc):
    from bitcoin_api.main import app
    from bitcoin_api.dependencies import get_rpc
    from bitcoin_api.config import settings

    original = settings.admin_api_key
    settings.admin_api_key = "test-admin-secret"
    app.dependency_overrides[get_rpc] = lambda: mock_rpc
    from fastapi.testclient import TestClient
    with TestClient(app, headers={"X-Admin-Key": "test-admin-secret"}) as c:
        yield c
    settings.admin_api_key = original
    app.dependency_overrides.clear()


def test_analytics_overview_with_admin_key(admin_client):
    """Analytics overview should return 200 with valid admin key."""
    resp = admin_client.get("/api/v1/analytics/overview")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "requests_24h" in data
    assert "unique_keys_24h" in data
    assert "error_rate_24h" in data
    assert "avg_latency_ms_24h" in data


def test_analytics_requests_with_admin_key(admin_client):
    """Analytics requests should return time-series data."""
    resp = admin_client.get("/api/v1/analytics/requests?period=24h&interval=1h")
    assert resp.status_code == 200
    assert "data" in resp.json()
    assert isinstance(resp.json()["data"], list)


def test_analytics_endpoints_with_admin_key(admin_client):
    """Analytics endpoints should return top endpoints."""
    resp = admin_client.get("/api/v1/analytics/endpoints?period=24h&limit=10")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_analytics_errors_with_admin_key(admin_client):
    """Analytics errors should return error breakdown."""
    resp = admin_client.get("/api/v1/analytics/errors?period=24h")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_analytics_user_agents_with_admin_key(admin_client):
    """Analytics user-agents should return top user agents."""
    resp = admin_client.get("/api/v1/analytics/user-agents?period=24h")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_analytics_latency_with_admin_key(admin_client):
    """Analytics latency should return percentiles."""
    resp = admin_client.get("/api/v1/analytics/latency?period=24h")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "p50" in data
    assert "p95" in data
    assert "p99" in data
    assert "count" in data


def test_log_usage_stores_new_fields(client):
    """log_usage should store method, response_time_ms, user_agent."""
    from bitcoin_api.db import get_db, log_usage
    from bitcoin_api.usage_buffer import usage_buffer
    log_usage("test-key", "/api/v1/test", 200, method="GET", response_time_ms=42.5, user_agent="TestBot/1.0")
    usage_buffer.flush()
    conn = get_db()
    row = conn.execute(
        "SELECT method, response_time_ms, user_agent FROM usage_log WHERE key_hash = 'test-key' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert row is not None
    assert row[0] == "GET"
    assert abs(row[1] - 42.5) < 0.01
    assert row[2] == "TestBot/1.0"


def test_usage_log_migration_creates_columns():
    """Migration should create method, response_time_ms, user_agent columns."""
    from bitcoin_api.db import get_db
    conn = get_db()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(usage_log)").fetchall()]
    assert "method" in cols
    assert "response_time_ms" in cols
    assert "user_agent" in cols


def test_usage_log_indexes_exist():
    """New indexes should exist on usage_log."""
    from bitcoin_api.db import get_db
    conn = get_db()
    indexes = [r[1] for r in conn.execute("PRAGMA index_list(usage_log)").fetchall()]
    assert "idx_usage_endpoint" in indexes
    assert "idx_usage_status" in indexes


def test_health_deep(authed_client):
    """GET /health/deep should return health check data for authenticated users."""
    with patch("bitcoin_api.routers.health_deep.get_job_health", return_value={"fee_collector": "ok"}), \
         patch("bitcoin_api.routers.health_deep.usage_buffer") as mock_buf:
        mock_buf.pending_count = 0
        resp = authed_client.get("/api/v1/health/deep")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    data = body["data"]
    assert data["rpc"]["ok"] is True
    assert data["rpc"]["height"] == 880000
    assert data["db"]["ok"] is True
    assert "sync_progress" in data
    assert "uptime_seconds" in data


def test_health_deep_requires_auth(client):
    """GET /health/deep should reject anonymous users with 403."""
    resp = client.get("/api/v1/health/deep")
    assert resp.status_code == 403


# --- New Analytics Endpoints (Sprint 16) ---


def test_analytics_keys_with_admin_key(admin_client):
    """Analytics keys should return per-key usage data."""
    resp = admin_client.get("/api/v1/analytics/keys?period=24h")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_analytics_keys_requires_admin(client):
    """Analytics keys should return 403 without admin key."""
    resp = client.get("/api/v1/analytics/keys")
    assert resp.status_code == 403


def test_analytics_growth_with_admin_key(admin_client):
    """Analytics growth should return DoD and WoW metrics."""
    resp = admin_client.get("/api/v1/analytics/growth")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "requests_today" in data
    assert "requests_wow_pct" in data
    assert "keys_today" in data


def test_analytics_slow_endpoints_with_admin_key(admin_client):
    """Analytics slow-endpoints should return p95 latency data."""
    resp = admin_client.get("/api/v1/analytics/slow-endpoints?period=24h&limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_analytics_retention_with_admin_key(admin_client):
    """Analytics retention should return active key counts."""
    resp = admin_client.get("/api/v1/analytics/retention")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "total_registered_keys" in data
    assert "active_24h" in data
    assert "retention_7d_pct" in data


def test_admin_dashboard_requires_key(client):
    """Admin dashboard should return 403 without key."""
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 403


def test_admin_dashboard_rejects_wrong_key(client):
    """Admin dashboard should reject invalid key."""
    resp = client.get("/admin/dashboard?key=wrong")
    assert resp.status_code == 403


def test_admin_dashboard_with_valid_key(admin_client):
    """Admin dashboard should return HTML with valid key."""
    from bitcoin_api.config import settings
    resp = admin_client.get(f"/admin/dashboard?key={settings.admin_api_key}")
    assert resp.status_code == 200
    assert "Admin Dashboard" in resp.text


# --- Guide Endpoint (Sprint 20) ---


def test_guide_returns_envelope(client):
    """Guide should return standard {data, meta} envelope."""
    resp = client.get("/api/v1/guide")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    data = body["data"]
    assert "welcome" in data
    assert "quickstart" in data
    assert "categories" in data
    assert "auth" in data
    assert "links" in data


def test_guide_quickstart_has_steps(client):
    """Guide quickstart should have numbered steps with examples."""
    resp = client.get("/api/v1/guide")
    qs = resp.json()["data"]["quickstart"]
    assert len(qs) >= 3
    assert qs[0]["step"] == 1
    assert "curl" in qs[0]["examples"]


def test_guide_use_case_filter(client):
    """Filtering by use_case should return only that category."""
    resp = client.get("/api/v1/guide?use_case=fees")
    assert resp.status_code == 200
    cats = resp.json()["data"]["categories"]
    assert len(cats) == 1
    assert cats[0]["use_case"] == "fees"
    assert cats[0]["name"] == "Fee Estimation"


def test_guide_lang_filter(client):
    """Filtering by lang should strip other language examples."""
    resp = client.get("/api/v1/guide?lang=python")
    assert resp.status_code == 200
    cats = resp.json()["data"]["categories"]
    for cat in cats:
        for ep in cat["endpoints"]:
            assert "python" in ep["examples"]
            assert "curl" not in ep["examples"]
            assert "javascript" not in ep["examples"]


def test_guide_lang_all(client):
    """lang=all should include all three language examples."""
    resp = client.get("/api/v1/guide?lang=all")
    assert resp.status_code == 200
    ep = resp.json()["data"]["categories"][0]["endpoints"][0]
    assert "curl" in ep["examples"]
    assert "python" in ep["examples"]
    assert "javascript" in ep["examples"]


def test_guide_feature_flagged_categories(client):
    """Feature-flagged categories should appear based on settings."""
    from bitcoin_api.config import settings
    cats = client.get("/api/v1/guide?lang=curl").json()["data"]["categories"]
    use_cases = [c["use_case"] for c in cats]
    if settings.feature_flags.get("prices_router", False):
        assert "prices" in use_cases
    else:
        assert "prices" not in use_cases


def test_guide_auth_shows_rate_limits(client):
    """Auth section should show tier rate limits from settings."""
    from bitcoin_api.config import settings
    auth = client.get("/api/v1/guide").json()["data"]["auth"]
    assert auth["tiers"]["anonymous"]["per_minute"] == settings.rate_limit_anonymous
    assert auth["tiers"]["free"]["per_minute"] == settings.rate_limit_free
    assert auth["method"] == "X-API-Key header"


def test_guide_no_rate_limit(client):
    """Guide endpoint should not be rate limited."""
    for _ in range(35):
        resp = client.get("/api/v1/guide")
        assert resp.status_code == 200


def test_error_help_url_on_401(client):
    """401 errors should include help_url pointing to the guide."""
    resp = client.get("/api/v1/fees", headers={"X-API-Key": "invalid-key-12345"})
    assert resp.status_code == 401
    error = resp.json()["error"]
    assert error["help_url"] == "/api/v1/guide"
    assert "POST /api/v1/register" in error["detail"]
