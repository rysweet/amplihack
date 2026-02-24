"""Tests for the metacognition grader with 4-dimension scoring."""

from unittest.mock import MagicMock, patch

import pytest

from amplihack.eval.metacognition_grader import (
    Dimension,
    MetacognitionGrader,
    MetacognitionScore,
)


def _mock_llm_response(text: str) -> MagicMock:
    """Create a mock litellm response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = text
    return mock_response


class TestDimension:
    """Tests for Dimension dataclass."""

    def test_dimension_creation(self):
        dim = Dimension(
            name="factual_accuracy",
            score=0.85,
            reasoning="Most facts were correct.",
        )
        assert dim.name == "factual_accuracy"
        assert dim.score == 0.85
        assert dim.reasoning == "Most facts were correct."

    def test_dimension_score_bounds(self):
        dim = Dimension(name="test", score=0.0, reasoning="Low")
        assert dim.score == 0.0

        dim = Dimension(name="test", score=1.0, reasoning="High")
        assert dim.score == 1.0


class TestMetacognitionScore:
    """Tests for MetacognitionScore dataclass."""

    def test_score_creation(self):
        dimensions = [
            Dimension(name="factual_accuracy", score=0.9, reasoning="Good"),
            Dimension(name="self_awareness", score=0.8, reasoning="Fair"),
            Dimension(name="knowledge_boundaries", score=0.7, reasoning="OK"),
            Dimension(name="explanation_quality", score=0.85, reasoning="Solid"),
        ]
        score = MetacognitionScore(
            dimensions=dimensions,
            overall_score=0.8125,
            summary="Student demonstrated good metacognition.",
        )
        assert len(score.dimensions) == 4
        assert score.overall_score == 0.8125
        assert "metacognition" in score.summary.lower()

    def test_overall_score_is_average_of_dimensions(self):
        dimensions = [
            Dimension(name="d1", score=0.8, reasoning=""),
            Dimension(name="d2", score=0.6, reasoning=""),
            Dimension(name="d3", score=1.0, reasoning=""),
            Dimension(name="d4", score=0.4, reasoning=""),
        ]
        expected_avg = (0.8 + 0.6 + 1.0 + 0.4) / 4
        score = MetacognitionScore(
            dimensions=dimensions,
            overall_score=expected_avg,
            summary="Test",
        )
        assert score.overall_score == pytest.approx(0.7, abs=0.001)


class TestMetacognitionGrader:
    """Tests for the MetacognitionGrader."""

    def test_grader_initialization(self):
        grader = MetacognitionGrader()
        assert grader.model is not None

    def test_grader_custom_model(self):
        grader = MetacognitionGrader(model="gpt-4")
        assert grader.model == "gpt-4"

    @patch("litellm.completion")
    def test_grade_produces_4_dimensions(self, mock_completion):
        """Grading produces exactly 4 metacognition dimensions."""
        mock_completion.return_value = _mock_llm_response(
            '{"factual_accuracy": {"score": 0.9, "reasoning": "Good recall"}, '
            '"self_awareness": {"score": 0.8, "reasoning": "Knows limits"}, '
            '"knowledge_boundaries": {"score": 0.7, "reasoning": "Some gaps"}, '
            '"explanation_quality": {"score": 0.85, "reasoning": "Clear explanations"}}'
        )

        grader = MetacognitionGrader()
        score = grader.grade(
            question="What does L1 evaluate?",
            expected_answer="L1 evaluates direct recall of facts from a single source.",
            student_answer="L1 tests recall of facts.",
            self_explanation="I know this because recall means remembering directly.",
        )

        assert isinstance(score, MetacognitionScore)
        assert len(score.dimensions) == 4
        dimension_names = {d.name for d in score.dimensions}
        assert "factual_accuracy" in dimension_names
        assert "self_awareness" in dimension_names
        assert "knowledge_boundaries" in dimension_names
        assert "explanation_quality" in dimension_names

    @patch("litellm.completion")
    def test_grade_computes_overall_score(self, mock_completion):
        """Overall score is mean of all dimensions."""
        mock_completion.return_value = _mock_llm_response(
            '{"factual_accuracy": {"score": 0.8, "reasoning": "Good"}, '
            '"self_awareness": {"score": 0.6, "reasoning": "Fair"}, '
            '"knowledge_boundaries": {"score": 1.0, "reasoning": "Excellent"}, '
            '"explanation_quality": {"score": 0.4, "reasoning": "Poor"}}'
        )

        grader = MetacognitionGrader()
        score = grader.grade(
            question="Test?",
            expected_answer="Expected",
            student_answer="Actual",
            self_explanation="Because reasons",
        )

        expected_overall = (0.8 + 0.6 + 1.0 + 0.4) / 4
        assert score.overall_score == pytest.approx(expected_overall, abs=0.001)

    @patch("litellm.completion")
    def test_grade_handles_empty_self_explanation(self, mock_completion):
        """Grader handles student with no self-explanation."""
        mock_completion.return_value = _mock_llm_response(
            '{"factual_accuracy": {"score": 0.5, "reasoning": "Partial"}, '
            '"self_awareness": {"score": 0.1, "reasoning": "No self-reflection"}, '
            '"knowledge_boundaries": {"score": 0.2, "reasoning": "Unclear"}, '
            '"explanation_quality": {"score": 0.0, "reasoning": "No explanation given"}}'
        )

        grader = MetacognitionGrader()
        score = grader.grade(
            question="What is L2?",
            expected_answer="L2 tests inference.",
            student_answer="I think L2 is something.",
            self_explanation="",
        )

        assert score.overall_score < 0.5  # Should be low without explanation

    @patch("litellm.completion")
    def test_grade_handles_llm_error(self, mock_completion):
        """Grader returns zero scores on LLM error."""
        mock_completion.side_effect = Exception("API Error")

        grader = MetacognitionGrader()
        score = grader.grade(
            question="Test?",
            expected_answer="Expected",
            student_answer="Actual",
            self_explanation="Explanation",
        )

        assert score.overall_score == 0.0
        assert len(score.dimensions) == 4
        assert all(d.score == 0.0 for d in score.dimensions)

    @patch("litellm.completion")
    def test_batch_grade(self, mock_completion):
        """Batch grading scores multiple question-answer pairs."""
        mock_completion.return_value = _mock_llm_response(
            '{"factual_accuracy": {"score": 0.9, "reasoning": "Good"}, '
            '"self_awareness": {"score": 0.8, "reasoning": "Good"}, '
            '"knowledge_boundaries": {"score": 0.7, "reasoning": "Good"}, '
            '"explanation_quality": {"score": 0.85, "reasoning": "Good"}}'
        )

        grader = MetacognitionGrader()
        items = [
            {
                "question": "What is L1?",
                "expected": "Recall",
                "actual": "Recall of facts",
                "explanation": "Direct recall",
            },
            {
                "question": "What is L2?",
                "expected": "Inference",
                "actual": "Reasoning from facts",
                "explanation": "Connecting facts",
            },
        ]

        scores = grader.batch_grade(items)
        assert len(scores) == 2
        assert all(isinstance(s, MetacognitionScore) for s in scores)
