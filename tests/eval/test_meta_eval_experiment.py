"""Tests for the meta-eval teaching experiment runner.

TDD tests updated for Phase 3 refactoring:
- _quiz_student() and run() are now async
- Uses amplihack.llm.client.completion (not litellm)
- Mock targets: module-local completion references in each sub-module
  - amplihack.eval.teaching_session.completion (for TeachingSession)
  - amplihack.eval.metacognition_grader.completion (for MetacognitionGrader)
  - amplihack.eval.meta_eval_experiment.completion (for _quiz_student)
- Mock type: AsyncMock(return_value="plain string")
- _mock_llm_response() helper is removed
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from amplihack.eval.meta_eval_experiment import (
    ExperimentConfig,
    ExperimentReport,
    MetaEvalExperiment,
)

# Common mock response strings (plain strings — NOT response objects)
_TEACHER_MSG = "Test LLM response: L1 tests recall of direct facts from single sources."
_STUDENT_MSG = (
    '{"response": "Test LLM response: L1 is recall.", '
    '"self_explanation": "Test LLM response: Direct facts."}'
)
_GRADER_MSG = (
    '{"factual_accuracy": {"score": 0.9, "reasoning": "Test LLM response: Good"}, '
    '"self_awareness": {"score": 0.8, "reasoning": "Test LLM response: Good"}, '
    '"knowledge_boundaries": {"score": 0.7, "reasoning": "Test LLM response: Good"}, '
    '"explanation_quality": {"score": 0.85, "reasoning": "Test LLM response: Good"}}'
)
_QUIZ_MSG = (
    '{"answer": "Test LLM response: The four levels are L1-L4.", '
    '"self_explanation": "Test LLM response: The teacher explained them."}'
)


class TestExperimentConfig:
    """Tests for ExperimentConfig."""

    def test_default_config(self):
        config = ExperimentConfig()
        assert config.teaching_turns == 6
        assert config.quiz_questions >= 1
        assert config.model is not None

    def test_custom_config(self):
        config = ExperimentConfig(
            teaching_turns=10,
            quiz_questions=8,
            model="gpt-4",
        )
        assert config.teaching_turns == 10
        assert config.quiz_questions == 8
        assert config.model == "gpt-4"


class TestExperimentReport:
    """Tests for ExperimentReport."""

    def test_report_creation(self):
        report = ExperimentReport(
            knowledge_base_size=5,
            teaching_turns_completed=6,
            quiz_results=[],
            metacognition_scores=[],
            overall_score=0.0,
            summary="No results",
        )
        assert report.knowledge_base_size == 5
        assert report.teaching_turns_completed == 6
        assert report.overall_score == 0.0

    def test_report_to_dict(self):
        report = ExperimentReport(
            knowledge_base_size=3,
            teaching_turns_completed=4,
            quiz_results=[{"question": "Q1", "score": 0.8}],
            metacognition_scores=[{"overall": 0.75}],
            overall_score=0.77,
            summary="Good results",
        )
        result = report.to_dict()
        assert isinstance(result, dict)
        assert result["knowledge_base_size"] == 3
        assert result["overall_score"] == 0.77


class TestMetaEvalExperiment:
    """Tests for the MetaEvalExperiment runner."""

    def test_experiment_initialization(self):
        experiment = MetaEvalExperiment(config=ExperimentConfig())
        assert experiment.config is not None

    def test_build_knowledge_base(self):
        """Experiment builds knowledge base from eval system docs."""
        experiment = MetaEvalExperiment(config=ExperimentConfig())
        kb = experiment.build_knowledge_base()
        assert isinstance(kb, list)
        assert len(kb) > 0
        combined = " ".join(kb)
        assert "L1" in combined or "recall" in combined.lower()

    def test_generate_eval_quiz(self):
        """Experiment generates quiz questions about eval system."""
        experiment = MetaEvalExperiment(config=ExperimentConfig(quiz_questions=3))
        kb = experiment.build_knowledge_base()
        quiz = experiment.generate_eval_quiz(kb)
        assert isinstance(quiz, list)
        assert len(quiz) >= 1
        for q in quiz:
            assert "question" in q
            assert "expected_answer" in q

    def test_run_is_async(self):
        """run() must be a coroutine function (async def)."""
        import inspect

        experiment = MetaEvalExperiment(config=ExperimentConfig())
        assert inspect.iscoroutinefunction(experiment.run), "run() must be async after refactoring"

    def test_quiz_student_is_async(self):
        """_quiz_student() must be a coroutine function (async def)."""
        import inspect

        experiment = MetaEvalExperiment(config=ExperimentConfig())
        assert inspect.iscoroutinefunction(experiment._quiz_student), (
            "_quiz_student() must be async after refactoring"
        )

    def test_does_not_use_litellm_in_quiz_student(self):
        """_quiz_student no longer defers to litellm — uses module-level completion import."""

        import amplihack.eval.meta_eval_experiment as exp_module

        # After refactoring, the module-level 'completion' reference exists
        assert hasattr(exp_module, "completion"), (
            "amplihack.eval.meta_eval_experiment must import completion at module level"
        )

    @pytest.mark.asyncio
    async def test_run_experiment_produces_report(self, tmp_path):
        """Full async experiment produces a structured report."""
        call_count = 0

        async def teaching_session_mock(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _TEACHER_MSG if call_count % 2 == 1 else _STUDENT_MSG

        with (
            patch(
                "amplihack.eval.teaching_session.completion",
                side_effect=teaching_session_mock,
            ),
            patch(
                "amplihack.eval.meta_eval_experiment.completion",
                new=AsyncMock(return_value=_QUIZ_MSG),
            ),
            patch(
                "amplihack.eval.metacognition_grader.completion",
                new=AsyncMock(return_value=_GRADER_MSG),
            ),
        ):
            config = ExperimentConfig(
                teaching_turns=2,
                quiz_questions=3,
                output_dir=str(tmp_path),
            )
            experiment = MetaEvalExperiment(config=config)
            report = await experiment.run()

        assert isinstance(report, ExperimentReport)
        assert report.teaching_turns_completed == 2
        assert report.knowledge_base_size > 0
        assert 0.0 <= report.overall_score <= 1.0

    @pytest.mark.asyncio
    async def test_run_experiment_saves_report(self, tmp_path):
        """Experiment saves JSON report to output directory."""
        call_count = 0

        async def teaching_session_mock(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _TEACHER_MSG if call_count % 2 == 1 else _STUDENT_MSG

        with (
            patch(
                "amplihack.eval.teaching_session.completion",
                side_effect=teaching_session_mock,
            ),
            patch(
                "amplihack.eval.meta_eval_experiment.completion",
                new=AsyncMock(return_value=_QUIZ_MSG),
            ),
            patch(
                "amplihack.eval.metacognition_grader.completion",
                new=AsyncMock(return_value=_GRADER_MSG),
            ),
        ):
            config = ExperimentConfig(
                teaching_turns=1,
                quiz_questions=3,
                output_dir=str(tmp_path),
            )
            experiment = MetaEvalExperiment(config=config)
            await experiment.run()

        report_file = tmp_path / "meta_eval_report.json"
        assert report_file.exists()

        with open(report_file) as f:
            saved = json.load(f)
        assert "overall_score" in saved
        assert "knowledge_base_size" in saved

    @pytest.mark.asyncio
    async def test_experiment_handles_teaching_failure(self, tmp_path):
        """Experiment returns error report when teaching session fails."""
        with patch(
            "amplihack.eval.teaching_session.completion",
            new=AsyncMock(side_effect=Exception("Test LLM response: Teaching API Error")),
        ):
            config = ExperimentConfig(
                teaching_turns=1,
                quiz_questions=1,
                output_dir=str(tmp_path),
            )
            experiment = MetaEvalExperiment(config=config)
            report = await experiment.run()

        # Should produce an error report with zero scores, not raise
        assert isinstance(report, ExperimentReport)
        assert report.overall_score == 0.0

    @pytest.mark.asyncio
    async def test_quiz_student_uses_module_local_completion(self, tmp_path):
        """_quiz_student() calls module-local completion (not litellm)."""
        call_count = 0

        async def teaching_session_mock(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _TEACHER_MSG if call_count % 2 == 1 else _STUDENT_MSG

        with (
            patch(
                "amplihack.eval.teaching_session.completion",
                side_effect=teaching_session_mock,
            ),
            patch(
                "amplihack.eval.meta_eval_experiment.completion",
                new=AsyncMock(return_value=_QUIZ_MSG),
            ) as mock_quiz_completion,
            patch(
                "amplihack.eval.metacognition_grader.completion",
                new=AsyncMock(return_value=_GRADER_MSG),
            ),
        ):
            config = ExperimentConfig(
                teaching_turns=1,
                quiz_questions=2,
                output_dir=str(tmp_path),
            )
            experiment = MetaEvalExperiment(config=config)
            await experiment.run()

        # _quiz_student calls completion once per quiz question
        assert mock_quiz_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_quiz_results_use_parsed_json_answer(self, tmp_path):
        """Quiz results extract 'answer' from JSON response."""
        call_count = 0

        async def teaching_session_mock(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _TEACHER_MSG if call_count % 2 == 1 else _STUDENT_MSG

        with (
            patch(
                "amplihack.eval.teaching_session.completion",
                side_effect=teaching_session_mock,
            ),
            patch(
                "amplihack.eval.meta_eval_experiment.completion",
                new=AsyncMock(return_value=_QUIZ_MSG),
            ),
            patch(
                "amplihack.eval.metacognition_grader.completion",
                new=AsyncMock(return_value=_GRADER_MSG),
            ),
        ):
            config = ExperimentConfig(
                teaching_turns=1,
                quiz_questions=1,
                output_dir=str(tmp_path),
            )
            experiment = MetaEvalExperiment(config=config)
            report = await experiment.run()

        assert len(report.quiz_results) == 1
        quiz_result = report.quiz_results[0]
        assert "student_answer" in quiz_result
        # Answer comes from JSON "answer" field
        assert "Test LLM response" in quiz_result["student_answer"]
