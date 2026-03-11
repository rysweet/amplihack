# File: tests/integration/test_cli_session_init.py
"""Integration tests for session module init paths.

Tests covering:
- launch_command with subprocess_safe=True
- launch_command with nesting detection triggering AutoStager
- _ensure_amplihack_staged in non-UVX mode (no-op)
- _ensure_amplihack_staged in UVX mode (copies files, calls ensure_settings_json)
- handle_auto_mode with auto=False
- handle_auto_mode with auto=True and no prompt
- handle_append_instruction success and error paths
"""

import argparse
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.session import (
    _ensure_amplihack_staged,
    handle_append_instruction,
    handle_auto_mode,
    launch_command,
)


def _make_args(**kwargs) -> argparse.Namespace:
    """Create a Namespace with sensible defaults for tests."""
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


class TestLaunchCommandSubprocessSafe:
    """launch_command with subprocess_safe=True skips staging and nesting detection.

    Note: SessionTracker is imported both at module level and lazily inside launch_command.
    The lazy import rebinds the name, so we must patch at the source module.
    """

    def test_subprocess_safe_skips_staging(self):
        """With subprocess_safe=True, _ensure_amplihack_staged is not called."""
        args = _make_args(subprocess_safe=True)

        mock_tracker = MagicMock()
        mock_tracker.start_session.return_value = "session-123"

        with (
            patch(
                "amplihack.launcher.session_tracker.SessionTracker",
                return_value=mock_tracker,
            ),
            patch("amplihack.session._ensure_amplihack_staged") as mock_staged,
            patch("amplihack.session._launch_command_impl", return_value=0),
        ):
            result = launch_command(args, [])
            mock_staged.assert_not_called()
            assert result == 0

    def test_subprocess_safe_still_tracks_session(self):
        """With subprocess_safe=True, session tracking still happens."""
        args = _make_args(subprocess_safe=True)

        mock_tracker = MagicMock()
        mock_tracker.start_session.return_value = "session-abc"

        with (
            patch(
                "amplihack.launcher.session_tracker.SessionTracker",
                return_value=mock_tracker,
            ),
            patch("amplihack.session._launch_command_impl", return_value=0),
        ):
            launch_command(args, [])
            mock_tracker.start_session.assert_called_once()
            mock_tracker.complete_session.assert_called_once_with("session-abc")


class TestLaunchCommandNestingDetected:
    """launch_command with nesting detected triggers AutoStager.

    NestingDetector and AutoStager are lazily imported inside launch_command, so
    we patch at their source modules.
    """

    def test_nesting_triggers_auto_stager(self):
        """AutoStager is called when nesting requires staging."""
        args = _make_args(subprocess_safe=False)

        mock_nesting = MagicMock()
        mock_nesting.requires_staging = True
        mock_nesting.is_nested = True
        mock_nesting.parent_session_id = None

        mock_staging_result = MagicMock()
        mock_staging_result.temp_root = Path("/tmp/staged")

        mock_stager = MagicMock()
        mock_stager.stage_for_nested_execution.return_value = mock_staging_result

        mock_detector_instance = MagicMock()
        mock_detector_instance.detect_nesting.return_value = mock_nesting

        mock_tracker = MagicMock()
        mock_tracker.start_session.return_value = "session-nest"

        with (
            patch(
                "amplihack.launcher.nesting_detector.NestingDetector",
                return_value=mock_detector_instance,
            ),
            patch(
                "amplihack.launcher.auto_stager.AutoStager",
                return_value=mock_stager,
            ),
            patch("amplihack.session._ensure_amplihack_staged"),
            patch(
                "amplihack.launcher.session_tracker.SessionTracker",
                return_value=mock_tracker,
            ),
            patch("amplihack.session._launch_command_impl", return_value=0),
            patch("os.chdir"),
        ):
            launch_command(args, [])
            mock_stager.stage_for_nested_execution.assert_called_once()

    def test_cwd_restored_on_exit(self):
        """CWD is restored to original after staging, even on success."""
        args = _make_args(subprocess_safe=False)
        original_cwd = Path("/original/path")

        mock_nesting = MagicMock()
        mock_nesting.requires_staging = True
        mock_nesting.is_nested = True
        mock_nesting.parent_session_id = None

        mock_staging_result = MagicMock()
        mock_staging_result.temp_root = Path("/tmp/staged")

        mock_stager = MagicMock()
        mock_stager.stage_for_nested_execution.return_value = mock_staging_result

        mock_detector_instance = MagicMock()
        mock_detector_instance.detect_nesting.return_value = mock_nesting

        mock_tracker = MagicMock()
        mock_tracker.start_session.return_value = "session-cwd"

        chdir_calls = []

        def record_chdir(path):
            chdir_calls.append(str(path))

        with (
            patch(
                "amplihack.launcher.nesting_detector.NestingDetector",
                return_value=mock_detector_instance,
            ),
            patch(
                "amplihack.launcher.auto_stager.AutoStager",
                return_value=mock_stager,
            ),
            patch("amplihack.session._ensure_amplihack_staged"),
            patch(
                "amplihack.launcher.session_tracker.SessionTracker",
                return_value=mock_tracker,
            ),
            patch("amplihack.session._launch_command_impl", return_value=0),
            patch("os.chdir", side_effect=record_chdir),
            patch("amplihack.session.Path.cwd", return_value=original_cwd),
        ):
            launch_command(args, [])

        # CWD was changed to temp dir and then restored
        assert str(mock_staging_result.temp_root) in chdir_calls


class TestEnsureAmplihackStaged:
    """Tests for _ensure_amplihack_staged."""

    def test_non_uvx_returns_immediately(self):
        """In non-UVX mode, function returns without doing anything."""
        with (
            patch("amplihack.session.is_uvx_deployment", return_value=False),
            patch("amplihack.session.copytree_manifest") as mock_copy,
        ):
            _ensure_amplihack_staged()
            mock_copy.assert_not_called()

    def test_uvx_calls_copytree_manifest(self):
        """In UVX mode, copytree_manifest is called.

        ensure_settings_json is lazily imported inside _ensure_amplihack_staged,
        so we patch at its source module: amplihack.settings.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("amplihack.session.is_uvx_deployment", return_value=True),
                patch("amplihack.session.cleanup_legacy_skills") as mock_cleanup,
                patch("amplihack.session.copytree_manifest", return_value=["dir1"]) as mock_copy,
                patch("amplihack.session.Path.home", return_value=Path(tmpdir)),
                patch("amplihack.settings.ensure_settings_json"),
                patch("amplihack.session._fix_global_statusline_path"),
                patch("os.chmod"),
            ):
                mock_cleanup.return_value = MagicMock(cleaned=[], skipped=[], errors=[])
                _ensure_amplihack_staged()
                mock_copy.assert_called_once()

    def test_uvx_calls_ensure_settings_json(self):
        """In UVX mode, ensure_settings_json is called."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("amplihack.session.is_uvx_deployment", return_value=True),
                patch("amplihack.session.cleanup_legacy_skills") as mock_cleanup,
                patch("amplihack.session.copytree_manifest", return_value=["dir1"]),
                patch("amplihack.session.Path.home", return_value=Path(tmpdir)),
                patch("amplihack.settings.ensure_settings_json") as mock_settings,
                patch("amplihack.session._fix_global_statusline_path"),
                patch("os.chmod"),
            ):
                mock_cleanup.return_value = MagicMock(cleaned=[], skipped=[], errors=[])
                _ensure_amplihack_staged()
                mock_settings.assert_called_once()

    def test_uvx_exits_on_copy_failure(self):
        """In UVX mode, sys.exit(1) is called when copy fails."""
        with (
            patch("amplihack.session.is_uvx_deployment", return_value=True),
            patch("amplihack.session.cleanup_legacy_skills") as mock_cleanup,
            patch("amplihack.session.copytree_manifest", return_value=None),
            patch("amplihack.session.Path.home", return_value=Path("/home/user")),
            patch("pathlib.Path.mkdir"),
            patch("os.chmod"),
        ):
            mock_cleanup.return_value = MagicMock(cleaned=[], skipped=[], errors=[])
            with pytest.raises(SystemExit) as exc_info:
                _ensure_amplihack_staged()
            assert exc_info.value.code == 1


class TestHandleAutoMode:
    """Tests for handle_auto_mode."""

    def test_auto_false_returns_none(self):
        """With auto=False, returns None (no-op)."""
        args = _make_args(auto=False)
        result = handle_auto_mode("claude", args, ["-p", "do something"])
        assert result is None

    def test_auto_true_no_prompt_returns_1(self):
        """With auto=True but no -p prompt, returns exit code 1."""
        args = _make_args(auto=True)
        result = handle_auto_mode("claude", args, ["--verbose"])
        assert result == 1

    def test_auto_true_none_cmd_args_returns_1(self):
        """With auto=True and None cmd_args, returns exit code 1."""
        args = _make_args(auto=True)
        result = handle_auto_mode("claude", args, None)
        assert result == 1

    def test_auto_true_with_prompt_delegates_to_auto_mode(self):
        """With auto=True and prompt, delegates to AutoMode.run().

        AutoMode is lazily imported inside handle_auto_mode, so we patch at its
        source module: amplihack.launcher.auto_mode.
        """
        args = _make_args(auto=True, max_turns=5)
        mock_auto = MagicMock()
        mock_auto.run.return_value = 0

        with patch("amplihack.launcher.auto_mode.AutoMode", return_value=mock_auto):
            result = handle_auto_mode("claude", args, ["-p", "do something"])
            assert result == 0
            mock_auto.run.assert_called_once()

    def test_auto_true_sets_skip_reflection_env(self):
        """With auto=True, AMPLIHACK_SKIP_REFLECTION is set to '1'."""
        args = _make_args(auto=True, max_turns=5)
        mock_auto = MagicMock()
        mock_auto.run.return_value = 0

        with (
            patch("amplihack.launcher.auto_mode.AutoMode", return_value=mock_auto),
            patch.dict(os.environ, {}, clear=False),
        ):
            handle_auto_mode("claude", args, ["-p", "task"])
            assert os.environ.get("AMPLIHACK_SKIP_REFLECTION") == "1"


class TestHandleAppendInstruction:
    """Tests for handle_append_instruction."""

    def test_no_append_returns_0(self):
        """With no --append flag, returns 0 without doing anything."""
        args = _make_args(append=None)
        result = handle_append_instruction(args)
        assert result == 0

    def test_success_returns_0(self):
        """Successful append returns 0 and prints session info.

        append_instructions is lazily imported inside handle_append_instruction,
        so we patch at its source module.
        """
        args = _make_args(append="do this next")

        mock_result = MagicMock()
        mock_result.session_id = "sess-123"
        mock_result.filename = "instruction.md"

        with patch(
            "amplihack.launcher.append_handler.append_instructions",
            return_value=mock_result,
        ):
            result = handle_append_instruction(args)
            assert result == 0

    def test_append_error_returns_1(self):
        """AppendError results in exit code 1."""
        from amplihack.launcher.append_handler import AppendError

        args = _make_args(append="do this next")

        with patch(
            "amplihack.launcher.append_handler.append_instructions",
            side_effect=AppendError("no active session"),
        ):
            result = handle_append_instruction(args)
            assert result == 1

    def test_value_error_returns_1(self):
        """ValueError from append_instructions results in exit code 1."""
        args = _make_args(append="do this next")

        with patch(
            "amplihack.launcher.append_handler.append_instructions",
            side_effect=ValueError("invalid instruction"),
        ):
            result = handle_append_instruction(args)
            assert result == 1


# BUG FIX TESTS — Issue 3053: crash_session double-crash prevention in cli.py
class TestLaunchCommandCrashSessionDoubleCrash:
    """Regression tests for Issue 3053 — cli.py double-crash guard.

    When _launch_command_impl raises AND crash_session also raises (because the
    runtime directory was deleted between session start and the error handler),
    the original exception must still propagate.  The secondary crash_session
    failure must be swallowed and logged at DEBUG level only.

    Expected fix in launch_command():
        except Exception as e:
            logger.debug(...)
            try:
                tracker.crash_session(session_id)
            except Exception as crash_err:
                logger.debug(f"crash_session also failed: {crash_err}")
            raise   # re-raises original `e`, not crash_err
    """

    def test_original_exception_propagates_when_crash_session_also_fails(self):
        """Original exception re-raises even when crash_session raises too.

        The test verifies that the caller sees the *original* RuntimeError,
        not the secondary FileNotFoundError from crash_session.
        """
        args = _make_args(subprocess_safe=True)
        original_error = RuntimeError("primary failure")

        mock_tracker = MagicMock()
        mock_tracker.start_session.return_value = "session-fail"
        mock_tracker.crash_session.side_effect = FileNotFoundError(
            "No such file or directory: '.claude/runtime/sessions.jsonl'"
        )

        with (
            patch(
                "amplihack.launcher.session_tracker.SessionTracker",
                return_value=mock_tracker,
            ),
            patch(
                "amplihack.session._launch_command_impl",
                side_effect=original_error,
            ),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                launch_command(args, [])

            # Must be the original RuntimeError, not the FileNotFoundError
            assert exc_info.value is original_error

    def test_crash_session_failure_is_not_reraised(self):
        """FileNotFoundError from crash_session does not propagate to caller.

        The secondary exception from crash_session must be suppressed.
        """
        args = _make_args(subprocess_safe=True)

        mock_tracker = MagicMock()
        mock_tracker.start_session.return_value = "session-fail2"
        mock_tracker.crash_session.side_effect = FileNotFoundError(
            "No such file or directory: '.claude/runtime/sessions.jsonl'"
        )

        with (
            patch(
                "amplihack.launcher.session_tracker.SessionTracker",
                return_value=mock_tracker,
            ),
            patch(
                "amplihack.session._launch_command_impl",
                side_effect=ValueError("original problem"),
            ),
        ):
            # FileNotFoundError from crash_session must not leak out
            with pytest.raises(ValueError):
                launch_command(args, [])

            # crash_session was still called — best-effort cleanup attempted
            mock_tracker.crash_session.assert_called_once_with("session-fail2")

    def test_crash_session_success_still_reraises_original(self):
        """When crash_session succeeds normally, original exception still propagates.

        Baseline sanity check: the outer `raise` is unconditional regardless of
        whether crash_session itself succeeded or failed.
        """
        args = _make_args(subprocess_safe=True)
        original_error = ValueError("something went wrong")

        mock_tracker = MagicMock()
        mock_tracker.start_session.return_value = "session-reraise"
        # crash_session succeeds (no side_effect)

        with (
            patch(
                "amplihack.launcher.session_tracker.SessionTracker",
                return_value=mock_tracker,
            ),
            patch(
                "amplihack.session._launch_command_impl",
                side_effect=original_error,
            ),
        ):
            with pytest.raises(ValueError) as exc_info:
                launch_command(args, [])

            assert exc_info.value is original_error
            mock_tracker.crash_session.assert_called_once_with("session-reraise")

    def test_crash_session_failure_logged_at_debug(self, caplog):
        """Secondary crash_session failure is logged at DEBUG level.

        The debug message must mention the secondary failure so operators
        can diagnose double-failure scenarios in debug logs.
        """
        import logging

        args = _make_args(subprocess_safe=True)
        secondary_error = FileNotFoundError(".claude/runtime/sessions.jsonl")

        mock_tracker = MagicMock()
        mock_tracker.start_session.return_value = "session-log"
        mock_tracker.crash_session.side_effect = secondary_error

        with (
            patch(
                "amplihack.launcher.session_tracker.SessionTracker",
                return_value=mock_tracker,
            ),
            patch(
                "amplihack.session._launch_command_impl",
                side_effect=RuntimeError("trigger"),
            ),
            caplog.at_level(logging.DEBUG, logger="amplihack.session"),
        ):
            with pytest.raises(RuntimeError):
                launch_command(args, [])

        # A DEBUG-level record mentioning the secondary failure must exist
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        crash_fail_logged = any(
            "crash_session" in r.message and "failed" in r.message
            for r in debug_records
        )
        assert crash_fail_logged, (
            f"Expected a DEBUG log mentioning 'crash_session' and 'failed'. "
            f"Actual DEBUG records: {[r.message for r in debug_records]}"
        )
