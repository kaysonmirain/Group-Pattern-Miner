#!/usr/bin/env python3
"""Run Group-Pattern-Miner on sample or user-supplied trajectory data."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config import MinerConfig
from src.pipeline import load_trajectories, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover co-moving object groups in trajectory data."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/sample_trajectories.csv"),
        help="CSV with columns object_id, timestamp, lat, lon",
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("results"),
        help="Directory for output visuals",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=300,
        help="Time window size in seconds (default: 300)",
    )
    parser.add_argument(
        "--distance",
        type=float,
        default=100.0,
        help="Proximity threshold in meters (default: 100)",
    )
    parser.add_argument(
        "--min-duration",
        type=int,
        default=3,
        help="Minimum consecutive windows for a pattern (default: 3)",
    )
    args = parser.parse_args()

    config = MinerConfig(
        window_size_seconds=args.window_size,
        distance_threshold_meters=args.distance,
        min_duration_windows=args.min_duration,
    )

    df = load_trajectories(args.input)
    patterns, _ = run_pipeline(df, config=config, results_dir=args.results)

    print(f"Loaded {len(df)} trajectory points from {args.input}")
    print(f"Found {len(patterns)} co-movement pattern(s)")
    for pattern in patterns:
        members = ", ".join(sorted(pattern.members))
        print(
            f"  Group {pattern.group_id}: {pattern.size} members, "
            f"{pattern.duration_windows} windows [{members}]"
        )
    print(f"Results saved to {args.results}/")


if __name__ == "__main__":
    main()
