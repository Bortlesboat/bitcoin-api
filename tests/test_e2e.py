"""End-to-end tests against a running Satoshi API instance.

Run with: pytest tests/test_e2e.py -m e2e
Requires: API running at http://localhost:9332
"""
import pytest
import httpx

BASE_URL = "http://localhost:9332/api/v1"

pytestmark = pytest.mark.e2e


def api_available():
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


skip_if_no_api = pytest.mark.skipif(
    not api_available(), reason="API not running at localhost:9332"
)


@skip_if_no_api
def test_health():
    r = httpx.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "ok"
    assert data["chain"] in ("main", "test", "signet", "regtest")


@skip_if_no_api
def test_fees_reasonable():
    r = httpx.get(f"{BASE_URL}/fees/recommended")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "estimates" in data, "Missing estimates in fee response"
    assert len(data["estimates"]) > 0, "No fee estimates returned"
    for target, rate in data["estimates"].items():
        assert 0 <= rate <= 10000, f"Fee rate {rate} for target {target} out of range"


@skip_if_no_api
def test_block_height_above_880000():
    r = httpx.get(f"{BASE_URL}/blocks/latest")
    assert r.status_code == 200
    height = r.json()["data"]["height"]
    assert height > 880000, f"Block height {height} suspiciously low"


@skip_if_no_api
def test_genesis_block():
    r = httpx.get(f"{BASE_URL}/blocks/0")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["hash"] == "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"


@skip_if_no_api
def test_mempool_not_empty():
    r = httpx.get(f"{BASE_URL}/mempool")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["size"] > 0, "Mempool empty — node may not be connected"


@skip_if_no_api
def test_known_tx_pizza():
    """The famous 10,000 BTC pizza transaction."""
    pizza_txid = "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d"
    r = httpx.get(f"{BASE_URL}/tx/{pizza_txid}")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["txid"] == pizza_txid


@skip_if_no_api
def test_rate_limit_headers_present():
    r = httpx.get(f"{BASE_URL}/fees")
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers
    assert "X-Request-ID" in r.headers


@skip_if_no_api
def test_network_info():
    r = httpx.get(f"{BASE_URL}/network")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "connections" in data


@skip_if_no_api
def test_mining_info():
    r = httpx.get(f"{BASE_URL}/mining")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["difficulty"] > 0
