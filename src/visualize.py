"""Generate folium and matplotlib outputs for discovered group patterns."""

from __future__ import annotations

from pathlib import Path

import folium
import matplotlib.pyplot as plt
import pandas as pd

from src.grouping import GroupPattern

GROUP_COLORS = [
    "#e41a1c",
    "#377eb8",
    "#4daf4a",
    "#984ea3",
    "#ff7f00",
    "#a65628",
    "#f781bf",
    "#999999",
    "#66c2a5",
    "#fc8d62",
]


def _color_for_index(index: int) -> str:
    return GROUP_COLORS[index % len(GROUP_COLORS)]


def save_group_map(
    df: pd.DataFrame,
    patterns: list[GroupPattern],
    output_path: str | Path,
    lat_col: str = "lat",
    lon_col: str = "lon",
    object_col: str = "object_id",
) -> Path:
    """Draw each group's member trajectories on a folium map with legend and popups."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if df.empty:
        center = [0.0, 0.0]
    else:
        center = [float(df[lat_col].mean()), float(df[lon_col].mean())]

    fmap = folium.Map(location=center, zoom_start=13, tiles="OpenStreetMap")
    legend_entries: list[tuple[str, str]] = []

    for idx, pattern in enumerate(patterns):
        color = _color_for_index(idx)
        legend_entries.append(
            (f"Group {pattern.group_id} (n={pattern.size})", color)
        )
        member_df = df[df[object_col].astype(str).isin(pattern.members)].sort_values(
            "timestamp"
        )

        for object_id, track in member_df.groupby(object_col, sort=False):
            points = list(zip(track[lat_col], track[lon_col]))
            if len(points) < 2:
                continue
            folium.PolyLine(
                points,
                color=color,
                weight=4,
                opacity=0.85,
                popup=folium.Popup(
                    f"Group {pattern.group_id}<br>"
                    f"Size: {pattern.size}<br>"
                    f"Object: {object_id}<br>"
                    f"Duration: {pattern.duration_windows} windows",
                    max_width=250,
                ),
            ).add_to(fmap)

    legend_html = """
    <div style="
        position: fixed; bottom: 30px; left: 30px; z-index: 9999;
        background: white; padding: 10px 12px; border: 1px solid #ccc;
        border-radius: 4px; font-size: 13px; line-height: 1.5;
        box-shadow: 0 1px 4px rgba(0,0,0,0.25);
    ">
    <b>Co-movement groups</b><br>
    """
    for label, color in legend_entries:
        legend_html += (
            f'<span style="color:{color}; font-weight:bold;">---</span> '
            f"{label}<br>"
        )
    legend_html += "</div>"
    fmap.get_root().html.add_child(folium.Element(legend_html))

    fmap.save(str(output_path))
    return output_path


def save_duration_chart(
    patterns: list[GroupPattern],
    output_path: str | Path,
    top_n: int = 10,
) -> Path:
    """Bar chart of top groups ranked by consecutive-window duration."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ranked = sorted(patterns, key=lambda g: (-g.duration_windows, -g.size))[:top_n]
    if not ranked:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No co-movement patterns found", ha="center", va="center")
        ax.set_axis_off()
    else:
        labels = [f"G{g.group_id} (n={g.size})" for g in ranked]
        durations = [g.duration_windows for g in ranked]
        colors = [_color_for_index(i) for i in range(len(ranked))]

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(labels, durations, color=colors, edgecolor="white")
        ax.set_xlabel("Group (member count)")
        ax.set_ylabel("Duration (consecutive windows)")
        ax.set_title("Top Co-Movement Groups by Duration")
        ax.tick_params(axis="x", rotation=30)
        plt.tight_layout()

    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def save_group_snapshot_sequence(
    df: pd.DataFrame,
    pattern: GroupPattern,
    output_path: str | Path,
    window_col: str = "window_id",
    lat_col: str = "lat",
    lon_col: str = "lon",
    object_col: str = "object_id",
) -> Path | None:
    """
    Optional matplotlib snapshot sequence showing one group across consecutive windows.
    """
    if pattern.duration_windows < 1:
        return None

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    member_df = df[
        (df[object_col].astype(str).isin(pattern.members))
        & (df[window_col] >= pattern.start_window)
        & (df[window_col] <= pattern.end_window)
    ]
    windows = sorted(member_df[window_col].unique())
    if not windows:
        return None

    n = len(windows)
    cols = min(4, n)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 4 * rows), squeeze=False)
    color = _color_for_index(0)

    for i, window_id in enumerate(windows):
        ax = axes[i // cols][i % cols]
        snap = member_df[member_df[window_col] == window_id]
        for object_id, obj_rows in snap.groupby(object_col, sort=False):
            ax.scatter(
                obj_rows[lon_col],
                obj_rows[lat_col],
                s=80,
                color=color,
                label=str(object_id),
            )
            ax.annotate(
                str(object_id),
                (obj_rows[lon_col].iloc[0], obj_rows[lat_col].iloc[0]),
                fontsize=8,
                xytext=(4, 4),
                textcoords="offset points",
            )
        ax.set_title(f"Window {window_id}")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True, alpha=0.3)

    for j in range(n, rows * cols):
        axes[j // cols][j % cols].set_axis_off()

    fig.suptitle(
        f"Group {pattern.group_id} staying together "
        f"({pattern.size} members, {pattern.duration_windows} windows)",
        fontsize=14,
    )
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path
