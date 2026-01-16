"""Agent adapter system for converting Claude agents to Copilot format.

Philosophy:
- Ruthless simplicity - direct conversion with clear rules
- Zero-BS - every function works
- Regeneratable - can rebuild .github/agents/ from .claude/agents/
- Self-contained module

Public API (the "studs"):
    From agent_parser:
        AgentDocument: Parsed agent structure
        parse_agent: Parse agent markdown file
        has_frontmatter: Check for YAML frontmatter

    From agent_adapter:
        adapt_agent_for_copilot: Full agent adaptation
        adapt_frontmatter: Transform frontmatter format
        adapt_instructions: Adapt agent instructions

    From agent_registry:
        AgentRegistryEntry: Single agent in registry
        categorize_agent: Categorize agent by path
        create_registry: Generate registry from conversions
        write_registry: Write registry to JSON file

    From copilot_agent_converter:
        ConversionReport: Results of conversion operation
        AgentConversion: Single agent conversion result
        convert_agents: Convert all agents
        convert_single_agent: Convert one agent
        validate_agent: Validate agent structure
        is_agents_synced: Check if agents are in sync
"""

from .agent_parser import (
    AgentDocument,
    parse_agent,
    has_frontmatter,
)

from .agent_adapter import (
    adapt_agent_for_copilot,
    adapt_frontmatter,
    adapt_instructions,
)

from .agent_registry import (
    AgentRegistryEntry,
    categorize_agent,
    create_registry,
    write_registry,
)

from .copilot_agent_converter import (
    ConversionReport,
    AgentConversion,
    convert_agents,
    convert_single_agent,
    validate_agent,
    is_agents_synced,
)

__all__ = [
    # Parser
    "AgentDocument",
    "parse_agent",
    "has_frontmatter",
    # Adapter
    "adapt_agent_for_copilot",
    "adapt_frontmatter",
    "adapt_instructions",
    # Registry
    "AgentRegistryEntry",
    "categorize_agent",
    "create_registry",
    "write_registry",
    # Converter
    "ConversionReport",
    "AgentConversion",
    "convert_agents",
    "convert_single_agent",
    "validate_agent",
    "is_agents_synced",
]
