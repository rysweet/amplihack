"""
Agent Memory Tool for Amplifier.

Provides persistent memory storage for agents with session isolation,
agent namespacing, and thread-safe operations.

Features:
- Session-based memory isolation
- Agent namespacing for organized storage
- Thread-safe concurrent access
- <50ms operation performance
- Secure SQLite backend
"""

from .backend import MemoryBackend
from .interface import AgentMemory, MemoryEntry, MemoryType
from .tool import MemoryTool, create_tool

__all__ = [
    "MemoryBackend",
    "AgentMemory",
    "MemoryType",
    "MemoryEntry",
    "MemoryTool",
    "create_tool",
]
