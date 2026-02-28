"""Tests for agentic answer mode (answer_question_agentic).

Philosophy:
- Test without requiring API keys
- Mock LLM for predictable results
- Verify the agentic loop is invoked and produces answers
- Verify fallback to single-shot on failure
- Verify CLI --answer-mode flag wiring
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.agents.goal_seeking import LearningAgent
from amplihack.agents.goal_seeking.agentic_loop import LoopState


class TestAnswerQuestionAgentic:
    """Test suite for LearningAgent.answer_question_agentic."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_storage):
        """Create LearningAgent with temporary storage."""
        agent = LearningAgent(agent_name="test_agentic", storage_path=str(temp_storage))
        yield agent
        agent.close()

    def test_empty_question_returns_error(self, agent):
        """Empty question returns error without invoking the loop."""
        answer = agent.answer_question_agentic("")
        assert "Error" in answer or "empty" in answer.lower()

    def test_whitespace_question_returns_error(self, agent):
        """Whitespace-only question returns error."""
        answer = agent.answer_question_agentic("   ")
        assert "Error" in answer or "empty" in answer.lower()

    @patch.object(LearningAgent, "answer_question")
    def test_fallback_on_empty_states(self, mock_single_shot, agent):
        """Falls back to single-shot when agentic loop returns empty states."""
        mock_single_shot.return_value = "Single-shot fallback answer"

        # Make run_until_goal return empty list
        with patch.object(agent.loop, "run_until_goal", return_value=[]):
            answer = agent.answer_question_agentic("What is photosynthesis?")

        mock_single_shot.assert_called_once_with("What is photosynthesis?")
        assert answer == "Single-shot fallback answer"

    @patch.object(LearningAgent, "answer_question")
    def test_fallback_on_loop_exception(self, mock_single_shot, agent):
        """Falls back to single-shot when agentic loop raises exception."""
        mock_single_shot.return_value = "Fallback answer"

        with patch.object(agent.loop, "run_until_goal", side_effect=RuntimeError("Loop crashed")):
            answer = agent.answer_question_agentic("What is gravity?")

        mock_single_shot.assert_called_once_with("What is gravity?")
        assert answer == "Fallback answer"

    def test_agentic_loop_called_with_correct_goal(self, agent):
        """Verifies that run_until_goal is called with the question in the goal."""
        state = LoopState(
            perception="test",
            reasoning="test reasoning",
            action={"action": "synthesize_answer", "params": {}},
            learning="learned",
            outcome="The answer is 42",
            iteration=1,
        )

        with patch.object(agent.loop, "run_until_goal", return_value=[state]) as mock_run:
            agent.answer_question_agentic("What is the meaning of life?")

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args
            goal = call_kwargs.kwargs.get("goal") or call_kwargs.args[0]
            assert "What is the meaning of life?" in goal

    def test_extracts_string_outcome(self, agent):
        """When the last state has a string outcome, it is returned as the answer."""
        state = LoopState(
            perception="test",
            reasoning="found relevant facts",
            action={"action": "synthesize_answer", "params": {}},
            learning="synthesized answer",
            outcome="Photosynthesis converts light to energy",
            iteration=1,
        )

        with patch.object(agent.loop, "run_until_goal", return_value=[state]):
            answer = agent.answer_question_agentic("What is photosynthesis?")

        assert "Photosynthesis converts light to energy" in answer

    def test_extracts_dict_outcome(self, agent):
        """When outcome is a dict, extracts answer or result key."""
        state = LoopState(
            perception="test",
            reasoning="found facts",
            action={"action": "synthesize_answer", "params": {}},
            learning="done",
            outcome={"answer": "Dogs are mammals", "confidence": 0.9},
            iteration=1,
        )

        with patch.object(agent.loop, "run_until_goal", return_value=[state]):
            answer = agent.answer_question_agentic("Are dogs mammals?")

        assert "Dogs are mammals" in answer

    def test_multiple_iterations_uses_last_state(self, agent):
        """With multiple loop iterations, the last state's outcome is used."""
        state1 = LoopState(
            perception="test",
            reasoning="searching memory",
            action={"action": "search_memory", "params": {"query": "dogs"}},
            learning="found some facts",
            outcome=[{"context": "Dogs", "outcome": "Dogs are mammals"}],
            iteration=1,
        )
        state2 = LoopState(
            perception="found facts",
            reasoning="now synthesizing",
            action={"action": "synthesize_answer", "params": {}},
            learning="synthesized",
            outcome="Dogs are indeed mammals belonging to class Mammalia",
            iteration=2,
        )

        with patch.object(agent.loop, "run_until_goal", return_value=[state1, state2]):
            answer = agent.answer_question_agentic("Are dogs mammals?")

        assert "Mammalia" in answer

    def test_goal_achieved_stops_on_synthesize(self, agent):
        """The is_goal_achieved callback detects synthesize_answer action."""
        # Create a mock that captures the is_goal_achieved callback
        captured_callback = {}

        def mock_run_until_goal(goal, initial_observation, is_goal_achieved=None):
            captured_callback["fn"] = is_goal_achieved
            state = LoopState(
                perception="test",
                reasoning="done",
                action={"action": "synthesize_answer", "params": {}},
                learning="done",
                outcome="Final answer",
                iteration=1,
            )
            return [state]

        with patch.object(agent.loop, "run_until_goal", side_effect=mock_run_until_goal):
            agent.answer_question_agentic("Test?")

        # Verify the callback works correctly
        callback = captured_callback["fn"]
        assert callback is not None

        # Test: synthesize_answer should signal goal achieved
        synth_state = MagicMock()
        synth_state.action = {"action": "synthesize_answer", "params": {}}
        assert callback(synth_state) is True

        # Test: search_memory should NOT signal goal achieved
        search_state = MagicMock()
        search_state.action = {"action": "search_memory", "params": {"query": "test"}}
        assert callback(search_state) is False

    def test_stores_qa_pair_in_memory(self, agent):
        """Verifies that a Q&A pair is stored in memory after agentic answer."""
        state = LoopState(
            perception="test",
            reasoning="done",
            action={"action": "synthesize_answer", "params": {}},
            learning="done",
            outcome="Gravity is a fundamental force",
            iteration=1,
        )

        initial_stats = agent.get_memory_stats()
        initial_count = initial_stats.get("total_experiences", 0)

        with patch.object(agent.loop, "run_until_goal", return_value=[state]):
            agent.answer_question_agentic("What is gravity?")

        final_stats = agent.get_memory_stats()
        final_count = final_stats.get("total_experiences", 0)
        assert final_count > initial_count

    @patch.object(LearningAgent, "answer_question")
    def test_fallback_on_none_outcome(self, mock_single_shot, agent):
        """Falls back to single-shot when outcome is None."""
        mock_single_shot.return_value = "Fallback"

        state = LoopState(
            perception="test",
            reasoning="done",
            action={"action": "search_memory", "params": {}},
            learning="nothing useful",
            outcome=None,
            iteration=1,
        )

        with patch.object(agent.loop, "run_until_goal", return_value=[state]):
            answer = agent.answer_question_agentic("Test question?")

        mock_single_shot.assert_called_once()
        assert answer == "Fallback"

    @patch.object(LearningAgent, "answer_question")
    def test_fallback_on_error_outcome(self, mock_single_shot, agent):
        """Falls back to single-shot when outcome starts with 'Error'."""
        mock_single_shot.return_value = "Fallback"

        state = LoopState(
            perception="test",
            reasoning="done",
            action={"action": "error", "params": {}},
            learning="failed",
            outcome="Error: action not found",
            iteration=1,
        )

        with patch.object(agent.loop, "run_until_goal", return_value=[state]):
            answer = agent.answer_question_agentic("Test question?")

        mock_single_shot.assert_called_once()
        assert answer == "Fallback"


class TestAgenticLoopModelPropagation:
    """Test that the agentic loop receives the correct model from LearningAgent."""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_loop_uses_agent_model_not_default(self, temp_storage):
        """AgenticLoop should use the LearningAgent's resolved model, not DEFAULT_MODEL."""
        agent = LearningAgent(
            agent_name="test_model_prop",
            model="claude-opus-4-6",
            storage_path=str(temp_storage),
        )
        try:
            assert agent.loop.model == "claude-opus-4-6"
        finally:
            agent.close()

    def test_loop_uses_env_when_model_none(self, temp_storage):
        """When model=None, loop should get env var or fallback, not the hardcoded default."""
        with patch.dict("os.environ", {"EVAL_MODEL": "test-model-from-env"}):
            agent = LearningAgent(
                agent_name="test_model_env",
                model=None,
                storage_path=str(temp_storage),
            )
            try:
                assert agent.loop.model == "test-model-from-env"
            finally:
                agent.close()


class TestSDKBaseAnswerMode:
    """Test that GoalSeekingAgent.answer_question passes answer_mode through."""

    def test_sdk_answer_question_default_mode(self):
        """Default answer_mode is single-shot."""
        # GoalSeekingAgent is abstract, so we check the signature
        import inspect

        from amplihack.agents.goal_seeking.sdk_adapters.base import GoalSeekingAgent

        sig = inspect.signature(GoalSeekingAgent.answer_question)
        assert "answer_mode" in sig.parameters
        assert sig.parameters["answer_mode"].default == "single-shot"

    def test_sdk_answer_question_agentic_calls_correct_method(self):
        """When answer_mode='agentic', it calls answer_question_agentic on LearningAgent."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import GoalSeekingAgent

        # Create a mock agent that has the needed methods
        mock_agent = MagicMock(spec=GoalSeekingAgent)
        mock_agent._get_learning_agent = MagicMock()
        mock_la = MagicMock()
        mock_la.answer_question_agentic.return_value = "Agentic answer"
        mock_agent._get_learning_agent.return_value = mock_la

        # Call the unbound method with the mock as self
        result = GoalSeekingAgent.answer_question(mock_agent, "Test?", answer_mode="agentic")

        mock_la.answer_question_agentic.assert_called_once_with("Test?")
        assert result == "Agentic answer"


class TestMiniAgentWrapper:
    """Test the _MiniAgentWrapper used in the eval harness."""

    def test_wrapper_single_shot_mode(self):
        """In single-shot mode, calls answer_question on underlying agent."""
        from amplihack.eval.long_horizon_memory import _MiniAgentWrapper

        mock_la = MagicMock()
        mock_la.answer_question.return_value = "Single-shot answer"

        wrapper = _MiniAgentWrapper(mock_la, answer_mode="single-shot")
        result = wrapper.answer_question("Test?")

        mock_la.answer_question.assert_called_once_with("Test?")
        assert result == "Single-shot answer"

    def test_wrapper_agentic_mode(self):
        """In agentic mode, calls answer_question_agentic on underlying agent."""
        from amplihack.eval.long_horizon_memory import _MiniAgentWrapper

        mock_la = MagicMock()
        mock_la.answer_question_agentic.return_value = "Agentic answer"

        wrapper = _MiniAgentWrapper(mock_la, answer_mode="agentic")
        result = wrapper.answer_question("Test?")

        mock_la.answer_question_agentic.assert_called_once_with("Test?")
        assert result == "Agentic answer"

    def test_wrapper_forwards_learn(self):
        """learn_from_content is forwarded to underlying agent."""
        from amplihack.eval.long_horizon_memory import _MiniAgentWrapper

        mock_la = MagicMock()
        mock_la.learn_from_content.return_value = {"facts_extracted": 1}

        wrapper = _MiniAgentWrapper(mock_la)
        result = wrapper.learn_from_content("Test content")

        mock_la.learn_from_content.assert_called_once_with("Test content")
        assert result == {"facts_extracted": 1}

    def test_wrapper_handles_tuple_answer(self):
        """Single-shot mode handles tuple return from answer_question."""
        from amplihack.eval.long_horizon_memory import _MiniAgentWrapper

        mock_la = MagicMock()
        mock_la.answer_question.return_value = ("Answer text", {"trace": "data"})

        wrapper = _MiniAgentWrapper(mock_la, answer_mode="single-shot")
        result = wrapper.answer_question("Test?")

        assert result == "Answer text"


class TestSDKAgentWrapperAnswerMode:
    """Test that _SDKAgentWrapper passes answer_mode through."""

    def test_wrapper_passes_answer_mode(self):
        """_SDKAgentWrapper passes answer_mode to underlying agent."""
        from amplihack.eval.long_horizon_memory import _SDKAgentWrapper

        mock_sdk = MagicMock()
        mock_sdk.answer_question.return_value = "SDK answer"

        wrapper = _SDKAgentWrapper(mock_sdk, answer_mode="agentic")
        wrapper.answer_question("Test?")

        mock_sdk.answer_question.assert_called_once_with("Test?", answer_mode="agentic")

    def test_wrapper_default_single_shot(self):
        """_SDKAgentWrapper defaults to single-shot mode."""
        from amplihack.eval.long_horizon_memory import _SDKAgentWrapper

        mock_sdk = MagicMock()
        mock_sdk.answer_question.return_value = "SDK answer"

        wrapper = _SDKAgentWrapper(mock_sdk)
        wrapper.answer_question("Test?")

        mock_sdk.answer_question.assert_called_once_with("Test?", answer_mode="single-shot")
