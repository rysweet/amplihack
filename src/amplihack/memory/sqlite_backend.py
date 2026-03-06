"""SQLite memory backend — protocol definition and SQLite implementation.

Replaces the old backends/ directory. Provides the MemoryBackend protocol,
BackendCapabilities, SQLiteBackend, and create_backend factory.

Public API:
    MemoryBackend: Protocol interface all backends must implement
    BackendCapabilities: Feature flags for each backend
    SQLiteBackend: MemoryBackend implementation using SQLite
    create_backend: Factory function to create a backend instance
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .database import MemoryDatabase
from .models import MemoryEntry, MemoryQuery, SessionInfo

logger = logging.getLogger(__name__)


@dataclass
class BackendCapabilities:
    """Capabilities that each backend supports."""

    supports_graph_queries: bool = False
    supports_vector_search: bool = False
    supports_transactions: bool = True
    supports_fulltext_search: bool = False
    max_concurrent_connections: int = 1
    backend_name: str = "unknown"
    backend_version: str = "0.0.0"


class MemoryBackend(Protocol):
    """Protocol interface that all memory backends must implement."""

    def get_capabilities(self) -> BackendCapabilities: ...

    async def initialize(self) -> None: ...

    async def store_memory(self, memory: MemoryEntry) -> bool: ...

    async def retrieve_memories(self, query: MemoryQuery) -> list[MemoryEntry]: ...

    async def get_memory_by_id(self, memory_id: str) -> MemoryEntry | None: ...

    async def delete_memory(self, memory_id: str) -> bool: ...

    async def cleanup_expired(self) -> int: ...

    async def get_session_info(self, session_id: str) -> SessionInfo | None: ...

    async def list_sessions(self, limit: int | None = None) -> list[SessionInfo]: ...

    async def get_stats(self) -> dict[str, Any]: ...

    async def close(self) -> None: ...


class SQLiteBackend:
    """SQLite backend — wraps MemoryDatabase to implement MemoryBackend protocol."""

    def __init__(self, db_path: Path | str | None = None):
        self.database = MemoryDatabase(db_path)
        self._executor = ThreadPoolExecutor(max_workers=1)

    def get_capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            supports_graph_queries=False,
            supports_vector_search=False,
            supports_transactions=True,
            supports_fulltext_search=True,
            max_concurrent_connections=1,
            backend_name="sqlite",
            backend_version="3.x",
        )

    async def initialize(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.database.initialize)

    async def store_memory(self, memory: MemoryEntry) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.store_memory, memory)

    async def retrieve_memories(self, query: MemoryQuery) -> list[MemoryEntry]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.retrieve_memories, query)

    async def get_memory_by_id(self, memory_id: str) -> MemoryEntry | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.get_memory_by_id, memory_id)

    async def delete_memory(self, memory_id: str) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.delete_memory, memory_id)

    async def cleanup_expired(self) -> int:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.cleanup_expired)

    async def get_session_info(self, session_id: str) -> SessionInfo | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.get_session_info, session_id)

    async def list_sessions(self, limit: int | None = None) -> list[SessionInfo]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.list_sessions, limit)

    async def delete_session(self, session_id: str) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.delete_session, session_id)

    async def get_stats(self) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.database.get_stats)

    async def close(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.database.close)
        self._executor.shutdown(wait=True)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False


def create_backend(backend_type: str | None = None, **config: Any) -> "MemoryBackend":
    """Create a SQLite memory backend.

    Args:
        backend_type: Ignored (only SQLite is supported; use KuzuGraphStore for graph storage).
        **config: Backend-specific configuration. Accepts ``db_path``.

    Returns:
        Initialized SQLiteBackend instance.
    """
    if backend_type is not None and backend_type.lower() not in ("sqlite", ""):
        logger.warning(
            "create_backend: backend_type=%r is not supported; using SQLite. "
            "For graph storage use KuzuGraphStore directly.",
            backend_type,
        )
    db_path = config.get("db_path")
    return SQLiteBackend(db_path=db_path)


__all__ = ["BackendCapabilities", "MemoryBackend", "SQLiteBackend", "create_backend"]
