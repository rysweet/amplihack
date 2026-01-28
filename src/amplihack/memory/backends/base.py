"""Backend abstraction protocol fer memory storage.

Defines the interface that all backend implementations must implement.

Philosophy:
- Protocol-based: Uses typing.Protocol fer duck typing
- Performance contracts: <50ms retrieval, <500ms storage
- Capability flags: Each backend advertises what it supports
- Zero-BS: No abstract base classes, just clear protocol

Public API:
    MemoryBackend: Protocol interface all backends implement
    BackendCapabilities: Feature flags fer each backend
"""

from dataclasses import dataclass
from typing import Any, Protocol

from ..models import MemoryEntry, MemoryQuery, SessionInfo


@dataclass
class BackendCapabilities:
    """Capabilities that each backend supports.

    Allows backends to advertise what features they provide.
    Coordinator can check capabilities before using advanced features.
    """

    supports_graph_queries: bool = False  # Graph traversal, relationship queries
    supports_vector_search: bool = False  # Semantic similarity search
    supports_transactions: bool = True  # ACID transactions
    supports_fulltext_search: bool = False  # Full-text indexing
    max_concurrent_connections: int = 1  # Connection pool size
    backend_name: str = "unknown"
    backend_version: str = "0.0.0"


class MemoryBackend(Protocol):
    """Protocol interface that all memory backends must implement.

    Defines the contract fer store/retrieve/delete operations.
    Performance contracts:
    - retrieve_memories: <50ms
    - store_memory: <500ms
    - delete_memory: <100ms
    """

    def get_capabilities(self) -> BackendCapabilities:
        """Get backend capabilities.

        Returns:
            BackendCapabilities fer this backend
        """
        ...

    async def initialize(self) -> None:
        """Initialize backend (create schema, indexes, etc).

        MUST be called before first use.
        Should be idempotent (safe to call multiple times).
        """
        ...

    async def store_memory(self, memory: MemoryEntry) -> bool:
        """Store a memory entry.

        Args:
            memory: Memory entry to store

        Returns:
            True if successful, False otherwise

        Performance: Must complete under 500ms
        """
        ...

    async def retrieve_memories(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Retrieve memories matching the query.

        Args:
            query: Query parameters

        Returns:
            List of matching memory entries

        Performance: Must complete under 50ms
        """
        ...

    async def get_memory_by_id(self, memory_id: str) -> MemoryEntry | None:
        """Get a specific memory by ID.

        Args:
            memory_id: Unique memory identifier

        Returns:
            Memory entry if found, None otherwise

        Performance: Must complete under 50ms
        """
        ...

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry.

        Args:
            memory_id: Unique memory identifier

        Returns:
            True if deleted, False otherwise

        Performance: Must complete under 100ms
        """
        ...

    async def cleanup_expired(self) -> int:
        """Remove expired memory entries.

        Returns:
            Number of entries removed

        Performance: No strict limit (periodic maintenance)
        """
        ...

    async def get_session_info(self, session_id: str) -> SessionInfo | None:
        """Get information about a session.

        Args:
            session_id: Session identifier

        Returns:
            Session information if found

        Performance: Must complete under 50ms
        """
        ...

    async def list_sessions(self, limit: int | None = None) -> list[SessionInfo]:
        """List all sessions ordered by last accessed.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session information

        Performance: Must complete under 100ms
        """
        ...

    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with backend statistics

        Performance: Must complete under 100ms
        """
        ...

    async def close(self) -> None:
        """Close backend connection and cleanup resources.

        Should be idempotent (safe to call multiple times).
        """
        ...


__all__ = ["MemoryBackend", "BackendCapabilities"]
