"""Tests for x402 payment analytics."""


def test_x402_stats_empty(client):
    """x402-stats returns zeros when no payments exist."""
    resp = client.get("/api/v1/x402-stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_challenges"] == 0
    assert data["total_paid"] == 0
    assert data["total_failed"] == 0
    assert data["total_revenue_usd"] == "0.00"
    assert data["conversion_rate"] == 0.0
    assert data["unique_payers"] == 0
    assert data["daily_revenue"] == []
    assert data["top_endpoints"] == []
    assert data["recent_payments"] == []


def test_x402_log_and_stats():
    """Log some payments and verify stats come back correctly."""
    from bitcoin_api.db import log_x402_payment, get_x402_stats, get_db, _hash_ip

    # Insert test data
    log_x402_payment("/api/v1/ai/explain-tx", "$0.01", "challenged", "1.2.3.4", "", "TestBot/1.0")
    log_x402_payment("/api/v1/ai/explain-tx", "$0.01", "challenged", "1.2.3.4", "", "TestBot/1.0")
    log_x402_payment("/api/v1/ai/explain-tx", "$0.01", "paid", "1.2.3.4", "x402:abc123", "TestBot/1.0")
    log_x402_payment("/api/v1/ai/explain-tx", "$0.01", "failed", "5.6.7.8", "x402:bad", "TestBot/1.0")
    log_x402_payment("/api/v1/fees", "$0.001", "challenged", "1.2.3.4", "", "AgentSDK/2.0")

    stats = get_x402_stats()
    assert stats["total_challenges"] == 3
    assert stats["total_paid"] == 1
    assert stats["total_failed"] == 1
    assert float(stats["total_revenue_usd"]) == 0.01
    assert stats["conversion_rate"] == 33.3  # 1 paid / 3 challenged
    assert stats["unique_payers"] == 1
    assert len(stats["daily_revenue"]) >= 1

    # Top endpoints — explain-tx has more challenges so it should be first
    assert len(stats["top_endpoints"]) >= 1
    top = stats["top_endpoints"][0]
    assert top["endpoint"] == "/api/v1/ai/explain-tx"
    assert top["challenges"] == 2
    assert top["paid"] == 1

    # Recent payments
    assert len(stats["recent_payments"]) == 5
    assert stats["recent_payments"][0]["status"] in ("challenged", "paid", "failed")

    # 24h stats
    assert stats["last_24h"]["challenges"] == 3
    assert stats["last_24h"]["paid"] == 1

    # Verify IP is hashed, not raw
    conn = get_db()
    row = conn.execute("SELECT client_ip_hash FROM x402_payments WHERE client_ip_hash != '' LIMIT 1").fetchone()
    assert row is not None
    assert row["client_ip_hash"] != "1.2.3.4"
    assert row["client_ip_hash"] == _hash_ip("1.2.3.4")


def test_hash_ip():
    """IP hashing works correctly."""
    from bitcoin_api.db import _hash_ip
    assert _hash_ip("") == ""
    h = _hash_ip("192.168.1.1")
    assert len(h) == 16
    assert h == _hash_ip("192.168.1.1")  # deterministic
    assert h != _hash_ip("10.0.0.1")  # different IPs


def test_x402_dashboard_served(client):
    """The /x402 page is served."""
    resp = client.get("/x402")
    assert resp.status_code == 200
    assert "x402" in resp.text.lower()
    assert "premium Bitcoin API calls" in resp.text
    assert "Recent x402 Activity" in resp.text


def test_payment_logger_injection():
    """set_payment_logger properly injects the callback."""
    from bitcoin_api_x402.middleware import set_payment_logger, _log_payment
    calls = []

    def my_logger(*args):
        calls.append(args)

    set_payment_logger(my_logger)
    _log_payment("/test", "$0.01", "challenged", "1.2.3.4", "", "TestBot")
    assert len(calls) == 1
    assert calls[0] == ("/test", "$0.01", "challenged", "1.2.3.4", "", "TestBot")

    # Cleanup
    set_payment_logger(None)


def test_payment_logger_exception_safety():
    """Logger exceptions don't propagate."""
    from bitcoin_api_x402.middleware import set_payment_logger, _log_payment

    def bad_logger(*args):
        raise RuntimeError("boom")

    set_payment_logger(bad_logger)
    # Should not raise
    _log_payment("/test", "$0.01", "challenged")

    # Cleanup
    set_payment_logger(None)
