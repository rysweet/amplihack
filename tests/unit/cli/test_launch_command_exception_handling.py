"""Tests for launch_command exception handling (bug #3233).

Verifies that triple-nested exception handling has been flattened:
- crash_session failures propagate (not silently swallowed)
- os.chdir failures propagate (not silently swallowed)
- Original exception is still re-raised from the except block
"""

from __future__ import annotations

import argparse
import os
from unittest.mock import MagicMock, patch

import pytest


def _make_args(**overrides) -> argparse.Namespace:
    """Build a minimal argparse.Namespace for launch_command."""
    defaults = {
        "auto": False,
        "subprocess_safe": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


@pytest.fixture
def mock_tracker():
    tracker = MagicMock()
    tracker.start_session.return_value = "test-session-id"
    return tracker


@pytest.fixture
def _patch_startup():
    """Patch _common_launcher_startup to be a no-op."""
    with patch("amplihack.cli._common_launcher_startup"):
        yield


@pytest.fixture
def _patch_env_cwd(tmp_path):
    """Ensure AMPLIHACK_ORIGINAL_CWD is set so finally-branch runs os.chdir."""
    original = os.environ.get("AMPLIHACK_ORIGINAL_CWD")
    os.environ["AMPLIHACK_ORIGINAL_CWD"] = str(tmp_path)
    yield tmp_path
    if original is None:
        os.environ.pop("AMPLIHACK_ORIGINAL_CWD", None)
    else:
        os.environ["AMPLIHACK_ORIGINAL_CWD"] = original


class TestLaunchCommandExceptionFlattened:
    """Verify the flattened (non-nested) exception handling in launch_command."""

    def test_crash_session_failure_propagates(
        self, mock_tracker, _patch_startup, _patch_env_cwd
    ):
        """crash_session errors must propagate, not be silently swallowed."""
        mock_tracker.crash_session.side_effect = RuntimeError("DB write failed")

        with patch("amplihack.launcher.session_tracker.SessionTracker", return_value=mock_tracker), \
             patch("amplihack.cli._launch_command_impl", side_effect=ValueError("boom")):

            from amplihack.cli import launch_command

            # crash_session raises RuntimeError which should propagate
            # (before the fix, it was caught and swallowed)
            with pytest.raises(RuntimeError, match="DB write failed"):
                launch_command(_make_args())

    def test_chdir_failure_propagates(
        self, mock_tracker, _patch_startup, _patch_env_cwd
    ):
        """os.chdir failures in finally must propagate, not be silently swallowed."""
        with patch("amplihack.launcher.session_tracker.SessionTracker", return_value=mock_tracker), \
             patch("amplihack.cli._launch_command_impl", return_value=0), \
             patch("amplihack.cli.os.chdir", side_effect=OSError("No such directory")):

            from amplihack.cli import launch_command

            # Before the fix, this OSError was caught and logged.
            # After the fix, it propagates.
            with pytest.raises(OSError, match="No such directory"):
                launch_command(_make_args())

    def test_original_exception_reraises_on_impl_failure(
        self, mock_tracker, _patch_startup, _patch_env_cwd
    ):
        """The original exception from _launch_command_impl must still be raised."""
        with patch("amplihack.launcher.session_tracker.SessionTracker", return_value=mock_tracker), \
             patch("amplihack.cli._launch_command_impl", side_effect=ValueError("original error")):

            from amplihack.cli import launch_command

            with pytest.raises(ValueError, match="original error"):
                launch_command(_make_args())

        mock_tracker.crash_session.assert_called_once_with("test-session-id")

    def test_happy_path_completes_session(
        self, mock_tracker, _patch_startup, _patch_env_cwd
    ):
        """On success, complete_session is called and result is returned."""
        with patch("amplihack.launcher.session_tracker.SessionTracker", return_value=mock_tracker), \
             patch("amplihack.cli._launch_command_impl", return_value=0):

            from amplihack.cli import launch_command

            result = launch_command(_make_args())

        assert result == 0
        mock_tracker.complete_session.assert_called_once_with("test-session-id")
        mock_tracker.crash_session.assert_not_called()

    def test_no_nested_try_except_in_source(self):
        """Verify the source code no longer contains nested try/except blocks
        in the launch_command function."""
        import inspect
        from amplihack.cli import launch_command

        source = inspect.getsource(launch_command)

        # There should be no deeply-nested try blocks (8-space indent inside
        # the function body's 4-space try block).
        nested_try = "            try:" in source
        assert not nested_try, (
            "launch_command still contains nested try blocks -- "
            "the triple-nesting bug (#3233) has not been fully fixed"
        )
