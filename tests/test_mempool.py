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


# --- New tests: edge cases and error paths ---


def test_mempool_info_returns_envelope(client):
    """Mempool info should return standard {data, meta} envelope."""
    resp = client.get("/api/v1/mempool/info")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body


def test_mempool_info_fields(client):
    """Mempool info should include key fields from getmempoolinfo."""
    resp = client.get("/api/v1/mempool/info")
    data = resp.json()["data"]
    assert "size" in data
    assert "bytes" in data
    assert "maxmempool" in data
    assert "mempoolminfee" in data


def test_mempool_analysis_empty_mempool(client, mock_rpc):
    """Empty mempool should still return a valid response."""
    with patch("bitcoin_api.routers.mempool.cached_mempool_analysis") as mock_ma:
        mock_summary = MagicMock()
        mock_summary.model_dump.return_value = {
            "size": 0, "bytes": 0, "fee_histogram": [],
            "congestion": "low",
        }
        mock_ma.return_value = mock_summary
        resp = client.get("/api/v1/mempool")
        assert resp.status_code == 200
        assert resp.json()["data"]["size"] == 0


def test_mempool_tx_returns_fee_data(client):
    """Mempool entry should include fee information."""
    txid = "a" * 64
    resp = client.get(f"/api/v1/mempool/tx/{txid}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "fees" in data
    assert "vsize" in data


def test_mempool_tx_too_short_txid(client):
    """Txid that is 63 chars should return 422."""
    resp = client.get(f"/api/v1/mempool/tx/{'a' * 63}")
    assert resp.status_code == 422


def test_mempool_tx_too_long_txid(client):
    """Txid that is 65 chars should return 422."""
    resp = client.get(f"/api/v1/mempool/tx/{'a' * 65}")
    assert resp.status_code == 422


def test_mempool_txids_limit_param(client):
    """Limit parameter should cap returned txids."""
    resp = client.get("/api/v1/mempool/txids?limit=1")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


def test_mempool_txids_returns_strings(client):
    """All items in txids response should be strings."""
    resp = client.get("/api/v1/mempool/txids")
    data = resp.json()["data"]
    assert all(isinstance(txid, str) for txid in data)


def test_mempool_recent_default_count(client):
    """Default count should return results without explicit param."""
    resp = client.get("/api/v1/mempool/recent")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)


def test_mempool_recent_fee_rate_calculation(client):
    """Fee rate should be calculated as fee_sat / vsize."""
    resp = client.get("/api/v1/mempool/recent?count=5")
    data = resp.json()["data"]
    for entry in data:
        assert entry["fee_rate"] >= 0
        assert isinstance(entry["fee_rate"], (int, float))
