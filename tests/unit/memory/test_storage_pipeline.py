"""Unit tests fer memory storage pipeline logic.

Tests storage pipeline that reviews content with multiple agents
before persisting to database.

Philosophy:
- Test storage logic in isolation (mock DB)
- Validate agent review coordination
- Test quality gate thresholds
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# These imports will fail until implementation exists (TDD)
try:
    from amplihack.memory.storage_pipeline import (
        AgentReview,
        QualityGate,
        ReviewResult,
        StoragePipeline,
        StorageRequest,
        StorageResult,
    )
    from amplihack.memory.types import MemoryType
except ImportError:
    pytest.skip("Storage pipeline not implemented yet", allow_module_level=True)


class TestStorageRequest:
    """Test StorageRequest data structure."""

    def test_create_storage_request(self):
        """Create storage request with required fields."""
        request = StorageRequest(
            content="User discovered that architect works best with specs",
            memory_type=MemoryType.SEMANTIC,
            context={"session": "123", "confidence": 0.9},
        )

        assert request.content
        assert request.memory_type == MemoryType.SEMANTIC
        assert request.context["session"] == "123"

    def test_storage_request_requires_content(self):
        """Storage request must have content."""
        with pytest.raises(ValueError, match="content"):
            StorageRequest(
                content="",
                memory_type=MemoryType.SEMANTIC,
            )

    def test_storage_request_requires_memory_type(self):
        """Storage request must specify memory type."""
        with pytest.raises(ValueError, match="memory_type"):
            StorageRequest(
                content="Some content",
                memory_type=None,
            )

    def test_storage_request_with_metadata(self):
        """Storage request can include metadata."""
        request = StorageRequest(
            content="Test",
            memory_type=MemoryType.EPISODIC,
            context={},
            metadata={
                "source": "user_prompt",
                "timestamp": datetime.now().isoformat(),
            },
        )

        assert request.metadata["source"] == "user_prompt"


class TestAgentReview:
    """Test AgentReview scoring logic."""

    def test_agent_review_creation(self):
        """Create agent review with score and reasoning."""
        review = AgentReview(
            agent_name="analyzer",
            importance_score=8,
            reasoning="Contains valuable pattern about agent usage",
            confidence=0.9,
        )

        assert review.agent_name == "analyzer"
        assert review.importance_score == 8
        assert 0 <= review.confidence <= 1.0

    def test_agent_review_score_bounded(self):
        """Review scores must be 0-10."""
        with pytest.raises(ValueError, match="0 and 10"):
            AgentReview(
                agent_name="analyzer",
                importance_score=15,  # Invalid
                reasoning="Test",
            )

    def test_agent_review_confidence_bounded(self):
        """Confidence must be 0.0-1.0."""
        with pytest.raises(ValueError, match="0.0 and 1.0"):
            AgentReview(
                agent_name="analyzer",
                importance_score=8,
                reasoning="Test",
                confidence=1.5,  # Invalid
            )


class TestReviewResult:
    """Test ReviewResult aggregation."""

    def test_review_result_aggregates_scores(self):
        """ReviewResult aggregates multiple agent scores."""
        reviews = [
            AgentReview("analyzer", 8, "Good pattern", 0.9),
            AgentReview("patterns", 7, "Useful insight", 0.85),
            AgentReview("knowledge-archaeologist", 9, "Important learning", 0.95),
        ]

        result = ReviewResult(reviews=reviews)

        # Average: (8 + 7 + 9) / 3 = 8.0
        assert result.average_score == pytest.approx(8.0)
        assert result.min_score == 7
        assert result.max_score == 9

    def test_review_result_weighted_by_confidence(self):
        """ReviewResult can weight scores by confidence."""
        reviews = [
            AgentReview("analyzer", 8, "Good", 1.0),  # Full confidence
            AgentReview("patterns", 4, "Maybe", 0.5),  # Low confidence
        ]

        result = ReviewResult(reviews=reviews)

        # Weighted average should favor high-confidence review
        assert result.weighted_average > 6.0

    def test_review_result_meets_threshold(self):
        """Check if review meets quality threshold."""
        reviews = [
            AgentReview("analyzer", 8, "Good", 0.9),
            AgentReview("patterns", 7, "Good", 0.9),
        ]

        result = ReviewResult(reviews=reviews)

        assert result.meets_threshold(4.0)  # Average 7.5 > 4.0
        assert not result.meets_threshold(9.0)  # Average 7.5 < 9.0


class TestQualityGate:
    """Test quality gate threshold logic."""

    def test_quality_gate_default_threshold(self):
        """Quality gate has default threshold of 4.0."""
        gate = QualityGate()
        assert gate.threshold == 4.0

    def test_quality_gate_custom_threshold(self):
        """Quality gate accepts custom threshold."""
        gate = QualityGate(threshold=7.0)
        assert gate.threshold == 7.0

    def test_quality_gate_passes_above_threshold(self):
        """Content above threshold passes gate."""
        gate = QualityGate(threshold=5.0)

        reviews = [
            AgentReview("analyzer", 8, "Good", 0.9),
            AgentReview("patterns", 7, "Good", 0.9),
        ]
        result = ReviewResult(reviews=reviews)

        assert gate.should_store(result)

    def test_quality_gate_rejects_below_threshold(self):
        """Content below threshold rejected."""
        gate = QualityGate(threshold=5.0)

        reviews = [
            AgentReview("analyzer", 3, "Low value", 0.9),
            AgentReview("patterns", 2, "Trivial", 0.9),
        ]
        result = ReviewResult(reviews=reviews)

        assert not gate.should_store(result)

    def test_quality_gate_requires_minimum_reviews(self):
        """Quality gate requires minimum number of reviews."""
        gate = QualityGate(min_reviews=3)

        reviews = [
            AgentReview("analyzer", 8, "Good", 0.9),
            # Only 1 review, need 3
        ]
        result = ReviewResult(reviews=reviews)

        assert not gate.should_store(result)


class TestStoragePipeline:
    """Test complete storage pipeline."""

    @pytest.fixture
    def mock_db(self):
        """Mock database fer testing."""
        return Mock()

    @pytest.fixture
    def mock_task_tool(self):
        """Mock Task tool fer agent invocation."""
        return AsyncMock()

    def test_storage_pipeline_creation(self, mock_db):
        """Create storage pipeline with database."""
        pipeline = StoragePipeline(database=mock_db)
        assert pipeline.database == mock_db

    @pytest.mark.asyncio
    async def test_store_with_review_invokes_agents(self, mock_db, mock_task_tool):
        """Storage pipeline invokes multiple agents fer review."""
        pipeline = StoragePipeline(database=mock_db)

        # Mock agent responses
        mock_task_tool.side_effect = [
            {"importance_score": 8, "reasoning": "Good pattern"},
            {"importance_score": 7, "reasoning": "Useful"},
            {"importance_score": 9, "reasoning": "Important"},
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task_tool):
            request = StorageRequest(
                content="Architect works better with specs",
                memory_type=MemoryType.SEMANTIC,
            )

            await pipeline.store_with_review(request)

            # Should invoke 3 agents (analyzer, patterns, knowledge-archaeologist)
            assert mock_task_tool.call_count == 3

    @pytest.mark.asyncio
    async def test_store_with_review_passes_quality_gate(self, mock_db):
        """Content above threshold is stored."""
        pipeline = StoragePipeline(database=mock_db)

        # Mock high-quality agent reviews
        with patch.object(
            pipeline,
            "_invoke_agent_review",
            side_effect=[
                AgentReview("analyzer", 8, "Good", 0.9),
                AgentReview("patterns", 7, "Good", 0.9),
                AgentReview("knowledge-archaeologist", 9, "Good", 0.9),
            ],
        ):
            request = StorageRequest(
                content="Important pattern",
                memory_type=MemoryType.SEMANTIC,
            )

            result = await pipeline.store_with_review(request)

            assert result.stored
            assert result.memory_id is not None
            assert mock_db.insert.called

    @pytest.mark.asyncio
    async def test_store_with_review_rejects_low_quality(self, mock_db):
        """Content below threshold is rejected."""
        pipeline = StoragePipeline(database=mock_db)

        # Mock low-quality agent reviews
        with patch.object(
            pipeline,
            "_invoke_agent_review",
            side_effect=[
                AgentReview("analyzer", 2, "Trivial", 0.9),
                AgentReview("patterns", 3, "Low value", 0.9),
                AgentReview("knowledge-archaeologist", 2, "Not useful", 0.9),
            ],
        ):
            request = StorageRequest(
                content="Hello",
                memory_type=MemoryType.EPISODIC,
            )

            result = await pipeline.store_with_review(request)

            assert not result.stored
            assert result.rejection_reason == "below_threshold"
            assert not mock_db.insert.called

    @pytest.mark.asyncio
    async def test_store_parallel_agent_review(self, mock_db):
        """Agent reviews execute in parallel fer performance."""
        import time

        pipeline = StoragePipeline(database=mock_db)

        async def slow_review(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return AgentReview("test", 8, "Good", 0.9)

        with patch.object(pipeline, "_invoke_agent_review", slow_review):
            request = StorageRequest(
                content="Test",
                memory_type=MemoryType.SEMANTIC,
            )

            start = time.perf_counter()
            await pipeline.store_with_review(request)
            duration = time.perf_counter() - start

            # With 3 agents @ 100ms each:
            # Sequential: ~300ms
            # Parallel: ~100ms
            # Allow some overhead but should be <200ms fer parallel
            assert duration < 0.2

    @pytest.mark.asyncio
    async def test_store_handles_agent_failure_gracefully(self, mock_db):
        """Pipeline handles agent failures gracefully."""
        pipeline = StoragePipeline(database=mock_db)

        # Mock agent failure
        with patch.object(
            pipeline,
            "_invoke_agent_review",
            side_effect=[
                AgentReview("analyzer", 8, "Good", 0.9),
                Exception("Agent failed"),  # One agent fails
                AgentReview("knowledge-archaeologist", 7, "Good", 0.9),
            ],
        ):
            request = StorageRequest(
                content="Test",
                memory_type=MemoryType.SEMANTIC,
            )

            result = await pipeline.store_with_review(request)

            # Should still get result with 2 successful reviews
            assert len(result.reviews) == 2

    def test_store_includes_metadata(self, mock_db):
        """Stored memories include metadata."""
        pipeline = StoragePipeline(database=mock_db)

        request = StorageRequest(
            content="Test",
            memory_type=MemoryType.SEMANTIC,
            metadata={
                "source": "user_prompt",
                "session_id": "123",
            },
        )

        # Mock successful storage
        with patch.object(
            pipeline,
            "store_with_review",
            return_value=StorageResult(
                stored=True,
                memory_id="mem-123",
            ),
        ):
            pipeline.store_with_review(request)

            # Verify metadata passed through
            assert mock_db.insert.called


class TestStorageResult:
    """Test StorageResult data structure."""

    def test_storage_result_success(self):
        """StorageResult fer successful storage."""
        result = StorageResult(
            stored=True,
            memory_id="mem-123",
            reviews=[
                AgentReview("analyzer", 8, "Good", 0.9),
            ],
        )

        assert result.stored
        assert result.memory_id == "mem-123"
        assert len(result.reviews) == 1

    def test_storage_result_rejection(self):
        """StorageResult fer rejected content."""
        result = StorageResult(
            stored=False,
            rejection_reason="below_threshold",
            reviews=[
                AgentReview("analyzer", 2, "Trivial", 0.9),
            ],
        )

        assert not result.stored
        assert result.rejection_reason == "below_threshold"
        assert result.memory_id is None

    def test_storage_result_get_summary(self):
        """Get human-readable summary of storage result."""
        result = StorageResult(
            stored=True,
            memory_id="mem-123",
            reviews=[
                AgentReview("analyzer", 8, "Good", 0.9),
                AgentReview("patterns", 7, "Useful", 0.9),
            ],
        )

        summary = result.get_summary()
        assert "mem-123" in summary
        assert "stored" in summary.lower()
        assert "8" in summary or "7" in summary  # Contains scores


class TestStoragePerformance:
    """Test storage pipeline performance requirements."""

    @pytest.mark.asyncio
    async def test_storage_completes_under_500ms(self, mock_db):
        """Storage pipeline completes in <500ms (P95)."""
        import time

        pipeline = StoragePipeline(database=mock_db)

        # Mock fast agent reviews
        with patch.object(
            pipeline,
            "_invoke_agent_review",
            return_value=AgentReview("test", 8, "Good", 0.9),
        ):
            request = StorageRequest(
                content="Test",
                memory_type=MemoryType.SEMANTIC,
            )

            start = time.perf_counter()
            await pipeline.store_with_review(request)
            duration = time.perf_counter() - start

            # Should complete quickly with parallel agents
            assert duration < 0.5


class TestStorageEdgeCases:
    """Test edge cases in storage pipeline."""

    def test_store_empty_content_rejected(self, mock_db):
        """Empty content cannot be stored."""
        with pytest.raises(ValueError, match="content"):
            StorageRequest(
                content="",
                memory_type=MemoryType.SEMANTIC,
            )

    @pytest.mark.asyncio
    async def test_store_duplicate_content_detection(self, mock_db):
        """Detect and handle duplicate content."""
        pipeline = StoragePipeline(database=mock_db)

        content = "Architect works better with specs"

        # Store first time
        mock_db.find_similar.return_value = []
        request1 = StorageRequest(content=content, memory_type=MemoryType.SEMANTIC)

        # Mock successful review
        with patch.object(
            pipeline,
            "_invoke_agent_review",
            return_value=AgentReview("test", 8, "Good", 0.9),
        ):
            result1 = await pipeline.store_with_review(request1)
            assert result1.stored

        # Try to store duplicate
        mock_db.find_similar.return_value = [{"id": "mem-123", "content": content}]
        request2 = StorageRequest(content=content, memory_type=MemoryType.SEMANTIC)

        result2 = await pipeline.store_with_review(request2)
        assert not result2.stored
        assert result2.rejection_reason == "duplicate"

    def test_store_very_long_content(self, mock_db):
        """Handle very long content appropriately."""
        # 10K word content
        long_content = "test " * 10000

        request = StorageRequest(
            content=long_content,
            memory_type=MemoryType.SEMANTIC,
        )

        # Should handle without error (may truncate or chunk)
        assert request.content
