#!/usr/bin/env python3
"""Shared logic for integrating Neo4j memory with agent execution.

This module provides utilities for:
1. Detecting agent references in prompts (@.claude/agents/*.md)
2. Injecting relevant memory context before agent execution
3. Extracting and storing learnings after agent execution

Integration Points:
- user_prompt_submit: Inject memory context when agent detected
- stop: Extract learnings from conversation after agent execution
"""

import logging
import re
import sys
from pathlib import Path
from typing import Any

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

logger = logging.getLogger(__name__)


# Agent reference patterns
AGENT_REFERENCE_PATTERNS = [
    r"@\.claude/agents/amplihack/[^/]+/([^/]+)\.md",  # @.claude/agents/amplihack/core/architect.md
    r"@\.claude/agents/([^/]+)\.md",  # @.claude/agents/architect.md
    r"Include\s+@\.claude/agents/[^/]+/([^/]+)\.md",  # Include @.claude/agents/...
    r"Use\s+([a-z-]+)\.md\s+agent",  # Use architect.md agent
    r"/([a-z-]+)\s",  # Slash commands that invoke agents (e.g., /ultrathink, /fix)
]

# Map slash commands to agent types
SLASH_COMMAND_AGENTS = {
    "ultrathink": "orchestrator",
    "fix": "fix-agent",
    "analyze": "analyzer",
    "improve": "reviewer",
    "socratic": "ambiguity",
    "debate": "multi-agent-debate",
    "reflect": "reflection",
    "xpia": "xpia-defense",
}


def detect_agent_references(prompt: str) -> list[str]:
    """Detect agent references in a prompt.

    Args:
        prompt: The user prompt to analyze

    Returns:
        List of agent type names detected (e.g., ["architect", "builder"])
    """
    agents = set()

    # Check each pattern
    for pattern in AGENT_REFERENCE_PATTERNS:
        matches = re.finditer(pattern, prompt, re.IGNORECASE)
        for match in matches:
            agent_name = match.group(1).lower()
            # Normalize agent names
            agent_name = agent_name.replace("_", "-")
            agents.add(agent_name)

    return list(agents)


def detect_slash_command_agent(prompt: str) -> str | None:
    """Detect if prompt starts with a slash command that invokes an agent.

    Args:
        prompt: The user prompt to analyze

    Returns:
        Agent type name if slash command detected, None otherwise
    """
    # Check if prompt starts with a slash command
    prompt_clean = prompt.strip()
    if not prompt_clean.startswith("/"):
        return None

    # Extract command name
    match = re.match(r"^/([a-z-]+)", prompt_clean)
    if not match:
        return None

    command = match.group(1)
    return SLASH_COMMAND_AGENTS.get(command)


def inject_memory_for_agents(
    prompt: str, agent_types: list[str], session_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    """Inject memory context for detected agents into prompt.

    Args:
        prompt: Original user prompt
        agent_types: List of agent types detected
        session_id: Optional session ID for logging

    Returns:
        Tuple of (enhanced_prompt, metadata_dict)
    """
    if not agent_types:
        return prompt, {}

    try:
        # Import memory integration (lazy import to avoid startup overhead)
        from amplihack.memory.neo4j.agent_integration import (
            detect_agent_type,
            inject_memory_context,
        )
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        # Check if Neo4j is available
        if not ensure_neo4j_running(blocking=False):
            logger.warning("Neo4j not available for memory injection")
            return prompt, {"neo4j_available": False}

        # Inject memory for each agent type
        memory_sections = []
        metadata = {"agents": agent_types, "memories_injected": 0, "neo4j_available": True}

        for agent_type in agent_types:
            # Normalize agent type
            normalized_type = detect_agent_type(agent_type)
            if not normalized_type:
                logger.debug(f"Unknown agent type: {agent_type}")
                continue

            # Get memory context for this agent
            try:
                memory_context = inject_memory_context(
                    agent_type=normalized_type,
                    task=prompt[:500],  # Use first 500 chars as task description
                    max_memories=5,
                )

                if memory_context:
                    memory_sections.append(
                        f"\n## Memory for {normalized_type} Agent\n{memory_context}"
                    )
                    metadata["memories_injected"] += 1

            except Exception as e:
                logger.warning(f"Failed to inject memory for {normalized_type}: {e}")
                continue

        # Build enhanced prompt
        if memory_sections:
            enhanced_prompt = "\n".join(memory_sections) + "\n\n---\n\n" + prompt
            return enhanced_prompt, metadata

        return prompt, metadata

    except ImportError as e:
        logger.warning(f"Memory integration not available: {e}")
        return prompt, {"neo4j_available": False, "error": "import_failed"}

    except Exception as e:
        logger.error(f"Failed to inject memory: {e}")
        return prompt, {"neo4j_available": False, "error": str(e)}


def extract_learnings_from_conversation(
    conversation_text: str, agent_types: list[str], session_id: str | None = None
) -> dict[str, Any]:
    """Extract and store learnings from conversation after agent execution.

    Args:
        conversation_text: Full conversation text (including agent responses)
        agent_types: List of agent types that were involved
        session_id: Optional session ID for tracking

    Returns:
        Metadata about learnings stored
    """
    if not agent_types:
        return {"learnings_stored": 0, "agents": []}

    try:
        # Import memory integration (lazy import)
        from amplihack.memory.neo4j.agent_integration import (
            detect_agent_type,
            extract_and_store_learnings,
        )
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        # Check if Neo4j is available
        if not ensure_neo4j_running(blocking=False):
            logger.warning("Neo4j not available for learning extraction")
            return {"neo4j_available": False, "learnings_stored": 0}

        # Extract and store learnings for each agent
        metadata = {
            "agents": agent_types,
            "learnings_stored": 0,
            "neo4j_available": True,
            "memory_ids": [],
        }

        for agent_type in agent_types:
            # Normalize agent type
            normalized_type = detect_agent_type(agent_type)
            if not normalized_type:
                continue

            try:
                # Extract and store learnings
                memory_ids = extract_and_store_learnings(
                    agent_type=normalized_type,
                    output=conversation_text,
                    task="Conversation with user",  # Generic task description
                    success=True,
                )

                if memory_ids:
                    metadata["learnings_stored"] += len(memory_ids)
                    metadata["memory_ids"].extend(memory_ids)
                    logger.info(
                        f"Stored {len(memory_ids)} learnings from {normalized_type} conversation"
                    )

            except Exception as e:
                logger.warning(f"Failed to extract learnings for {normalized_type}: {e}")
                continue

        return metadata

    except ImportError as e:
        logger.warning(f"Memory integration not available: {e}")
        return {"neo4j_available": False, "error": "import_failed"}

    except Exception as e:
        logger.error(f"Failed to extract learnings: {e}")
        return {"neo4j_available": False, "error": str(e)}


def format_memory_injection_notice(metadata: dict[str, Any]) -> str:
    """Format a notice about memory injection for logging/display.

    Args:
        metadata: Metadata from inject_memory_for_agents

    Returns:
        Formatted notice string
    """
    if not metadata.get("neo4j_available"):
        return ""

    agents = metadata.get("agents", [])
    count = metadata.get("memories_injected", 0)

    if count > 0:
        agent_list = ", ".join(agents)
        return f"🧠 Injected {count} relevant memories for agents: {agent_list}"

    return ""


def format_learning_extraction_notice(metadata: dict[str, Any]) -> str:
    """Format a notice about learning extraction for logging/display.

    Args:
        metadata: Metadata from extract_learnings_from_conversation

    Returns:
        Formatted notice string
    """
    if not metadata.get("neo4j_available"):
        return ""

    count = metadata.get("learnings_stored", 0)

    if count > 0:
        agents = metadata.get("agents", [])
        agent_list = ", ".join(agents)
        return f"🧠 Stored {count} new learnings from agents: {agent_list}"

    return ""
