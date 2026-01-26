#!/usr/bin/env python3
"""Sync agent descriptions from .md files to bundle.md.

This script extracts descriptions from agent frontmatter and updates
the inline descriptions in bundle.md to keep them in sync.

Usage:
    python scripts/sync_agent_descriptions.py [--check] [--verbose]

Options:
    --check     Only check if sync is needed, don't modify files
    --verbose   Show detailed output
"""

import argparse
import sys
from pathlib import Path

import yaml


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content

    lines = content.split("\n")
    end_idx = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        return {}, content

    frontmatter_str = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :])

    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError:
        return {}, content

    return frontmatter, body


def extract_description(agent_file: Path) -> str | None:
    """Extract description from agent .md file."""
    try:
        content = agent_file.read_text()
        frontmatter, _ = parse_frontmatter(content)

        # Check meta.description (Amplifier convention) OR top-level description (amplihack)
        meta = frontmatter.get("meta", {})
        description = meta.get("description") or frontmatter.get("description", "")

        return description if description else None

    except Exception as e:
        print(f"Warning: Failed to read {agent_file.name}: {e}", file=sys.stderr)
        return None


def find_all_agents(agents_dir: Path) -> dict[str, str]:
    """Find all agent .md files and extract their descriptions.

    Returns:
        Dict mapping agent name to description
    """
    agents = {}

    for agent_file in agents_dir.rglob("*.md"):
        agent_name = agent_file.stem
        description = extract_description(agent_file)

        if description:
            agents[agent_name] = description

    return agents


def update_bundle_config(
    bundle_file: Path, agent_descriptions: dict[str, str], verbose: bool = False
) -> tuple[str, int]:
    """Update bundle.md with agent descriptions.

    Returns:
        Tuple of (updated_content, changes_count)
    """
    content = bundle_file.read_text()
    lines = content.split("\n")

    updated_lines = []
    changes = 0
    in_agents_section = False
    skip_until_next_agent = False
    current_multiline_agent = None
    current_indent = None

    for i, line in enumerate(lines):
        # Detect agents section
        if line.strip() == "agents:":
            in_agents_section = True
            updated_lines.append(line)
            continue

        # Exit agents section when we hit another top-level key
        if in_agents_section and line and not line.startswith(" ") and not line.startswith("\t"):
            in_agents_section = False
            current_multiline_agent = None

        if not in_agents_section:
            updated_lines.append(line)
            continue

        # Agent definition line: "  amplihack:agent-name:"
        if line.strip().startswith("amplihack:") and line.strip().endswith(":"):
            # Multi-line format agent
            agent_name = line.split(":")[1].strip().rstrip(":")
            current_indent = line[: len(line) - len(line.lstrip())]
            current_multiline_agent = agent_name
            updated_lines.append(line)
            continue

        # In multi-line agent, pass through path line without resetting tracking
        if current_multiline_agent and line.strip().startswith("path:"):
            updated_lines.append(line)
            continue

        # In multi-line agent, check for description line
        if current_multiline_agent and "description:" in line:
            expected_desc = agent_descriptions.get(current_multiline_agent)
            if expected_desc:
                # Extract current description from bundle
                current_desc = line.split("description:", 1)[1].strip().strip('"')

                if current_desc != expected_desc:
                    # Description changed, update it
                    escaped_desc = expected_desc.replace('"', '\\"')
                    updated_lines.append(f'{current_indent}  description: "{escaped_desc}"')
                    changes += 1
                    if verbose:
                        print(f"  ✓ Updated {current_multiline_agent}")
                else:
                    # Description matches, keep as-is
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

            # Done with this agent
            current_multiline_agent = None
            continue

        # Reset multi-line tracking only when we see another agent definition
        if (
            current_multiline_agent
            and line.strip().startswith("amplihack:")
            and line.strip().endswith(":")
        ):
            current_multiline_agent = None

        # Single-line format: "  amplihack:agent-name: { path: ... }"
        if (
            line.strip().startswith("amplihack:")
            and "{ path:" in line
            and "description:" not in line
        ):
            agent_full = line.split(":")[1].strip()
            agent_name = agent_full.split(":")[0] if ":" in agent_full else agent_full
            description = agent_descriptions.get(agent_name)

            if description:
                # Extract the path part
                path_part = line.split("{ path:")[1].split("}")[0].strip()
                indent = line[: len(line) - len(line.lstrip())]

                # Convert to multi-line format
                escaped_desc = description.replace('"', '\\"')
                updated_lines.append(f"{indent}amplihack:{agent_name}:")
                updated_lines.append(f"{indent}  path: {path_part}")
                updated_lines.append(f'{indent}  description: "{escaped_desc}"')

                changes += 1
                if verbose:
                    print(f"  ✓ Converted {agent_name} to multi-line")

                skip_until_next_agent = True
                continue
            else:
                updated_lines.append(line)
                skip_until_next_agent = False
        elif skip_until_next_agent:
            # Skip lines that were part of the old single-line format
            continue
        else:
            updated_lines.append(line)

    return "\n".join(updated_lines), changes


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Sync agent descriptions to bundle.md")
    parser.add_argument(
        "--check", action="store_true", help="Check if sync is needed without modifying"
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")

    args = parser.parse_args()

    # Paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    agents_dir = repo_root / "amplifier-bundle" / "agents"
    bundle_file = repo_root / "amplifier-bundle" / "bundle.md"

    if not agents_dir.exists():
        print(f"Error: Agents directory not found: {agents_dir}", file=sys.stderr)
        return 1

    if not bundle_file.exists():
        print(f"Error: Bundle file not found: {bundle_file}", file=sys.stderr)
        return 1

    # Extract descriptions from agent files
    if args.verbose:
        print(f"Scanning agents in {agents_dir}...")

    agent_descriptions = find_all_agents(agents_dir)

    if args.verbose:
        print(f"Found {len(agent_descriptions)} agents with descriptions\n")

    # Update bundle.md
    updated_content, changes = update_bundle_config(
        bundle_file, agent_descriptions, verbose=args.verbose
    )

    if changes == 0:
        print("✅ All agent descriptions are in sync")
        return 0

    if args.check:
        print(f"❌ {changes} agent descriptions need syncing")
        print("Run without --check to update bundle.md")
        return 1

    # Write updated content
    bundle_file.write_text(updated_content)
    print(f"✅ Updated {changes} agent descriptions in bundle.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
