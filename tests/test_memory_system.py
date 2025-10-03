"""Comprehensive test suite for the Agent Memory System."""

import json
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from amplihack.memory import MemoryDatabase, MemoryEntry, MemoryManager, MemoryType
from amplihack.memory.maintenance import MemoryMaintenance
from amplihack.memory.models import MemoryQuery


class TestMemoryDatabase:
    """Test the core database functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_memory.db"
            yield MemoryDatabase(db_path)

    def test_database_initialization(self, temp_db):
        """Test database initialization and schema creation."""
        # Database should be created and initialized
        assert temp_db.db_path.exists()
        assert temp_db.db_path.stat().st_mode & 0o777 == 0o600  # Check permissions

        # Test connection and basic query
        with temp_db._get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "memory_entries" in tables
            assert "sessions" in tables
            assert "session_agents" in tables

    def test_memory_storage_and_retrieval(self, temp_db):
        """Test storing and retrieving memory entries."""
        # Create test memory
        memory = MemoryEntry(
            id=str(uuid.uuid4()),
            session_id="test_session",
            agent_id="test_agent",
            memory_type=MemoryType.CONTEXT,
            title="Test Memory",
            content="This is test content",
            metadata={"key": "value"},
            tags=["test", "example"],
            importance=7,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
        )

        # Store memory
        assert temp_db.store_memory(memory) is True

        # Retrieve by ID
        retrieved = temp_db.get_memory_by_id(memory.id)
        assert retrieved is not None
        assert retrieved.id == memory.id
        assert retrieved.title == memory.title
        assert retrieved.content == memory.content
        assert retrieved.metadata == memory.metadata
        assert retrieved.tags == memory.tags
        assert retrieved.importance == memory.importance

    def test_memory_query_filtering(self, temp_db):
        """Test memory query filtering capabilities."""
        # Create multiple test memories
        memories = []
        for i in range(5):
            memory = MemoryEntry(
                id=str(uuid.uuid4()),
                session_id="test_session",
                agent_id=f"agent_{i % 2}",  # Two different agents
                memory_type=MemoryType.CONTEXT if i % 2 == 0 else MemoryType.DECISION,
                title=f"Memory {i}",
                content=f"Content for memory {i}",
                metadata={"index": i},
                tags=["test"] if i < 3 else ["example"],
                importance=i + 1,
                created_at=datetime.now() - timedelta(hours=i),
                accessed_at=datetime.now() - timedelta(hours=i),
            )
            memories.append(memory)
            temp_db.store_memory(memory)

        # Test session filtering
        query = MemoryQuery(session_id="test_session")
        results = temp_db.retrieve_memories(query)
        assert len(results) == 5

        # Test agent filtering
        query = MemoryQuery(session_id="test_session", agent_id="agent_0")
        results = temp_db.retrieve_memories(query)
        assert len(results) == 3  # agents 0, 2, 4

        # Test memory type filtering
        query = MemoryQuery(session_id="test_session", memory_type=MemoryType.DECISION)
        results = temp_db.retrieve_memories(query)
        assert len(results) == 2  # memories 1, 3

        # Test importance filtering
        query = MemoryQuery(session_id="test_session", min_importance=4)
        results = temp_db.retrieve_memories(query)
        assert len(results) == 2  # memories 3, 4 (importance 4, 5)

        # Test content search
        query = MemoryQuery(session_id="test_session", content_search="memory 2")
        results = temp_db.retrieve_memories(query)
        assert len(results) == 1
        assert results[0].title == "Memory 2"

        # Test limit
        query = MemoryQuery(session_id="test_session", limit=3)
        results = temp_db.retrieve_memories(query)
        assert len(results) == 3

    def test_session_tracking(self, temp_db):
        """Test session and agent tracking."""
        # Store memory to create session
        memory = MemoryEntry(
            id=str(uuid.uuid4()),
            session_id="test_session",
            agent_id="test_agent",
            memory_type=MemoryType.CONTEXT,
            title="Test Memory",
            content="Test content",
            metadata={},
            created_at=datetime.now(),
            accessed_at=datetime.now(),
        )
        temp_db.store_memory(memory)

        # Get session info
        session_info = temp_db.get_session_info("test_session")
        assert session_info is not None
        assert session_info.session_id == "test_session"
        assert "test_agent" in session_info.agent_ids
        assert session_info.memory_count == 1

        # List sessions
        sessions = temp_db.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == "test_session"

    def test_cleanup_expired(self, temp_db):
        """Test cleanup of expired memories."""
        # Create expired memory
        expired_memory = MemoryEntry(
            id=str(uuid.uuid4()),
            session_id="test_session",
            agent_id="test_agent",
            memory_type=MemoryType.CONTEXT,
            title="Expired Memory",
            content="This memory has expired",
            metadata={},
            created_at=datetime.now() - timedelta(hours=2),
            accessed_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1),  # Expired 1 hour ago
        )

        # Create non-expired memory
        active_memory = MemoryEntry(
            id=str(uuid.uuid4()),
            session_id="test_session",
            agent_id="test_agent",
            memory_type=MemoryType.CONTEXT,
            title="Active Memory",
            content="This memory is still active",
            metadata={},
            created_at=datetime.now(),
            accessed_at=datetime.now(),
        )

        # Store both memories
        temp_db.store_memory(expired_memory)
        temp_db.store_memory(active_memory)

        # Verify both exist
        query = MemoryQuery(session_id="test_session", include_expired=True)
        all_memories = temp_db.retrieve_memories(query)
        assert len(all_memories) == 2

        # Cleanup expired
        cleanup_count = temp_db.cleanup_expired()
        assert cleanup_count == 1

        # Verify only active memory remains
        remaining_memories = temp_db.retrieve_memories(query)
        assert len(remaining_memories) == 1
        assert remaining_memories[0].title == "Active Memory"

    def test_database_stats(self, temp_db):
        """Test database statistics generation."""
        # Create test memories
        for i in range(3):
            memory = MemoryEntry(
                id=str(uuid.uuid4()),
                session_id="test_session",
                agent_id=f"agent_{i}",
                memory_type=MemoryType.CONTEXT,
                title=f"Memory {i}",
                content=f"Content {i}",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )
            temp_db.store_memory(memory)

        # Get stats
        stats = temp_db.get_stats()
        assert stats["total_memories"] == 3
        assert stats["total_sessions"] == 1
        assert "memory_types" in stats
        assert "top_agents" in stats
        assert "db_size_bytes" in stats


class TestMemoryManager:
    """Test the high-level memory manager interface."""

    @pytest.fixture
    def temp_manager(self):
        """Create temporary memory manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "test_memory.db")
            yield MemoryManager(db_path=db_path, session_id="test_session")

    def test_manager_initialization(self, temp_manager):
        """Test memory manager initialization."""
        assert temp_manager.session_id == "test_session"
        assert temp_manager.db is not None

    def test_store_and_retrieve_basic(self, temp_manager):
        """Test basic store and retrieve operations."""
        # Store memory
        memory_id = temp_manager.store(
            agent_id="test_agent",
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.CONTEXT,
            metadata={"key": "value"},
            tags=["test"],
            importance=8,
        )

        assert memory_id is not None

        # Retrieve by ID
        memory = temp_manager.get(memory_id)
        assert memory is not None
        assert memory.title == "Test Memory"
        assert memory.content == "This is test content"
        assert memory.metadata["key"] == "value"
        assert memory.tags == ["test"]
        assert memory.importance == 8

        # Retrieve by search
        memories = temp_manager.retrieve(agent_id="test_agent")
        assert len(memories) == 1
        assert memories[0].id == memory_id

    def test_string_memory_type(self, temp_manager):
        """Test using string memory types."""
        memory_id = temp_manager.store(
            agent_id="test_agent",
            title="Decision Memory",
            content="Decision content",
            memory_type="decision",  # String instead of enum
        )

        memory = temp_manager.get(memory_id)
        assert memory.memory_type == MemoryType.DECISION

    def test_memory_expiration(self, temp_manager):
        """Test memory expiration functionality."""
        # Store memory with short expiration
        memory_id = temp_manager.store(
            agent_id="test_agent",
            title="Expiring Memory",
            content="This will expire soon",
            expires_in=timedelta(milliseconds=100),
        )

        # Memory should exist initially
        memory = temp_manager.get(memory_id)
        assert memory is not None

        # Wait for expiration
        time.sleep(0.2)

        # Cleanup expired memories
        cleaned_count = temp_manager.cleanup_expired()
        assert cleaned_count == 1

        # Memory should no longer exist
        memory = temp_manager.get(memory_id)
        assert memory is None

    def test_batch_operations(self, temp_manager):
        """Test batch store operations."""
        memories_data = [
            {
                "agent_id": "agent1",
                "title": "Memory 1",
                "content": "Content 1",
                "memory_type": "context",
                "importance": 5,
            },
            {
                "agent_id": "agent1",
                "title": "Memory 2",
                "content": "Content 2",
                "memory_type": "decision",
                "tags": ["important"],
            },
            {
                "agent_id": "agent2",
                "title": "Memory 3",
                "content": "Content 3",
                "memory_type": "pattern",
            },
        ]

        # Store batch
        memory_ids = temp_manager.store_batch(memories_data)
        assert len(memory_ids) == 3
        assert all(mid is not None for mid in memory_ids)

        # Verify all stored
        all_memories = temp_manager.retrieve()
        assert len(all_memories) == 3

        # Test agent filtering
        agent1_memories = temp_manager.retrieve(agent_id="agent1")
        assert len(agent1_memories) == 2

    def test_search_functionality(self, temp_manager):
        """Test search capabilities."""
        # Store test memories
        temp_manager.store(
            agent_id="agent1",
            title="Database Design",
            content="SQLite schema for memory system",
            memory_type="pattern",
            tags=["database", "design"],
        )

        temp_manager.store(
            agent_id="agent1",
            title="API Architecture",
            content="REST API design patterns",
            memory_type="decision",
            tags=["api", "design"],
        )

        # Search by content
        results = temp_manager.search("SQLite")
        assert len(results) == 1
        assert results[0].title == "Database Design"

        # Search by title
        results = temp_manager.search("API")
        assert len(results) == 1
        assert results[0].title == "API Architecture"

        # Filter by tags
        results = temp_manager.retrieve(tags=["design"])
        assert len(results) == 2

        # Filter by memory type
        results = temp_manager.retrieve(memory_type="decision")
        assert len(results) == 1
        assert results[0].title == "API Architecture"

    def test_memory_update(self, temp_manager):
        """Test memory update functionality."""
        # Store initial memory
        memory_id = temp_manager.store(
            agent_id="test_agent",
            title="Original Title",
            content="Original content",
            importance=5,
        )

        # Update memory
        success = temp_manager.update(
            memory_id,
            title="Updated Title",
            content="Updated content",
            importance=8,
            tags=["updated"],
        )
        assert success is True

        # Verify updates
        memory = temp_manager.get(memory_id)
        assert memory.title == "Updated Title"
        assert memory.content == "Updated content"
        assert memory.importance == 8
        assert memory.tags == ["updated"]

    def test_session_isolation(self):
        """Test that sessions are properly isolated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "test_memory.db")

            # Create two managers with different sessions
            manager1 = MemoryManager(db_path=db_path, session_id="session1")
            manager2 = MemoryManager(db_path=db_path, session_id="session2")

            # Store memory in session 1
            memory_id1 = manager1.store(
                agent_id="agent1",
                title="Session 1 Memory",
                content="Content for session 1",
            )

            # Store memory in session 2
            memory_id2 = manager2.store(
                agent_id="agent1",
                title="Session 2 Memory",
                content="Content for session 2",
            )

            # Verify session isolation
            session1_memories = manager1.retrieve()
            session2_memories = manager2.retrieve()

            assert len(session1_memories) == 1
            assert len(session2_memories) == 1
            assert session1_memories[0].id != session2_memories[0].id

            # Verify cross-session access is blocked
            assert manager1.get(memory_id2) is None
            assert manager2.get(memory_id1) is None

    def test_context_manager(self, temp_manager):
        """Test context manager functionality."""
        with temp_manager as manager:
            manager.store(
                agent_id="test_agent",
                title="Context Test",
                content="Testing context manager",
            )

        # Context manager should handle cleanup
        assert True  # Just test that no exceptions occur


class TestMemoryMaintenance:
    """Test memory maintenance operations."""

    @pytest.fixture
    def temp_maintenance(self):
        """Create temporary maintenance system for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_memory.db"
            yield MemoryMaintenance(db_path)

    def test_cleanup_expired_memories(self, temp_maintenance):
        """Test cleanup of expired memories."""
        # Create memories with different expiration times
        db = temp_maintenance.db

        # Expired memory
        expired_memory = MemoryEntry(
            id=str(uuid.uuid4()),
            session_id="test_session",
            agent_id="test_agent",
            memory_type=MemoryType.CONTEXT,
            title="Expired Memory",
            content="Expired content",
            metadata={},
            created_at=datetime.now() - timedelta(hours=2),
            accessed_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1),
        )

        # Active memory
        active_memory = MemoryEntry(
            id=str(uuid.uuid4()),
            session_id="test_session",
            agent_id="test_agent",
            memory_type=MemoryType.CONTEXT,
            title="Active Memory",
            content="Active content",
            metadata={},
            created_at=datetime.now(),
            accessed_at=datetime.now(),
        )

        db.store_memory(expired_memory)
        db.store_memory(active_memory)

        # Run cleanup
        result = temp_maintenance.cleanup_expired()
        assert result["expired_memories_removed"] == 1
        assert "cleanup_duration_ms" in result

    def test_analyze_memory_usage(self, temp_maintenance):
        """Test memory usage analysis."""
        # Create test data
        db = temp_maintenance.db
        for i in range(5):
            memory = MemoryEntry(
                id=str(uuid.uuid4()),
                session_id=f"session_{i % 2}",
                agent_id=f"agent_{i % 3}",
                memory_type=MemoryType.CONTEXT,
                title=f"Memory {i}",
                content=f"Content {i}",
                metadata={},
                created_at=datetime.now() - timedelta(hours=i),
                accessed_at=datetime.now() - timedelta(hours=i),
            )
            db.store_memory(memory)

        # Analyze usage
        analysis = temp_maintenance.analyze_memory_usage()
        assert analysis["total_memories"] == 5
        assert analysis["total_sessions"] == 2
        assert "memory_age_distribution" in analysis
        assert "recommendations" in analysis

    def test_vacuum_database(self, temp_maintenance):
        """Test database vacuum operation."""
        # Add some data first
        db = temp_maintenance.db
        for i in range(10):
            memory = MemoryEntry(
                id=str(uuid.uuid4()),
                session_id="test_session",
                agent_id="test_agent",
                memory_type=MemoryType.CONTEXT,
                title=f"Memory {i}",
                content=f"Content {i}" * 100,  # Larger content
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )
            db.store_memory(memory)

        # Run vacuum
        result = temp_maintenance.vacuum_database()
        assert result["success"] is True
        assert "size_before_bytes" in result
        assert "size_after_bytes" in result
        assert "vacuum_duration_ms" in result

    def test_full_maintenance(self, temp_maintenance):
        """Test comprehensive maintenance run."""
        # Create test data with some expired memories
        db = temp_maintenance.db

        # Add regular memory
        memory = MemoryEntry(
            id=str(uuid.uuid4()),
            session_id="test_session",
            agent_id="test_agent",
            memory_type=MemoryType.CONTEXT,
            title="Regular Memory",
            content="Regular content",
            metadata={},
            created_at=datetime.now(),
            accessed_at=datetime.now(),
        )
        db.store_memory(memory)

        # Add expired memory
        expired_memory = MemoryEntry(
            id=str(uuid.uuid4()),
            session_id="test_session",
            agent_id="test_agent",
            memory_type=MemoryType.CONTEXT,
            title="Expired Memory",
            content="Expired content",
            metadata={},
            created_at=datetime.now() - timedelta(hours=1),
            accessed_at=datetime.now() - timedelta(hours=1),
            expires_at=datetime.now() - timedelta(minutes=30),
        )
        db.store_memory(expired_memory)

        # Run full maintenance
        result = temp_maintenance.run_full_maintenance(
            cleanup_expired=True,
            vacuum=True,
            optimize=True,
        )

        assert "expired_cleanup" in result
        assert "vacuum" in result
        assert "optimization" in result
        assert "final_analysis" in result
        assert result["expired_cleanup"]["expired_memories_removed"] == 1

    def test_export_session_memories(self, temp_maintenance):
        """Test session memory export functionality."""
        # Create test memories
        db = temp_maintenance.db
        session_id = "export_test_session"

        for i in range(3):
            memory = MemoryEntry(
                id=str(uuid.uuid4()),
                session_id=session_id,
                agent_id=f"agent_{i}",
                memory_type=MemoryType.CONTEXT,
                title=f"Export Memory {i}",
                content=f"Export content {i}",
                metadata={"index": i},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )
            db.store_memory(memory)

        # Export session
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "export.json"
            result = temp_maintenance.export_session_memories(session_id, export_path)

            assert result["success"] is True
            assert result["exported_memories"] == 3
            assert export_path.exists()

            # Verify export content
            with export_path.open() as f:
                export_data = json.load(f)

            assert export_data["session_id"] == session_id
            assert export_data["memory_count"] == 3
            assert len(export_data["memories"]) == 3


class TestMemoryModels:
    """Test memory model functionality."""

    def test_memory_entry_serialization(self):
        """Test memory entry JSON serialization."""
        memory = MemoryEntry(
            id="test_id",
            session_id="test_session",
            agent_id="test_agent",
            memory_type=MemoryType.CONTEXT,
            title="Test Memory",
            content="Test content",
            metadata={"key": "value"},
            tags=["test"],
            importance=7,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            accessed_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        # Test to_dict
        memory_dict = memory.to_dict()
        assert memory_dict["id"] == "test_id"
        assert memory_dict["memory_type"] == "context"
        assert memory_dict["metadata"]["key"] == "value"

        # Test from_dict
        reconstructed = MemoryEntry.from_dict(memory_dict)
        assert reconstructed.id == memory.id
        assert reconstructed.memory_type == memory.memory_type
        assert reconstructed.metadata == memory.metadata

        # Test JSON round trip
        json_str = memory.to_json()
        from_json = MemoryEntry.from_json(json_str)
        assert from_json.id == memory.id
        assert from_json.title == memory.title

    def test_memory_query_sql_generation(self):
        """Test memory query SQL generation."""
        query = MemoryQuery(
            session_id="test_session",
            agent_id="test_agent",
            memory_type=MemoryType.DECISION,
            min_importance=5,
            content_search="test content",
        )

        where_clause, params = query.to_sql_where()
        assert "session_id = ?" in where_clause
        assert "agent_id = ?" in where_clause
        assert "memory_type = ?" in where_clause
        assert "importance >= ?" in where_clause
        assert "LIKE ?" in where_clause

        assert "test_session" in params
        assert "test_agent" in params
        assert "decision" in params
        assert 5 in params


@pytest.mark.performance
class TestMemoryPerformance:
    """Test memory system performance requirements."""

    @pytest.fixture
    def perf_manager(self):
        """Create memory manager for performance testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "perf_memory.db")
            yield MemoryManager(db_path=db_path)

    def test_storage_performance(self, perf_manager):
        """Test that storage operations complete within 50ms."""
        # Store multiple memories and measure time
        start_time = time.time()

        for i in range(10):
            perf_manager.store(
                agent_id="perf_agent",
                title=f"Performance Test {i}",
                content=f"Performance test content {i}" * 10,
                memory_type=MemoryType.CONTEXT,
                importance=i % 10 + 1,
            )

        end_time = time.time()
        avg_time_ms = ((end_time - start_time) / 10) * 1000

        # Should average less than 50ms per operation
        assert avg_time_ms < 50, f"Average storage time {avg_time_ms:.2f}ms exceeds 50ms limit"

    def test_retrieval_performance(self, perf_manager):
        """Test that retrieval operations complete within 50ms."""
        # Setup: Store many memories
        for i in range(100):
            perf_manager.store(
                agent_id=f"agent_{i % 5}",
                title=f"Memory {i}",
                content=f"Content {i}" * 5,
                memory_type=MemoryType.CONTEXT,
                importance=i % 10 + 1,
                tags=[f"tag_{i % 3}"],
            )

        # Test retrieval performance
        start_time = time.time()

        # Various query types
        queries = [
            {"agent_id": "agent_0"},
            {"memory_type": "context"},
            {"min_importance": 7},
            {"tags": ["tag_1"]},
            {"search": "Content 50"},
        ]

        for query_params in queries:
            perf_manager.retrieve(**query_params)

        end_time = time.time()
        avg_time_ms = ((end_time - start_time) / len(queries)) * 1000

        # Should average less than 50ms per operation
        assert avg_time_ms < 50, f"Average retrieval time {avg_time_ms:.2f}ms exceeds 50ms limit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
