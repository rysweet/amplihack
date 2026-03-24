"""Tests for the metacognition grader with 4-dimension scoring.

TDD tests updated for Phase 3 refactoring:
- _grade_with_llm(), grade(), batch_grade() are now async
- grade_metacognition() stays SYNC (asyncio.run bridge)
- Uses amplihack.llm.client.completion (not litellm)
- Mock target: amplihack.eval.metacognition_grader.completion
- Mock type: AsyncMock(return_value="plain string")
- _mock_llm_response() helper is removed
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from amplihack.eval.metacognition_grader import (
    Dimension,
    MetacognitionGrader,
    MetacognitionScore,
)


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

    def test_grader_does_not_import_litellm(self):
        """metacognition_grader.py must not import litellm after refactoring."""
        import amplihack.eval.metacognition_grader as grader_module

        assert not hasattr(grader_module, "litellm"), (
            "litellm should be removed from metacognition_grader.py after refactoring"
        )

    def test_grade_is_async(self):
        """grade() must be a coroutine function (async def)."""
        import inspect

        grader = MetacognitionGrader()
        assert inspect.iscoroutinefunction(grader.grade), "grade() must be async after refactoring"

    def test_batch_grade_is_async(self):
        """batch_grade() must be a coroutine function (async def)."""
        import inspect

        grader = MetacognitionGrader()
        assert inspect.iscoroutinefunction(grader.batch_grade), (
            "batch_grade() must be async after refactoring"
        )

    def test_grade_metacognition_stays_sync(self):
        """grade_metacognition() module-level function stays SYNCHRONOUS."""
        import inspect

        from amplihack.eval.metacognition_grader import grade_metacognition

        assert not inspect.iscoroutinefunction(grade_metacognition), (
            "grade_metacognition() must remain SYNCHRONOUS (asyncio.run bridge "
            "to protect progressive_test_suite.py callers)"
        )

    @pytest.mark.asyncio
    async def test_grade_produces_4_dimensions(self):
        """Grading produces exactly 4 metacognition dimensions."""
        with patch(
            "amplihack.eval.metacognition_grader.completion",
            new=AsyncMock(
                return_value=(
                    '{"factual_accuracy": {"score": 0.9, "reasoning": "Test LLM response: Good recall"}, '
                    '"self_awareness": {"score": 0.8, "reasoning": "Test LLM response: Knows limits"}, '
                    '"knowledge_boundaries": {"score": 0.7, "reasoning": "Test LLM response: Some gaps"}, '
                    '"explanation_quality": {"score": 0.85, "reasoning": "Test LLM response: Clear"}}'
                )
            ),
        ):
            grader = MetacognitionGrader()
            score = await grader.grade(
                question="What does L1 evaluate?",
                expected_answer="L1 evaluates direct recall of facts from a single source.",
                student_answer="L1 tests recall of facts.",
                self_explanation="Test LLM response: I know this because recall means remembering directly.",
            )

        assert isinstance(score, MetacognitionScore)
        assert len(score.dimensions) == 4
        dimension_names = {d.name for d in score.dimensions}
        assert "factual_accuracy" in dimension_names
        assert "self_awareness" in dimension_names
        assert "knowledge_boundaries" in dimension_names
        assert "explanation_quality" in dimension_names

    @pytest.mark.asyncio
    async def test_grade_computes_overall_score(self):
        """Overall score is mean of all 4 dimensions."""
        with patch(
            "amplihack.eval.metacognition_grader.completion",
            new=AsyncMock(
                return_value=(
                    '{"factual_accuracy": {"score": 0.8, "reasoning": "Test LLM response: Good"}, '
                    '"self_awareness": {"score": 0.6, "reasoning": "Test LLM response: Fair"}, '
                    '"knowledge_boundaries": {"score": 1.0, "reasoning": "Test LLM response: Excellent"}, '
                    '"explanation_quality": {"score": 0.4, "reasoning": "Test LLM response: Poor"}}'
                )
            ),
        ):
            grader = MetacognitionGrader()
            score = await grader.grade(
                question="Test?",
                expected_answer="Expected",
                student_answer="Actual",
                self_explanation="Test LLM response: Because reasons",
            )

        expected_overall = (0.8 + 0.6 + 1.0 + 0.4) / 4
        assert score.overall_score == pytest.approx(expected_overall, abs=0.001)

    @pytest.mark.asyncio
    async def test_grade_handles_empty_self_explanation(self):
        """Grader handles student with no self-explanation."""
        with patch(
            "amplihack.eval.metacognition_grader.completion",
            new=AsyncMock(
                return_value=(
                    '{"factual_accuracy": {"score": 0.5, "reasoning": "Test LLM response: Partial"}, '
                    '"self_awareness": {"score": 0.1, "reasoning": "Test LLM response: No self-reflection"}, '
                    '"knowledge_boundaries": {"score": 0.2, "reasoning": "Test LLM response: Unclear"}, '
                    '"explanation_quality": {"score": 0.0, "reasoning": "Test LLM response: No explanation"}}'
                )
            ),
        ):
            grader = MetacognitionGrader()
            score = await grader.grade(
                question="What is L2?",
                expected_answer="L2 tests inference.",
                student_answer="Test LLM response: I think L2 is something.",
                self_explanation="",
            )

        assert score.overall_score < 0.5

    @pytest.mark.asyncio
    async def test_grade_handles_llm_error(self):
        """grade() returns zero scores on LLM/completion error (fail-open)."""
        with patch(
            "amplihack.eval.metacognition_grader.completion",
            new=AsyncMock(side_effect=Exception("Test LLM response: API Error")),
        ):
            grader = MetacognitionGrader()
            score = await grader.grade(
                question="Test?",
                expected_answer="Expected",
                student_answer="Actual",
                self_explanation="Test LLM response: Explanation",
            )

        assert score.overall_score == 0.0
        assert len(score.dimensions) == 4
        assert all(d.score == 0.0 for d in score.dimensions)

    @pytest.mark.asyncio
    async def test_batch_grade(self):
        """Batch grading scores multiple question-answer pairs."""
        with patch(
            "amplihack.eval.metacognition_grader.completion",
            new=AsyncMock(
                return_value=(
                    '{"factual_accuracy": {"score": 0.9, "reasoning": "Test LLM response: Good"}, '
                    '"self_awareness": {"score": 0.8, "reasoning": "Test LLM response: Good"}, '
                    '"knowledge_boundaries": {"score": 0.7, "reasoning": "Test LLM response: Good"}, '
                    '"explanation_quality": {"score": 0.85, "reasoning": "Test LLM response: Good"}}'
                )
            ),
        ):
            grader = MetacognitionGrader()
            items = [
                {
                    "question": "What is L1?",
                    "expected": "Recall",
                    "actual": "Test LLM response: Recall of facts",
                    "explanation": "Test LLM response: Direct recall",
                },
                {
                    "question": "What is L2?",
                    "expected": "Inference",
                    "actual": "Test LLM response: Reasoning from facts",
                    "explanation": "Test LLM response: Connecting facts",
                },
            ]

            scores = await grader.batch_grade(items)

        assert len(scores) == 2
        assert all(isinstance(s, MetacognitionScore) for s in scores)

    @pytest.mark.asyncio
    async def test_completion_plain_string_used_directly(self):
        """_grade_with_llm uses completion() result as plain str (no .choices[0])."""
        json_response = (
            '{"factual_accuracy": {"score": 0.9, "reasoning": "Test LLM response: Good"}, '
            '"self_awareness": {"score": 0.8, "reasoning": "Test LLM response: Good"}, '
            '"knowledge_boundaries": {"score": 0.7, "reasoning": "Test LLM response: Good"}, '
            '"explanation_quality": {"score": 0.85, "reasoning": "Test LLM response: Good"}}'
        )

        with patch(
            "amplihack.eval.metacognition_grader.completion",
            new=AsyncMock(return_value=json_response),
        ):
            grader = MetacognitionGrader()
            # This will fail if code tries response.choices[0].message.content
            # since the mock returns a plain string
            score = await grader.grade(
                question="Test?",
                expected_answer="Expected",
                student_answer="Test LLM response: Actual",
                self_explanation="Test LLM response: Explanation",
            )

        assert isinstance(score, MetacognitionScore)
        assert score.overall_score > 0.0


class TestGradeMetacognitionSyncBridge:
    """Tests for grade_metacognition() synchronous bridge function."""

    def test_grade_metacognition_is_callable(self):
        """grade_metacognition() is importable and callable."""
        from amplihack.eval.metacognition_grader import grade_metacognition

        assert callable(grade_metacognition)

    def test_grade_metacognition_accepts_trace_dict(self):
        """grade_metacognition() accepts dict trace and returns ReasoningTraceScore."""
        from amplihack.eval.metacognition_grader import ReasoningTraceScore, grade_metacognition

        with patch(
            "amplihack.eval.metacognition_grader.completion",
            new=AsyncMock(
                return_value=(
                    '{"factual_accuracy": {"score": 0.5, "reasoning": "Test LLM response: OK"}, '
                    '"self_awareness": {"score": 0.5, "reasoning": "Test LLM response: OK"}, '
                    '"knowledge_boundaries": {"score": 0.5, "reasoning": "Test LLM response: OK"}, '
                    '"explanation_quality": {"score": 0.5, "reasoning": "Test LLM response: OK"}}'
                )
            ),
        ):
            result = grade_metacognition(
                trace={"step": "reasoning", "output": "result"},
                answer_score=0.8,
                level="L1",
            )

        assert isinstance(result, ReasoningTraceScore)
        assert isinstance(result.overall, float)

    def test_grade_metacognition_accepts_string_trace(self):
        """grade_metacognition() accepts string trace."""
        from amplihack.eval.metacognition_grader import grade_metacognition

        with patch(
            "amplihack.eval.metacognition_grader.completion",
            new=AsyncMock(
                return_value=(
                    '{"factual_accuracy": {"score": 0.5, "reasoning": "Test LLM response: OK"}, '
                    '"self_awareness": {"score": 0.5, "reasoning": "Test LLM response: OK"}, '
                    '"knowledge_boundaries": {"score": 0.5, "reasoning": "Test LLM response: OK"}, '
                    '"explanation_quality": {"score": 0.5, "reasoning": "Test LLM response: OK"}}'
                )
            ),
        ):
            result = grade_metacognition(
                trace="Test LLM response: reasoning trace as string",
                answer_score=0.7,
                level="L2",
            )

        assert result is not None
        assert isinstance(result.overall, float)

    def test_grade_metacognition_returns_zero_on_error(self):
        """grade_metacognition() returns zero-score on error (fail-open)."""
        from amplihack.eval.metacognition_grader import grade_metacognition

        with patch(
            "amplihack.eval.metacognition_grader.completion",
            new=AsyncMock(side_effect=Exception("Test LLM response: API Error")),
        ):
            result = grade_metacognition(
                trace="Test LLM response: trace",
                answer_score=0.0,
                level="L1",
            )

        assert result.overall == 0.0
