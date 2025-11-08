"""Unit tests for hook configuration function."""

import sys
from pathlib import Path

import pytest

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from amplihack import create_hook_config


class TestCreateHookConfig:
    """Test suite for create_hook_config function."""

    def test_home_claude_path(self):
        """Test hook config with $HOME/.claude base path."""
        config = create_hook_config("$HOME/.claude")

        # Verify all hook types are present
        assert "SessionStart" in config
        assert "Stop" in config
        assert "PostToolUse" in config
        assert "PreCompact" in config

        # Verify SessionStart hook configuration
        assert len(config["SessionStart"]) == 1
        assert "hooks" in config["SessionStart"][0]
        session_hook = config["SessionStart"][0]["hooks"][0]
        assert session_hook["type"] == "command"
        assert session_hook["command"] == "$HOME/.claude/tools/amplihack/hooks/session_start.py"
        assert session_hook["timeout"] == 10000

        # Verify Stop hook configuration
        assert len(config["Stop"]) == 1
        stop_hook = config["Stop"][0]["hooks"][0]
        assert stop_hook["command"] == "$HOME/.claude/tools/amplihack/hooks/stop.py"
        assert stop_hook["timeout"] == 30000

        # Verify PostToolUse hook configuration
        assert len(config["PostToolUse"]) == 1
        assert config["PostToolUse"][0]["matcher"] == "*"
        post_hook = config["PostToolUse"][0]["hooks"][0]
        assert post_hook["command"] == "$HOME/.claude/tools/amplihack/hooks/post_tool_use.py"
        assert "timeout" not in post_hook  # PostToolUse doesn't have timeout

        # Verify PreCompact hook configuration
        assert len(config["PreCompact"]) == 1
        pre_hook = config["PreCompact"][0]["hooks"][0]
        assert pre_hook["command"] == "$HOME/.claude/tools/amplihack/hooks/pre_compact.py"
        assert pre_hook["timeout"] == 30000

    def test_claude_project_dir_path(self):
        """Test hook config with $CLAUDE_PROJECT_DIR/.claude base path."""
        config = create_hook_config("$CLAUDE_PROJECT_DIR/.claude")

        # Verify path substitution works correctly
        session_hook = config["SessionStart"][0]["hooks"][0]
        assert session_hook["command"] == "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/session_start.py"

        stop_hook = config["Stop"][0]["hooks"][0]
        assert stop_hook["command"] == "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/stop.py"

        post_hook = config["PostToolUse"][0]["hooks"][0]
        assert post_hook["command"] == "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/post_tool_use.py"

        pre_hook = config["PreCompact"][0]["hooks"][0]
        assert pre_hook["command"] == "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/pre_compact.py"

    def test_custom_path(self):
        """Test hook config with custom base path."""
        custom_path = "/custom/path/to/hooks"
        config = create_hook_config(custom_path)

        # Verify custom path is used correctly
        session_hook = config["SessionStart"][0]["hooks"][0]
        assert session_hook["command"] == f"{custom_path}/tools/amplihack/hooks/session_start.py"

    def test_config_structure(self):
        """Test that config structure is correct for all hooks."""
        config = create_hook_config("$HOME/.claude")

        # Verify SessionStart structure
        assert isinstance(config["SessionStart"], list)
        assert "hooks" in config["SessionStart"][0]
        assert isinstance(config["SessionStart"][0]["hooks"], list)

        # Verify Stop structure
        assert isinstance(config["Stop"], list)
        assert "hooks" in config["Stop"][0]

        # Verify PostToolUse structure (has matcher)
        assert isinstance(config["PostToolUse"], list)
        assert "matcher" in config["PostToolUse"][0]
        assert "hooks" in config["PostToolUse"][0]

        # Verify PreCompact structure
        assert isinstance(config["PreCompact"], list)
        assert "hooks" in config["PreCompact"][0]

    def test_timeouts_configured_correctly(self):
        """Test that timeout values are set correctly for different hooks."""
        config = create_hook_config("$HOME/.claude")

        # SessionStart should have 10s timeout
        session_hook = config["SessionStart"][0]["hooks"][0]
        assert session_hook.get("timeout") == 10000

        # Stop should have 30s timeout
        stop_hook = config["Stop"][0]["hooks"][0]
        assert stop_hook.get("timeout") == 30000

        # PostToolUse should NOT have timeout
        post_hook = config["PostToolUse"][0]["hooks"][0]
        assert "timeout" not in post_hook

        # PreCompact should have 30s timeout
        pre_hook = config["PreCompact"][0]["hooks"][0]
        assert pre_hook.get("timeout") == 30000

    def test_no_duplication(self):
        """Test that hook configurations are not duplicated."""
        config = create_hook_config("$HOME/.claude")

        # Each hook type should have exactly one entry
        assert len(config["SessionStart"]) == 1
        assert len(config["Stop"]) == 1
        assert len(config["PostToolUse"]) == 1
        assert len(config["PreCompact"]) == 1

        # Each entry should have exactly one hook configuration
        assert len(config["SessionStart"][0]["hooks"]) == 1
        assert len(config["Stop"][0]["hooks"]) == 1
        assert len(config["PostToolUse"][0]["hooks"]) == 1
        assert len(config["PreCompact"][0]["hooks"]) == 1
