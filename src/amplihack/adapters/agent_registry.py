"""Maintain manifest of converted agents for discovery.

Philosophy:
- Ruthless simplicity - JSON registry with clear structure
- Zero-BS - registry generation works or doesn't exist
- Self-contained and regeneratable
- No external dependencies beyond stdlib

Public API (the "studs"):
    AgentRegistryEntry: Single agent in registry
    create_registry: Generate registry from conversions
    write_registry: Write registry to JSON file
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal


@dataclass
class AgentRegistryEntry:
    """Single agent in registry.

    Attributes:
        name: Agent name
        description: Agent description
        category: Agent category (core, specialized, workflow)
        source_path: Original path in .claude/agents/
        target_path: Converted path in .github/agents/
        triggers: Trigger keywords for agent discovery
        version: Agent version
    """
    name: str
    description: str
    category: Literal["core", "specialized", "workflow"]
    source_path: str
    target_path: str
    triggers: List[str]
    version: str


def categorize_agent(source_path: Path) -> Literal["core", "specialized", "workflow"]:
    """Categorize agent based on source path.

    Categories:
    - core: .claude/agents/amplihack/core/*.md
    - specialized: .claude/agents/amplihack/specialized/*.md
    - workflow: .claude/agents/amplihack/workflows/*.md

    Args:
        source_path: Path to agent file in .claude/agents/

    Returns:
        Category name

    Example:
        >>> categorize_agent(Path(".claude/agents/amplihack/core/architect.md"))
        'core'
        >>> categorize_agent(Path(".claude/agents/amplihack/specialized/fix-agent.md"))
        'specialized'
    """
    path_str = str(source_path)

    if "/core/" in path_str:
        return "core"
    elif "/specialized/" in path_str:
        return "specialized"
    elif "/workflow" in path_str:
        return "workflow"
    else:
        # Default to specialized for uncategorized agents
        return "specialized"


def generate_usage_examples(agent_name: str, category: str) -> List[str]:
    """Generate usage examples for agent.

    Args:
        agent_name: Name of the agent
        category: Category of the agent

    Returns:
        List of usage example commands

    Example:
        >>> generate_usage_examples("architect", "core")
        ['copilot -p "Include @.github/agents/core/architect.md -- Design a REST API"', ...]
    """
    examples = []

    # Basic usage
    examples.append(
        f'copilot -p "Include @.github/agents/{category}/{agent_name}.md -- '
        f'Your task here"'
    )

    # Shortened @agent syntax if supported
    examples.append(
        f'copilot -p "/agent {agent_name} -- Your task here"'
    )

    return examples


def create_registry(
    entries: List[AgentRegistryEntry],
    source_dir: str = ".claude/agents",
    target_dir: str = ".github/agents"
) -> Dict[str, Any]:
    """Create agent registry from entries.

    Args:
        entries: List of agent registry entries
        source_dir: Source directory path
        target_dir: Target directory path

    Returns:
        Registry dictionary ready for JSON serialization

    Example:
        >>> entries = [
        ...     AgentRegistryEntry(
        ...         name="architect",
        ...         description="System design agent",
        ...         category="core",
        ...         source_path=".claude/agents/core/architect.md",
        ...         target_path=".github/agents/core/architect.md",
        ...         triggers=["architect", "design"],
        ...         version="1.0.0"
        ...     )
        ... ]
        >>> registry = create_registry(entries)
        >>> registry["version"]
        '1.0.0'
        >>> "core" in registry["categories"]
        True
    """
    # Group entries by category
    categories: Dict[str, List[Dict[str, Any]]] = {
        "core": [],
        "specialized": [],
        "workflow": []
    }

    usage_examples: Dict[str, List[str]] = {}

    for entry in entries:
        # Add entry to appropriate category
        entry_dict = asdict(entry)
        categories[entry.category].append(entry_dict)

        # Generate usage examples
        usage_examples[entry.name] = generate_usage_examples(
            entry.name,
            entry.category
        )

    # Create registry structure
    registry = {
        "version": "1.0.0",
        "generated": datetime.utcnow().isoformat() + "Z",
        "source": source_dir,
        "target": target_dir,
        "total_agents": len(entries),
        "categories": categories,
        "usage_examples": usage_examples
    }

    return registry


def write_registry(registry: Dict[str, Any], output_path: Path) -> None:
    """Write registry to JSON file.

    Args:
        registry: Registry dictionary
        output_path: Path to write JSON file

    Raises:
        OSError: If file cannot be written

    Example:
        >>> registry = {"version": "1.0.0", "categories": {}}
        >>> write_registry(registry, Path(".github/agents/REGISTRY.json"))
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise OSError(
            f"Failed to write registry to {output_path}\n"
            f"Error: {str(e)}\n"
            f"Fix: Check directory permissions and disk space"
        )


__all__ = [
    "AgentRegistryEntry",
    "categorize_agent",
    "create_registry",
    "write_registry",
]
