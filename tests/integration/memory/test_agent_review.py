"""Integration tests fer multi-agent review coordination.

Tests parallel agent invocation and consensus building
fer memory importance scoring.

Philosophy:
- Test agent coordination (mocked Task tool)
- Validate parallel execution
- Test consensus mechanisms
"""

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# These imports will fail until implementation exists (TDD)
try:
    from amplihack.memory.agent_review import (
        AgentReview,
        AgentReviewCoordinator,
        ConsensusBuilder,
        ParallelReviewer,
    )

    from amplihack.memory.types import MemoryType
except ImportError:
    pytest.skip("Agent review not implemented yet", allow_module_level=True)


class TestParallelAgentReview:
    """Test parallel agent invocation fer reviews."""

    @pytest.fixture
    def mock_task_tool(self):
        """Mock Task tool fer agent invocation."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_three_agents_invoked_in_parallel(self, mock_task_tool):
        """Three agents invoked in parallel fer efficiency."""
        coordinator = AgentReviewCoordinator()

        # Mock agent responses
        mock_task_tool.side_effect = [
            {"importance_score": 8, "reasoning": "Analyzer: Good pattern"},
            {"importance_score": 7, "reasoning": "Patterns: Useful"},
            {"importance_score": 9, "reasoning": "Archaeologist: Important"},
        ]

        with patch("amplihack.memory.agent_review.Task", mock_task_tool):
            content = "Architect works better with module specs"
            memory_type = MemoryType.SEMANTIC

            reviews = await coordinator.review_importance(content, memory_type)

            # Should invoke all 3 agents
            assert mock_task_tool.call_count == 3
            assert len(reviews) == 3

    @pytest.mark.asyncio
    async def test_parallel_faster_than_sequential(self, mock_task_tool):
        """Parallel execution significantly faster than sequential."""
        coordinator_parallel = AgentReviewCoordinator(parallel=True)
        coordinator_sequential = AgentReviewCoordinator(parallel=False)

        async def slow_agent(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return {"importance_score": 8, "reasoning": "Good"}

        content = "Test content"
        memory_type = MemoryType.SEMANTIC

        # Test parallel
        with patch("amplihack.memory.agent_review.Task", slow_agent):
            start = time.perf_counter()
            await coordinator_parallel.review_importance(content, memory_type)
            parallel_time = time.perf_counter() - start

        # Test sequential
        with patch("amplihack.memory.agent_review.Task", slow_agent):
            start = time.perf_counter()
            await coordinator_sequential.review_importance(content, memory_type)
            sequential_time = time.perf_counter() - start

        # Parallel should be ~3x faster (3 agents @ 100ms each)
        # Parallel: ~100ms, Sequential: ~300ms
        assert parallel_time < sequential_time * 0.5

    @pytest.mark.asyncio
    async def test_agent_review_completes_under_500ms(self, mock_task_tool):
        """Agent review completes under 500ms requirement."""
        coordinator = AgentReviewCoordinator()

        # Mock fast responses
        mock_task_tool.side_effect = [
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 7, "reasoning": "Good"},
            {"importance_score": 9, "reasoning": "Good"},
        ]

        with patch("amplihack.memory.agent_review.Task", mock_task_tool):
            content = "Test content"
            memory_type = MemoryType.SEMANTIC

            start = time.perf_counter()
            await coordinator.review_importance(content, memory_type)
            duration = time.perf_counter() - start

            # Should complete very quickly with parallel execution
            assert duration < 0.5


class TestAgentReviewContent:
    """Test agent review content and prompts."""

    @pytest.fixture
    def mock_task_tool(self):
        """Mock Task tool fer capturing prompts."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_agents_receive_content_and_context(self, mock_task_tool):
        """Agents receive content and context in prompt."""
        coordinator = AgentReviewCoordinator()

        mock_task_tool.return_value = {
            "importance_score": 8,
            "reasoning": "Good",
        }

        with patch("amplihack.memory.agent_review.Task", mock_task_tool):
            content = "Test pattern about architect"
            context = {"session": "test-123", "source": "user_prompt"}

            await coordinator.review_importance(content, MemoryType.SEMANTIC, context=context)

            # Check that agents received content and context
            for call in mock_task_tool.call_args_list:
                args, kwargs = call
                prompt = kwargs.get("prompt", "")
                assert "Test pattern about architect" in prompt
                assert "SEMANTIC" in prompt or "Semantic" in prompt

    @pytest.mark.asyncio
    async def test_agents_invoked_with_correct_subagent_types(self, mock_task_tool):
        """Agents invoked with correct subagent types."""
        coordinator = AgentReviewCoordinator()

        mock_task_tool.return_value = {
            "importance_score": 8,
            "reasoning": "Good",
        }

        with patch("amplihack.memory.agent_review.Task", mock_task_tool):
            await coordinator.review_importance("Test", MemoryType.SEMANTIC)

            # Check subagent types
            called_agents = []
            for call in mock_task_tool.call_args_list:
                args, kwargs = call
                subagent_type = kwargs.get("subagent_type", "")
                called_agents.append(subagent_type)

            # Should invoke analyzer, patterns, knowledge-archaeologist
            assert "analyzer" in called_agents
            assert "patterns" in called_agents
            assert (
                "knowledge-archaeologist" in called_agents
                or "knowledge_archaeologist" in called_agents
            )


class TestConsensusBuilding:
    """Test consensus building from agent reviews."""

    def test_consensus_average_score(self):
        """Consensus calculates average score."""
        reviews = [
            AgentReview("analyzer", 8, "Good", 0.9),
            AgentReview("patterns", 7, "Useful", 0.85),
            AgentReview("knowledge-archaeologist", 9, "Important", 0.95),
        ]

        consensus = ConsensusBuilder.build_consensus(reviews)

        # Average: (8 + 7 + 9) / 3 = 8.0
        assert consensus.average_score == pytest.approx(8.0)

    def test_consensus_weighted_by_confidence(self):
        """Consensus weighted by agent confidence."""
        reviews = [
            AgentReview("analyzer", 8, "High confidence", 1.0),
            AgentReview("patterns", 4, "Low confidence", 0.5),
        ]

        consensus = ConsensusBuilder.build_consensus(reviews, weighted=True)

        # Weighted should favor high-confidence review
        assert consensus.weighted_average > 6.0

    def test_consensus_meets_threshold(self):
        """Check if consensus meets quality threshold."""
        reviews_high = [
            AgentReview("analyzer", 8, "Good", 0.9),
            AgentReview("patterns", 9, "Good", 0.9),
        ]

        reviews_low = [
            AgentReview("analyzer", 2, "Poor", 0.9),
            AgentReview("patterns", 3, "Poor", 0.9),
        ]

        consensus_high = ConsensusBuilder.build_consensus(reviews_high)
        consensus_low = ConsensusBuilder.build_consensus(reviews_low)

        threshold = 4.0

        assert consensus_high.meets_threshold(threshold)
        assert not consensus_low.meets_threshold(threshold)

    def test_consensus_requires_minimum_reviews(self):
        """Consensus requires minimum number of reviews."""
        reviews_insufficient = [
            AgentReview("analyzer", 8, "Good", 0.9),
            # Only 1 review
        ]

        reviews_sufficient = [
            AgentReview("analyzer", 8, "Good", 0.9),
            AgentReview("patterns", 7, "Good", 0.9),
            AgentReview("knowledge-archaeologist", 9, "Good", 0.9),
        ]

        # With min_reviews=3
        consensus_insufficient = ConsensusBuilder.build_consensus(
            reviews_insufficient, min_reviews=3
        )
        consensus_sufficient = ConsensusBuilder.build_consensus(reviews_sufficient, min_reviews=3)

        assert not consensus_insufficient.is_valid()
        assert consensus_sufficient.is_valid()

    def test_consensus_tracks_disagreement(self):
        """Consensus tracks level of disagreement."""
        reviews_agree = [
            AgentReview("analyzer", 8, "Good", 0.9),
            AgentReview("patterns", 8, "Good", 0.9),
            AgentReview("knowledge-archaeologist", 8, "Good", 0.9),
        ]

        reviews_disagree = [
            AgentReview("analyzer", 2, "Poor", 0.9),
            AgentReview("patterns", 9, "Great", 0.9),
            AgentReview("knowledge-archaeologist", 5, "Okay", 0.9),
        ]

        consensus_agree = ConsensusBuilder.build_consensus(reviews_agree)
        consensus_disagree = ConsensusBuilder.build_consensus(reviews_disagree)

        # High agreement = low variance
        assert consensus_agree.score_variance < 1.0

        # High disagreement = high variance
        assert consensus_disagree.score_variance > 5.0


class TestAgentReviewErrorHandling:
    """Test error handling in agent review coordination."""

    @pytest.mark.asyncio
    async def test_handles_agent_timeout_gracefully(self):
        """Handle agent timeout without crashing."""
        coordinator = AgentReviewCoordinator(timeout=0.5)

        async def timeout_agent(*args, **kwargs):
            await asyncio.sleep(1.0)  # Exceeds timeout
            return {"importance_score": 8, "reasoning": "Good"}

        with patch("amplihack.memory.agent_review.Task", timeout_agent):
            content = "Test content"
            memory_type = MemoryType.SEMANTIC

            reviews = await coordinator.review_importance(content, memory_type)

            # Should get partial reviews (agents that completed)
            # Or handle timeout gracefully
            assert isinstance(reviews, list)

    @pytest.mark.asyncio
    async def test_handles_agent_failure_gracefully(self):
        """Handle agent failure without crashing."""
        coordinator = AgentReviewCoordinator()

        mock_task = AsyncMock()
        mock_task.side_effect = [
            {"importance_score": 8, "reasoning": "Good"},
            Exception("Agent crashed"),
            {"importance_score": 7, "reasoning": "Good"},
        ]

        with patch("amplihack.memory.agent_review.Task", mock_task):
            content = "Test content"
            memory_type = MemoryType.SEMANTIC

            reviews = await coordinator.review_importance(content, memory_type)

            # Should get 2 successful reviews
            assert len(reviews) == 2

    @pytest.mark.asyncio
    async def test_handles_malformed_agent_response(self):
        """Handle malformed agent responses."""
        coordinator = AgentReviewCoordinator()

        mock_task = AsyncMock()
        mock_task.side_effect = [
            {"importance_score": 8, "reasoning": "Good"},
            {"invalid": "response"},  # Malformed
            {"importance_score": 7, "reasoning": "Good"},
        ]

        with patch("amplihack.memory.agent_review.Task", mock_task):
            content = "Test content"
            memory_type = MemoryType.SEMANTIC

            reviews = await coordinator.review_importance(content, memory_type)

            # Should get 2 valid reviews
            assert len(reviews) == 2
            for review in reviews:
                assert hasattr(review, "importance_score")
                assert hasattr(review, "reasoning")

    @pytest.mark.asyncio
    async def test_handles_all_agents_failing(self):
        """Handle case where all agents fail."""
        coordinator = AgentReviewCoordinator()

        mock_task = AsyncMock()
        mock_task.side_effect = [
            Exception("Agent 1 failed"),
            Exception("Agent 2 failed"),
            Exception("Agent 3 failed"),
        ]

        with patch("amplihack.memory.agent_review.Task", mock_task):
            content = "Test content"
            memory_type = MemoryType.SEMANTIC

            reviews = await coordinator.review_importance(content, memory_type)

            # Should return empty list or raise appropriate error
            assert reviews == [] or isinstance(reviews, Exception)


class TestAgentReviewStatistics:
    """Test agent review statistics tracking."""

    @pytest.mark.asyncio
    async def test_tracks_review_count(self, mock_task_tool):
        """Track total number of reviews performed."""
        coordinator = AgentReviewCoordinator()

        mock_task_tool.return_value = {
            "importance_score": 8,
            "reasoning": "Good",
        }

        with patch("amplihack.memory.agent_review.Task", mock_task_tool):
            for _ in range(5):
                await coordinator.review_importance("Test", MemoryType.SEMANTIC)

            stats = coordinator.get_statistics()
            assert stats["total_reviews"] == 5

    @pytest.mark.asyncio
    async def test_tracks_average_duration(self, mock_task_tool):
        """Track average review duration."""
        coordinator = AgentReviewCoordinator()

        mock_task_tool.return_value = {
            "importance_score": 8,
            "reasoning": "Good",
        }

        with patch("amplihack.memory.agent_review.Task", mock_task_tool):
            for _ in range(3):
                await coordinator.review_importance("Test", MemoryType.SEMANTIC)

            stats = coordinator.get_statistics()
            assert "average_duration_ms" in stats
            assert stats["average_duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_tracks_consensus_distribution(self, mock_task_tool):
        """Track distribution of consensus scores."""
        coordinator = AgentReviewCoordinator()

        # Mix of high and low scores
        responses = [
            {"importance_score": 8, "reasoning": "Good"},
            {"importance_score": 2, "reasoning": "Poor"},
        ] * 3

        mock_task_tool.side_effect = responses

        with patch("amplihack.memory.agent_review.Task", mock_task_tool):
            # First review (high scores)
            await coordinator.review_importance("Good content", MemoryType.SEMANTIC)

            # Second review (low scores)
            await coordinator.review_importance("Poor content", MemoryType.SEMANTIC)

            stats = coordinator.get_statistics()
            assert "score_distribution" in stats


class TestParallelReviewer:
    """Test ParallelReviewer utility."""

    @pytest.mark.asyncio
    async def test_parallel_reviewer_invokes_all_agents(self):
        """ParallelReviewer invokes all agents concurrently."""
        reviewer = ParallelReviewer()

        async def mock_agent(name: str, content: str) -> dict[str, Any]:
            return {"importance_score": 8, "reasoning": f"{name} says good"}

        agents = ["analyzer", "patterns", "knowledge-archaeologist"]

        results = await reviewer.review_parallel(
            agents=agents,
            content="Test content",
            agent_func=mock_agent,
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_parallel_reviewer_timeout_enforcement(self):
        """ParallelReviewer enforces timeout."""
        reviewer = ParallelReviewer(timeout=0.1)

        async def slow_agent(name: str, content: str) -> dict[str, Any]:
            await asyncio.sleep(0.5)  # Exceeds timeout
            return {"importance_score": 8, "reasoning": "Good"}

        agents = ["analyzer"]

        with pytest.raises(asyncio.TimeoutError):
            await reviewer.review_parallel(
                agents=agents,
                content="Test",
                agent_func=slow_agent,
            )

    @pytest.mark.asyncio
    async def test_parallel_reviewer_partial_results_on_failure(self):
        """ParallelReviewer returns partial results on some failures."""
        reviewer = ParallelReviewer()

        async def agent_func(name: str, content: str) -> dict[str, Any]:
            if name == "patterns":
                raise Exception("Agent failed")
            return {"importance_score": 8, "reasoning": f"{name} good"}

        agents = ["analyzer", "patterns", "knowledge-archaeologist"]

        results = await reviewer.review_parallel(
            agents=agents,
            content="Test",
            agent_func=agent_func,
            fail_fast=False,
        )

        # Should get 2 successful results
        assert len([r for r in results if r is not None]) == 2
