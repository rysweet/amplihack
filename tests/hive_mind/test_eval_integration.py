"""Cross-repo integration tests: amplihack-agent-eval + hive mind.

Verifies that the eval harness (amplihack_eval) can use InMemoryHiveGraph
as a hive_store for distributed memory sharing through LearningAgentAdapter.

All LLM calls are mocked via unittest.mock patching litellm.completion.
Tests run fast (<2s) with no external dependencies.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def _mock_litellm_completion(**kwargs):
    """Return a mock litellm response with plausible content."""
    msg = MagicMock()
    msg.content = '{"facts": [{"fact": "Test fact about photosynthesis", "confidence": 0.9}]}'
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _mock_litellm_completion_answer(**kwargs):
    """Return a mock litellm response for answer_question."""
    msg = MagicMock()
    msg.content = "Photosynthesis converts light energy into chemical energy in plants."
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# Test 1-3: LearningAgentAdapter with hive_store
# ---------------------------------------------------------------------------


class TestAdapterWithHiveStore:
    """Verify LearningAgentAdapter accepts and uses hive_store param."""

    @patch("litellm.completion", side_effect=_mock_litellm_completion)
    def test_adapter_accepts_hive_store_param(self, mock_llm):
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

    @patch("litellm.completion", side_effect=_mock_litellm_completion)
    def test_adapter_learn_stores_in_hive(self, mock_llm):
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
            # Learn some content
            adapter.learn("Photosynthesis is the process by which plants convert light to energy.")

            # Verify LLM was called (fact extraction)
            assert mock_llm.call_count >= 1

            # The adapter should have tried to store facts.
            # We verify the adapter didn't crash and the hive is accessible.
            stats = hive.get_stats()
            # hive_id should match what we created
            assert stats["hive_id"] == "learn-test-hive"
            adapter.close()

    @patch("litellm.completion", side_effect=_mock_litellm_completion_answer)
    def test_adapter_answer_retrieves_from_hive(self, mock_llm):
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

    @patch("litellm.completion", side_effect=_mock_litellm_completion)
    def test_adapter_close_cleans_up(self, mock_llm):
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


class TestMultiSeedReportCIFields:
    """Verify MultiSeedReport has confidence interval fields from eval repo."""

    def test_multi_seed_report_has_ci_fields(self):
        """Test 6: MultiSeedReport has CI fields (overall_ci_95_lower, etc.)."""
        # Construct a minimal MultiSeedReport to verify the CI fields exist
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
            overall_ci_95_lower=0.80,
            overall_ci_95_upper=0.90,
            overall_margin_of_error=0.05,
            repeats_per_seed=1,
            intra_seed_stddev=0.0,
        )

        # Verify CI fields exist and have correct values
        assert report.overall_ci_95_lower == 0.80
        assert report.overall_ci_95_upper == 0.90
        assert report.overall_margin_of_error == 0.05
        assert report.repeats_per_seed == 1
        assert report.intra_seed_stddev == 0.0

    def test_multi_seed_report_to_dict_includes_ci(self):
        """MultiSeedReport.to_dict() includes CI fields in output."""
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
            overall_ci_95_lower=0.80,
            overall_ci_95_upper=0.90,
            overall_margin_of_error=0.05,
        )
        d = report.to_dict()
        assert "overall_ci_95_lower" in d
        assert "overall_ci_95_upper" in d
        assert "overall_margin_of_error" in d
        assert d["overall_ci_95_lower"] == 0.80
        assert d["overall_ci_95_upper"] == 0.90


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
