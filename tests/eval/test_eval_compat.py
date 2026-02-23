"""Tests for eval compat layer and amplihack agent adapters.

Verifies that:
1. Backward-compatible imports from amplihack_eval work via compat.py
2. AmplihackLearningAgentAdapter wraps LearningAgent correctly
3. AmplihackMultiAgentAdapter wraps MultiAgentLearningAgent correctly
4. AmplihackSDKAgentAdapter wraps SDK agents correctly
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ===========================================================================
# Test 1: compat.py imports
# ===========================================================================


class TestCompatImports:
    """Verify compat re-exports from amplihack-agent-eval."""

    def test_adapter_types_importable(self):
        """AgentAdapter, AgentResponse, ToolCall should be importable."""
        from amplihack.eval.compat import AgentAdapter, AgentResponse, ToolCall

        assert AgentAdapter is not None
        assert AgentResponse is not None
        assert ToolCall is not None

    def test_runner_types_importable(self):
        """EvalRunner and LongHorizonMemoryEval should be importable."""
        from amplihack.eval.compat import EvalRunner, LongHorizonMemoryEval

        assert EvalRunner is not None
        # LongHorizonMemoryEval is an alias for EvalRunner
        assert LongHorizonMemoryEval is EvalRunner

    def test_grader_importable(self):
        """grade_answer and GradeResult should be importable."""
        from amplihack.eval.compat import GradeResult, grade_answer

        assert callable(grade_answer)
        assert GradeResult is not None

    def test_data_types_importable(self):
        """Data generation types should be importable."""
        from amplihack.eval.compat import (
            GradingRubric,
            GroundTruth,
            Question,
            Turn,
            generate_dialogue,
            generate_questions,
        )

        assert Turn is not None
        assert Question is not None
        assert GroundTruth is not None
        assert GradingRubric is not None
        assert callable(generate_dialogue)
        assert callable(generate_questions)

    def test_self_improve_types_importable(self):
        """Self-improvement types should be importable."""
        from amplihack.eval.compat import (
            PatchProposal,
            ReviewResult,
            ReviewVote,
            propose_patch,
            vote_on_proposal,
        )

        assert PatchProposal is not None
        assert ReviewVote is not None
        assert ReviewResult is not None
        assert callable(propose_patch)
        assert callable(vote_on_proposal)

    def test_all_list_populated(self):
        """__all__ should list all re-exported names."""
        from amplihack.eval import compat

        assert len(compat.__all__) > 0
        assert "AgentAdapter" in compat.__all__
        assert "EvalRunner" in compat.__all__
        assert "grade_answer" in compat.__all__

    def test_types_are_same_objects(self):
        """Compat types should be the exact same objects as the eval package types."""
        from amplihack.eval.compat import AgentAdapter as CompatAdapter
        from amplihack.eval.compat import EvalRunner as CompatRunner
        from amplihack_eval.adapters.base import AgentAdapter as EvalAdapter
        from amplihack_eval.core.runner import EvalRunner as EvalRunnerOrig

        assert CompatAdapter is EvalAdapter
        assert CompatRunner is EvalRunnerOrig


# ===========================================================================
# Test 2: AmplihackLearningAgentAdapter
# ===========================================================================


class TestAmplihackLearningAgentAdapter:
    """Test AmplihackLearningAgentAdapter wraps LearningAgent correctly."""

    @patch("amplihack.agents.goal_seeking.learning_agent.LearningAgent")
    def test_init_creates_agent(self, mock_agent_cls):
        """Constructor should instantiate a LearningAgent."""
        from amplihack.eval.agent_adapter import AmplihackLearningAgentAdapter

        adapter = AmplihackLearningAgentAdapter(agent_name="test")
        mock_agent_cls.assert_called_once()
        assert adapter.name == "AmplihackLearning(test)"

    @patch("amplihack.agents.goal_seeking.learning_agent.LearningAgent")
    def test_learn_delegates(self, mock_agent_cls):
        """learn() should call agent.learn_from_content()."""
        from amplihack.eval.agent_adapter import AmplihackLearningAgentAdapter

        mock_instance = MagicMock()
        mock_agent_cls.return_value = mock_instance

        adapter = AmplihackLearningAgentAdapter(agent_name="test")
        adapter.learn("The sky is blue.")

        mock_instance.learn_from_content.assert_called_once_with("The sky is blue.")

    @patch("amplihack.agents.goal_seeking.learning_agent.LearningAgent")
    def test_answer_returns_agent_response_from_string(self, mock_agent_cls):
        """answer() should wrap a string return in AgentResponse."""
        from amplihack_eval.adapters.base import AgentResponse

        from amplihack.eval.agent_adapter import AmplihackLearningAgentAdapter

        mock_instance = MagicMock()
        mock_instance.answer_question.return_value = "Blue"
        mock_agent_cls.return_value = mock_instance

        adapter = AmplihackLearningAgentAdapter(agent_name="test")
        response = adapter.answer("What color is the sky?")

        assert isinstance(response, AgentResponse)
        assert response.answer == "Blue"
        assert response.reasoning_trace == ""

    @patch("amplihack.agents.goal_seeking.learning_agent.LearningAgent")
    def test_answer_handles_tuple_return(self, mock_agent_cls):
        """answer() should unpack (answer, trace) tuples."""
        from amplihack_eval.adapters.base import AgentResponse

        from amplihack.eval.agent_adapter import AmplihackLearningAgentAdapter

        mock_instance = MagicMock()
        mock_trace = MagicMock()
        mock_trace.__str__ = lambda self: "reasoning trace here"
        mock_instance.answer_question.return_value = ("Blue", mock_trace)
        mock_agent_cls.return_value = mock_instance

        adapter = AmplihackLearningAgentAdapter(agent_name="test")
        response = adapter.answer("What color is the sky?")

        assert isinstance(response, AgentResponse)
        assert response.answer == "Blue"
        assert "reasoning trace here" in response.reasoning_trace

    @patch("amplihack.agents.goal_seeking.learning_agent.LearningAgent")
    def test_close_delegates(self, mock_agent_cls):
        """close() should call agent.close()."""
        from amplihack.eval.agent_adapter import AmplihackLearningAgentAdapter

        mock_instance = MagicMock()
        mock_agent_cls.return_value = mock_instance

        adapter = AmplihackLearningAgentAdapter(agent_name="test")
        adapter.close()

        mock_instance.close.assert_called_once()

    @patch("amplihack.agents.goal_seeking.learning_agent.LearningAgent")
    def test_reset_recreates_agent(self, mock_agent_cls):
        """reset() should close and re-create the agent."""
        from amplihack.eval.agent_adapter import AmplihackLearningAgentAdapter

        mock_instance = MagicMock()
        mock_agent_cls.return_value = mock_instance

        adapter = AmplihackLearningAgentAdapter(agent_name="test")
        adapter.reset()

        mock_instance.close.assert_called_once()
        # Should have been called twice: once in __init__, once in reset()
        assert mock_agent_cls.call_count == 2

    @patch("amplihack.agents.goal_seeking.learning_agent.LearningAgent")
    def test_implements_agent_adapter(self, mock_agent_cls):
        """Adapter should be a valid AgentAdapter subclass."""
        from amplihack_eval.adapters.base import AgentAdapter

        from amplihack.eval.agent_adapter import AmplihackLearningAgentAdapter

        adapter = AmplihackLearningAgentAdapter(agent_name="test")
        assert isinstance(adapter, AgentAdapter)


# ===========================================================================
# Test 3: AmplihackMultiAgentAdapter
# ===========================================================================


class TestAmplihackMultiAgentAdapter:
    """Test AmplihackMultiAgentAdapter wraps MultiAgentLearningAgent correctly."""

    @patch(
        "amplihack.agents.goal_seeking.sub_agents.multi_agent.MultiAgentLearningAgent"
    )
    def test_init_creates_agent_with_hierarchical(self, mock_agent_cls):
        """Constructor should pass use_hierarchical=True."""
        from amplihack.eval.agent_adapter import AmplihackMultiAgentAdapter

        adapter = AmplihackMultiAgentAdapter(agent_name="multi-test")
        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["use_hierarchical"] is True
        assert adapter.name == "AmplihackMultiAgent(multi-test)"

    @patch(
        "amplihack.agents.goal_seeking.sub_agents.multi_agent.MultiAgentLearningAgent"
    )
    def test_capabilities_include_multi_agent(self, mock_agent_cls):
        """Capabilities should include 'multi_agent'."""
        from amplihack.eval.agent_adapter import AmplihackMultiAgentAdapter

        adapter = AmplihackMultiAgentAdapter(agent_name="test")
        assert "multi_agent" in adapter.capabilities
        assert "memory" in adapter.capabilities

    @patch(
        "amplihack.agents.goal_seeking.sub_agents.multi_agent.MultiAgentLearningAgent"
    )
    def test_learn_delegates(self, mock_agent_cls):
        """learn() should delegate to learn_from_content()."""
        from amplihack.eval.agent_adapter import AmplihackMultiAgentAdapter

        mock_instance = MagicMock()
        mock_agent_cls.return_value = mock_instance

        adapter = AmplihackMultiAgentAdapter(agent_name="test")
        adapter.learn("Some facts.")

        mock_instance.learn_from_content.assert_called_once_with("Some facts.")

    @patch(
        "amplihack.agents.goal_seeking.sub_agents.multi_agent.MultiAgentLearningAgent"
    )
    def test_implements_agent_adapter(self, mock_agent_cls):
        """Adapter should be a valid AgentAdapter subclass."""
        from amplihack_eval.adapters.base import AgentAdapter

        from amplihack.eval.agent_adapter import AmplihackMultiAgentAdapter

        adapter = AmplihackMultiAgentAdapter(agent_name="test")
        assert isinstance(adapter, AgentAdapter)


# ===========================================================================
# Test 4: AmplihackSDKAgentAdapter
# ===========================================================================


class TestAmplihackSDKAgentAdapter:
    """Test AmplihackSDKAgentAdapter wraps SDK agents correctly."""

    @patch("amplihack.agents.goal_seeking.sdk_adapters.factory.create_agent")
    def test_init_creates_agent_with_sdk(self, mock_create):
        """Constructor should call create_agent with correct SDK."""
        from amplihack.eval.agent_adapter import AmplihackSDKAgentAdapter

        adapter = AmplihackSDKAgentAdapter(agent_name="sdk-test", sdk="mini")
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["sdk"] == "mini"
        assert call_kwargs["name"] == "sdk-test"
        assert adapter.name == "AmplihackSDK(mini/sdk-test)"

    @patch("amplihack.agents.goal_seeking.sdk_adapters.factory.create_agent")
    def test_capabilities_vary_by_sdk(self, mock_create):
        """mini SDK should only have 'memory'; others should have 'tool_use' too."""
        from amplihack.eval.agent_adapter import AmplihackSDKAgentAdapter

        mini_adapter = AmplihackSDKAgentAdapter(sdk="mini")
        assert mini_adapter.capabilities == {"memory"}

        claude_adapter = AmplihackSDKAgentAdapter(sdk="claude")
        assert "tool_use" in claude_adapter.capabilities

    @patch("amplihack.agents.goal_seeking.sdk_adapters.factory.create_agent")
    def test_close_delegates(self, mock_create):
        """close() should call the underlying agent's close()."""
        from amplihack.eval.agent_adapter import AmplihackSDKAgentAdapter

        mock_agent = MagicMock()
        mock_create.return_value = mock_agent

        adapter = AmplihackSDKAgentAdapter(sdk="mini")
        adapter.close()

        mock_agent.close.assert_called_once()

    @patch("amplihack.agents.goal_seeking.sdk_adapters.factory.create_agent")
    def test_reset_recreates_agent(self, mock_create):
        """reset() should close and re-create the SDK agent."""
        from amplihack.eval.agent_adapter import AmplihackSDKAgentAdapter

        mock_agent = MagicMock()
        mock_create.return_value = mock_agent

        adapter = AmplihackSDKAgentAdapter(sdk="mini")
        adapter.reset()

        mock_agent.close.assert_called_once()
        assert mock_create.call_count == 2  # init + reset

    @patch("amplihack.agents.goal_seeking.sdk_adapters.factory.create_agent")
    def test_implements_agent_adapter(self, mock_create):
        """Adapter should be a valid AgentAdapter subclass."""
        from amplihack_eval.adapters.base import AgentAdapter

        from amplihack.eval.agent_adapter import AmplihackSDKAgentAdapter

        adapter = AmplihackSDKAgentAdapter(sdk="mini")
        assert isinstance(adapter, AgentAdapter)

    @pytest.mark.parametrize("sdk_type", ["mini", "claude", "copilot", "microsoft"])
    @patch("amplihack.agents.goal_seeking.sdk_adapters.factory.create_agent")
    def test_all_sdk_types_accepted(self, mock_create, sdk_type):
        """All SDK types should be passable to the adapter."""
        from amplihack.eval.agent_adapter import AmplihackSDKAgentAdapter

        adapter = AmplihackSDKAgentAdapter(sdk=sdk_type)
        assert sdk_type in adapter.name


# ===========================================================================
# Test 5: Integration - existing eval code still works
# ===========================================================================


class TestExistingEvalCode:
    """Verify that existing amplihack eval code is not broken."""

    def test_long_horizon_data_generation(self):
        """generate_dialogue and generate_questions should still work via compat."""
        from amplihack.eval.compat import generate_dialogue, generate_questions

        gt = generate_dialogue(num_turns=10, seed=42)
        assert len(gt.turns) == 10

        questions = generate_questions(gt, num_questions=3)
        assert len(questions) == 3
        assert all(q.text for q in questions)

    def test_eval_runner_can_be_instantiated(self):
        """EvalRunner should be instantiable via compat."""
        from amplihack.eval.compat import EvalRunner

        runner = EvalRunner(num_turns=10, num_questions=5, seed=42)
        assert runner.num_turns == 10
        assert runner.num_questions == 5

    def test_eval_runner_generate(self):
        """EvalRunner.generate() should produce data."""
        from amplihack.eval.compat import EvalRunner

        runner = EvalRunner(num_turns=10, num_questions=5, seed=42)
        gt, questions = runner.generate()
        assert len(gt.turns) == 10
        assert len(questions) == 5

    def test_tool_call_dataclass(self):
        """ToolCall should be a working dataclass."""
        from amplihack.eval.compat import ToolCall

        tc = ToolCall(tool_name="search", arguments={"q": "test"}, result="found")
        assert tc.tool_name == "search"
        assert tc.arguments == {"q": "test"}

    def test_agent_response_dataclass(self):
        """AgentResponse should be a working dataclass."""
        from amplihack.eval.compat import AgentResponse

        resp = AgentResponse(answer="Blue", reasoning_trace="Color recall")
        assert resp.answer == "Blue"
        assert resp.confidence == 0.0  # default
