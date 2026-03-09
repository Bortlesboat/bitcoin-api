"""Tests for the RPC proxy endpoint."""


def test_proxy_getblockchaininfo(client, mock_rpc):
    mock_rpc.getblockchaininfo.return_value = {"chain": "main", "blocks": 940000}
    resp = client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 1, "method": "getblockchaininfo", "params": []
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["chain"] == "main"
    assert body["result"]["blocks"] == 940000
    assert body["id"] == 1


def test_proxy_estimatesmartfee_with_params(client, mock_rpc):
    mock_rpc.estimatesmartfee.return_value = {"feerate": 0.00012, "blocks": 6}
    resp = client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 2, "method": "estimatesmartfee", "params": [6]
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["feerate"] == 0.00012
    mock_rpc.estimatesmartfee.assert_called_once_with(6)


def test_proxy_blocks_disallowed_method(client):
    resp = client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 3, "method": "stop", "params": []
    })
    assert resp.status_code == 403
    body = resp.json()
    assert "not allowed" in body["error"]["message"]


def test_proxy_blocks_wallet_methods(client):
    for method in ["dumpprivkey", "getnewaddress", "importprivkey", "walletpassphrase"]:
        resp = client.post("/api/v1/rpc", json={
            "jsonrpc": "2.0", "id": 4, "method": method, "params": []
        })
        assert resp.status_code == 403, f"{method} should be blocked"


def test_proxy_handles_rpc_error(client, mock_rpc):
    mock_rpc.getrawtransaction.side_effect = Exception("No such mempool or blockchain transaction")
    resp = client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 5, "method": "getrawtransaction", "params": ["deadbeef"]
    })
    assert resp.status_code == 500
    body = resp.json()
    assert "No such mempool" in body["error"]["message"]


def test_proxy_sendrawtransaction_allowed(client, mock_rpc):
    """sendrawtransaction is the one write operation we allow."""
    mock_rpc.sendrawtransaction.return_value = "abc123txid"
    resp = client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 6, "method": "sendrawtransaction", "params": ["0200..."]
    })
    assert resp.status_code == 200
    assert resp.json()["result"] == "abc123txid"


def test_proxy_returns_jsonrpc_envelope(client, mock_rpc):
    mock_rpc.getblockcount.return_value = 940025
    resp = client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 99, "method": "getblockcount", "params": []
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["jsonrpc"] == "2.0"
    assert body["id"] == 99
    assert body["result"] == 940025
