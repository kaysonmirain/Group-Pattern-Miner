"""Unit tests for timestamp window snapping."""

import unittest

import pandas as pd

from src.window import snap_to_windows


class WindowTests(unittest.TestCase):
    def test_numeric_timestamps_snap_to_floor(self):
        df = pd.DataFrame({"timestamp": [100, 299, 300]})
        out = snap_to_windows(df, window_size_seconds=300)
        self.assertEqual(out["window_id"].tolist(), [0, 0, 300])

    def test_datetime_timestamps_snap_to_epoch_window(self):
        df = pd.DataFrame(
            {"timestamp": ["2024-01-01T00:04:59Z", "2024-01-01T00:05:00Z"]}
        )
        out = snap_to_windows(df, window_size_seconds=300)
        self.assertEqual(out["window_id"].tolist(), [1704067200, 1704067500])

    def test_invalid_window_size(self):
        df = pd.DataFrame({"timestamp": [100]})
        with self.assertRaisesRegex(ValueError, "window_size_seconds"):
            snap_to_windows(df, window_size_seconds=0)


if __name__ == "__main__":
    unittest.main()
