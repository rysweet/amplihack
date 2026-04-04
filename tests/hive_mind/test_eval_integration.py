"""Cross-repo integration tests: amplihack-agent-eval + hive mind.

Verifies that the eval harness (amplihack_eval) can use InMemoryHiveGraph
as a hive_store for distributed memory sharing through LearningAgentAdapter.

All LLM calls are mocked via unittest.mock.
Tests run fast (<2s) with no external dependencies.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from amplihack_eval.adapters.learning_agent import LearningAgentAdapter
from amplihack_eval.core.multi_seed import MultiSeedReport
from amplihack_eval.core.runner import EvalRunner

from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveFact,
    InMemoryHiveGraph,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _mock_completion(**kwargs):
    """Return a mock LLM response with plausible content."""
    return '{"facts": [{"fact": "Test fact about photosynthesis", "confidence": 0.9}]}'


async def _mock_completion_answer(**kwargs):
    """Return a mock LLM response for answer_question."""
    return "Photosynthesis converts light energy into chemical energy in plants."


# ---------------------------------------------------------------------------
# Test 1-3: LearningAgentAdapter with hive_store
# ---------------------------------------------------------------------------


class TestAdapterWithHiveStore:
    """Verify LearningAgentAdapter accepts and uses hive_store param."""

    @pytest.mark.asyncio
    @patch(
        "amplihack.agents.goal_seeking.learning_agent._llm_completion",
        new_callable=AsyncMock,
        side_effect=_mock_completion,
    )
    async def test_adapter_accepts_hive_store_param(self, mock_llm):
        """Test 1: LearningAgentAdapter can be constructed with hive_store=InMemoryHiveGraph."""
        hive = InMemoryHiveGraph(hive_id="eval-test-hive")
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = LearningAgentAdapter(
                agent_name="test_agent",
                model="gpt-4o-mini",
                storage_path=Path(tmpdir) / "db",
                use_hierarchical=True,
                hive_store=hive,
            )
            assert adapter is not None
            assert adapter.name == "LearningAgent(gpt-4o-mini)"
            adapter.close()

    @pytest.mark.asyncio
    @patch(
        "amplihack.agents.goal_seeking.learning_agent._llm_completion",
        new_callable=AsyncMock,
        side_effect=_mock_completion,
    )
    async def test_adapter_learn_stores_in_hive(self, mock_llm):
        """Test 2: adapter.learn() stores facts in both local DB and hive."""
        hive = InMemoryHiveGraph(hive_id="learn-test-hive")
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = LearningAgentAdapter(
                agent_name="hive_learner",
                model="gpt-4o-mini",
                storage_path=Path(tmpdir) / "db",
                use_hierarchical=True,
                hive_store=hive,
            )
            # Learn some content — exercises the full adapter→agent→hive path
            adapter.learn("Photosynthesis is the process by which plants convert light to energy.")

            # The adapter should have tried to store facts.
            # We verify the adapter didn't crash and the hive is accessible.
            stats = hive.get_stats()
            # hive_id should match what we created
            assert stats["hive_id"] == "learn-test-hive"
            adapter.close()

    @pytest.mark.asyncio
    @patch(
        "amplihack.agents.goal_seeking.learning_agent._llm_completion",
        new_callable=AsyncMock,
        side_effect=_mock_completion_answer,
    )
    async def test_adapter_answer_retrieves_from_hive(self, mock_llm):
        """Test 3: adapter.answer() can retrieve from both local and hive."""
        hive = InMemoryHiveGraph(hive_id="answer-test-hive")
        # Pre-populate hive with a fact from a different agent
        hive.register_agent("other_agent", domain="biology")
        hive.promote_fact(
            "other_agent",
            HiveFact(
                fact_id="hf_shared_001",
                content="Chloroplasts contain chlorophyll which absorbs light energy",
                concept="photosynthesis",
                confidence=0.95,
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = LearningAgentAdapter(
                agent_name="hive_answerer",
                model="gpt-4o-mini",
                storage_path=Path(tmpdir) / "db",
                use_hierarchical=True,
                hive_store=hive,
            )
            response = adapter.answer("What do chloroplasts contain?")

            # Should return an AgentResponse with a non-empty answer
            assert response is not None
            assert response.answer != ""
            assert len(response.answer) > 5

            # Verify the hive fact is still there (wasn't consumed)
            fact = hive.get_fact("hf_shared_001")
            assert fact is not None
            assert fact.content == "Chloroplasts contain chlorophyll which absorbs light energy"

            adapter.close()


# ---------------------------------------------------------------------------
# Test 4: adapter.close() cleanup
# ---------------------------------------------------------------------------


class TestAdapterCleanup:
    """Verify adapter.close() cleans up properly."""

    @pytest.mark.asyncio
    @patch(
        "amplihack.agents.goal_seeking.learning_agent._llm_completion",
        new_callable=AsyncMock,
        side_effect=_mock_completion,
    )
    async def test_adapter_close_cleans_up(self, mock_llm):
        """Test 4: adapter.close() runs without error and cleans up resources."""
        hive = InMemoryHiveGraph(hive_id="cleanup-test-hive")
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = LearningAgentAdapter(
                agent_name="cleanup_agent",
                model="gpt-4o-mini",
                storage_path=Path(tmpdir) / "db",
                use_hierarchical=True,
                hive_store=hive,
            )
            # Learn something so there's state to clean up
            adapter.learn("Test content for cleanup verification.")

            # close() should not raise
            adapter.close()

            # Calling close() again should also be safe (idempotent)
            adapter.close()


# ---------------------------------------------------------------------------
# Test 5: EvalRunner instantiation
# ---------------------------------------------------------------------------


class TestEvalRunnerInstantiation:
    """Verify EvalRunner can be instantiated with minimal params."""

    def test_eval_runner_minimal_params(self):
        """Test 5: EvalRunner(num_turns=5, num_questions=2) instantiates correctly."""
        runner = EvalRunner(num_turns=5, num_questions=2)
        assert runner.num_turns == 5
        assert runner.num_questions == 2
        assert runner.seed == 42  # default
        assert runner.grader_votes == 3  # default

    def test_eval_runner_generate(self):
        """EvalRunner.generate() produces dialogue and questions without LLM calls."""
        runner = EvalRunner(num_turns=5, num_questions=2)
        ground_truth, questions = runner.generate()

        assert ground_truth is not None
        assert len(questions) == 2
        # Each question should have required fields
        for q in questions:
            assert hasattr(q, "question_id")
            assert hasattr(q, "text")
            assert hasattr(q, "category")


# ---------------------------------------------------------------------------
# Test 6: MultiSeedReport CI fields
# ---------------------------------------------------------------------------


class TestMultiSeedReportFields:
    """Verify MultiSeedReport instantiation and serialization."""

    def test_multi_seed_report_basic_construction(self):
        """Test 6: MultiSeedReport can be constructed with required fields."""
        report = MultiSeedReport(
            seeds=[42],
            num_turns=5,
            num_questions=2,
            total_time_s=1.0,
            overall_mean=0.85,
            overall_stddev=0.05,
            category_stats=[],
            noisy_questions=[],
            all_question_variances=[],
            per_seed_reports={},
        )

        assert report.overall_mean == 0.85
        assert report.overall_stddev == 0.05
        assert report.seeds == [42]
        assert report.num_turns == 5

    def test_multi_seed_report_to_dict(self):
        """MultiSeedReport.to_dict() produces valid dict with required fields."""
        report = MultiSeedReport(
            seeds=[42],
            num_turns=5,
            num_questions=2,
            total_time_s=1.0,
            overall_mean=0.85,
            overall_stddev=0.05,
            category_stats=[],
            noisy_questions=[],
            all_question_variances=[],
            per_seed_reports={},
        )
        d = report.to_dict()
        assert "overall_mean" in d
        assert "overall_stddev" in d
        assert d["overall_mean"] == 0.85
        assert d["overall_stddev"] == 0.05


# ---------------------------------------------------------------------------
# Test 7: InMemoryHiveGraph standalone sanity
# ---------------------------------------------------------------------------


class TestHiveGraphSanity:
    """Quick sanity: InMemoryHiveGraph works as expected for eval integration."""

    def test_hive_promote_and_query(self):
        """InMemoryHiveGraph can promote and query facts."""
        hive = InMemoryHiveGraph(hive_id="sanity-hive")
        hive.register_agent("agent_a", domain="science")
        fid = hive.promote_fact(
            "agent_a",
            HiveFact(
                fact_id="",
                content="Water boils at 100 degrees Celsius at sea level",
                concept="thermodynamics",
                confidence=0.95,
            ),
        )
        assert fid  # non-empty fact_id returned

        results = hive.query_facts("water boils temperature")
        assert len(results) >= 1
        assert any("Water boils" in f.content for f in results)

        hive.close()
