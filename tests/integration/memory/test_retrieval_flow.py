"""Integration tests fer complete retrieval flow.

Tests end-to-end retrieval from query through relevance scoring
to context formatting.

Philosophy:
- Test multiple components working together
- Use real database with test data
- Validate complete retrieval behavior
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

# These imports will fail until implementation exists (TDD)
try:
    from amplihack.memory.coordinator import MemoryCoordinator
    from amplihack.memory.database import MemoryDatabase
    from amplihack.memory.retrieval_pipeline import (
        RetrievalPipeline,
        RetrievalQuery,
    )
    from amplihack.memory.types import MemoryEntry, MemoryType
except ImportError:
    pytest.skip("Memory system not implemented yet", allow_module_level=True)


class TestRetrievalFlowIntegration:
    """Test complete retrieval flow integration."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database with test data."""
        db_path = tmp_path / "test_memory.db"
        db = MemoryDatabase(db_path)
        db.initialize()

        # Insert test memories
        test_memories = [
            {
                "content": "To fix CI failures: check logs, identify issue, fix, rerun tests",
                "memory_type": MemoryType.PROCEDURAL,
                "timestamp": datetime.now(),
                "metadata": {"usage_count": 5},
            },
            {
                "content": "Always validate user input before database operations",
                "memory_type": MemoryType.SEMANTIC,
                "timestamp": datetime.now() - timedelta(days=7),
                "metadata": {"confidence": 0.9},
            },
            {
                "content": "User asked about authentication implementation on Dec 1",
                "memory_type": MemoryType.EPISODIC,
                "timestamp": datetime.now() - timedelta(days=30),
                "metadata": {"participants": ["user", "claude"]},
            },
            {
                "content": "Refactor auth module after code review completes",
                "memory_type": MemoryType.PROSPECTIVE,
                "timestamp": datetime.now(),
                "metadata": {"trigger": "code review", "deadline": None},
            },
            {
                "content": "Currently working on auth.py JWT validation function",
                "memory_type": MemoryType.WORKING,
                "timestamp": datetime.now(),
                "metadata": {"task_id": "auth-123", "file": "auth.py"},
            },
        ]

        for mem in test_memories:
            db.insert(
                content=mem["content"],
                memory_type=mem["memory_type"],
                timestamp=mem["timestamp"],
                metadata=mem["metadata"],
            )

        yield db
        db.close()

    @pytest.mark.asyncio
    async def test_retrieve_relevant_memories_fer_query(self, temp_db):
        """Retrieve relevant memories fer specific query."""
        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="How do we fix CI failures?",
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        # Should return relevant memories
        assert len(result.memories) > 0

        # Most relevant should be procedural about CI
        assert result.memories[0].memory_type == MemoryType.PROCEDURAL
        assert "CI" in result.memories[0].content

    @pytest.mark.asyncio
    async def test_retrieve_respects_memory_type_filter(self, temp_db):
        """Retrieval respects memory type filter."""
        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="authentication",
            memory_types=[MemoryType.PROCEDURAL, MemoryType.SEMANTIC],
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        # Should only return procedural and semantic
        for memory in result.memories:
            assert memory.memory_type in [
                MemoryType.PROCEDURAL,
                MemoryType.SEMANTIC,
            ]

    @pytest.mark.asyncio
    async def test_retrieve_respects_token_budget(self, temp_db):
        """Retrieval respects strict token budget."""
        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="authentication",
            token_budget=200,  # Small budget
        )

        result = await pipeline.retrieve_relevant(query)

        # Total tokens must not exceed budget
        assert result.total_tokens <= 200

        # Should return fewer memories due to budget constraint
        assert len(result.memories) < 5

    @pytest.mark.asyncio
    async def test_retrieve_prioritizes_recent_memories(self, temp_db):
        """Recent memories prioritized over old ones with same relevance."""
        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="authentication",
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        # Recent working memory should be prioritized
        recent_memories = [
            m for m in result.memories if m.timestamp > datetime.now() - timedelta(days=1)
        ]
        old_memories = [
            m for m in result.memories if m.timestamp < datetime.now() - timedelta(days=20)
        ]

        # Recent should appear first
        if recent_memories and old_memories:
            recent_pos = result.memories.index(recent_memories[0])
            old_pos = result.memories.index(old_memories[0])
            assert recent_pos < old_pos

    @pytest.mark.asyncio
    async def test_retrieve_prioritizes_procedural_and_semantic(self, temp_db):
        """Procedural and semantic memories prioritized."""
        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="validation",
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        # Semantic memory about validation should be highly ranked
        semantic_memory = [m for m in result.memories if m.memory_type == MemoryType.SEMANTIC][0]

        # Should be in top results
        assert result.memories.index(semantic_memory) < 3

    @pytest.mark.asyncio
    async def test_retrieve_filters_by_time_range(self, temp_db):
        """Retrieval filters by time range."""
        pipeline = RetrievalPipeline(database=temp_db)

        # Only want last 7 days
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        query = RetrievalQuery(
            query_text="authentication",
            token_budget=5000,
            time_range=(week_ago, now),
        )

        result = await pipeline.retrieve_relevant(query)

        # All returned memories should be recent
        for memory in result.memories:
            assert memory.timestamp >= week_ago

    @pytest.mark.asyncio
    async def test_retrieve_empty_fer_no_matches(self, temp_db):
        """Retrieval returns empty fer no matches."""
        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="quantum physics",  # Not in test data
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        # Should return empty or very low relevance
        assert len(result.memories) == 0 or all(m.relevance < 0.3 for m in result.memories)

    @pytest.mark.asyncio
    async def test_retrieve_formatted_context(self, temp_db):
        """Retrieval provides formatted context fer injection."""
        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="CI failures",
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        # Get formatted context
        formatted = result.get_formatted_context()

        assert formatted
        assert isinstance(formatted, str)
        assert "CI" in formatted or "failures" in formatted

        # Should include memory type labels
        assert "PROCEDURAL" in formatted or "Procedural" in formatted


class TestRetrievalWithCoordinator:
    """Test retrieval through MemoryCoordinator."""

    @pytest.fixture
    def coordinator(self, temp_db):
        """Create coordinator with test database."""
        return MemoryCoordinator(database=temp_db)

    @pytest.mark.asyncio
    async def test_coordinator_retrieve_delegates_to_pipeline(self, coordinator, temp_db):
        """Coordinator delegates to retrieval pipeline."""
        query = RetrievalQuery(
            query_text="CI failures",
            token_budget=5000,
        )

        memories = await coordinator.retrieve(query)

        assert isinstance(memories, list)
        assert len(memories) > 0

    @pytest.mark.asyncio
    async def test_coordinator_retrieve_returns_memory_entries(self, coordinator, temp_db):
        """Coordinator returns list of MemoryEntry objects."""
        query = RetrievalQuery(
            query_text="authentication",
            token_budget=5000,
        )

        memories = await coordinator.retrieve(query)

        for memory in memories:
            assert isinstance(memory, MemoryEntry)
            assert memory.id
            assert memory.content
            assert memory.memory_type


class TestRetrievalTokenBudget:
    """Test token budget enforcement in retrieval."""

    @pytest.mark.asyncio
    async def test_budget_strictly_enforced(self, temp_db):
        """Token budget never exceeded."""
        pipeline = RetrievalPipeline(database=temp_db)

        # Test with various budget sizes
        budgets = [100, 500, 1000, 5000]

        for budget in budgets:
            query = RetrievalQuery(
                query_text="authentication",
                token_budget=budget,
            )

            result = await pipeline.retrieve_relevant(query)

            # Strict enforcement
            assert result.total_tokens <= budget

    @pytest.mark.asyncio
    async def test_budget_allocation_by_relevance(self, temp_db):
        """Higher relevance memories get more tokens."""
        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="CI failures",
            token_budget=1000,
        )

        result = await pipeline.retrieve_relevant(query)

        if len(result.memories) > 1:
            # Most relevant should get more token allocation
            # (measured by how much of content is included)
            first_memory_tokens = result.memory_tokens[result.memories[0].id]
            last_memory_tokens = result.memory_tokens[result.memories[-1].id]

            assert first_memory_tokens >= last_memory_tokens

    @pytest.mark.asyncio
    async def test_zero_budget_returns_empty(self, temp_db):
        """Zero token budget returns no memories."""
        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="authentication",
            token_budget=0,
        )

        result = await pipeline.retrieve_relevant(query)

        assert len(result.memories) == 0
        assert result.total_tokens == 0


class TestRetrievalRelevanceScoring:
    """Test relevance scoring in retrieval flow."""

    @pytest.mark.asyncio
    async def test_exact_keyword_match_high_score(self, temp_db):
        """Exact keyword matches score highest."""
        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="CI failures",
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        # Top result should be procedural about CI
        top_memory = result.memories[0]
        assert "CI" in top_memory.content or "failures" in top_memory.content
        assert top_memory.relevance > 0.7

    @pytest.mark.asyncio
    async def test_semantic_similarity_scoring(self, temp_db):
        """Semantic similarity scored beyond keyword matching."""
        pipeline = RetrievalPipeline(database=temp_db)

        # Query with synonyms
        query = RetrievalQuery(
            query_text="input sanitization",  # Similar to "validation"
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)

        # Validation memory should still be relevant
        validation_memories = [m for m in result.memories if "validate" in m.content.lower()]

        if validation_memories:
            assert validation_memories[0].relevance > 0.4


class TestRetrievalPerformance:
    """Test retrieval performance requirements."""

    @pytest.mark.asyncio
    async def test_retrieval_completes_under_50ms(self, temp_db):
        """Retrieval completes under 50ms requirement."""
        import time

        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="authentication",
            token_budget=5000,
        )

        start = time.perf_counter()
        await pipeline.retrieve_relevant(query)
        duration = time.perf_counter() - start

        # Should be very fast
        assert duration < 0.05

    @pytest.mark.asyncio
    async def test_retrieval_scalable_to_large_db(self, temp_db):
        """Retrieval performs well with many memories."""
        # Add 100 more memories
        for i in range(100):
            temp_db.insert(
                content=f"Test memory {i} about various topics",
                memory_type=MemoryType.SEMANTIC,
                timestamp=datetime.now(),
                metadata={},
            )

        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="authentication",
            token_budget=5000,
        )

        import time

        start = time.perf_counter()
        await pipeline.retrieve_relevant(query)
        duration = time.perf_counter() - start

        # Should still be fast even with 105 memories
        assert duration < 0.1


class TestRetrievalContextFormatting:
    """Test context formatting in retrieval flow."""

    @pytest.mark.asyncio
    async def test_formatted_context_includes_type_labels(self, temp_db):
        """Formatted context labels memory types."""
        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="authentication",
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)
        formatted = result.get_formatted_context()

        # Should include type labels
        assert "PROCEDURAL" in formatted or "Procedural" in formatted
        assert "SEMANTIC" in formatted or "Semantic" in formatted

    @pytest.mark.asyncio
    async def test_formatted_context_groups_by_type(self, temp_db):
        """Formatted context groups memories by type."""
        pipeline = RetrievalPipeline(database=temp_db, group_by_type=True)

        query = RetrievalQuery(
            query_text="authentication",
            token_budget=5000,
        )

        result = await pipeline.retrieve_relevant(query)
        formatted = result.get_formatted_context()

        # Procedural memories should be grouped together
        # (all procedural mentions before semantic mentions)
        procedural_indices = [
            i for i, line in enumerate(formatted.split("\n")) if "PROCEDURAL" in line
        ]
        semantic_indices = [i for i, line in enumerate(formatted.split("\n")) if "SEMANTIC" in line]

        if procedural_indices and semantic_indices:
            # All procedural should come before semantic (or vice versa)
            assert max(procedural_indices) < min(semantic_indices) or max(semantic_indices) < min(
                procedural_indices
            )

    @pytest.mark.asyncio
    async def test_formatted_context_respects_token_budget(self, temp_db):
        """Formatted context stays within token budget."""
        from amplihack.memory.token_budget import TokenCounter

        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="authentication",
            token_budget=500,  # Small budget
        )

        result = await pipeline.retrieve_relevant(query)
        formatted = result.get_formatted_context()

        # Count tokens in formatted context
        tokens = TokenCounter.count(formatted)

        # Should stay within budget (allow small overhead fer formatting)
        assert tokens <= 550  # 10% overhead allowed fer labels/formatting


class TestRetrievalErrorHandling:
    """Test error handling in retrieval flow."""

    @pytest.mark.asyncio
    async def test_retrieval_handles_db_errors_gracefully(self, temp_db):
        """Retrieval handles database errors."""
        pipeline = RetrievalPipeline(database=temp_db)

        # Mock database error
        with patch.object(temp_db, "search", side_effect=Exception("DB error")):
            query = RetrievalQuery(
                query_text="test",
                token_budget=5000,
            )

            result = await pipeline.retrieve_relevant(query)

            # Should not crash
            assert result.memories == []
            assert result.error == "DB error"

    @pytest.mark.asyncio
    async def test_retrieval_handles_malformed_memories(self, temp_db):
        """Retrieval handles malformed memory data."""
        # Insert malformed memory
        temp_db.execute(
            "INSERT INTO memories (content, memory_type) VALUES (?, ?)",
            ("Test", "INVALID_TYPE"),
        )

        pipeline = RetrievalPipeline(database=temp_db)

        query = RetrievalQuery(
            query_text="test",
            token_budget=5000,
        )

        # Should handle gracefully, skip malformed entries
        result = await pipeline.retrieve_relevant(query)

        # Should return valid memories only
        for memory in result.memories:
            assert memory.memory_type in [
                MemoryType.EPISODIC,
                MemoryType.SEMANTIC,
                MemoryType.PROSPECTIVE,
                MemoryType.PROCEDURAL,
                MemoryType.WORKING,
            ]
