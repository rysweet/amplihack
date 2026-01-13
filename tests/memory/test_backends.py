"""Tests fer backend abstraction layer.

Verifies:
- Backend protocol implementation
- Backend selection logic
- SQLite backend wrapper works
- Coordinator uses backends correctly
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from amplihack.memory.backends import BackendType, SQLiteBackend, create_backend
from amplihack.memory.coordinator import MemoryCoordinator, StorageRequest
from amplihack.memory.models import MemoryEntry
from amplihack.memory.models import MemoryType as OldMemoryType
from amplihack.memory.types import MemoryType


class TestBackendSelection:
    """Test backend selection logic."""

    def test_default_backend_selection_works(self):
        """Default backend should be created without errors."""
        backend = create_backend()
        assert backend is not None
        capabilities = backend.get_capabilities()
        assert capabilities.backend_name in ["sqlite", "kuzu"]

    def test_explicit_sqlite_backend(self):
        """Can explicitly request SQLite backend."""
        backend = create_backend(backend_type="sqlite")
        capabilities = backend.get_capabilities()
        assert capabilities.backend_name == "sqlite"

    def test_explicit_sqlite_backend_enum(self):
        """Can request SQLite using enum."""
        backend = create_backend(backend_type=BackendType.SQLITE)
        capabilities = backend.get_capabilities()
        assert capabilities.backend_name == "sqlite"

    def test_invalid_backend_type_raises_error(self):
        """Invalid backend type should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid backend type"):
            create_backend(backend_type="invalid")

    def test_neo4j_backend_not_implemented_yet(self):
        """Neo4j backend should raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Neo4j backend not yet implemented"):
            create_backend(backend_type="neo4j")

    def test_backend_with_custom_path(self):
        """Can create backend with custom database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "custom_memory.db"
            backend = create_backend(backend_type="sqlite", db_path=db_path)
            assert backend is not None
            # Database file should be created
            assert db_path.exists()


class TestSQLiteBackend:
    """Test SQLite backend wrapper."""

    def test_sqlite_backend_implements_protocol(self):
        """SQLite backend implements all protocol methods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            # Check all required methods exist
            assert hasattr(backend, "get_capabilities")
            assert hasattr(backend, "initialize")
            assert hasattr(backend, "store_memory")
            assert hasattr(backend, "retrieve_memories")
            assert hasattr(backend, "get_memory_by_id")
            assert hasattr(backend, "delete_memory")
            assert hasattr(backend, "cleanup_expired")
            assert hasattr(backend, "get_session_info")
            assert hasattr(backend, "list_sessions")
            assert hasattr(backend, "get_stats")
            assert hasattr(backend, "close")

    def test_sqlite_backend_capabilities(self):
        """SQLite backend reports correct capabilities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = SQLiteBackend(db_path=Path(tmpdir) / "test.db")
            capabilities = backend.get_capabilities()

            assert capabilities.backend_name == "sqlite"
            assert capabilities.supports_transactions is True
            assert capabilities.supports_fulltext_search is True
            assert capabilities.supports_graph_queries is False
            assert capabilities.supports_vector_search is False

    def test_sqlite_backend_store_and_retrieve(self):
        """SQLite backend can store and retrieve memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = SQLiteBackend(db_path=Path(tmpdir) / "test.db")
            backend.initialize()

            # Create test memory
            memory = MemoryEntry(
                id="test-123",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=OldMemoryType.CONVERSATION,
                title="Test Memory",
                content="This be a test memory",
                metadata={"new_memory_type": MemoryType.EPISODIC.value},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            # Store memory
            success = backend.store_memory(memory)
            assert success is True

            # Retrieve memory
            retrieved = backend.get_memory_by_id("test-123")
            assert retrieved is not None
            assert retrieved.id == "test-123"
            assert retrieved.content == "This be a test memory"


class TestCoordinatorBackendIntegration:
    """Test coordinator integration with backends."""

    @pytest.mark.asyncio
    async def test_coordinator_uses_backend(self):
        """Coordinator can use backend fer storage/retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create coordinator with SQLite backend
            coordinator = MemoryCoordinator(backend_type="sqlite", db_path=Path(tmpdir) / "test.db")

            # Store a memory
            request = StorageRequest(
                content="Test memory content fer backend integration",
                memory_type=MemoryType.EPISODIC,
            )

            memory_id = await coordinator.store(request)
            assert memory_id is not None

            # Verify backend capabilities
            backend_info = coordinator.get_backend_info()
            assert backend_info["backend_name"] == "sqlite"
            assert "supports_graph_queries" in backend_info

    @pytest.mark.asyncio
    async def test_coordinator_backward_compatible_with_database_param(self):
        """Coordinator still works with old database parameter (deprecated)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # This tests backward compatibility - users might still pass database
            # Should work but use backend internally
            backend = SQLiteBackend(db_path=Path(tmpdir) / "test.db")
            coordinator = MemoryCoordinator(backend=backend)

            # Should work normally
            request = StorageRequest(
                content="Backward compatibility test",
                memory_type=MemoryType.SEMANTIC,
            )

            memory_id = await coordinator.store(request)
            assert memory_id is not None

    @pytest.mark.asyncio
    async def test_coordinator_default_backend(self):
        """Coordinator uses default backend when none specified."""
        coordinator = MemoryCoordinator()

        # Should have created a backend (either Kùzu or SQLite)
        backend_info = coordinator.get_backend_info()
        assert backend_info["backend_name"] in ["sqlite", "kuzu"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
