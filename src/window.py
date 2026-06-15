"""Snap trajectory timestamps to fixed, configurable time windows."""

import pandas as pd


def snap_to_windows(
    df: pd.DataFrame,
    window_size_seconds: int,
    timestamp_col: str = "timestamp",
) -> pd.DataFrame:
    """
    Add a ``window_id`` column by flooring each timestamp to a fixed window start.

    Parameters
    ----------
    df : pd.DataFrame
        Trajectory data with at least a timestamp column.
    window_size_seconds : int
        Width of each time window in seconds.
    timestamp_col : str
        Name of the timestamp column (Unix seconds or pandas-convertible).

    Returns
    -------
    pd.DataFrame
        Copy of ``df`` with integer ``window_id`` (window start in seconds).
    """
    if window_size_seconds <= 0:
        raise ValueError("window_size_seconds must be positive")

    if timestamp_col not in df.columns:
        raise ValueError(f"Missing required column: {timestamp_col}")

    out = df.copy()
    raw_ts = out[timestamp_col]

    if pd.api.types.is_numeric_dtype(raw_ts):
        epoch_seconds = pd.to_numeric(raw_ts, errors="raise").astype("int64")
    else:
        parsed = pd.to_datetime(raw_ts, errors="raise", utc=True)
        epoch_seconds = (parsed.astype("int64") // 1_000_000_000).astype("int64")

    out["window_id"] = (epoch_seconds // window_size_seconds) * window_size_seconds
    return out
