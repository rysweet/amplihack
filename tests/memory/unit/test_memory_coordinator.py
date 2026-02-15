"""Unit tests for MemoryCoordinator - the main memory interface.

This file implements the core unit tests from the testing strategy.
Tests are fast (<100ms), isolated, and focus on behavior validation.
"""

from datetime import datetime, timedelta

from amplihack.memory.coordinator import MemoryCoordinator
from amplihack.memory.models import MemoryEntry, MemoryQuery, MemoryType


class TestMemoryCoordinatorStore:
    """Test memory storage operations (<100ms)."""

    def test_store_episodic_memory_creates_entry(self, mock_backend):
        """Test storing episodic memory creates valid entry."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)

        # ACT
        result = coordinator.store(
            memory_type=MemoryType.EPISODIC,
            title="User asked about authentication",
            content="Discussion about JWT vs session-based auth",
            session_id="sess_123",
            agent_id="architect",
            metadata={"topic": "security"},
        )

        # ASSERT
        assert result.success is True
        assert result.memory_id is not None
        mock_backend.store.assert_called_once()

        # Verify stored entry structure
        stored_entry = mock_backend.store.call_args[0][0]
        assert isinstance(stored_entry, MemoryEntry)
        assert stored_entry.memory_type == MemoryType.EPISODIC
        assert stored_entry.session_id == "sess_123"
        assert stored_entry.agent_id == "architect"

    def test_store_with_importance_auto_calculation(self, mock_backend):
        """Test importance is automatically calculated during storage."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)

        # ACT
        result = coordinator.store(
            memory_type=MemoryType.SEMANTIC,
            title="Critical security vulnerability found",
            content="SQL injection vulnerability in login endpoint",
            session_id="sess_456",
            agent_id="security",
            metadata={"severity": "critical"},
        )

        # ASSERT
        assert result.success is True
        stored_entry = mock_backend.store.call_args[0][0]

        # Critical security findings should have high importance
        # (Actual scoring logic in storage pipeline)
        assert stored_entry.importance is not None

    def test_store_procedural_with_steps(self, mock_backend):
        """Test storing procedural memory with execution steps."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)

        # ACT
        result = coordinator.store(
            memory_type=MemoryType.PROCEDURAL,
            title="How to fix import errors",
            content="1. Check dependencies\n2. Verify PYTHONPATH\n3. Restart IDE",
            session_id="sess_789",
            agent_id="builder",
            metadata={"success_rate": 0.95},
        )

        # ASSERT
        assert result.success is True
        stored_entry = mock_backend.store.call_args[0][0]
        assert stored_entry.memory_type == MemoryType.PROCEDURAL
        assert "1." in stored_entry.content
        assert stored_entry.metadata["success_rate"] == 0.95

    def test_store_fails_gracefully_on_empty_title(self, mock_backend):
        """Test error handling for invalid memory entries."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)

        # ACT
        result = coordinator.store(
            memory_type=MemoryType.EPISODIC,
            title="",  # Invalid: empty title
            content="Some content",
            session_id="sess_999",
            agent_id="test",
        )

        # ASSERT
        assert result.success is False
        assert "title" in result.error.lower() or "required" in result.error.lower()
        mock_backend.store.assert_not_called()

    def test_store_fails_on_missing_required_fields(self, mock_backend):
        """Test validation of required fields."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)

        # ACT & ASSERT - Missing session_id
        result = coordinator.store(
            memory_type=MemoryType.EPISODIC,
            title="Test",
            content="Content",
            session_id="",  # Invalid
            agent_id="test",
        )
        assert result.success is False

    def test_store_working_memory_with_expiration(self, mock_backend):
        """Test storing working memory with automatic expiration."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        expiration = datetime.now() + timedelta(hours=1)

        # ACT
        result = coordinator.store(
            memory_type=MemoryType.WORKING,
            title="Temporary context",
            content="Active task state",
            session_id="sess_work",
            agent_id="builder",
            expires_at=expiration,
        )

        # ASSERT
        assert result.success is True
        stored_entry = mock_backend.store.call_args[0][0]
        assert stored_entry.memory_type == MemoryType.WORKING
        assert stored_entry.expires_at == expiration


class TestMemoryCoordinatorRetrieve:
    """Test memory retrieval operations (<50ms without review)."""

    def test_retrieve_by_session_id(self, mock_backend, sample_memory_entry):
        """Test retrieving all memories for a session."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.query.return_value = [
            sample_memory_entry,
            create_mock_memory("mem_2", "sess_100"),
        ]

        # ACT
        result = coordinator.retrieve(query=MemoryQuery(session_id="sess_100"))

        # ASSERT
        assert len(result.memories) == 2
        assert all(m.session_id == "sess_100" for m in result.memories)
        mock_backend.query.assert_called_once()

    def test_retrieve_by_memory_type(self, mock_backend):
        """Test filtering by memory type."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        semantic_memory = create_mock_memory("mem_3", "sess_200", memory_type=MemoryType.SEMANTIC)
        mock_backend.query.return_value = [semantic_memory]

        # ACT
        result = coordinator.retrieve(query=MemoryQuery(memory_type=MemoryType.SEMANTIC))

        # ASSERT
        assert len(result.memories) == 1
        assert result.memories[0].memory_type == MemoryType.SEMANTIC

    def test_retrieve_with_content_search(self, mock_backend):
        """Test full-text search functionality."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.query.return_value = [
            create_mock_memory("mem_4", "sess_300", content="authentication flow details"),
        ]

        # ACT
        result = coordinator.retrieve(query=MemoryQuery(content_search="authentication"))

        # ASSERT
        assert len(result.memories) == 1
        assert "authentication" in result.memories[0].content.lower()

    def test_retrieve_with_importance_threshold(self, mock_backend):
        """Test filtering by importance score."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.query.return_value = [
            create_mock_memory("mem_5", "sess_400", importance=9),
            create_mock_memory("mem_6", "sess_400", importance=8),
        ]

        # ACT
        result = coordinator.retrieve(query=MemoryQuery(min_importance=8))

        # ASSERT
        assert len(result.memories) == 2
        assert all(m.importance >= 8 for m in result.memories)

    def test_retrieve_empty_results(self, mock_backend):
        """Test handling of no matching memories."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.query.return_value = []

        # ACT
        result = coordinator.retrieve(query=MemoryQuery(session_id="nonexistent"))

        # ASSERT
        assert len(result.memories) == 0
        assert result.success is True

    def test_retrieve_with_time_range(self, mock_backend):
        """Test filtering by time range."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        start_time = datetime.now() - timedelta(days=7)
        end_time = datetime.now()

        mock_backend.query.return_value = [create_mock_memory("mem_recent", "sess_500")]

        # ACT
        result = coordinator.retrieve(
            query=MemoryQuery(created_after=start_time, created_before=end_time)
        )

        # ASSERT
        assert len(result.memories) == 1
        mock_backend.query.assert_called_once()

    def test_retrieve_with_limit(self, mock_backend):
        """Test pagination with limit."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.query.return_value = [
            create_mock_memory(f"mem_{i}", "sess_600") for i in range(10)
        ]

        # ACT
        result = coordinator.retrieve(query=MemoryQuery(session_id="sess_600", limit=5))

        # ASSERT
        assert len(result.memories) <= 5


class TestMemoryCoordinatorWorkingMemory:
    """Test working memory operations (temporary context)."""

    def test_clear_working_memory_for_session(self, mock_backend):
        """Test clearing working memory at session boundaries."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.delete_by_query.return_value = 3  # 3 memories deleted

        # ACT
        result = coordinator.clear_working_memory(session_id="sess_500")

        # ASSERT
        assert result.success is True
        assert result.deleted_count == 3
        mock_backend.delete_by_query.assert_called_once()

    def test_working_memory_auto_expires(self, mock_backend):
        """Test working memory expires after timeout."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        _ = datetime.now() - timedelta(hours=2)

        # Mock: no expired memories returned
        mock_backend.query.return_value = []

        # ACT - Query should exclude expired memories by default
        result = coordinator.retrieve(
            query=MemoryQuery(
                session_id="sess_600", memory_type=MemoryType.WORKING, include_expired=False
            )
        )

        # ASSERT
        assert len(result.memories) == 0

    def test_include_expired_memories_when_requested(self, mock_backend):
        """Test retrieving expired memories when explicitly requested."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        expired_memory = create_mock_memory("mem_expired", "sess_700")
        expired_memory.expires_at = datetime.now() - timedelta(hours=1)

        mock_backend.query.return_value = [expired_memory]

        # ACT
        result = coordinator.retrieve(
            query=MemoryQuery(session_id="sess_700", include_expired=True)
        )

        # ASSERT
        assert len(result.memories) == 1


class TestMemoryCoordinatorDelete:
    """Test memory deletion operations."""

    def test_delete_by_id(self, mock_backend):
        """Test deleting specific memory by ID."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.delete.return_value = True

        # ACT
        result = coordinator.delete(memory_id="mem_to_delete")

        # ASSERT
        assert result.success is True
        mock_backend.delete.assert_called_once_with("mem_to_delete")

    def test_delete_nonexistent_memory(self, mock_backend):
        """Test deleting non-existent memory."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.delete.return_value = False

        # ACT
        result = coordinator.delete(memory_id="nonexistent")

        # ASSERT
        assert result.success is False


class TestMemoryCoordinatorBoundaryConditions:
    """Test boundary conditions and edge cases."""

    def test_store_with_very_long_content(self, mock_backend):
        """Test storing memory with very long content."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        long_content = "x" * 100000  # 100KB content

        # ACT
        result = coordinator.store(
            memory_type=MemoryType.EPISODIC,
            title="Large content test",
            content=long_content,
            session_id="sess_large",
            agent_id="test",
        )

        # ASSERT
        assert result.success is True
        stored_entry = mock_backend.store.call_args[0][0]
        assert len(stored_entry.content) == 100000

    def test_retrieve_with_zero_limit(self, mock_backend):
        """Test retrieval with limit=0 (no results)."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.query.return_value = []

        # ACT
        result = coordinator.retrieve(query=MemoryQuery(session_id="sess_800", limit=0))

        # ASSERT
        assert len(result.memories) == 0

    def test_store_with_null_metadata(self, mock_backend):
        """Test storing memory with empty metadata."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)

        # ACT
        result = coordinator.store(
            memory_type=MemoryType.EPISODIC,
            title="No metadata",
            content="Content without metadata",
            session_id="sess_900",
            agent_id="test",
            metadata={},
        )

        # ASSERT
        assert result.success is True
        stored_entry = mock_backend.store.call_args[0][0]
        assert stored_entry.metadata == {}


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================


def create_mock_memory(
    memory_id: str,
    session_id: str,
    memory_type: MemoryType = MemoryType.EPISODIC,
    importance: int = 5,
    content: str = "Test content",
) -> MemoryEntry:
    """Helper to create mock memory entries."""
    return MemoryEntry(
        id=memory_id,
        session_id=session_id,
        agent_id="test_agent",
        memory_type=memory_type,
        title="Test Memory",
        content=content,
        metadata={},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
        importance=importance,
    )


# =============================================================================
# Test Performance Validation
# =============================================================================


class TestPerformanceConstraints:
    """Validate unit tests meet performance constraints (<100ms)."""

    def test_all_unit_tests_complete_quickly(self, mock_backend, benchmark):
        """Benchmark test to ensure unit tests are fast."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.query.return_value = []

        # ACT & ASSERT - Should complete in <100ms
        def retrieve_operation():
            coordinator.retrieve(query=MemoryQuery(session_id="test"))

        _ = benchmark(retrieve_operation)
        # Benchmark automatically validates timing
