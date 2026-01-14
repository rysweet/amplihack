"""
Memory injection and extraction for agent execution.

Injects relevant memories before agent execution and extracts learnings after.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Learning extraction patterns
LEARNING_PATTERNS = [
    # Decisions
    (r"decided to\s+(.+?)(?:\.|$)", "decision"),
    (r"choosing\s+(.+?)\s+(?:because|over|instead)", "decision"),
    (r"went with\s+(.+?)(?:\.|$)", "decision"),
    # Patterns
    (r"pattern:?\s*(.+?)(?:\.|$)", "pattern"),
    (r"best practice:?\s*(.+?)(?:\.|$)", "pattern"),
    (r"approach:?\s*(.+?)(?:\.|$)", "pattern"),
    # Learnings
    (r"learned that\s+(.+?)(?:\.|$)", "learning"),
    (r"discovered that\s+(.+?)(?:\.|$)", "learning"),
    (r"found that\s+(.+?)(?:\.|$)", "learning"),
    (r"realized\s+(.+?)(?:\.|$)", "learning"),
    # Anti-patterns
    (r"avoid\s+(.+?)(?:\.|$)", "anti-pattern"),
    (r"don't\s+(.+?)(?:\.|$)", "anti-pattern"),
    (r"never\s+(.+?)(?:\.|$)", "anti-pattern"),
]


def inject_memory_for_agents(
    prompt: str,
    agent_types: list[str],
    memory_backend: Any = None,
    session_id: str | None = None,
    token_budget: int = 2000,
) -> tuple[str, dict[str, Any]]:
    """Inject memory context for detected agents into prompt.

    Args:
        prompt: Original user prompt
        agent_types: List of agent types detected
        memory_backend: Optional memory backend instance
        session_id: Optional session ID for logging
        token_budget: Maximum tokens for memory context

    Returns:
        Tuple of (enhanced_prompt, metadata_dict)
    """
    if not agent_types:
        return prompt, {}

    metadata = {
        "agents": agent_types,
        "memories_injected": 0,
        "memory_available": memory_backend is not None,
    }

    if not memory_backend:
        return prompt, metadata

    try:
        memory_sections = []

        for agent_type in agent_types:
            normalized_type = agent_type.lower().replace(" ", "-")

            # Search for relevant memories
            memories = memory_backend.search_memories(
                session_id=session_id or "default",
                tags=[normalized_type],
                limit=10,
            )

            if memories:
                lines = [f"\n## Memory Context for {normalized_type}\n"]
                for mem in memories[:5]:  # Limit to 5 per agent
                    value = mem.get("memory_value", "")[:200]  # Truncate
                    lines.append(f"- {value}")

                memory_sections.append("\n".join(lines))
                metadata["memories_injected"] += len(memories[:5])

        if memory_sections:
            enhanced_prompt = "\n".join(memory_sections) + "\n\n---\n\n" + prompt
            return enhanced_prompt, metadata

        return prompt, metadata

    except Exception as e:
        logger.warning(f"Failed to inject memory: {e}")
        metadata["error"] = str(e)
        return prompt, metadata


def extract_learnings(
    conversation_text: str,
    agent_types: list[str],
    memory_backend: Any = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Extract and store learnings from conversation after agent execution.

    Args:
        conversation_text: Full conversation text
        agent_types: List of agent types involved
        memory_backend: Optional memory backend instance
        session_id: Optional session ID

    Returns:
        Metadata about learnings stored
    """
    if not agent_types:
        return {"learnings_stored": 0, "agents": []}

    metadata = {
        "agents": agent_types,
        "learnings_stored": 0,
        "learnings": [],
        "memory_available": memory_backend is not None,
    }

    # Extract learnings using patterns
    extracted = []
    for pattern, learning_type in LEARNING_PATTERNS:
        matches = re.finditer(pattern, conversation_text, re.IGNORECASE)
        for match in matches:
            content = match.group(1).strip()
            if len(content) > 10:  # Minimum length
                extracted.append(
                    {
                        "content": content[:500],  # Truncate
                        "type": learning_type,
                        "agents": agent_types,
                    }
                )

    # Deduplicate by content
    seen = set()
    unique_learnings = []
    for learning in extracted:
        key = learning["content"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique_learnings.append(learning)

    metadata["learnings"] = unique_learnings[:20]  # Limit

    # Store if backend available
    if memory_backend and unique_learnings:
        try:
            for learning in unique_learnings[:10]:  # Store max 10
                memory_backend.store_memory(
                    session_id=session_id or "default",
                    key=f"learning_{learning['type']}_{hash(learning['content']) % 10000}",
                    value=learning["content"],
                    memory_type=learning["type"],
                    importance=6,
                    tags=learning["agents"],
                )
                metadata["learnings_stored"] += 1
        except Exception as e:
            logger.warning(f"Failed to store learnings: {e}")
            metadata["store_error"] = str(e)

    return metadata
