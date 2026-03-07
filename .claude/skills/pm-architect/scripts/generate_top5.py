#!/usr/bin/env python3
"""Aggregate priorities from PM sub-skills into a strict Top 5 ranked list.

Queries backlog-curator, workstream-coordinator, roadmap-strategist, and
work-delegator state to produce a unified priority ranking.

Usage:
    python generate_top5.py [--project-root PATH]

Returns JSON with top 5 priorities.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


# Aggregation weights
WEIGHT_BACKLOG = 0.35
WEIGHT_WORKSTREAM = 0.25
WEIGHT_ROADMAP = 0.25
WEIGHT_DELEGATION = 0.15

TOP_N = 5


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file safely."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_backlog_candidates(pm_dir: Path) -> list[dict]:
    """Extract priority candidates from backlog.

    Scores READY items using the same multi-criteria approach as backlog-curator.
    """
    backlog_data = load_yaml(pm_dir / "backlog" / "items.yaml")
    items = backlog_data.get("items", [])
    ready_items = [item for item in items if item.get("status") == "READY"]

    candidates = []
    priority_map = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}

    for item in ready_items:
        priority = item.get("priority", "MEDIUM")
        priority_score = priority_map.get(priority, 0.5)

        # Blocking score: count items that depend on this one
        item_id = item["id"]
        blocking_count = 0
        for other in items:
            if other["id"] == item_id:
                continue
            deps = other.get("dependencies", [])
            if item_id in deps:
                blocking_count += 1

        total_items = max(len(items), 1)
        blocking_score = min(blocking_count / max(total_items * 0.3, 1), 1.0)

        # Ease score based on estimated hours
        hours = item.get("estimated_hours", 4)
        if hours < 2:
            ease_score = 1.0
        elif hours <= 6:
            ease_score = 0.6
        else:
            ease_score = 0.3

        raw_score = (priority_score * 0.40 + blocking_score * 0.30 + ease_score * 0.20 + priority_score * 0.10) * 100

        # Rationale
        reasons = []
        if priority == "HIGH":
            reasons.append("HIGH priority")
        if blocking_count > 0:
            reasons.append(f"unblocks {blocking_count} item(s)")
        if hours < 2:
            reasons.append("quick win")
        if not reasons:
            reasons.append("good next step")

        candidates.append({
            "title": item.get("title", item_id),
            "source": "backlog",
            "raw_score": round(raw_score, 1),
            "rationale": ", ".join(reasons),
            "item_id": item_id,
            "priority": priority,
        })

    return candidates


def load_workstream_candidates(pm_dir: Path) -> list[dict]:
    """Extract urgent items from workstream state.

    Stalled or blocked workstreams become high-priority candidates.
    """
    workstreams_dir = pm_dir / "workstreams"
    if not workstreams_dir.exists():
        return []

    candidates = []
    now = datetime.now(UTC)

    for ws_file in workstreams_dir.glob("ws-*.yaml"):
        ws = load_yaml(ws_file)
        if not ws or ws.get("status") != "RUNNING":
            continue

        last_activity = ws.get("last_activity")
        if not last_activity:
            continue

        try:
            last_dt = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
            hours_idle = (now - last_dt).total_seconds() / 3600
        except (ValueError, TypeError):
            hours_idle = 0.0

        # Stalled workstreams get urgency score proportional to idle time
        if hours_idle > 1:
            urgency = min(hours_idle / 4.0, 1.0)  # Max at 4 hours
            raw_score = urgency * 100

            candidates.append({
                "title": f"Investigate stalled: {ws.get('title', ws.get('id', 'unknown'))}",
                "source": "workstream",
                "raw_score": round(raw_score, 1),
                "rationale": f"no activity for {hours_idle:.1f} hours",
                "item_id": ws.get("id", ""),
                "priority": "HIGH" if hours_idle > 2 else "MEDIUM",
            })

    return candidates


def extract_roadmap_goals(pm_dir: Path) -> list[str]:
    """Extract strategic goals from roadmap markdown."""
    roadmap_path = pm_dir / "roadmap.md"
    if not roadmap_path.exists():
        return []

    text = roadmap_path.read_text()
    goals = []

    # Extract goals from markdown headers and bullet points
    for line in text.splitlines():
        line = line.strip()
        # Match "## Goal: ...", "- Goal: ...", "* ..."
        if line.startswith("## ") or line.startswith("### "):
            goals.append(line.lstrip("#").strip())
        elif line.startswith("- ") or line.startswith("* "):
            goals.append(line.lstrip("-* ").strip())

    return goals


def score_roadmap_alignment(candidate: dict, goals: list[str]) -> float:
    """Score how well a candidate aligns with roadmap goals. Returns 0.0-1.0."""
    if not goals:
        return 0.5  # Neutral when no goals defined

    title_lower = candidate["title"].lower()
    max_alignment = 0.0

    for goal in goals:
        goal_words = set(goal.lower().split())
        # Remove common stop words
        goal_words -= {"the", "a", "an", "and", "or", "to", "for", "in", "of", "is", "with"}
        if not goal_words:
            continue

        matching = sum(1 for word in goal_words if word in title_lower)
        alignment = matching / len(goal_words) if goal_words else 0.0
        max_alignment = max(max_alignment, alignment)

    return min(max_alignment, 1.0)


def load_delegation_candidates(pm_dir: Path) -> list[dict]:
    """Extract items from delegation state that need action."""
    delegations_dir = pm_dir / "delegations"
    if not delegations_dir.exists():
        return []

    candidates = []
    for deleg_file in delegations_dir.glob("*.yaml"):
        deleg = load_yaml(deleg_file)
        if not deleg:
            continue

        status = deleg.get("status", "")
        if status in ("PENDING", "READY"):
            raw_score = 70.0 if status == "READY" else 50.0
            candidates.append({
                "title": f"Delegate: {deleg.get('title', deleg_file.stem)}",
                "source": "delegation",
                "raw_score": raw_score,
                "rationale": f"delegation {status.lower()}, ready for assignment",
                "item_id": deleg.get("id", deleg_file.stem),
                "priority": "MEDIUM",
            })

    return candidates


def aggregate_and_rank(
    backlog: list[dict],
    workstream: list[dict],
    delegation: list[dict],
    goals: list[str],
    top_n: int = TOP_N,
) -> list[dict]:
    """Aggregate candidates from all sources and rank by weighted score.

    Each candidate's final score is computed as:
        final = (source_weight * raw_score) + (roadmap_weight * alignment * 100)

    where source_weight depends on which sub-skill produced the candidate.
    """
    scored = []

    source_weights = {
        "backlog": WEIGHT_BACKLOG,
        "workstream": WEIGHT_WORKSTREAM,
        "delegation": WEIGHT_DELEGATION,
    }

    all_candidates = backlog + workstream + delegation

    for candidate in all_candidates:
        source = candidate["source"]
        source_weight = source_weights.get(source, 0.25)
        raw = candidate["raw_score"]

        alignment = score_roadmap_alignment(candidate, goals)
        final_score = (source_weight * raw) + (WEIGHT_ROADMAP * alignment * 100)

        scored.append({
            "title": candidate["title"],
            "source": candidate["source"],
            "score": round(final_score, 1),
            "rationale": candidate["rationale"],
            "item_id": candidate.get("item_id", ""),
            "priority": candidate.get("priority", "MEDIUM"),
            "alignment": round(alignment, 2),
        })

    # Sort by score descending, then by priority (HIGH first) for tiebreaking
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    scored.sort(key=lambda x: (-x["score"], priority_order.get(x["priority"], 1)))

    # Take top N and assign ranks
    top = scored[:top_n]
    for i, item in enumerate(top):
        item["rank"] = i + 1

    return top


def generate_top5(project_root: Path) -> dict:
    """Generate the Top 5 priority list from all PM sub-skill state."""
    pm_dir = project_root / ".pm"

    if not pm_dir.exists():
        return {
            "top5": [],
            "message": "No .pm/ directory found. Run pm-architect to initialize.",
            "sources": {"backlog": 0, "workstream": 0, "roadmap_goals": 0, "delegation": 0},
        }

    # Gather candidates from each source
    backlog = load_backlog_candidates(pm_dir)
    workstream = load_workstream_candidates(pm_dir)
    goals = extract_roadmap_goals(pm_dir)
    delegation = load_delegation_candidates(pm_dir)

    # Aggregate and rank
    top5 = aggregate_and_rank(backlog, workstream, delegation, goals)

    return {
        "top5": top5,
        "sources": {
            "backlog": len(backlog),
            "workstream": len(workstream),
            "roadmap_goals": len(goals),
            "delegation": len(delegation),
        },
        "total_candidates": len(backlog) + len(workstream) + len(delegation),
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate Top 5 priorities from PM state")
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )

    args = parser.parse_args()

    try:
        result = generate_top5(args.project_root)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
