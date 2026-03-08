"""Tests for block-related endpoints."""

from unittest.mock import patch, MagicMock


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


def test_negative_block_height(client):
    """Negative block height should return 422."""
    resp = client.get("/api/v1/blocks/-1")
    assert resp.status_code == 422


def test_negative_block_stats_height(client):
    """Negative height on stats should return 422."""
    resp = client.get("/api/v1/blocks/-1/stats")
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
    assert isinstance(body["data"], dict)
    assert "transactions" in body["data"]
    assert "total_tx_count" in body["data"]
    assert isinstance(body["data"]["transactions"], list)


def test_block_txs_invalid_hash(client):
    resp = client.get("/api/v1/blocks/xyz/txs")
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


def test_block_raw(client):
    """Raw block returns hex string."""
    block_hash = "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670"
    resp = client.get(f"/api/v1/blocks/{block_hash}/raw")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], str)


def test_block_raw_invalid_hash(client):
    """Raw block rejects invalid hash."""
    resp = client.get("/api/v1/blocks/invalid_hash/raw")
    assert resp.status_code == 422
