"""Agent integration for Neo4j memory system.

This module provides the bridge between amplihack agents and the Neo4j memory system.
Agents can use this to:
1. Load relevant memories before starting work (inject_memory_context)
2. Store learnings after completing work (extract_and_store_learnings)

Usage:
    # Before agent runs
    context = inject_memory_context(agent_type="architect", task="Design auth system")

    # After agent completes
    extract_and_store_learnings(
        agent_type="architect",
        output="Agent's response...",
        task="Design auth system",
        success=True
    )
"""

import logging
import re
from typing import Any, Dict, List, Optional

from .agent_memory import AgentMemoryManager
from .lifecycle import ensure_neo4j_running

logger = logging.getLogger(__name__)


# Agent type mapping from various agent file names
AGENT_TYPE_MAP = {
    "architect.md": "architect",
    "architect": "architect",
    "builder.md": "builder",
    "builder": "builder",
    "reviewer.md": "reviewer",
    "reviewer": "reviewer",
    "tester.md": "tester",
    "tester": "tester",
    "optimizer.md": "optimizer",
    "optimizer": "optimizer",
    "security.md": "security",
    "security": "security",
    "database.md": "database",
    "database": "database",
    "api-designer.md": "api-designer",
    "api-designer": "api-designer",
    "integration.md": "integration",
    "integration": "integration",
    "analyzer.md": "analyzer",
    "analyzer": "analyzer",
    "cleanup.md": "cleanup",
    "cleanup": "cleanup",
    "fix-agent.md": "fix-agent",
    "fix-agent": "fix-agent",
    "pre-commit-diagnostic.md": "pre-commit-diagnostic",
    "pre-commit-diagnostic": "pre-commit-diagnostic",
    "ci-diagnostic.md": "ci-diagnostic",
    "ci-diagnostic": "ci-diagnostic",
}


def detect_agent_type(agent_identifier: str) -> Optional[str]:
    """Detect agent type from identifier (filename or type name).

    Args:
        agent_identifier: Agent filename (e.g., "architect.md") or type (e.g., "architect")

    Returns:
        Normalized agent type string, or None if not recognized
    """
    return AGENT_TYPE_MAP.get(agent_identifier)


def detect_task_category(task: str) -> str:
    """Detect task category from task description using keyword matching.

    Args:
        task: Task description string

    Returns:
        Category string (e.g., "system_design", "implementation", etc.)
    """
    task_lower = task.lower()

    # Category keyword mapping (ordered by specificity - most specific first)
    categories = {
        "optimization": ["optimize", "performance", "speed", "efficiency", "cache"],
        "security": ["security", "auth", "permission", "vulnerability", "xss", "injection"],
        "testing": ["test", "verify", "validate", "check", "coverage"],
        "error_handling": ["error", "exception", "fix", "bug", "failure"],
        "system_design": ["design", "architect", "structure", "pattern", "api design"],
        "database": ["database", "schema", "query", "migration", "sql"],
        "api": ["api", "endpoint", "route", "interface", "rest", "graphql"],
        "integration": ["integrate", "connect", "external", "service"],
        "implementation": ["implement", "build", "create", "code", "develop"],
    }

    # Check each category for keyword matches
    for category, keywords in categories.items():
        if any(kw in task_lower for kw in keywords):
            return category

    return "general"


def inject_memory_context(
    agent_type: str,
    task: str,
    task_category: Optional[str] = None,
    min_quality: float = 0.6,
    max_memories: int = 5,
) -> str:
    """Inject relevant memory context for an agent task.

    This function queries Neo4j for relevant memories and formats them
    for inclusion in the agent's prompt.

    Args:
        agent_type: Type of agent (e.g., "architect", "builder")
        task: Task description
        task_category: Optional category (auto-detected if None)
        min_quality: Minimum quality score for memories (0-1)
        max_memories: Maximum number of memories to include

    Returns:
        Formatted memory context string (empty if no memories or error)

    Example:
        >>> context = inject_memory_context(
        ...     agent_type="architect",
        ...     task="Design authentication system"
        ... )
        >>> print(context)
        ## 🧠 Memory Context (Relevant Past Learnings)
        ...
    """
    try:
        # Ensure Neo4j is running (non-blocking)
        if not ensure_neo4j_running(blocking=False):
            logger.warning("Neo4j not available, skipping memory context")
            return ""

        # Detect task category if not provided
        if not task_category:
            task_category = detect_task_category(task)

        # Create memory manager for this agent type
        try:
            mgr = AgentMemoryManager(agent_type=agent_type)
        except Exception as e:
            logger.warning(f"Failed to create AgentMemoryManager: {e}")
            return ""

        # Query memories for this agent type and category
        memories = mgr.recall(
            category=task_category,
            min_quality=min_quality,
            include_global=True,
            limit=max_memories * 2,  # Get extras for filtering
        )

        # Filter by relevance to task (simple keyword matching)
        relevant_memories = _filter_by_relevance(memories, task)[:max_memories]

        # Also query cross-agent learnings for certain agent types
        cross_agent_memories = []
        if agent_type in ["architect", "builder", "reviewer"]:
            cross_agent_memories = mgr.learn_from_others(
                category=task_category,
                min_quality=0.75,  # Higher threshold for cross-agent
                limit=3,
            )

        # Format memory context
        if not relevant_memories and not cross_agent_memories:
            return ""  # No memories to inject

        return _format_memory_context(
            agent_type=agent_type,
            memories=relevant_memories,
            cross_agent_memories=cross_agent_memories,
            task_category=task_category,
        )

    except Exception as e:
        logger.error(f"Failed to inject memory context: {e}")
        return ""  # Non-fatal: agent continues without memory


def extract_and_store_learnings(
    agent_type: str,
    output: str,
    task: str,
    task_category: Optional[str] = None,
    success: bool = True,
    duration_seconds: float = 0.0,
) -> List[str]:
    """Extract learnings from agent output and store in Neo4j.

    This function parses the agent's output for patterns, decisions,
    recommendations, and other learnings, then stores them in Neo4j.

    Args:
        agent_type: Type of agent
        output: Full agent output/response
        task: Task that was performed
        task_category: Optional category (auto-detected if None)
        success: Whether task was successful
        duration_seconds: How long the task took

    Returns:
        List of memory IDs that were stored

    Example:
        >>> memory_ids = extract_and_store_learnings(
        ...     agent_type="architect",
        ...     output="## Decision: Use JWT\\n**What**: Token-based auth...",
        ...     task="Design authentication",
        ...     success=True
        ... )
        >>> print(f"Stored {len(memory_ids)} memories")
    """
    try:
        # Ensure Neo4j is running (non-blocking)
        if not ensure_neo4j_running(blocking=False):
            logger.warning("Neo4j not available, skipping memory storage")
            return []

        # Detect task category if not provided
        if not task_category:
            task_category = detect_task_category(task)

        # Extract learnings from output
        from .extraction_patterns import extract_learnings

        learnings = extract_learnings(
            output=output,
            agent_type=agent_type,
            task_category=task_category,
        )

        if not learnings:
            logger.debug(f"No learnings extracted from {agent_type} output")
            return []

        # Create memory manager
        try:
            mgr = AgentMemoryManager(agent_type=agent_type)
        except Exception as e:
            logger.error(f"Failed to create AgentMemoryManager: {e}")
            return []

        # Store each learning
        memory_ids = []
        for learning in learnings:
            try:
                # Determine if this should be global scope
                is_global = (
                    learning["type"] in ["anti_pattern", "error_solution"]
                    and learning.get("confidence", 0) >= 0.85
                )

                # Map learning type to memory type
                memory_type_map = {
                    "decision": "declarative",
                    "recommendation": "procedural",
                    "anti_pattern": "anti_pattern",
                    "procedural": "procedural",
                    "error_solution": "procedural",
                    "pattern": "procedural",
                }
                memory_type = memory_type_map.get(learning["type"], "declarative")

                # Store memory
                memory_id = mgr.remember(
                    content=learning["content"],
                    category=learning.get("category", task_category),
                    memory_type=memory_type,
                    tags=[task_category, agent_type, learning["type"]],
                    confidence=learning.get("confidence", 0.7),
                    metadata={
                        "task": task[:200],  # Truncate long tasks
                        "duration_seconds": duration_seconds,
                        "success": success,
                        "reasoning": learning.get("reasoning", ""),
                    },
                    global_scope=is_global,
                )

                memory_ids.append(memory_id)

            except Exception as e:
                logger.warning(f"Failed to store learning: {e}")
                continue

        logger.info(
            f"Stored {len(memory_ids)} learnings from {agent_type} "
            f"(category: {task_category})"
        )
        return memory_ids

    except Exception as e:
        logger.error(f"Failed to extract and store learnings: {e}")
        return []  # Non-fatal


def _filter_by_relevance(memories: List[Dict[str, Any]], task: str) -> List[Dict[str, Any]]:
    """Filter memories by relevance to task using keyword matching.

    Args:
        memories: List of memory dictionaries
        task: Task description

    Returns:
        Filtered and sorted list of memories
    """
    task_keywords = set(re.findall(r'\w+', task.lower()))

    # Score each memory by keyword overlap
    scored_memories = []
    for mem in memories:
        content = mem.get("content", "").lower()
        content_keywords = set(re.findall(r'\w+', content))

        # Calculate relevance score
        overlap = len(task_keywords & content_keywords)
        relevance = overlap / max(len(task_keywords), 1)

        # Boost by quality score
        quality = mem.get("quality_score", 0.5)
        final_score = relevance * 0.6 + quality * 0.4

        scored_memories.append((final_score, mem))

    # Sort by score (descending) and return memories
    scored_memories.sort(reverse=True, key=lambda x: x[0])
    return [mem for score, mem in scored_memories]


def _format_memory_context(
    agent_type: str,
    memories: List[Dict[str, Any]],
    cross_agent_memories: List[Dict[str, Any]],
    task_category: str,
) -> str:
    """Format memories into context string for agent prompt.

    Args:
        agent_type: Type of agent
        memories: Memories from same agent type
        cross_agent_memories: Memories from other agents
        task_category: Task category

    Returns:
        Formatted context string
    """
    lines = [
        "## 🧠 Memory Context (Relevant Past Learnings)",
        "",
        f"*Based on previous {agent_type} work in category: {task_category}*",
        "",
    ]

    if memories:
        lines.append(f"### Past {agent_type.title()} Learnings")
        lines.append("")

        for i, mem in enumerate(memories, 1):
            category = mem.get("category", "general")
            quality = mem.get("quality_score", 0)
            content = mem.get("content", "")

            lines.append(f"**{i}. {category}** (quality: {quality:.2f})")
            lines.append(f"   {content}")

            # Add outcome if available
            metadata = mem.get("metadata", {})
            if metadata.get("outcome"):
                lines.append(f"   *Outcome: {metadata['outcome']}*")

            lines.append("")

    if cross_agent_memories:
        lines.append("### Learnings from Other Agents")
        lines.append("")

        for i, mem in enumerate(cross_agent_memories, 1):
            other_agent = mem.get("agent_type", "unknown")
            category = mem.get("category", "general")
            content = mem.get("content", "")

            lines.append(f"**{i}. From {other_agent}**: {category}")
            lines.append(f"   {content}")
            lines.append("")

    if not memories and not cross_agent_memories:
        lines.append("*No relevant past learnings found for this task.*")
        lines.append("")

    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def format_memory_for_agent(memory_context: str, agent_prompt: str) -> str:
    """Combine memory context with agent prompt.

    Args:
        memory_context: Formatted memory context from inject_memory_context()
        agent_prompt: Original agent prompt

    Returns:
        Combined prompt with memory context prepended
    """
    if not memory_context:
        return agent_prompt

    return f"{memory_context}\n{agent_prompt}"
