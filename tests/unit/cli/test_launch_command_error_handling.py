"""Tests for launch_command exception handling (issue #3233).

Verifies that the crash handler uses a flat try/except/finally
instead of triple-nested exception handling, and that failures
in crash_session() and os.chdir() propagate instead of being swallowed.
"""

from __future__ import annotations

import argparse
import os
from unittest.mock import MagicMock, patch

import pytest


def _make_args():
    """Minimal args namespace for launch_command."""
    ns = argparse.Namespace()
    ns.auto = False
    ns._nesting_result = None
    return ns


# Patch the local import path used inside launch_command
TRACKER_PATH = "amplihack.launcher.session_tracker.SessionTracker"


class TestLaunchCommandErrorHandling:
    """Verify flat exception handling in launch_command (issue #3233)."""

    @patch("amplihack.cli._launch_command_impl", side_effect=RuntimeError("boom"))
    @patch("amplihack.cli._common_launcher_startup")
    @patch(TRACKER_PATH)
    def test_crash_session_failure_propagates(
        self, mock_tracker_cls, mock_startup, mock_impl
    ):
        """crash_session() errors must propagate, not be silently swallowed."""
        from amplihack.cli import launch_command

        tracker_instance = MagicMock()
        tracker_instance.start_session.return_value = "sess-1"
        tracker_instance.crash_session.side_effect = OSError("db write failed")
        mock_tracker_cls.return_value = tracker_instance

        # crash_session raises OSError; since it's no longer wrapped in
        # try/except, the OSError propagates (not the original RuntimeError).
        with pytest.raises(OSError, match="db write failed"):
            launch_command(_make_args())

        tracker_instance.crash_session.assert_called_once_with("sess-1")

    @patch("amplihack.cli._launch_command_impl", side_effect=RuntimeError("boom"))
    @patch("amplihack.cli._common_launcher_startup")
    @patch(TRACKER_PATH)
    def test_original_error_propagates_when_crash_session_succeeds(
        self, mock_tracker_cls, mock_startup, mock_impl
    ):
        """When crash_session succeeds, the original exception re-raises."""
        from amplihack.cli import launch_command

        tracker_instance = MagicMock()
        tracker_instance.start_session.return_value = "sess-2"
        mock_tracker_cls.return_value = tracker_instance

        with pytest.raises(RuntimeError, match="boom"):
            launch_command(_make_args())

        tracker_instance.crash_session.assert_called_once_with("sess-2")

    @patch("amplihack.cli._launch_command_impl", return_value=0)
    @patch("amplihack.cli._common_launcher_startup")
    @patch(TRACKER_PATH)
    @patch("os.chdir")
    def test_chdir_failure_propagates_in_finally(
        self, mock_chdir, mock_tracker_cls, mock_startup, mock_impl
    ):
        """os.chdir failure in finally must propagate, not be swallowed."""
        from amplihack.cli import launch_command

        tracker_instance = MagicMock()
        tracker_instance.start_session.return_value = "sess-3"
        mock_tracker_cls.return_value = tracker_instance

        mock_chdir.side_effect = OSError("no such directory")

        with patch.dict(os.environ, {"AMPLIHACK_ORIGINAL_CWD": "/nonexistent"}):
            with pytest.raises(OSError, match="no such directory"):
                launch_command(_make_args())

    @patch("amplihack.cli._launch_command_impl", return_value=0)
    @patch("amplihack.cli._common_launcher_startup")
    @patch(TRACKER_PATH)
    def test_successful_execution_completes_session(
        self, mock_tracker_cls, mock_startup, mock_impl
    ):
        """Happy path: session is completed, not crashed."""
        from amplihack.cli import launch_command

        tracker_instance = MagicMock()
        tracker_instance.start_session.return_value = "sess-4"
        mock_tracker_cls.return_value = tracker_instance

        result = launch_command(_make_args())

        assert result == 0
        tracker_instance.complete_session.assert_called_once_with("sess-4")
        tracker_instance.crash_session.assert_not_called()

    @patch("amplihack.cli._launch_command_impl", side_effect=RuntimeError("boom"))
    @patch("amplihack.cli._common_launcher_startup")
    @patch(TRACKER_PATH)
    def test_logger_debug_called_on_error(
        self, mock_tracker_cls, mock_startup, mock_impl
    ):
        """logger.debug (not logging.debug) is called with session error info."""
        from amplihack.cli import launch_command

        tracker_instance = MagicMock()
        tracker_instance.start_session.return_value = "sess-5"
        mock_tracker_cls.return_value = tracker_instance

        with patch("amplihack.cli.logger") as mock_logger:
            with pytest.raises(RuntimeError, match="boom"):
                launch_command(_make_args())

            # Verify logger.debug was called (not logging.debug)
            mock_logger.debug.assert_called_once()
            call_msg = mock_logger.debug.call_args[0][0]
            assert "sess-5" in call_msg
            assert "RuntimeError" in call_msg
