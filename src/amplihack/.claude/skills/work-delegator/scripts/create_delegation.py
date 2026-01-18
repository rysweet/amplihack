#!/usr/bin/env python3
"""Create rich delegation package for backlog item.

Usage:
    python create_delegation.py BACKLOG_ID [--project-root PATH] [--agent AGENT]

Returns JSON delegation package with comprehensive context.
"""

import argparse
import json
import re
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
    if any(kw in text for kw in ["document", "docs", "readme", "comment"]):
        return "documentation"
    if any(kw in text for kw in ["refactor", "clean", "improve", "optimize"]):
        return "refactor"
    if any(kw in text for kw in ["add", "implement", "create", "new", "feature"]):
        return "feature"

    return "other"


def estimate_complexity(item: dict) -> str:
    """Estimate complexity."""
    hours = item.get("estimated_hours", 4)
    if hours < 2:
        return "simple"
    if hours <= 6:
        return "medium"
    return "complex"


def find_relevant_files(item: dict, project_root: Path, max_files: int = 10) -> list[str]:
    """Find files relevant to backlog item."""
    # Extract keywords from title/description
    text = item.get("title", "") + " " + item.get("description", "")
    words = re.findall(r"\b\w{3,}\b", text.lower())
    keywords = set(words) - {"the", "and", "for", "with", "from", "this", "that"}

    relevant = []

    # Search Python files in common locations
    search_paths = [
        project_root / "src",
        project_root / ".claude" / "tools",
        project_root / "tests",
    ]

    for search_path in search_paths:
        if not search_path.exists():
            continue

        for py_file in search_path.rglob("*.py"):
            # Check if filename or parent dir matches keywords
            file_parts = py_file.stem.lower().split("_")
            if any(kw in file_parts for kw in keywords):
                try:
                    rel_path = py_file.relative_to(project_root)
                    relevant.append(str(rel_path))
                except ValueError:
                    pass

    return relevant[:max_files]


def find_similar_patterns(item: dict, category: str) -> list[str]:
    """Find similar code patterns (guidance)."""
    patterns = []

    if category == "feature":
        patterns.extend(
            [
                "Look for similar feature implementations in src/",
                "Check existing tests for pattern examples",
                "Follow existing code organization patterns",
            ]
        )
    elif category == "bug":
        patterns.extend(
            [
                "Search for similar error handling patterns",
                "Look for existing fixes to similar issues",
                "Check test suite for regression test patterns",
            ]
        )
    elif category == "test":
        patterns.extend(
            [
                "Review existing test structure in tests/",
                "Check conftest.py for fixture patterns",
                "Match current test naming conventions",
            ]
        )
    elif category == "refactor":
        patterns.extend(
            [
                "Ensure all existing tests still pass",
                "Follow current architectural patterns",
                "Maintain backward compatibility",
            ]
        )
    else:
        patterns.extend(
            [
                "Follow existing code organization patterns",
                "Match current naming conventions",
                "Adhere to project philosophy (ruthless simplicity)",
            ]
        )

    return patterns[:5]


def generate_test_requirements(category: str) -> list[str]:
    """Generate test requirements based on category."""
    if category == "feature":
        return [
            "Unit tests for new functions/classes",
            "Integration tests for feature workflow",
            "Edge case coverage (empty inputs, invalid data)",
            "Test success and error paths",
        ]
    if category == "bug":
        return [
            "Regression test that fails before fix",
            "Test passes after fix",
            "Test edge cases related to bug",
        ]
    if category == "refactor":
        return [
            "All existing tests still pass",
            "No behavior changes",
            "Code coverage maintained or improved",
        ]
    if category == "test":
        return [
            "Tests cover stated requirements",
            "Tests are maintainable and clear",
            "Tests run quickly (< 1s per test)",
        ]
    return [
        "Add tests appropriate for changes",
        "Ensure existing tests pass",
    ]


def generate_architectural_notes(item: dict, category: str, complexity: str) -> str:
    """Generate architectural guidance."""
    notes = []

    # Complexity-based
    if complexity == "simple":
        notes.append("Keep it simple - single file or function if possible")
    elif complexity == "complex":
        notes.append("Break into smaller, testable components")
        notes.append("Consider creating module structure with clear contracts")

    # Category-specific
    if category == "feature":
        notes.append("Follow existing patterns in codebase")
        notes.append("Consider extension points for future needs")
    elif category == "refactor":
        notes.append("Maintain backward compatibility unless explicitly removing")
        notes.append("Make changes incrementally if possible")

    return "\n".join(f"- {note}" for note in notes)


def generate_agent_instructions(agent: str, category: str) -> str:
    """Generate agent-specific instructions."""
    templates = {
        "builder": """1. Analyze requirements and examine relevant files listed below
2. Design solution following existing patterns
3. Implement working code (no stubs or placeholders)
4. Add comprehensive tests per test requirements
5. Follow architectural notes
6. Update documentation

Focus on ruthless simplicity. Start with simplest solution that works.""",
        "reviewer": """1. Review code for philosophy compliance
2. Verify no stubs, placeholders, or dead code
3. Check test coverage against requirements
4. Validate architectural notes followed
5. Look for unnecessary complexity
6. Ensure documentation updated

Focus on ruthless simplicity and zero-BS implementation.""",
        "tester": """1. Analyze behavior and contracts
2. Review test requirements below
3. Design tests for edge cases
4. Implement comprehensive coverage
5. Verify all tests pass
6. Document test scenarios

Focus on testing behavior, not implementation details.""",
    }

    base = templates.get(agent, "Complete task following project philosophy")

    # Add category-specific guidance
    if category == "bug":
        base += "\n\n**Bug Fix Workflow**: Write failing test first, then fix, verify test passes."
    elif category == "refactor":
        base += (
            "\n\n**Refactor Workflow**: Ensure tests pass before and after. No behavior changes."
        )

    return base


def load_project_context(project_root: Path) -> str:
    """Load project context from config and roadmap."""
    pm_dir = project_root / ".pm"
    config = load_yaml(pm_dir / "config.yaml")

    context = f"""**Project**: {config.get("project_name", "Unknown")}
**Type**: {config.get("project_type", "other")}
**Quality Bar**: {config.get("quality_bar", "balanced")}

**Primary Goals**:
"""

    for goal in config.get("primary_goals", []):
        context += f"- {goal}\n"

    # Add roadmap snippet
    roadmap_path = pm_dir / "roadmap.md"
    if roadmap_path.exists():
        roadmap = roadmap_path.read_text()
        context += f"\n**Roadmap Summary**:\n{roadmap[:500]}..."

    return context


def create_delegation_package(backlog_id: str, project_root: Path, agent: str = "builder") -> dict:
    """Create comprehensive delegation package."""
    pm_dir = project_root / ".pm"

    # Load backlog
    backlog_data = load_yaml(pm_dir / "backlog" / "items.yaml")
    items = backlog_data.get("items", [])

    # Find backlog item
    item = next((i for i in items if i["id"] == backlog_id), None)
    if not item:
        raise ValueError(f"Backlog item {backlog_id} not found")

    # Analyze item
    category = categorize_item(item)
    complexity = estimate_complexity(item)
    relevant_files = find_relevant_files(item, project_root)
    similar_patterns = find_similar_patterns(item, category)
    test_requirements = generate_test_requirements(category)
    arch_notes = generate_architectural_notes(item, category, complexity)
    instructions = generate_agent_instructions(agent, category)
    project_context = load_project_context(project_root)

    # Success criteria
    success_criteria = [
        "All requirements implemented and working",
        "Tests pass (if applicable)",
        "Code follows project philosophy (ruthless simplicity)",
        "No stubs or placeholders",
        "Documentation updated",
    ]

    return {
        "backlog_item": {
            "id": item["id"],
            "title": item["title"],
            "description": item.get("description", ""),
            "priority": item.get("priority", "MEDIUM"),
            "estimated_hours": item.get("estimated_hours", 4),
            "tags": item.get("tags", []),
        },
        "agent_role": agent,
        "category": category,
        "complexity": complexity,
        "project_context": project_context,
        "instructions": instructions,
        "relevant_files": relevant_files,
        "similar_patterns": similar_patterns,
        "test_requirements": test_requirements,
        "architectural_notes": arch_notes,
        "success_criteria": success_criteria,
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create delegation package for backlog item")
    parser.add_argument("backlog_id", help="Backlog item ID (e.g., BL-001)")
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )
    parser.add_argument("--agent", default="builder", help="Agent role (builder, reviewer, tester)")

    args = parser.parse_args()

    try:
        package = create_delegation_package(args.backlog_id, args.project_root, args.agent)
        print(json.dumps(package, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
