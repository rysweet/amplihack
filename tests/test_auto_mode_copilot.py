"""Tests for enhanced Copilot auto mode.

Philosophy:
- Test contracts, not implementation
- 60% unit tests, 30% integration, 10% E2E
- Fast execution with mocking
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplihack.copilot.session_manager import (
    CopilotSessionManager,
    SessionRegistry,
    SessionState,
)
from amplihack.launcher.auto_mode_copilot import (
    CopilotAgentLibrary,
    CopilotAutoMode,
)


# Unit Tests (60%)


class TestAgentLibrary:
    """Test agent library and selection logic."""

    def test_get_architect_agent(self):
        """Architect agent has correct role and tools."""
        agent = CopilotAgentLibrary.get_architect_agent()
        assert agent.name == "architect"
        assert "design" in agent.role.lower()
        assert "Read" in agent.tools
        assert "PHILOSOPHY" in agent.system_prompt

    def test_get_builder_agent(self):
        """Builder agent has correct role and tools."""
        agent = CopilotAgentLibrary.get_builder_agent()
        assert agent.name == "builder"
        assert "implementation" in agent.role.lower()
        assert "Edit" in agent.tools
        assert "zero-BS" in agent.system_prompt

    def test_get_tester_agent(self):
        """Tester agent has correct role and tools."""
        agent = CopilotAgentLibrary.get_tester_agent()
        assert agent.name == "tester"
        assert "test" in agent.role.lower()
        assert "Bash" in agent.tools

    def test_get_reviewer_agent(self):
        """Reviewer agent has correct role and tools."""
        agent = CopilotAgentLibrary.get_reviewer_agent()
        assert agent.name == "reviewer"
        assert "review" in agent.role.lower()
        assert "Grep" in agent.tools

    def test_select_agents_for_feature(self):
        """Feature tasks select architect, builder, tester."""
        agents = CopilotAgentLibrary.select_agents("feature")
        names = [a.name for a in agents]
        assert "architect" in names
        assert "builder" in names
        assert "tester" in names

    def test_select_agents_for_bug(self):
        """Bug tasks select builder and tester."""
        agents = CopilotAgentLibrary.select_agents("bug")
        names = [a.name for a in agents]
        assert "builder" in names
        assert "tester" in names
        assert len(agents) == 2

    def test_select_agents_for_refactor(self):
        """Refactor tasks select architect, builder, reviewer."""
        agents = CopilotAgentLibrary.select_agents("refactor")
        names = [a.name for a in agents]
        assert "architect" in names
        assert "builder" in names
        assert "reviewer" in names

    def test_select_agents_for_test(self):
        """Test tasks select only tester."""
        agents = CopilotAgentLibrary.select_agents("test")
        names = [a.name for a in agents]
        assert "tester" in names
        assert len(agents) == 1

    def test_select_agents_default(self):
        """Unknown task types select all agents."""
        agents = CopilotAgentLibrary.select_agents("unknown")
        names = [a.name for a in agents]
        assert len(names) == 4
        assert "architect" in names
        assert "builder" in names
        assert "tester" in names
        assert "reviewer" in names


class TestSessionState:
    """Test session state data structure."""

    def test_session_state_defaults(self):
        """Session state has correct defaults."""
        state = SessionState(session_id="test_123")
        assert state.session_id == "test_123"
        assert state.fork_count == 0
        assert state.phase == "init"
        assert isinstance(state.context, dict)


class TestCopilotSessionManager:
    """Test session manager functionality."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temp directory for tests."""
        return tmp_path

    @pytest.fixture
    def session_manager(self, temp_dir):
        """Create session manager for tests."""
        return CopilotSessionManager(temp_dir, "test_session_123")

    def test_init_creates_state_file(self, session_manager, temp_dir):
        """Session manager creates state file on init."""
        state_file = temp_dir / ".claude" / "runtime" / "copilot_sessions" / "test_session_123.json"
        assert state_file.exists()

    def test_should_fork_initially_false(self, session_manager):
        """Newly created session should not fork."""
        assert not session_manager.should_fork()

    def test_should_fork_after_threshold(self, session_manager):
        """Session should fork after threshold exceeded."""
        # Set fork threshold to 0 seconds
        session_manager.fork_threshold = 0
        assert session_manager.should_fork()

    def test_fork_session_increments_count(self, session_manager):
        """Forking session increments fork count."""
        initial_count = session_manager.state.fork_count
        fork_id = session_manager.fork_session({"key": "value"})
        assert session_manager.state.fork_count == initial_count + 1
        assert "fork1" in fork_id

    def test_fork_session_creates_state_file(self, session_manager, temp_dir):
        """Forking creates state file for new session."""
        fork_id = session_manager.fork_session({"test": "data"})
        fork_state_file = temp_dir / ".claude" / "runtime" / "copilot_sessions" / f"{fork_id}.json"
        assert fork_state_file.exists()

    def test_update_phase(self, session_manager):
        """Updating phase saves to state."""
        session_manager.update_phase("executing")
        assert session_manager.state.phase == "executing"

    def test_increment_turn(self, session_manager):
        """Incrementing turn updates state."""
        initial_turns = session_manager.state.total_turns
        session_manager.increment_turn()
        assert session_manager.state.total_turns == initial_turns + 1

    def test_update_context(self, session_manager):
        """Updating context saves to state."""
        session_manager.update_context("plan", "Test plan")
        assert session_manager.get_context("plan") == "Test plan"

    def test_get_context_with_default(self, session_manager):
        """Getting missing context returns default."""
        assert session_manager.get_context("missing", "default") == "default"

    def test_get_state_returns_dict(self, session_manager):
        """Get state returns dictionary with all fields."""
        state = session_manager.get_state()
        assert isinstance(state, dict)
        assert "session_id" in state
        assert "fork_count" in state
        assert "phase" in state
        assert "elapsed_seconds" in state

    def test_build_continuation_prompt(self, session_manager):
        """Build continuation prompt includes context."""
        session_manager.update_context("objective", "Test objective")
        session_manager.fork_session({"objective": "Test objective"})
        prompt = session_manager.build_continuation_prompt()
        assert "test_session_123" in prompt
        assert "objective" in prompt.lower()


class TestSessionRegistry:
    """Test session registry functionality."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temp directory for tests."""
        return tmp_path

    @pytest.fixture
    def registry(self, temp_dir):
        """Create registry for tests."""
        return SessionRegistry(temp_dir)

    def test_register_session(self, registry):
        """Registering session adds to registry."""
        registry.register_session("session_1", {"task": "test"})
        session = registry.get_session("session_1")
        assert session is not None
        assert session["metadata"]["task"] == "test"

    def test_get_nonexistent_session(self, registry):
        """Getting nonexistent session returns None."""
        assert registry.get_session("nonexistent") is None

    def test_list_sessions(self, registry):
        """List sessions returns all registered sessions."""
        registry.register_session("session_1", {"task": "test1"})
        registry.register_session("session_2", {"task": "test2"})
        sessions = registry.list_sessions()
        assert len(sessions) >= 2
        session_ids = [s["session_id"] for s in sessions]
        assert "session_1" in session_ids
        assert "session_2" in session_ids


# Integration Tests (30%)


class TestCopilotAutoModeIntegration:
    """Integration tests for auto mode."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temp directory for tests."""
        return tmp_path

    @pytest.fixture
    def auto_mode(self, temp_dir):
        """Create auto mode instance for tests."""
        return CopilotAutoMode(
            prompt="Test prompt",
            max_turns=3,
            working_dir=temp_dir,
            task_type="feature",
        )

    def test_auto_mode_init(self, auto_mode, temp_dir):
        """Auto mode initializes correctly."""
        assert auto_mode.prompt == "Test prompt"
        assert auto_mode.max_turns == 3
        assert auto_mode.task_type == "feature"
        assert len(auto_mode.agents) > 0

    def test_auto_mode_creates_log_dir(self, auto_mode):
        """Auto mode creates log directory."""
        assert auto_mode.log_dir.exists()

    def test_auto_mode_writes_prompt_file(self, auto_mode):
        """Auto mode writes prompt to file."""
        prompt_file = auto_mode.log_dir / "prompt.md"
        assert prompt_file.exists()
        content = prompt_file.read_text()
        assert "Test prompt" in content

    def test_build_agent_prompt(self, auto_mode):
        """Building agent prompt includes system context."""
        agent = CopilotAgentLibrary.get_builder_agent()
        prompt = auto_mode._build_agent_prompt(agent, "Implement feature X")
        assert agent.name in prompt
        assert agent.role in prompt
        assert "Implement feature X" in prompt

    @pytest.mark.asyncio
    async def test_fork_if_needed_below_threshold(self, auto_mode):
        """Fork not triggered below threshold."""
        initial_fork_count = auto_mode.session_manager.get_fork_count()
        await auto_mode._fork_if_needed("test context")
        assert auto_mode.session_manager.get_fork_count() == initial_fork_count

    @pytest.mark.asyncio
    async def test_fork_if_needed_above_threshold(self, auto_mode):
        """Fork triggered when threshold exceeded."""
        # Set threshold to 0 to trigger immediate fork
        auto_mode.session_manager.fork_threshold = 0
        initial_fork_count = auto_mode.session_manager.get_fork_count()
        await auto_mode._fork_if_needed("test context")
        assert auto_mode.session_manager.get_fork_count() == initial_fork_count + 1


# E2E Tests (10%)


class TestCopilotAutoModeEndToEnd:
    """End-to-end tests for auto mode."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temp directory for tests."""
        return tmp_path

    @pytest.mark.asyncio
    async def test_run_copilot_command_mocked(self, temp_dir):
        """Run Copilot command with mocked subprocess."""
        auto_mode = CopilotAutoMode(
            prompt="Test task",
            max_turns=2,
            working_dir=temp_dir,
        )

        # Mock subprocess to avoid actual Copilot CLI calls
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_process = MagicMock()
            mock_process.communicate = AsyncMock(
                return_value=(b"Test output", b"")
            )
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            code, output = await auto_mode._run_copilot_command("Test prompt")

            assert code == 0
            assert output == "Test output"
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_workflow_mocked(self, temp_dir):
        """Test full auto mode workflow with mocked Copilot."""
        auto_mode = CopilotAutoMode(
            prompt="Simple test task",
            max_turns=3,
            working_dir=temp_dir,
        )

        # Mock all Copilot commands
        call_count = 0

        async def mock_run_command(prompt, agent=None):
            nonlocal call_count
            call_count += 1

            # Simulate responses for each phase
            if call_count == 1:  # Clarify
                return (0, "Objective: Test task clarified")
            elif call_count == 2:  # Plan
                return (0, "Plan: Step 1, Step 2, Step 3")
            elif call_count == 3:  # Execute
                return (0, "Execution: Completed step 1")
            elif call_count == 4:  # Evaluate
                return (0, "COMPLETE - All criteria met")
            else:  # Summary
                return (0, "Summary: Task completed successfully")

        auto_mode._run_copilot_command = mock_run_command

        # Run auto mode
        exit_code = await auto_mode.run()

        assert exit_code == 0
        assert call_count >= 4  # At least clarify, plan, execute, evaluate


# Test fixtures and helpers


@pytest.fixture
def mock_copilot_cli():
    """Mock Copilot CLI availability."""
    with patch("shutil.which", return_value="/usr/bin/copilot"):
        yield


__all__ = [
    "TestAgentLibrary",
    "TestSessionState",
    "TestCopilotSessionManager",
    "TestSessionRegistry",
    "TestCopilotAutoModeIntegration",
    "TestCopilotAutoModeEndToEnd",
]
