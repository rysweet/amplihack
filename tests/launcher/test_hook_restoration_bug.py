"""TDD tests for Issue #2335: Hook restoration bug in launch_interactive().

Bug Description:
    SettingsManager backs up settings.json BEFORE hooks are added by prepare_launch(),
    then restores the old backup on exit, removing the hooks that were added.

Expected Fix:
    Remove SettingsManager instantiation and usage from launch_interactive() since
    hooks should persist across sessions and should be managed by ensure_settings_json().

Test Coverage:
    1. Hooks persist after launch_interactive() completes
    2. SettingsManager is NOT instantiated in launch_interactive()
    3. ensure_settings_json() still works correctly (regression test)
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.launcher.core import ClaudeLauncher


class TestHookRestorationBug:
    """Test suite for hook restoration bug (Issue #2335)."""

    @pytest.fixture
    def temp_claude_dir(self, tmp_path):
        """Create temporary .claude directory with settings.json."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        return claude_dir

    @pytest.fixture
    def settings_with_hooks(self, temp_claude_dir):
        """Create settings.json with hooks configured."""
        settings_path = temp_claude_dir / "settings.json"
        settings_data = {
            "permissions": {
                "allow": ["Bash", "TodoWrite"],
                "deny": [],
                "defaultMode": "bypassPermissions",
            },
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/home/user/.amplihack/.claude/tools/amplihack/hooks/session_start.py",
                                "timeout": 10,
                            }
                        ]
                    }
                ],
                "Stop": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/home/user/.amplihack/.claude/tools/amplihack/hooks/stop.py",
                                "timeout": 120,
                            }
                        ]
                    }
                ],
            },
        }

        with open(settings_path, "w") as f:
            json.dump(settings_data, f, indent=2)

        return settings_path

    def test_hooks_persist_after_launch_interactive_completes(
        self, temp_claude_dir, settings_with_hooks, monkeypatch
    ):
        """Test that hooks remain in settings.json after launch_interactive() returns.

        This test WILL FAIL until the bug is fixed.

        Expected behavior:
            - Hooks should persist in settings.json after function completes
            - No backup/restore should occur that removes hooks

        Bug behavior:
            - SettingsManager backs up settings BEFORE hooks are added
            - On exit, it restores the old backup, removing hooks
        """
        # Setup: Patch home directory to use temp directory
        monkeypatch.setenv("HOME", str(temp_claude_dir.parent))
        monkeypatch.setattr(Path, "home", lambda: temp_claude_dir.parent)

        # Read initial hooks
        with open(settings_with_hooks) as f:
            initial_settings = json.load(f)
        initial_hooks = initial_settings.get("hooks", {})

        # Create launcher instance
        launcher = ClaudeLauncher()

        # Mock subprocess.call to prevent actual Claude execution
        with patch("subprocess.call", return_value=0):
            # Mock prepare_launch to succeed without side effects
            with patch.object(launcher, "prepare_launch", return_value=True):
                # Mock build_claude_command to return dummy command
                with patch.object(launcher, "build_claude_command", return_value=["echo", "test"]):
                    # Call launch_interactive
                    exit_code = launcher.launch_interactive()

        # Verify exit code
        assert exit_code == 0, "Launch should succeed"

        # CRITICAL TEST: Verify hooks still exist in settings.json
        with open(settings_with_hooks) as f:
            final_settings = json.load(f)

        final_hooks = final_settings.get("hooks", {})

        # This assertion WILL FAIL until bug is fixed
        assert final_hooks == initial_hooks, (
            "Hooks should persist after launch_interactive() completes. "
            "Bug: SettingsManager restores backup that removes hooks."
        )

        # Verify specific hooks are present
        assert "SessionStart" in final_hooks, "SessionStart hook should persist"
        assert "Stop" in final_hooks, "Stop hook should persist"

    def test_settings_manager_not_instantiated_in_launch_interactive(self):
        """Test that SettingsManager is NOT instantiated in launch_interactive().

        This test WILL FAIL until the bug is fixed.

        Expected behavior:
            - launch_interactive() should NOT create a SettingsManager instance
            - Settings management should be handled by ensure_settings_json() only

        Bug behavior:
            - launch_interactive() creates SettingsManager (line 797-803)
            - This causes backup/restore cycle that removes hooks
        """
        launcher = ClaudeLauncher()

        # Mock dependencies to prevent actual execution
        with patch("subprocess.call", return_value=0):
            with patch.object(launcher, "prepare_launch", return_value=True):
                with patch.object(launcher, "build_claude_command", return_value=["echo", "test"]):
                    # Patch SettingsManager where it's imported (in launch_interactive)
                    with patch(
                        "amplihack.launcher.settings_manager.SettingsManager"
                    ) as mock_settings_manager:
                        # Call launch_interactive
                        launcher.launch_interactive()

                        # This assertion WILL FAIL until bug is fixed
                        mock_settings_manager.assert_not_called()

    def test_ensure_settings_json_still_works_correctly(self, temp_claude_dir, monkeypatch):
        """Regression test: ensure_settings_json() should still work after fix.

        This test verifies that removing SettingsManager from launch_interactive()
        doesn't break the ensure_settings_json() function that actually manages hooks.

        Expected behavior:
            - ensure_settings_json() creates settings.json with hooks
            - Hooks persist in the file after function completes
            - No SettingsManager backup/restore interferes
        """
        # Setup: Patch home directory
        monkeypatch.setenv("HOME", str(temp_claude_dir.parent))
        monkeypatch.setattr(Path, "home", lambda: temp_claude_dir.parent)

        # Mock CLAUDE_DIR and HOME to use temp directory
        with patch("amplihack.settings.CLAUDE_DIR", str(temp_claude_dir)):
            with patch("amplihack.settings.HOME", str(temp_claude_dir.parent)):
                # Import and call ensure_settings_json
                from amplihack.settings import ensure_settings_json

                # Create settings.json with hooks
                result = ensure_settings_json()

                # Verify function succeeded
                assert result is True, "ensure_settings_json() should succeed"

        # Verify settings.json exists
        settings_path = temp_claude_dir / "settings.json"
        assert settings_path.exists(), "settings.json should be created"

        # Verify hooks are present
        with open(settings_path) as f:
            settings = json.load(f)

        assert "hooks" in settings, "Hooks should be in settings.json"
        assert "SessionStart" in settings["hooks"], "SessionStart hook should exist"
        assert "Stop" in settings["hooks"], "Stop hook should exist"

        # Verify hooks persist (not removed by any backup/restore)
        with open(settings_path) as f:
            settings_after = json.load(f)

        assert settings_after["hooks"] == settings["hooks"], "Hooks should persist unchanged"

    def test_no_backup_files_created_by_launch_interactive(
        self, temp_claude_dir, settings_with_hooks, monkeypatch
    ):
        """Test that launch_interactive() doesn't create backup files.

        This test WILL FAIL until the bug is fixed.

        Expected behavior:
            - No .backup files should be created by launch_interactive()
            - Settings backups are only for ensure_settings_json() safety

        Bug behavior:
            - SettingsManager creates .backup files during launch
            - These backups contain settings WITHOUT hooks
        """
        # Setup: Patch home directory
        monkeypatch.setenv("HOME", str(temp_claude_dir.parent))
        monkeypatch.setattr(Path, "home", lambda: temp_claude_dir.parent)

        # Create launcher
        launcher = ClaudeLauncher()

        # Mock dependencies
        with patch("subprocess.call", return_value=0):
            with patch.object(launcher, "prepare_launch", return_value=True):
                with patch.object(launcher, "build_claude_command", return_value=["echo", "test"]):
                    # Call launch_interactive
                    launcher.launch_interactive()

        # Check for backup files
        backup_files = list(temp_claude_dir.glob("settings.json.backup.*"))

        # This assertion WILL FAIL until bug is fixed
        assert len(backup_files) == 0, (
            f"No backup files should be created by launch_interactive(). "
            f"Found: {[f.name for f in backup_files]}"
        )

    def test_hooks_added_by_prepare_launch_persist(self, temp_claude_dir, monkeypatch):
        """Test that hooks added by prepare_launch() persist after launch completes.

        This is the core bug test: prepare_launch() adds hooks, but they should
        NOT be removed when launch_interactive() exits.

        This test WILL FAIL until the bug is fixed.
        """
        # Setup: Empty settings.json (no hooks initially)
        settings_path = temp_claude_dir / "settings.json"
        initial_settings = {
            "permissions": {"allow": [], "deny": [], "defaultMode": "bypassPermissions"}
        }

        with open(settings_path, "w") as f:
            json.dump(initial_settings, f, indent=2)

        # Patch home and CLAUDE_DIR
        monkeypatch.setenv("HOME", str(temp_claude_dir.parent))
        monkeypatch.setattr(Path, "home", lambda: temp_claude_dir.parent)

        # Create launcher
        launcher = ClaudeLauncher()

        # Mock to simulate prepare_launch() adding hooks
        def mock_prepare_launch():
            # Simulate ensure_settings_json() adding hooks
            with open(settings_path) as f:
                settings = json.load(f)

            settings["hooks"] = {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "session_start.py", "timeout": 10}]}
                ]
            }

            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=2)

            return True

        # Run launch_interactive with mocked prepare_launch
        with patch("subprocess.call", return_value=0):
            with patch.object(launcher, "prepare_launch", side_effect=mock_prepare_launch):
                with patch.object(launcher, "build_claude_command", return_value=["echo", "test"]):
                    launcher.launch_interactive()

        # CRITICAL TEST: Hooks added by prepare_launch should still be present
        with open(settings_path) as f:
            final_settings = json.load(f)

        # This assertion WILL FAIL until bug is fixed
        assert "hooks" in final_settings, "Hooks added by prepare_launch() should persist"
        assert "SessionStart" in final_settings.get("hooks", {}), "SessionStart hook should persist"
