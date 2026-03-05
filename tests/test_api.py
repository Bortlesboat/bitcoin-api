"""Tests for bitcoin-api endpoints."""

from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest


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
    """Block by hash should call analyze_block directly."""
    block_hash = "a" * 64
    with patch("bitcoin_api.routers.blocks.analyze_block") as mock_ab:
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


def test_decode_transaction(client):
    """POST /decode should decode raw tx hex."""
    resp = client.post("/api/v1/decode", json={"hex": "0200000001"})
    assert resp.status_code == 200
    body = resp.json()
    assert "txid" in body["data"]


def test_decode_invalid_hex(client):
    """POST /decode with non-hex should return 422."""
    resp = client.post("/api/v1/decode", json={"hex": "not-hex!"})
    assert resp.status_code == 422
