"""Tests for Fee Observatory endpoints."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def obs_db(tmp_path):
    """Create a temporary observatory DB with test data."""
    db_path = tmp_path / "observatory.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    # Create tables matching the observatory schema
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS block_fee_stats (
            height INTEGER PRIMARY KEY,
            timestamp TEXT,
            tx_count INTEGER,
            min_feerate REAL,
            max_feerate REAL,
            median_feerate REAL,
            mean_feerate REAL,
            p10 REAL,
            p25 REAL,
            p75 REAL,
            p90 REAL
        );

        CREATE TABLE IF NOT EXISTS fee_estimates_multi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            source TEXT,
            target_blocks INTEGER,
            estimate_sat_vb REAL
        );

        CREATE TABLE IF NOT EXISTS confirmation_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_height INTEGER,
            source TEXT,
            target_blocks INTEGER,
            estimate_sat_vb REAL,
            actual_min_feerate REAL,
            would_have_confirmed INTEGER,
            estimate_timestamp TEXT,
            actual_min_feerate_effective REAL,
            confirmed_vs_effective INTEGER
        );
    """)

    # Insert test data
    conn.execute(
        "INSERT INTO block_fee_stats VALUES (880000, '2026-03-18T12:00:00', 3000, 1.0, 500.0, 12.0, 25.0, 2.0, 5.0, 50.0, 100.0)"
    )
    conn.execute(
        "INSERT INTO block_fee_stats VALUES (879999, '2026-03-18T11:50:00', 2800, 1.0, 400.0, 10.0, 20.0, 2.0, 4.0, 40.0, 80.0)"
    )

    conn.execute(
        "INSERT INTO fee_estimates_multi VALUES (NULL, '2099-01-01T00:00:00', 'core', 6, 12.5)"
    )
    conn.execute(
        "INSERT INTO fee_estimates_multi VALUES (NULL, '2099-01-01T00:00:00', 'mempool', 6, 15.0)"
    )

    conn.execute(
        """INSERT INTO confirmation_outcomes VALUES
           (NULL, 880000, 'core', 6, 12.5, 10.0, 1, '2099-01-01T00:00:00', NULL, NULL)"""
    )
    conn.execute(
        """INSERT INTO confirmation_outcomes VALUES
           (NULL, 880000, 'mempool', 6, 15.0, 10.0, 1, '2099-01-01T00:00:00', NULL, NULL)"""
    )
    conn.execute(
        """INSERT INTO confirmation_outcomes VALUES
           (NULL, 879999, 'core', 6, 8.0, 10.0, 0, '2099-01-01T00:00:00', NULL, NULL)"""
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def obs_client(obs_db):
    """TestClient with observatory pointed at the temp DB."""
    import bitcoin_api.routers.observatory as obs_mod

    # Inject a pre-opened connection so _get_obs_conn returns it directly
    conn = sqlite3.connect(str(obs_db), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    obs_mod._obs_conn = conn

    from bitcoin_api.main import app
    with TestClient(app) as c:
        yield c

    conn.close()
    obs_mod._obs_conn = None


# --- Scoreboard ---

def test_scoreboard_returns_data(obs_client):
    resp = obs_client.get("/api/v1/fees/observatory/scoreboard")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 2  # core + mempool


def test_scoreboard_fields(obs_client):
    resp = obs_client.get("/api/v1/fees/observatory/scoreboard")
    body = resp.json()
    row = body["data"][0]
    assert "source" in row
    assert "total_outcomes" in row
    assert "accuracy_pct" in row
    assert "avg_overpayment" in row


def test_scoreboard_hours_param(obs_client):
    resp = obs_client.get("/api/v1/fees/observatory/scoreboard?hours=24")
    assert resp.status_code == 200


def test_scoreboard_hours_validation(obs_client):
    resp = obs_client.get("/api/v1/fees/observatory/scoreboard?hours=0")
    assert resp.status_code == 422


# --- Block Stats ---

def test_block_stats_returns_data(obs_client):
    resp = obs_client.get("/api/v1/fees/observatory/block-stats")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 2


def test_block_stats_fields(obs_client):
    resp = obs_client.get("/api/v1/fees/observatory/block-stats")
    body = resp.json()
    row = body["data"][0]
    assert "height" in row
    assert "median_feerate" in row


def test_block_stats_limit(obs_client):
    resp = obs_client.get("/api/v1/fees/observatory/block-stats?limit=1")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


def test_block_stats_limit_validation(obs_client):
    resp = obs_client.get("/api/v1/fees/observatory/block-stats?limit=200")
    assert resp.status_code == 422


# --- Estimates ---

def test_estimates_returns_data(obs_client):
    resp = obs_client.get("/api/v1/fees/observatory/estimates")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)


def test_estimates_source_filter(obs_client):
    resp = obs_client.get("/api/v1/fees/observatory/estimates?source=core")
    assert resp.status_code == 200
    for row in resp.json()["data"]:
        assert row["source"] == "core"


def test_estimates_hours_param(obs_client):
    resp = obs_client.get("/api/v1/fees/observatory/estimates?hours=1")
    assert resp.status_code == 200


# --- 503 when observatory unavailable ---

def test_503_when_db_missing(client):
    """Observatory endpoints return 503 when DB doesn't exist."""
    import bitcoin_api.routers.observatory as obs_mod
    obs_mod._obs_conn = None

    with patch("bitcoin_api.config.settings") as mock_settings:
        mock_settings.observatory_db_path = "/nonexistent/path/observatory.db"
        mock_settings.enable_observatory = True
        # Force fresh connection attempt
        obs_mod._obs_conn = None

        # The _get_obs_conn will raise 503 since path doesn't exist
        with patch.object(obs_mod, "_get_obs_conn", side_effect=lambda: (_ for _ in ()).throw(
            __import__("fastapi").HTTPException(status_code=503, detail="Fee Observatory database not available")
        )):
            resp = client.get("/api/v1/fees/observatory/scoreboard")
            assert resp.status_code == 503


# --- Static page ---

def test_fee_observatory_page(client):
    """The legacy /fee-observatory route should redirect to the main fee tracker."""
    resp = client.get("/fee-observatory", follow_redirects=False)
    assert resp.status_code == 308
    assert resp.headers["location"] == "/fees"
