"""Tests for long-horizon grading improvements.

Tests deterministic grading with rubrics, hybrid grading,
multi-vote median calculation, rubric generation, and --sdk parameter parsing.
"""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from amplihack.eval.long_horizon_data import (
    GradingRubric,
    Question,
    generate_dialogue,
    generate_questions,
)
from amplihack.eval.long_horizon_memory import (
    DimensionScore,
    LongHorizonMemoryEval,
    _deterministic_grade,
    _grade_hybrid,
    _grade_multi_vote,
)


# ============================================================
# Test GradingRubric dataclass
# ============================================================


class TestGradingRubric:
    """Tests for the GradingRubric dataclass."""

    def test_default_rubric_fields(self):
        """Default rubric has empty lists and dict."""
        rubric = GradingRubric()
        assert rubric.required_keywords == []
        assert rubric.acceptable_paraphrases == []
        assert rubric.incorrect_patterns == []
        assert rubric.dimension_weights == {}

    def test_rubric_with_keywords(self):
        """Rubric stores required keywords."""
        rubric = GradingRubric(
            required_keywords=["Sarah", "Chen", "March"],
            acceptable_paraphrases=["birthday"],
            incorrect_patterns=["April"],
        )
        assert len(rubric.required_keywords) == 3
        assert "Sarah" in rubric.required_keywords
        assert "April" in rubric.incorrect_patterns

    def test_rubric_with_dimension_weights(self):
        """Rubric stores dimension weight overrides."""
        rubric = GradingRubric(
            dimension_weights={"factual_accuracy": 2.0, "specificity": 0.5}
        )
        assert rubric.dimension_weights["factual_accuracy"] == 2.0


# ============================================================
# Test deterministic grading
# ============================================================


class TestDeterministicGrading:
    """Tests for _deterministic_grade() with rubric-based scoring."""

    def test_all_keywords_match(self):
        """Score 1.0 when all keywords present."""
        rubric = GradingRubric(required_keywords=["March", "15"])
        scores = _deterministic_grade(rubric, "March 15", ["factual_accuracy"])
        assert "factual_accuracy" in scores
        assert scores["factual_accuracy"].score == 1.0

    def test_partial_keyword_match(self):
        """Score proportional to matched keywords."""
        rubric = GradingRubric(required_keywords=["March", "15", "birthday"])
        scores = _deterministic_grade(rubric, "March 15", ["factual_accuracy"])
        assert scores["factual_accuracy"].score == pytest.approx(2 / 3, abs=0.01)

    def test_no_keywords_match(self):
        """Score 0.0 when no keywords match."""
        rubric = GradingRubric(required_keywords=["March", "15"])
        scores = _deterministic_grade(rubric, "July 22", ["factual_accuracy"])
        assert scores["factual_accuracy"].score == 0.0

    def test_case_insensitive_matching(self):
        """Keywords match case-insensitively."""
        rubric = GradingRubric(required_keywords=["MARCH", "15"])
        scores = _deterministic_grade(rubric, "march 15th", ["factual_accuracy"])
        assert scores["factual_accuracy"].score == 1.0

    def test_incorrect_pattern_overrides(self):
        """Score 0.0 when incorrect pattern found, even with keyword matches."""
        rubric = GradingRubric(
            required_keywords=["September", "20"],
            incorrect_patterns=["June 15"],
        )
        scores = _deterministic_grade(
            rubric,
            "The deadline is September 20 (originally June 15)",
            ["factual_accuracy"],
        )
        assert scores["factual_accuracy"].score == 0.0
        assert "incorrect pattern" in scores["factual_accuracy"].reasoning.lower()

    def test_paraphrase_bonus(self):
        """Paraphrase matches add bonus to score."""
        rubric = GradingRubric(
            required_keywords=["Statistics", "MIT"],
            acceptable_paraphrases=["doctorate", "Ph.D."],
        )
        scores = _deterministic_grade(
            rubric,
            "She has a Ph.D. in Statistics from MIT",
            ["factual_accuracy"],
        )
        # 2/2 keywords + 0.1 bonus for 1 paraphrase = 1.0 (capped)
        assert scores["factual_accuracy"].score == 1.0

    def test_only_deterministic_dimensions_scored(self):
        """Only factual_accuracy and specificity are scored deterministically."""
        rubric = GradingRubric(required_keywords=["test"])
        scores = _deterministic_grade(
            rubric,
            "test answer",
            ["factual_accuracy", "temporal_awareness", "source_attribution"],
        )
        assert "factual_accuracy" in scores
        assert "temporal_awareness" not in scores
        assert "source_attribution" not in scores

    def test_specificity_dimension(self):
        """Specificity can be scored deterministically."""
        rubric = GradingRubric(required_keywords=["$450K", "migration"])
        scores = _deterministic_grade(
            rubric,
            "The migration cost was $450K",
            ["specificity"],
        )
        assert "specificity" in scores
        assert scores["specificity"].score == 1.0

    def test_empty_keywords_neutral_score(self):
        """Empty keywords list gives neutral 0.5 score."""
        rubric = GradingRubric(required_keywords=[])
        scores = _deterministic_grade(rubric, "any answer", ["factual_accuracy"])
        assert scores["factual_accuracy"].score == 0.5

    def test_reasoning_includes_match_count(self):
        """Reasoning shows how many keywords matched."""
        rubric = GradingRubric(required_keywords=["March", "15", "birthday"])
        scores = _deterministic_grade(rubric, "March 15", ["factual_accuracy"])
        assert "2/3" in scores["factual_accuracy"].reasoning


# ============================================================
# Test hybrid grading
# ============================================================


class TestHybridGrading:
    """Tests for _grade_hybrid() combining deterministic + LLM."""

    def test_no_rubric_falls_through_to_llm(self):
        """Without rubric, all dimensions go to LLM."""
        question = Question(
            question_id="test_01",
            text="What is X?",
            expected_answer="Y",
            category="test",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=None,
        )
        with patch("amplihack.eval.long_horizon_memory._grade_with_llm") as mock_llm:
            mock_llm.return_value = [DimensionScore("factual_accuracy", 0.9, "LLM")]
            scores = _grade_hybrid(question, "Y", ["factual_accuracy"])
            mock_llm.assert_called_once()
            assert scores[0].score == 0.9

    def test_rubric_deterministic_skips_llm_for_factual(self):
        """With rubric, factual_accuracy is scored deterministically."""
        question = Question(
            question_id="test_02",
            text="What is Sarah's birthday?",
            expected_answer="March 15",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=GradingRubric(required_keywords=["March", "15"]),
        )
        with patch("amplihack.eval.long_horizon_memory._grade_with_llm") as mock_llm:
            scores = _grade_hybrid(question, "March 15", ["factual_accuracy"])
            mock_llm.assert_not_called()
            assert scores[0].score == 1.0
            assert scores[0].dimension == "factual_accuracy"

    def test_hybrid_splits_dimensions(self):
        """Hybrid sends only non-deterministic dimensions to LLM."""
        question = Question(
            question_id="test_03",
            text="What is the current deadline?",
            expected_answer="September 20",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            rubric=GradingRubric(required_keywords=["September", "20"]),
        )
        with patch("amplihack.eval.long_horizon_memory._grade_with_llm") as mock_llm:
            mock_llm.return_value = [DimensionScore("temporal_awareness", 0.8, "LLM")]
            scores = _grade_hybrid(
                question,
                "September 20",
                ["factual_accuracy", "temporal_awareness"],
            )
            # LLM should only be called for temporal_awareness
            call_args = mock_llm.call_args
            assert call_args[0][2] == ["temporal_awareness"]
            # factual_accuracy should be 1.0 (deterministic)
            assert scores[0].dimension == "factual_accuracy"
            assert scores[0].score == 1.0
            # temporal_awareness should be 0.8 (LLM)
            assert scores[1].dimension == "temporal_awareness"
            assert scores[1].score == 0.8

    def test_dimension_weights_applied(self):
        """Rubric dimension_weights scale the final scores."""
        question = Question(
            question_id="test_04",
            text="Test?",
            expected_answer="Answer",
            category="test",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=GradingRubric(
                required_keywords=["Answer"],
                dimension_weights={"factual_accuracy": 0.5},
            ),
        )
        scores = _grade_hybrid(question, "Answer", ["factual_accuracy"])
        # 1.0 * 0.5 weight = 0.5
        assert scores[0].score == 0.5


# ============================================================
# Test multi-vote grading
# ============================================================


class TestMultiVoteGrading:
    """Tests for _grade_multi_vote() median calculation."""

    def test_single_vote_no_overhead(self):
        """num_votes=1 calls _grade_hybrid once."""
        question = Question(
            question_id="mv_01",
            text="Test?",
            expected_answer="Answer",
            category="test",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=GradingRubric(required_keywords=["Answer"]),
        )
        scores = _grade_multi_vote(question, "Answer", ["factual_accuracy"], num_votes=1)
        assert len(scores) == 1
        assert scores[0].score == 1.0

    def test_multi_vote_deterministic_stable(self):
        """Deterministic grading gives same score every vote -> median is same."""
        question = Question(
            question_id="mv_02",
            text="Birthday?",
            expected_answer="March 15",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=GradingRubric(required_keywords=["March", "15"]),
        )
        scores = _grade_multi_vote(question, "March 15", ["factual_accuracy"], num_votes=5)
        assert scores[0].score == 1.0
        assert "median of 5 votes" in scores[0].reasoning

    def test_multi_vote_median_calculation(self):
        """Multi-vote takes the median of LLM scores."""
        question = Question(
            question_id="mv_03",
            text="Who leads now?",
            expected_answer="Amara Okafor",
            category="temporal",
            relevant_turns=[],
            scoring_dimensions=["temporal_awareness"],
            rubric=GradingRubric(required_keywords=["Amara"]),
        )
        # Mock LLM to return different scores
        llm_scores = [
            [DimensionScore("temporal_awareness", 0.6, "vote1")],
            [DimensionScore("temporal_awareness", 0.8, "vote2")],
            [DimensionScore("temporal_awareness", 0.9, "vote3")],
        ]
        with patch("amplihack.eval.long_horizon_memory._grade_with_llm") as mock_llm:
            mock_llm.side_effect = llm_scores
            scores = _grade_multi_vote(
                question,
                "Amara Okafor leads now",
                ["temporal_awareness"],
                num_votes=3,
            )
            assert scores[0].score == 0.8  # median of 0.6, 0.8, 0.9
            assert mock_llm.call_count == 3

    def test_multi_vote_preserves_dimension_order(self):
        """Multi-vote returns scores in the same order as requested dimensions."""
        question = Question(
            question_id="mv_04",
            text="Test?",
            expected_answer="Test",
            category="test",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=GradingRubric(required_keywords=["Test"]),
        )
        scores = _grade_multi_vote(
            question,
            "Test",
            ["factual_accuracy", "specificity"],
            num_votes=3,
        )
        assert len(scores) == 2
        assert scores[0].dimension == "factual_accuracy"
        assert scores[1].dimension == "specificity"


# ============================================================
# Test rubric generation for different question types
# ============================================================


class TestRubricGeneration:
    """Tests that generated questions include appropriate rubrics."""

    def test_all_questions_have_rubrics(self):
        """Every generated question has a non-None rubric."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        questions = generate_questions(gt, num_questions=100)
        for q in questions:
            assert q.rubric is not None, f"Question {q.question_id} missing rubric"

    def test_numerical_questions_have_number_keywords(self):
        """Numerical precision questions have numeric keywords in rubric."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        questions = generate_questions(gt, num_questions=100)
        numerical = [q for q in questions if q.category == "numerical_precision"]
        assert len(numerical) > 0
        for q in numerical:
            assert q.rubric is not None
            has_number = any(
                any(c.isdigit() for c in kw) for kw in q.rubric.required_keywords
            )
            assert has_number, (
                f"Numerical question {q.question_id} should have numeric keywords, "
                f"got: {q.rubric.required_keywords}"
            )

    def test_needle_questions_have_exact_keywords(self):
        """Needle-in-haystack questions have exact answer keywords."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        questions = generate_questions(gt, num_questions=100)
        needles = [q for q in questions if q.category == "needle_in_haystack"]
        assert len(needles) > 0
        for q in needles:
            assert q.rubric is not None
            assert len(q.rubric.required_keywords) >= 1, (
                f"Needle question {q.question_id} needs at least 1 keyword"
            )

    def test_temporal_questions_may_have_incorrect_patterns(self):
        """Some temporal questions have incorrect_patterns to catch stale answers."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        questions = generate_questions(gt, num_questions=100)
        temporal = [q for q in questions if q.category == "temporal_evolution"]
        has_incorrect = any(
            q.rubric and q.rubric.incorrect_patterns for q in temporal
        )
        assert has_incorrect, "At least one temporal question should have incorrect_patterns"

    def test_source_questions_have_multiple_keywords(self):
        """Source attribution questions have keywords for multiple sources."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        questions = generate_questions(gt, num_questions=100)
        source = [q for q in questions if q.category == "source_attribution"]
        assert len(source) > 0
        for q in source:
            assert q.rubric is not None
            assert len(q.rubric.required_keywords) >= 2, (
                f"Source question {q.question_id} should have keywords for multiple sources"
            )


# ============================================================
# Test --sdk parameter parsing
# ============================================================


class TestSDKParameter:
    """Tests for --sdk CLI argument parsing."""

    def test_sdk_default_is_mini(self):
        """Default --sdk value is 'mini'."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--sdk",
            type=str,
            default="mini",
            choices=["mini", "claude", "copilot", "microsoft"],
        )
        args = parser.parse_args([])
        assert args.sdk == "mini"

    def test_sdk_claude_accepted(self):
        """--sdk claude is a valid choice."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--sdk",
            type=str,
            default="mini",
            choices=["mini", "claude", "copilot", "microsoft"],
        )
        args = parser.parse_args(["--sdk", "claude"])
        assert args.sdk == "claude"

    def test_sdk_copilot_accepted(self):
        """--sdk copilot is a valid choice."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--sdk",
            type=str,
            default="mini",
            choices=["mini", "claude", "copilot", "microsoft"],
        )
        args = parser.parse_args(["--sdk", "copilot"])
        assert args.sdk == "copilot"

    def test_sdk_microsoft_accepted(self):
        """--sdk microsoft is a valid choice."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--sdk",
            type=str,
            default="mini",
            choices=["mini", "claude", "copilot", "microsoft"],
        )
        args = parser.parse_args(["--sdk", "microsoft"])
        assert args.sdk == "microsoft"

    def test_sdk_invalid_rejected(self):
        """Invalid --sdk value raises SystemExit."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--sdk",
            type=str,
            default="mini",
            choices=["mini", "claude", "copilot", "microsoft"],
        )
        with pytest.raises(SystemExit):
            parser.parse_args(["--sdk", "invalid"])


# ============================================================
# Test LongHorizonMemoryEval grader_votes parameter
# ============================================================


class TestEvalGraderVotes:
    """Tests for the grader_votes parameter on LongHorizonMemoryEval."""

    def test_default_grader_votes(self):
        """Default grader_votes is 3."""
        evaluator = LongHorizonMemoryEval(num_turns=50, num_questions=5)
        assert evaluator.grader_votes == 3

    def test_custom_grader_votes(self):
        """Custom grader_votes is stored."""
        evaluator = LongHorizonMemoryEval(num_turns=50, num_questions=5, grader_votes=7)
        assert evaluator.grader_votes == 7

    def test_minimum_grader_votes_is_1(self):
        """grader_votes cannot go below 1."""
        evaluator = LongHorizonMemoryEval(num_turns=50, num_questions=5, grader_votes=0)
        assert evaluator.grader_votes == 1

    @patch("amplihack.eval.long_horizon_memory._grade_multi_vote")
    def test_evaluate_passes_grader_votes(self, mock_grade):
        """evaluate() passes grader_votes to _grade_multi_vote."""
        mock_grade.return_value = [DimensionScore("factual_accuracy", 0.8, "OK")]

        evaluator = LongHorizonMemoryEval(
            num_turns=50, num_questions=3, grader_votes=5
        )
        evaluator.generate()

        agent = MagicMock()
        agent.answer_question.return_value = "Test answer"
        agent.get_memory_stats.return_value = {}

        evaluator.evaluate(agent)

        # Check that grader_votes=5 was passed
        for call in mock_grade.call_args_list:
            assert call.kwargs.get("num_votes") == 5 or call[1].get("num_votes") == 5


# ============================================================
# Test multi-seed report structures
# ============================================================


class TestMultiSeedStructures:
    """Tests for multi-seed data structures (no actual evaluation)."""

    def test_question_variance_creation(self):
        """QuestionVariance dataclass works correctly."""
        from amplihack.eval.long_horizon_multi_seed import QuestionVariance

        qv = QuestionVariance(
            question_id="test_01",
            question_text="What is X?",
            category="test",
            scores_by_seed={42: 0.8, 123: 0.6, 456: 0.9},
            mean_score=0.767,
            stddev=0.153,
            is_noisy=True,
        )
        assert qv.is_noisy is True
        assert len(qv.scores_by_seed) == 3

    def test_category_stats_creation(self):
        """CategoryStats dataclass works correctly."""
        from amplihack.eval.long_horizon_multi_seed import CategoryStats

        cs = CategoryStats(
            category="needle_in_haystack",
            mean_score=0.85,
            stddev=0.05,
            min_score=0.78,
            max_score=0.92,
            scores_by_seed={42: 0.85, 123: 0.78, 456: 0.92},
        )
        assert cs.mean_score == 0.85

    def test_safe_stddev_single_value(self):
        """_safe_stddev returns 0 for single value."""
        from amplihack.eval.long_horizon_multi_seed import _safe_stddev

        assert _safe_stddev([0.5]) == 0.0

    def test_safe_stddev_empty(self):
        """_safe_stddev returns 0 for empty list."""
        from amplihack.eval.long_horizon_multi_seed import _safe_stddev

        assert _safe_stddev([]) == 0.0

    def test_safe_stddev_multiple(self):
        """_safe_stddev computes correct sample stddev."""
        from amplihack.eval.long_horizon_multi_seed import _safe_stddev

        # stddev of [0.8, 0.8, 0.8] ~= 0.0 (fp precision)
        assert _safe_stddev([0.8, 0.8, 0.8]) == pytest.approx(0.0, abs=1e-10)

        # stddev of [0.6, 0.8, 1.0] should be ~0.2
        result = _safe_stddev([0.6, 0.8, 1.0])
        assert 0.19 < result < 0.21

    def test_multi_seed_report_to_dict(self):
        """MultiSeedReport.to_dict() is JSON-serializable."""
        import json

        from amplihack.eval.long_horizon_multi_seed import (
            CategoryStats,
            MultiSeedReport,
        )

        report = MultiSeedReport(
            seeds=[42, 123],
            num_turns=100,
            num_questions=20,
            total_time_s=120.0,
            overall_mean=0.75,
            overall_stddev=0.05,
            category_stats=[
                CategoryStats(
                    category="test",
                    mean_score=0.75,
                    stddev=0.05,
                    min_score=0.70,
                    max_score=0.80,
                    scores_by_seed={42: 0.70, 123: 0.80},
                )
            ],
            noisy_questions=[],
            all_question_variances=[],
            per_seed_reports={},
        )
        d = report.to_dict()
        json_str = json.dumps(d)
        assert json_str
        assert d["overall_mean"] == 0.75
        assert d["num_noisy_questions"] == 0
