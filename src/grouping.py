"""Merge co-located pairs over time into persistent co-movement groups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class GroupPattern:
    """A group of objects that moved together for several consecutive windows."""

    group_id: int
    members: frozenset[str]
    start_window: int
    end_window: int
    duration_windows: int
    size: int


def _connected_components(
    pairs: Iterable[tuple[str, str]],
) -> list[frozenset[str]]:
    """Build connected components from undirected pair edges (union-find)."""
    parent: dict[str, str] = {}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    nodes: set[str] = set()
    for a, b in pairs:
        nodes.add(a)
        nodes.add(b)
        if a not in parent:
            parent[a] = a
        if b not in parent:
            parent[b] = b
        union(a, b)

    components: dict[str, set[str]] = {}
    for node in nodes:
        root = find(node)
        components.setdefault(root, set()).add(node)

    return sorted(
        (frozenset(members) for members in components.values() if len(members) >= 2),
        key=lambda members: tuple(sorted(members)),
    )


def components_from_pairs(
    pairs_by_window: dict[int, list[tuple[str, str]]],
) -> dict[int, list[frozenset[str]]]:
    """Convert per-window pair lists into connected group member sets."""
    return {
        window_id: _connected_components(pairs)
        for window_id, pairs in pairs_by_window.items()
    }


def find_co_movement_patterns(
    pairs_by_window: dict[int, list[tuple[str, str]]],
    min_duration_windows: int,
    window_size_seconds: int | None = None,
) -> list[GroupPattern]:
    """
    Identify groups that persist as the same member set for at least
    ``min_duration_windows`` consecutive windows.
    """
    if min_duration_windows <= 0:
        raise ValueError("min_duration_windows must be positive")
    if window_size_seconds is not None and window_size_seconds <= 0:
        raise ValueError("window_size_seconds must be positive")

    components_by_window = components_from_pairs(pairs_by_window)
    window_ids = sorted(components_by_window.keys())

    active: dict[frozenset[str], dict[str, int]] = {}
    completed: list[GroupPattern] = []
    next_group_id = 1

    def finalize(member_set: frozenset[str], streak: dict[str, int]) -> None:
        nonlocal next_group_id
        if streak["length"] >= min_duration_windows:
            completed.append(
                GroupPattern(
                    group_id=next_group_id,
                    members=member_set,
                    start_window=streak["start"],
                    end_window=streak["last"],
                    duration_windows=streak["length"],
                    size=len(member_set),
                )
            )
            next_group_id += 1

    previous_window_id: int | None = None
    for window_id in window_ids:
        if (
            previous_window_id is not None
            and window_size_seconds is not None
            and window_id - previous_window_id != window_size_seconds
        ):
            for member_set, streak in list(active.items()):
                finalize(member_set, streak)
            active.clear()

        current_components = components_by_window[window_id]
        current_sets = set(current_components)

        for member_set, streak in list(active.items()):
            if member_set not in current_sets:
                finalize(member_set, streak)
                del active[member_set]

        for member_set in current_components:
            if member_set in active:
                streak = active[member_set]
                streak["length"] += 1
                streak["last"] = window_id
            else:
                active[member_set] = {
                    "start": window_id,
                    "last": window_id,
                    "length": 1,
                }
        previous_window_id = window_id

    for member_set, streak in active.items():
        finalize(member_set, streak)

    completed.sort(key=lambda g: (-g.duration_windows, -g.size, g.start_window))
    return completed
