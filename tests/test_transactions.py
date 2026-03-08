"""Tests for transaction-related endpoints."""

from unittest.mock import patch, MagicMock


def test_transaction_analysis(client, mock_rpc):
    """Transaction analysis endpoint."""
    txid = "a" * 64
    with patch("bitcoin_api.routers.transactions.analyze_transaction") as mock_at:
        mock_analysis = MagicMock()
        mock_analysis.model_dump.return_value = {
            "txid": txid, "version": 2, "size": 225,
            "fee_sats": 5000, "is_segwit": True,
        }
        mock_at.return_value = mock_analysis
        resp = client.get(f"/api/v1/tx/{txid}")
        assert resp.status_code == 200
        assert resp.json()["data"]["txid"] == txid


def test_transaction_invalid_txid(client):
    """Invalid txid should return 422."""
    resp = client.get("/api/v1/tx/not-a-txid")
    assert resp.status_code == 422


def test_raw_transaction(client):
    """Raw transaction endpoint."""
    txid = "a" * 64
    resp = client.get(f"/api/v1/tx/{txid}/raw")
    assert resp.status_code == 200


def test_raw_transaction_invalid_txid(client):
    """Invalid txid on raw endpoint should return 422."""
    resp = client.get("/api/v1/tx/xyz/raw")
    assert resp.status_code == 422


def test_decode_transaction(authed_client):
    """POST /decode should decode raw tx hex."""
    resp = authed_client.post("/api/v1/decode", json={"hex": "0200000001"})
    assert resp.status_code == 200
    body = resp.json()
    assert "txid" in body["data"]


def test_decode_invalid_hex(authed_client):
    """POST /decode with non-hex should return 422."""
    resp = authed_client.post("/api/v1/decode", json={"hex": "not-hex!"})
    assert resp.status_code == 422


def test_broadcast_transaction(authed_client):
    """POST /broadcast should return txid."""
    resp = authed_client.post("/api/v1/broadcast", json={"hex": "0200000001"})
    assert resp.status_code == 200
    body = resp.json()
    assert "txid" in body["data"]


def test_broadcast_invalid_hex(authed_client):
    """POST /broadcast with non-hex should return 422."""
    resp = authed_client.post("/api/v1/broadcast", json={"hex": "not-hex!"})
    assert resp.status_code == 422


def test_tx_status(client):
    txid = "abc" * 21 + "a"
    resp = client.get(f"/api/v1/tx/{txid}/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["confirmed"] is True
    assert body["data"]["confirmations"] == 1000
    assert body["data"]["block_height"] == 879000


def test_tx_status_invalid_txid(client):
    resp = client.get("/api/v1/tx/not-a-txid/status")
    assert resp.status_code == 422


def test_tx_hex(client):
    txid = "a" * 64
    resp = client.get(f"/api/v1/tx/{txid}/hex")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], str)
    assert len(body["data"]) > 0


def test_tx_hex_invalid_txid(client):
    resp = client.get("/api/v1/tx/bad/hex")
    assert resp.status_code == 422


def test_tx_outspends(client):
    txid = "abc" * 21 + "a"
    resp = client.get(f"/api/v1/tx/{txid}/outspends")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 2  # mock has 2 vouts
    assert "spent" in body["data"][0]
    assert "vout" in body["data"][0]


def test_tx_outspends_invalid_txid(client):
    resp = client.get("/api/v1/tx/xyz/outspends")
    assert resp.status_code == 422


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

    txid = "a" * 64
    resp = client.get(f"/api/v1/utxo/{txid}/0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["in_utxo_set"] is False
    assert "note" in body["data"]

    client.app.dependency_overrides.clear()


def test_vout_negative(client):
    """Negative vout should return 422."""
    txid = "a" * 64
    resp = client.get(f"/api/v1/utxo/{txid}/-1")
    assert resp.status_code == 422


def test_broadcast_decode_failure(authed_client):
    """Malformed hex that can't be decoded should return 422."""
    from bitcoinlib_rpc.rpc import RPCError

    with patch(
        "bitcoin_api.routers.transactions.BitcoinRPC",
    ):
        mock_rpc = MagicMock()

        def side_effect(method, *args):
            if method == "decoderawtransaction":
                raise RPCError(-22, "TX decode failed")
            if method == "getblockchaininfo":
                return {"chain": "main", "blocks": 880000, "verificationprogress": 0.9999}
            return {}

        mock_rpc.call.side_effect = side_effect
        from bitcoin_api.dependencies import get_rpc
        authed_client.app.dependency_overrides[get_rpc] = lambda: mock_rpc

        resp = authed_client.post("/api/v1/broadcast", json={"hex": "deadbeef"})
        assert resp.status_code == 422
        assert "could not be decoded" in resp.json()["error"]["detail"]


def test_broadcast_already_in_mempool(authed_client):
    """RPC error -25 on broadcast should return 409."""
    from bitcoinlib_rpc.rpc import RPCError

    mock_rpc = MagicMock()

    def side_effect(method, *args):
        if method == "decoderawtransaction":
            return {"txid": "a" * 64}
        if method == "sendrawtransaction":
            raise RPCError(-25, "Transaction already in mempool")
        if method == "getblockchaininfo":
            return {"chain": "main", "blocks": 880000, "verificationprogress": 0.9999}
        return {}

    mock_rpc.call.side_effect = side_effect
    from bitcoin_api.dependencies import get_rpc
    authed_client.app.dependency_overrides[get_rpc] = lambda: mock_rpc

    resp = authed_client.post("/api/v1/broadcast", json={"hex": "0200000001"})
    assert resp.status_code == 409
    assert "already in mempool" in resp.json()["error"]["detail"].lower()


def test_broadcast_policy_rejection(authed_client):
    """RPC error -26 on broadcast should return 422."""
    from bitcoinlib_rpc.rpc import RPCError

    mock_rpc = MagicMock()

    def side_effect(method, *args):
        if method == "decoderawtransaction":
            return {"txid": "a" * 64}
        if method == "sendrawtransaction":
            raise RPCError(-26, "non-mandatory-script-verify-flag")
        if method == "getblockchaininfo":
            return {"chain": "main", "blocks": 880000, "verificationprogress": 0.9999}
        return {}

    mock_rpc.call.side_effect = side_effect
    from bitcoin_api.dependencies import get_rpc
    authed_client.app.dependency_overrides[get_rpc] = lambda: mock_rpc

    resp = authed_client.post("/api/v1/broadcast", json={"hex": "0200000001"})
    assert resp.status_code == 422
    assert "policy" in resp.json()["error"]["detail"].lower()


def test_anonymous_post_broadcast_rejected(client):
    """Anonymous users cannot broadcast transactions."""
    resp = client.post("/api/v1/broadcast", json={"hex": "0200000001"})
    assert resp.status_code == 403
    assert "API key required" in resp.json()["error"]["detail"]


def test_anonymous_post_decode_rejected(client):
    """Anonymous users cannot decode transactions."""
    resp = client.post("/api/v1/decode", json={"hex": "0200000001"})
    assert resp.status_code == 403
    assert "API key required" in resp.json()["error"]["detail"]


def test_merkle_proof(client):
    """Merkle proof returns proof hex and block hash."""
    txid = "abc" * 21 + "a"
    resp = client.get(f"/api/v1/tx/{txid}/merkle-proof")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert "proof_hex" in data
    assert "block_hash" in data


def test_merkle_proof_invalid_txid(client):
    """Merkle proof rejects invalid txid."""
    resp = client.get("/api/v1/tx/invalid/merkle-proof")
    assert resp.status_code == 422


def test_rpc_error_not_found(client, mock_rpc):
    """RPC error -5 should map to 404."""
    from bitcoinlib_rpc.rpc import RPCError

    with patch(
        "bitcoin_api.routers.transactions.analyze_transaction",
        side_effect=RPCError(-5, "Transaction not found"),
    ):
        resp = client.get("/api/v1/tx/" + "a" * 64)
        assert resp.status_code == 404
        assert resp.json()["error"]["title"] == "Not Found"


def test_error_envelope_consistency(client):
    """All error responses use the {error} envelope, never raw strings."""
    # 404
    resp = client.get("/api/v1/tx/" + "0" * 64)
    body = resp.json()
    assert "error" in body
    assert "status" in body["error"]
    assert "detail" in body["error"]

    # 422
    resp = client.get("/api/v1/tx/not-a-txid")
    body = resp.json()
    assert "error" in body
    assert "status" in body["error"]


def test_no_traceback_in_errors(client):
    """Error responses must never contain Python tracebacks."""
    resp = client.get("/api/v1/tx/ZZZZ")
    text = resp.text
    assert "Traceback" not in text
    assert ".py" not in text or "detail" in text  # .py only in structured error detail is ok


def test_post_without_content_type_json(authed_client):
    """POST with wrong content-type should be rejected."""
    resp = authed_client.post(
        "/api/v1/decode",
        content=b"not json",
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 422
