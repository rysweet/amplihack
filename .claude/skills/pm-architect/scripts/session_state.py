#!/usr/bin/env python3
"""Session state management for PM Architect context preservation.

Pattern: Amplifier P5 - Session State Maintenance
Preserves PM decision context across sessions to reduce repeated questions.

Usage:
    python session_state.py [--project-root PATH] [COMMAND]

Commands:
    init                  Initialize session state
    update-decision       Record decision with rationale
    track-preference      Track stakeholder preference
    set-focus            Set current focus
    add-question         Add open question
    add-action           Add next action
    show                 Display current state
    search               Search past decisions
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file safely."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict[str, Any]) -> None:
    """Save YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def get_timestamp() -> str:
    """Get current UTC timestamp."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class PMSessionState:
    """Track PM Architect decision context across sessions."""

    def __init__(self, session_dir: Path):
        """Initialize session state manager.

        Args:
            session_dir: PM directory (.pm/)
        """
        self.session_dir = session_dir
        self.state_file = session_dir / "session_state.md"
        self.yaml_file = session_dir / "session_state.yaml"
        self.state = self.load_state()

    def load_state(self) -> dict:
        """Load session state from YAML (machine-readable)."""
        if self.yaml_file.exists():
            return load_yaml(self.yaml_file)

        return self.initial_state()

    def initial_state(self) -> dict:
        """Create initial state structure."""
        return {
            "initialized_at": get_timestamp(),
            "last_updated": get_timestamp(),
            "current_focus": "",
            "recent_decisions": [],
            "stakeholder_context": {},
            "open_questions": [],
            "next_actions": [],
            "decision_rationale": {},
            "session_metrics": {
                "total_decisions": 0,
                "stakeholders_tracked": 0,
                "questions_resolved": 0,
            },
        }

    def save_state(self):
        """Persist state as both YAML and Markdown."""
        self.state["last_updated"] = get_timestamp()

        # Save machine-readable YAML
        save_yaml(self.yaml_file, self.state)

        # Save human-readable Markdown
        self.save_markdown()

    def save_markdown(self):
        """Save state as human-readable markdown."""
        content = f"""# PM Architect Session State

**Last Updated**: {self.state["last_updated"]}
**Initialized**: {self.state["initialized_at"]}

## Current Focus

{self.state["current_focus"] or "*No focus set*"}

## Recent Decisions

{self.format_decisions(self.state["recent_decisions"])}

## Stakeholder Context

{self.format_stakeholder_context(self.state["stakeholder_context"])}

## Open Questions

{self.format_questions(self.state["open_questions"])}

## Next Actions

{self.format_actions(self.state["next_actions"])}

## Session Metrics

- Total Decisions: {self.state["session_metrics"]["total_decisions"]}
- Stakeholders Tracked: {self.state["session_metrics"]["stakeholders_tracked"]}
- Questions Resolved: {self.state["session_metrics"]["questions_resolved"]}
"""
        self.state_file.write_text(content)

    def format_decisions(self, decisions: list[dict]) -> str:
        """Format decisions for markdown."""
        if not decisions:
            return "*No decisions recorded*"

        lines = []
        for i, dec in enumerate(decisions[-10:], 1):  # Last 10 decisions
            timestamp = dec.get("timestamp", "unknown")
            decision = dec.get("decision", "")
            rationale = dec.get("rationale", "")
            lines.append(f"{i}. **{decision}** ({timestamp})")
            if rationale:
                lines.append(f"   - Rationale: {rationale}")

        return "\n".join(lines)

    def format_stakeholder_context(self, context: dict) -> str:
        """Format stakeholder preferences for markdown."""
        if not context:
            return "*No stakeholder context*"

        lines = []
        for stakeholder, prefs in context.items():
            lines.append(f"### {stakeholder}")
            for pref in prefs[-5:]:  # Last 5 preferences
                lines.append(f"- {pref['preference']} ({pref['timestamp']})")

        return "\n".join(lines)

    def format_questions(self, questions: list[dict]) -> str:
        """Format open questions for markdown."""
        if not questions:
            return "*No open questions*"

        lines = []
        for i, q in enumerate(questions, 1):
            question = q.get("question", "")
            added = q.get("added_at", "unknown")
            status = q.get("status", "OPEN")
            lines.append(f"{i}. [{status}] {question} (added {added})")

        return "\n".join(lines)

    def format_actions(self, actions: list[dict]) -> str:
        """Format next actions for markdown."""
        if not actions:
            return "*No actions defined*"

        lines = []
        for i, action in enumerate(actions, 1):
            desc = action.get("description", "")
            priority = action.get("priority", "MEDIUM")
            lines.append(f"{i}. [{priority}] {desc}")

        return "\n".join(lines)

    def update_decision(self, decision: str, rationale: str):
        """Record decision with rationale.

        Args:
            decision: What was decided
            rationale: Why it was decided
        """
        self.state["recent_decisions"].append(
            {"decision": decision, "rationale": rationale, "timestamp": get_timestamp()}
        )
        self.state["session_metrics"]["total_decisions"] += 1
        self.save_state()

    def track_stakeholder_preference(self, stakeholder: str, preference: str):
        """Build stakeholder preference profile over time.

        Args:
            stakeholder: Stakeholder name/role
            preference: Observed preference or priority
        """
        if stakeholder not in self.state["stakeholder_context"]:
            self.state["stakeholder_context"][stakeholder] = []
            self.state["session_metrics"]["stakeholders_tracked"] += 1

        self.state["stakeholder_context"][stakeholder].append(
            {"preference": preference, "timestamp": get_timestamp()}
        )
        self.save_state()

    def set_focus(self, focus: str):
        """Set current focus area.

        Args:
            focus: Description of current focus
        """
        self.state["current_focus"] = focus
        self.save_state()

    def add_question(self, question: str, context: str = ""):
        """Add open question requiring resolution.

        Args:
            question: Question text
            context: Additional context
        """
        self.state["open_questions"].append(
            {
                "question": question,
                "context": context,
                "added_at": get_timestamp(),
                "status": "OPEN",
            }
        )
        self.save_state()

    def resolve_question(self, question_index: int, resolution: str):
        """Mark question as resolved.

        Args:
            question_index: Index of question (0-based)
            resolution: How it was resolved
        """
        if 0 <= question_index < len(self.state["open_questions"]):
            self.state["open_questions"][question_index]["status"] = "RESOLVED"
            self.state["open_questions"][question_index]["resolution"] = resolution
            self.state["open_questions"][question_index]["resolved_at"] = get_timestamp()
            self.state["session_metrics"]["questions_resolved"] += 1
            self.save_state()

    def add_action(self, description: str, priority: str = "MEDIUM"):
        """Add next action.

        Args:
            description: Action description
            priority: HIGH, MEDIUM, or LOW
        """
        self.state["next_actions"].append(
            {"description": description, "priority": priority, "added_at": get_timestamp()}
        )
        self.save_state()

    def clear_completed_actions(self):
        """Remove completed actions from list."""
        # In future, could track completion explicitly
        # For now, user manually manages via update

    def search_decisions(self, query: str) -> list[dict]:
        """Search past decisions by keyword.

        Args:
            query: Search term

        Returns:
            List of matching decisions
        """
        query_lower = query.lower()
        matches = []

        for decision in self.state["recent_decisions"]:
            decision_text = decision.get("decision", "").lower()
            rationale = decision.get("rationale", "").lower()

            if query_lower in decision_text or query_lower in rationale:
                matches.append(decision)

        return matches

    def get_stakeholder_profile(self, stakeholder: str) -> dict:
        """Get all preferences for a stakeholder.

        Args:
            stakeholder: Stakeholder name

        Returns:
            Profile with preferences and patterns
        """
        prefs = self.state["stakeholder_context"].get(stakeholder, [])
        return {"stakeholder": stakeholder, "total_preferences": len(prefs), "preferences": prefs}


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(description="Manage PM session state")
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Init command
    subparsers.add_parser("init", help="Initialize session state")

    # Update decision command
    decision_parser = subparsers.add_parser("update-decision", help="Record decision")
    decision_parser.add_argument("decision", help="What was decided")
    decision_parser.add_argument("rationale", help="Why it was decided")

    # Track preference command
    pref_parser = subparsers.add_parser("track-preference", help="Track stakeholder preference")
    pref_parser.add_argument("stakeholder", help="Stakeholder name")
    pref_parser.add_argument("preference", help="Preference observed")

    # Set focus command
    focus_parser = subparsers.add_parser("set-focus", help="Set current focus")
    focus_parser.add_argument("focus", help="Focus description")

    # Add question command
    question_parser = subparsers.add_parser("add-question", help="Add open question")
    question_parser.add_argument("question", help="Question text")
    question_parser.add_argument("--context", default="", help="Additional context")

    # Add action command
    action_parser = subparsers.add_parser("add-action", help="Add next action")
    action_parser.add_argument("description", help="Action description")
    action_parser.add_argument(
        "--priority", default="MEDIUM", choices=["HIGH", "MEDIUM", "LOW"], help="Action priority"
    )

    # Show command
    subparsers.add_parser("show", help="Show current state")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search decisions")
    search_parser.add_argument("query", help="Search term")

    args = parser.parse_args()

    try:
        pm_dir = args.project_root / ".pm"
        if not pm_dir.exists():
            print(json.dumps({"error": "PM not initialized"}), file=sys.stderr)
            return 1

        state = PMSessionState(pm_dir)

        if args.command == "init":
            state.save_state()
            print(json.dumps({"status": "initialized", "file": str(state.state_file)}))

        elif args.command == "update-decision":
            state.update_decision(args.decision, args.rationale)
            print(json.dumps({"status": "recorded", "decision": args.decision}))

        elif args.command == "track-preference":
            state.track_stakeholder_preference(args.stakeholder, args.preference)
            print(json.dumps({"status": "tracked", "stakeholder": args.stakeholder}))

        elif args.command == "set-focus":
            state.set_focus(args.focus)
            print(json.dumps({"status": "updated", "focus": args.focus}))

        elif args.command == "add-question":
            state.add_question(args.question, args.context)
            print(json.dumps({"status": "added", "question": args.question}))

        elif args.command == "add-action":
            state.add_action(args.description, args.priority)
            print(json.dumps({"status": "added", "action": args.description}))

        elif args.command == "show":
            print(json.dumps(state.state, indent=2))

        elif args.command == "search":
            results = state.search_decisions(args.query)
            print(json.dumps({"query": args.query, "matches": len(results), "results": results}))

        return 0

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
