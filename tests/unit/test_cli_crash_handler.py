"""Unit tests for cli.launch_command crash handler — issue #3233.

Verifies that the crash handler uses a flat try/except/finally
(no nested exception swallowing) and that failures in crash_session()
or os.chdir() propagate instead of being silently swallowed.
"""

import argparse
import os
from unittest.mock import MagicMock, patch

import pytest


def _make_args(**kwargs) -> argparse.Namespace:
    """Create a Namespace with sensible defaults for launch_command."""
    defaults = {
        "subprocess_safe": False,
        "auto": False,
        "docker": False,
        "no_reflection": False,
        "with_proxy_config": None,
        "checkout_repo": None,
        "max_turns": 10,
        "ui": False,
        "append": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture()
def mock_tracker():
    tracker = MagicMock()
    tracker.start_session.return_value = "sess-001"
    return tracker


@pytest.fixture()
def _patch_startup(mock_tracker):
    """Patch everything around launch_command so only the crash handler runs.

    SessionTracker is imported lazily inside launch_command, so we must
    patch at the source module (amplihack.launcher.session_tracker).
    """
    with (
        patch("amplihack.cli._common_launcher_startup"),
        patch(
            "amplihack.launcher.session_tracker.SessionTracker",
            return_value=mock_tracker,
        ),
        patch.dict(os.environ, {"AMPLIHACK_ORIGINAL_CWD": os.getcwd()}),
    ):
        yield


@pytest.mark.usefixtures("_patch_startup")
class TestCrashHandlerFlat:
    """The crash handler in launch_command must not nest exception handlers."""

    def test_crash_session_called_on_error(self, mock_tracker):
        """When _launch_command_impl raises, crash_session is invoked."""
        with (
            patch(
                "amplihack.cli._launch_command_impl",
                side_effect=RuntimeError("boom"),
            ),
            pytest.raises(RuntimeError, match="boom"),
        ):
            from amplihack.cli import launch_command

            launch_command(_make_args())

        mock_tracker.crash_session.assert_called_once_with("sess-001")

    def test_crash_session_failure_propagates(self, mock_tracker):
        """If crash_session itself fails, its error propagates (not swallowed)."""
        mock_tracker.crash_session.side_effect = OSError("disk full")

        with (
            patch(
                "amplihack.cli._launch_command_impl",
                side_effect=RuntimeError("boom"),
            ),
            pytest.raises(OSError, match="disk full"),
        ):
            from amplihack.cli import launch_command

            launch_command(_make_args())

    def test_chdir_failure_propagates(self, mock_tracker):
        """If os.chdir fails in finally, its error propagates (not swallowed)."""
        with (
            patch(
                "amplihack.cli._launch_command_impl",
                return_value=0,
            ),
            patch("os.chdir", side_effect=OSError("no such dir")),
            pytest.raises(OSError, match="no such dir"),
        ):
            from amplihack.cli import launch_command

            launch_command(_make_args())

    def test_happy_path_restores_cwd(self, mock_tracker):
        """On success, CWD is restored and complete_session is called."""
        with patch(
            "amplihack.cli._launch_command_impl",
            return_value=0,
        ):
            from amplihack.cli import launch_command

            result = launch_command(_make_args())

        assert result == 0
        mock_tracker.complete_session.assert_called_once_with("sess-001")
