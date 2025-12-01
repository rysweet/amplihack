#!/usr/bin/env python3
"""Search past PM decisions across all sessions.

Pattern: Amplifier Tool Mapping - Transcript Integration
Maps Amplifier's transcript search patterns to Amplihack runtime logs.

Usage:
    python search_decisions.py [--query TERM] [--session SESSION_ID] [--limit N]

Examples:
    python search_decisions.py --query "authentication"
    python search_decisions.py --session 20251122_140530
    python search_decisions.py --query "priority" --limit 10
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file safely."""
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def extract_decisions_from_markdown(md_path: Path) -> list[dict]:
    """Extract decisions from DECISIONS.md file.

    Format expected:
    ## Decision: <title>
    **Date**: <timestamp>
    **Rationale**: <reason>
    **Alternatives**: <alternatives>
    """
    if not md_path.exists():
        return []

    content = md_path.read_text()
    decisions = []

    # Pattern to match decision blocks
    pattern = r"## Decision: (.+?)\n\*\*Date\*\*: (.+?)\n\*\*Rationale\*\*: (.+?)(?:\n\*\*Alternatives\*\*: (.+?))?\n"

    for match in re.finditer(pattern, content, re.DOTALL):
        decision = {
            "decision": match.group(1).strip(),
            "date": match.group(2).strip(),
            "rationale": match.group(3).strip(),
            "alternatives": match.group(4).strip() if match.group(4) else "None documented",
        }
        decisions.append(decision)

    return decisions


def extract_session_context(session_dir: Path) -> dict:
    """Extract relevant context from session directory.

    Looks for:
    - DECISIONS.md
    - session_state.yaml (if PM Architect used)
    - Original request from logs
    """
    context = {
        "session_id": session_dir.name,
        "decisions": [],
        "pm_state": None,
        "created": None,
    }

    # Get session creation time
    try:
        context["created"] = datetime.fromtimestamp(session_dir.stat().st_ctime).isoformat()
    except Exception:
        pass

    # Extract decisions
    decisions_file = session_dir / "DECISIONS.md"
    if decisions_file.exists():
        context["decisions"] = extract_decisions_from_markdown(decisions_file)

    # Check for PM state
    pm_state_file = session_dir / "pm_session_state.yaml"
    if pm_state_file.exists():
        context["pm_state"] = load_yaml(pm_state_file)

    return context


def search_sessions(
    logs_dir: Path, query: str = None, session_id: str = None, limit: int = None
) -> list[dict]:
    """Search PM decisions across all sessions.

    Args:
        logs_dir: Runtime logs directory (.claude/runtime/logs/)
        query: Search term (searches decision text and rationale)
        session_id: Specific session to search
        limit: Maximum results to return

    Returns:
        List of matching decisions with context
    """
    if not logs_dir.exists():
        return []

    results = []
    query_lower = query.lower() if query else None

    # Determine sessions to search
    if session_id:
        session_dirs = [logs_dir / session_id] if (logs_dir / session_id).exists() else []
    else:
        session_dirs = [d for d in logs_dir.iterdir() if d.is_dir()]

    # Search each session
    for session_dir in sorted(session_dirs, key=lambda d: d.stat().st_mtime, reverse=True):
        context = extract_session_context(session_dir)

        # Search decisions in this session
        for decision in context["decisions"]:
            # Apply query filter if specified
            if query_lower:
                decision_text = (
                    decision["decision"]
                    + " "
                    + decision["rationale"]
                    + " "
                    + decision.get("alternatives", "")
                ).lower()

                if query_lower not in decision_text:
                    continue

            # Add to results
            results.append(
                {
                    "session_id": context["session_id"],
                    "session_created": context["created"],
                    "decision": decision["decision"],
                    "date": decision["date"],
                    "rationale": decision["rationale"],
                    "alternatives": decision["alternatives"],
                    "pm_context": (
                        context["pm_state"] is not None
                    ),  # Whether PM Architect was active
                }
            )

            # Check limit
            if limit and len(results) >= limit:
                return results

    return results


def restore_pm_context(session_id: str, logs_dir: Path) -> dict:
    """Restore PM Architect context from specific session.

    Pattern: Amplifier transcript restoration adapted to runtime logs.

    Args:
        session_id: Session identifier
        logs_dir: Runtime logs directory

    Returns:
        Complete PM context for session
    """
    session_dir = logs_dir / session_id
    if not session_dir.exists():
        return {"error": f"Session {session_id} not found"}

    context = extract_session_context(session_dir)

    # Add PM-specific restoration
    restoration = {
        "session_id": session_id,
        "session_created": context["created"],
        "decisions_made": context["decisions"],
        "decision_count": len(context["decisions"]),
    }

    # Include PM state if available
    if context["pm_state"]:
        pm_state = context["pm_state"]
        restoration["pm_architect"] = {
            "current_focus": pm_state.get("current_focus"),
            "stakeholders": list(pm_state.get("stakeholder_context", {}).keys()),
            "open_questions": len(pm_state.get("open_questions", [])),
            "next_actions": len(pm_state.get("next_actions", [])),
            "metrics": pm_state.get("session_metrics", {}),
        }

    return restoration


def get_decision_patterns(logs_dir: Path, min_frequency: int = 2) -> dict:
    """Identify recurring decision patterns across sessions.

    Args:
        logs_dir: Runtime logs directory
        min_frequency: Minimum times a pattern must appear

    Returns:
        Common decision patterns and their frequency
    """
    all_decisions = search_sessions(logs_dir)

    # Analyze patterns
    decision_types = {}
    rationale_keywords = {}

    for result in all_decisions:
        # Extract decision type (first word of decision)
        decision = result["decision"]
        first_word = decision.split()[0].lower() if decision.split() else "unknown"
        decision_types[first_word] = decision_types.get(first_word, 0) + 1

        # Extract keywords from rationale
        rationale = result["rationale"].lower()
        words = re.findall(r"\b\w{4,}\b", rationale)  # Words 4+ chars
        for word in words:
            rationale_keywords[word] = rationale_keywords.get(word, 0) + 1

    # Filter by frequency
    frequent_types = {k: v for k, v in decision_types.items() if v >= min_frequency}
    frequent_keywords = {k: v for k, v in rationale_keywords.items() if v >= min_frequency}

    return {
        "total_decisions": len(all_decisions),
        "decision_types": dict(sorted(frequent_types.items(), key=lambda x: x[1], reverse=True)),
        "common_rationale_keywords": dict(
            sorted(frequent_keywords.items(), key=lambda x: x[1], reverse=True)[:20]
        ),
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Search PM decisions across sessions")
    parser.add_argument("--query", help="Search term")
    parser.add_argument("--session", help="Specific session ID to search")
    parser.add_argument("--limit", type=int, help="Maximum results to return")
    parser.add_argument(
        "--restore", help="Restore complete context for session ID", metavar="SESSION_ID"
    )
    parser.add_argument(
        "--patterns", action="store_true", help="Analyze decision patterns across all sessions"
    )
    parser.add_argument(
        "--logs-dir",
        type=Path,
        default=Path.cwd() / ".claude" / "runtime" / "logs",
        help="Runtime logs directory",
    )

    args = parser.parse_args()

    try:
        if args.restore:
            # Restore PM context from specific session
            result = restore_pm_context(args.restore, args.logs_dir)
            print(json.dumps(result, indent=2))

        elif args.patterns:
            # Analyze decision patterns
            result = get_decision_patterns(args.logs_dir)
            print(json.dumps(result, indent=2))

        else:
            # Search decisions
            results = search_sessions(args.logs_dir, args.query, args.session, args.limit)
            print(
                json.dumps(
                    {"query": args.query, "session": args.session, "results": results}, indent=2
                )
            )

        return 0

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
