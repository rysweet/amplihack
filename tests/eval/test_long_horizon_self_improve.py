"""Tests for long-horizon self-improvement runner.

Tests:
- Category analysis from eval reports
- Bottleneck diagnosis per category
- Runner configuration
- Integration with LongHorizonMemoryEval
"""

from __future__ import annotations

from amplihack.eval.long_horizon_memory import (
    CategoryBreakdown,
    DimensionScore,
    EvalReport,
    EvalResult,
)
from amplihack.eval.long_horizon_self_improve import (
    LongHorizonRunnerConfig,
    _analyze_categories,
    _diagnose_bottleneck,
)

# ============================================================
# Fixtures
# ============================================================


def _make_eval_result(
    qid: str,
    question: str,
    category: str,
    score: float,
    expected: str = "expected",
    actual: str = "actual",
) -> EvalResult:
    """Create a test EvalResult."""
    return EvalResult(
        question_id=qid,
        question_text=question,
        category=category,
        expected_answer=expected,
        actual_answer=actual,
        dimensions=[
            DimensionScore("factual_accuracy", score, "test"),
            DimensionScore("specificity", score, "test"),
        ],
        overall_score=score,
    )


def _make_report(results: list[EvalResult]) -> EvalReport:
    """Create a test EvalReport from results."""
    categories: dict[str, list[EvalResult]] = {}
    for r in results:
        categories.setdefault(r.category, []).append(r)

    breakdown = []
    for cat, cat_results in categories.items():
        scores = [r.overall_score for r in cat_results]
        dim_avgs: dict[str, list[float]] = {}
        for r in cat_results:
            for d in r.dimensions:
                dim_avgs.setdefault(d.dimension, []).append(d.score)

        breakdown.append(
            CategoryBreakdown(
                category=cat,
                num_questions=len(cat_results),
                avg_score=sum(scores) / len(scores),
                min_score=min(scores),
                max_score=max(scores),
                dimension_averages={k: sum(v) / len(v) for k, v in dim_avgs.items()},
            )
        )

    overall = sum(r.overall_score for r in results) / len(results) if results else 0.0

    return EvalReport(
        num_turns=100,
        num_questions=len(results),
        total_facts_delivered=100,
        learning_time_s=10.0,
        questioning_time_s=5.0,
        grading_time_s=3.0,
        overall_score=overall,
        category_breakdown=breakdown,
        results=results,
    )


# ============================================================
# Category Analysis Tests
# ============================================================


class TestCategoryAnalysis:
    """Tests for _analyze_categories."""

    def test_identifies_failing_categories(self):
        report = _make_report(
            [
                _make_eval_result("q1", "What is X?", "needle_in_haystack", 0.5),
                _make_eval_result("q2", "What is Y?", "needle_in_haystack", 0.6),
                _make_eval_result("q3", "How many?", "meta_memory", 0.3),
                _make_eval_result("q4", "When?", "temporal_evolution", 0.95),
            ]
        )

        analyses = _analyze_categories(report, threshold=0.7)

        # Should be sorted worst first
        assert analyses[0].category == "meta_memory"
        assert analyses[0].avg_score == 0.3

    def test_identifies_failed_questions(self):
        report = _make_report(
            [
                _make_eval_result("q1", "Good question", "needle_in_haystack", 0.9),
                _make_eval_result("q2", "Bad question", "needle_in_haystack", 0.3),
            ]
        )

        analyses = _analyze_categories(report, threshold=0.7)
        nih = next(a for a in analyses if a.category == "needle_in_haystack")

        assert len(nih.failed_questions) == 1
        assert nih.failed_questions[0]["question_id"] == "q2"

    def test_all_passing(self):
        report = _make_report(
            [
                _make_eval_result("q1", "Q1", "temporal_evolution", 0.95),
                _make_eval_result("q2", "Q2", "temporal_evolution", 0.90),
            ]
        )

        analyses = _analyze_categories(report, threshold=0.7)
        assert all(len(a.failed_questions) == 0 for a in analyses)

    def test_empty_report(self):
        report = _make_report([])
        analyses = _analyze_categories(report, threshold=0.7)
        assert len(analyses) == 0


# ============================================================
# Bottleneck Diagnosis Tests
# ============================================================


class TestBottleneckDiagnosis:
    """Tests for _diagnose_bottleneck."""

    def test_needle_in_haystack(self):
        bottleneck, fix = _diagnose_bottleneck(
            "needle_in_haystack",
            [{"question_text": "Q", "score": 0.3}],
            {"factual_accuracy": 0.3, "specificity": 0.5},
        )
        assert "retrieval" in bottleneck
        assert "entity" in fix.lower() or "index" in fix.lower()

    def test_meta_memory(self):
        bottleneck, fix = _diagnose_bottleneck(
            "meta_memory",
            [{"question_text": "How many?", "score": 0.2}],
            {"factual_accuracy": 0.2},
        )
        assert "aggregation" in bottleneck
        assert "cypher" in fix.lower() or "count" in fix.lower()

    def test_source_attribution(self):
        bottleneck, fix = _diagnose_bottleneck(
            "source_attribution",
            [{"question_text": "From which?", "score": 0.5}],
            {"source_attribution": 0.4, "factual_accuracy": 0.8},
        )
        assert "source" in bottleneck

    def test_temporal_evolution(self):
        bottleneck, fix = _diagnose_bottleneck(
            "temporal_evolution",
            [{"question_text": "When?", "score": 0.5}],
            {"temporal_awareness": 0.4},
        )
        assert "temporal" in bottleneck

    def test_no_failures(self):
        bottleneck, fix = _diagnose_bottleneck(
            "anything",
            [],
            {"factual_accuracy": 0.9},
        )
        assert bottleneck == ""
        assert fix == ""


# ============================================================
# Config Tests
# ============================================================


class TestRunnerConfig:
    """Tests for LongHorizonRunnerConfig."""

    def test_defaults(self):
        config = LongHorizonRunnerConfig()
        assert config.num_turns == 100
        assert config.num_questions == 20
        assert config.max_iterations == 3
        assert config.failure_threshold == 0.7
        assert not config.use_multi_agent

    def test_custom_config(self):
        config = LongHorizonRunnerConfig(
            num_turns=50,
            num_questions=10,
            max_iterations=5,
            use_multi_agent=True,
        )
        assert config.num_turns == 50
        assert config.use_multi_agent
