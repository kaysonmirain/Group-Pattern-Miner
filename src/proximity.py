"""Find co-located object pairs within each time window using spatial grid binning."""

from __future__ import annotations

from collections import defaultdict
import numpy as np
import pandas as pd

EARTH_RADIUS_M = 6_371_000.0


def _haversine_vectorized(
    lat1: np.ndarray,
    lon1: np.ndarray,
    lat2: np.ndarray,
    lon2: np.ndarray,
) -> np.ndarray:
    """Great-circle distance in meters between point pairs (vectorized)."""
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def _cell_size_degrees(distance_threshold_meters: float) -> float:
    """Approximate grid cell size in degrees from a meter threshold."""
    meters_per_degree = 111_320.0
    return max(distance_threshold_meters / meters_per_degree, 1e-6)


def _project_to_local_meters(
    lats: np.ndarray,
    lons: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Project lat/lon to local x/y meters for grid indexing."""
    meters_per_degree = 111_320.0
    mean_lat_rad = np.radians(float(np.mean(lats))) if len(lats) else 0.0
    x = lons * meters_per_degree * max(float(np.cos(mean_lat_rad)), 1e-6)
    y = lats * meters_per_degree
    return x, y


def _grid_indices(
    lats: np.ndarray,
    lons: np.ndarray,
    cell_size_meters: float,
) -> tuple[np.ndarray, np.ndarray]:
    x, y = _project_to_local_meters(lats, lons)
    x_origin = float(x.min()) if len(x) else 0.0
    y_origin = float(y.min()) if len(y) else 0.0
    row = np.floor((y - y_origin) / cell_size_meters).astype(np.int64)
    col = np.floor((x - x_origin) / cell_size_meters).astype(np.int64)
    return row, col


def _candidate_cell_pairs(
    cells: list[tuple[int, int]],
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Return same/neighbor cell pairs once, avoiding duplicate comparisons."""
    cell_set = set(cells)
    ordered_pairs: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for cell in sorted(cell_set):
        r, c = cell
        for dr in (0, 1):
            dc_values = (0, 1) if dr == 0 else (-1, 0, 1)
            for dc in dc_values:
                other = (r + dr, c + dc)
                if other in cell_set:
                    ordered_pairs.append((cell, other))
    return ordered_pairs


def find_proximity_pairs(
    df: pd.DataFrame,
    distance_threshold_meters: float,
    window_col: str = "window_id",
    object_col: str = "object_id",
    lat_col: str = "lat",
    lon_col: str = "lon",
) -> dict[int, list[tuple[str, str]]]:
    """
    For each window, return sorted pairs of objects within the distance threshold.

    Uses a local meter grid so only objects in the same or adjacent cells are
    compared, avoiding an all-pairs O(n^2) scan over the full window.
    """
    if distance_threshold_meters <= 0:
        raise ValueError("distance_threshold_meters must be positive")

    required = {window_col, object_col, lat_col, lon_col}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    pairs_by_window: dict[int, list[tuple[str, str]]] = {}

    for window_id, group in df.groupby(window_col, sort=True):
        # One position per object per window (mean if duplicated).
        agg = (
            group.groupby(object_col, sort=False)[[lat_col, lon_col]]
            .mean()
            .reset_index()
        )
        if len(agg) < 2:
            pairs_by_window[int(window_id)] = []
            continue

        object_ids = agg[object_col].astype(str).to_numpy()
        lats = agg[lat_col].to_numpy(dtype=float)
        lons = agg[lon_col].to_numpy(dtype=float)

        rows, cols = _grid_indices(lats, lons, distance_threshold_meters)
        buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
        for idx, (r, c) in enumerate(zip(rows, cols)):
            buckets[(int(r), int(c))].append(idx)

        window_pairs: set[tuple[str, str]] = set()

        for cell_a, cell_b in _candidate_cell_pairs(list(buckets.keys())):
            idx_a = np.array(buckets[cell_a], dtype=np.int64)
            idx_b = np.array(buckets[cell_b], dtype=np.int64)

            if cell_a == cell_b:
                if len(idx_a) < 2:
                    continue
                left_pos, right_pos = np.triu_indices(len(idx_a), k=1)
                left = idx_a[left_pos]
                right = idx_a[right_pos]
            else:
                left_grid, right_grid = np.meshgrid(idx_a, idx_b, indexing="ij")
                left = left_grid.ravel()
                right = right_grid.ravel()

            distances = _haversine_vectorized(
                lats[left],
                lons[left],
                lats[right],
                lons[right],
            )

            close = distances <= distance_threshold_meters
            for i, j in zip(left[close], right[close]):
                a, b = sorted((object_ids[i], object_ids[j]))
                window_pairs.add((a, b))

        pairs_by_window[int(window_id)] = sorted(window_pairs)

    return pairs_by_window
