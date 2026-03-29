"""Tests for fee-related endpoints."""

from unittest.mock import patch, MagicMock

from bitcoin_api.config import settings


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


def test_fees_plan_defaults(client):
    """Plan endpoint with no params should return valid structure (defaults to simple_send)."""
    resp = client.get("/api/v1/fees/plan")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["transaction"]["inputs"] == 1
    assert data["transaction"]["outputs"] == 2
    assert data["transaction"]["address_type"] == "segwit"
    assert data["transaction"]["estimated_vsize"] > 0
    assert "cost_tiers" in data
    assert "immediate" in data["cost_tiers"]
    assert "standard" in data["cost_tiers"]
    assert "patient" in data["cost_tiers"]
    assert "opportunistic" in data["cost_tiers"]
    assert data["cost_tiers"]["immediate"]["total_fee_sats"] > 0
    assert data["recommendation"] in ("send", "wait", "urgent_only")
    assert 0 <= data["recommendation_confidence"] <= 1.0
    assert "delay_savings_pct" in data
    assert "trend" in data
    assert "available_profiles" in data


def test_fees_plan_with_profile(client):
    """Plan endpoint with profile preset."""
    resp = client.get("/api/v1/fees/plan?profile=batch_payout")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["transaction"]["inputs"] == 1
    assert data["transaction"]["outputs"] == 10
    assert data["profile"] == "batch_payout"
    assert "profile_description" in data


def test_fees_plan_with_custom_params(client):
    """Plan endpoint with explicit inputs/outputs/address_type."""
    resp = client.get("/api/v1/fees/plan?inputs=3&outputs=2&address_type=taproot")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["transaction"]["inputs"] == 3
    assert data["transaction"]["outputs"] == 2
    assert data["transaction"]["address_type"] == "taproot"
    assert data["transaction"]["script_type"] == "p2tr"


def test_fees_plan_with_history(client):
    """Plan endpoint should include historical comparison when fee history exists."""
    from bitcoin_api.db import get_db
    conn = get_db()
    for i in range(5):
        conn.execute(
            "INSERT INTO fee_history (ts, next_block_fee, median_fee, low_fee, mempool_size, mempool_vsize, congestion) "
            "VALUES (datetime('now', ?), ?, ?, ?, ?, ?, ?)",
            (f"-{(4-i)*30} minutes", 10.0 + i * 5, 8.0 + i, 3.0 + i, 15000, 8500000, "normal"),
        )
    conn.commit()

    resp = client.get("/api/v1/fees/plan")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "historical_comparison" in data
    assert data["historical_comparison"]["cheapest_fee_rate"] > 0
    # current_premium_pct can be negative if current fees are already below historical cheapest
    assert isinstance(data["historical_comparison"]["current_premium_pct"], (int, float))


def test_fees_plan_taproot_lighter(client):
    """Taproot transactions should have lower vsize than legacy."""
    resp_tr = client.get("/api/v1/fees/plan?inputs=1&outputs=2&address_type=taproot")
    resp_legacy = client.get("/api/v1/fees/plan?inputs=1&outputs=2&address_type=legacy")
    assert resp_tr.status_code == 200
    assert resp_legacy.status_code == 200
    assert resp_tr.json()["data"]["transaction"]["estimated_vsize"] < resp_legacy.json()["data"]["transaction"]["estimated_vsize"]


def test_fees_plan_invalid_inputs(client):
    """Plan endpoint with invalid inputs should return 422."""
    resp = client.get("/api/v1/fees/plan?inputs=0")
    assert resp.status_code == 422


def test_fees_plan_unknown_profile(client):
    """Unknown profile should fall back to defaults."""
    resp = client.get("/api/v1/fees/plan?profile=nonexistent")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["transaction"]["inputs"] == 1
    assert data["transaction"]["outputs"] == 2


def test_fees_savings_empty(client):
    """Savings endpoint with no fee history should return info message."""
    resp = client.get("/api/v1/fees/savings?hours=1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["datapoints"] == 0
    assert "message" in data


def test_fees_savings_with_data(client):
    """Savings endpoint with seeded fee history should return savings analysis."""
    from bitcoin_api.db import get_db
    conn = get_db()
    # Seed varying fee data to create meaningful savings
    fees = [5.0, 10.0, 20.0, 15.0, 8.0, 25.0, 12.0, 6.0, 18.0, 30.0]
    for i, fee in enumerate(fees):
        conn.execute(
            "INSERT INTO fee_history (ts, next_block_fee, median_fee, low_fee, mempool_size, mempool_vsize, congestion) "
            "VALUES (datetime('now', ?), ?, ?, ?, ?, ?, ?)",
            (f"-{(len(fees)-i)*5} minutes", fee, fee * 0.7, fee * 0.3, 15000, 8500000, "normal"),
        )
    conn.commit()

    resp = client.get("/api/v1/fees/savings?hours=1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["datapoints"] == 10
    assert data["reference_vsize"] == 141
    assert data["always_send_now"]["avg_fee_rate"] > 0
    assert data["optimal_timing"]["best_fee_rate"] == 5.0
    assert data["savings_per_tx"]["sats"] > 0
    assert data["savings_per_tx"]["percent"] > 0
    assert "monthly_projection" in data
    assert data["monthly_projection"]["total_savings_sats"] > 0
    assert "fee_range" in data
    assert data["fee_range"]["min"] == 5.0
    assert data["fee_range"]["max"] == 30.0


def test_fees_savings_independent_of_plan(client):
    """Savings endpoint should work independently (no RPC dependency)."""
    # Savings only needs DB data, not a live node — verify it works without mock_rpc issues
    resp = client.get("/api/v1/fees/savings")
    assert resp.status_code == 200
    assert "data" in resp.json()


def test_fees_plan_currency_usd(client):
    """Plan with currency=usd should include USD fields when price available."""
    from unittest.mock import patch
    with patch("bitcoin_api.routers.fees.get_cached_price", return_value=95000.0):
        resp = client.get("/api/v1/fees/plan?currency=usd")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["btc_price_usd"] == 95000.0
    assert "total_fee_usd" in data["cost_tiers"]["immediate"]
    assert isinstance(data["cost_tiers"]["immediate"]["total_fee_usd"], float)


def test_fees_plan_currency_usd_price_unavailable(client):
    """Plan with currency=usd should degrade gracefully when price unavailable."""
    from unittest.mock import patch
    with patch("bitcoin_api.routers.fees.get_cached_price", return_value=None):
        resp = client.get("/api/v1/fees/plan?currency=usd")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "btc_price_usd" not in data
    assert "total_fee_usd" not in data["cost_tiers"]["immediate"]
    assert "currency_note" in data
    # Sats and BTC values should still be present
    assert data["cost_tiers"]["immediate"]["total_fee_sats"] > 0
    assert data["cost_tiers"]["immediate"]["total_fee_btc"] > 0


def test_fees_plan_default_no_usd(client):
    """Plan without currency param should not include USD fields."""
    resp = client.get("/api/v1/fees/plan")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "btc_price_usd" not in data
    assert "total_fee_usd" not in data["cost_tiers"]["immediate"]


def test_fees_savings_currency_usd(client):
    """Savings with currency=usd should include USD fields."""
    from unittest.mock import patch
    from bitcoin_api.db import get_db
    conn = get_db()
    for i, fee in enumerate([5.0, 15.0, 25.0, 10.0, 20.0]):
        conn.execute(
            "INSERT INTO fee_history (ts, next_block_fee, median_fee, low_fee, mempool_size, mempool_vsize, congestion) "
            "VALUES (datetime('now', ?), ?, ?, ?, ?, ?, ?)",
            (f"-{(5-i)*5} minutes", fee, fee * 0.7, fee * 0.3, 15000, 8500000, "normal"),
        )
    conn.commit()

    with patch("bitcoin_api.routers.fees.get_cached_price", return_value=95000.0):
        resp = client.get("/api/v1/fees/savings?hours=1&currency=usd")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["btc_price_usd"] == 95000.0
    assert "avg_cost_usd" in data["always_send_now"]
    assert "best_cost_usd" in data["optimal_timing"]
    assert "usd" in data["savings_per_tx"]
    assert "total_savings_usd" in data["monthly_projection"]


def test_429_has_request_id(client):
    """Rate limit 429 responses should include request_id in error body."""
    for _ in range(settings.rate_limit_anonymous):
        client.get("/api/v1/fees/6")
    resp = client.get("/api/v1/fees/6")
    assert resp.status_code == 429
    body = resp.json()
    assert body["error"]["request_id"] is not None
    assert "X-Request-ID" in resp.headers
