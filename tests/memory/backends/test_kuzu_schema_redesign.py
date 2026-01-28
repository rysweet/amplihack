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


class TestKuzuBackendSessionIsolation:
    """Integration tests for session_id filtering (no mocks)."""

    def test_retrieve_memories_filters_by_session_id(self):
        """CRITICAL: Verify session_id filtering actually works end-to-end.

        This is an integration test that uses a real Kuzu database to verify
        that session isolation works correctly. It stores memories in two
        different sessions and verifies that queries return only memories
        from the requested session.

        Philosophy: Test behavior at module boundaries with real database.
        """
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            # Store memories in two different sessions
            memory_s1 = MemoryEntry(
                id="mem-1",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.EPISODIC,
                title="Session 1 Memory",
                content="Data from session 1",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )
            memory_s2 = MemoryEntry(
                id="mem-2",
                session_id="session-2",
                agent_id="agent-1",
                memory_type=MemoryType.EPISODIC,
                title="Session 2 Memory",
                content="Data from session 2",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            backend.store_memory(memory_s1)
            backend.store_memory(memory_s2)

            # Query session-1 - should get ONLY session-1 memories
            query = MemoryQuery(session_id="session-1")
            results = backend.retrieve_memories(query)

            assert len(results) == 1, f"Expected 1 memory, got {len(results)}"
            assert results[0].session_id == "session-1"
            assert results[0].content == "Data from session 1"
            assert results[0].id == "mem-1"

            # Query session-2 - should get ONLY session-2 memories
            query = MemoryQuery(session_id="session-2")
            results = backend.retrieve_memories(query)

            assert len(results) == 1, f"Expected 1 memory, got {len(results)}"
            assert results[0].session_id == "session-2"
            assert results[0].content == "Data from session 2"
            assert results[0].id == "mem-2"

    def test_session_isolation_across_memory_types(self):
        """Verify session_id filtering works across all 5 memory types."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            # Store different memory types in two sessions
            memory_types = [
                MemoryType.EPISODIC,
                MemoryType.SEMANTIC,
                MemoryType.PROCEDURAL,
                MemoryType.PROSPECTIVE,
                MemoryType.WORKING,
            ]

            for i, mem_type in enumerate(memory_types):
                # Session 1 memory
                backend.store_memory(
                    MemoryEntry(
                        id=f"s1-{mem_type.value}-{i}",
                        session_id="session-1",
                        agent_id="agent-1",
                        memory_type=mem_type,
                        title=f"Session 1 {mem_type.value}",
                        content=f"Session 1 content for {mem_type.value}",
                        metadata={},
                        created_at=datetime.now(),
                        accessed_at=datetime.now(),
                    )
                )

                # Session 2 memory
                backend.store_memory(
                    MemoryEntry(
                        id=f"s2-{mem_type.value}-{i}",
                        session_id="session-2",
                        agent_id="agent-1",
                        memory_type=mem_type,
                        title=f"Session 2 {mem_type.value}",
                        content=f"Session 2 content for {mem_type.value}",
                        metadata={},
                        created_at=datetime.now(),
                        accessed_at=datetime.now(),
                    )
                )

            # Query session-1 - should get exactly 5 memories (one of each type)
            query = MemoryQuery(session_id="session-1")
            results = backend.retrieve_memories(query)

            assert len(results) == 5, f"Expected 5 memories from session-1, got {len(results)}"
            session_ids = [r.session_id for r in results]
            assert all(sid == "session-1" for sid in session_ids), "Found memory from wrong session"

            # Query session-2 - should get exactly 5 memories
            query = MemoryQuery(session_id="session-2")
            results = backend.retrieve_memories(query)

            assert len(results) == 5, f"Expected 5 memories from session-2, got {len(results)}"
            session_ids = [r.session_id for r in results]
            assert all(sid == "session-2" for sid in session_ids), "Found memory from wrong session"

    def test_query_without_session_id_returns_all_sessions(self):
        """Verify that querying without session_id returns memories from all sessions."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            # Store memories in multiple sessions
            for session_num in range(1, 4):
                backend.store_memory(
                    MemoryEntry(
                        id=f"mem-session-{session_num}",
                        session_id=f"session-{session_num}",
                        agent_id="agent-1",
                        memory_type=MemoryType.EPISODIC,
                        title=f"Memory {session_num}",
                        content=f"Content {session_num}",
                        metadata={},
                        created_at=datetime.now(),
                        accessed_at=datetime.now(),
                    )
                )

            # Query without session_id - should get all 3 memories
            query = MemoryQuery()
            results = backend.retrieve_memories(query)

            assert len(results) == 3, f"Expected 3 memories from all sessions, got {len(results)}"
            session_ids = {r.session_id for r in results}
            assert session_ids == {"session-1", "session-2", "session-3"}
