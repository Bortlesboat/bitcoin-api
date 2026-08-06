"""Export fee research data into benchmark-ready JSONL rows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..db import get_db, get_fee_history

BENCHMARK_FEE_RATE_BINS: tuple[int, ...] = (1, 2, 3, 5, 8, 13, 21, 34, 55)
BENCHMARK_FORECAST_HORIZONS: tuple[int, ...] = (1, 2, 3, 4, 5, 6)


@dataclass(frozen=True)
class BenchmarkBlockOutcome:
    block_height: int
    captured_at: str
    min_feerate: float
    p50_feerate: float


def build_fee_forecast_benchmark_rows(
    *,
    hours: int = 168,
    interval_minutes: int = 10,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Build documented benchmark rows from fee research tables."""
    if hours <= 0:
        raise ValueError("hours must be greater than zero")
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be greater than zero")
    if limit is not None and limit < 0:
        raise ValueError("limit must be zero or greater")

    observations = get_fee_history(hours=hours, interval_minutes=interval_minutes)
    if not observations:
        return []

    outcomes = _load_block_outcomes()
    if not outcomes:
        return []

    rows: list[dict[str, Any]] = []
    for observation in observations:
        observation_time = _parse_sql_timestamp(observation["ts"])
        next_block_index = next(
            (
                index
                for index, outcome in enumerate(outcomes)
                if _parse_sql_timestamp(outcome.captured_at) > observation_time
            ),
            len(outcomes),
        )
        future_blocks = outcomes[
            next_block_index : next_block_index + len(BENCHMARK_FORECAST_HORIZONS)
        ]
        if len(future_blocks) < len(BENCHMARK_FORECAST_HORIZONS):
            continue
        first_height = future_blocks[0].block_height
        if any(
            block.block_height != first_height + offset
            for offset, block in enumerate(future_blocks)
        ):
            continue

        prior_block = outcomes[next_block_index - 1] if next_block_index > 0 else None
        recent_block_median = (
            float(prior_block.p50_feerate)
            if prior_block is not None
            else float(observation.get("median_fee") or 0.0)
        )

        rows.append(
            {
                "observation_id": _build_observation_id(observation_time),
                "observed_at": _to_utc_z(observation_time),
                "features": {
                    "next_block_fee": float(observation["next_block_fee"]),
                    "median_fee": float(observation["median_fee"]),
                    "low_fee": float(observation["low_fee"]),
                    "pending_tx_count": int(observation["mempool_size"]),
                    "mempool_vbytes": int(observation["mempool_vsize"]),
                    "congestion": observation["congestion"],
                    "recent_block_median_sat_vb": round(recent_block_median, 3),
                },
                "clearing_fee_bin_by_horizon": {
                    horizon: _fee_rate_to_bin_index(float(block.min_feerate))
                    for horizon, block in zip(
                        BENCHMARK_FORECAST_HORIZONS, future_blocks, strict=True
                    )
                },
            }
        )

    if limit is not None and limit >= 0:
        rows = rows[-limit:] if limit else []

    return rows


def write_fee_forecast_benchmark_export(
    output_path: Path,
    *,
    hours: int = 168,
    interval_minutes: int = 10,
    limit: int | None = None,
) -> int:
    """Write benchmark export rows as JSONL and return the row count."""
    rows = build_fee_forecast_benchmark_rows(
        hours=hours,
        interval_minutes=interval_minutes,
        limit=limit,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = "\n".join(json.dumps(row, sort_keys=True) for row in rows)
    output_path.write_text(f"{serialized}\n" if serialized else "", encoding="utf-8")
    return len(rows)


def _load_block_outcomes() -> list[BenchmarkBlockOutcome]:
    conn = get_db()
    rows = conn.execute(
        "SELECT block_height, captured_at, min_feerate, p50_feerate "
        "FROM block_confirmations ORDER BY block_height ASC"
    ).fetchall()
    return [
        BenchmarkBlockOutcome(
            block_height=int(row["block_height"]),
            captured_at=row["captured_at"],
            min_feerate=float(row["min_feerate"]),
            p50_feerate=float(row["p50_feerate"]),
        )
        for row in rows
    ]


def _parse_sql_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def _to_utc_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_observation_id(value: datetime) -> str:
    return f"fee-history-{value.strftime('%Y%m%dT%H%M%SZ')}"


def _fee_rate_to_bin_index(fee_rate: float) -> int:
    if fee_rate <= BENCHMARK_FEE_RATE_BINS[0]:
        return 0

    for index, upper_edge in enumerate(BENCHMARK_FEE_RATE_BINS[1:], start=0):
        if fee_rate < upper_edge:
            return index

    return len(BENCHMARK_FEE_RATE_BINS) - 1
