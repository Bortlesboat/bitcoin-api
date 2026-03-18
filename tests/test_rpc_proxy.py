"""Tests for the RPC proxy endpoint."""


def test_proxy_requires_auth(client):
    """All RPC proxy methods now require an API key."""
    resp = client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 1, "method": "getblockchaininfo", "params": []
    })
    assert resp.status_code == 403


def test_proxy_getblockchaininfo(authed_client, mock_rpc):
    mock_rpc.getblockchaininfo.return_value = {"chain": "main", "blocks": 940000}
    resp = authed_client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 1, "method": "getblockchaininfo", "params": []
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["chain"] == "main"
    assert body["result"]["blocks"] == 940000
    assert body["id"] == 1


def test_proxy_estimatesmartfee_with_params(authed_client, mock_rpc):
    mock_rpc.estimatesmartfee.return_value = {"feerate": 0.00012, "blocks": 6}
    resp = authed_client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 2, "method": "estimatesmartfee", "params": [6]
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["feerate"] == 0.00012
    mock_rpc.estimatesmartfee.assert_called_once_with(6)


def test_proxy_blocks_disallowed_method(authed_client):
    resp = authed_client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 3, "method": "stop", "params": []
    })
    assert resp.status_code == 403
    body = resp.json()
    assert "not allowed" in body["error"]["message"]
    # Allowlist should NOT be leaked in the error message
    assert "getblockchaininfo" not in body["error"]["message"]


def test_proxy_blocks_wallet_methods(authed_client):
    for method in ["dumpprivkey", "getnewaddress", "importprivkey", "walletpassphrase"]:
        resp = authed_client.post("/api/v1/rpc", json={
            "jsonrpc": "2.0", "id": 4, "method": method, "params": []
        })
        assert resp.status_code == 403, f"{method} should be blocked"


def test_proxy_handles_rpc_error(authed_client, mock_rpc):
    """Non-RPC exceptions (no .code attr) are sanitized to a generic message."""
    mock_rpc.getrawtransaction.side_effect = Exception("No such mempool or blockchain transaction")
    resp = authed_client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 5, "method": "getrawtransaction", "params": ["deadbeef"]
    })
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["message"] == "Internal RPC error"


def test_proxy_handles_rpc_error_with_code(authed_client, mock_rpc):
    """RPC errors (with .code attr) pass through their message."""
    class RPCError(Exception):
        def __init__(self, msg, code):
            super().__init__(msg)
            self.code = code
    mock_rpc.getrawtransaction.side_effect = RPCError("No such mempool or blockchain transaction", -5)
    resp = authed_client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 5, "method": "getrawtransaction", "params": ["deadbeef"]
    })
    assert resp.status_code == 500
    body = resp.json()
    assert "No such mempool" in body["error"]["message"]
    assert body["error"]["code"] == -5


def test_proxy_sendrawtransaction_requires_auth(client, mock_rpc):
    """sendrawtransaction requires an API key (anonymous is rejected)."""
    resp = client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 6, "method": "sendrawtransaction", "params": ["0200..."]
    })
    assert resp.status_code == 403


def test_proxy_sendrawtransaction_allowed_with_auth(authed_client, mock_rpc):
    """sendrawtransaction works with a valid API key."""
    mock_rpc.sendrawtransaction.return_value = "abc123txid"
    resp = authed_client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 6, "method": "sendrawtransaction", "params": ["0200..."]
    })
    assert resp.status_code == 200
    assert resp.json()["result"] == "abc123txid"


def test_proxy_blocks_scantxoutset(authed_client):
    """scantxoutset bypasses address router semaphore — DOS risk."""
    resp = authed_client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 7, "method": "scantxoutset", "params": ["start", []]
    })
    assert resp.status_code == 403
    assert "not allowed" in resp.json()["error"]["message"]


def test_proxy_blocks_getblocktemplate(authed_client):
    """getblocktemplate is computationally expensive and not useful for API consumers."""
    resp = authed_client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 8, "method": "getblocktemplate", "params": []
    })
    assert resp.status_code == 403
    assert "not allowed" in resp.json()["error"]["message"]


def test_proxy_returns_jsonrpc_envelope(authed_client, mock_rpc):
    mock_rpc.getblockcount.return_value = 940025
    resp = authed_client.post("/api/v1/rpc", json={
        "jsonrpc": "2.0", "id": 99, "method": "getblockcount", "params": []
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["jsonrpc"] == "2.0"
    assert body["id"] == 99
    assert body["result"] == 940025
