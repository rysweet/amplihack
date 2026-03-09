"""Outside-in test: launch_command() restores CWD on shutdown.

Reproduces the bug from PR #2965 where the finally block in launch_command()
referenced `original_cwd` without defining it, causing NameError on every
session shutdown.

Tests verify the fix works from a user's perspective:
- Session completes without NameError
- CWD is restored after staging changes it
- AMPLIHACK_ORIGINAL_CWD env var is respected when set
"""

import argparse
import os
from unittest.mock import MagicMock, patch

import pytest

# Patch targets — SessionTracker is a local import inside launch_command,
# so we must patch at the source module for the mock to take effect.
_STARTUP = "amplihack.cli._common_launcher_startup"
_IMPL = "amplihack.cli._launch_command_impl"
_TRACKER_CLS = "amplihack.launcher.session_tracker.SessionTracker"


def _make_args(**overrides) -> argparse.Namespace:
    """Build a minimal args Namespace for launch_command testing."""
    defaults = {
        "command": "launch",
        "verbose": False,
        "quiet": False,
        "subprocess_safe": False,
        "auto": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _mock_session_tracker():
    """Create a mock SessionTracker that returns a fake session ID."""
    tracker = MagicMock()
    tracker.start_session.return_value = "test-session-id"
    return tracker


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove AMPLIHACK_ORIGINAL_CWD so tests control the env explicitly."""
    monkeypatch.delenv("AMPLIHACK_ORIGINAL_CWD", raising=False)


class TestLaunchCommandCWDRestore:
    """Verify launch_command() defines and restores original_cwd in finally block."""

    def test_no_name_error_on_normal_exit(self):
        """Before the fix, this raised NameError: name 'original_cwd' is not defined."""
        from amplihack.cli import launch_command

        args = _make_args()
        tracker = _mock_session_tracker()

        with (
            patch(_STARTUP),
            patch(_IMPL, return_value=0),
            patch(_TRACKER_CLS, return_value=tracker),
        ):
            result = launch_command(args)
            assert result == 0

    def test_no_name_error_on_exception_exit(self):
        """CWD restore must run even when _launch_command_impl raises."""
        from amplihack.cli import launch_command

        args = _make_args()
        tracker = _mock_session_tracker()

        with (
            patch(_STARTUP),
            patch(_IMPL, side_effect=RuntimeError("session crash")),
            patch(_TRACKER_CLS, return_value=tracker),
        ):
            with pytest.raises(RuntimeError, match="session crash"):
                launch_command(args)

            tracker.crash_session.assert_called_once_with("test-session-id")

    def test_restores_cwd_after_normal_exit(self, tmp_path):
        """Verify CWD is restored to original value after session completes."""
        from amplihack.cli import launch_command

        original = tmp_path / "original"
        original.mkdir()
        staged = tmp_path / "staged"
        staged.mkdir()

        args = _make_args()
        tracker = _mock_session_tracker()

        saved_cwd = os.getcwd()
        try:
            os.chdir(original)

            def fake_startup(a):
                os.chdir(staged)

            with (
                patch(_STARTUP, side_effect=fake_startup),
                patch(_IMPL, return_value=0),
                patch(_TRACKER_CLS, return_value=tracker),
            ):
                launch_command(args)

            assert os.getcwd() == str(original)
        finally:
            os.chdir(saved_cwd)

    def test_restores_cwd_even_on_exception(self, tmp_path):
        """Verify CWD is restored even when session crashes."""
        from amplihack.cli import launch_command

        original = tmp_path / "original"
        original.mkdir()
        staged = tmp_path / "staged"
        staged.mkdir()

        args = _make_args()
        tracker = _mock_session_tracker()

        saved_cwd = os.getcwd()
        try:
            os.chdir(original)

            def fake_startup(a):
                os.chdir(staged)

            with (
                patch(_STARTUP, side_effect=fake_startup),
                patch(_IMPL, side_effect=RuntimeError("boom")),
                patch(_TRACKER_CLS, return_value=tracker),
            ):
                with pytest.raises(RuntimeError):
                    launch_command(args)

            assert os.getcwd() == str(original)
        finally:
            os.chdir(saved_cwd)

    def test_uses_amplihack_original_cwd_env_var(self, tmp_path, monkeypatch):
        """When AMPLIHACK_ORIGINAL_CWD is set, use it instead of os.getcwd()."""
        from amplihack.cli import launch_command

        env_original = tmp_path / "env_original"
        env_original.mkdir()
        current = tmp_path / "current"
        current.mkdir()

        args = _make_args()
        tracker = _mock_session_tracker()

        monkeypatch.setenv("AMPLIHACK_ORIGINAL_CWD", str(env_original))

        saved_cwd = os.getcwd()
        try:
            os.chdir(current)

            with (
                patch(_STARTUP),
                patch(_IMPL, return_value=0),
                patch(_TRACKER_CLS, return_value=tracker),
            ):
                launch_command(args)

            assert os.getcwd() == str(env_original)
        finally:
            os.chdir(saved_cwd)
