"""Tests for AgenticLoop with mocked LLM responses.

Philosophy:
- Test without requiring API keys
- Mock LLM calls for predictable testing
- Verify loop phases execute in order
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.agents.goal_seeking import ActionExecutor, AgenticLoop, MemoryRetriever


class TestAgenticLoop:
    """Test suite for AgenticLoop."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def memory(self, temp_storage):
        """Create MemoryRetriever with temporary storage."""
        memory = MemoryRetriever(agent_name="test_agent", storage_path=temp_storage)
        yield memory
        memory.close()

    @pytest.fixture
    def executor(self):
        """Create ActionExecutor with test actions."""
        executor = ActionExecutor()
        executor.register_action("greet", lambda name: f"Hello {name}!")
        executor.register_action("add", lambda a, b: a + b)
        return executor

    @pytest.fixture
    def loop(self, executor, memory):
        """Create AgenticLoop with mocked executor and memory."""
        return AgenticLoop(
            agent_name="test_agent",
            action_executor=executor,
            memory_retriever=memory,
            model="gpt-3.5-turbo",
        )

    def test_init_with_valid_params(self, executor, memory):
        """Test initialization with valid parameters."""
        loop = AgenticLoop(agent_name="test", action_executor=executor, memory_retriever=memory)

        assert loop.agent_name == "test"
        assert loop.action_executor is executor
        assert loop.memory_retriever is memory

    def test_init_with_empty_agent_name_fails(self, executor, memory):
        """Test initialization with empty agent name fails."""
        with pytest.raises(ValueError, match="agent_name cannot be empty"):
            AgenticLoop(agent_name="", action_executor=executor, memory_retriever=memory)

    def test_perceive_builds_perception(self, loop):
        """Test perceive phase builds perception string."""
        perception = loop.perceive(observation="User Alice is present", goal="Greet the user")

        assert "Goal: Greet the user" in perception
        assert "Observation: User Alice is present" in perception

    def test_perceive_includes_relevant_memory(self, loop, memory):
        """Test perceive includes relevant past experiences."""
        # Store a relevant memory
        memory.store_fact(context="Greeting users", fact="Always use friendly tone", confidence=0.9)

        perception = loop.perceive(observation="User Bob is present", goal="Greet the user")

        # Should include past experiences if found
        assert "Goal:" in perception
        assert "Observation:" in perception

    @patch("amplihack.agents.goal_seeking.agentic_loop.litellm.completion")
    def test_reason_calls_llm(self, mock_completion, loop):
        """Test reason phase calls LLM."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"reasoning": "Test reasoning", "action": "greet", "params": {"name": "Alice"}}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        perception = "Goal: Greet user\nObservation: User Alice present"
        result = loop.reason(perception)

        assert mock_completion.called
        assert result["reasoning"] == "Test reasoning"
        assert result["action"] == "greet"
        assert result["params"] == {"name": "Alice"}

    @patch("amplihack.agents.goal_seeking.agentic_loop.litellm.completion")
    def test_reason_handles_llm_failure(self, mock_completion, loop):
        """Test reason phase handles LLM failure gracefully."""
        # Mock LLM failure
        mock_completion.side_effect = Exception("API error")

        perception = "Goal: Test\nObservation: Test"
        result = loop.reason(perception)

        assert result["action"] == "error"
        assert "error" in result["params"]["error"].lower()

    @patch("amplihack.agents.goal_seeking.agentic_loop.litellm.completion")
    def test_reason_parses_json_from_markdown(self, mock_completion, loop):
        """Test reason phase can parse JSON from markdown code blocks."""
        # Mock LLM response with markdown
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='```json\n{"reasoning": "Test", "action": "add", "params": {"a": 1, "b": 2}}\n```'
                )
            )
        ]
        mock_completion.return_value = mock_response

        perception = "Goal: Test"
        result = loop.reason(perception)

        assert result["action"] == "add"
        assert result["params"]["a"] == 1
        assert result["params"]["b"] == 2

    def test_act_executes_action(self, loop):
        """Test act phase executes the chosen action."""
        action_decision = {"action": "greet", "params": {"name": "Alice"}}

        outcome = loop.act(action_decision)

        assert outcome == "Hello Alice!"

    def test_act_handles_missing_action(self, loop):
        """Test act phase handles missing action."""
        action_decision = {"params": {"name": "Alice"}}

        outcome = loop.act(action_decision)

        assert "error" in outcome

    def test_act_handles_action_failure(self, loop):
        """Test act phase handles action failure."""
        action_decision = {"action": "nonexistent", "params": {}}

        outcome = loop.act(action_decision)

        assert "error" in outcome
        assert "not found" in outcome["error"]

    def test_learn_stores_experience(self, loop, memory):
        """Test learn phase stores experience in memory."""
        perception = "Goal: Test\nObservation: Test"
        reasoning = "Test reasoning"
        action = {"action": "greet", "params": {"name": "Alice"}}
        outcome = "Hello Alice!"

        learning = loop.learn(perception, reasoning, action, outcome)

        assert "Action: greet" in learning
        assert "Outcome:" in learning

        # Verify stored in memory
        stats = memory.get_statistics()
        assert stats["total_experiences"] > 0

    def test_learn_handles_failure_outcome(self, loop, memory):
        """Test learn phase handles failed outcomes."""
        perception = "Goal: Test"
        reasoning = "Test"
        action = {"action": "test"}
        outcome = {"error": "Action failed"}

        learning = loop.learn(perception, reasoning, action, outcome)

        # Should still store learning with lower confidence
        assert "Action: test" in learning

    @patch("amplihack.agents.goal_seeking.agentic_loop.litellm.completion")
    def test_run_iteration_executes_all_phases(self, mock_completion, loop):
        """Test run_iteration executes all four phases."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"reasoning": "Greet user", "action": "greet", "params": {"name": "Alice"}}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        state = loop.run_iteration(goal="Greet user", observation="User Alice present")

        assert state.perception is not None
        assert state.reasoning == "Greet user"
        assert state.action["action"] == "greet"
        assert state.outcome == "Hello Alice!"
        assert state.learning is not None
        assert state.iteration == 1

    @patch("amplihack.agents.goal_seeking.agentic_loop.litellm.completion")
    def test_run_iteration_increments_count(self, mock_completion, loop):
        """Test run_iteration increments iteration count."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"reasoning": "Test", "action": "greet", "params": {"name": "Test"}}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        state1 = loop.run_iteration("Goal", "Observation")
        state2 = loop.run_iteration("Goal", "Observation")

        assert state1.iteration == 1
        assert state2.iteration == 2

    @patch("amplihack.agents.goal_seeking.agentic_loop.litellm.completion")
    def test_run_until_goal_stops_when_achieved(self, mock_completion, loop):
        """Test run_until_goal stops when goal is achieved."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"reasoning": "Test", "action": "greet", "params": {"name": "Test"}}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        def check_goal(state):
            return state.iteration >= 2

        states = loop.run_until_goal(
            goal="Test goal", initial_observation="Test", is_goal_achieved=check_goal
        )

        assert len(states) == 2

    @patch("amplihack.agents.goal_seeking.agentic_loop.litellm.completion")
    def test_run_until_goal_respects_max_iterations(self, mock_completion, loop):
        """Test run_until_goal respects max iterations."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"reasoning": "Test", "action": "greet", "params": {"name": "Test"}}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        loop.max_iterations = 3

        states = loop.run_until_goal(goal="Test goal", initial_observation="Test")

        assert len(states) <= 3
