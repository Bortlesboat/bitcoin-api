"""Tests for bitcoin-api endpoints."""

from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Bitcoin API"
    assert "docs" in data


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["chain"] == "main"
    assert data["blocks"] == 880000


def test_status(client, mock_rpc):
    with patch("bitcoin_api.routers.status.get_status") as mock_get_status:
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
        mock_get_status.return_value = mock_status

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

    resp = client.get("/api/v1/utxo/abc123/0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["spent"] is True

    client.app.dependency_overrides.clear()


def test_rate_limit_headers(client):
    resp = client.get("/api/v1/health")
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers


def test_rate_limit_enforcement(client):
    """Anonymous tier should be limited to 30 req/min."""
    for i in range(30):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200, f"Request {i+1} failed"

    resp = client.get("/api/v1/health")
    assert resp.status_code == 429
    body = resp.json()
    assert body["error"]["status"] == 429


def test_docs_accessible(client):
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_envelope_format(client):
    with patch("bitcoin_api.routers.status.get_status") as mock_get_status:
        mock_status = MagicMock()
        mock_status.model_dump.return_value = {"chain": "main", "blocks": 880000}
        mock_get_status.return_value = mock_status

        resp = client.get("/api/v1/status")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "timestamp" in body["meta"]
