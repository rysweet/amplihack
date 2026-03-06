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

from .config import MemoryConfig
from .database import MemoryDatabase
from .distributed_store import DistributedGraphStore
from .facade import Memory
from .graph_store import GraphStore
from .manager import MemoryManager
from .memory_store import InMemoryGraphStore
from .models import MemoryEntry, MemoryType, SessionInfo

try:
    from .kuzu_store import KuzuGraphStore
except ImportError:
    KuzuGraphStore = None  # type: ignore[assignment,misc]

__all__ = [
    "DistributedGraphStore",
    "GraphStore",
    "InMemoryGraphStore",
    "KuzuGraphStore",
    "Memory",
    "MemoryConfig",
    "MemoryDatabase",
    "MemoryEntry",
    "MemoryManager",
    "MemoryType",
    "SessionInfo",
]
