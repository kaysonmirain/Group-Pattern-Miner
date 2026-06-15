"""Unit tests for proximity pair detection."""

import unittest

import numpy as np
import pandas as pd

from src.proximity import (
    _cell_size_degrees,
    _haversine_vectorized,
    find_proximity_pairs,
)


class ProximityTests(unittest.TestCase):
    def test_haversine_zero_distance(self):
        dist = _haversine_vectorized(
            np.array([37.0]),
            np.array([-122.0]),
            np.array([37.0]),
            np.array([-122.0]),
        )
        self.assertAlmostEqual(dist[0], 0.0, places=3)

    def test_haversine_known_separation(self):
        # About 111 m per 0.001 degree latitude.
        dist = _haversine_vectorized(
            np.array([0.0]),
            np.array([0.0]),
            np.array([0.001]),
            np.array([0.0]),
        )
        self.assertGreater(dist[0], 100)
        self.assertLess(dist[0], 120)

    def test_cell_size_scales_with_threshold(self):
        small = _cell_size_degrees(50.0)
        large = _cell_size_degrees(200.0)
        self.assertGreater(large, small)

    def test_find_pairs_within_threshold(self):
        df = pd.DataFrame(
            {
                "window_id": [0, 0, 0],
                "object_id": ["a", "b", "c"],
                "lat": [37.7749, 37.7750, 37.7800],
                "lon": [-122.4194, -122.4193, -122.4100],
            }
        )
        pairs = find_proximity_pairs(df, distance_threshold_meters=200.0)
        self.assertEqual(pairs[0], [("a", "b")])
        self.assertNotIn(("a", "c"), pairs[0])
        self.assertNotIn(("b", "c"), pairs[0])

    def test_find_pairs_uses_grid_without_missing_neighbors(self):
        df = pd.DataFrame(
            {
                "window_id": [100, 100],
                "object_id": ["x", "y"],
                "lat": [37.7749, 37.7757],
                "lon": [-122.4194, -122.4194],
            }
        )
        pairs = find_proximity_pairs(df, distance_threshold_meters=100.0)
        self.assertEqual(pairs[100], [("x", "y")])

    def test_find_pairs_empty_window(self):
        df = pd.DataFrame(
            {
                "window_id": [0],
                "object_id": ["solo"],
                "lat": [37.0],
                "lon": [-122.0],
            }
        )
        pairs = find_proximity_pairs(df, distance_threshold_meters=100.0)
        self.assertEqual(pairs[0], [])

    def test_find_pairs_multiple_windows(self):
        df = pd.DataFrame(
            {
                "window_id": [0, 0, 300, 300],
                "object_id": ["a", "b", "a", "b"],
                "lat": [37.0, 37.0001, 37.1, 37.5],
                "lon": [-122.0, -122.0, -122.0, -122.0],
            }
        )
        pairs = find_proximity_pairs(df, distance_threshold_meters=500.0)
        self.assertIn(("a", "b"), pairs[0])
        self.assertEqual(pairs[300], [])

    def test_find_pairs_requires_columns(self):
        df = pd.DataFrame({"object_id": ["a"], "lat": [0.0], "lon": [0.0]})
        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            find_proximity_pairs(df, distance_threshold_meters=100.0)

    def test_find_pairs_invalid_threshold(self):
        df = pd.DataFrame(
            {
                "window_id": [0, 0],
                "object_id": ["a", "b"],
                "lat": [0.0, 0.0],
                "lon": [0.0, 0.0],
            }
        )
        with self.assertRaisesRegex(ValueError, "distance_threshold_meters"):
            find_proximity_pairs(df, distance_threshold_meters=0)


if __name__ == "__main__":
    unittest.main()
