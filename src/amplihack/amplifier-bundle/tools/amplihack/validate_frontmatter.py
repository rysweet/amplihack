#!/usr/bin/env python3
"""Validate frontmatter across amplihack components."""

import sys
from pathlib import Path

import yaml

# Required fields by type
REQUIRED_FIELDS = {
    "workflow": ["name", "version", "description", "phases"],
    "command": ["name", "version", "description", "triggers"],
    "skill": ["name", "version", "description"],
    "agent": ["name", "version", "description", "role"],
}


def validate_file(path: Path, component_type: str) -> list[str]:
    """Validate frontmatter in a single file."""
    errors = []

    # Read file
    content = path.read_text()

    # Extract frontmatter
    if not content.startswith("---"):
        return ["Missing frontmatter delimiter"]

    parts = content.split("---", 2)
    if len(parts) < 3:
        return ["Incomplete frontmatter"]

    # Parse YAML
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        return [f"Invalid YAML: {e}"]

    # Check required fields
    for field in REQUIRED_FIELDS.get(component_type, []):
        if field not in fm:
            errors.append(f"Missing required field: {field}")

    # Validate version format
    if "version" in fm:
        version = str(fm["version"])
        parts_v = version.split(".")
        if len(parts_v) != 3 or not all(p.isdigit() for p in parts_v):
            errors.append(f"Invalid version format: {version} (expected X.Y.Z)")

    return errors


def main():
    """Run validation on all components."""
    all_errors = {}

    # Find all files
    workflows = list(Path(".claude/workflow").glob("*.md"))
    commands = list(Path(".claude/commands").rglob("*.md"))
    skills = list(Path(".claude/skills").glob("*/SKILL.md"))
    agents = list(Path(".claude/agents").rglob("*.md"))

    # Validate each
    for wf in workflows:
        if wf.name == "README.md":
            continue
        errors = validate_file(wf, "workflow")
        if errors:
            all_errors[str(wf)] = errors

    for cmd in commands:
        if "README" in cmd.name:
            continue
        errors = validate_file(cmd, "command")
        if errors:
            all_errors[str(cmd)] = errors

    for skill in skills:
        errors = validate_file(skill, "skill")
        if errors:
            all_errors[str(skill)] = errors

    for agent in agents:
        if "README" in agent.name or "CATALOG" in agent.name:
            continue
        errors = validate_file(agent, "agent")
        if errors:
            all_errors[str(agent)] = errors

    # Report
    if not all_errors:
        print("✓ All frontmatter valid!")
        return 0

    print(f"✗ Found errors in {len(all_errors)} files:\n")
    for path, errors in all_errors.items():
        print(f"{path}:")
        for error in errors:
            print(f"  - {error}")
        print()

    # Summary statistics
    total_files = len(workflows) + len(commands) + len(skills) + len(agents)
    total_files -= sum(1 for _ in workflows if _.name == "README.md")
    total_files -= sum(1 for _ in commands if "README" in _.name)
    total_files -= sum(1 for _ in agents if "README" in _.name or "CATALOG" in _.name)

    print(f"Summary: {len(all_errors)}/{total_files} files with errors")

    return 1


if __name__ == "__main__":
    sys.exit(main())
