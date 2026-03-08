"""Tests for mempool-related endpoints."""

from unittest.mock import patch, MagicMock


def test_mempool_info(client):
    resp = client.get("/api/v1/mempool/info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["size"] == 15000


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


def test_mempool_tx_invalid_txid(client):
    """Invalid txid on mempool entry should return 422."""
    resp = client.get("/api/v1/mempool/tx/bad-txid")
    assert resp.status_code == 422


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
    assert resp.status_code == 422  # Query validation rejects count > 100
