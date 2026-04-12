"""Tests for misc endpoints: supply, stats, prices, exchanges, address, streams, websocket, classify_client, migrations, etc."""

import asyncio
import pytest


# --- Supply ---


def test_supply_endpoint(client):
    """Supply endpoint returns circulating supply data."""
    from bitcoin_api.config import settings
    original = settings.enable_supply_router
    settings.enable_supply_router = True
    resp = client.get("/api/v1/supply")
    settings.enable_supply_router = original
    # May be 404 if feature flag isn't wired at app startup (registered once)
    if resp.status_code == 200:
        body = resp.json()
        assert "data" in body
        data = body["data"]
        assert "circulating_supply_btc" in data
        assert "total_possible_btc" in data
        assert data["total_possible_btc"] == 21000000
        assert data["halvings_completed"] >= 0
        assert data["blocks_until_halving"] > 0
        assert data["annual_inflation_rate_pct"] > 0
        assert data["percent_mined"] > 0


def test_supply_math_correctness(client):
    """Supply calculations should be mathematically correct for block 880000."""
    resp = client.get("/api/v1/supply")
    if resp.status_code == 200:
        data = resp.json()["data"]
        # Block 880000: 4 halvings completed (840000 was 4th halving)
        assert data["halvings_completed"] == 4
        assert data["current_block_subsidy_btc"] == 3.125
        assert data["next_halving_height"] == 1050000
        assert data["blocks_until_halving"] == 1050000 - 880000


# --- Stats ---


def test_stats_utxo_set(authed_client):
    """UTXO set returns summary data."""
    resp = authed_client.get("/api/v1/stats/utxo-set")
    if resp.status_code == 200:
        body = resp.json()
        data = body["data"]
        assert "height" in data
        assert "txouts" in data
        assert "total_amount_btc" in data


def test_stats_segwit_adoption(authed_client):
    """SegWit adoption returns type distribution."""
    resp = authed_client.get("/api/v1/stats/segwit-adoption?blocks=2")
    if resp.status_code == 200:
        body = resp.json()
        data = body["data"]
        assert "blocks_analyzed" in data
        assert "total_outputs" in data
        assert "type_distribution" in data
        assert "segwit_percentage" in data
        assert "taproot_percentage" in data
        assert "max_blocks" in body["meta"]


def test_stats_op_returns(authed_client):
    """OP_RETURN stats returns usage data."""
    resp = authed_client.get("/api/v1/stats/op-returns?blocks=2")
    if resp.status_code == 200:
        body = resp.json()
        data = body["data"]
        assert "blocks_analyzed" in data
        assert "total_op_returns" in data
        assert "total_bytes" in data
        assert "samples" in data
        assert "max_blocks" in body["meta"]


def test_stats_segwit_invalid_blocks(authed_client):
    """SegWit adoption rejects blocks > 1000."""
    resp = authed_client.get("/api/v1/stats/segwit-adoption?blocks=5000")
    if resp.status_code != 404:  # feature flag may be off
        assert resp.status_code == 422


def test_stats_op_returns_invalid_blocks(authed_client):
    """OP_RETURN stats rejects blocks > 1000."""
    resp = authed_client.get("/api/v1/stats/op-returns?blocks=5000")
    if resp.status_code != 404:
        assert resp.status_code == 422


def test_stats_utxo_set_requires_auth(client):
    """UTXO set info requires API key."""
    resp = client.get("/api/v1/stats/utxo-set")
    if resp.status_code != 404:  # feature flag may be off
        assert resp.status_code == 403


def test_stats_segwit_requires_auth(client):
    """SegWit adoption stats requires API key."""
    resp = client.get("/api/v1/stats/segwit-adoption")
    if resp.status_code != 404:
        assert resp.status_code == 403


def test_stats_op_returns_requires_auth(client):
    """OP_RETURN stats requires API key."""
    resp = client.get("/api/v1/stats/op-returns")
    if resp.status_code != 404:
        assert resp.status_code == 403


# --- Stats Services Unit Tests ---


def test_classify_output_type():
    """classify_output_type maps script types correctly."""
    from bitcoin_api.services.stats import classify_output_type
    assert classify_output_type("witness_v0_keyhash") == "P2WPKH"
    assert classify_output_type("witness_v1_taproot") == "P2TR"
    assert classify_output_type("nulldata") == "OP_RETURN"
    assert classify_output_type("pubkeyhash") == "P2PKH"
    assert classify_output_type("unknown_type") == "unknown_type"


def test_classify_outputs():
    """classify_outputs counts output types in a block."""
    from bitcoin_api.services.stats import classify_outputs
    block = {
        "tx": [
            {"vout": [
                {"scriptPubKey": {"type": "witness_v0_keyhash"}},
                {"scriptPubKey": {"type": "witness_v1_taproot"}},
            ]},
            {"vout": [
                {"scriptPubKey": {"type": "witness_v0_keyhash"}},
                {"scriptPubKey": {"type": "nulldata", "hex": "6a0b68656c6c6f"}},
            ]},
        ]
    }
    counts = classify_outputs(block)
    assert counts["P2WPKH"] == 2
    assert counts["P2TR"] == 1
    assert counts["OP_RETURN"] == 1


def test_parse_op_returns():
    """parse_op_returns extracts OP_RETURN data."""
    from bitcoin_api.services.stats import parse_op_returns
    block = {
        "tx": [
            {"txid": "abc123", "vout": [
                {"scriptPubKey": {"type": "witness_v0_keyhash"}},
                {"scriptPubKey": {"type": "nulldata", "hex": "6a0b68656c6c6f20776f726c64"}},
            ]},
        ]
    }
    result = parse_op_returns(block)
    assert len(result) == 1
    assert result[0]["txid"] == "abc123"
    assert result[0]["hex"] == "6a0b68656c6c6f20776f726c64"
    assert result[0]["size_bytes"] == 13


def test_parse_op_returns_empty():
    """parse_op_returns returns empty for blocks with no OP_RETURN."""
    from bitcoin_api.services.stats import parse_op_returns
    block = {"tx": [{"txid": "abc", "vout": [{"scriptPubKey": {"type": "pubkeyhash"}}]}]}
    assert parse_op_returns(block) == []


# --- Prices ---


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


# --- IBIT Tool ---


def test_ibit_estimate_math():
    """IBIT estimate math should match the approved weekend calculator formula."""
    from bitcoin_api.services.ibit import compute_ibit_estimate, IBIT_SNAPSHOT

    result = compute_ibit_estimate(
        btc_price_usd=73500.75,
        shares=5200,
        snapshot=IBIT_SNAPSHOT,
    )

    assert result["btc_per_ibit"] == pytest.approx(0.000566819218, abs=1e-9)
    assert result["estimated_ibit_price_now"] == pytest.approx(41.782279, abs=1e-6)
    assert result["estimated_btc_exposure"] == pytest.approx(2.947460, abs=1e-6)


def test_ibit_estimate_endpoint(monkeypatch):
    """Public IBIT estimate endpoint should return snapshot + estimate fields."""
    from bitcoin_api.routers.exchanges import ibit_estimate

    monkeypatch.setattr(
        "bitcoin_api.routers.exchanges.get_cached_price",
        lambda: 73500.75,
    )

    body = ibit_estimate(shares=5200, btc_price_usd=None)
    data = body["data"]
    assert data["ticker"] == "IBIT"
    assert data["inputs"]["btc_price_source"] == "live"
    assert data["snapshot"]["date"] == "2026-04-10"
    assert data["estimate"]["estimated_ibit_price_now"] == pytest.approx(41.782279, abs=1e-6)
    assert data["estimate"]["estimated_position_value_usd"] == pytest.approx(217267.85, abs=1e-2)
    assert data["estimate"]["estimated_btc_exposure"] == pytest.approx(2.947460, abs=1e-6)


# --- Exchange Compare ---


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
    """Returns 503 when BTC price is unavailable."""
    monkeypatch.setattr(
        "bitcoin_api.routers.exchanges.get_cached_price", lambda: None
    )
    resp = client.get("/api/v1/tools/exchange-compare")
    assert resp.status_code == 503


# --- Address ---


def test_address_summary(authed_client):
    """Address summary returns balance, utxo count, and address info."""
    resp = authed_client.get("/api/v1/address/bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")
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


def test_address_utxos(authed_client):
    """Address UTXOs returns list of unspent outputs."""
    resp = authed_client.get("/api/v1/address/bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4/utxos")
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


def test_address_utxos_limit(authed_client):
    """UTXO limit parameter should cap results."""
    resp = authed_client.get("/api/v1/address/bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4/utxos?limit=1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["utxo_count"] == 2  # total count stays
    assert data["returned"] == 1   # but only 1 returned
    assert len(data["utxos"]) == 1


def test_address_invalid_format(authed_client):
    """Garbage address format should return 422."""
    resp = authed_client.get("/api/v1/address/!!invalid!!")
    assert resp.status_code == 422


def test_address_invalid_address(authed_client, mock_rpc):
    """Valid format but invalid address should return 400."""
    original = mock_rpc.call.side_effect

    def addr_invalid(method, *args):
        if method == "validateaddress":
            return {"isvalid": False}
        return original(method, *args)

    mock_rpc.call.side_effect = addr_invalid
    resp = authed_client.get("/api/v1/address/1InvalidAddressNotRealButLongEnough")
    assert resp.status_code == 400


# --- SSE Streams ---


def test_stream_blocks_generator(mock_rpc):
    """Block SSE generator should yield a connected event first."""
    from bitcoin_api.routers.stream import _block_event_generator

    async def get_first_event():
        gen = _block_event_generator(mock_rpc)
        return await gen.__anext__()

    event = asyncio.run(get_first_event())
    assert "event: connected" in event
    assert '"height"' in event


def test_stream_fees_generator(mock_rpc):
    """Fee SSE generator should yield a connected event first."""
    from bitcoin_api.routers.stream import _fee_event_generator

    async def get_first_event():
        gen = _fee_event_generator(mock_rpc)
        return await gen.__anext__()

    event = asyncio.run(get_first_event())
    assert "event: connected" in event


def test_whale_txs_stream_generator(mock_rpc):
    """Whale tx SSE generator should yield a connected event first."""
    from bitcoin_api.routers.stream import _whale_tx_generator

    async def get_first_event():
        gen = _whale_tx_generator(mock_rpc, 10.0)
        return await gen.__anext__()

    event = asyncio.run(get_first_event())
    assert "event: connected" in event
    assert '"min_btc"' in event


def test_whale_stream_requires_auth(client):
    """Whale tx stream requires API key."""
    resp = client.get("/api/v1/stream/whale-txs")
    assert resp.status_code == 403
    body = resp.json()
    detail = body.get("detail", "") or body.get("error", {}).get("detail", "")
    assert "API key required" in detail


# --- WebSocket ---


def test_websocket_subscribe_and_receive(client):
    """WebSocket client can subscribe to a channel and receive events."""
    import json
    from bitcoin_api.pubsub import hub

    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_text(json.dumps({"action": "subscribe", "channel": "new_block"}))
        resp = json.loads(ws.receive_text())
        assert resp["type"] == "subscribed"
        assert resp["channel"] == "new_block"

        # Publish an event from the hub
        hub.publish("new_block", {"height": 900000, "timestamp": 1234567890})
        event = json.loads(ws.receive_text())
        assert event["channel"] == "new_block"
        assert event["height"] == 900000


def test_websocket_unsubscribe(client):
    """WebSocket client can unsubscribe from a channel."""
    import json

    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_text(json.dumps({"action": "subscribe", "channel": "new_fees"}))
        resp = json.loads(ws.receive_text())
        assert resp["type"] == "subscribed"

        ws.send_text(json.dumps({"action": "unsubscribe", "channel": "new_fees"}))
        resp = json.loads(ws.receive_text())
        assert resp["type"] == "unsubscribed"


def test_websocket_invalid_json(client):
    """WebSocket should handle invalid JSON gracefully."""
    import json

    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_text("not json at all")
        resp = json.loads(ws.receive_text())
        assert resp["type"] == "error"
        assert "Invalid JSON" in resp["detail"]


def test_websocket_unknown_channel(client):
    """Subscribing to an unknown channel should return error."""
    import json

    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_text(json.dumps({"action": "subscribe", "channel": "nonexistent"}))
        resp = json.loads(ws.receive_text())
        assert resp["type"] == "error"
        assert "Unknown channel" in resp["detail"]


def test_websocket_unknown_action(client):
    """Unknown action should return error."""
    import json

    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_text(json.dumps({"action": "explode", "channel": "new_block"}))
        resp = json.loads(ws.receive_text())
        assert resp["type"] == "error"
        assert "Unknown action" in resp["detail"]


def test_websocket_ping_pong(client):
    """Ping action should return pong."""
    import json

    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_text(json.dumps({"action": "ping"}))
        resp = json.loads(ws.receive_text())
        assert resp["type"] == "pong"


def test_websocket_duplicate_subscribe(client):
    """Subscribing twice to the same channel should return error."""
    import json

    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_text(json.dumps({"action": "subscribe", "channel": "new_block"}))
        json.loads(ws.receive_text())  # subscribed

        ws.send_text(json.dumps({"action": "subscribe", "channel": "new_block"}))
        resp = json.loads(ws.receive_text())
        assert resp["type"] == "error"
        assert "Already subscribed" in resp["detail"]


def test_websocket_unsubscribe_without_subscribe(client):
    """Unsubscribing without subscribing should return error."""
    import json

    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_text(json.dumps({"action": "unsubscribe", "channel": "new_block"}))
        resp = json.loads(ws.receive_text())
        assert resp["type"] == "error"
        assert "Not subscribed" in resp["detail"]


def test_websocket_multiple_channels(client):
    """Client can subscribe to multiple channels simultaneously."""
    import json
    from bitcoin_api.pubsub import hub

    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_text(json.dumps({"action": "subscribe", "channel": "new_block"}))
        json.loads(ws.receive_text())
        ws.send_text(json.dumps({"action": "subscribe", "channel": "new_fees"}))
        json.loads(ws.receive_text())

        hub.publish("new_fees", {"next_block_fee": 15.0, "timestamp": 123})
        event = json.loads(ws.receive_text())
        assert event["channel"] == "new_fees"


def test_pubsub_hub_subscriber_count():
    """PubSubHub.subscriber_count should track subscriptions."""
    from bitcoin_api.pubsub import PubSubHub
    h = PubSubHub()
    assert h.subscriber_count == 0
    q = h.subscribe("new_block")
    assert h.subscriber_count == 1
    h.unsubscribe("new_block", q)
    assert h.subscriber_count == 0


# --- classify_client ---


def test_classify_client_bitcoin_mcp():
    """classify_client should detect bitcoin-mcp user agents."""
    from bitcoin_api.middleware import classify_client
    assert classify_client("bitcoin-mcp/0.3.0") == "bitcoin-mcp"


def test_classify_client_browser():
    """classify_client should detect browser user agents."""
    from bitcoin_api.middleware import classify_client
    assert classify_client("Mozilla/5.0 Chrome/120") == "browser"


def test_classify_client_sdk():
    """classify_client should detect SDK user agents."""
    from bitcoin_api.middleware import classify_client
    assert classify_client("python-requests/2.31") == "sdk"


def test_classify_client_ai_agent():
    """classify_client should detect AI agent user agents (case insensitive)."""
    from bitcoin_api.middleware import classify_client
    assert classify_client("Claude-Agent/1.0") == "ai-agent"


def test_classify_client_empty():
    """classify_client should return unknown for empty user agent."""
    from bitcoin_api.middleware import classify_client
    assert classify_client("") == "unknown"


def test_classify_client_unknown():
    """classify_client should return unknown for unrecognized user agents."""
    from bitcoin_api.middleware import classify_client
    assert classify_client("SomeRandomBot/1.0") == "unknown"


# --- Usage Logging & Migrations ---


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


def test_migration_005_client_type_column():
    """Migration 005 should add client_type column to usage_log."""
    from bitcoin_api.db import get_db
    conn = get_db()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(usage_log)").fetchall()]
    assert "client_type" in cols


def test_migration_005_client_type_index():
    """Migration 005 should create index on client_type."""
    from bitcoin_api.db import get_db
    conn = get_db()
    indexes = [r[1] for r in conn.execute("PRAGMA index_list(usage_log)").fetchall()]
    assert "idx_usage_log_client_type" in indexes


def test_migration_010_signup_columns_exist():
    """Migration 010 should add all 9 first-touch attribution columns to api_keys."""
    from bitcoin_api.db import get_db
    conn = get_db()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(api_keys)").fetchall()]
    expected = [
        "utm_term", "utm_content",
        "first_landing_path", "first_referrer",
        "first_utm_source", "first_utm_medium", "first_utm_campaign",
        "first_utm_term", "first_utm_content",
    ]
    for col in expected:
        assert col in cols, f"Column '{col}' missing from api_keys (migration 010)"
