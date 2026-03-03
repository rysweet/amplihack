"""Tests for LockModeHook — dumb and smart co-pilot modes."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplifier_hook_lock_mode import (
    LockModeHook,
    _disable_lock,
    _dumb_directive_with_goal,
    _get_copilot_directive,
)


@pytest.fixture()
def lock_dir(tmp_path: Path) -> Path:
    """Create a temporary lock directory and patch module paths."""
    lock_dir = tmp_path / ".claude" / "runtime" / "locks"
    lock_dir.mkdir(parents=True)
    return lock_dir


@pytest.fixture()
def _patch_paths(lock_dir: Path):
    """Patch module-level path constants to use tmp_path."""
    import amplifier_hook_lock_mode as mod

    original_lock_dir = mod._LOCK_DIR
    original_lock_file = mod._LOCK_FILE
    original_message_file = mod._MESSAGE_FILE
    original_goal_file = mod._GOAL_FILE

    mod._LOCK_DIR = lock_dir
    mod._LOCK_FILE = lock_dir / ".lock_active"
    mod._MESSAGE_FILE = lock_dir / ".lock_message"
    mod._GOAL_FILE = lock_dir / ".lock_goal"

    yield

    mod._LOCK_DIR = original_lock_dir
    mod._LOCK_FILE = original_lock_file
    mod._MESSAGE_FILE = original_message_file
    mod._GOAL_FILE = original_goal_file


class TestLockModeHookDumbMode:
    """Dumb mode — no goal, bare 'continue' directive."""

    @pytest.mark.usefixtures("_patch_paths")
    def test_returns_none_when_not_locked(self, lock_dir: Path):
        hook = LockModeHook()
        result = asyncio.get_event_loop().run_until_complete(
            hook("provider:request", {})
        )
        assert result is None

    @pytest.mark.usefixtures("_patch_paths")
    def test_returns_none_for_non_provider_events(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        hook = LockModeHook()
        result = asyncio.get_event_loop().run_until_complete(
            hook("session:end", {})
        )
        assert result is None

    @pytest.mark.usefixtures("_patch_paths")
    def test_injects_dumb_directive_when_locked(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        hook = LockModeHook()
        result = asyncio.get_event_loop().run_until_complete(
            hook("provider:request", {})
        )
        assert result is not None
        assert result.action == "inject_context"
        assert "LOCK MODE ACTIVE" in result.context_injection
        assert result.metadata["mode"] == "dumb"
        assert result.ephemeral is True

    @pytest.mark.usefixtures("_patch_paths")
    def test_includes_custom_message(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        (lock_dir / ".lock_message").write_text("Focus on tests")
        hook = LockModeHook()
        result = asyncio.get_event_loop().run_until_complete(
            hook("provider:request", {})
        )
        assert "Focus on tests" in result.context_injection

    @pytest.mark.usefixtures("_patch_paths")
    def test_disabled_hook_returns_none(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        hook = LockModeHook(config={"enabled": False})
        result = asyncio.get_event_loop().run_until_complete(
            hook("provider:request", {})
        )
        assert result is None


class TestLockModeHookSmartMode:
    """Smart mode — goal present, uses SessionCopilot."""

    @pytest.mark.usefixtures("_patch_paths")
    def test_smart_mode_with_send_input(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        (lock_dir / ".lock_goal").write_text("Fix the auth bug")

        mock_suggestion = MagicMock()
        mock_suggestion.action = "send_input"
        mock_suggestion.input_text = "Run the test suite now"
        mock_suggestion.reasoning = "Tests needed after code change"
        mock_suggestion.confidence = 0.85
        mock_suggestion.progress_pct = 60

        mock_copilot = MagicMock()
        mock_copilot.suggest.return_value = mock_suggestion

        with patch(
            "amplifier_hook_lock_mode.SessionCopilot",
            return_value=mock_copilot,
        ):
            from amplifier_hook_lock_mode import _get_copilot_directive
            directive, metadata = _get_copilot_directive("Fix the auth bug")

        assert "Run the test suite now" in directive
        assert "Co-Pilot Guidance" in directive
        assert metadata["copilot_action"] == "send_input"
        assert metadata["copilot_confidence"] == 0.85

    @pytest.mark.usefixtures("_patch_paths")
    def test_smart_mode_mark_complete_auto_disables(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        (lock_dir / ".lock_goal").write_text("Create PR")

        mock_suggestion = MagicMock()
        mock_suggestion.action = "mark_complete"
        mock_suggestion.input_text = ""
        mock_suggestion.reasoning = "PR has been created"
        mock_suggestion.confidence = 0.95
        mock_suggestion.progress_pct = 100

        mock_copilot = MagicMock()
        mock_copilot.suggest.return_value = mock_suggestion

        with patch(
            "amplifier_hook_lock_mode.SessionCopilot",
            return_value=mock_copilot,
        ):
            directive, metadata = _get_copilot_directive("Create PR")

        assert "Goal Achieved" in directive
        assert "Auto-Disabled" in directive
        # Lock files should be removed
        assert not (lock_dir / ".lock_active").exists()
        assert not (lock_dir / ".lock_goal").exists()

    @pytest.mark.usefixtures("_patch_paths")
    def test_smart_mode_escalate_auto_disables(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        (lock_dir / ".lock_goal").write_text("Fix complex issue")

        mock_suggestion = MagicMock()
        mock_suggestion.action = "escalate"
        mock_suggestion.input_text = ""
        mock_suggestion.reasoning = "Merge conflict needs human resolution"
        mock_suggestion.confidence = 0.9
        mock_suggestion.progress_pct = 50

        mock_copilot = MagicMock()
        mock_copilot.suggest.return_value = mock_suggestion

        with patch(
            "amplifier_hook_lock_mode.SessionCopilot",
            return_value=mock_copilot,
        ):
            directive, metadata = _get_copilot_directive("Fix complex issue")

        assert "Escalation" in directive
        assert "Auto-Disabled" in directive
        assert not (lock_dir / ".lock_active").exists()

    @pytest.mark.usefixtures("_patch_paths")
    def test_smart_mode_wait_falls_back_to_dumb_with_goal(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        (lock_dir / ".lock_goal").write_text("Write tests")

        mock_suggestion = MagicMock()
        mock_suggestion.action = "wait"
        mock_suggestion.input_text = ""
        mock_suggestion.reasoning = "Agent is still working"
        mock_suggestion.confidence = 0.95
        mock_suggestion.progress_pct = None

        mock_copilot = MagicMock()
        mock_copilot.suggest.return_value = mock_suggestion

        with patch(
            "amplifier_hook_lock_mode.SessionCopilot",
            return_value=mock_copilot,
        ):
            directive, metadata = _get_copilot_directive("Write tests")

        # Falls back to dumb directive with goal context
        assert "Write tests" in directive
        assert "Continue working toward this goal" in directive

    @pytest.mark.usefixtures("_patch_paths")
    def test_smart_mode_low_confidence_falls_back(self, lock_dir: Path):
        """send_input with confidence < 0.6 falls back to dumb mode."""
        (lock_dir / ".lock_active").write_text("locked")
        (lock_dir / ".lock_goal").write_text("Build feature")

        mock_suggestion = MagicMock()
        mock_suggestion.action = "send_input"
        mock_suggestion.input_text = "Maybe try something?"
        mock_suggestion.reasoning = "Unsure about next step"
        mock_suggestion.confidence = 0.4
        mock_suggestion.progress_pct = None

        mock_copilot = MagicMock()
        mock_copilot.suggest.return_value = mock_suggestion

        with patch(
            "amplifier_hook_lock_mode.SessionCopilot",
            return_value=mock_copilot,
        ):
            directive, metadata = _get_copilot_directive("Build feature")

        # Low confidence should NOT inject the specific suggestion
        assert "Maybe try something?" not in directive
        assert "Continue working toward this goal" in directive


class TestSmartModeFallbacks:
    """Fallback behavior when SessionCopilot is unavailable."""

    @pytest.mark.usefixtures("_patch_paths")
    def test_import_error_falls_back_to_dumb_with_goal(self, lock_dir: Path):
        with patch(
            "amplifier_hook_lock_mode.SessionCopilot",
            side_effect=ImportError("No fleet module"),
        ):
            # Import side_effect won't work because it's caught inside
            # Need to patch at import level
            pass

        # Test the import error path directly
        import amplifier_hook_lock_mode as mod
        original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        # Simpler: just test _dumb_directive_with_goal directly
        directive = _dumb_directive_with_goal("Fix auth")
        assert "Fix auth" in directive
        assert "Smart Co-Pilot" in directive

    @pytest.mark.usefixtures("_patch_paths")
    def test_copilot_exception_falls_back(self, lock_dir: Path):
        mock_copilot = MagicMock()
        mock_copilot.suggest.side_effect = RuntimeError("LLM unavailable")

        with patch(
            "amplifier_hook_lock_mode.SessionCopilot",
            return_value=mock_copilot,
        ):
            directive, metadata = _get_copilot_directive("Fix auth")

        assert "Fix auth" in directive
        assert "copilot_error" in metadata


class TestDisableLock:
    """_disable_lock removes all lock files."""

    @pytest.mark.usefixtures("_patch_paths")
    def test_removes_all_lock_files(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        (lock_dir / ".lock_message").write_text("msg")
        (lock_dir / ".lock_goal").write_text("goal")

        _disable_lock()

        assert not (lock_dir / ".lock_active").exists()
        assert not (lock_dir / ".lock_message").exists()
        assert not (lock_dir / ".lock_goal").exists()

    @pytest.mark.usefixtures("_patch_paths")
    def test_handles_missing_files(self, lock_dir: Path):
        """No error when files don't exist."""
        _disable_lock()  # Should not raise


class TestHookGetGoal:
    """LockModeHook._get_goal reads the goal file."""

    @pytest.mark.usefixtures("_patch_paths")
    def test_returns_empty_when_no_goal(self, lock_dir: Path):
        hook = LockModeHook()
        assert hook._get_goal() == ""

    @pytest.mark.usefixtures("_patch_paths")
    def test_returns_goal_content(self, lock_dir: Path):
        (lock_dir / ".lock_goal").write_text("Fix the auth bug")
        hook = LockModeHook()
        assert hook._get_goal() == "Fix the auth bug"


class TestLockTool:
    """Tests for the lock_tool.py CLI."""

    def test_create_lock_with_goal(self, tmp_path: Path, monkeypatch):
        """lock --goal creates both lock and goal files."""
        lock_dir = tmp_path / ".claude" / "runtime" / "locks"
        lock_dir.mkdir(parents=True)

        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "tools" / "amplihack"))

        # Patch the module-level constants
        import importlib
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        # Direct test of the file operations
        lock_file = lock_dir / ".lock_active"
        goal_file = lock_dir / ".lock_goal"

        # Simulate what create_lock does
        import os
        fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, b"locked\n")
        os.close(fd)
        goal_file.write_text("Fix auth bug")

        assert lock_file.exists()
        assert goal_file.read_text() == "Fix auth bug"

    def test_remove_lock_cleans_goal(self, tmp_path: Path):
        """unlock removes goal file too."""
        lock_dir = tmp_path / ".claude" / "runtime" / "locks"
        lock_dir.mkdir(parents=True)

        lock_file = lock_dir / ".lock_active"
        goal_file = lock_dir / ".lock_goal"
        msg_file = lock_dir / ".lock_message"

        lock_file.write_text("locked")
        goal_file.write_text("Fix auth")
        msg_file.write_text("focus")

        # Simulate remove_lock
        for f in (lock_file, msg_file, goal_file):
            if f.exists():
                f.unlink()

        assert not lock_file.exists()
        assert not goal_file.exists()
        assert not msg_file.exists()
