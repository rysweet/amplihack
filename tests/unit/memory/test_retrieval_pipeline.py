"""Unit tests fer memory retrieval pipeline logic.

Tests retrieval pipeline that selects and formats relevant memories
within token budget fer context injection.

Philosophy:
- Test retrieval logic in isolation (mock DB)
- Validate relevance scoring
- Test budget enforcement
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

# These imports will fail until implementation exists (TDD)
try:
    from amplihack.memory.retrieval_pipeline import (
        ContextFormatter,
        RelevanceScorer,
        RetrievalPipeline,
        RetrievalQuery,
        RetrievalResult,
    )
    from amplihack.memory.types import MemoryEntry, MemoryType
except ImportError:
    pytest.skip("Retrieval pipeline not implemented yet", allow_module_level=True)


class TestRetrievalQuery:
    """Test RetrievalQuery data structure."""

    def test_create_retrieval_query(self):
        """Create retrieval query with required fields."""
        query = RetrievalQuery(
            query_text="How do we handle CI failures?",
            memory_types=[MemoryType.PROCEDURAL, MemoryType.SEMANTIC],
            token_budget=5000,
        )

        assert query.query_text
        assert len(query.memory_types) == 2
        assert query.token_budget == 5000

    def test_retrieval_query_defaults_all_types(self):
        """Query defaults to all memory types if none specified."""
        query = RetrievalQuery(
            query_text="Test query",
            token_budget=5000,
        )

        # Should include all 5 types by default
        assert len(query.memory_types) == 5

    def test_retrieval_query_requires_text(self):
        """Query must have query text."""
        with pytest.raises(ValueError, match="query_text"):
            RetrievalQuery(
                query_text="",
                token_budget=5000,
            )

    def test_retrieval_query_requires_positive_budget(self):
        """Query must have positive token budget."""
        with pytest.raises(ValueError, match="positive"):
            RetrievalQuery(
                query_text="Test",
                token_budget=-100,
            )

    def test_retrieval_query_with_time_range(self):
        """Query can filter by time range."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        query = RetrievalQuery(
            query_text="Recent discussions",
            token_budget=5000,
            time_range=(yesterday, now),
        )

        assert query.time_range
        assert query.time_range[0] == yesterday
        assert query.time_range[1] == now

    def test_retrieval_query_with_context(self):
        """Query can include context fer better matching."""
        query = RetrievalQuery(
            query_text="Fix authentication bug",
            token_budget=5000,
            context={
                "current_task": "implement-auth",
                "current_file": "auth.py",
            },
        )

        assert query.context["current_task"] == "implement-auth"


class TestRelevanceScorer:
    """Test relevance scoring logic."""

    def test_relevance_scorer_creation(self):
        """Create relevance scorer."""
        scorer = RelevanceScorer()
        assert scorer

    def test_score_exact_match_high_relevance(self):
        """Exact keyword match scores high relevance."""
        scorer = RelevanceScorer()

        query = "How to fix CI failures"
        memory_content = "To fix CI failures: check logs, fix issue, rerun tests"

        score = scorer.score(query, memory_content)
        assert score > 0.8  # High relevance

    def test_score_partial_match_medium_relevance(self):
        """Partial keyword match scores medium relevance."""
        scorer = RelevanceScorer()

        query = "authentication implementation"
        memory_content = "User authentication requires validation"

        score = scorer.score(query, memory_content)
        assert 0.4 < score < 0.8  # Medium relevance

    def test_score_no_match_low_relevance(self):
        """No keyword match scores low relevance."""
        scorer = RelevanceScorer()

        query = "database optimization"
        memory_content = "Frontend styling guidelines"

        score = scorer.score(query, memory_content)
        assert score < 0.3  # Low relevance

    def test_score_considers_recency(self):
        """Recent memories score higher than old memories."""
        scorer = RelevanceScorer(recency_weight=0.2)

        query = "test pattern"
        content = "test pattern example"

        now = datetime.now()
        old_timestamp = now - timedelta(days=30)

        recent_score = scorer.score(query, content, timestamp=now)
        old_score = scorer.score(query, content, timestamp=old_timestamp)

        assert recent_score > old_score

    def test_score_considers_memory_type_priority(self):
        """Procedural/semantic memories score higher than episodic."""
        scorer = RelevanceScorer()

        query = "How to deploy"
        content = "Deployment procedure"

        procedural_score = scorer.score(query, content, memory_type=MemoryType.PROCEDURAL)
        episodic_score = scorer.score(query, content, memory_type=MemoryType.EPISODIC)

        assert procedural_score > episodic_score

    def test_score_semantic_similarity(self):
        """Score considers semantic similarity, not just keywords."""
        scorer = RelevanceScorer()

        query = "fixing bugs"
        content = "resolving issues and defects"

        # Should score reasonably high despite different words
        score = scorer.score(query, content)
        assert score > 0.5


class TestRetrievalPipeline:
    """Test complete retrieval pipeline."""

    @pytest.fixture
    def mock_db(self):
        """Mock database fer testing."""
        db = Mock()
        db.search.return_value = []
        return db

    @pytest.fixture
    def sample_memories(self):
        """Sample memories fer testing."""
        return [
            MemoryEntry(
                id="mem-1",
                content="To fix CI: check logs, fix issue, rerun",
                memory_type=MemoryType.PROCEDURAL,
                timestamp=datetime.now(),
                metadata={"usage_count": 5},
            ),
            MemoryEntry(
                id="mem-2",
                content="Always validate input before processing",
                memory_type=MemoryType.SEMANTIC,
                timestamp=datetime.now() - timedelta(days=7),
                metadata={"confidence": 0.9},
            ),
            MemoryEntry(
                id="mem-3",
                content="User asked about authentication on Dec 1",
                memory_type=MemoryType.EPISODIC,
                timestamp=datetime.now() - timedelta(days=30),
                metadata={},
            ),
        ]

    def test_retrieval_pipeline_creation(self, mock_db):
        """Create retrieval pipeline with database."""
        pipeline = RetrievalPipeline(database=mock_db)
        assert pipeline.database == mock_db

    @pytest.mark.asyncio
    async def test_retrieve_relevant_memories(self, mock_db, sample_memories):
        """Retrieve relevant memories fer query."""
        mock_db.search.return_value = sample_memories
        pipeline = RetrievalPipeline(database=mock_db)

        query = RetrievalQuery(
            query_text="How to fix CI failures",
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        assert result.memories
        assert len(result.memories) > 0
        # Most relevant should be procedural memory about CI
        assert result.memories[0].memory_type == MemoryType.PROCEDURAL

    @pytest.mark.asyncio
    async def test_retrieve_respects_token_budget(self, mock_db, sample_memories):
        """Retrieval respects token budget."""
        mock_db.search.return_value = sample_memories
        pipeline = RetrievalPipeline(database=mock_db)

        query = RetrievalQuery(
            query_text="test query",
            token_budget=100,  # Very limited budget
        )

        result = await pipeline.retrieve_relevant(query)

        # Should only return memories that fit in budget
        assert result.total_tokens <= 100

    @pytest.mark.asyncio
    async def test_retrieve_filters_by_memory_type(self, mock_db, sample_memories):
        """Retrieval filters by requested memory types."""
        mock_db.search.return_value = sample_memories
        pipeline = RetrievalPipeline(database=mock_db)

        query = RetrievalQuery(
            query_text="test query",
            memory_types=[MemoryType.PROCEDURAL],
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        # Should only return procedural memories
        for memory in result.memories:
            assert memory.memory_type == MemoryType.PROCEDURAL

    @pytest.mark.asyncio
    async def test_retrieve_filters_by_time_range(self, mock_db, sample_memories):
        """Retrieval filters by time range."""
        mock_db.search.return_value = sample_memories
        pipeline = RetrievalPipeline(database=mock_db)

        # Only want memories from last 7 days
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        query = RetrievalQuery(
            query_text="test query",
            token_budget=5000,
            time_range=(week_ago, now),
        )

        result = await pipeline.retrieve_relevant(query)

        # Should only return recent memories
        for memory in result.memories:
            assert memory.timestamp >= week_ago

    @pytest.mark.asyncio
    async def test_retrieve_prioritizes_by_relevance(self, mock_db, sample_memories):
        """Retrieval returns most relevant memories first."""
        mock_db.search.return_value = sample_memories
        pipeline = RetrievalPipeline(database=mock_db)

        query = RetrievalQuery(
            query_text="CI failures",
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        # First memory should be most relevant (procedural about CI)
        assert "CI" in result.memories[0].content or "fix" in result.memories[0].content

    @pytest.mark.asyncio
    async def test_retrieve_min_relevance_threshold(self, mock_db, sample_memories):
        """Retrieval only returns memories above relevance threshold."""
        mock_db.search.return_value = sample_memories
        pipeline = RetrievalPipeline(database=mock_db, min_relevance=0.7)

        query = RetrievalQuery(
            query_text="database optimization",  # Not relevant to samples
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        # Should return few or no memories (low relevance)
        assert len(result.memories) < len(sample_memories)

    @pytest.mark.asyncio
    async def test_retrieve_empty_when_no_matches(self, mock_db):
        """Retrieval returns empty result when no matches."""
        mock_db.search.return_value = []
        pipeline = RetrievalPipeline(database=mock_db)

        query = RetrievalQuery(
            query_text="test query",
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        assert len(result.memories) == 0
        assert result.total_tokens == 0


class TestRetrievalResult:
    """Test RetrievalResult data structure."""

    def test_retrieval_result_creation(self):
        """Create retrieval result with memories."""
        memories = [
            MemoryEntry(
                id="mem-1",
                content="Test memory",
                memory_type=MemoryType.SEMANTIC,
                timestamp=datetime.now(),
            ),
        ]

        result = RetrievalResult(
            memories=memories,
            total_tokens=150,
            query_metadata={"query": "test"},
        )

        assert len(result.memories) == 1
        assert result.total_tokens == 150
        assert result.query_metadata["query"] == "test"

    def test_retrieval_result_empty(self):
        """Empty retrieval result."""
        result = RetrievalResult(
            memories=[],
            total_tokens=0,
        )

        assert len(result.memories) == 0
        assert result.is_empty()

    def test_retrieval_result_get_by_type(self):
        """Get memories filtered by type."""
        memories = [
            MemoryEntry(
                id="mem-1",
                content="Procedural",
                memory_type=MemoryType.PROCEDURAL,
                timestamp=datetime.now(),
            ),
            MemoryEntry(
                id="mem-2",
                content="Semantic",
                memory_type=MemoryType.SEMANTIC,
                timestamp=datetime.now(),
            ),
        ]

        result = RetrievalResult(memories=memories, total_tokens=200)

        procedural = result.get_by_type(MemoryType.PROCEDURAL)
        assert len(procedural) == 1
        assert procedural[0].memory_type == MemoryType.PROCEDURAL


class TestContextFormatter:
    """Test context formatting fer injection."""

    def test_format_memories_fer_injection(self):
        """Format memories into context string."""
        formatter = ContextFormatter()

        memories = [
            MemoryEntry(
                id="mem-1",
                content="Pattern: Always validate input",
                memory_type=MemoryType.SEMANTIC,
                timestamp=datetime.now(),
            ),
            MemoryEntry(
                id="mem-2",
                content="Procedure: Fix CI by checking logs",
                memory_type=MemoryType.PROCEDURAL,
                timestamp=datetime.now(),
            ),
        ]

        formatted = formatter.format(memories)

        assert "Pattern: Always validate input" in formatted
        assert "Procedure: Fix CI by checking logs" in formatted
        assert "SEMANTIC" in formatted or "Semantic" in formatted
        assert "PROCEDURAL" in formatted or "Procedural" in formatted

    def test_format_includes_metadata(self):
        """Formatted context includes relevant metadata."""
        formatter = ContextFormatter(include_metadata=True)

        memory = MemoryEntry(
            id="mem-1",
            content="Test content",
            memory_type=MemoryType.SEMANTIC,
            timestamp=datetime.now(),
            metadata={"confidence": 0.9, "source": "user"},
        )

        formatted = formatter.format([memory])

        assert "confidence" in formatted.lower() or "0.9" in formatted

    def test_format_groups_by_type(self):
        """Formatter can group memories by type."""
        formatter = ContextFormatter(group_by_type=True)

        memories = [
            MemoryEntry(
                id="mem-1",
                content="Semantic 1",
                memory_type=MemoryType.SEMANTIC,
                timestamp=datetime.now(),
            ),
            MemoryEntry(
                id="mem-2",
                content="Procedural 1",
                memory_type=MemoryType.PROCEDURAL,
                timestamp=datetime.now(),
            ),
            MemoryEntry(
                id="mem-3",
                content="Semantic 2",
                memory_type=MemoryType.SEMANTIC,
                timestamp=datetime.now(),
            ),
        ]

        formatted = formatter.format(memories)

        # Semantic memories should be grouped together
        semantic_pos = formatted.index("Semantic 1")
        semantic2_pos = formatted.index("Semantic 2")
        procedural_pos = formatted.index("Procedural 1")

        # Semantic memories should be adjacent
        assert abs(semantic2_pos - semantic_pos) < abs(procedural_pos - semantic_pos)


class TestRetrievalPerformance:
    """Test retrieval pipeline performance requirements."""

    @pytest.mark.asyncio
    async def test_retrieval_completes_under_50ms(self, mock_db):
        """Retrieval completes in <50ms (fast)."""
        import time

        # Mock fast database search
        mock_db.search.return_value = [
            MemoryEntry(
                id=f"mem-{i}",
                content=f"Memory {i}",
                memory_type=MemoryType.SEMANTIC,
                timestamp=datetime.now(),
            )
            for i in range(10)
        ]

        pipeline = RetrievalPipeline(database=mock_db)

        query = RetrievalQuery(
            query_text="test query",
            token_budget=5000,
        )

        start = time.perf_counter()
        await pipeline.retrieve_relevant(query)
        duration = time.perf_counter() - start

        # Should complete very quickly
        assert duration < 0.05  # 50ms


class TestRetrievalEdgeCases:
    """Test edge cases in retrieval pipeline."""

    @pytest.mark.asyncio
    async def test_retrieve_with_zero_budget(self, mock_db):
        """Retrieve with zero budget returns empty."""
        pipeline = RetrievalPipeline(database=mock_db)

        query = RetrievalQuery(
            query_text="test",
            token_budget=0,
        )

        result = await pipeline.retrieve_relevant(query)
        assert len(result.memories) == 0

    @pytest.mark.asyncio
    async def test_retrieve_with_very_large_budget(self, mock_db, sample_memories):
        """Retrieve with huge budget returns all relevant memories."""
        mock_db.search.return_value = sample_memories
        pipeline = RetrievalPipeline(database=mock_db)

        query = RetrievalQuery(
            query_text="test",
            token_budget=1000000,  # 1M tokens
        )

        result = await pipeline.retrieve_relevant(query)
        # Should return all memories that pass relevance threshold
        assert len(result.memories) > 0

    @pytest.mark.asyncio
    async def test_retrieve_handles_db_errors_gracefully(self, mock_db):
        """Retrieval handles database errors gracefully."""
        mock_db.search.side_effect = Exception("DB error")
        pipeline = RetrievalPipeline(database=mock_db)

        query = RetrievalQuery(
            query_text="test",
            token_budget=5000,
        )

        # Should not crash, return empty result
        result = await pipeline.retrieve_relevant(query)
        assert result.memories == []
        assert result.error == "DB error"

    @pytest.mark.asyncio
    async def test_retrieve_deduplicates_similar_memories(self, mock_db, sample_memories):
        """Retrieval deduplicates very similar memories."""
        # Add duplicate memory
        duplicate = MemoryEntry(
            id="mem-4",
            content="To fix CI: check logs, fix issue, rerun tests",  # Very similar to mem-1
            memory_type=MemoryType.PROCEDURAL,
            timestamp=datetime.now(),
        )
        sample_memories.append(duplicate)

        mock_db.search.return_value = sample_memories
        pipeline = RetrievalPipeline(database=mock_db, deduplicate=True)

        query = RetrievalQuery(
            query_text="CI failures",
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        # Should only return one of the duplicate memories
        ci_memories = [m for m in result.memories if "CI" in m.content]
        assert len(ci_memories) == 1
