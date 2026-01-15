"""Parse amplihack agent markdown files with YAML frontmatter.

Philosophy:
- Ruthless simplicity - straightforward YAML parsing
- Zero-BS - every function works or doesn't exist
- Standard library only (yaml is standard enough)
- Self-contained and regeneratable

Public API (the "studs"):
    AgentDocument: Parsed agent structure
    parse_agent: Parse agent markdown file
    has_frontmatter: Check for YAML frontmatter
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class AgentDocument:
    """Parsed agent document with frontmatter and body.

    Attributes:
        frontmatter: Parsed YAML frontmatter as dictionary
        body: Markdown content after frontmatter
        source_path: Original file path
    """
    frontmatter: Dict[str, Any]
    body: str
    source_path: Path


def has_frontmatter(content: str) -> bool:
    """Check if content has YAML frontmatter.

    Frontmatter is detected by:
    - Starts with '---'
    - Has closing '---'
    - Content between markers

    Args:
        content: File content to check

    Returns:
        True if valid frontmatter detected

    Example:
        >>> has_frontmatter("---\\nname: test\\n---\\nContent")
        True
        >>> has_frontmatter("No frontmatter here")
        False
    """
    if not content.strip():
        return False

    # Must start with --- at beginning of file
    if not content.lstrip().startswith("---"):
        return False

    # Find closing ---
    lines = content.split("\n")
    if len(lines) < 3:  # Need at least ---, content, ---
        return False

    # Skip first --- and look for closing ---
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            start_idx = i
            break

    # Look for closing ---
    for i in range(start_idx + 1, len(lines)):
        if lines[i].strip() == "---":
            return True

    return False


def parse_agent(agent_path: Path) -> AgentDocument:
    """Parse agent markdown file with YAML frontmatter.

    Args:
        agent_path: Path to agent markdown file

    Returns:
        AgentDocument with parsed frontmatter and body

    Raises:
        FileNotFoundError: If agent file doesn't exist
        ValueError: If frontmatter is invalid or missing required fields
        yaml.YAMLError: If YAML parsing fails

    Example:
        >>> agent = parse_agent(Path(".claude/agents/core/architect.md"))
        >>> agent.frontmatter["name"]
        'architect'
    """
    if not agent_path.exists():
        raise FileNotFoundError(
            f"Agent file not found: {agent_path}\n"
            f"Ensure the path is correct and file exists"
        )

    content = agent_path.read_text(encoding="utf-8")

    if not has_frontmatter(content):
        raise ValueError(
            f"Agent file missing YAML frontmatter: {agent_path}\n"
            f"Frontmatter must start with '---' and end with '---'\n"
            f"Example:\n"
            f"---\n"
            f"name: agent-name\n"
            f"description: Agent description\n"
            f"---\n"
            f"\n"
            f"Agent content here..."
        )

    # Split frontmatter and body
    lines = content.split("\n")

    # Find frontmatter boundaries
    start_idx = -1
    end_idx = -1

    for i, line in enumerate(lines):
        if line.strip() == "---":
            if start_idx == -1:
                start_idx = i
            else:
                end_idx = i
                break

    if start_idx == -1 or end_idx == -1:
        raise ValueError(
            f"Invalid frontmatter format in {agent_path}\n"
            f"Could not find opening and closing '---' markers"
        )

    # Extract frontmatter and body
    frontmatter_lines = lines[start_idx + 1:end_idx]
    body_lines = lines[end_idx + 1:]

    frontmatter_text = "\n".join(frontmatter_lines)
    body = "\n".join(body_lines).strip()

    # Parse YAML
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        raise ValueError(
            f"Invalid YAML in agent frontmatter: {agent_path}\n"
            f"Error: {str(e)}\n"
            f"Fix: Ensure frontmatter has valid YAML between '---' markers\n"
            f"Common issues:\n"
            f"  - Unquoted colons in values (use quotes)\n"
            f"  - Incorrect indentation\n"
            f"  - Missing spaces after colons"
        )

    if frontmatter is None:
        frontmatter = {}

    # Validate required fields
    if "name" not in frontmatter:
        raise ValueError(
            f"Agent frontmatter missing 'name' field: {agent_path}\n"
            f"Required fields: name, description\n"
            f"Example:\n"
            f"---\n"
            f"name: my-agent\n"
            f"description: What this agent does\n"
            f"---"
        )

    if "description" not in frontmatter:
        raise ValueError(
            f"Agent frontmatter missing 'description' field: {agent_path}\n"
            f"Required fields: name, description\n"
            f"Example:\n"
            f"---\n"
            f"name: my-agent\n"
            f"description: What this agent does\n"
            f"---"
        )

    return AgentDocument(
        frontmatter=frontmatter,
        body=body,
        source_path=agent_path
    )


__all__ = ["AgentDocument", "parse_agent", "has_frontmatter"]
