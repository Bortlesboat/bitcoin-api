import json
from datetime import datetime, timedelta, timezone

import pytest


def _sql_time(minutes_offset: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes_offset)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _seed_fee_history_row(
    conn,
    *,
    ts: str,
    next_block_fee: float,
    median_fee: float,
    low_fee: float,
    mempool_size: int,
    mempool_vsize: int,
    congestion: str,
) -> None:
    conn.execute(
        "INSERT INTO fee_history (ts, next_block_fee, median_fee, low_fee, mempool_size, mempool_vsize, congestion) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            ts,
            next_block_fee,
            median_fee,
            low_fee,
            mempool_size,
            mempool_vsize,
            congestion,
        ),
    )


def _seed_block_confirmation(
    conn,
    *,
    block_height: int,
    block_time: str,
    captured_at: str | None = None,
    min_feerate: float,
    p50_feerate: float,
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO block_confirmations "
        "(block_height, block_hash, block_time, captured_at, tx_count, total_fees_sat, "
        "min_feerate, max_feerate, p10_feerate, p25_feerate, p50_feerate, "
        "p75_feerate, p90_feerate, core_est_1, core_est_6, core_est_144) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            block_height,
            f"hash-{block_height}",
            block_time,
            captured_at or block_time,
            2500,
            10_000_000,
            min_feerate,
            max(min_feerate + 20.0, p50_feerate),
            max(min_feerate, 1.0),
            max(min_feerate + 1.0, 2.0),
            p50_feerate,
            p50_feerate + 10.0,
            p50_feerate + 20.0,
            None,
            None,
            None,
        ),
    )


def test_build_fee_forecast_benchmark_rows_returns_importer_shape():
    from bitcoin_api.db import get_db
    from bitcoin_api.services.benchmark_export import build_fee_forecast_benchmark_rows

    conn = get_db()
    observation_time = _sql_time(-60)
    skipped_time = _sql_time(-10)

    _seed_fee_history_row(
        conn,
        ts=observation_time,
        next_block_fee=18.0,
        median_fee=11.0,
        low_fee=3.0,
        mempool_size=22000,
        mempool_vsize=1_500_000,
        congestion="high",
    )
    _seed_fee_history_row(
        conn,
        ts=skipped_time,
        next_block_fee=7.0,
        median_fee=5.0,
        low_fee=2.0,
        mempool_size=8000,
        mempool_vsize=700_000,
        congestion="normal",
    )

    _seed_block_confirmation(
        conn,
        block_height=880000,
        block_time=_sql_time(-70),
        min_feerate=2.0,
        p50_feerate=12.0,
    )

    future_blocks = [
        (-55, 1.0, 10.0),
        (-45, 2.0, 11.0),
        (-35, 4.0, 12.0),
        (-25, 6.0, 13.0),
        (-15, 15.0, 14.0),
        (-5, 40.0, 16.0),
    ]
    for index, (minutes_offset, min_feerate, p50_feerate) in enumerate(
        future_blocks, start=1
    ):
        _seed_block_confirmation(
            conn,
            block_height=880000 + index,
            block_time=_sql_time(minutes_offset),
            min_feerate=min_feerate,
            p50_feerate=p50_feerate,
        )
    conn.commit()

    rows = build_fee_forecast_benchmark_rows(hours=2, interval_minutes=1)

    assert len(rows) == 1
    row = rows[0]
    assert row["observation_id"].startswith("fee-history-")
    assert row["observed_at"].endswith("Z")
    assert row["features"] == {
        "next_block_fee": 18.0,
        "median_fee": 11.0,
        "low_fee": 3.0,
        "pending_tx_count": 22000,
        "mempool_vbytes": 1_500_000,
        "congestion": "high",
        "recent_block_median_sat_vb": 12.0,
    }
    assert row["clearing_fee_bin_by_horizon"] == {
        1: 0,
        2: 1,
        3: 2,
        4: 3,
        5: 5,
        6: 7,
    }


def test_fee_forecast_benchmark_cli_writes_jsonl(tmp_path):
    from bitcoin_api.benchmark_export_cli import main
    from bitcoin_api.db import get_db

    conn = get_db()
    observation_time = _sql_time(-60)

    _seed_fee_history_row(
        conn,
        ts=observation_time,
        next_block_fee=12.0,
        median_fee=8.0,
        low_fee=2.0,
        mempool_size=14000,
        mempool_vsize=990_000,
        congestion="normal",
    )
    _seed_block_confirmation(
        conn,
        block_height=881000,
        block_time=_sql_time(-70),
        min_feerate=1.0,
        p50_feerate=9.0,
    )
    for index, min_feerate in enumerate((1.0, 2.0, 3.0, 5.0, 8.0, 13.0), start=1):
        _seed_block_confirmation(
            conn,
            block_height=881000 + index,
            block_time=_sql_time(-60 + (index * 8)),
            min_feerate=min_feerate,
            p50_feerate=min_feerate + 4.0,
        )
    conn.commit()

    output_path = tmp_path / "historical-export.jsonl"
    exit_code = main(
        [
            str(output_path),
            "--hours",
            "2",
            "--interval-minutes",
            "1",
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    assert set(rows[0]) == {
        "observation_id",
        "observed_at",
        "features",
        "clearing_fee_bin_by_horizon",
    }
    assert rows[0]["clearing_fee_bin_by_horizon"] == {
        "1": 0,
        "2": 1,
        "3": 2,
        "4": 3,
        "5": 4,
        "6": 5,
    }


def test_benchmark_horizons_follow_capture_time_and_consecutive_height():
    from bitcoin_api.db import get_db
    from bitcoin_api.services.benchmark_export import build_fee_forecast_benchmark_rows

    conn = get_db()
    observation_time = _sql_time(-60)
    _seed_fee_history_row(
        conn,
        ts=observation_time,
        next_block_fee=10.0,
        median_fee=7.0,
        low_fee=2.0,
        mempool_size=10_000,
        mempool_vsize=800_000,
        congestion="normal",
    )
    _seed_block_confirmation(
        conn,
        block_height=900_000,
        block_time=_sql_time(-5),
        captured_at=_sql_time(-70),
        min_feerate=1.0,
        p50_feerate=9.0,
    )

    # Header times are deliberately out of order. Capture time and chain height
    # determine which blocks were actually future outcomes for the observation.
    for index, (captured_offset, header_offset, min_feerate) in enumerate(
        [
            (-55, -15, 1.0),
            (-45, -50, 2.0),
            (-35, -10, 3.0),
            (-25, -40, 5.0),
            (-15, -20, 8.0),
            (-5, -30, 13.0),
        ],
        start=1,
    ):
        _seed_block_confirmation(
            conn,
            block_height=900_000 + index,
            block_time=_sql_time(header_offset),
            captured_at=_sql_time(captured_offset),
            min_feerate=min_feerate,
            p50_feerate=min_feerate + 4.0,
        )
    conn.commit()

    rows = build_fee_forecast_benchmark_rows(hours=2, interval_minutes=1)

    assert len(rows) == 1
    assert rows[0]["features"]["recent_block_median_sat_vb"] == 9.0
    assert rows[0]["clearing_fee_bin_by_horizon"] == {
        1: 0,
        2: 1,
        3: 2,
        4: 3,
        5: 4,
        6: 5,
    }


def test_benchmark_skips_outcomes_with_a_missing_chain_height():
    from bitcoin_api.db import get_db
    from bitcoin_api.services.benchmark_export import build_fee_forecast_benchmark_rows

    conn = get_db()
    _seed_fee_history_row(
        conn,
        ts=_sql_time(-60),
        next_block_fee=10.0,
        median_fee=7.0,
        low_fee=2.0,
        mempool_size=10_000,
        mempool_vsize=800_000,
        congestion="normal",
    )
    for index, height in enumerate(
        (910_001, 910_002, 910_004, 910_005, 910_006, 910_007), start=1
    ):
        _seed_block_confirmation(
            conn,
            block_height=height,
            block_time=_sql_time(-60 + (index * 8)),
            min_feerate=float(index),
            p50_feerate=float(index + 4),
        )
    conn.commit()

    assert build_fee_forecast_benchmark_rows(hours=2, interval_minutes=1) == []


def test_fee_rate_bins_keep_the_highest_boundary_distinct():
    from bitcoin_api.services.benchmark_export import _fee_rate_to_bin_index

    expected_bins = {
        0.5: 0,
        1.0: 0,
        2.0: 1,
        3.0: 2,
        5.0: 3,
        8.0: 4,
        13.0: 5,
        21.0: 6,
        34.0: 7,
        55.0: 8,
        100.0: 8,
    }
    assert {
        fee_rate: _fee_rate_to_bin_index(fee_rate) for fee_rate in expected_bins
    } == expected_bins


def test_benchmark_builder_rejects_invalid_ranges():
    from bitcoin_api.services.benchmark_export import build_fee_forecast_benchmark_rows

    for kwargs in ({"hours": 0}, {"interval_minutes": 0}, {"limit": -1}):
        with pytest.raises(ValueError):
            build_fee_forecast_benchmark_rows(**kwargs)


def test_benchmark_cli_rejects_invalid_ranges(tmp_path):
    from bitcoin_api.benchmark_export_cli import main

    for args in (
        [str(tmp_path / "hours.jsonl"), "--hours", "0"],
        [str(tmp_path / "interval.jsonl"), "--interval-minutes", "0"],
        [str(tmp_path / "limit.jsonl"), "--limit", "-1"],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main(args)
        assert exc_info.value.code == 2
