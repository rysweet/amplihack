"""Tests for the TeachingSession multi-turn framework.

TDD tests updated for Phase 3 refactoring:
- _generate_teacher_message(), _generate_student_response(), run() are now async
- Uses amplihack.llm.client.completion (not litellm)
- Mock target: amplihack.eval.teaching_session.completion (module-local reference)
- Mock type: AsyncMock(return_value="plain string")
- _mock_llm_response() helper is removed (return_value is now a plain string)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from amplihack.eval.teaching_session import (
    TeachingConfig,
    TeachingResult,
    TeachingSession,
    Turn,
)


class TestTeachingConfig:
    """Tests for TeachingConfig dataclass."""

    def test_default_config(self):
        config = TeachingConfig()
        assert config.max_turns == 6
        assert config.model == "claude-opus-4-6"
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

    def test_session_does_not_import_litellm(self):
        """teaching_session.py must not import litellm after refactoring."""
        import amplihack.eval.teaching_session as teaching_module

        assert not hasattr(teaching_module, "litellm"), (
            "litellm should be removed from teaching_session.py after refactoring"
        )

    def test_generate_teacher_message_is_async(self):
        """_generate_teacher_message() must be a coroutine function (async def)."""
        import inspect

        session = TeachingSession(
            knowledge_base=["L1 tests recall of direct facts."],
            config=TeachingConfig(max_turns=3),
        )

        assert inspect.iscoroutinefunction(session._generate_teacher_message), (
            "_generate_teacher_message must be async after refactoring"
        )

    def test_generate_student_response_is_async(self):
        """_generate_student_response() must be a coroutine function (async def)."""
        import inspect

        session = TeachingSession(
            knowledge_base=["L1 tests recall."],
            config=TeachingConfig(max_turns=3),
        )

        assert inspect.iscoroutinefunction(session._generate_student_response), (
            "_generate_student_response must be async after refactoring"
        )

    def test_run_is_async(self):
        """run() must be a coroutine function (async def)."""
        import inspect

        session = TeachingSession(
            knowledge_base=["Fact 1"],
            config=TeachingConfig(max_turns=1),
        )

        assert inspect.iscoroutinefunction(session.run), "run() must be async after refactoring"

    @pytest.mark.asyncio
    async def test_generate_teacher_message(self):
        """Teacher generates a message using new completion adapter."""
        with patch(
            "amplihack.eval.teaching_session.completion",
            new=AsyncMock(
                return_value="Test LLM response: L1 evaluates direct recall from single sources."
            ),
        ):
            session = TeachingSession(
                knowledge_base=["L1 tests recall of direct facts."],
                config=TeachingConfig(max_turns=3),
            )

            message = await session._generate_teacher_message(turn_number=1, history=[])

        assert message
        assert isinstance(message, str)

    @pytest.mark.asyncio
    async def test_generate_student_response(self):
        """Student generates a response with self-explanation using new adapter."""
        with patch(
            "amplihack.eval.teaching_session.completion",
            new=AsyncMock(
                return_value=(
                    '{"response": "Test LLM response: L1 tests recall.", '
                    '"self_explanation": "Test LLM response: recall means direct facts."}'
                )
            ),
        ):
            session = TeachingSession(
                knowledge_base=["L1 tests recall."],
                config=TeachingConfig(max_turns=3),
            )

            response, explanation = await session._generate_student_response(
                teacher_message="L1 tests recall of direct facts.",
                history=[],
            )

        assert response
        assert isinstance(response, str)
        assert isinstance(explanation, str)

    @pytest.mark.asyncio
    async def test_run_session_produces_turns(self):
        """Full async session produces correct number of turns."""
        call_count = 0

        async def mock_completion_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:  # Teacher turns (odd calls)
                return "Test LLM response: L1 tests recall of direct facts from a single source."
            # Student turns (even calls)
            return (
                '{"response": "Test LLM response: I understand, L1 is about direct fact recall.", '
                '"self_explanation": "Test LLM response: The teacher explained L1 focuses on recall."}'
            )

        with patch(
            "amplihack.eval.teaching_session.completion",
            side_effect=mock_completion_side_effect,
        ):
            session = TeachingSession(
                knowledge_base=["L1 tests recall of direct facts."],
                config=TeachingConfig(max_turns=3),
            )

            result = await session.run()

        assert isinstance(result, TeachingResult)
        assert len(result.turns) == 3
        assert all(isinstance(t, Turn) for t in result.turns)

    @pytest.mark.asyncio
    async def test_session_accumulates_history(self):
        """Turn numbers are sequential across accumulated history."""
        call_count = 0

        async def track_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:
                return f"Test LLM response: Teaching point {call_count}"
            return (
                f'{{"response": "Test LLM response: Got it {call_count}", '
                f'"self_explanation": "Test LLM response: Learned in turn {call_count}"}}'
            )

        with patch(
            "amplihack.eval.teaching_session.completion",
            side_effect=track_calls,
        ):
            session = TeachingSession(
                knowledge_base=["Fact A", "Fact B"],
                config=TeachingConfig(max_turns=2),
            )

            result = await session.run()

        assert len(result.turns) == 2
        assert result.turns[0].turn_number == 1
        assert result.turns[1].turn_number == 2

    @pytest.mark.asyncio
    async def test_session_extracts_knowledge_transferred(self):
        """Session records knowledge_transferred list from teacher messages."""
        call_count = 0

        async def mock_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "Test LLM response: L1 tests direct recall from single sources."
            return (
                '{"response": "Test LLM response: L1 is about recalling facts directly.", '
                '"self_explanation": "Test LLM response: Direct recall means exact facts."}'
            )

        with patch(
            "amplihack.eval.teaching_session.completion",
            side_effect=mock_side_effect,
        ):
            session = TeachingSession(
                knowledge_base=["L1 tests direct recall from single sources."],
                config=TeachingConfig(max_turns=1),
            )

            result = await session.run()

        assert isinstance(result.knowledge_transferred, list)

    @pytest.mark.asyncio
    async def test_completion_plain_string_used_directly_by_teacher(self):
        """Teacher message is the plain string from completion() — no .choices[0] parsing."""
        teacher_response = "Test LLM response: direct string content"

        with patch(
            "amplihack.eval.teaching_session.completion",
            new=AsyncMock(return_value=teacher_response),
        ):
            session = TeachingSession(
                knowledge_base=["Some fact"],
                config=TeachingConfig(max_turns=1),
            )
            result = await session._generate_teacher_message(turn_number=1, history=[])

        assert result == teacher_response

    @pytest.mark.asyncio
    async def test_completion_patch_target_is_module_local(self):
        """Patching amplihack.eval.teaching_session.completion intercepts the call."""
        with patch(
            "amplihack.eval.teaching_session.completion",
            new=AsyncMock(return_value="Test LLM response: patched correctly"),
        ) as mock_comp:
            session = TeachingSession(
                knowledge_base=["Some fact"],
                config=TeachingConfig(max_turns=1),
            )
            await session._generate_teacher_message(turn_number=1, history=[])

        mock_comp.assert_called_once()
