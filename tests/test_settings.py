"""Tests for settings.py hook path configuration - TDD approach.

Testing pyramid distribution:
- 60% Unit tests (24 lines) - Fast, heavily mocked
- 30% Integration tests (12 lines) - Multiple components
- 10% E2E tests (4 lines) - Complete workflows

Philosophy:
- Tests MUST fail before implementation (RED phase of TDD)
- Test the contract, not implementation details
- Focus on critical behavior: absolute paths from relative inputs
"""

import json
import os
from unittest.mock import patch

import pytest

from amplihack.settings import (
    ensure_settings_json,
    update_hook_paths,
)

# =============================================================================
# UNIT TESTS (60% - ~24 lines)
# =============================================================================


class TestHookPathExpansion:
    """Unit tests for hook path expansion behavior"""

    def test_hook_path_expansion_removes_home_variable(self):
        """Test that $HOME gets expanded to actual path"""
        # Arrange
        settings = {"hooks": {}}
        hooks_to_update = [{"type": "SessionStart", "file": "session_start.py"}]

        # Mock hooks_dir_path with $HOME (should be expanded)
        with patch.dict(os.environ, {"HOME": "/mock/home"}):
            hooks_dir_path = "$HOME/.amplihack/.claude/tools/amplihack/hooks"

            # Act
            update_hook_paths(settings, "amplihack", hooks_to_update, hooks_dir_path)

            # Assert
            hook_command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
            assert "$HOME" not in hook_command, "Hook path should NOT contain $HOME variable"
            assert "/mock/home" in hook_command, "Hook path should contain expanded home path"

    def test_hook_path_expansion_removes_tilde(self):
        """Test that ~ gets expanded to home directory"""
        # Arrange
        settings = {"hooks": {}}
        hooks_to_update = [{"type": "Stop", "file": "stop.py"}]

        # Mock hooks_dir_path with tilde
        hooks_dir_path = "~/.amplihack/.claude/tools/amplihack/hooks"

        # Act
        update_hook_paths(settings, "amplihack", hooks_to_update, hooks_dir_path)

        # Assert
        hook_command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        assert "~" not in hook_command, "Hook path should NOT contain tilde"
        assert os.path.expanduser("~") in hook_command, "Hook path should contain expanded home"

    def test_hook_path_is_absolute(self):
        """Test that resulting path is absolute (starts with /)"""
        # Arrange
        settings = {"hooks": {}}
        hooks_to_update = [{"type": "PostToolUse", "file": "post_tool_use.py", "matcher": "*"}]

        # Use relative path that should be made absolute
        hooks_dir_path = ".claude/tools/amplihack/hooks"

        # Act
        update_hook_paths(settings, "amplihack", hooks_to_update, hooks_dir_path)

        # Assert
        hook_command = settings["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
        assert os.path.isabs(hook_command), f"Hook path must be absolute: {hook_command}"
        assert not hook_command.startswith(".claude"), (
            "Hook path should NOT start with relative path"
        )


# =============================================================================
# INTEGRATION TESTS (30% - ~12 lines)
# =============================================================================


class TestSettingsJsonAbsolutePaths:
    """Integration tests for settings.json absolute path generation"""

    @patch("amplihack.settings.HOME", "/mock/home")
    @patch("amplihack.settings.CLAUDE_DIR", "/mock/home/.claude")
    def test_settings_json_contains_only_absolute_paths(self, tmp_path):
        """Test that ensure_settings_json generates ONLY absolute paths"""
        # Arrange - Mock settings path
        settings_path = tmp_path / "settings.json"

        with patch("amplihack.settings.CLAUDE_DIR", str(tmp_path)):
            with patch("os.path.exists") as mock_exists:
                # Mock hook files exist
                mock_exists.return_value = True

                # Act
                result = ensure_settings_json()

                # Assert function succeeded
                assert result is True, "ensure_settings_json should succeed"

                # Read generated settings.json
                assert settings_path.exists(), "settings.json should be created"
                with open(settings_path) as f:
                    settings = json.load(f)

                # Verify ALL hook paths are absolute (no relative paths)
                for hook_type, hook_configs in settings.get("hooks", {}).items():
                    for config in hook_configs:
                        for hook in config.get("hooks", []):
                            command = hook.get("command", "")
                            assert os.path.isabs(command), (
                                f"Hook {hook_type} path must be absolute: {command}"
                            )
                            assert not command.startswith(".claude"), (
                                f"Hook {hook_type} must NOT have relative path: {command}"
                            )
                            assert "$HOME" not in command, (
                                f"Hook {hook_type} must NOT contain $HOME: {command}"
                            )
                            assert "~" not in command, (
                                f"Hook {hook_type} must NOT contain tilde: {command}"
                            )


# =============================================================================
# E2E TESTS (10% - ~4 lines)
# =============================================================================


class TestCrossDirExecution:
    """End-to-end tests for hooks working from different directories"""

    @pytest.mark.slow
    def test_hooks_work_from_different_working_directories(self, tmp_path):
        """Test hooks can be found when working directory changes"""
        # Arrange - Create test directory structure
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        hooks_dir = home_dir / ".amplihack" / ".claude" / "tools" / "amplihack" / "hooks"
        hooks_dir.mkdir(parents=True)

        # Create dummy hook file
        hook_file = hooks_dir / "session_start.py"
        hook_file.write_text("#!/usr/bin/env python3\nprint('test')")
        hook_file.chmod(0o755)

        # Create settings with absolute path
        settings = {"hooks": {}}
        hooks_to_update = [{"type": "SessionStart", "file": "session_start.py"}]
        hooks_dir_path = str(hooks_dir)

        update_hook_paths(settings, "amplihack", hooks_to_update, hooks_dir_path)

        # Get hook command
        hook_command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]

        # Act - Change to different directory
        work_dir = tmp_path / "different" / "working" / "directory"
        work_dir.mkdir(parents=True)
        original_cwd = os.getcwd()

        try:
            os.chdir(work_dir)

            # Assert - Hook file can still be found via absolute path
            assert os.path.exists(hook_command), (
                f"Hook must be accessible from ANY directory: {hook_command}"
            )
            assert os.path.isabs(hook_command), (
                f"Hook path must be absolute for cross-dir execution: {hook_command}"
            )
        finally:
            os.chdir(original_cwd)
