"""Tests for the teaching evaluation layer."""

from __future__ import annotations

from amplihack.agents.domain_agents.code_review.agent import CodeReviewAgent
from amplihack.agents.domain_agents.meeting_synthesizer.agent import MeetingSynthesizerAgent
from amplihack.eval.teaching_eval import (
    DomainTeachingEvalResult,
    DomainTeachingEvaluator,
    run_combined_eval,
)


class TestDomainTeachingEvaluatorCodeReview:
    """Test teaching evaluation with CodeReviewAgent."""

    def test_evaluate_security_teaching(self):
        agent = CodeReviewAgent("test_reviewer")
        evaluator = DomainTeachingEvaluator(agent)
        result = evaluator.evaluate("security review")

        assert isinstance(result, DomainTeachingEvalResult)
        assert result.agent_name == "test_reviewer"
        assert result.domain == "code_review"
        assert result.topic == "security review"
        assert 0.0 <= result.composite_score <= 1.0

    def test_evaluate_style_teaching(self):
        agent = CodeReviewAgent("test_reviewer")
        evaluator = DomainTeachingEvaluator(agent)
        result = evaluator.evaluate("style review")

        assert result.composite_score > 0.0

    def test_dimension_scores(self):
        agent = CodeReviewAgent("test_reviewer")
        evaluator = DomainTeachingEvaluator(agent)
        result = evaluator.evaluate("security review")

        assert len(result.dimension_scores) == 4
        dimensions = {d.dimension for d in result.dimension_scores}
        assert dimensions == {"clarity", "completeness", "student_performance", "adaptivity"}

        for dim in result.dimension_scores:
            assert 0.0 <= dim.score <= 1.0
            assert dim.weight > 0
            assert dim.details

    def test_weights_sum_to_one(self):
        evaluator = DomainTeachingEvaluator(CodeReviewAgent("test"))
        total_weight = sum(evaluator.WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.001

    def test_composite_is_weighted_sum(self):
        agent = CodeReviewAgent("test_reviewer")
        evaluator = DomainTeachingEvaluator(agent)
        result = evaluator.evaluate("security review")

        expected = sum(d.score * d.weight for d in result.dimension_scores)
        assert abs(result.composite_score - expected) < 0.001

    def test_to_dict(self):
        agent = CodeReviewAgent("test_reviewer")
        evaluator = DomainTeachingEvaluator(agent)
        result = evaluator.evaluate("security review")

        d = result.to_dict()
        assert d["agent_name"] == "test_reviewer"
        assert d["domain"] == "code_review"
        assert "composite_score" in d
        assert "dimensions" in d
        assert len(d["dimensions"]) == 4


class TestDomainTeachingEvaluatorMeeting:
    """Test teaching evaluation with MeetingSynthesizerAgent."""

    def test_evaluate_teaching(self):
        agent = MeetingSynthesizerAgent("test_synth")
        evaluator = DomainTeachingEvaluator(agent)
        result = evaluator.evaluate("action item extraction")

        assert isinstance(result, DomainTeachingEvalResult)
        assert result.domain == "meeting_synthesizer"
        assert result.composite_score > 0.0

    def test_teaching_result_present(self):
        agent = MeetingSynthesizerAgent("test_synth")
        evaluator = DomainTeachingEvaluator(agent)
        result = evaluator.evaluate("meeting summarization")

        assert result.teaching_result is not None
        assert result.teaching_result.lesson_plan
        assert result.teaching_result.instruction
        assert result.teaching_result.student_attempt


class TestRunCombinedEval:
    """Test the combined domain + teaching evaluation."""

    def test_combined_eval_code_review(self):
        agent = CodeReviewAgent("test_reviewer")
        result = run_combined_eval(agent, "security review")

        assert result["agent_name"] == "test_reviewer"
        assert result["domain"] == "code_review"
        assert 0.0 <= result["domain_score"] <= 1.0
        assert 0.0 <= result["teaching_score"] <= 1.0
        assert 0.0 <= result["combined_score"] <= 1.0
        assert result["domain_weight"] == 0.6
        assert result["teaching_weight"] == 0.4

    def test_combined_eval_meeting_synth(self):
        agent = MeetingSynthesizerAgent("test_synth")
        result = run_combined_eval(agent, "action item extraction")

        assert result["domain"] == "meeting_synthesizer"
        assert result["combined_score"] > 0.0

    def test_combined_score_formula(self):
        agent = CodeReviewAgent("test_reviewer")
        result = run_combined_eval(agent, "quality review", domain_weight=0.7, teaching_weight=0.3)

        expected = result["domain_score"] * 0.7 + result["teaching_score"] * 0.3
        assert abs(result["combined_score"] - round(expected, 3)) < 0.01

    def test_custom_weights(self):
        agent = CodeReviewAgent("test_reviewer")
        result = run_combined_eval(agent, "security", domain_weight=0.5, teaching_weight=0.5)
        assert result["domain_weight"] == 0.5
        assert result["teaching_weight"] == 0.5

    def test_details_present(self):
        agent = CodeReviewAgent("test_reviewer")
        result = run_combined_eval(agent, "security review")

        assert "domain_details" in result
        assert "teaching_details" in result
        assert "levels" in result["domain_details"]
        assert "dimensions" in result["teaching_details"]
