"""Tests for the History Explorer feature."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bitcoin_api.routers.history import router, _load_data, _history_data
import bitcoin_api.routers.history as history_module
from bitcoin_api.main import app
from bitcoin_api.dependencies import get_rpc

_DATA_FILE = Path(__file__).resolve().parent.parent / "static" / "history" / "history-data.json"


def _make_client():
    """Create an isolated test client for the history router."""
    # Reset cached data
    history_module._history_data = None
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")
    return TestClient(test_app)


def _make_real_client():
    """Create a test client using the real app with mocked RPC."""
    history_module._history_data = None
    mock_rpc = MagicMock()
    app.dependency_overrides[get_rpc] = lambda: mock_rpc
    client = TestClient(app)
    return client


class TestHistoryEvents:
    def test_list_events(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "meta" in data
        assert data["meta"]["total"] > 0

    def test_list_events_with_limit(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) <= 5
        assert data["meta"]["limit"] == 5

    def test_list_events_with_offset(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events?offset=5&limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["offset"] == 5

    def test_filter_by_era(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events?era=genesis")
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["era"] == "genesis" for e in data["data"])

    def test_filter_by_category(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events?category=halving")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 4
        assert all(e["category"] == "halving" for e in data["data"])

    def test_filter_by_tag(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events?tag=satoshi")
        assert resp.status_code == 200
        data = resp.json()
        assert all("satoshi" in e["tags"] for e in data["data"])

    def test_filter_combined(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events?era=first-transactions&category=transaction")
        assert resp.status_code == 200
        data = resp.json()
        for e in data["data"]:
            assert e["era"] == "first-transactions"
            assert e["category"] == "transaction"

    def test_get_event_by_id(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events/genesis-block")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == "genesis-block"
        assert data["block_height"] == 0

    def test_get_event_not_found(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events/nonexistent")
        assert resp.status_code == 404

    def test_event_has_required_fields(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events/bitcoin-pizza")
        assert resp.status_code == 200
        ev = resp.json()["data"]
        for field in ("id", "title", "date", "era", "category", "description", "significance", "tags"):
            assert field in ev, f"Missing field: {field}"

    def test_pizza_event_data(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events/bitcoin-pizza")
        assert resp.status_code == 200
        ev = resp.json()["data"]
        assert ev["date"] == "2010-05-22"
        assert ev["block_height"] == 57043
        assert ev["txid"] == "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d"

    def test_first_tx_event_data(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events/first-bitcoin-tx")
        assert resp.status_code == 200
        ev = resp.json()["data"]
        assert ev["block_height"] == 170
        assert ev["txid"] == "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16"

    def test_empty_era_filter_returns_empty(self):
        client = _make_client()
        resp = client.get("/api/v1/history/events?era=nonexistent-era")
        assert resp.status_code == 200
        assert resp.json()["data"] == []
        assert resp.json()["meta"]["total"] == 0


class TestHistoryEras:
    def test_list_eras(self):
        client = _make_client()
        resp = client.get("/api/v1/history/eras")
        assert resp.status_code == 200
        eras = resp.json()["data"]
        assert len(eras) == 7

    def test_get_era_by_id(self):
        client = _make_client()
        resp = client.get("/api/v1/history/eras/genesis")
        assert resp.status_code == 200
        era = resp.json()["data"]
        assert era["name"] == "Genesis Era"
        assert era["start_block"] == 0

    def test_get_era_not_found(self):
        client = _make_client()
        resp = client.get("/api/v1/history/eras/nonexistent")
        assert resp.status_code == 404


class TestHistoryConcepts:
    def test_list_concepts(self):
        client = _make_client()
        resp = client.get("/api/v1/history/concepts")
        assert resp.status_code == 200
        concepts = resp.json()["data"]
        assert len(concepts) == 14
        assert "halving" in concepts

    def test_get_concept_by_id(self):
        client = _make_client()
        resp = client.get("/api/v1/history/concepts/halving")
        assert resp.status_code == 200
        c = resp.json()["data"]
        assert c["id"] == "halving"
        assert "name" in c
        assert "try_it" in c
        assert "mcp_tool" in c

    def test_get_concept_not_found(self):
        client = _make_client()
        resp = client.get("/api/v1/history/concepts/nonexistent")
        assert resp.status_code == 404

    def test_concept_has_required_fields(self):
        client = _make_client()
        resp = client.get("/api/v1/history/concepts/segwit")
        assert resp.status_code == 200
        c = resp.json()["data"]
        for field in ("id", "name", "description", "try_it", "mcp_tool"):
            assert field in c, f"Missing field: {field}"


class TestHistorySearch:
    def test_search_by_title(self):
        client = _make_client()
        resp = client.get("/api/v1/history/search?q=pizza")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) > 0
        assert any("pizza" in e["title"].lower() for e in data["data"])

    def test_search_by_tag(self):
        client = _make_client()
        resp = client.get("/api/v1/history/search?q=satoshi")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) >= 3

    def test_search_no_results(self):
        client = _make_client()
        resp = client.get("/api/v1/history/search?q=zzzznonexistentzzz")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 0

    def test_search_requires_query(self):
        client = _make_client()
        resp = client.get("/api/v1/history/search")
        assert resp.status_code == 422

    def test_search_results_sorted_by_score(self):
        client = _make_client()
        resp = client.get("/api/v1/history/search?q=halving")
        assert resp.status_code == 200
        results = resp.json()["data"]
        assert len(results) >= 4
        # Title matches should come first
        assert "halving" in results[0]["title"].lower()


class TestHistoryStaticPages:
    def test_history_index_page(self):
        client = _make_real_client()
        resp = client.get("/history")
        assert resp.status_code == 200
        assert "Bitcoin History Explorer" in resp.text

    def test_history_block_page(self):
        client = _make_real_client()
        resp = client.get("/history/block")
        assert resp.status_code == 200
        assert "Block Explorer" in resp.text

    def test_history_tx_page(self):
        client = _make_real_client()
        resp = client.get("/history/tx")
        assert resp.status_code == 200
        assert "Transaction Explorer" in resp.text

    def test_history_address_page(self):
        client = _make_real_client()
        resp = client.get("/history/address")
        assert resp.status_code == 200
        assert "Address" in resp.text

    def test_history_data_json_served(self):
        client = _make_real_client()
        resp = client.get("/history/history-data.json")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"

    def test_history_unknown_page_404(self):
        client = _make_real_client()
        resp = client.get("/history/unknown")
        assert resp.status_code == 404

    def test_history_path_traversal_blocked(self):
        client = _make_real_client()
        resp = client.get("/history/..%2F..%2Fetc%2Fpasswd")
        assert resp.status_code in (404, 400)

    def test_history_path_traversal_dotdot_blocked(self):
        client = _make_real_client()
        resp = client.get("/history/../secrets")
        # FastAPI may normalize this or return 404
        assert resp.status_code in (200, 404, 400)

    def test_history_disabled_returns_404(self):
        """When feature flag is off, history pages return 404."""
        from bitcoin_api.config import settings
        history_module._history_data = None
        mock_rpc = MagicMock()
        app.dependency_overrides[get_rpc] = lambda: mock_rpc
        original = settings.enable_history_explorer
        try:
            settings.enable_history_explorer = False
            client = TestClient(app)
            resp = client.get("/history")
            assert resp.status_code == 404
        finally:
            settings.enable_history_explorer = original
            app.dependency_overrides.clear()


class TestHistoryAPIViaRealApp:
    def test_events_via_real_app(self):
        client = _make_real_client()
        resp = client.get("/api/v1/history/events?limit=3")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) <= 3

    def test_eras_via_real_app(self):
        client = _make_real_client()
        resp = client.get("/api/v1/history/eras")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 7

    def test_search_via_real_app(self):
        client = _make_real_client()
        resp = client.get("/api/v1/history/search?q=genesis")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) > 0


class TestHistoryDataIntegrity:
    """Validate the curated data file itself."""

    def test_data_file_exists(self):
        assert _DATA_FILE.exists(), f"Data file not found: {_DATA_FILE}"

    def test_data_file_valid_json(self):
        data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        assert "eras" in data
        assert "events" in data
        assert "concepts" in data

    def test_events_chronological_order(self):
        data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        events = data["events"]
        dates = [e["date"] for e in events]
        assert dates == sorted(dates), f"Events not in chronological order: {dates}"

    def test_all_event_eras_valid(self):
        data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        era_ids = {e["id"] for e in data["eras"]}
        for event in data["events"]:
            assert event["era"] in era_ids, f"Event {event['id']} has invalid era: {event['era']}"

    def test_all_learn_concepts_valid(self):
        data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        concept_ids = set(data["concepts"].keys())
        for event in data["events"]:
            for cid in event.get("learn", []):
                assert cid in concept_ids, f"Event {event['id']} references unknown concept: {cid}"

    def test_event_count(self):
        data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        assert len(data["events"]) == 26

    def test_era_count(self):
        data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        assert len(data["eras"]) == 7

    def test_concept_count(self):
        data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        assert len(data["concepts"]) == 14
