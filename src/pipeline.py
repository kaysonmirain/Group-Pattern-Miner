"""End-to-end group pattern mining pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import MinerConfig, DEFAULT_CONFIG
from src.grouping import GroupPattern, find_co_movement_patterns
from src.proximity import find_proximity_pairs
from src.visualize import (
    save_duration_chart,
    save_group_map,
    save_group_snapshot_sequence,
)
from src.window import snap_to_windows


def load_trajectories(path: str | Path) -> pd.DataFrame:
    """Load trajectory CSV with columns object_id, timestamp, lat, lon."""
    df = pd.read_csv(path)
    required = {"object_id", "timestamp", "lat", "lon"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    return df


def run_pipeline(
    df: pd.DataFrame,
    config: MinerConfig = DEFAULT_CONFIG,
    results_dir: str | Path = "results",
) -> tuple[list[GroupPattern], pd.DataFrame]:
    """
    Window trajectories, find proximity pairs, discover patterns, and save visuals.
    """
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    windowed = snap_to_windows(df, config.window_size_seconds)
    pairs = find_proximity_pairs(windowed, config.distance_threshold_meters)
    patterns = find_co_movement_patterns(
        pairs,
        config.min_duration_windows,
        window_size_seconds=config.window_size_seconds,
    )

    save_group_map(windowed, patterns, results_dir / "group_trajectories_map.html")
    save_duration_chart(patterns, results_dir / "top_groups_by_duration.png")

    if patterns:
        save_group_snapshot_sequence(
            windowed,
            patterns[0],
            results_dir / "group_snapshot_sequence.png",
        )

    return patterns, windowed
