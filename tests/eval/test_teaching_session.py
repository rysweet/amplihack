"""Tests for the TeachingSession multi-turn framework."""

from unittest.mock import MagicMock, patch

import pytest

from amplihack.eval.teaching_session import (
    TeachingConfig,
    TeachingResult,
    TeachingSession,
    Turn,
)


def _mock_llm_response(text: str) -> MagicMock:
    """Create a mock litellm response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = text
    return mock_response


class TestTeachingConfig:
    """Tests for TeachingConfig dataclass."""

    def test_default_config(self):
        config = TeachingConfig()
        assert config.max_turns == 6
        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.teacher_system_prompt is not None
        assert config.student_system_prompt is not None

    def test_custom_config(self):
        config = TeachingConfig(max_turns=10, model="gpt-4")
        assert config.max_turns == 10
        assert config.model == "gpt-4"


class TestTurn:
    """Tests for Turn dataclass."""

    def test_turn_creation(self):
        turn = Turn(
            turn_number=1,
            teacher_message="What is L1?",
            student_response="L1 is recall.",
            self_explanation="I know this because...",
        )
        assert turn.turn_number == 1
        assert turn.teacher_message == "What is L1?"
        assert turn.student_response == "L1 is recall."
        assert turn.self_explanation == "I know this because..."


class TestTeachingResult:
    """Tests for TeachingResult dataclass."""

    def test_result_creation(self):
        result = TeachingResult(
            turns=[],
            knowledge_transferred=[],
            student_accuracy=0.0,
        )
        assert result.turns == []
        assert result.student_accuracy == 0.0
        assert result.knowledge_transferred == []


class TestTeachingSession:
    """Tests for the TeachingSession orchestrator."""

    def test_session_initialization(self):
        session = TeachingSession(
            knowledge_base=["Fact 1", "Fact 2"],
            config=TeachingConfig(max_turns=3),
        )
        assert session.knowledge_base == ["Fact 1", "Fact 2"]
        assert session.config.max_turns == 3

    def test_session_requires_knowledge(self):
        with pytest.raises(ValueError, match="knowledge_base cannot be empty"):
            TeachingSession(knowledge_base=[], config=TeachingConfig())

    @patch("litellm.completion")
    def test_generate_teacher_message(self, mock_completion):
        """Teacher generates a teaching message from knowledge base."""
        mock_completion.return_value = _mock_llm_response(
            "Let me teach you about L1 evaluation. "
            "L1 tests recall of direct facts from a single source."
        )

        session = TeachingSession(
            knowledge_base=["L1 tests recall of direct facts."],
            config=TeachingConfig(max_turns=3),
        )

        message = session._generate_teacher_message(turn_number=1, history=[])
        assert message  # Non-empty
        assert isinstance(message, str)

    @patch("litellm.completion")
    def test_generate_student_response(self, mock_completion):
        """Student generates a response with self-explanation."""
        mock_completion.return_value = _mock_llm_response(
            '{"response": "L1 tests recall.", '
            '"self_explanation": "I understand this because the teacher said recall means direct facts."}'
        )

        session = TeachingSession(
            knowledge_base=["L1 tests recall."],
            config=TeachingConfig(max_turns=3),
        )

        response, explanation = session._generate_student_response(
            teacher_message="L1 tests recall of direct facts.",
            history=[],
        )
        assert response  # Non-empty
        assert isinstance(response, str)
        assert isinstance(explanation, str)

    @patch("litellm.completion")
    def test_run_session_produces_turns(self, mock_completion):
        """Full session produces correct number of turns."""
        # Alternate teacher and student responses
        teacher_response = _mock_llm_response(
            "L1 tests recall of direct facts from a single source."
        )
        student_response = _mock_llm_response(
            '{"response": "I understand, L1 is about direct fact recall.", '
            '"self_explanation": "The teacher explained that L1 focuses on recall."}'
        )

        mock_completion.side_effect = [
            teacher_response,
            student_response,  # Turn 1
            teacher_response,
            student_response,  # Turn 2
            teacher_response,
            student_response,  # Turn 3
        ]

        session = TeachingSession(
            knowledge_base=["L1 tests recall of direct facts."],
            config=TeachingConfig(max_turns=3),
        )

        result = session.run()
        assert isinstance(result, TeachingResult)
        assert len(result.turns) == 3
        assert all(isinstance(t, Turn) for t in result.turns)

    @patch("litellm.completion")
    def test_session_accumulates_history(self, mock_completion):
        """Each turn builds on previous conversation."""
        call_count = 0

        def track_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:  # Teacher calls
                return _mock_llm_response(f"Teaching point {call_count}")
            # Student calls
            return _mock_llm_response(
                f'{{"response": "Got it {call_count}", '
                f'"self_explanation": "I learned this in turn {call_count}"}}'
            )

        mock_completion.side_effect = track_calls

        session = TeachingSession(
            knowledge_base=["Fact A", "Fact B"],
            config=TeachingConfig(max_turns=2),
        )

        result = session.run()
        assert len(result.turns) == 2
        # Verify turns are numbered correctly
        assert result.turns[0].turn_number == 1
        assert result.turns[1].turn_number == 2

    @patch("litellm.completion")
    def test_session_extracts_knowledge_transferred(self, mock_completion):
        """Session identifies what knowledge was transferred."""
        mock_completion.side_effect = [
            _mock_llm_response("L1 tests direct recall from single sources."),
            _mock_llm_response(
                '{"response": "L1 is about recalling facts directly.", '
                '"self_explanation": "Direct recall means retrieving exact facts."}'
            ),
        ]

        session = TeachingSession(
            knowledge_base=["L1 tests direct recall from single sources."],
            config=TeachingConfig(max_turns=1),
        )

        result = session.run()
        assert isinstance(result.knowledge_transferred, list)
