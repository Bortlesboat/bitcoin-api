"""Tests for Stripe billing endpoints."""

from unittest.mock import patch
from pydantic import SecretStr


def test_billing_checkout_503_when_not_configured(authed_client):
    """Billing checkout should return 503 when Stripe is not configured."""
    resp = authed_client.post("/api/v1/billing/checkout")
    assert resp.status_code == 503
    body = resp.json()
    detail = body.get("detail", "") or body.get("error", {}).get("detail", "")
    assert "not configured" in detail.lower()


def test_billing_status_503_when_not_configured(authed_client):
    """Billing status should return 503 when Stripe is not configured."""
    resp = authed_client.get("/api/v1/billing/status")
    assert resp.status_code == 503


def test_billing_cancel_503_when_not_configured(authed_client):
    """Billing cancel should return 503 when Stripe is not configured."""
    resp = authed_client.post("/api/v1/billing/cancel")
    assert resp.status_code == 503


def test_billing_checkout_requires_auth(client):
    """Billing checkout should reject anonymous users."""
    from bitcoin_api.config import settings
    original = settings.stripe_secret_key
    original_price = settings.stripe_price_id
    settings.stripe_secret_key = SecretStr("test_stripe_key_fake")
    settings.stripe_price_id = "price_test_fake"
    try:
        resp = client.post("/api/v1/billing/checkout")
        assert resp.status_code == 401
    finally:
        settings.stripe_secret_key = original
        settings.stripe_price_id = original_price


def test_billing_status_requires_auth(client):
    """Billing status should reject anonymous users."""
    from bitcoin_api.config import settings
    original = settings.stripe_secret_key
    original_price = settings.stripe_price_id
    settings.stripe_secret_key = SecretStr("test_stripe_key_fake")
    settings.stripe_price_id = "price_test_fake"
    try:
        resp = client.get("/api/v1/billing/status")
        assert resp.status_code == 401
    finally:
        settings.stripe_secret_key = original
        settings.stripe_price_id = original_price


def test_billing_status_no_subscription(authed_client):
    """Billing status should return none when no subscription exists."""
    from bitcoin_api.config import settings
    original = settings.stripe_secret_key
    original_price = settings.stripe_price_id
    settings.stripe_secret_key = SecretStr("test_stripe_key_fake")
    settings.stripe_price_id = "price_test_fake"
    try:
        resp = authed_client.get("/api/v1/billing/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "none"
        assert data["subscription_id"] is None
    finally:
        settings.stripe_secret_key = original
        settings.stripe_price_id = original_price


def test_billing_webhook_rejects_bad_signature(authed_client):
    """Billing webhook should reject requests with invalid signature."""
    from bitcoin_api.config import settings
    original_key = settings.stripe_secret_key
    original_secret = settings.stripe_webhook_secret
    original_price = settings.stripe_price_id
    settings.stripe_secret_key = SecretStr("test_stripe_key_fake")
    settings.stripe_webhook_secret = SecretStr("test_webhook_secret_fake")
    settings.stripe_price_id = "price_test_fake"
    try:
        resp = authed_client.post(
            "/api/v1/billing/webhook",
            content=b'{"type": "checkout.session.completed"}',
            headers={"stripe-signature": "t=123,v1=bad_sig"},
        )
        assert resp.status_code == 400
    finally:
        settings.stripe_secret_key = original_key
        settings.stripe_webhook_secret = original_secret
        settings.stripe_price_id = original_price


def test_billing_webhook_checkout_completed(authed_client):
    """Webhook checkout.session.completed should upgrade tier to pro."""
    import hashlib
    from bitcoin_api.config import settings
    from bitcoin_api.db import get_db

    original_key = settings.stripe_secret_key
    original_secret = settings.stripe_webhook_secret
    original_price = settings.stripe_price_id
    settings.stripe_secret_key = SecretStr("test_stripe_key_fake")
    settings.stripe_webhook_secret = SecretStr("test_webhook_secret_fake")
    settings.stripe_price_id = "price_test_fake"

    # Get the key hash from the authed_client
    key_hash = hashlib.sha256("test-authed-key-fixture".encode()).hexdigest()

    # Ensure subscriptions table exists
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key_hash TEXT NOT NULL,
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT UNIQUE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    # Add stripe_customer_id column if not exists
    try:
        db.execute("ALTER TABLE api_keys ADD COLUMN stripe_customer_id TEXT")
    except Exception:
        pass
    db.commit()

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"api_key_hash": key_hash},
                "customer": "cus_test123",
                "subscription": "sub_test456",
            }
        }
    }

    with patch("bitcoin_api.routers.billing.verify_webhook_signature", return_value=event):
        resp = authed_client.post(
            "/api/v1/billing/webhook",
            content=b'{}',
            headers={"stripe-signature": "t=123,v1=test"},
        )
    assert resp.status_code == 200

    # Verify tier was upgraded
    row = db.execute("SELECT tier FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
    assert row[0] == "pro"

    # Verify subscription was created
    sub = db.execute("SELECT status FROM subscriptions WHERE api_key_hash = ?", (key_hash,)).fetchone()
    assert sub[0] == "active"

    settings.stripe_secret_key = original_key
    settings.stripe_webhook_secret = original_secret
    settings.stripe_price_id = original_price


def test_billing_webhook_subscription_canceled(authed_client):
    """Webhook customer.subscription.deleted should downgrade tier to free."""
    import hashlib
    from bitcoin_api.config import settings
    from bitcoin_api.db import get_db

    original_key = settings.stripe_secret_key
    original_secret = settings.stripe_webhook_secret
    original_price = settings.stripe_price_id
    settings.stripe_secret_key = SecretStr("test_stripe_key_fake")
    settings.stripe_webhook_secret = SecretStr("test_webhook_secret_fake")
    settings.stripe_price_id = "price_test_fake"

    key_hash = hashlib.sha256("test-authed-key-fixture".encode()).hexdigest()

    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key_hash TEXT NOT NULL,
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT UNIQUE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    try:
        db.execute("ALTER TABLE api_keys ADD COLUMN stripe_customer_id TEXT")
    except Exception:
        pass
    # Seed a pro subscription
    db.execute("UPDATE api_keys SET tier = 'pro' WHERE key_hash = ?", (key_hash,))
    db.execute(
        "INSERT OR REPLACE INTO subscriptions (api_key_hash, stripe_customer_id, stripe_subscription_id, status) VALUES (?, 'cus_test', 'sub_cancel_test', 'active')",
        (key_hash,),
    )
    db.commit()

    event = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_cancel_test",
                "status": "canceled",
            }
        }
    }

    with patch("bitcoin_api.routers.billing.verify_webhook_signature", return_value=event):
        resp = authed_client.post(
            "/api/v1/billing/webhook",
            content=b'{}',
            headers={"stripe-signature": "t=123,v1=test"},
        )
    assert resp.status_code == 200

    row = db.execute("SELECT tier FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
    assert row[0] == "free"

    sub = db.execute("SELECT status FROM subscriptions WHERE stripe_subscription_id = 'sub_cancel_test'").fetchone()
    assert sub[0] == "canceled"

    settings.stripe_secret_key = original_key
    settings.stripe_webhook_secret = original_secret
    settings.stripe_price_id = original_price


def test_billing_cancel_no_subscription(authed_client):
    """Cancel should return 404 when no active subscription."""
    from bitcoin_api.config import settings
    from bitcoin_api.db import get_db

    original = settings.stripe_secret_key
    original_price = settings.stripe_price_id
    settings.stripe_secret_key = SecretStr("test_stripe_key_fake")
    settings.stripe_price_id = "price_test_fake"

    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key_hash TEXT NOT NULL,
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT UNIQUE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    db.commit()

    try:
        resp = authed_client.post("/api/v1/billing/cancel")
        assert resp.status_code == 404
    finally:
        settings.stripe_secret_key = original
        settings.stripe_price_id = original_price


def test_billing_webhook_no_rate_limit(client):
    """Billing webhook should not be rate limited."""
    for _ in range(35):
        resp = client.post("/api/v1/billing/webhook")
        # Will get 503 (not configured) but never 429
        assert resp.status_code != 429


def test_billing_checkout_no_price_id(authed_client):
    """Checkout returns 503 when stripe_price_id is empty."""
    from bitcoin_api.config import settings
    original_key = settings.stripe_secret_key
    original_price = settings.stripe_price_id
    settings.stripe_secret_key = SecretStr("test_stripe_key_fake")
    settings.stripe_price_id = ""
    try:
        resp = authed_client.post("/api/v1/billing/checkout")
        assert resp.status_code == 503
        body = resp.json()
        detail = body.get("detail", "") or body.get("error", {}).get("detail", "")
        assert "price ID" in detail
    finally:
        settings.stripe_secret_key = original_key
        settings.stripe_price_id = original_price
