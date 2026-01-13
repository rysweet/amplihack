"""Integration tests fer complete storage flow.

Tests end-to-end storage from request through agent review
to database persistence.

Philosophy:
- Test multiple components working together
- Use real agent coordination (mocked Task tool)
- Validate complete flow behavior
"""

import asyncio
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

# These imports will fail until implementation exists (TDD)
try:
    from amplihack.memory.trivial_filter import TrivialFilter

    from amplihack.memory.coordinator import MemoryCoordinator
    from amplihack.memory.database import MemoryDatabase
    from amplihack.memory.storage_pipeline import StoragePipeline, StorageRequest
    from amplihack.memory.types import MemoryType
except ImportError:
    pytest.skip("Memory system not implemented yet", allow_module_level=True)


class TestStorageFlowIntegration:
    """Test complete storage flow integration."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary SQLite database fer testing."""
        db_path = tmp_path / "test_memory.db"
        db = MemoryDatabase(db_path)
        db.initialize()
        yield db
        db.close()

    @pytest.fixture
    def mock_task_tool(self):
        """Mock Task tool fer agent invocation."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_store_high_quality_content_succeeds(self, temp_db, mock_task_tool):
        """High-quality content passes all stages and stores."""
        # Setup: Create pipeline with real DB and mocked agents
        pipeline = StoragePipeline(database=temp_db)

        # Mock high-quality agent reviews
        mock_task_tool.side_effect = [
            {"importance_score": 8, "reasoning": "Valuable pattern"},
            {"importance_score": 9, "reasoning": "Important insight"},
            {"importance_score": 7, "reasoning": "Useful learning"},
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task_tool):
            request = StorageRequest(
                content="Architect agent performs better when given module specs first",
                memory_type=MemoryType.SEMANTIC,
                context={"session": "test-123"},
            )

            # Execute: Store through complete pipeline
            result = await pipeline.store_with_review(request)

            # Assert: Content stored successfully
            assert result.stored
            assert result.memory_id is not None

            # Verify in database
            stored_memory = temp_db.get_by_id(result.memory_id)
            assert stored_memory is not None
            assert stored_memory["content"] == request.content
            assert stored_memory["memory_type"] == MemoryType.SEMANTIC.value

    @pytest.mark.asyncio
    async def test_store_low_quality_content_rejected(self, temp_db, mock_task_tool):
        """Low-quality content rejected by agent reviews."""
        pipeline = StoragePipeline(database=temp_db)

        # Mock low-quality agent reviews
        mock_task_tool.side_effect = [
            {"importance_score": 2, "reasoning": "Too trivial"},
            {"importance_score": 3, "reasoning": "No learning value"},
            {"importance_score": 1, "reasoning": "Not useful"},
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task_tool):
            request = StorageRequest(
                content="Hello",
                memory_type=MemoryType.EPISODIC,
            )

            result = await pipeline.store_with_review(request)

            # Assert: Content not stored
            assert not result.stored
            assert result.rejection_reason == "below_threshold"

            # Verify not in database
            all_memories = temp_db.get_all()
            assert len(all_memories) == 0

    @pytest.mark.asyncio
    async def test_trivial_filter_prevents_storage(self, temp_db, mock_task_tool):
        """Trivial filter prevents unnecessary agent invocation."""
        pipeline = StoragePipeline(
            database=temp_db,
            trivial_filter=TrivialFilter(),
        )

        request = StorageRequest(
            content="Hi",  # Simple greeting
            memory_type=MemoryType.EPISODIC,
        )

        result = await pipeline.store_with_review(request)

        # Assert: Filtered before agent review
        assert not result.stored
        assert result.rejection_reason == "trivial_filter"

        # Agents never invoked
        assert mock_task_tool.call_count == 0

    @pytest.mark.asyncio
    async def test_storage_preserves_metadata(self, temp_db, mock_task_tool):
        """Storage flow preserves metadata through pipeline."""
        pipeline = StoragePipeline(database=temp_db)

        mock_task_tool.side_effect = [
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task_tool):
            request = StorageRequest(
                content="Test content",
                memory_type=MemoryType.SEMANTIC,
                metadata={
                    "source": "user_prompt",
                    "session_id": "test-123",
                    "confidence": 0.9,
                },
            )

            result = await pipeline.store_with_review(request)

            # Verify metadata preserved in DB
            stored = temp_db.get_by_id(result.memory_id)
            assert stored["metadata"]["source"] == "user_prompt"
            assert stored["metadata"]["session_id"] == "test-123"
            assert stored["metadata"]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_storage_tracks_agent_reviews(self, temp_db, mock_task_tool):
        """Storage tracks which agents reviewed and their scores."""
        pipeline = StoragePipeline(database=temp_db)

        mock_task_tool.side_effect = [
            {
                "importance_score": 8,
                "reasoning": "Analyzer: Good pattern",
                "agent": "analyzer",
            },
            {
                "importance_score": 9,
                "reasoning": "Patterns: Valuable",
                "agent": "patterns",
            },
            {
                "importance_score": 7,
                "reasoning": "Archaeologist: Useful",
                "agent": "knowledge-archaeologist",
            },
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task_tool):
            request = StorageRequest(
                content="Test content",
                memory_type=MemoryType.SEMANTIC,
            )

            result = await pipeline.store_with_review(request)

            # Verify review metadata stored
            stored = temp_db.get_by_id(result.memory_id)
            reviews = stored["metadata"]["reviews"]

            assert len(reviews) == 3
            assert reviews[0]["agent"] == "analyzer"
            assert reviews[0]["score"] == 8


class TestStorageWithCoordinator:
    """Test storage through MemoryCoordinator."""

    @pytest.fixture
    def coordinator(self, temp_db):
        """Create coordinator with real database."""
        return MemoryCoordinator(database=temp_db)

    @pytest.mark.asyncio
    async def test_coordinator_store_delegates_to_pipeline(self, coordinator, mock_task_tool):
        """Coordinator delegates to storage pipeline."""
        mock_task_tool.side_effect = [
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task_tool):
            request = StorageRequest(
                content="Valuable insight",
                memory_type=MemoryType.SEMANTIC,
            )

            memory_id = await coordinator.store(request)

            assert memory_id is not None

    @pytest.mark.asyncio
    async def test_coordinator_store_returns_none_on_rejection(self, coordinator, mock_task_tool):
        """Coordinator returns None when content rejected."""
        mock_task_tool.side_effect = [
            {"importance_score": 2, "reasoning": "Low quality"},
            {"importance_score": 1, "reasoning": "Trivial"},
            {"importance_score": 2, "reasoning": "Not useful"},
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task_tool):
            request = StorageRequest(
                content="Trivial content",
                memory_type=MemoryType.EPISODIC,
            )

            memory_id = await coordinator.store(request)

            assert memory_id is None


class TestStorageErrorHandling:
    """Test error handling in storage flow."""

    @pytest.mark.asyncio
    async def test_storage_handles_agent_timeout(self, temp_db):
        """Storage handles agent timeout gracefully."""
        pipeline = StoragePipeline(database=temp_db)

        # Mock agent timeout
        mock_task = AsyncMock()
        mock_task.side_effect = [
            {"importance_score": 8, "reasoning": "Good"},
            TimeoutError("Agent timed out"),
            {"importance_score": 7, "reasoning": "Good"},
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task):
            request = StorageRequest(
                content="Test content",
                memory_type=MemoryType.SEMANTIC,
            )

            result = await pipeline.store_with_review(request)

            # Should still get result with 2 reviews
            assert len(result.reviews) == 2

    @pytest.mark.asyncio
    async def test_storage_handles_database_error(self, temp_db, mock_task_tool):
        """Storage handles database errors gracefully."""
        pipeline = StoragePipeline(database=temp_db)

        mock_task_tool.side_effect = [
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
        ]

        # Mock database failure
        with patch.object(temp_db, "insert", side_effect=sqlite3.Error("DB error")):
            with patch("amplihack.memory.storage_pipeline.Task", mock_task_tool):
                request = StorageRequest(
                    content="Test content",
                    memory_type=MemoryType.SEMANTIC,
                )

                result = await pipeline.store_with_review(request)

                # Should not crash, but indicate error
                assert not result.stored
                assert "error" in result.rejection_reason.lower()

    @pytest.mark.asyncio
    async def test_storage_handles_malformed_agent_response(self, temp_db):
        """Storage handles malformed agent responses."""
        pipeline = StoragePipeline(database=temp_db)

        mock_task = AsyncMock()
        mock_task.side_effect = [
            {"importance_score": 8, "reasoning": "Good"},
            {"invalid": "response"},  # Malformed
            {"importance_score": 7, "reasoning": "Good"},
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task):
            request = StorageRequest(
                content="Test content",
                memory_type=MemoryType.SEMANTIC,
            )

            result = await pipeline.store_with_review(request)

            # Should handle gracefully with 2 valid reviews
            assert len(result.reviews) == 2


class TestStoragePerformance:
    """Test storage performance requirements."""

    @pytest.mark.asyncio
    async def test_parallel_agent_invocation_faster_than_sequential(self, temp_db):
        """Parallel agent invocation faster than sequential."""
        import time

        pipeline_parallel = StoragePipeline(database=temp_db, parallel_review=True)
        pipeline_sequential = StoragePipeline(database=temp_db, parallel_review=False)

        async def slow_agent(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return {"importance_score": 8, "reasoning": "Good"}

        request = StorageRequest(
            content="Test content",
            memory_type=MemoryType.SEMANTIC,
        )

        # Test parallel (default)
        with patch("amplihack.memory.storage_pipeline.Task", slow_agent):
            start = time.perf_counter()
            await pipeline_parallel.store_with_review(request)
            parallel_time = time.perf_counter() - start

        # Test sequential
        with patch("amplihack.memory.storage_pipeline.Task", slow_agent):
            start = time.perf_counter()
            await pipeline_sequential.store_with_review(request)
            sequential_time = time.perf_counter() - start

        # Parallel should be significantly faster
        # 3 agents @ 100ms each: parallel ~100ms, sequential ~300ms
        assert parallel_time < sequential_time * 0.5

    @pytest.mark.asyncio
    async def test_storage_completes_under_500ms(self, temp_db, mock_task_tool):
        """Storage completes under 500ms requirement."""
        import time

        pipeline = StoragePipeline(database=temp_db)

        mock_task_tool.side_effect = [
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task_tool):
            request = StorageRequest(
                content="Test content",
                memory_type=MemoryType.SEMANTIC,
            )

            start = time.perf_counter()
            await pipeline.store_with_review(request)
            duration = time.perf_counter() - start

            # Should complete quickly
            assert duration < 0.5


class TestStorageDatabaseIntegration:
    """Test storage integration with database."""

    @pytest.mark.asyncio
    async def test_stored_memory_queryable_immediately(self, temp_db, mock_task_tool):
        """Stored memory immediately queryable."""
        pipeline = StoragePipeline(database=temp_db)

        mock_task_tool.side_effect = [
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task_tool):
            request = StorageRequest(
                content="Test pattern about architect agent",
                memory_type=MemoryType.SEMANTIC,
            )

            result = await pipeline.store_with_review(request)

            # Immediately query
            memories = temp_db.search("architect")

            assert len(memories) > 0
            assert memories[0]["id"] == result.memory_id

    @pytest.mark.asyncio
    async def test_multiple_memories_stored_independently(self, temp_db, mock_task_tool):
        """Multiple memories can be stored independently."""
        pipeline = StoragePipeline(database=temp_db)

        # Mock good reviews for both
        mock_task_tool.side_effect = [
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 8, "reasoning": "Good"},
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task_tool):
            request1 = StorageRequest(
                content="First memory",
                memory_type=MemoryType.SEMANTIC,
            )

            request2 = StorageRequest(
                content="Second memory",
                memory_type=MemoryType.PROCEDURAL,
            )

            result1 = await pipeline.store_with_review(request1)
            result2 = await pipeline.store_with_review(request2)

            # Both stored successfully
            assert result1.stored
            assert result2.stored
            assert result1.memory_id != result2.memory_id

            # Both in database
            all_memories = temp_db.get_all()
            assert len(all_memories) == 2
