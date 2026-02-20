"""Data analysis domain tools. Pure functions for computing statistics, detecting trends, and generating insights."""

from __future__ import annotations

import re
from typing import Any


def compute_statistics(data: list[float | int], label: str = "values") -> dict[str, Any]:
    """Compute basic statistics for a dataset.

    Args:
        data: List of numeric values
        label: Label for the dataset

    Returns:
        Dict with count, mean, median, min, max, std_dev, range
    """
    if not data:
        return {
            "label": label,
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "min": 0.0,
            "max": 0.0,
            "std_dev": 0.0,
            "range": 0.0,
        }

    sorted_data = sorted(data)
    n = len(data)
    total = sum(data)
    mean = total / n

    # Median
    if n % 2 == 0:
        median = (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
    else:
        median = sorted_data[n // 2]

    # Standard deviation
    variance = sum((x - mean) ** 2 for x in data) / n
    std_dev = variance ** 0.5

    return {
        "label": label,
        "count": n,
        "mean": round(mean, 3),
        "median": round(median, 3),
        "min": min(data),
        "max": max(data),
        "std_dev": round(std_dev, 3),
        "range": round(max(data) - min(data), 3),
    }


def detect_trends(data: list[float | int], labels: list[str] | None = None) -> dict[str, Any]:
    """Detect trends in sequential data.

    Identifies increasing, decreasing, or stable patterns.

    Args:
        data: Sequential numeric values (e.g. monthly revenue)
        labels: Optional labels for each data point (e.g. month names)

    Returns:
        Dict with trend_direction, change_rate, peak, trough, trend_segments
    """
    if not data or len(data) < 2:
        return {
            "trend_direction": "insufficient_data",
            "change_rate": 0.0,
            "peak": {"value": data[0] if data else 0, "index": 0},
            "trough": {"value": data[0] if data else 0, "index": 0},
            "trend_segments": [],
        }

    if labels is None:
        labels = [f"point_{i}" for i in range(len(data))]

    # Overall trend
    changes = [data[i] - data[i - 1] for i in range(1, len(data))]
    positive_changes = sum(1 for c in changes if c > 0)
    negative_changes = sum(1 for c in changes if c < 0)

    if positive_changes > negative_changes * 1.5:
        trend_direction = "increasing"
    elif negative_changes > positive_changes * 1.5:
        trend_direction = "decreasing"
    else:
        trend_direction = "stable"

    # Change rate (overall)
    overall_change = data[-1] - data[0]
    change_rate = overall_change / abs(data[0]) if data[0] != 0 else 0.0

    # Peak and trough
    peak_idx = data.index(max(data))
    trough_idx = data.index(min(data))

    # Detect trend segments (consecutive increases/decreases)
    segments: list[dict[str, Any]] = []
    current_direction = "start"
    segment_start = 0

    for i in range(1, len(data)):
        direction = "up" if data[i] > data[i - 1] else "down" if data[i] < data[i - 1] else "flat"
        if direction != current_direction and current_direction != "start":
            segments.append({
                "direction": current_direction,
                "start_label": labels[segment_start] if segment_start < len(labels) else str(segment_start),
                "end_label": labels[i - 1] if i - 1 < len(labels) else str(i - 1),
                "length": i - segment_start,
            })
            segment_start = i - 1
        current_direction = direction

    # Final segment
    if segment_start < len(data) - 1:
        segments.append({
            "direction": current_direction,
            "start_label": labels[segment_start] if segment_start < len(labels) else str(segment_start),
            "end_label": labels[-1] if labels else str(len(data) - 1),
            "length": len(data) - segment_start,
        })

    return {
        "trend_direction": trend_direction,
        "change_rate": round(change_rate, 3),
        "peak": {
            "value": max(data),
            "index": peak_idx,
            "label": labels[peak_idx] if peak_idx < len(labels) else str(peak_idx),
        },
        "trough": {
            "value": min(data),
            "index": trough_idx,
            "label": labels[trough_idx] if trough_idx < len(labels) else str(trough_idx),
        },
        "trend_segments": segments,
        "data_points": len(data),
    }


def generate_insights(data: dict[str, Any]) -> dict[str, Any]:
    """Generate analytical insights from structured data.

    Examines data for notable patterns, anomalies, and key findings.

    Args:
        data: Dictionary with at least a 'values' key containing numeric data,
              and optionally 'labels', 'category', 'title'

    Returns:
        Dict with insights list, key_finding, anomalies, recommendations
    """
    values = data.get("values", [])
    labels = data.get("labels", [])
    category = data.get("category", "general")
    title = data.get("title", "Dataset Analysis")

    insights: list[str] = []
    anomalies: list[dict[str, Any]] = []
    recommendations: list[str] = []

    if not values:
        return {
            "title": title,
            "insights": ["No data provided for analysis"],
            "key_finding": "Insufficient data",
            "anomalies": [],
            "recommendations": ["Provide numeric data for analysis"],
        }

    stats = compute_statistics(values)
    mean = stats["mean"]
    std_dev = stats["std_dev"]

    # Basic insights
    insights.append(f"Dataset contains {stats['count']} values ranging from {stats['min']} to {stats['max']}")
    insights.append(f"Mean: {mean}, Median: {stats['median']}, Std Dev: {std_dev}")

    # Detect anomalies (values > 2 std deviations from mean)
    if std_dev > 0:
        for i, v in enumerate(values):
            z_score = abs(v - mean) / std_dev
            if z_score > 2:
                label = labels[i] if i < len(labels) else f"point_{i}"
                anomalies.append({
                    "index": i,
                    "label": label,
                    "value": v,
                    "z_score": round(z_score, 2),
                    "direction": "above" if v > mean else "below",
                })

    if anomalies:
        insights.append(f"Found {len(anomalies)} anomalous values (>2 std deviations)")

    # Trend insights
    if len(values) >= 3:
        trend = detect_trends(values, labels)
        insights.append(f"Overall trend: {trend['trend_direction']} (change rate: {trend['change_rate']:.1%})")

    # Skewness check
    if mean != stats["median"]:
        direction = "right" if mean > stats["median"] else "left"
        insights.append(f"Distribution is skewed {direction} (mean {'>' if direction == 'right' else '<'} median)")

    # Key finding
    if anomalies:
        key_finding = f"Notable anomalies detected in {len(anomalies)} data points"
    elif len(values) >= 3 and abs(values[-1] - values[0]) / max(abs(values[0]), 1) > 0.2:
        key_finding = f"Significant change of {((values[-1] - values[0]) / max(abs(values[0]), 1)):.1%} over the period"
    else:
        key_finding = f"Data is relatively stable around {mean:.1f}"

    # Recommendations
    if anomalies:
        recommendations.append("Investigate anomalous data points for root causes")
    if len(values) >= 3:
        trend = detect_trends(values, labels)
        if trend["trend_direction"] == "decreasing":
            recommendations.append("Declining trend warrants attention and intervention")
        elif trend["trend_direction"] == "increasing":
            recommendations.append("Positive trend - identify and reinforce contributing factors")
    if stats["std_dev"] > mean * 0.5:
        recommendations.append("High variability - consider stabilization strategies")
    if not recommendations:
        recommendations.append("Continue monitoring for changes")

    return {
        "title": title,
        "insights": insights,
        "key_finding": key_finding,
        "anomalies": anomalies,
        "recommendations": recommendations,
        "statistics": stats,
    }


def create_narrative(data: dict[str, Any], style: str = "executive") -> dict[str, Any]:
    """Create a narrative summary of data analysis.

    Transforms analytical results into a readable story.

    Args:
        data: Dictionary with 'values', optionally 'labels', 'title', 'context'
        style: Narrative style (executive, technical, storytelling)

    Returns:
        Dict with narrative text, key_points, style_applied
    """
    values = data.get("values", [])
    title = data.get("title", "Data Analysis")
    context = data.get("context", "")
    labels = data.get("labels", [])

    if not values:
        return {
            "narrative": f"No data available for {title}.",
            "key_points": [],
            "style_applied": style,
        }

    stats = compute_statistics(values)
    key_points: list[str] = []
    narrative_parts: list[str] = []

    if style == "executive":
        narrative_parts.append(f"**{title}**")
        if context:
            narrative_parts.append(f"\n{context}")
        narrative_parts.append(
            f"\nThe analysis covers {stats['count']} data points. "
            f"The average is {stats['mean']}, with values ranging from "
            f"{stats['min']} to {stats['max']}."
        )
        key_points.append(f"Average: {stats['mean']}")

        if len(values) >= 3:
            trend = detect_trends(values, labels)
            narrative_parts.append(
                f"\nThe overall trend is {trend['trend_direction']}, "
                f"with a change rate of {trend['change_rate']:.1%}."
            )
            key_points.append(f"Trend: {trend['trend_direction']}")

            if trend["change_rate"] > 0.1:
                narrative_parts.append("This represents meaningful growth.")
                key_points.append("Positive growth identified")
            elif trend["change_rate"] < -0.1:
                narrative_parts.append("This declining trend requires attention.")
                key_points.append("Declining trend flagged")

    elif style == "technical":
        narrative_parts.append(f"# {title} - Technical Analysis\n")
        narrative_parts.append(f"n={stats['count']}, mean={stats['mean']}, "
                              f"median={stats['median']}, sd={stats['std_dev']}")
        narrative_parts.append(f"Range: [{stats['min']}, {stats['max']}]")
        key_points.append(f"SD={stats['std_dev']}")

        if len(values) >= 3:
            trend = detect_trends(values, labels)
            narrative_parts.append(f"Trend: {trend['trend_direction']} (rate={trend['change_rate']:.3f})")
            key_points.append(f"Trend={trend['trend_direction']}")

    else:  # storytelling
        narrative_parts.append(f"The story of {title} begins with {stats['count']} observations.")
        narrative_parts.append(
            f"At its lowest, we saw {stats['min']}. "
            f"At its peak, {stats['max']}. "
            f"On average, things settled around {stats['mean']}."
        )
        key_points.append("Journey from low to high captured")

        if len(values) >= 3:
            trend = detect_trends(values, labels)
            if trend["trend_direction"] == "increasing":
                narrative_parts.append("The numbers tell a story of growth.")
                key_points.append("Growth narrative")
            elif trend["trend_direction"] == "decreasing":
                narrative_parts.append("The numbers reveal a challenging trend.")
                key_points.append("Challenge narrative")
            else:
                narrative_parts.append("The numbers show remarkable stability.")
                key_points.append("Stability narrative")

    return {
        "narrative": "\n".join(narrative_parts),
        "key_points": key_points,
        "style_applied": style,
        "word_count": len(" ".join(narrative_parts).split()),
    }
