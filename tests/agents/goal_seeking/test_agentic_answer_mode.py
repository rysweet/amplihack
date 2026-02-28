"""Tests for agentic answer mode (answer_question_agentic).

Philosophy:
- Test without requiring API keys
- Mock LLM for predictable results
- Verify augmentation pattern: single-shot first, then refine if gaps detected
- Verify single-shot result is never lost (agentic >= single-shot)
- Verify CLI --answer-mode flag wiring
"""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.agents.goal_seeking import LearningAgent


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
        """Empty question returns error without invoking any pipeline."""
        answer = agent.answer_question_agentic("")
        assert "Error" in answer or "empty" in answer.lower()

    def test_whitespace_question_returns_error(self, agent):
        """Whitespace-only question returns error."""
        answer = agent.answer_question_agentic("   ")
        assert "Error" in answer or "empty" in answer.lower()

    def test_returns_single_shot_when_complete(self, agent):
        """When single-shot answer is complete, returns it without refinement."""
        with patch.object(agent, "answer_question", return_value="Photosynthesis is X"):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": True, "gaps": []},
            ):
                answer = agent.answer_question_agentic("What is photosynthesis?")

        assert answer == "Photosynthesis is X"

    def test_returns_single_shot_when_no_gaps(self, agent):
        """When evaluation says incomplete but no gaps, returns single-shot."""
        with patch.object(agent, "answer_question", return_value="Partial answer"):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": False, "gaps": []},
            ):
                answer = agent.answer_question_agentic("Test question?")

        assert answer == "Partial answer"

    def test_returns_single_shot_when_no_additional_facts(self, agent):
        """When gap search finds nothing new, returns single-shot result."""
        mock_memory = MagicMock()
        mock_memory.search.return_value = []
        agent.memory = mock_memory

        with patch.object(agent, "answer_question", return_value=("Single-shot answer", None)):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": False, "gaps": ["missing topic"]},
            ):
                answer = agent.answer_question_agentic("What is gravity?")

        assert answer == "Single-shot answer"

    def test_refines_when_gaps_and_new_facts(self, agent):
        """When gaps detected and new facts found, re-synthesizes with all facts."""
        mock_memory = MagicMock()
        mock_memory.search.return_value = [
            {"experience_id": "new1", "context": "new", "outcome": "New fact"}
        ]
        mock_memory.get_all_facts.return_value = [
            {"experience_id": "orig1", "context": "orig", "outcome": "Original fact"}
        ]
        agent.memory = mock_memory

        with patch.object(agent, "answer_question", return_value=("Initial answer", None)):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": False, "gaps": ["missing detail"]},
            ):
                with patch.object(
                    agent, "_detect_intent", return_value={"intent": "simple_recall"}
                ):
                    with patch.object(
                        agent, "_synthesize_with_llm", return_value="Refined answer with more info"
                    ):
                        answer = agent.answer_question_agentic("Test question?")

        assert answer == "Refined answer with more info"

    def test_max_iterations_limits_gap_searches(self, agent):
        """Max iterations caps the number of gap-filling searches."""
        mock_memory = MagicMock()
        mock_memory.search.return_value = [
            {"experience_id": "new1", "context": "c", "outcome": "f"}
        ]
        mock_memory.get_all_facts.return_value = []
        agent.memory = mock_memory

        gaps = ["gap1", "gap2", "gap3", "gap4", "gap5"]

        with patch.object(agent, "answer_question", return_value=("Initial", None)):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": False, "gaps": gaps},
            ):
                with patch.object(
                    agent, "_detect_intent", return_value={"intent": "simple_recall"}
                ):
                    with patch.object(agent, "_synthesize_with_llm", return_value="Refined"):
                        # max_iterations=2 means only 2 gap queries
                        agent.answer_question_agentic("Test?", max_iterations=2)

        # search called only 2 times (not 5)
        assert mock_memory.search.call_count == 2

    def test_return_trace_returns_tuple(self, agent):
        """When return_trace=True, returns (answer, trace) tuple."""
        mock_trace = MagicMock()
        with patch.object(agent, "answer_question", return_value=("Answer text", mock_trace)):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": True},
            ):
                result = agent.answer_question_agentic("Test?", return_trace=True)

        assert isinstance(result, tuple)
        assert result[0] == "Answer text"
        assert result[1] is mock_trace

    def test_deduplicates_facts(self, agent):
        """Duplicate facts from original and gap search are deduplicated."""
        shared_fact = {"experience_id": "shared1", "context": "c", "outcome": "f"}
        new_fact = {"experience_id": "new1", "context": "c", "outcome": "new f"}

        mock_memory = MagicMock()
        mock_memory.search.return_value = [shared_fact, new_fact]
        mock_memory.get_all_facts.return_value = [shared_fact]
        agent.memory = mock_memory

        captured_context = {}

        def mock_synthesize(question, context, question_level, intent=None):
            captured_context["facts"] = context
            return "Refined answer"

        with patch.object(agent, "answer_question", return_value=("Initial", None)):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": False, "gaps": ["gap"]},
            ):
                with patch.object(
                    agent, "_detect_intent", return_value={"intent": "simple_recall"}
                ):
                    with patch.object(agent, "_synthesize_with_llm", side_effect=mock_synthesize):
                        agent.answer_question_agentic("Test?")

        # Should have 2 unique facts, not 3 (shared appears once)
        ids = [f.get("experience_id") for f in captured_context["facts"]]
        assert ids.count("shared1") == 1
        assert "new1" in ids

    def test_handles_answer_question_returning_string(self, agent):
        """Works when answer_question returns a plain string (no tuple)."""
        with patch.object(agent, "answer_question", return_value="Plain string answer"):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": True},
            ):
                answer = agent.answer_question_agentic("Test?")

        assert answer == "Plain string answer"


class TestEvaluateAnswerCompleteness:
    """Test suite for _evaluate_answer_completeness."""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_storage):
        agent = LearningAgent(agent_name="test_eval", storage_path=str(temp_storage))
        yield agent
        agent.close()

    def test_empty_answer_returns_incomplete(self, agent):
        """An empty answer is always incomplete."""
        result = agent._evaluate_answer_completeness("What is X?", "")
        assert result["is_complete"] is False
        assert len(result["gaps"]) > 0

    def test_no_info_answer_returns_incomplete(self, agent):
        """'I don't have enough' answer is always incomplete."""
        result = agent._evaluate_answer_completeness(
            "What is X?", "I don't have enough information"
        )
        assert result["is_complete"] is False

    @patch("litellm.completion")
    def test_complete_answer_from_llm(self, mock_llm, agent):
        """When LLM says complete, returns is_complete=True."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"is_complete": True})
        mock_llm.return_value = mock_response

        result = agent._evaluate_answer_completeness("What is X?", "X is a thing that does Y.")
        assert result["is_complete"] is True
        assert result["gaps"] == []

    @patch("litellm.completion")
    def test_incomplete_answer_from_llm(self, mock_llm, agent):
        """When LLM finds gaps, returns them as search queries."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {"is_complete": False, "gaps": ["missing detail about Z", "need info on W"]}
        )
        mock_llm.return_value = mock_response

        result = agent._evaluate_answer_completeness("What is X?", "X is partially described.")
        assert result["is_complete"] is False
        assert len(result["gaps"]) == 2
        assert "missing detail about Z" in result["gaps"]

    @patch("litellm.completion")
    def test_handles_markdown_wrapped_json(self, mock_llm, agent):
        """Handles LLM responses wrapped in markdown code fences."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '```json\n{"is_complete": false, "gaps": ["topic A"]}\n```'
        mock_llm.return_value = mock_response

        result = agent._evaluate_answer_completeness("Q?", "A.")
        assert result["is_complete"] is False
        assert "topic A" in result["gaps"]

    @patch("litellm.completion")
    def test_defaults_to_complete_on_parse_error(self, mock_llm, agent):
        """On JSON parse error, defaults to complete (conservative)."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON at all"
        mock_llm.return_value = mock_response

        result = agent._evaluate_answer_completeness("Q?", "A.")
        assert result["is_complete"] is True

    @patch("litellm.completion")
    def test_defaults_to_complete_on_exception(self, mock_llm, agent):
        """On LLM failure, defaults to complete (conservative)."""
        mock_llm.side_effect = RuntimeError("API down")

        result = agent._evaluate_answer_completeness("Q?", "A.")
        assert result["is_complete"] is True


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
