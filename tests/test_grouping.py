"""Unit tests for co-movement group detection."""

import unittest

from src.grouping import (
    components_from_pairs,
    find_co_movement_patterns,
)


class GroupingTests(unittest.TestCase):
    def test_components_merge_transitive_pairs(self):
        pairs = {0: [("a", "b"), ("b", "c")]}
        components = components_from_pairs(pairs)
        self.assertEqual(components[0], [frozenset({"a", "b", "c"})])

    def test_components_ignore_singletons(self):
        pairs = {0: []}
        components = components_from_pairs(pairs)
        self.assertEqual(components[0], [])

    def test_pattern_requires_min_duration(self):
        member_set = frozenset({"a", "b"})
        pairs = {
            0: [("a", "b")],
            300: [("a", "b")],
        }
        short = find_co_movement_patterns(
            pairs,
            min_duration_windows=3,
            window_size_seconds=300,
        )
        self.assertEqual(short, [])

        pairs[600] = [("a", "b")]
        long_enough = find_co_movement_patterns(
            pairs,
            min_duration_windows=3,
            window_size_seconds=300,
        )
        self.assertEqual(len(long_enough), 1)
        self.assertEqual(long_enough[0].members, member_set)
        self.assertEqual(long_enough[0].duration_windows, 3)
        self.assertEqual(long_enough[0].size, 2)

    def test_pattern_breaks_on_empty_window(self):
        pairs = {
            0: [("a", "b")],
            300: [("a", "b")],
            600: [("a", "b")],
            900: [],
            1200: [("a", "b")],
            1500: [("a", "b")],
            1800: [("a", "b")],
        }
        patterns = find_co_movement_patterns(
            pairs,
            min_duration_windows=3,
            window_size_seconds=300,
        )
        self.assertEqual(len(patterns), 2)
        self.assertTrue(all(p.duration_windows == 3 for p in patterns))

    def test_pattern_breaks_on_missing_window_id_gap(self):
        pairs = {
            0: [("a", "b")],
            300: [("a", "b")],
            900: [("a", "b")],
            1200: [("a", "b")],
        }
        patterns = find_co_movement_patterns(
            pairs,
            min_duration_windows=3,
            window_size_seconds=300,
        )
        self.assertEqual(patterns, [])

    def test_pattern_ranked_by_duration_then_size(self):
        pairs = {
            0: [("a", "b"), ("c", "d"), ("d", "e")],
            300: [("a", "b"), ("c", "d"), ("d", "e")],
            600: [("a", "b"), ("c", "d"), ("d", "e")],
            900: [("a", "b"), ("c", "d"), ("d", "e")],
            1200: [("a", "b")],
            1500: [("a", "b")],
            1800: [("a", "b")],
        }
        patterns = find_co_movement_patterns(
            pairs,
            min_duration_windows=3,
            window_size_seconds=300,
        )
        self.assertEqual(len(patterns), 2)
        self.assertGreaterEqual(
            patterns[0].duration_windows,
            patterns[1].duration_windows,
        )
        if patterns[0].duration_windows == patterns[1].duration_windows:
            self.assertGreaterEqual(patterns[0].size, patterns[1].size)

    def test_multiple_disjoint_groups_same_window(self):
        pairs = {
            0: [("a", "b"), ("c", "d")],
            300: [("a", "b"), ("c", "d")],
            600: [("a", "b"), ("c", "d")],
        }
        patterns = find_co_movement_patterns(
            pairs,
            min_duration_windows=3,
            window_size_seconds=300,
        )
        member_sets = {p.members for p in patterns}
        self.assertIn(frozenset({"a", "b"}), member_sets)
        self.assertIn(frozenset({"c", "d"}), member_sets)

    def test_invalid_min_duration(self):
        with self.assertRaisesRegex(ValueError, "min_duration_windows"):
            find_co_movement_patterns({}, min_duration_windows=0)


if __name__ == "__main__":
    unittest.main()
