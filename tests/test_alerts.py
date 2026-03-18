"""Tests for alert webhook endpoints (/api/v1/alerts/*)."""


def test_create_fee_alert(authed_client):
    """Create a fee alert with valid data."""
    resp = authed_client.post("/api/v1/alerts/fees", json={
        "webhook_url": "https://example.com/webhook",
        "threshold_sat_vb": 5.0,
        "condition": "below",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["threshold_sat_vb"] == 5.0
    assert data["condition"] == "below"
    assert data["active"] is True
    assert "id" in data


def test_create_fee_alert_above(authed_client):
    """Create an 'above' condition alert."""
    resp = authed_client.post("/api/v1/alerts/fees", json={
        "webhook_url": "https://example.com/webhook",
        "threshold_sat_vb": 50.0,
        "condition": "above",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["condition"] == "above"


def test_list_fee_alerts(authed_client):
    """List alerts returns created alerts."""
    authed_client.post("/api/v1/alerts/fees", json={
        "webhook_url": "https://example.com/webhook",
        "threshold_sat_vb": 5.0,
    })
    resp = authed_client.get("/api/v1/alerts/fees")
    assert resp.status_code == 200
    alerts = resp.json()["data"]
    assert len(alerts) >= 1
    assert alerts[0]["threshold_sat_vb"] == 5.0


def test_delete_fee_alert(authed_client):
    """Delete (deactivate) a fee alert."""
    create_resp = authed_client.post("/api/v1/alerts/fees", json={
        "webhook_url": "https://example.com/webhook",
        "threshold_sat_vb": 5.0,
    })
    alert_id = create_resp.json()["data"]["id"]

    resp = authed_client.delete(f"/api/v1/alerts/fees/{alert_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["active"] is False


def test_delete_nonexistent_alert(authed_client):
    """Deleting a non-existent alert returns 404."""
    resp = authed_client.delete("/api/v1/alerts/fees/99999")
    assert resp.status_code == 404


def test_fee_alert_requires_auth(client):
    """Fee alerts require an API key."""
    resp = client.post("/api/v1/alerts/fees", json={
        "webhook_url": "https://example.com/webhook",
        "threshold_sat_vb": 5.0,
    })
    assert resp.status_code == 403


def test_fee_alert_limit(authed_client):
    """Max 10 active fee alerts per key."""
    for i in range(10):
        resp = authed_client.post("/api/v1/alerts/fees", json={
            "webhook_url": f"https://example.com/webhook{i}",
            "threshold_sat_vb": float(i + 1),
        })
        assert resp.status_code == 200

    # 11th should fail
    resp = authed_client.post("/api/v1/alerts/fees", json={
        "webhook_url": "https://example.com/webhook-overflow",
        "threshold_sat_vb": 11.0,
    })
    assert resp.status_code == 429


def test_create_tx_watch(authed_client):
    """Create a transaction watch."""
    txid = "a" * 64
    resp = authed_client.post(f"/api/v1/alerts/tx/watch/{txid}", json={
        "webhook_url": "https://example.com/tx-webhook",
        "target_confirmations": 3,
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["txid"] == txid
    assert data["target_confirmations"] == 3
    assert data["active"] is True


def test_list_tx_watches(authed_client):
    """List transaction watches."""
    txid = "b" * 64
    authed_client.post(f"/api/v1/alerts/tx/watch/{txid}", json={
        "webhook_url": "https://example.com/tx-webhook",
    })
    resp = authed_client.get("/api/v1/alerts/tx")
    assert resp.status_code == 200
    watches = resp.json()["data"]
    assert len(watches) >= 1


def test_delete_tx_watch(authed_client):
    """Delete (deactivate) a transaction watch."""
    txid = "c" * 64
    create_resp = authed_client.post(f"/api/v1/alerts/tx/watch/{txid}", json={
        "webhook_url": "https://example.com/tx-webhook",
    })
    watch_id = create_resp.json()["data"]["id"]

    resp = authed_client.delete(f"/api/v1/alerts/tx/{watch_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["active"] is False


def test_tx_watch_invalid_txid(authed_client):
    """Invalid txid returns 422."""
    resp = authed_client.post("/api/v1/alerts/tx/watch/not-a-txid", json={
        "webhook_url": "https://example.com/tx-webhook",
    })
    assert resp.status_code == 422


def test_tx_watch_requires_auth(client):
    """Transaction watches require an API key."""
    txid = "d" * 64
    resp = client.post(f"/api/v1/alerts/tx/watch/{txid}", json={
        "webhook_url": "https://example.com/tx-webhook",
    })
    assert resp.status_code == 403


def test_ssrf_rejects_localhost(authed_client):
    """Webhook URL pointing to localhost should be rejected."""
    resp = authed_client.post("/api/v1/alerts/fees", json={
        "webhook_url": "http://127.0.0.1:8332/",
        "threshold_sat_vb": 5.0,
    })
    assert resp.status_code == 422
    assert "private" in resp.json()["error"]["detail"].lower() or "internal" in resp.json()["error"]["detail"].lower()


def test_ssrf_rejects_private_ip(authed_client):
    """Webhook URL pointing to a private IP should be rejected."""
    resp = authed_client.post("/api/v1/alerts/fees", json={
        "webhook_url": "http://10.0.0.1/webhook",
        "threshold_sat_vb": 5.0,
    })
    assert resp.status_code == 422


def test_ssrf_rejects_metadata_ip(authed_client):
    """Webhook URL pointing to AWS metadata endpoint should be rejected."""
    resp = authed_client.post("/api/v1/alerts/fees", json={
        "webhook_url": "http://169.254.169.254/latest/meta-data/",
        "threshold_sat_vb": 5.0,
    })
    assert resp.status_code == 422
