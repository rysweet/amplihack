"""Tests for hook strategies.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from amplihack.hooks.strategies.base import HookStrategy
from amplihack.hooks.strategies.claude_strategy import ClaudeStrategy
from amplihack.hooks.strategies.copilot_strategy import CopilotStrategy

# ============================================================================
# UNIT TESTS (60%)
# ============================================================================


class TestHookStrategyBase:
    """Unit tests for HookStrategy abstract base class."""

    def test_get_launcher_name_from_class_name(self):
        """Test default launcher name extraction."""
        strategy = ClaudeStrategy()
        assert strategy.get_launcher_name() == "claude"

        strategy = CopilotStrategy()
        assert strategy.get_launcher_name() == "copilot"

    def test_abstract_methods_must_be_implemented(self):
        """Test that abstract methods must be implemented."""
        # Attempting to instantiate abstract class should fail
        with pytest.raises(TypeError):
            HookStrategy()

    def test_concrete_strategy_implements_abstract_methods(self):
        """Test that concrete strategies implement all abstract methods."""
        strategy = ClaudeStrategy()
        assert hasattr(strategy, "inject_context")
        assert hasattr(strategy, "power_steer")
        assert callable(strategy.inject_context)
        assert callable(strategy.power_steer)


class TestClaudeStrategy:
    """Unit tests for ClaudeStrategy."""

    def test_inject_context_returns_correct_structure(self):
        """Test that inject_context returns Claude-specific structure."""
        strategy = ClaudeStrategy()
        context = "# Test Context\n\nThis is test context."

        result = strategy.inject_context(context)

        assert "hookSpecificOutput" in result
        assert "additionalContext" in result["hookSpecificOutput"]
        assert result["hookSpecificOutput"]["additionalContext"] == context

    def test_inject_context_handles_empty_context(self):
        """Test inject_context with empty string."""
        strategy = ClaudeStrategy()
        result = strategy.inject_context("")

        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["additionalContext"] == ""

    def test_inject_context_handles_multiline_context(self):
        """Test inject_context with multiline markdown."""
        strategy = ClaudeStrategy()
        context = """# Header

## Subheader

- Bullet 1
- Bullet 2

```python
code here
```
"""
        result = strategy.inject_context(context)
        assert result["hookSpecificOutput"]["additionalContext"] == context

    def test_power_steer_returns_true(self):
        """Test that power_steer returns True for Claude."""
        strategy = ClaudeStrategy()
        result = strategy.power_steer("test prompt")
        assert result is True

    def test_power_steer_ignores_session_id(self):
        """Test that power_steer ignores session_id parameter."""
        strategy = ClaudeStrategy()
        result = strategy.power_steer("test prompt", session_id="ignored")
        assert result is True

    def test_get_launcher_name(self):
        """Test launcher name for Claude."""
        strategy = ClaudeStrategy()
        assert strategy.get_launcher_name() == "claude"


class TestCopilotStrategy:
    """Unit tests for CopilotStrategy."""

    def test_inject_context_returns_empty_dict(self):
        """Test that inject_context returns empty dict (file-based)."""
        strategy = CopilotStrategy()

        with patch.object(strategy, "_write_with_retry"):
            with patch.object(strategy, "_update_agents_file"):
                result = strategy.inject_context("test context")
                assert result == {}

    def test_inject_context_writes_dynamic_context_file(self, tmp_path):
        """Test that inject_context writes to dynamic context file."""
        strategy = CopilotStrategy()
        context = "# Test Context\n\nDynamic content here."

        context_file = tmp_path / "dynamic_context.md"

        with patch.object(CopilotStrategy, "CONTEXT_DIR", tmp_path):
            with patch.object(CopilotStrategy, "DYNAMIC_CONTEXT_FILE", context_file):
                with patch.object(strategy, "_update_agents_file"):
                    strategy.inject_context(context)

                    assert context_file.exists()
                    assert context_file.read_text() == context

    def test_inject_context_creates_directories(self, tmp_path):
        """Test that inject_context creates necessary directories."""
        strategy = CopilotStrategy()

        context_dir = tmp_path / "runtime" / "copilot"
        agents_dir = tmp_path / ".github" / "agents"
        context_file = context_dir / "dynamic_context.md"
        agents_file = agents_dir / "AGENTS.md"

        with patch.object(CopilotStrategy, "CONTEXT_DIR", context_dir):
            with patch.object(CopilotStrategy, "DYNAMIC_CONTEXT_FILE", context_file):
                with patch.object(CopilotStrategy, "AGENTS_FILE", agents_file):
                    strategy.inject_context("test")

                    assert context_dir.exists()
                    assert agents_dir.exists()

    def test_power_steer_checks_gh_availability(self):
        """Test that power_steer checks for gh CLI."""
        strategy = CopilotStrategy()

        with patch("shutil.which", return_value=None):
            result = strategy.power_steer("test prompt")
            assert result is False

    def test_power_steer_spawns_subprocess_with_gh(self):
        """Test that power_steer spawns correct subprocess."""
        strategy = CopilotStrategy()

        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.Popen") as mock_popen:
                result = strategy.power_steer("test prompt", session_id="test-session")

                assert result is True
                mock_popen.assert_called_once()

                # Check command arguments
                call_args = mock_popen.call_args
                cmd = call_args[0][0]
                assert cmd[0] == "gh"
                assert cmd[1] == "copilot"
                assert "--continue" in cmd
                assert "test-session" in cmd
                assert "-p" in cmd
                assert "test prompt" in cmd

    def test_power_steer_without_session_id(self):
        """Test power_steer without session ID."""
        strategy = CopilotStrategy()

        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.Popen") as mock_popen:
                result = strategy.power_steer("test prompt")

                assert result is True
                cmd = mock_popen.call_args[0][0]
                assert "--continue" not in cmd
                assert "-p" in cmd

    def test_power_steer_handles_subprocess_error(self):
        """Test power_steer handles subprocess failures gracefully."""
        strategy = CopilotStrategy()

        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.Popen", side_effect=OSError("Failed to spawn")):
                result = strategy.power_steer("test prompt")
                assert result is False

    def test_get_launcher_name(self):
        """Test launcher name for Copilot."""
        strategy = CopilotStrategy()
        assert strategy.get_launcher_name() == "copilot"


class TestCopilotAgentsFileUpdate:
    """Unit tests for AGENTS.md file management."""

    def test_update_agents_file_creates_new_file(self, tmp_path):
        """Test creating AGENTS.md from scratch."""
        strategy = CopilotStrategy()
        agents_file = tmp_path / "AGENTS.md"

        with patch.object(CopilotStrategy, "AGENTS_FILE", agents_file):
            with patch.object(
                CopilotStrategy, "DYNAMIC_CONTEXT_FILE", Path("runtime/copilot/dynamic_context.md")
            ):
                strategy._update_agents_file()

                assert agents_file.exists()
                content = agents_file.read_text()
                assert "GitHub Copilot Agents Context" in content
                assert "@include" in content
                assert "dynamic_context.md" in content

    def test_update_agents_file_appends_to_existing(self, tmp_path):
        """Test appending to existing AGENTS.md."""
        strategy = CopilotStrategy()
        agents_file = tmp_path / "AGENTS.md"
        agents_file.write_text("# Existing Content\n\nSome stuff here.\n")

        with patch.object(CopilotStrategy, "AGENTS_FILE", agents_file):
            with patch.object(
                CopilotStrategy, "DYNAMIC_CONTEXT_FILE", Path("runtime/copilot/dynamic_context.md")
            ):
                strategy._update_agents_file()

                content = agents_file.read_text()
                assert "Existing Content" in content
                assert "Some stuff here" in content
                assert "@include" in content

    def test_update_agents_file_skips_if_already_present(self, tmp_path):
        """Test that update is skipped if @include already present."""
        strategy = CopilotStrategy()
        agents_file = tmp_path / "AGENTS.md"

        include_line = "@include runtime/copilot/dynamic_context.md"
        agents_file.write_text(f"# Content\n\n{include_line}\n")
        original_content = agents_file.read_text()

        with patch.object(CopilotStrategy, "AGENTS_FILE", agents_file):
            with patch.object(
                CopilotStrategy, "DYNAMIC_CONTEXT_FILE", Path("runtime/copilot/dynamic_context.md")
            ):
                strategy._update_agents_file()

                # Content should be unchanged
                assert agents_file.read_text() == original_content


# ============================================================================
# INTEGRATION TESTS (30%)
# ============================================================================


class TestClaudeStrategyIntegration:
    """Integration tests for ClaudeStrategy."""

    def test_complete_context_injection_flow(self):
        """Test complete Claude context injection."""
        strategy = ClaudeStrategy()
        context = """# Session Context

## Current Task
Implementing adaptive hooks

## Key Points
- Detect launcher type
- Inject context appropriately
"""
        result = strategy.inject_context(context)

        # Verify structure
        assert "hookSpecificOutput" in result
        assert "additionalContext" in result["hookSpecificOutput"]

        # Verify content preserved
        injected = result["hookSpecificOutput"]["additionalContext"]
        assert "Session Context" in injected
        assert "Current Task" in injected
        assert "Implementing adaptive hooks" in injected

    def test_complete_power_steering_flow(self):
        """Test complete Claude power steering."""
        strategy = ClaudeStrategy()
        prompt = "Continue with implementation of feature X"

        result = strategy.power_steer(prompt, session_id="test-123")

        assert result is True
        # For Claude, steering is handled by hook return value


class TestCopilotStrategyIntegration:
    """Integration tests for CopilotStrategy."""

    def test_complete_context_injection_flow(self, tmp_path):
        """Test complete Copilot context injection."""
        strategy = CopilotStrategy()

        context_dir = tmp_path / "runtime" / "copilot"
        context_file = context_dir / "dynamic_context.md"
        agents_file = tmp_path / ".github" / "agents" / "AGENTS.md"

        with patch.object(CopilotStrategy, "CONTEXT_DIR", context_dir):
            with patch.object(CopilotStrategy, "DYNAMIC_CONTEXT_FILE", context_file):
                with patch.object(CopilotStrategy, "AGENTS_FILE", agents_file):
                    context = "# Dynamic Context\n\nTest content."
                    result = strategy.inject_context(context)

                    # Should return empty dict
                    assert result == {}

                    # Should write context file
                    assert context_file.exists()
                    assert context_file.read_text() == context

                    # Should update AGENTS.md
                    assert agents_file.exists()
                    agents_content = agents_file.read_text()
                    assert "@include" in agents_content

    def test_complete_power_steering_flow(self):
        """Test complete Copilot power steering."""
        strategy = CopilotStrategy()

        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.Popen") as mock_popen:
                result = strategy.power_steer("Implement feature Y", session_id="session-456")

                assert result is True

                # Verify subprocess call
                assert mock_popen.called
                cmd = mock_popen.call_args[0][0]
                assert "gh" in cmd
                assert "copilot" in cmd
                assert "Implement feature Y" in cmd
                assert "session-456" in cmd


# ============================================================================
# E2E TESTS (10%)
# ============================================================================


class TestStrategyEndToEnd:
    """End-to-end tests for strategy workflows."""

    def test_claude_complete_workflow(self):
        """Test Claude strategy from context injection to power steering."""
        strategy = ClaudeStrategy()

        # Step 1: Inject context
        context = "# Task: Implement adaptive hooks\n\nFollow these steps..."
        inject_result = strategy.inject_context(context)

        assert "hookSpecificOutput" in inject_result
        assert inject_result["hookSpecificOutput"]["additionalContext"] == context

        # Step 2: Power steer
        prompt = "Continue with next step in workflow"
        steer_result = strategy.power_steer(prompt)

        assert steer_result is True

    def test_copilot_complete_workflow(self, tmp_path):
        """Test Copilot strategy from context injection to power steering."""
        strategy = CopilotStrategy()

        context_dir = tmp_path / "runtime" / "copilot"
        context_file = context_dir / "dynamic_context.md"
        agents_file = tmp_path / ".github" / "agents" / "AGENTS.md"

        with patch.object(CopilotStrategy, "CONTEXT_DIR", context_dir):
            with patch.object(CopilotStrategy, "DYNAMIC_CONTEXT_FILE", context_file):
                with patch.object(CopilotStrategy, "AGENTS_FILE", agents_file):
                    # Step 1: Inject context
                    context = "# Task Context\n\nImplement feature Z"
                    inject_result = strategy.inject_context(context)

                    assert inject_result == {}
                    assert context_file.exists()
                    assert agents_file.exists()

                    # Step 2: Power steer
                    with patch("shutil.which", return_value="/usr/bin/gh"):
                        with patch("subprocess.Popen") as mock_popen:
                            prompt = "Continue implementation"
                            steer_result = strategy.power_steer(prompt, session_id="test-789")

                            assert steer_result is True
                            assert mock_popen.called


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Create temporary directory for test files."""
    return tmp_path_factory.mktemp("strategy_tests")
