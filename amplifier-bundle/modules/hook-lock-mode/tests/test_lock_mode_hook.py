"""Tests for LockModeHook — autonomous co-pilot mode."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplifier_hook_lock_mode import (
    LockModeHook,
    _disable_lock,
    _get_copilot_directive,
    _goal_directive,
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

    orig = (mod._LOCK_DIR, mod._LOCK_FILE, mod._GOAL_FILE)
    mod._LOCK_DIR = lock_dir
    mod._LOCK_FILE = lock_dir / ".lock_active"
    mod._GOAL_FILE = lock_dir / ".lock_goal"
    yield
    mod._LOCK_DIR, mod._LOCK_FILE, mod._GOAL_FILE = orig


class TestLockModeHookBasics:
    """Core hook behavior."""

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
    def test_disabled_hook_returns_none(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        hook = LockModeHook(config={"enabled": False})
        result = asyncio.get_event_loop().run_until_complete(
            hook("provider:request", {})
        )
        assert result is None

    @pytest.mark.usefixtures("_patch_paths")
    def test_locked_without_goal_uses_default(self, lock_dir: Path):
        """Lock active but no goal file — uses a default goal."""
        (lock_dir / ".lock_active").write_text("locked")
        hook = LockModeHook()

        # Patch _get_copilot_directive to avoid needing SessionCopilot
        with patch("amplifier_hook_lock_mode._get_copilot_directive") as mock_gcd:
            mock_gcd.return_value = ("directive", {"copilot_action": "wait"})
            result = asyncio.get_event_loop().run_until_complete(
                hook("provider:request", {})
            )

        assert result is not None
        assert result.action == "inject_context"
        assert result.metadata["lock_mode"] is True


class TestCopilotDirective:
    """_get_copilot_directive behavior with mocked SessionCopilot."""

    @pytest.mark.usefixtures("_patch_paths")
    def test_send_input_high_confidence(self, lock_dir: Path):
        mock_suggestion = MagicMock()
        mock_suggestion.action = "send_input"
        mock_suggestion.input_text = "Run the test suite"
        mock_suggestion.reasoning = "Tests needed"
        mock_suggestion.confidence = 0.85
        mock_suggestion.progress_pct = 60

        mock_copilot = MagicMock()
        mock_copilot.suggest.return_value = mock_suggestion

        with patch("amplifier_hook_lock_mode.SessionCopilot", return_value=mock_copilot):
            directive, metadata = _get_copilot_directive("Fix auth bug")

        assert "Run the test suite" in directive
        assert "Co-Pilot Guidance" in directive
        assert metadata["copilot_action"] == "send_input"

    @pytest.mark.usefixtures("_patch_paths")
    def test_mark_complete_auto_disables(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        (lock_dir / ".lock_goal").write_text("Create PR")

        mock_suggestion = MagicMock()
        mock_suggestion.action = "mark_complete"
        mock_suggestion.reasoning = "PR created"
        mock_suggestion.confidence = 0.95
        mock_suggestion.progress_pct = 100
        mock_suggestion.input_text = ""

        mock_copilot = MagicMock()
        mock_copilot.suggest.return_value = mock_suggestion

        with patch("amplifier_hook_lock_mode.SessionCopilot", return_value=mock_copilot):
            directive, metadata = _get_copilot_directive("Create PR")

        assert "Goal Achieved" in directive
        assert not (lock_dir / ".lock_active").exists()
        assert not (lock_dir / ".lock_goal").exists()

    @pytest.mark.usefixtures("_patch_paths")
    def test_escalate_auto_disables(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        (lock_dir / ".lock_goal").write_text("Fix issue")

        mock_suggestion = MagicMock()
        mock_suggestion.action = "escalate"
        mock_suggestion.reasoning = "Merge conflict"
        mock_suggestion.confidence = 0.9
        mock_suggestion.progress_pct = 50
        mock_suggestion.input_text = ""

        mock_copilot = MagicMock()
        mock_copilot.suggest.return_value = mock_suggestion

        with patch("amplifier_hook_lock_mode.SessionCopilot", return_value=mock_copilot):
            directive, metadata = _get_copilot_directive("Fix issue")

        assert "Escalation" in directive
        assert not (lock_dir / ".lock_active").exists()

    @pytest.mark.usefixtures("_patch_paths")
    def test_low_confidence_falls_back_to_goal_directive(self, lock_dir: Path):
        mock_suggestion = MagicMock()
        mock_suggestion.action = "send_input"
        mock_suggestion.input_text = "Maybe try something?"
        mock_suggestion.reasoning = "Unsure"
        mock_suggestion.confidence = 0.4
        mock_suggestion.progress_pct = None

        mock_copilot = MagicMock()
        mock_copilot.suggest.return_value = mock_suggestion

        with patch("amplifier_hook_lock_mode.SessionCopilot", return_value=mock_copilot):
            directive, metadata = _get_copilot_directive("Build feature")

        assert "Maybe try something?" not in directive
        assert "Continue working toward this goal" in directive

    @pytest.mark.usefixtures("_patch_paths")
    def test_wait_uses_goal_directive(self, lock_dir: Path):
        mock_suggestion = MagicMock()
        mock_suggestion.action = "wait"
        mock_suggestion.reasoning = "Agent working"
        mock_suggestion.confidence = 0.95
        mock_suggestion.progress_pct = None
        mock_suggestion.input_text = ""

        mock_copilot = MagicMock()
        mock_copilot.suggest.return_value = mock_suggestion

        with patch("amplifier_hook_lock_mode.SessionCopilot", return_value=mock_copilot):
            directive, metadata = _get_copilot_directive("Write tests")

        assert "Continue working toward this goal" in directive

    @pytest.mark.usefixtures("_patch_paths")
    def test_copilot_exception_falls_back(self, lock_dir: Path):
        mock_copilot = MagicMock()
        mock_copilot.suggest.side_effect = RuntimeError("LLM unavailable")

        with patch("amplifier_hook_lock_mode.SessionCopilot", return_value=mock_copilot):
            directive, metadata = _get_copilot_directive("Fix auth")

        assert "Fix auth" in directive
        assert "copilot_error" in metadata


class TestDisableLock:
    """_disable_lock removes all lock files."""

    @pytest.mark.usefixtures("_patch_paths")
    def test_removes_all_lock_files(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        (lock_dir / ".lock_goal").write_text("goal")
        _disable_lock()
        assert not (lock_dir / ".lock_active").exists()
        assert not (lock_dir / ".lock_goal").exists()

    @pytest.mark.usefixtures("_patch_paths")
    def test_handles_missing_files(self, lock_dir: Path):
        _disable_lock()  # Should not raise


class TestGoalDirective:
    """_goal_directive produces correct output."""

    def test_includes_goal_text(self):
        directive = _goal_directive("Fix the auth bug")
        assert "Fix the auth bug" in directive
        assert "Autonomous Co-Pilot Active" in directive
        assert "Continue working" in directive


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
