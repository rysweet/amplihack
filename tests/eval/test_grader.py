"""Tests for semantic grader."""

from unittest.mock import MagicMock, patch

import pytest

from amplihack.eval.grader import GradeResult, grade_answer


def test_grade_answer_perfect_match():
    """Test grading when answer matches expected perfectly."""
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value.content = [
            MagicMock(text='{"score": 1.0, "reasoning": "Perfect match"}')
        ]

        result = grade_answer(
            question="What was announced?",
            expected="GPT-5 was released",
            actual="GPT-5 was released",
            level="L1",
        )

        assert isinstance(result, GradeResult)
        assert result.score == 1.0
        assert "Perfect" in result.reasoning


def test_grade_answer_partial_match():
    """Test grading when answer is partially correct."""
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value.content = [
            MagicMock(text='{"score": 0.7, "reasoning": "Main point correct, missing details"}')
        ]

        result = grade_answer(
            question="What was announced?",
            expected="GPT-5 was released on February 15",
            actual="GPT-5 was released",
            level="L1",
        )

        assert 0.6 <= result.score <= 0.8
        assert "missing" in result.reasoning.lower() or "correct" in result.reasoning.lower()


def test_grade_answer_semantic_equivalence():
    """Test grading recognizes semantic equivalence."""
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value.content = [
            MagicMock(text='{"score": 0.95, "reasoning": "Semantically equivalent"}')
        ]

        result = grade_answer(
            question="What happened?",
            expected="The company launched a new product",
            actual="A new product was introduced by the company",
            level="L1",
        )

        assert result.score >= 0.9
        assert "semantic" in result.reasoning.lower() or "equivalent" in result.reasoning.lower()


def test_grade_answer_incorrect():
    """Test grading when answer is incorrect."""
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value.content = [
            MagicMock(text='{"score": 0.1, "reasoning": "Answer is factually incorrect"}')
        ]

        result = grade_answer(
            question="What was announced?",
            expected="GPT-5 was released",
            actual="GPT-4 was released",
            level="L1",
        )

        assert result.score <= 0.3
        assert "incorrect" in result.reasoning.lower() or "wrong" in result.reasoning.lower()


def test_grade_answer_considers_cognitive_level():
    """Test that grading considers the cognitive level."""
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value.content = [
            MagicMock(text='{"score": 0.8, "reasoning": "Good inference from facts"}')
        ]

        result = grade_answer(
            question="Why did stock prices fall?",
            expected="Because earnings missed expectations",
            actual="Due to poor financial results",
            level="L2",  # Inference level
        )

        assert result.score >= 0.7
        assert "inference" in result.reasoning.lower() or result.score > 0


def test_grade_answer_handles_api_errors():
    """Test graceful handling of API errors."""
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            grade_answer(
                question="Test question?",
                expected="Expected answer",
                actual="Actual answer",
                level="L1",
            )
