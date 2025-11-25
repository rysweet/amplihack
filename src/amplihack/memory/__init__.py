"""Agent Memory System for amplihack.

Provides persistent memory storage for AI agents with session isolation,
thread-safe operations, and efficient retrieval.

Supports multiple graph database backends:
- Neo4j (Docker-based): Full-featured graph database
- Kùzu (embedded): Zero-infrastructure, file-based graph database

Use auto_backend for automatic backend selection:
    from amplihack.memory.auto_backend import get_connector
    with get_connector() as conn:
        results = conn.execute_query("MATCH (n) RETURN count(n)")
"""

from .database import MemoryDatabase
from .manager import MemoryManager
from .models import MemoryEntry, MemoryType, SessionInfo

__all__ = [
    "MemoryDatabase",
    "MemoryEntry",
    "MemoryManager",
    "MemoryType",
    "SessionInfo",
]
