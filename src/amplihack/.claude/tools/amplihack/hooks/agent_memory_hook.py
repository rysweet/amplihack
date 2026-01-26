#!/usr/bin/env python3
"""Shared logic for integrating memory system with agent execution.

This module provides utilities for:
1. Detecting agent references in prompts (@.claude/agents/*.md)
2. Injecting relevant memory context before agent execution
3. Extracting and storing learnings after agent execution

Integration Points:
- user_prompt_submit: Inject memory context when agent detected
- stop: Extract learnings from conversation after agent execution

Uses MemoryCoordinator for storage (Kuzu backend).
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


async def inject_memory_for_agents(
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
        # Import memory coordinator (lazy import to avoid startup overhead)
        from amplihack.memory.coordinator import MemoryCoordinator, RetrievalQuery
        from amplihack.memory.types import MemoryType

        # Initialize coordinator with session_id
        coordinator = MemoryCoordinator(session_id=session_id or "hook_session")

        # Inject memory for each agent type
        memory_sections = []
        metadata = {"agents": agent_types, "memories_injected": 0, "memory_available": True}

        for agent_type in agent_types:
            # Normalize agent type (lowercase, replace spaces with hyphens)
            normalized_type = agent_type.lower().replace(" ", "-")

            # Get memory context for this agent
            try:
                # Retrieve relevant memories using query
                query_text = prompt[:500]  # Use first 500 chars as query

                # Build retrieval query with comprehensive context
                query = RetrievalQuery(
                    query_text=query_text,
                    token_budget=2000,
                    memory_types=[MemoryType.EPISODIC, MemoryType.SEMANTIC, MemoryType.PROCEDURAL],
                )

                memories = await coordinator.retrieve(query)

                if memories:
                    # Format memories for injection
                    memory_lines = [f"\n## Memory for {normalized_type} Agent\n"]
                    for mem in memories:
                        # Note: score attribute removed with Neo4j, using importance instead
                        relevance = getattr(mem, "importance", 5) / 10.0  # Normalize to 0-1 scale
                        memory_lines.append(f"- {mem.content} (importance: {relevance:.2f})")

                    memory_sections.append("\n".join(memory_lines))
                    metadata["memories_injected"] += len(memories)

            except Exception as e:
                logger.warning(f"Failed to inject memory for {normalized_type}: {e}")
                continue

        # Build enhanced prompt
        if memory_sections:
            enhanced_prompt = "\n".join(memory_sections) + "\n\n---\n\n" + prompt
            return enhanced_prompt, metadata

        return prompt, metadata

    except ImportError as e:
        logger.warning(f"Memory system not available: {e}")
        return prompt, {"memory_available": False, "error": "import_failed"}

    except Exception as e:
        logger.error(f"Failed to inject memory: {e}")
        return prompt, {"memory_available": False, "error": str(e)}


async def extract_learnings_from_conversation(
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
        # Import memory coordinator (lazy import)
        from amplihack.memory.coordinator import MemoryCoordinator, StorageRequest
        from amplihack.memory.types import MemoryType

        # Initialize coordinator with session_id
        coordinator = MemoryCoordinator(session_id=session_id or "hook_session")

        # Extract and store learnings for each agent
        metadata = {
            "agents": agent_types,
            "learnings_stored": 0,
            "memory_available": True,
            "memory_ids": [],
        }

        for agent_type in agent_types:
            # Normalize agent type (lowercase, replace spaces with hyphens)
            normalized_type = agent_type.lower().replace(" ", "-")

            try:
                # Store learning as SEMANTIC memory (reusable knowledge)
                # Extract key learnings from conversation text (simplified extraction)
                # In production, you might want more sophisticated extraction
                learning_content = f"Agent {normalized_type}: {conversation_text[:500]}"

                # Build storage request with context and metadata
                request = StorageRequest(
                    content=learning_content,
                    memory_type=MemoryType.SEMANTIC,
                    context={"agent_type": normalized_type},
                    metadata={
                        "tags": ["learning", "conversation"],
                        "task": "Conversation with user",
                        "success": True,
                    },
                )

                memory_id = await coordinator.store(request)

                if memory_id:
                    metadata["learnings_stored"] += 1
                    metadata["memory_ids"].append(memory_id)
                    logger.info(f"Stored 1 learning from {normalized_type} conversation")

            except Exception as e:
                logger.warning(f"Failed to extract learnings for {normalized_type}: {e}")
                continue

        return metadata

    except ImportError as e:
        logger.warning(f"Memory system not available: {e}")
        return {"memory_available": False, "error": "import_failed"}

    except Exception as e:
        logger.error(f"Failed to extract learnings: {e}")
        return {"memory_available": False, "error": str(e)}


def format_memory_injection_notice(metadata: dict[str, Any]) -> str:
    """Format a notice about memory injection for logging/display.

    Args:
        metadata: Metadata from inject_memory_for_agents

    Returns:
        Formatted notice string
    """
    if not metadata.get("memory_available"):
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
    if not metadata.get("memory_available"):
        return ""

    count = metadata.get("learnings_stored", 0)

    if count > 0:
        agents = metadata.get("agents", [])
        agent_list = ", ".join(agents)
        return f"🧠 Stored {count} new learnings from agents: {agent_list}"

    return ""


# ============================================================================
# SYNC WRAPPERS - Solution for Issue #1960
# ============================================================================
# These sync wrapper functions safely handle async functions in synchronous
# contexts (like hooks). They handle three critical edge cases:
# 1. No event loop exists (create new loop)
# 2. Event loop already running (use thread to avoid nested loop)
# 3. Import errors or exceptions (fail-open gracefully)


def inject_memory_for_agents_sync(
    prompt: str, agent_types: list[str], session_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    """Synchronous wrapper for inject_memory_for_agents.

    Safely calls async inject_memory_for_agents from synchronous context.
    Handles three edge cases:
    1. No event loop - creates new loop
    2. Running event loop - uses thread to avoid nesting
    3. Errors - fails open (returns original prompt)

    Args:
        prompt: Original user prompt
        agent_types: List of agent types detected
        session_id: Optional session ID for logging

    Returns:
        Tuple of (enhanced_prompt, metadata_dict)
    """
    # Handle empty agent_types early
    if not agent_types:
        return prompt, {}

    try:
        import asyncio

        # Try to get running loop
        try:
            loop = asyncio.get_running_loop()
            # Loop is running - must use thread to avoid nested loop error
            import threading

            result = [None]  # type: ignore[var-annotated]
            error = [None]  # type: ignore[var-annotated]

            def run_in_thread():
                try:
                    # Create new loop in thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result[0] = new_loop.run_until_complete(  # type: ignore[index]
                            inject_memory_for_agents(prompt, agent_types, session_id)
                        )
                    finally:
                        new_loop.close()
                except Exception as e:
                    error[0] = e  # type: ignore[index]

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join(timeout=30)  # 30 second timeout

            if error[0]:
                raise error[0]

            if result[0]:
                return result[0]
            # Timeout or no result
            logger.warning("Memory injection timed out in thread")
            return prompt, {"memory_available": False, "error": "timeout"}

        except RuntimeError:
            # No running loop - safe to create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    inject_memory_for_agents(prompt, agent_types, session_id)
                )
                return result
            finally:
                loop.close()

    except ImportError as e:
        logger.warning(f"Memory system not available: {e}")
        return prompt, {"memory_available": False, "error": "import_failed"}

    except Exception as e:
        logger.error(f"Failed to inject memory (sync wrapper): {e}")
        return prompt, {"memory_available": False, "error": str(e)}


def extract_learnings_from_conversation_sync(
    conversation_text: str, agent_types: list[str], session_id: str | None = None
) -> dict[str, Any]:
    """Synchronous wrapper for extract_learnings_from_conversation.

    Safely calls async extract_learnings_from_conversation from synchronous context.
    Handles three edge cases:
    1. No event loop - creates new loop
    2. Running event loop - uses thread to avoid nesting
    3. Errors - fails open (returns minimal metadata)

    Args:
        conversation_text: Full conversation text
        agent_types: List of agent types involved
        session_id: Optional session ID for tracking

    Returns:
        Metadata about learnings stored
    """
    # Handle empty agent_types early
    if not agent_types:
        return {"learnings_stored": 0, "agents": []}

    try:
        import asyncio

        # Try to get running loop
        try:
            loop = asyncio.get_running_loop()
            # Loop is running - must use thread to avoid nested loop error
            import threading

            result = [None]  # type: ignore[var-annotated]
            error = [None]  # type: ignore[var-annotated]

            def run_in_thread():
                try:
                    # Create new loop in thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result[0] = new_loop.run_until_complete(  # type: ignore[index]
                            extract_learnings_from_conversation(
                                conversation_text, agent_types, session_id
                            )
                        )
                    finally:
                        new_loop.close()
                except Exception as e:
                    error[0] = e  # type: ignore[index]

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join(timeout=30)  # 30 second timeout

            if error[0]:
                raise error[0]

            if result[0]:
                return result[0]
            # Timeout or no result
            logger.warning("Learning extraction timed out in thread")
            return {"memory_available": False, "error": "timeout", "learnings_stored": 0}

        except RuntimeError:
            # No running loop - safe to create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    extract_learnings_from_conversation(conversation_text, agent_types, session_id)
                )
                return result
            finally:
                loop.close()

    except ImportError as e:
        logger.warning(f"Memory system not available: {e}")
        return {"memory_available": False, "error": "import_failed", "learnings_stored": 0}

    except Exception as e:
        logger.error(f"Failed to extract learnings (sync wrapper): {e}")
        return {"memory_available": False, "error": str(e), "learnings_stored": 0}
