"""SQLite backend implementation.

Wraps existing MemoryDatabase as a backend that implements the MemoryBackend protocol.

Philosophy:
- Zero abstraction overhead: Direct delegation to MemoryDatabase
- Backward compatible: Preserves all existing functionality
- Self-contained: All SQLite-specific logic in this module

Public API:
    SQLiteBackend: MemoryBackend implementation using SQLite
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ..database import MemoryDatabase
from ..models import MemoryEntry, MemoryQuery, SessionInfo
from .base import BackendCapabilities


class SQLiteBackend:
    """SQLite backend implementation.

    Wraps existing MemoryDatabase to implement MemoryBackend protocol.
    Preserves all existing functionality while providing standardized interface.
    """

    def __init__(self, db_path: Path | str | None = None):
        """Initialize SQLite backend.

        Args:
            db_path: Path to SQLite database file. Defaults to ~/.amplihack/memory.db
        """
        self.database = MemoryDatabase(db_path)
        self._executor = ThreadPoolExecutor(max_workers=1)

    def get_capabilities(self) -> BackendCapabilities:
        """Get SQLite backend capabilities."""
        return BackendCapabilities(
            supports_graph_queries=False,  # SQLite doesn't support native graph queries
            supports_vector_search=False,  # SQLite doesn't support native vector search
            supports_transactions=True,  # SQLite has ACID transactions
            supports_fulltext_search=True,  # SQLite has FTS5
            max_concurrent_connections=1,  # SQLite single writer
            backend_name="sqlite",
            backend_version="3.x",
        )

    async def initialize(self) -> None:
        """Initialize SQLite backend.

        Creates schema and indexes if needed.
        Idempotent - safe to call multiple times.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.database.initialize)

    async def store_memory(self, memory: MemoryEntry) -> bool:
        """Store a memory entry.

        Args:
            memory: Memory entry to store

        Returns:
            True if successful, False otherwise

        Performance: <500ms (SQLite insert + index updates)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.store_memory, memory)

    async def retrieve_memories(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Retrieve memories matching the query.

        Args:
            query: Query parameters

        Returns:
            List of matching memory entries

        Performance: <50ms (SQLite index lookups)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.retrieve_memories, query)

    async def get_memory_by_id(self, memory_id: str) -> MemoryEntry | None:
        """Get a specific memory by ID.

        Args:
            memory_id: Unique memory identifier

        Returns:
            Memory entry if found, None otherwise

        Performance: <50ms (SQLite primary key lookup)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.get_memory_by_id, memory_id)

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry.

        Args:
            memory_id: Unique memory identifier

        Returns:
            True if deleted, False otherwise

        Performance: <100ms (SQLite delete + cascade)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.delete_memory, memory_id)

    async def cleanup_expired(self) -> int:
        """Remove expired memory entries.

        Returns:
            Number of entries removed

        Performance: No strict limit (periodic maintenance)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.cleanup_expired)

    async def get_session_info(self, session_id: str) -> SessionInfo | None:
        """Get information about a session.

        Args:
            session_id: Session identifier

        Returns:
            Session information if found

        Performance: <50ms (SQLite joins)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self.database.get_session_info, session_id
        )

    async def list_sessions(self, limit: int | None = None) -> list[SessionInfo]:
        """List all sessions ordered by last accessed.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session information

        Performance: <100ms (SQLite ORDER BY)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.list_sessions, limit)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its associated memories.

        Args:
            session_id: Session identifier to delete

        Returns:
            True if session was deleted, False otherwise

        Performance: <500ms (cascading delete)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.delete_session, session_id)

    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with backend statistics

        Performance: <100ms (SQLite aggregations)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.get_stats)

    async def close(self) -> None:
        """Close SQLite connection and cleanup resources.

        Idempotent - safe to call multiple times.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.database.close)
        # Shutdown executor properly waiting for completion
        self._executor.shutdown(wait=True)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with proper cleanup."""
        await self.close()
        return False


__all__ = ["SQLiteBackend"]
