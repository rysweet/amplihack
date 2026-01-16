"""Adapt Claude Code agents for GitHub Copilot CLI compatibility.

Philosophy:
- Ruthless simplicity - direct transformations
- Zero-BS - every adaptation works or doesn't exist
- Preserve agent semantics - only change invocation patterns
- Self-contained and regeneratable

Public API (the "studs"):
    adapt_agent_for_copilot: Full agent adaptation
    adapt_frontmatter: Transform frontmatter format
    adapt_instructions: Adapt agent instructions
"""

import re
from typing import Any, Dict, List

from .agent_parser import AgentDocument


def adapt_frontmatter(frontmatter: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Claude frontmatter to Copilot format.

    Transformations:
    1. Combine description + role into single description
    2. Extract/generate triggers from description
    3. Remove model field (Copilot doesn't support)
    4. Preserve name and version

    Args:
        frontmatter: Claude Code frontmatter dictionary

    Returns:
        Copilot-compatible frontmatter dictionary

    Example:
        >>> fm = {
        ...     "name": "architect",
        ...     "description": "System design agent",
        ...     "role": "Architect specialist",
        ...     "model": "inherit",
        ...     "version": "1.0.0"
        ... }
        >>> adapted = adapt_frontmatter(fm)
        >>> adapted["description"]
        'System design agent. Architect specialist.'
        >>> "model" in adapted
        False
    """
    adapted = {}

    # Copy name (required)
    adapted["name"] = frontmatter["name"]

    # Combine description + role
    description_parts = []
    if "description" in frontmatter:
        description_parts.append(frontmatter["description"])
    if "role" in frontmatter:
        description_parts.append(frontmatter["role"])

    adapted["description"] = ". ".join(description_parts) if description_parts else ""

    # Extract or generate triggers
    triggers = _extract_triggers(adapted["name"], adapted["description"])
    adapted["triggers"] = triggers

    # Copy version if present
    if "version" in frontmatter:
        adapted["version"] = frontmatter["version"]

    # Note: model field is intentionally dropped (Copilot doesn't support)

    return adapted


def _extract_triggers(name: str, description: str) -> List[str]:
    """Extract trigger keywords from agent name and description.

    Args:
        name: Agent name
        description: Agent description

    Returns:
        List of trigger keywords

    Example:
        >>> _extract_triggers("architect", "System design and architecture")
        ['architect', 'system design', 'architecture']
    """
    triggers = []

    # Always include the agent name
    triggers.append(name)

    # Common trigger patterns from description
    description_lower = description.lower()

    # Extract key phrases (simplified heuristic)
    trigger_patterns = [
        r'\b(architect|architecture|design)\b',
        r'\b(build|builder|implementation)\b',
        r'\b(review|reviewer|code review)\b',
        r'\b(test|tester|testing)\b',
        r'\b(optimize|optimizer|performance)\b',
        r'\b(security|secure)\b',
        r'\b(database|db|data)\b',
        r'\b(api|rest|graphql)\b',
        r'\b(fix|debug|troubleshoot)\b',
    ]

    for pattern in trigger_patterns:
        matches = re.findall(pattern, description_lower)
        for match in matches:
            if match not in triggers:
                triggers.append(match)

    # Limit to 5 most relevant triggers
    return triggers[:5]


def adapt_instructions(body: str) -> str:
    """Adapt agent instructions for Copilot CLI patterns.

    Transformations:
    1. Task tool → subagent invocation pattern
    2. TodoWrite → state file updates
    3. @.claude/ references → Include @.claude/
    4. Skill tool → MCP server call
    5. /command references → .github/agents/ references

    Args:
        body: Agent markdown body

    Returns:
        Adapted markdown body with Copilot patterns

    Example:
        >>> body = "Use Task tool to invoke architect"
        >>> adapted = adapt_instructions(body)
        >>> "Task tool" not in adapted
        >>> "subagent" in adapted
        True
    """
    adapted = body

    # Transform Task tool references
    adapted = _adapt_task_tool(adapted)

    # Transform TodoWrite references
    adapted = _adapt_todowrite(adapted)

    # Transform context references
    adapted = _adapt_context_references(adapted)

    # Transform Skill tool references
    adapted = _adapt_skill_tool(adapted)

    # Transform command references
    adapted = _adapt_command_references(adapted)

    return adapted


def _adapt_task_tool(body: str) -> str:
    """Transform Task tool references to subagent patterns."""
    # Pattern: Task tool -> subagent invocation
    patterns = [
        (r'\bTask tool\b', 'subagent invocation'),
        (r'\bTask\(subagent_type=([^)]+)\)', r'invoke @.github/agents/\1'),
        (r'invoke.*Task\s+tool', 'invoke subagent'),
    ]

    adapted = body
    for pattern, replacement in patterns:
        adapted = re.sub(pattern, replacement, adapted, flags=re.IGNORECASE)

    return adapted


def _adapt_todowrite(body: str) -> str:
    """Transform TodoWrite references to state file updates."""
    # Pattern: TodoWrite -> state file updates in .claude/runtime/
    patterns = [
        (r'\bTodoWrite\b', 'state file updates in .claude/runtime/'),
        (r'\bTodoWrite\([^)]+\)', 'update .claude/runtime/state files'),
    ]

    adapted = body
    for pattern, replacement in patterns:
        adapted = re.sub(pattern, replacement, adapted)

    return adapted


def _adapt_context_references(body: str) -> str:
    """Transform context references to explicit includes."""
    # Pattern: @.claude/context/FILE.md -> Include @.claude/context/FILE.md
    # Already explicit references are fine, just ensure "Include" prefix

    # Find lines with @.claude/ that don't start with "Include"
    lines = body.split('\n')
    adapted_lines = []

    for line in lines:
        # Only add "Include" if the line is ONLY the reference (not embedded in text)
        stripped = line.strip()
        if stripped.startswith('@.claude/') and not line.strip().startswith('Include @'):
            # Add "Include" prefix
            indent = len(line) - len(line.lstrip())
            line = ' ' * indent + f"Include {stripped}"

        adapted_lines.append(line)

    return '\n'.join(adapted_lines)


def _adapt_skill_tool(body: str) -> str:
    """Transform Skill tool references to MCP server calls."""
    # Pattern: Skill tool -> MCP server call
    patterns = [
        (r'\bSkill tool\b', 'MCP server call'),
        (r'\bSkill\([^)]+\)', 'call MCP server'),
        (r'invoke.*Skill', 'invoke MCP server'),
    ]

    adapted = body
    for pattern, replacement in patterns:
        adapted = re.sub(pattern, replacement, adapted, flags=re.IGNORECASE)

    return adapted


def _adapt_command_references(body: str) -> str:
    """Transform command references to agent references."""
    # Pattern: /command-name -> reference to .github/agents/
    # This is subtle - commands don't exist in Copilot, so we guide to agents
    # BUT: Preserve @.claude/ and other @ prefixed paths

    # Find /command patterns (but not in URLs or @ references)
    # Negative lookbehind for : (URLs) or @ (file references)
    pattern = r'(?<![@:])\/([a-z-]+)'

    def replace_command(match):
        command_name = match.group(1)
        # Skip common false positives
        if command_name in ['http', 'https', 'ftp', 'usr', 'bin', 'etc', 'claude', 'context']:
            return match.group(0)
        return f'@.github/agents/{command_name}'

    adapted = re.sub(pattern, replace_command, body)

    return adapted


def adapt_agent_for_copilot(agent: AgentDocument) -> AgentDocument:
    """Adapt complete Claude agent for Copilot CLI compatibility.

    Args:
        agent: Parsed Claude Code agent document

    Returns:
        Adapted agent document for Copilot CLI

    Example:
        >>> from pathlib import Path
        >>> agent = parse_agent(Path(".claude/agents/core/architect.md"))
        >>> adapted = adapt_agent_for_copilot(agent)
        >>> "triggers" in adapted.frontmatter
        True
    """
    adapted_frontmatter = adapt_frontmatter(agent.frontmatter)
    adapted_body = adapt_instructions(agent.body)

    return AgentDocument(
        frontmatter=adapted_frontmatter,
        body=adapted_body,
        source_path=agent.source_path
    )


__all__ = [
    "adapt_agent_for_copilot",
    "adapt_frontmatter",
    "adapt_instructions",
]
