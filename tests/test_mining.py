"""Tests for mining-related endpoints and services."""


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


def test_mining_hashrate_history(authed_client):
    """Hashrate history returns list of data points."""
    resp = authed_client.get("/api/v1/mining/hashrate/history?blocks=3")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert isinstance(data, list)
    if data:
        assert "height" in data[0]
        assert "hashrate_eh_s" in data[0]
        assert "difficulty" in data[0]


def test_mining_hashrate_history_default(authed_client):
    """Hashrate history works with default blocks param."""
    resp = authed_client.get("/api/v1/mining/hashrate/history")
    assert resp.status_code == 200


def test_mining_revenue(authed_client):
    """Mining revenue returns fee/subsidy breakdown."""
    resp = authed_client.get("/api/v1/mining/revenue?blocks=3")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert "blocks_analyzed" in data
    assert "total_subsidy_btc" in data
    assert "total_fees_btc" in data
    assert "total_revenue_btc" in data
    assert "fee_percentage" in data
    assert data["blocks_analyzed"] == 3
    assert "max_blocks" in body["meta"]


def test_mining_pools(authed_client):
    """Mining pools returns pool identification data."""
    resp = authed_client.get("/api/v1/mining/pools?blocks=3")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert "blocks_analyzed" in data
    assert "pools" in data
    assert isinstance(data["pools"], list)
    assert "unknown_count" in data
    assert "max_blocks" in body["meta"]


def test_mining_difficulty_history(client):
    """Difficulty history returns epoch data."""
    resp = client.get("/api/v1/mining/difficulty/history?epochs=3")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert isinstance(data, list)
    if data:
        assert "epoch" in data[0]
        assert "height" in data[0]
        assert "difficulty" in data[0]


def test_mining_revenue_history(authed_client):
    """Revenue history returns per-block data."""
    resp = authed_client.get("/api/v1/mining/revenue/history?blocks=3")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert isinstance(data, list)
    if data:
        assert "height" in data[0]
        assert "subsidy_btc" in data[0]
        assert "fees_btc" in data[0]
        assert "total_btc" in data[0]
    assert "max_blocks" in body["meta"]


def test_mining_hashrate_invalid_blocks(client):
    """Hashrate history rejects blocks > 2016."""
    resp = client.get("/api/v1/mining/hashrate/history?blocks=5000")
    assert resp.status_code == 422


def test_mining_revenue_invalid_blocks(client):
    """Mining revenue rejects blocks > 2016."""
    resp = client.get("/api/v1/mining/revenue?blocks=5000")
    assert resp.status_code == 422


def test_mining_pools_invalid_blocks(client):
    """Mining pools rejects blocks > 2016."""
    resp = client.get("/api/v1/mining/pools?blocks=5000")
    assert resp.status_code == 422


def test_mining_difficulty_invalid_epochs(client):
    """Difficulty history rejects epochs > 50."""
    resp = client.get("/api/v1/mining/difficulty/history?epochs=100")
    assert resp.status_code == 422


def test_mining_pools_requires_auth(client):
    """Mining pools requires API key."""
    resp = client.get("/api/v1/mining/pools")
    assert resp.status_code == 403


def test_mining_revenue_requires_auth(client):
    """Mining revenue requires API key."""
    resp = client.get("/api/v1/mining/revenue")
    assert resp.status_code == 403


def test_mining_revenue_history_requires_auth(client):
    """Mining revenue history requires API key."""
    resp = client.get("/api/v1/mining/revenue/history")
    assert resp.status_code == 403


def test_mining_hashrate_anonymous_rejected(client):
    """Anonymous hashrate history is rejected (requires API key)."""
    resp = client.get("/api/v1/mining/hashrate/history?blocks=500")
    assert resp.status_code == 403


# --- Mining Services Unit Tests ---


def test_parse_coinbase_tag_foundry():
    """parse_coinbase_tag identifies Foundry from coinbase hex."""
    from bitcoin_api.services.mining import parse_coinbase_tag
    # "Foundry USA Pool" as hex
    hex_str = "466f756e64727920555341".lower()
    # Pad it to make it look like a real coinbase
    result = parse_coinbase_tag("03a0d60d" + hex_str)
    assert result != "Unknown"


def test_parse_coinbase_tag_unknown():
    """parse_coinbase_tag returns Unknown for unrecognized data."""
    from bitcoin_api.services.mining import parse_coinbase_tag
    result = parse_coinbase_tag("deadbeef")
    assert result == "Unknown"


def test_extract_coinbase_hex():
    """extract_coinbase_hex pulls coinbase from block data."""
    from bitcoin_api.services.mining import extract_coinbase_hex
    block = {"tx": [{"vin": [{"coinbase": "03a0d60d2f466f756e6472792f"}]}]}
    result = extract_coinbase_hex(block)
    assert result == "03a0d60d2f466f756e6472792f"


def test_extract_coinbase_hex_empty():
    """extract_coinbase_hex handles empty block."""
    from bitcoin_api.services.mining import extract_coinbase_hex
    assert extract_coinbase_hex({}) == ""
    assert extract_coinbase_hex({"tx": []}) == ""


def test_calculate_hashrate():
    """calculate_hashrate computes from difficulty."""
    from bitcoin_api.services.mining import calculate_hashrate
    result = calculate_hashrate(110_000_000_000_000)
    assert result > 0
    # hashrate = difficulty * 2^32 / 600
    expected = 110_000_000_000_000 * (2 ** 32) / 600
    assert abs(result - expected) < 1
