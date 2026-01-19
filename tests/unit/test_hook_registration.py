"""Unit tests for hook registration validation - TDD approach.

Tests that all hooks are properly registered in hooks.json with ${CLAUDE_PLUGIN_ROOT} variable substitution.

Expected hooks to test:
- session_start.py → SessionStart
- stop.py → Stop
- post_tool_use.py → PostToolUse
- pre_compact.py → PreCompact
- pre_tool_use.py → PreToolUse (MISSING from hooks.json)
- user_prompt_submit.py → UserPromptSubmit (MISSING from hooks.json)

These tests are written BEFORE implementation (TDD).
All tests should FAIL initially for missing hooks.
"""

import json
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest


class TestHookRegistration:
    """Test all hooks are registered in hooks.json."""

    @pytest.fixture
    def hooks_directory(self, tmp_path):
        """Create mock hooks directory with hook files."""
        hooks_dir = tmp_path / ".claude" / "tools" / "amplihack" / "hooks"
        hooks_dir.mkdir(parents=True)

        # Create hook files
        hook_files = [
            "session_start.py",
            "stop.py",
            "post_tool_use.py",
            "pre_compact.py",
            "pre_tool_use.py",
            "user_prompt_submit.py",
        ]

        for hook_file in hook_files:
            (hooks_dir / hook_file).write_text("# Hook implementation")
            (hooks_dir / hook_file).chmod(0o755)  # Make executable

        return hooks_dir

    @pytest.fixture
    def hooks_json_path(self, hooks_directory):
        """Path to hooks.json file."""
        return hooks_directory / "hooks.json"

    def test_session_start_hook_registered(self, hooks_json_path):
        """Test SessionStart hook is registered in hooks.json."""
        # Arrange
        hooks_config = json.loads(hooks_json_path.read_text())

        # Act & Assert
        assert "SessionStart" in hooks_config
        assert len(hooks_config["SessionStart"]) > 0
        assert any(
            "${CLAUDE_PLUGIN_ROOT}" in hook.get("command", "")
            for hook in hooks_config["SessionStart"][0]["hooks"]
        )

    def test_stop_hook_registered(self, hooks_json_path):
        """Test Stop hook is registered in hooks.json."""
        # Arrange
        hooks_config = json.loads(hooks_json_path.read_text())

        # Act & Assert
        assert "Stop" in hooks_config
        assert "${CLAUDE_PLUGIN_ROOT}" in str(hooks_config["Stop"])

    def test_post_tool_use_hook_registered(self, hooks_json_path):
        """Test PostToolUse hook is registered in hooks.json."""
        # Arrange
        hooks_config = json.loads(hooks_json_path.read_text())

        # Act & Assert
        assert "PostToolUse" in hooks_config
        assert "${CLAUDE_PLUGIN_ROOT}" in str(hooks_config["PostToolUse"])

    def test_pre_compact_hook_registered(self, hooks_json_path):
        """Test PreCompact hook is registered in hooks.json."""
        # Arrange
        hooks_config = json.loads(hooks_json_path.read_text())

        # Act & Assert
        assert "PreCompact" in hooks_config
        assert "${CLAUDE_PLUGIN_ROOT}" in str(hooks_config["PreCompact"])

    def test_pre_tool_use_hook_registered(self, hooks_json_path):
        """Test PreToolUse hook is registered (currently MISSING)."""
        # Arrange
        hooks_config = json.loads(hooks_json_path.read_text())

        # Act & Assert - THIS WILL FAIL until PreToolUse is added
        assert "PreToolUse" in hooks_config, "PreToolUse hook missing from hooks.json"
        assert "${CLAUDE_PLUGIN_ROOT}" in str(hooks_config["PreToolUse"])

    def test_user_prompt_submit_hook_registered(self, hooks_json_path):
        """Test UserPromptSubmit hook is registered (currently MISSING)."""
        # Arrange
        hooks_config = json.loads(hooks_json_path.read_text())

        # Act & Assert - THIS WILL FAIL until UserPromptSubmit is added
        assert "UserPromptSubmit" in hooks_config, "UserPromptSubmit hook missing from hooks.json"
        assert "${CLAUDE_PLUGIN_ROOT}" in str(hooks_config["UserPromptSubmit"])

    def test_all_hooks_use_variable_substitution(self, hooks_json_path):
        """Test all hooks use ${CLAUDE_PLUGIN_ROOT} variable."""
        # Arrange
        hooks_config = json.loads(hooks_json_path.read_text())

        # Act & Assert
        for hook_name, hook_entries in hooks_config.items():
            for entry in hook_entries:
                for hook in entry.get("hooks", []):
                    command = hook.get("command", "")
                    assert "${CLAUDE_PLUGIN_ROOT}" in command, \
                        f"Hook {hook_name} does not use ${{CLAUDE_PLUGIN_ROOT}}"

    def test_no_absolute_paths_in_hooks(self, hooks_json_path):
        """Test hooks don't use absolute paths (must use variable)."""
        # Arrange
        hooks_config = json.loads(hooks_json_path.read_text())

        # Act & Assert
        for hook_name, hook_entries in hooks_config.items():
            for entry in hook_entries:
                for hook in entry.get("hooks", []):
                    command = hook.get("command", "")
                    # Should not start with / or contain /home/ etc
                    assert not command.startswith("/"), \
                        f"Hook {hook_name} uses absolute path: {command}"
                    assert "/home/" not in command, \
                        f"Hook {hook_name} contains hardcoded path: {command}"


class TestHookFileExecutability:
    """Test hook files are executable."""

    @pytest.fixture
    def hooks_directory(self):
        """Get actual hooks directory path."""
        return Path(".claude/tools/amplihack/hooks")

    def test_session_start_is_executable(self, hooks_directory):
        """Test session_start.py is executable."""
        hook_file = hooks_directory / "session_start.py"
        assert hook_file.exists()
        assert hook_file.stat().st_mode & 0o111, "session_start.py not executable"

    def test_stop_is_executable(self, hooks_directory):
        """Test stop.py is executable."""
        hook_file = hooks_directory / "stop.py"
        assert hook_file.exists()
        assert hook_file.stat().st_mode & 0o111, "stop.py not executable"

    def test_post_tool_use_is_executable(self, hooks_directory):
        """Test post_tool_use.py is executable."""
        hook_file = hooks_directory / "post_tool_use.py"
        assert hook_file.exists()
        assert hook_file.stat().st_mode & 0o111, "post_tool_use.py not executable"

    def test_pre_compact_is_executable(self, hooks_directory):
        """Test pre_compact.py is executable."""
        hook_file = hooks_directory / "pre_compact.py"
        assert hook_file.exists()
        assert hook_file.stat().st_mode & 0o111, "pre_compact.py not executable"

    def test_pre_tool_use_is_executable(self, hooks_directory):
        """Test pre_tool_use.py is executable."""
        hook_file = hooks_directory / "pre_tool_use.py"
        assert hook_file.exists()
        assert hook_file.stat().st_mode & 0o111, "pre_tool_use.py not executable"

    def test_user_prompt_submit_is_executable(self, hooks_directory):
        """Test user_prompt_submit.py is executable."""
        hook_file = hooks_directory / "user_prompt_submit.py"
        assert hook_file.exists()
        assert hook_file.stat().st_mode & 0o111, "user_prompt_submit.py not executable"


class TestHookDiscovery:
    """Test discovery of missing hooks."""

    def test_discover_all_hook_files(self):
        """Test discovery finds all .py files in hooks directory."""
        # Arrange
        hooks_dir = Path(".claude/tools/amplihack/hooks")

        # Act
        hook_files = list(hooks_dir.glob("*.py"))
        hook_files = [f for f in hook_files if not f.name.startswith("test_")]

        # Assert
        # Should find at least 6 hooks
        assert len(hook_files) >= 6
        hook_names = {f.name for f in hook_files}
        assert "session_start.py" in hook_names
        assert "stop.py" in hook_names
        assert "post_tool_use.py" in hook_names
        assert "pre_compact.py" in hook_names
        assert "pre_tool_use.py" in hook_names
        assert "user_prompt_submit.py" in hook_names

    def test_compare_files_vs_registered_hooks(self):
        """Test all discovered hook files are registered."""
        # Arrange
        hooks_dir = Path(".claude/tools/amplihack/hooks")
        hooks_json_path = hooks_dir / "hooks.json"

        # Act
        hook_files = {
            f.stem: f for f in hooks_dir.glob("*.py")
            if not f.name.startswith("test_") and f.is_file()
        }

        hooks_config = json.loads(hooks_json_path.read_text())
        registered_hooks = set(hooks_config.keys())

        # Map file names to expected hook names
        file_to_hook_map = {
            "session_start": "SessionStart",
            "stop": "Stop",
            "post_tool_use": "PostToolUse",
            "pre_compact": "PreCompact",
            "pre_tool_use": "PreToolUse",
            "user_prompt_submit": "UserPromptSubmit",
        }

        # Assert
        for file_stem, expected_hook in file_to_hook_map.items():
            if file_stem in hook_files:
                assert expected_hook in registered_hooks, \
                    f"Hook file {file_stem}.py exists but {expected_hook} not in hooks.json"


class TestHookTimeouts:
    """Test hook timeout configurations."""

    def test_session_start_has_timeout(self):
        """Test SessionStart hook has timeout configured."""
        # Arrange
        hooks_json_path = Path(".claude/tools/amplihack/hooks/hooks.json")
        hooks_config = json.loads(hooks_json_path.read_text())

        # Act & Assert
        session_start = hooks_config["SessionStart"][0]["hooks"][0]
        assert "timeout" in session_start
        assert session_start["timeout"] > 0

    def test_stop_has_timeout(self):
        """Test Stop hook has timeout configured."""
        # Arrange
        hooks_json_path = Path(".claude/tools/amplihack/hooks/hooks.json")
        hooks_config = json.loads(hooks_json_path.read_text())

        # Act & Assert
        stop = hooks_config["Stop"][0]["hooks"][0]
        assert "timeout" in stop
        assert stop["timeout"] > 0

    def test_pre_compact_has_timeout(self):
        """Test PreCompact hook has timeout configured."""
        # Arrange
        hooks_json_path = Path(".claude/tools/amplihack/hooks/hooks.json")
        hooks_config = json.loads(hooks_json_path.read_text())

        # Act & Assert
        pre_compact = hooks_config["PreCompact"][0]["hooks"][0]
        assert "timeout" in pre_compact
        assert pre_compact["timeout"] > 0
