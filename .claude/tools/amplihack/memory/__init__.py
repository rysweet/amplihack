"""
Agent Memory System - Lightweight SQLite-based persistent memory for amplihack agents.

This module provides optional memory capabilities for agents with session management,
performance guarantees (<50ms operations), and clean separation of concerns.

Example:
    >>> from .claude.tools.amplihack.memory import AgentMemory
    >>>
    >>> # Basic usage
    >>> memory = AgentMemory("my-agent")
    >>> memory.store("preference", "dark-mode")
    >>> preference = memory.retrieve("preference")
    >>>
    >>> # With context manager
    >>> with AgentMemory("my-agent") as memory:
    >>>     memory.store("key", "value")
    >>>     value = memory.retrieve("key")

Features:
    - Lightweight SQLite backend (no heavy dependencies)
    - Session-based memory isolation
    - Markdown-first storage with JSON fallback
    - Optional activation (disabled by default in production)
    - Thread-safe operations
    - <50ms performance guarantee
    - Graceful degradation on errors
"""

from .core import MemoryBackend
from .interface import AgentMemory

# Public interface following builder agent guidelines
__all__ = ["AgentMemory", "MemoryBackend"]

# Module metadata
__version__ = "1.0.0"
__author__ = "amplihack"
__description__ = "Lightweight agent memory system"

# Default configuration
DEFAULT_DB_PATH = ".claude/runtime/memory.db"
DEFAULT_ENABLED = True
PERFORMANCE_TARGET_MS = 50
