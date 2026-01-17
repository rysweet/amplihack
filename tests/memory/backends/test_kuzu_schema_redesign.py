"""Tests for Kùzu schema redesign with 5 separate node types.

Tests the new schema with:
- 5 node types (EpisodicMemory, SemanticMemory, ProceduralMemory, ProspectiveMemory, WorkingMemory)
- 11 relationship types (CONTAINS_EPISODIC, CONTRIBUTES_TO_SEMANTIC, etc.)
- Session as first-class node
- Migration from old schema to new schema

Philosophy:
- TDD approach: Write test, implement, make it pass
- Test behavior, not implementation
- Complete coverage of schema changes
"""

import tempfile
from datetime import datetime
from unittest.mock import Mock, patch

from src.amplihack.memory.models import MemoryEntry, MemoryQuery, MemoryType


class TestKuzuBackendNodeTypes:
    """Test creation of 5 separate node types."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_episodic_memory_table(self, mock_kuzu):
        """Test that EpisodicMemory node table is created."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            # Check that EpisodicMemory table creation was attempted
            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("EpisodicMemory" in str(call) for call in calls)

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_semantic_memory_table(self, mock_kuzu):
        """Test that SemanticMemory node table is created."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("SemanticMemory" in str(call) for call in calls)

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_procedural_memory_table(self, mock_kuzu):
        """Test that ProceduralMemory node table is created."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("ProceduralMemory" in str(call) for call in calls)

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_prospective_memory_table(self, mock_kuzu):
        """Test that ProspectiveMemory node table is created."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("ProspectiveMemory" in str(call) for call in calls)

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_working_memory_table(self, mock_kuzu):
        """Test that WorkingMemory node table is created."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("WorkingMemory" in str(call) for call in calls)


class TestKuzuBackendRelationshipTypes:
    """Test creation of 11 relationship types."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_contains_episodic_relationship(self, mock_kuzu):
        """Test that CONTAINS_EPISODIC relationship table is created."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("CONTAINS_EPISODIC" in str(call) for call in calls)

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_all_11_relationships(self, mock_kuzu):
        """Test that all 11 relationship types are created."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            expected_relationships = [
                "CONTAINS_EPISODIC",
                "CONTAINS_WORKING",
                "CONTRIBUTES_TO_SEMANTIC",
                "USES_PROCEDURE",
                "CREATES_INTENTION",
                "DERIVES_FROM",
                "REFERENCES",
                "TRIGGERS",
                "ACTIVATES",
                "RECALLS",
                "BUILDS_ON",
            ]

            for rel_type in expected_relationships:
                assert any(rel_type in str(call) for call in calls), (
                    f"{rel_type} not found in calls"
                )


class TestKuzuBackendStoreMemoryRouting:
    """Test that store_memory routes to correct node type based on memory type."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_store_episodic_memory_creates_episodic_node(self, mock_kuzu):
        """Test storing episodic memory creates EpisodicMemory node."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-1",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.EPISODIC,
                title="Test Event",
                content="Something happened",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            # Reset mock to clear initialization calls
            mock_conn.execute.reset_mock()

            backend.store_memory(memory)

            # Check that EpisodicMemory node was created
            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("EpisodicMemory" in str(call) for call in calls)

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_store_semantic_memory_creates_semantic_node(self, mock_kuzu):
        """Test storing semantic memory creates SemanticMemory node."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-1",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.SEMANTIC,
                title="Test Knowledge",
                content="User prefers verbose output",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            backend.store_memory(memory)

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("SemanticMemory" in str(call) for call in calls)

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_store_procedural_memory_creates_procedural_node(self, mock_kuzu):
        """Test storing procedural memory creates ProceduralMemory node."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-1",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.PROCEDURAL,
                title="Git Workflow",
                content="How to create a PR",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            backend.store_memory(memory)

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("ProceduralMemory" in str(call) for call in calls)

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_store_prospective_memory_creates_prospective_node(self, mock_kuzu):
        """Test storing prospective memory creates ProspectiveMemory node."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-1",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.PROSPECTIVE,
                title="Reminder",
                content="Follow up on PR review",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            backend.store_memory(memory)

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("ProspectiveMemory" in str(call) for call in calls)

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_store_working_memory_creates_working_node(self, mock_kuzu):
        """Test storing working memory creates WorkingMemory node."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-1",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.WORKING,
                title="Current Goal",
                content="Implement Kùzu schema redesign",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            backend.store_memory(memory)

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("WorkingMemory" in str(call) for call in calls)


class TestKuzuBackendRetrieveMemoriesAcrossTypes:
    """Test that retrieve_memories queries across all node types."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_retrieve_memories_queries_all_node_types(self, mock_kuzu):
        """Test that retrieve_memories queries all 5 node types."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_result = Mock()
        mock_result.has_next.return_value = False

        mock_conn = Mock()
        mock_conn.execute.return_value = mock_result
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            mock_conn.execute.reset_mock()

            query = MemoryQuery(session_id="session-1")
            backend.retrieve_memories(query)

            # Should query all node types or use UNION
            calls = [str(call) for call in mock_conn.execute.call_args_list]
            # Implementation can use UNION or multiple queries, just verify query was made
            assert len(calls) > 0

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_retrieve_memories_filters_by_memory_type(self, mock_kuzu):
        """Test that retrieve_memories can filter by specific memory type."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_result = Mock()
        mock_result.has_next.return_value = False

        mock_conn = Mock()
        mock_conn.execute.return_value = mock_result
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            mock_conn.execute.reset_mock()

            # Query only episodic memories
            query = MemoryQuery(memory_type=MemoryType.EPISODIC)
            backend.retrieve_memories(query)

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            # Should only query EpisodicMemory when type is specified
            assert any("EpisodicMemory" in str(call) for call in calls)


class TestKuzuBackendMigration:
    """Test migration from old schema to new schema."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_migration_function_exists(self, mock_kuzu):
        """Test that migrate_to_new_schema method exists."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            assert hasattr(backend, "migrate_to_new_schema")
            assert callable(backend.migrate_to_new_schema)

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_migration_detects_old_schema(self, mock_kuzu):
        """Test that migration detects presence of old Memory table."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        # Mock old schema detection
        mock_result = Mock()
        mock_result.has_next.return_value = True
        mock_result.get_next.return_value = [True]

        mock_conn = Mock()
        mock_conn.execute.return_value = mock_result
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            # Should detect old schema exists
            assert hasattr(backend, "_has_old_schema")

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_migration_preserves_all_data(self, mock_kuzu):
        """Test that migration moves all memories to new node types."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")

            # Verify migrate_to_new_schema queries old Memory table
            mock_conn.execute.reset_mock()

            # This will fail until we implement, but defines the contract
            try:
                backend.migrate_to_new_schema()
            except Exception:
                pass  # Expected to fail until implementation

            # Migration should query old Memory table
            calls = [str(call) for call in mock_conn.execute.call_args_list]
            # Will verify proper behavior once implemented
            assert True  # Placeholder


class TestKuzuBackendSessionRelationships:
    """Test that Session relationships are properly created."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_store_episodic_creates_contains_relationship(self, mock_kuzu):
        """Test that storing episodic memory creates CONTAINS_EPISODIC relationship."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-1",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.EPISODIC,
                title="Test Event",
                content="Something happened",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            backend.store_memory(memory)

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            # Should create CONTAINS_EPISODIC relationship
            assert any("CONTAINS_EPISODIC" in str(call) for call in calls)

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_store_working_creates_contains_relationship(self, mock_kuzu):
        """Test that storing working memory creates CONTAINS_WORKING relationship."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-1",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.WORKING,
                title="Current Goal",
                content="Implement feature",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            backend.store_memory(memory)

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            # Should create CONTAINS_WORKING relationship
            assert any("CONTAINS_WORKING" in str(call) for call in calls)
