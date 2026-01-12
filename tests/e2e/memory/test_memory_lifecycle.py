"""End-to-end tests fer complete memory lifecycle.

Tests complete flow: Store → Retrieve → Clear
with real database and mocked agents.

Philosophy:
- Test complete user-facing flows
- Minimal mocking (only external agents)
- Validate real behavior
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

# These imports will fail until implementation exists (TDD)
try:
    from amplihack.memory.coordinator import MemoryCoordinator
    from amplihack.memory.database import MemoryDatabase
    from amplihack.memory.retrieval_pipeline import RetrievalQuery
    from amplihack.memory.storage_pipeline import StorageRequest
    from amplihack.memory.types import MemoryType
except ImportError:
    pytest.skip("Memory system not implemented yet", allow_module_level=True)


# Module-level fixtures used by all test classes
@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database fer testing."""
    db_path = tmp_path / "test_memory.db"
    db = MemoryDatabase(db_path)
    db.initialize()
    yield db
    db.close()


@pytest.fixture
def coordinator(temp_db):
    """Create memory coordinator with test database."""
    return MemoryCoordinator(database=temp_db, session_id="test-session")


@pytest.fixture
def mock_agents():
    """Mock agent responses fer consistent testing."""
    mock_invoke = AsyncMock()
    # Default to high-quality reviews
    mock_invoke.return_value = {
        "importance_score": 8,
        "reasoning": "Valuable learning",
    }
    return mock_invoke


class TestMemoryLifecycleE2E:
    """Test complete memory lifecycle end-to-end."""

    @pytest.mark.asyncio
    async def test_store_retrieve_clear_lifecycle(self, coordinator, mock_agents):
        """Complete lifecycle: store, retrieve, clear."""
        with patch.object(coordinator, "_invoke_agent", mock_agents):
            # 1. Store a memory
            request = StorageRequest(
                content="To fix CI failures: check logs, identify issue, fix, rerun tests",
                memory_type=MemoryType.PROCEDURAL,
                context={"session": "test-session-123"},
            )

            memory_id = await coordinator.store(request)
            assert memory_id is not None

            # 2. Retrieve the memory
            query = RetrievalQuery(
                query_text="How to fix CI failures?",
                token_budget=5000,
            )

            memories = await coordinator.retrieve(query)
            assert len(memories) > 0
            assert any("CI" in m.content for m in memories)

            # 3. Clear working memory (should not affect stored memory)
            await coordinator.clear_working_memory()

            # Procedural memory still retrievable
            memories = await coordinator.retrieve(query)
            assert len(memories) > 0

            # 4. Clear all memories
            await coordinator.clear_all()

            # No memories retrievable
            memories = await coordinator.retrieve(query)
            assert len(memories) == 0

    @pytest.mark.asyncio
    async def test_multiple_memory_types_lifecycle(self, coordinator, mock_agents):
        """Store and retrieve multiple memory types."""
        with patch.object(coordinator, "_invoke_agent", mock_agents):
            # Store different memory types
            requests = [
                StorageRequest(
                    content="User discussed authentication on Dec 1",
                    memory_type=MemoryType.EPISODIC,
                ),
                StorageRequest(
                    content="Always validate input before processing",
                    memory_type=MemoryType.SEMANTIC,
                ),
                StorageRequest(
                    content="Refactor auth module after code review",
                    memory_type=MemoryType.PROSPECTIVE,
                ),
                StorageRequest(
                    content="CI fix procedure: logs, fix, test",
                    memory_type=MemoryType.PROCEDURAL,
                ),
                StorageRequest(
                    content="Currently working on auth.py line 42",
                    memory_type=MemoryType.WORKING,
                ),
            ]

            memory_ids = []
            for request in requests:
                memory_id = await coordinator.store(request)
                assert memory_id is not None
                memory_ids.append(memory_id)

            # Retrieve specific types
            query = RetrievalQuery(
                query_text="authentication",
                memory_types=[MemoryType.SEMANTIC, MemoryType.PROCEDURAL],
                token_budget=5000,
            )

            memories = await coordinator.retrieve(query)

            # Should only return semantic and procedural
            for memory in memories:
                assert memory.memory_type in [
                    MemoryType.SEMANTIC,
                    MemoryType.PROCEDURAL,
                ]

    @pytest.mark.asyncio
    async def test_time_based_retrieval_lifecycle(self, coordinator, mock_agents):
        """Store memories at different times, retrieve by time range."""
        with patch.object(coordinator, "_invoke_agent", mock_agents):
            now = datetime.now()

            # Store old memory
            old_request = StorageRequest(
                content="Old discussion from last month",
                memory_type=MemoryType.EPISODIC,
                metadata={"timestamp": now - timedelta(days=30)},
            )
            await coordinator.store(old_request)

            # Store recent memory
            recent_request = StorageRequest(
                content="Recent discussion from today",
                memory_type=MemoryType.EPISODIC,
                metadata={"timestamp": now},
            )
            await coordinator.store(recent_request)

            # Retrieve only recent (last 7 days)
            query = RetrievalQuery(
                query_text="discussion",
                token_budget=5000,
                time_range=(now - timedelta(days=7), now),
            )

            memories = await coordinator.retrieve(query)

            # Should only get recent memory
            assert len(memories) == 1
            assert "today" in memories[0].content.lower()

    @pytest.mark.asyncio
    async def test_working_memory_auto_clear_on_completion(self, coordinator, mock_agents):
        """Working memory automatically cleared when task completes."""
        with patch.object(coordinator, "_invoke_agent", mock_agents):
            # Store working memory
            request = StorageRequest(
                content="Working on auth.py JWT validation",
                memory_type=MemoryType.WORKING,
                context={"task_id": "auth-123"},
            )

            await coordinator.store(request)

            # Retrieve working memory
            query = RetrievalQuery(
                query_text="current task",
                memory_types=[MemoryType.WORKING],
                token_budget=5000,
            )

            memories = await coordinator.retrieve(query)
            assert len(memories) > 0

            # Mark task complete
            await coordinator.mark_task_complete("auth-123")

            # Working memory should be cleared
            memories = await coordinator.retrieve(query)
            working_memories = [m for m in memories if m.context.get("task_id") == "auth-123"]
            assert len(working_memories) == 0


class TestMemoryPersistence:
    """Test memory persistence across coordinator instances."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Database path fer testing persistence."""
        return tmp_path / "persistent_memory.db"

    @pytest.mark.asyncio
    async def test_memories_persist_across_sessions(self, db_path, mock_agents):
        """Memories persist when coordinator is recreated."""
        # Use same session ID fer both coordinators to test persistence
        test_session_id = "persistence-test-session"

        # Session 1: Store memory
        db1 = MemoryDatabase(db_path)
        db1.initialize()
        coordinator1 = MemoryCoordinator(database=db1, session_id=test_session_id)

        with patch.object(coordinator1, "_invoke_agent", mock_agents):
            request = StorageRequest(
                content="Important pattern about architect",
                memory_type=MemoryType.SEMANTIC,
            )

            memory_id = await coordinator1.store(request)
            assert memory_id is not None

        # Close session 1
        db1.close()

        # Session 2: Retrieve memory (new coordinator, same DB, same session ID)
        db2 = MemoryDatabase(db_path)
        coordinator2 = MemoryCoordinator(database=db2, session_id=test_session_id)

        query = RetrievalQuery(
            query_text="architect",
            token_budget=5000,
        )

        memories = await coordinator2.retrieve(query)

        # Should retrieve memory from previous session
        assert len(memories) > 0
        assert any("architect" in m.content for m in memories)

        db2.close()


class TestMemoryQualityGate:
    """Test quality gate in complete flow."""

    @pytest.mark.asyncio
    async def test_high_quality_memory_stored(self, coordinator):
        """High-quality content passes quality gate."""
        mock_task = AsyncMock()
        mock_task.side_effect = [
            {"importance_score": 9, "reasoning": "Excellent"},
            {"importance_score": 8, "reasoning": "Very good"},
            {"importance_score": 8, "reasoning": "Good"},
        ]

        with patch.object(coordinator, "_invoke_agent", mock_task):
            request = StorageRequest(
                content="Architect performs better when given detailed module specs first",
                memory_type=MemoryType.SEMANTIC,
            )

            memory_id = await coordinator.store(request)

            # Should store successfully
            assert memory_id is not None

            # Should be retrievable
            query = RetrievalQuery(query_text="architect", token_budget=5000)
            memories = await coordinator.retrieve(query)
            assert len(memories) > 0

    @pytest.mark.asyncio
    async def test_low_quality_memory_rejected(self, coordinator):
        """Low-quality content rejected by quality gate."""
        mock_task = AsyncMock()
        mock_task.side_effect = [
            {"importance_score": 2, "reasoning": "Trivial"},
            {"importance_score": 1, "reasoning": "No value"},
            {"importance_score": 3, "reasoning": "Not useful"},
        ]

        with patch.object(coordinator, "_invoke_agent", mock_task):
            request = StorageRequest(
                content="Hello",
                memory_type=MemoryType.EPISODIC,
            )

            memory_id = await coordinator.store(request)

            # Should not store
            assert memory_id is None

            # Should not be retrievable
            query = RetrievalQuery(query_text="hello", token_budget=5000)
            memories = await coordinator.retrieve(query)
            assert len(memories) == 0


class TestMemoryTokenBudget:
    """Test token budget enforcement in complete flow."""

    @pytest.mark.asyncio
    async def test_retrieval_respects_budget_strictly(self, coordinator, mock_agents):
        """Retrieval strictly respects token budget."""
        with patch.object(coordinator, "_invoke_agent", mock_agents):
            # Store multiple large memories
            for i in range(10):
                request = StorageRequest(
                    content=f"Long memory content {i} " * 100,  # ~1000 chars each
                    memory_type=MemoryType.SEMANTIC,
                )
                await coordinator.store(request)

            # Retrieve with small budget
            query = RetrievalQuery(
                query_text="memory content",
                token_budget=500,  # Small budget
            )

            await coordinator.retrieve(query)

            # Should not exceed budget
            # (Coordinator should track and enforce)
            assert coordinator.last_retrieval_tokens <= 500

    @pytest.mark.asyncio
    async def test_zero_budget_returns_empty(self, coordinator, mock_agents):
        """Zero budget returns no memories."""
        with patch.object(coordinator, "_invoke_agent", mock_agents):
            # Store memory
            request = StorageRequest(
                content="Test memory",
                memory_type=MemoryType.SEMANTIC,
            )
            await coordinator.store(request)

            # Query with zero budget
            query = RetrievalQuery(
                query_text="test",
                token_budget=0,
            )

            memories = await coordinator.retrieve(query)
            assert len(memories) == 0


class TestMemoryStatistics:
    """Test memory statistics in complete flow."""

    @pytest.mark.asyncio
    async def test_coordinator_tracks_statistics(self, coordinator, mock_agents):
        """Coordinator tracks memory statistics."""
        with patch.object(coordinator, "_invoke_agent", mock_agents):
            # Store multiple memories (content must be >10 chars to not be trivial)
            for i in range(5):
                request = StorageRequest(
                    content=f"Important learning about memory pattern number {i}",
                    memory_type=MemoryType.SEMANTIC,
                )
                await coordinator.store(request)

            # Retrieve multiple times
            query = RetrievalQuery(query_text="memory", token_budget=5000)
            for _ in range(3):
                await coordinator.retrieve(query)

            # Get statistics
            stats = coordinator.get_statistics()

            assert stats["total_stored"] == 5
            assert stats["total_retrievals"] == 3
            assert stats["total_memories"] >= 5


class TestMemoryEdgeCases:
    """Test edge cases in complete flow."""

    @pytest.mark.asyncio
    async def test_store_empty_content_rejected(self, coordinator):
        """Empty content cannot be stored."""
        with pytest.raises(ValueError, match="content"):
            StorageRequest(
                content="",
                memory_type=MemoryType.SEMANTIC,
            )

    @pytest.mark.asyncio
    async def test_retrieve_with_invalid_type_handled(self, coordinator):
        """Invalid memory type handled gracefully."""
        query = RetrievalQuery(
            query_text="test",
            memory_types=["INVALID_TYPE"],  # Invalid
            token_budget=5000,
        )

        # Should handle gracefully
        memories = await coordinator.retrieve(query)
        assert memories == []

    @pytest.mark.asyncio
    async def test_duplicate_content_detection(self, coordinator, mock_agents):
        """Duplicate content detected and handled."""
        with patch.object(coordinator, "_invoke_agent", mock_agents):
            content = "Exact same content"

            # Store first time
            request1 = StorageRequest(
                content=content,
                memory_type=MemoryType.SEMANTIC,
            )
            memory_id1 = await coordinator.store(request1)
            assert memory_id1 is not None

            # Try to store duplicate
            request2 = StorageRequest(
                content=content,
                memory_type=MemoryType.SEMANTIC,
            )
            memory_id2 = await coordinator.store(request2)

            # Should reject duplicate
            assert memory_id2 is None or memory_id2 == memory_id1

            # Only one copy in database
            query = RetrievalQuery(query_text=content, token_budget=5000)
            memories = await coordinator.retrieve(query)
            assert len(memories) == 1

    @pytest.mark.asyncio
    async def test_very_long_content_handled(self, coordinator, mock_agents):
        """Very long content handled appropriately."""
        with patch.object(coordinator, "_invoke_agent", mock_agents):
            # 50K character content
            long_content = "test " * 10000

            request = StorageRequest(
                content=long_content,
                memory_type=MemoryType.SEMANTIC,
            )

            # Should handle without crashing (may truncate or chunk)
            memory_id = await coordinator.store(request)
            assert memory_id is not None


class TestMemoryPerformance:
    """Test performance requirements in complete flow."""

    @pytest.mark.asyncio
    async def test_store_completes_under_500ms(self, coordinator, mock_agents):
        """Storage completes under 500ms."""
        import time

        with patch.object(coordinator, "_invoke_agent", mock_agents):
            request = StorageRequest(
                content="Test memory",
                memory_type=MemoryType.SEMANTIC,
            )

            start = time.perf_counter()
            await coordinator.store(request)
            duration = time.perf_counter() - start

            assert duration < 0.5

    @pytest.mark.asyncio
    async def test_retrieve_completes_under_50ms(self, coordinator, mock_agents):
        """Retrieval completes under 50ms."""
        import time

        with patch.object(coordinator, "_invoke_agent", mock_agents):
            # Store some memories first
            for i in range(10):
                request = StorageRequest(
                    content=f"Memory {i}",
                    memory_type=MemoryType.SEMANTIC,
                )
                await coordinator.store(request)

            query = RetrievalQuery(query_text="memory", token_budget=5000)

            start = time.perf_counter()
            await coordinator.retrieve(query)
            duration = time.perf_counter() - start

            assert duration < 0.05
