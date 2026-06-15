"""Configuration parameters for group pattern mining."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MinerConfig:
    """Parameters controlling windowing, proximity, and group persistence."""

    # Time window size in seconds (timestamps are snapped to window starts).
    window_size_seconds: int = 300

    # Maximum distance in meters for two objects to count as co-located.
    distance_threshold_meters: float = 100.0

    # Minimum consecutive windows a group must persist to qualify as a pattern.
    min_duration_windows: int = 3


DEFAULT_CONFIG = MinerConfig()
