"""Agent Memory System integration for Claude Tools.

This module provides memory management capabilities for AI agents running
within the Claude tools framework. It enables persistent storage and retrieval
of agent memories with session isolation and thread-safe operations.

Key Features:
- Session-based memory isolation
- Agent namespacing for organized storage
- Thread-safe concurrent access
- <50ms operation performance
- Secure SQLite backend with proper permissions
- Optional memory activation for performance

Usage:
    from .claude.tools.amplihack.memory import get_memory_manager, activate_memory

    # Get memory manager for current session
    memory = get_memory_manager()

    # Store agent memory
    memory_id = memory.store(
        agent_id="architect",
        title="API Design Decision",
        content="Decided to use REST API with JSON responses",
        memory_type=MemoryType.DECISION,
        importance=8,
        tags=["api", "architecture"]
    )

    # Retrieve memories
    decisions = memory.retrieve(
        agent_id="architect",
        memory_type=MemoryType.DECISION,
        min_importance=7
    )
"""

import os
import threading
from pathlib import Path
from typing import Optional

from amplihack.memory import MemoryEntry, MemoryManager, MemoryType

# Global memory manager instance with thread safety
_memory_manager_lock = threading.RLock()
_memory_manager_instance: Optional[MemoryManager] = None
_memory_enabled = True


def get_memory_manager(session_id: Optional[str] = None) -> Optional[MemoryManager]:
    """Get memory manager instance for the current session.

    Returns thread-safe singleton memory manager. If memory is disabled
    or initialization fails, returns None for graceful degradation.

    Args:
        session_id: Optional session identifier. If not provided, attempts
                   to detect from environment or generates new session.

    Returns:
        MemoryManager instance or None if disabled/failed

    Example:
        memory = get_memory_manager()
        if memory:
            memory.store(agent_id="test", title="Test", content="Content")
    """
    global _memory_manager_instance

    if not _memory_enabled:
        return None

    with _memory_manager_lock:
        if _memory_manager_instance is None:
            try:
                # Use default database location
                db_path = Path.home() / ".amplihack" / "memory.db"

                # Auto-detect session from environment or generate
                if session_id is None:
                    session_id = _detect_session_id()

                _memory_manager_instance = MemoryManager(db_path=db_path, session_id=session_id)

            except Exception as e:
                # Graceful degradation - log error but don't crash
                print(f"Memory system initialization failed: {e}")
                _memory_manager_instance = None

        return _memory_manager_instance


def _detect_session_id() -> str:
    """Detect or generate session identifier.

    Attempts to detect session from environment variables or
    generates a new session based on timestamp.

    Returns:
        Session identifier string
    """
    # Check for existing session in environment
    session_id = os.environ.get("CLAUDE_SESSION_ID")
    if session_id:
        return session_id

    # Generate new session based on timestamp
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"claude_session_{timestamp}"


def activate_memory(enable: bool = True) -> None:
    """Activate or deactivate memory system.

    Allows dynamic enabling/disabling of memory functionality.
    When disabled, all memory operations return None gracefully.

    Args:
        enable: True to enable memory, False to disable

    Example:
        # Disable memory for performance-critical operations
        activate_memory(False)

        # Re-enable memory
        activate_memory(True)
    """
    global _memory_enabled, _memory_manager_instance

    with _memory_manager_lock:
        _memory_enabled = enable
        if not enable:
            # Clear instance when disabled
            _memory_manager_instance = None


def store_agent_memory(
    agent_id: str,
    title: str,
    content: str,
    memory_type: MemoryType = MemoryType.CONTEXT,
    importance: Optional[int] = None,
    tags: Optional["list[str]"] = None,
    **kwargs,
) -> Optional[str]:
    """Convenience function to store agent memory.

    Simplified interface for common memory storage operations.

    Args:
        agent_id: Identifier of the agent storing memory
        title: Brief memory title
        content: Main memory content
        memory_type: Type of memory being stored
        importance: Importance score (1-10)
        tags: List of tags for categorization
        **kwargs: Additional arguments passed to memory.store()

    Returns:
        Memory ID if successful, None if memory disabled/failed

    Example:
        memory_id = store_agent_memory(
            agent_id="architect",
            title="API Design",
            content="Decided on REST API",
            memory_type=MemoryType.DECISION,
            importance=8,
            tags=["api", "design"]
        )
    """
    memory = get_memory_manager()
    if memory is None:
        return None

    try:
        return memory.store(
            agent_id=agent_id,
            title=title,
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags,
            **kwargs,
        )
    except Exception as e:
        print(f"Failed to store memory: {e}")
        return None


def retrieve_agent_memories(
    agent_id: str,
    memory_type: Optional[MemoryType] = None,
    min_importance: Optional[int] = None,
    tags: Optional["list[str]"] = None,
    limit: Optional[int] = None,
    **kwargs,
) -> "list[MemoryEntry]":
    """Convenience function to retrieve agent memories.

    Simplified interface for common memory retrieval operations.

    Args:
        agent_id: Agent identifier to retrieve memories for
        memory_type: Filter by memory type
        min_importance: Minimum importance score
        tags: Filter by tags
        limit: Maximum number of memories to return
        **kwargs: Additional arguments passed to memory.retrieve()

    Returns:
        List of MemoryEntry objects, empty list if disabled/failed

    Example:
        decisions = retrieve_agent_memories(
            agent_id="architect",
            memory_type=MemoryType.DECISION,
            min_importance=7,
            limit=10
        )
    """
    memory = get_memory_manager()
    if memory is None:
        return []

    try:
        return memory.retrieve(
            agent_id=agent_id,
            memory_type=memory_type,
            min_importance=min_importance,
            tags=tags,
            limit=limit or 100,
            **kwargs,
        )
    except Exception as e:
        print(f"Failed to retrieve memories: {e}")
        return []


def search_memories(
    query: str, agent_id: Optional[str] = None, limit: Optional[int] = None
) -> "list[MemoryEntry]":
    """Search memories by content.

    Performs text search across memory titles and content.

    Args:
        query: Search query string
        agent_id: Optional agent filter
        limit: Maximum results to return

    Returns:
        List of matching MemoryEntry objects

    Example:
        results = search_memories("API design decisions")
    """
    memory = get_memory_manager()
    if memory is None:
        return []

    try:
        return memory.search(query, agent_id=agent_id, limit=limit if limit is not None else 100)
    except Exception as e:
        print(f"Failed to search memories: {e}")
        return []


# Export public interface
__all__ = [
    "MemoryEntry",
    "MemoryManager",
    "MemoryType",
    "activate_memory",
    "get_memory_manager",
    "retrieve_agent_memories",
    "search_memories",
    "store_agent_memory",
]
