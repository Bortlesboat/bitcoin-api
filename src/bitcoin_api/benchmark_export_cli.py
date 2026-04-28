"""CLI for exporting benchmark-ready fee forecast datasets."""

from __future__ import annotations

import argparse
from pathlib import Path

from .services.benchmark_export import write_fee_forecast_benchmark_export


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export fee research tables into benchmark-ready JSONL rows.",
    )
    parser.add_argument("output_path", type=Path, help="Destination JSONL path")
    parser.add_argument(
        "--hours",
        type=int,
        default=168,
        help="How many recent hours of fee history to inspect (default: 168)",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=10,
        help="Fee history downsampling interval in minutes (default: 10)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on exported examples (keeps the most recent rows)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    write_fee_forecast_benchmark_export(
        args.output_path,
        hours=args.hours,
        interval_minutes=args.interval_minutes,
        limit=args.limit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
