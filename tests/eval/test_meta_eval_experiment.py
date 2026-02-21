"""Tests for the meta-eval teaching experiment runner."""

import json
from unittest.mock import MagicMock, patch

from amplihack.eval.meta_eval_experiment import (
    ExperimentConfig,
    ExperimentReport,
    MetaEvalExperiment,
)


def _mock_llm_response(text: str) -> MagicMock:
    """Create a mock litellm response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = text
    return mock_response


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
        # Should contain info about L1-L4 levels
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

    @patch("litellm.completion")
    def test_run_experiment_produces_report(self, mock_completion, tmp_path):
        """Full experiment produces a structured report."""
        # Mock all LLM calls
        teacher_msg = _mock_llm_response("L1 tests recall of direct facts from single sources.")
        student_msg = _mock_llm_response(
            '{"response": "L1 is recall.", "self_explanation": "Direct facts."}'
        )
        grader_msg = _mock_llm_response(
            '{"factual_accuracy": {"score": 0.9, "reasoning": "Good"}, '
            '"self_awareness": {"score": 0.8, "reasoning": "Good"}, '
            '"knowledge_boundaries": {"score": 0.7, "reasoning": "Good"}, '
            '"explanation_quality": {"score": 0.85, "reasoning": "Good"}}'
        )

        # Teaching turns (teacher + student per turn) + grading calls
        mock_completion.side_effect = [
            teacher_msg,
            student_msg,  # Turn 1
            teacher_msg,
            student_msg,  # Turn 2
            grader_msg,  # Grade Q1
            grader_msg,  # Grade Q2
            grader_msg,  # Grade Q3
        ]

        config = ExperimentConfig(
            teaching_turns=2,
            quiz_questions=3,
            output_dir=str(tmp_path),
        )
        experiment = MetaEvalExperiment(config=config)
        report = experiment.run()

        assert isinstance(report, ExperimentReport)
        assert report.teaching_turns_completed == 2
        assert report.knowledge_base_size > 0
        assert 0.0 <= report.overall_score <= 1.0

    @patch("litellm.completion")
    def test_run_experiment_saves_report(self, mock_completion, tmp_path):
        """Experiment saves JSON report to output directory."""
        teacher_msg = _mock_llm_response("Teaching content.")
        student_msg = _mock_llm_response(
            '{"response": "Got it.", "self_explanation": "Makes sense."}'
        )
        grader_msg = _mock_llm_response(
            '{"factual_accuracy": {"score": 0.5, "reasoning": "OK"}, '
            '"self_awareness": {"score": 0.5, "reasoning": "OK"}, '
            '"knowledge_boundaries": {"score": 0.5, "reasoning": "OK"}, '
            '"explanation_quality": {"score": 0.5, "reasoning": "OK"}}'
        )

        mock_completion.side_effect = [
            teacher_msg,
            student_msg,  # Turn 1
            grader_msg,  # Grade Q1
            grader_msg,  # Grade Q2
            grader_msg,  # Grade Q3
        ]

        config = ExperimentConfig(
            teaching_turns=1,
            quiz_questions=3,
            output_dir=str(tmp_path),
        )
        experiment = MetaEvalExperiment(config=config)
        experiment.run()

        report_file = tmp_path / "meta_eval_report.json"
        assert report_file.exists()

        with open(report_file) as f:
            saved = json.load(f)
        assert "overall_score" in saved
        assert "knowledge_base_size" in saved

    @patch("litellm.completion")
    def test_experiment_handles_llm_errors(self, mock_completion, tmp_path):
        """Experiment handles LLM failures gracefully."""
        mock_completion.side_effect = Exception("API Error")

        config = ExperimentConfig(
            teaching_turns=1,
            quiz_questions=1,
            output_dir=str(tmp_path),
        )
        experiment = MetaEvalExperiment(config=config)
        report = experiment.run()

        # Should still produce a report, just with zero scores
        assert isinstance(report, ExperimentReport)
        assert report.overall_score == 0.0
