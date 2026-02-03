"""Integration tests for Kùzu backend session isolation.

Tests that session_id properly isolates memories between different sessions.

Philosophy:
- Test real behavior with actual database
- Verify session isolation across all 5 memory types
- Ensure queries filter by session_id correctly
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.amplihack.memory.backends.kuzu_backend import KuzuBackend
from src.amplihack.memory.models import MemoryEntry, MemoryQuery, MemoryType


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_db"
        yield db_path


@pytest.fixture
def backend(temp_db):
    """Create and initialize a KuzuBackend instance."""
    backend = KuzuBackend(db_path=temp_db, enable_auto_linking=False)
    backend.initialize()
    yield backend
    backend.close()


class TestSessionIsolation:
    """Test that memories are properly isolated by session_id."""

    def test_episodic_memory_session_isolation(self, backend):
        """Test that episodic memories from different sessions are isolated."""
        now = datetime.now()

        # Create memories in session-1
        memory1 = MemoryEntry(
            id="episodic-1",
            session_id="session-1",
            agent_id="agent-1",
            memory_type=MemoryType.EPISODIC,
            title="Session 1 Event",
            content="This happened in session 1",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory1)

        # Create memories in session-2
        memory2 = MemoryEntry(
            id="episodic-2",
            session_id="session-2",
            agent_id="agent-1",
            memory_type=MemoryType.EPISODIC,
            title="Session 2 Event",
            content="This happened in session 2",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory2)

        # Query session-1 memories
        query1 = MemoryQuery(session_id="session-1", memory_type=MemoryType.EPISODIC)
        results1 = backend.retrieve_memories(query1)

        # Should only get session-1 memory
        assert len(results1) == 1
        assert results1[0].id == "episodic-1"
        assert results1[0].session_id == "session-1"

        # Query session-2 memories
        query2 = MemoryQuery(session_id="session-2", memory_type=MemoryType.EPISODIC)
        results2 = backend.retrieve_memories(query2)

        # Should only get session-2 memory
        assert len(results2) == 1
        assert results2[0].id == "episodic-2"
        assert results2[0].session_id == "session-2"

    def test_semantic_memory_session_isolation(self, backend):
        """Test that semantic memories from different sessions are isolated."""
        now = datetime.now()

        memory1 = MemoryEntry(
            id="semantic-1",
            session_id="session-1",
            agent_id="agent-1",
            memory_type=MemoryType.SEMANTIC,
            title="Session 1 Knowledge",
            content="User prefers detailed output",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory1)

        memory2 = MemoryEntry(
            id="semantic-2",
            session_id="session-2",
            agent_id="agent-1",
            memory_type=MemoryType.SEMANTIC,
            title="Session 2 Knowledge",
            content="User prefers concise output",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory2)

        # Query each session
        query1 = MemoryQuery(session_id="session-1", memory_type=MemoryType.SEMANTIC)
        results1 = backend.retrieve_memories(query1)
        assert len(results1) == 1
        assert results1[0].id == "semantic-1"

        query2 = MemoryQuery(session_id="session-2", memory_type=MemoryType.SEMANTIC)
        results2 = backend.retrieve_memories(query2)
        assert len(results2) == 1
        assert results2[0].id == "semantic-2"

    def test_procedural_memory_session_isolation(self, backend):
        """Test that procedural memories from different sessions are isolated."""
        now = datetime.now()

        memory1 = MemoryEntry(
            id="procedural-1",
            session_id="session-1",
            agent_id="agent-1",
            memory_type=MemoryType.PROCEDURAL,
            title="Session 1 Procedure",
            content="How to deploy in session 1",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory1)

        memory2 = MemoryEntry(
            id="procedural-2",
            session_id="session-2",
            agent_id="agent-1",
            memory_type=MemoryType.PROCEDURAL,
            title="Session 2 Procedure",
            content="How to deploy in session 2",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory2)

        query1 = MemoryQuery(session_id="session-1", memory_type=MemoryType.PROCEDURAL)
        results1 = backend.retrieve_memories(query1)
        assert len(results1) == 1
        assert results1[0].id == "procedural-1"

        query2 = MemoryQuery(session_id="session-2", memory_type=MemoryType.PROCEDURAL)
        results2 = backend.retrieve_memories(query2)
        assert len(results2) == 1
        assert results2[0].id == "procedural-2"

    def test_prospective_memory_session_isolation(self, backend):
        """Test that prospective memories from different sessions are isolated."""
        now = datetime.now()

        memory1 = MemoryEntry(
            id="prospective-1",
            session_id="session-1",
            agent_id="agent-1",
            memory_type=MemoryType.PROSPECTIVE,
            title="Session 1 Reminder",
            content="Follow up on PR in session 1",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory1)

        memory2 = MemoryEntry(
            id="prospective-2",
            session_id="session-2",
            agent_id="agent-1",
            memory_type=MemoryType.PROSPECTIVE,
            title="Session 2 Reminder",
            content="Follow up on PR in session 2",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory2)

        query1 = MemoryQuery(session_id="session-1", memory_type=MemoryType.PROSPECTIVE)
        results1 = backend.retrieve_memories(query1)
        assert len(results1) == 1
        assert results1[0].id == "prospective-1"

        query2 = MemoryQuery(session_id="session-2", memory_type=MemoryType.PROSPECTIVE)
        results2 = backend.retrieve_memories(query2)
        assert len(results2) == 1
        assert results2[0].id == "prospective-2"

    def test_working_memory_session_isolation(self, backend):
        """Test that working memories from different sessions are isolated."""
        now = datetime.now()

        memory1 = MemoryEntry(
            id="working-1",
            session_id="session-1",
            agent_id="agent-1",
            memory_type=MemoryType.WORKING,
            title="Session 1 Goal",
            content="Implement feature X",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory1)

        memory2 = MemoryEntry(
            id="working-2",
            session_id="session-2",
            agent_id="agent-1",
            memory_type=MemoryType.WORKING,
            title="Session 2 Goal",
            content="Implement feature Y",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory2)

        query1 = MemoryQuery(session_id="session-1", memory_type=MemoryType.WORKING)
        results1 = backend.retrieve_memories(query1)
        assert len(results1) == 1
        assert results1[0].id == "working-1"

        query2 = MemoryQuery(session_id="session-2", memory_type=MemoryType.WORKING)
        results2 = backend.retrieve_memories(query2)
        assert len(results2) == 1
        assert results2[0].id == "working-2"

    def test_cross_session_query_returns_all(self, backend):
        """Test that queries without session_id return memories from all sessions."""
        now = datetime.now()

        # Create memories in multiple sessions
        memory1 = MemoryEntry(
            id="episodic-1",
            session_id="session-1",
            agent_id="agent-1",
            memory_type=MemoryType.EPISODIC,
            title="Session 1 Event",
            content="Event 1",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory1)

        memory2 = MemoryEntry(
            id="episodic-2",
            session_id="session-2",
            agent_id="agent-1",
            memory_type=MemoryType.EPISODIC,
            title="Session 2 Event",
            content="Event 2",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory2)

        # Query without session_id filter
        query = MemoryQuery(memory_type=MemoryType.EPISODIC)
        results = backend.retrieve_memories(query)

        # Should get memories from both sessions
        assert len(results) == 2
        session_ids = {r.session_id for r in results}
        assert session_ids == {"session-1", "session-2"}

    def test_get_memory_by_id_preserves_session_id(self, backend):
        """Test that retrieving by ID preserves the session_id."""
        now = datetime.now()

        memory = MemoryEntry(
            id="test-id",
            session_id="test-session",
            agent_id="agent-1",
            memory_type=MemoryType.EPISODIC,
            title="Test Event",
            content="Test content",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(memory)

        # Retrieve by ID
        retrieved = backend.get_memory_by_id("test-id")

        assert retrieved is not None
        assert retrieved.session_id == "test-session"
        assert retrieved.id == "test-id"

    def test_mixed_memory_types_session_isolation(self, backend):
        """Test session isolation when querying all memory types at once."""
        now = datetime.now()

        # Create different types in session-1
        episodic1 = MemoryEntry(
            id="e1",
            session_id="session-1",
            agent_id="agent-1",
            memory_type=MemoryType.EPISODIC,
            title="E1",
            content="Episodic 1",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(episodic1)

        semantic1 = MemoryEntry(
            id="s1",
            session_id="session-1",
            agent_id="agent-1",
            memory_type=MemoryType.SEMANTIC,
            title="S1",
            content="Semantic 1",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(semantic1)

        # Create different types in session-2
        episodic2 = MemoryEntry(
            id="e2",
            session_id="session-2",
            agent_id="agent-1",
            memory_type=MemoryType.EPISODIC,
            title="E2",
            content="Episodic 2",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(episodic2)

        semantic2 = MemoryEntry(
            id="s2",
            session_id="session-2",
            agent_id="agent-1",
            memory_type=MemoryType.SEMANTIC,
            title="S2",
            content="Semantic 2",
            metadata={},
            created_at=now,
            accessed_at=now,
        )
        backend.store_memory(semantic2)

        # Query session-1 (all types)
        query1 = MemoryQuery(session_id="session-1")
        results1 = backend.retrieve_memories(query1)

        # Should get 2 memories from session-1
        assert len(results1) == 2
        ids1 = {r.id for r in results1}
        assert ids1 == {"e1", "s1"}
        assert all(r.session_id == "session-1" for r in results1)

        # Query session-2 (all types)
        query2 = MemoryQuery(session_id="session-2")
        results2 = backend.retrieve_memories(query2)

        # Should get 2 memories from session-2
        assert len(results2) == 2
        ids2 = {r.id for r in results2}
        assert ids2 == {"e2", "s2"}
        assert all(r.session_id == "session-2" for r in results2)
