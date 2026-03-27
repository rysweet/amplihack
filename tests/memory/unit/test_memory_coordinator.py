"""Unit tests for MemoryCoordinator - the main memory interface.

Tests are fast (<100ms), isolated, and focus on behavior validation.
Uses mocked backends to avoid LLM calls and database I/O.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplihack.memory.coordinator import MemoryCoordinator, RetrievalQuery, StorageRequest
from amplihack.memory.models import MemoryEntry, MemoryType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def async_backend():
    """Mock backend with correct async method names for MemoryCoordinator."""
    backend = MagicMock()
    backend.initialize = AsyncMock(return_value=None)
    backend.store_memory = AsyncMock(return_value=True)
    backend.retrieve_memories = AsyncMock(return_value=[])
    backend.delete_memory = AsyncMock(return_value=True)
    backend.get_stats = AsyncMock(return_value={"total_memories": 0})
    return backend


def _make_entry(memory_id, session_id, memory_type=MemoryType.EPISODIC,
                content="Test content", importance=5):
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


# ---------------------------------------------------------------------------
# StorageRequest validation tests
# ---------------------------------------------------------------------------


class TestStorageRequest:
    """Tests for StorageRequest input validation."""

    def test_empty_content_raises_value_error(self):
        """Empty content must raise ValueError."""
        with pytest.raises(ValueError):
            StorageRequest(content="")

    def test_whitespace_only_content_raises_value_error(self):
        """Whitespace-only content must raise ValueError."""
        with pytest.raises(ValueError):
            StorageRequest(content="   ")

    def test_valid_request_defaults_to_episodic(self):
        """Valid content creates request with EPISODIC type by default."""
        req = StorageRequest(content="Valid content here")
        assert req.memory_type == MemoryType.EPISODIC

    def test_valid_request_with_explicit_type(self):
        """Memory type can be set explicitly."""
        req = StorageRequest(content="Valid content", memory_type=MemoryType.SEMANTIC)
        assert req.memory_type == MemoryType.SEMANTIC

    def test_valid_request_with_metadata(self):
        """Metadata is stored on the request."""
        req = StorageRequest(content="Valid content", metadata={"key": "val"})
        assert req.metadata["key"] == "val"


# ---------------------------------------------------------------------------
# Storage tests
# ---------------------------------------------------------------------------


class TestMemoryCoordinatorStore:
    """Test memory storage operations."""

    @pytest.mark.asyncio
    async def test_store_returns_memory_id_on_success(self, async_backend):
        """Successful storage returns a non-None memory ID string."""
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_123")
        with patch.object(coordinator, "_review_quality", AsyncMock(return_value=7)):
            with patch.object(coordinator, "_is_duplicate", AsyncMock(return_value=False)):
                request = StorageRequest(
                    content="Discussion about JWT vs session-based auth",
                    memory_type=MemoryType.EPISODIC,
                )
                memory_id = await coordinator.store(request)

        assert memory_id is not None
        assert isinstance(memory_id, str)
        async_backend.store_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_creates_entry_with_correct_memory_type(self, async_backend):
        """Stored MemoryEntry carries the requested memory type in metadata."""
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_456")
        with patch.object(coordinator, "_review_quality", AsyncMock(return_value=7)):
            with patch.object(coordinator, "_is_duplicate", AsyncMock(return_value=False)):
                request = StorageRequest(
                    content="SQL injection vulnerability in login endpoint",
                    memory_type=MemoryType.SEMANTIC,
                )
                await coordinator.store(request)

        stored_entry = async_backend.store_memory.call_args[0][0]
        assert isinstance(stored_entry, MemoryEntry)
        assert stored_entry.metadata.get("new_memory_type") == MemoryType.SEMANTIC.value

    @pytest.mark.asyncio
    async def test_store_procedural_memory_preserves_content(self, async_backend):
        """Procedural memory content is stored verbatim."""
        content = "1. Check dependencies\n2. Verify PYTHONPATH\n3. Restart IDE"
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_789")
        with patch.object(coordinator, "_review_quality", AsyncMock(return_value=7)):
            with patch.object(coordinator, "_is_duplicate", AsyncMock(return_value=False)):
                request = StorageRequest(content=content, memory_type=MemoryType.PROCEDURAL)
                await coordinator.store(request)

        stored_entry = async_backend.store_memory.call_args[0][0]
        assert "1." in stored_entry.content
        assert stored_entry.metadata.get("new_memory_type") == MemoryType.PROCEDURAL.value

    @pytest.mark.asyncio
    async def test_trivial_short_content_is_rejected(self, async_backend):
        """Very short trivial content is filtered before storage."""
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_triv")
        request = StorageRequest(content="ok")
        memory_id = await coordinator.store(request)

        assert memory_id is None
        async_backend.store_memory.assert_not_called()

    @pytest.mark.asyncio
    async def test_low_quality_content_is_rejected(self, async_backend):
        """Content scoring below the quality threshold (5/10) is not stored."""
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_lq")
        with patch.object(coordinator, "_review_quality", AsyncMock(return_value=3)):
            with patch.object(coordinator, "_is_duplicate", AsyncMock(return_value=False)):
                request = StorageRequest(
                    content="This content scores below the quality threshold"
                )
                memory_id = await coordinator.store(request)

        assert memory_id is None
        async_backend.store_memory.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_content_is_rejected(self, async_backend):
        """Content already in the store is not stored again."""
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_dup")
        with patch.object(coordinator, "_is_duplicate", AsyncMock(return_value=True)):
            request = StorageRequest(content="Duplicate content that was already stored")
            memory_id = await coordinator.store(request)

        assert memory_id is None
        async_backend.store_memory.assert_not_called()


# ---------------------------------------------------------------------------
# Retrieval tests
# ---------------------------------------------------------------------------


class TestMemoryCoordinatorRetrieve:
    """Test memory retrieval operations."""

    @pytest.mark.asyncio
    async def test_retrieve_returns_list(self, async_backend):
        """retrieve() returns a list (may be empty)."""
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_100")
        query = RetrievalQuery(query_text="authentication")
        memories = await coordinator.retrieve(query)
        assert isinstance(memories, list)

    @pytest.mark.asyncio
    async def test_retrieve_empty_when_backend_returns_nothing(self, async_backend):
        """Empty backend results yields empty memory list."""
        async_backend.retrieve_memories = AsyncMock(return_value=[])
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_200")
        memories = await coordinator.retrieve(RetrievalQuery(query_text="test"))
        assert len(memories) == 0

    @pytest.mark.asyncio
    async def test_retrieve_respects_zero_token_budget(self, async_backend):
        """Zero token budget returns empty list without querying backend."""
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_300")
        query = RetrievalQuery(query_text="test", token_budget=0)
        memories = await coordinator.retrieve(query)
        assert len(memories) == 0
        async_backend.retrieve_memories.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_filters_by_memory_type(self, async_backend):
        """retrieve() filters results to requested memory types."""
        semantic = _make_entry("m1", "sess_400", memory_type=MemoryType.SEMANTIC)
        semantic.metadata["new_memory_type"] = MemoryType.SEMANTIC.value
        episodic = _make_entry("m2", "sess_400", memory_type=MemoryType.EPISODIC)
        episodic.metadata["new_memory_type"] = MemoryType.EPISODIC.value
        async_backend.retrieve_memories = AsyncMock(return_value=[semantic, episodic])

        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_400")
        query = RetrievalQuery(query_text="test", memory_types=[MemoryType.SEMANTIC])
        memories = await coordinator.retrieve(query)

        assert all(
            m.metadata.get("new_memory_type") == MemoryType.SEMANTIC.value
            for m in memories
        )

    @pytest.mark.asyncio
    async def test_retrieve_applies_time_range_filter(self, async_backend):
        """retrieve() excludes entries outside the requested time range."""
        old_entry = _make_entry("m_old", "sess_500")
        old_entry.created_at = datetime.now() - timedelta(days=30)
        async_backend.retrieve_memories = AsyncMock(return_value=[old_entry])

        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_500")
        start = datetime.now() - timedelta(days=1)
        end = datetime.now()
        query = RetrievalQuery(query_text="test", time_range=(start, end))
        memories = await coordinator.retrieve(query)

        assert len(memories) == 0


# ---------------------------------------------------------------------------
# Clear-all / session management tests
# ---------------------------------------------------------------------------


class TestMemoryCoordinatorClearAll:
    """Test session memory cleanup operations."""

    @pytest.mark.asyncio
    async def test_clear_all_deletes_session_memories(self, async_backend):
        """clear_all() deletes all memories belonging to the specified session."""
        entry = _make_entry("mem_1", "sess_clear")
        async_backend.retrieve_memories = AsyncMock(return_value=[entry])
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_clear")

        await coordinator.clear_all(session_id="sess_clear")

        async_backend.delete_memory.assert_called_once_with("mem_1")

    @pytest.mark.asyncio
    async def test_clear_all_without_session_raises_value_error(self, async_backend):
        """clear_all() without a session_id raises ValueError."""
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_x")
        coordinator.session_id = None  # Remove session

        with pytest.raises(ValueError):
            await coordinator.clear_all()

    @pytest.mark.asyncio
    async def test_clear_all_uses_coordinator_session_id_by_default(self, async_backend):
        """clear_all() uses the coordinator's own session_id when none given."""
        entry = _make_entry("mem_default", "sess_coord")
        async_backend.retrieve_memories = AsyncMock(return_value=[entry])
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_coord")

        await coordinator.clear_all()  # No explicit session_id

        async_backend.delete_memory.assert_called_once_with("mem_default")


# ---------------------------------------------------------------------------
# Statistics tests
# ---------------------------------------------------------------------------


class TestMemoryCoordinatorStatistics:
    """Test statistics and monitoring."""

    @pytest.mark.asyncio
    async def test_statistics_returns_dict(self, async_backend):
        """get_statistics() returns a dictionary."""
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_stats")
        stats = await coordinator.get_statistics()
        assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_statistics_tracks_stored_count(self, async_backend):
        """Stored memory count increases after successful store."""
        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_cnt")
        with patch.object(coordinator, "_review_quality", AsyncMock(return_value=7)):
            with patch.object(coordinator, "_is_duplicate", AsyncMock(return_value=False)):
                await coordinator.store(
                    StorageRequest(content="A well-formed memory about the system")
                )

        stats = await coordinator.get_statistics()
        assert stats.get("total_stored", 0) >= 1


# ---------------------------------------------------------------------------
# Performance constraint (no external benchmark dep)
# ---------------------------------------------------------------------------


class TestPerformanceConstraints:
    """Validate unit tests meet performance constraints (<100ms)."""

    @pytest.mark.asyncio
    async def test_retrieve_completes_quickly(self, async_backend):
        """Retrieval must complete in under 200ms (unit test, mocked backend)."""
        import time

        coordinator = MemoryCoordinator(backend=async_backend, session_id="sess_perf")
        query = RetrievalQuery(query_text="test")

        start = time.perf_counter()
        await coordinator.retrieve(query)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 200, f"Retrieval took {elapsed_ms:.1f}ms, exceeds 200ms limit"
