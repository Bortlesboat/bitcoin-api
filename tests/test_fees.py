"""Tests for fee-related endpoints."""

from unittest.mock import patch, MagicMock


def test_fee_for_target(client):
    resp = client.get("/api/v1/fees/6")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["conf_target"] == 6
    assert body["data"]["fee_rate_sat_vb"] == 12.0


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


def test_fees_mempool_blocks(client):
    resp = client.get("/api/v1/fees/mempool-blocks")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    # With 2 mock mempool txs, should produce at least 1 block
    assert len(body["data"]) > 0
    block = body["data"][0]
    assert "block_index" in block
    assert "min_fee_rate" in block
    assert "tx_count" in block
    assert "total_weight" in block


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
    assert data["trend"]["snapshots_available"] >= 2  # background job may add more


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


def test_unified_error_format_422(client):
    """FastAPI validation errors should use our ErrorResponse format."""
    resp = client.get("/api/v1/fees/notanumber")
    assert resp.status_code == 422
    body = resp.json()
    assert "error" in body
    assert body["error"]["status"] == 422
    assert body["error"]["title"] == "Validation Error"
    assert "request_id" in body["error"]


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


def test_cache_control_on_fee_endpoint(client):
    """Fee endpoints should include Cache-Control header."""
    resp = client.get("/api/v1/fees")
    assert resp.status_code == 200
    assert "Cache-Control" in resp.headers
    assert "max-age=10" in resp.headers["Cache-Control"]


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


def test_429_has_request_id(client):
    """Rate limit 429 responses should include request_id in error body."""
    for _ in range(30):
        client.get("/api/v1/fees/6")
    resp = client.get("/api/v1/fees/6")
    assert resp.status_code == 429
    body = resp.json()
    assert body["error"]["request_id"] is not None
    assert "X-Request-ID" in resp.headers
