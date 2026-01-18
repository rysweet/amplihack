#!/usr/bin/env python3
"""Analyze backlog items and generate recommendations using multi-criteria scoring.

Usage:
    python analyze_backlog.py [--project-root PATH] [--max-recommendations N]

Returns JSON with top N recommendations.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file safely."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def categorize_item(item: dict) -> str:
    """Categorize backlog item."""
    text = (item.get("title", "") + " " + item.get("description", "")).lower()

    if any(kw in text for kw in ["fix", "bug", "issue", "error", "broken"]):
        return "bug"
    if any(kw in text for kw in ["test", "coverage", "verify", "validate"]):
        return "test"
    if any(kw in text for kw in ["document", "docs", "readme", "comment", "explain"]):
        return "documentation"
    if any(kw in text for kw in ["refactor", "clean", "improve", "optimize", "restructure"]):
        return "refactor"
    if any(kw in text for kw in ["add", "implement", "create", "new", "feature"]):
        return "feature"

    return "other"


def extract_technical_signals(item: dict) -> dict[str, bool]:
    """Extract technical complexity signals."""
    text = (item.get("title", "") + " " + item.get("description", "")).lower()

    return {
        "has_api_changes": any(kw in text for kw in ["api", "endpoint", "route"]),
        "has_db_changes": any(kw in text for kw in ["database", "db", "schema", "migration"]),
        "has_ui_changes": any(kw in text for kw in ["ui", "interface", "frontend", "view"]),
        "mentions_testing": any(kw in text for kw in ["test", "coverage", "verify"]),
        "mentions_security": any(
            kw in text for kw in ["security", "auth", "permission", "encryption"]
        ),
    }


def estimate_complexity(item: dict) -> str:
    """Estimate complexity: simple, medium, complex."""
    hours = item.get("estimated_hours", 4)

    if hours < 2:
        base = "simple"
    elif hours <= 6:
        base = "medium"
    else:
        base = "complex"

    # Adjust based on technical signals
    signals = extract_technical_signals(item)
    complexity_count = sum(1 for v in signals.values() if v)

    if complexity_count >= 3:
        if base == "simple":
            base = "medium"
        elif base == "medium":
            base = "complex"

    return base


def detect_dependencies(item: dict, all_items: list[dict]) -> list[str]:
    """Detect dependencies (simplified - checks for BL-XXX references)."""
    import re

    dependencies = []
    text = (item.get("title", "") + " " + item.get("description", "")).lower()

    # Find BL-XXX references
    pattern = r"bl-\d{3}"
    matches = re.findall(pattern, text, re.IGNORECASE)

    item_ids = {i["id"] for i in all_items}
    dependencies = [m.upper() for m in matches if m.upper() in item_ids]

    return list(set(dependencies))


def count_blocking(item: dict, all_items: list[dict]) -> int:
    """Count how many items this item would unblock."""
    count = 0
    item_id = item["id"]

    for other in all_items:
        if other["id"] == item_id:
            continue

        deps = detect_dependencies(other, all_items)
        if item_id in deps:
            count += 1

    return count


def calculate_scores(item: dict, config: dict, all_items: list[dict]) -> dict:
    """Calculate multi-criteria scores."""
    # Priority score (40%)
    priority_map = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}
    priority_score = priority_map.get(item.get("priority", "MEDIUM"), 0.5)

    # Blocking score (30%)
    blocking_count = count_blocking(item, all_items)
    total_items = len(all_items)
    max_expected = max(total_items * 0.3, 1)
    blocking_score = min(blocking_count / max_expected, 1.0) if total_items > 0 else 0.0

    # Ease score (20%)
    complexity = estimate_complexity(item)
    ease_map = {"simple": 1.0, "medium": 0.6, "complex": 0.3}
    ease_score = ease_map.get(complexity, 0.5)

    # Goal alignment score (10%)
    text = (item.get("title", "") + " " + item.get("description", "")).lower()
    goal_score = priority_score  # Base on priority

    # Check goal alignment
    goals = config.get("primary_goals", [])
    for goal in goals:
        goal_words = set(goal.lower().split())
        if any(word in text for word in goal_words):
            goal_score = min(goal_score + 0.1, 1.0)

    # Category adjustments
    category = categorize_item(item)
    if category == "bug":
        goal_score = min(goal_score + 0.15, 1.0)
    elif category == "documentation":
        goal_score = max(goal_score - 0.05, 0.0)

    # Total weighted score
    total_score = (
        priority_score * 0.40 + blocking_score * 0.30 + ease_score * 0.20 + goal_score * 0.10
    ) * 100

    return {
        "total_score": round(total_score, 1),
        "priority_score": priority_score,
        "blocking_score": round(blocking_score, 2),
        "ease_score": ease_score,
        "goal_score": round(goal_score, 2),
        "complexity": complexity,
        "blocking_count": blocking_count,
    }


def estimate_confidence(item: dict) -> float:
    """Estimate confidence in recommendation."""
    confidence = 0.5

    # Detailed description
    desc_len = len(item.get("description", ""))
    if desc_len > 100:
        confidence += 0.2
    elif desc_len > 50:
        confidence += 0.1

    # Explicit priority
    if item.get("priority") in ["HIGH", "LOW"]:
        confidence += 0.1

    # Tags provide context
    if item.get("tags"):
        confidence += 0.1

    # Estimated hours set
    if item.get("estimated_hours", 4) != 4:
        confidence += 0.1

    return min(confidence, 1.0)


def generate_rationale(item: dict, scores: dict) -> str:
    """Generate human-readable rationale."""
    reasons = []

    # Priority
    priority = item.get("priority", "MEDIUM")
    if priority == "HIGH":
        reasons.append("HIGH priority")
    elif priority == "LOW":
        reasons.append("LOW priority but valuable")

    # Blocking
    blocking_count = scores["blocking_count"]
    if blocking_count > 0:
        reasons.append(f"unblocks {blocking_count} other item(s)")

    # Complexity
    complexity = scores["complexity"]
    if complexity == "simple":
        reasons.append("quick win (simple)")
    elif complexity == "complex":
        reasons.append("complex but important")

    # Goal alignment
    if scores["goal_score"] > 0.7:
        reasons.append("high business value")

    if not reasons:
        reasons.append("good next step")

    return "Recommended because: " + ", ".join(reasons)


def analyze_backlog(project_root: Path, max_recommendations: int = 3) -> dict:
    """Analyze backlog and generate recommendations."""
    pm_dir = project_root / ".pm"

    # Load config
    config = load_yaml(pm_dir / "config.yaml")

    # Load backlog
    backlog_data = load_yaml(pm_dir / "backlog" / "items.yaml")
    items = backlog_data.get("items", [])

    # Filter to READY items only
    ready_items = [item for item in items if item.get("status") == "READY"]

    if not ready_items:
        return {"recommendations": [], "message": "No READY items in backlog"}

    # Score each item
    recommendations = []
    for item in ready_items:
        # Check dependencies
        deps = detect_dependencies(item, items)
        unmet_deps = [
            dep for dep in deps if any(i["id"] == dep and i.get("status") != "DONE" for i in items)
        ]

        if unmet_deps:
            continue  # Skip items with unmet dependencies

        scores = calculate_scores(item, config, items)
        confidence = estimate_confidence(item)
        rationale = generate_rationale(item, scores)

        recommendations.append(
            {
                "backlog_item": {
                    "id": item["id"],
                    "title": item["title"],
                    "priority": item.get("priority", "MEDIUM"),
                    "estimated_hours": item.get("estimated_hours", 4),
                },
                "score": scores["total_score"],
                "confidence": round(confidence, 2),
                "rationale": rationale,
                "complexity": scores["complexity"],
                "blocking_count": scores["blocking_count"],
                "dependencies": deps,
                "score_breakdown": {
                    "priority": scores["priority_score"],
                    "blocking": scores["blocking_score"],
                    "ease": scores["ease_score"],
                    "goal_alignment": scores["goal_score"],
                },
            }
        )

    # Sort by score descending
    recommendations.sort(key=lambda r: r["score"], reverse=True)

    # Take top N and assign ranks
    top_recommendations = recommendations[:max_recommendations]
    for i, rec in enumerate(top_recommendations):
        rec["rank"] = i + 1

    return {
        "recommendations": top_recommendations,
        "total_ready_items": len(ready_items),
        "scored_items": len(recommendations),
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze backlog and generate recommendations")
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )
    parser.add_argument(
        "--max-recommendations", type=int, default=3, help="Maximum recommendations to return"
    )

    args = parser.parse_args()

    try:
        result = analyze_backlog(args.project_root, args.max_recommendations)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
