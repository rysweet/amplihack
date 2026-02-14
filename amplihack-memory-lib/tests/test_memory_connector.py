"""
Unit tests for MemoryConnector - Connection management and database lifecycle.

All tests are written to FAIL initially (TDD approach).
"""

from datetime import datetime
from pathlib import Path

import pytest
from amplihack_memory import Experience, ExperienceType, MemoryConnector


class TestMemoryConnectorInitialization:
    """Test connector initialization and configuration."""

    def test_creates_connector_with_agent_name(self):
        """MemoryConnector initializes with agent name."""
        connector = MemoryConnector(agent_name="test-agent")
        assert connector.agent_name == "test-agent"

    def test_creates_default_storage_path(self):
        """Connector creates default storage path in ~/.amplihack/memory/."""
        connector = MemoryConnector(agent_name="test-agent")
        expected_path = Path.home() / ".amplihack" / "memory" / "test-agent"
        assert connector.storage_path == expected_path

    def test_accepts_custom_storage_path(self):
        """Connector accepts custom storage path."""
        custom_path = Path("/tmp/test-memory")
        connector = MemoryConnector(agent_name="test-agent", storage_path=custom_path)
        assert connector.storage_path == custom_path

    def test_creates_storage_directory_on_init(self):
        """Connector creates storage directory if it doesn't exist."""
        custom_path = Path("/tmp/test-memory-new")
        connector = MemoryConnector(agent_name="test-agent", storage_path=custom_path)
        assert custom_path.exists()
        assert custom_path.is_dir()

    def test_sets_default_max_memory(self):
        """Connector defaults to 100MB max memory."""
        connector = MemoryConnector(agent_name="test-agent")
        assert connector.max_memory_mb == 100

    def test_accepts_custom_max_memory(self):
        """Connector accepts custom max memory limit."""
        connector = MemoryConnector(agent_name="test-agent", max_memory_mb=250)
        assert connector.max_memory_mb == 250

    def test_enables_compression_by_default(self):
        """Connector enables compression by default."""
        connector = MemoryConnector(agent_name="test-agent")
        assert connector.enable_compression is True

    def test_can_disable_compression(self):
        """Connector can disable compression."""
        connector = MemoryConnector(agent_name="test-agent", enable_compression=False)
        assert connector.enable_compression is False


class TestMemoryConnectorDatabaseLifecycle:
    """Test database creation, connection, and cleanup."""

    def test_creates_sqlite_database_file(self):
        """Connector creates SQLite database file on first use."""
        custom_path = Path("/tmp/test-memory-db")
        connector = MemoryConnector(agent_name="test-agent", storage_path=custom_path)
        db_file = custom_path / "experiences.db"
        assert db_file.exists()
        assert db_file.is_file()

    def test_creates_experiences_table(self):
        """Connector creates experiences table with correct schema."""
        connector = MemoryConnector(agent_name="test-agent")
        # Query schema
        cursor = connector._connection.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='experiences'")
        schema = cursor.fetchone()[0]

        assert "experience_id TEXT PRIMARY KEY" in schema
        assert "agent_name TEXT NOT NULL" in schema
        assert "experience_type TEXT NOT NULL" in schema
        assert "context TEXT NOT NULL" in schema
        assert "outcome TEXT NOT NULL" in schema
        assert "confidence REAL NOT NULL" in schema
        assert "timestamp INTEGER NOT NULL" in schema

    def test_creates_required_indexes(self):
        """Connector creates indexes for fast retrieval."""
        connector = MemoryConnector(agent_name="test-agent")
        cursor = connector._connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        assert "idx_agent_name" in indexes
        assert "idx_experience_type" in indexes
        assert "idx_timestamp" in indexes
        assert "idx_confidence" in indexes
        assert "idx_agent_type" in indexes

    def test_creates_fulltext_search_index(self):
        """Connector creates FTS5 virtual table for full-text search."""
        connector = MemoryConnector(agent_name="test-agent")
        cursor = connector._connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='experiences_fts'"
        )
        assert cursor.fetchone() is not None

    def test_reuses_existing_database(self):
        """Connector reuses existing database without recreating."""
        custom_path = Path("/tmp/test-memory-reuse")

        # Create first connector and store experience
        connector1 = MemoryConnector(agent_name="test-agent", storage_path=custom_path)
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test context",
            outcome="Test outcome",
            confidence=0.8,
            timestamp=datetime.now(),
        )
        exp_id = connector1.store_experience(exp)

        # Create second connector to same location
        connector2 = MemoryConnector(agent_name="test-agent", storage_path=custom_path)

        # Should retrieve the previously stored experience
        experiences = connector2.retrieve_experiences()
        assert len(experiences) == 1
        assert experiences[0].experience_id == exp_id

    def test_closes_connection_properly(self):
        """Connector closes database connection on close()."""
        connector = MemoryConnector(agent_name="test-agent")
        connector.close()

        # Attempting to use closed connection should fail
        with pytest.raises(Exception):
            connector.retrieve_experiences()

    def test_context_manager_support(self):
        """Connector supports context manager protocol."""
        custom_path = Path("/tmp/test-memory-context")

        with MemoryConnector(agent_name="test-agent", storage_path=custom_path) as connector:
            exp = Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Test",
                outcome="Result",
                confidence=0.9,
                timestamp=datetime.now(),
            )
            connector.store_experience(exp)

        # Connection should be closed after exiting context
        # But data should persist
        connector2 = MemoryConnector(agent_name="test-agent", storage_path=custom_path)
        experiences = connector2.retrieve_experiences()
        assert len(experiences) == 1


class TestMemoryConnectorIsolation:
    """Test agent memory isolation."""

    def test_agent_memories_are_isolated(self):
        """Different agents have isolated memory storage."""
        connector1 = MemoryConnector(agent_name="agent-1")
        connector2 = MemoryConnector(agent_name="agent-2")

        # Store experience for agent-1
        exp1 = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Agent 1 experience",
            outcome="Agent 1 result",
            confidence=0.8,
            timestamp=datetime.now(),
        )
        connector1.store_experience(exp1)

        # Store experience for agent-2
        exp2 = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Agent 2 experience",
            outcome="Agent 2 result",
            confidence=0.9,
            timestamp=datetime.now(),
        )
        connector2.store_experience(exp2)

        # Each agent should only see their own experiences
        agent1_exps = connector1.retrieve_experiences()
        agent2_exps = connector2.retrieve_experiences()

        assert len(agent1_exps) == 1
        assert len(agent2_exps) == 1
        assert agent1_exps[0].context == "Agent 1 experience"
        assert agent2_exps[0].context == "Agent 2 experience"

    def test_agent_cannot_access_other_agent_storage(self):
        """Agent cannot retrieve experiences from another agent."""
        connector1 = MemoryConnector(agent_name="agent-secure")

        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Secure data",
            outcome="Sensitive result",
            confidence=0.95,
            timestamp=datetime.now(),
        )
        connector1.store_experience(exp)

        # Try to access with different agent name
        connector2 = MemoryConnector(agent_name="agent-intruder")
        intruder_exps = connector2.retrieve_experiences()

        # Should not see agent-secure's experiences
        assert len(intruder_exps) == 0


class TestMemoryConnectorErrorHandling:
    """Test error handling and validation."""

    def test_raises_on_invalid_agent_name(self):
        """Connector raises error for invalid agent names."""
        with pytest.raises(ValueError):
            MemoryConnector(agent_name="")

        with pytest.raises(ValueError):
            MemoryConnector(agent_name=" ")

        with pytest.raises(ValueError):
            MemoryConnector(agent_name=None)

    def test_raises_on_invalid_max_memory(self):
        """Connector raises error for invalid max_memory_mb values."""
        with pytest.raises(ValueError):
            MemoryConnector(agent_name="test", max_memory_mb=0)

        with pytest.raises(ValueError):
            MemoryConnector(agent_name="test", max_memory_mb=-100)

    def test_raises_on_storage_permission_error(self):
        """Connector raises error when storage path is not writable."""
        read_only_path = Path("/root/no-permission")

        with pytest.raises(PermissionError):
            MemoryConnector(agent_name="test", storage_path=read_only_path)

    def test_handles_corrupted_database_gracefully(self):
        """Connector handles corrupted database file gracefully."""
        custom_path = Path("/tmp/test-memory-corrupt")
        custom_path.mkdir(parents=True, exist_ok=True)

        # Create corrupted database file
        db_file = custom_path / "experiences.db"
        db_file.write_text("This is not a valid SQLite database")

        # Should detect corruption and either recover or fail cleanly
        with pytest.raises(Exception) as exc_info:
            MemoryConnector(agent_name="test", storage_path=custom_path)

        # Should provide helpful error message
        assert (
            "corrupted" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
        )


class TestMemoryConnectorPerformance:
    """Test performance characteristics."""

    def test_initialization_is_fast(self):
        """Connector initializes in less than 100ms."""
        import time

        start = time.time()
        connector = MemoryConnector(agent_name="perf-test")
        elapsed = (time.time() - start) * 1000  # Convert to ms

        assert elapsed < 100

    def test_handles_concurrent_access(self):
        """Connector handles concurrent access from multiple threads."""
        import threading

        connector = MemoryConnector(agent_name="concurrent-test")
        errors = []

        def store_experiences(thread_id):
            try:
                for i in range(10):
                    exp = Experience(
                        experience_type=ExperienceType.SUCCESS,
                        context=f"Thread {thread_id} experience {i}",
                        outcome="Result",
                        confidence=0.8,
                        timestamp=datetime.now(),
                    )
                    connector.store_experience(exp)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=store_experiences, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should handle concurrent access without errors
        assert len(errors) == 0

        # Should have stored all experiences
        experiences = connector.retrieve_experiences()
        assert len(experiences) == 40  # 4 threads * 10 experiences each
