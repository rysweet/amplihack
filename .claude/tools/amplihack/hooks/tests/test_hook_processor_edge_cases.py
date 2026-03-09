#!/usr/bin/env python3
"""Edge-case tests for hook_processor.py base class.

Covers: validate_path_containment, read_input, write_output, save_metric,
save_session_data, log rotation, run() error handling, get_session_id.
"""

import json
import os
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Concrete subclass for testing abstract HookProcessor
# ---------------------------------------------------------------------------


def _make_processor(tmp_path, process_return=None, process_side_effect=None):
    """Create a concrete HookProcessor subclass for testing."""
    with patch("hook_processor.HookProcessor.__init__", return_value=None):
        from hook_processor import HookProcessor

        class TestHook(HookProcessor):
            def process(self, input_data):
                if process_side_effect:
                    raise process_side_effect
                return process_return if process_return is not None else {}

        hook = TestHook.__new__(TestHook)
        hook.hook_name = "test_hook"
        hook.project_root = tmp_path

        # Setup directories
        hook.log_dir = tmp_path / ".claude" / "runtime" / "logs"
        hook.metrics_dir = tmp_path / ".claude" / "runtime" / "metrics"
        hook.analysis_dir = tmp_path / ".claude" / "runtime" / "analysis"
        hook.log_dir.mkdir(parents=True, exist_ok=True)
        hook.metrics_dir.mkdir(parents=True, exist_ok=True)
        hook.analysis_dir.mkdir(parents=True, exist_ok=True)
        hook.log_file = hook.log_dir / "test_hook.log"

        return hook


# ============================================================================
# validate_path_containment
# ============================================================================


class TestValidatePathContainment:
    """Security-critical: prevent path traversal."""

    def test_path_within_project_root(self, tmp_path):
        hook = _make_processor(tmp_path)
        sub = tmp_path / "src" / "file.py"
        sub.parent.mkdir(parents=True, exist_ok=True)
        sub.touch()
        result = hook.validate_path_containment(sub)
        assert result == sub.resolve()

    def test_path_traversal_blocked(self, tmp_path):
        hook = _make_processor(tmp_path)
        escape_path = tmp_path / ".." / "etc" / "passwd"
        with pytest.raises(ValueError, match="Path escapes project root"):
            hook.validate_path_containment(escape_path)

    def test_absolute_path_outside_root_blocked(self, tmp_path):
        hook = _make_processor(tmp_path)
        with pytest.raises(ValueError, match="Path escapes project root"):
            hook.validate_path_containment(Path("/etc/passwd"))

    def test_path_with_double_dot_segments(self, tmp_path):
        hook = _make_processor(tmp_path)
        # Create a subdir then traverse out
        (tmp_path / "src").mkdir(exist_ok=True)
        escape_path = tmp_path / "src" / ".." / ".." / "etc" / "passwd"
        with pytest.raises(ValueError, match="Path escapes project root"):
            hook.validate_path_containment(escape_path)

    def test_path_exactly_at_root(self, tmp_path):
        hook = _make_processor(tmp_path)
        result = hook.validate_path_containment(tmp_path)
        assert result == tmp_path.resolve()

    def test_nested_path_valid(self, tmp_path):
        hook = _make_processor(tmp_path)
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True, exist_ok=True)
        result = hook.validate_path_containment(deep)
        assert result == deep.resolve()


# ============================================================================
# read_input
# ============================================================================


class TestReadInput:
    """Input parsing edge cases."""

    def test_valid_json_parsed(self, tmp_path):
        hook = _make_processor(tmp_path)
        with patch("sys.stdin", StringIO('{"key": "value"}')):
            with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                result = hook.read_input()
        assert result == {"key": "value"}

    def test_empty_stdin_returns_empty(self, tmp_path):
        hook = _make_processor(tmp_path)
        with patch("sys.stdin", StringIO("")):
            with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                result = hook.read_input()
        assert result == {}

    def test_whitespace_only_returns_empty(self, tmp_path):
        hook = _make_processor(tmp_path)
        with patch("sys.stdin", StringIO("   \n  ")):
            with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                result = hook.read_input()
        assert result == {}

    def test_invalid_json_returns_empty(self, tmp_path):
        hook = _make_processor(tmp_path)
        with patch("sys.stdin", StringIO("{invalid json}")):
            with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                result = hook.read_input()
        assert result == {}

    def test_shutdown_in_progress_returns_empty(self, tmp_path):
        hook = _make_processor(tmp_path)
        with patch("hook_processor.is_shutdown_in_progress", return_value=True):
            result = hook.read_input()
        assert result == {}

    def test_stdin_oserror_returns_empty(self, tmp_path):
        hook = _make_processor(tmp_path)
        mock_stdin = MagicMock()
        mock_stdin.read.side_effect = OSError("pipe closed")
        with patch("sys.stdin", mock_stdin):
            with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                result = hook.read_input()
        assert result == {}

    def test_stdin_attribute_error_returns_empty(self, tmp_path):
        hook = _make_processor(tmp_path)
        with patch("sys.stdin", None):
            with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                result = hook.read_input()
        assert result == {}

    def test_nested_json_parsed(self, tmp_path):
        hook = _make_processor(tmp_path)
        data = {"toolUse": {"name": "Bash", "input": {"command": "ls"}}}
        with patch("sys.stdin", StringIO(json.dumps(data))):
            with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                result = hook.read_input()
        assert result == data


# ============================================================================
# write_output
# ============================================================================


class TestWriteOutput:
    """Output writing with pipe closure handling."""

    def test_normal_output(self, tmp_path):
        hook = _make_processor(tmp_path)
        buf = StringIO()
        with patch("sys.stdout", buf):
            hook.write_output({"result": "ok"})
        output = buf.getvalue()
        assert '"result": "ok"' in output

    def test_broken_pipe_absorbed(self, tmp_path):
        hook = _make_processor(tmp_path)
        mock_stdout = MagicMock()
        mock_stdout.write = MagicMock()
        with patch("json.dump", side_effect=BrokenPipeError):
            with patch("sys.stdout", mock_stdout):
                hook.write_output({"a": 1})  # Should not raise

    def test_epipe_errno32_absorbed(self, tmp_path):
        hook = _make_processor(tmp_path)
        mock_stdout = MagicMock()
        error = OSError("pipe error")
        error.errno = 32
        with patch("json.dump", side_effect=error):
            with patch("sys.stdout", mock_stdout):
                hook.write_output({"a": 1})  # Should not raise

    def test_epipe_errno_none_absorbed(self, tmp_path):
        hook = _make_processor(tmp_path)
        mock_stdout = MagicMock()
        error = OSError("unknown pipe")
        error.errno = None
        with patch("json.dump", side_effect=error):
            with patch("sys.stdout", mock_stdout):
                hook.write_output({"a": 1})  # Should not raise

    def test_unexpected_oserror_raised(self, tmp_path):
        hook = _make_processor(tmp_path)
        mock_stdout = MagicMock()
        error = OSError("disk full")
        error.errno = 28  # ENOSPC
        with patch("json.dump", side_effect=error):
            with patch("sys.stdout", mock_stdout):
                with pytest.raises(OSError):
                    hook.write_output({"a": 1})

    def test_empty_dict_output(self, tmp_path):
        hook = _make_processor(tmp_path)
        buf = StringIO()
        with patch("sys.stdout", buf):
            hook.write_output({})
        assert "{}" in buf.getvalue()


# ============================================================================
# save_metric
# ============================================================================


class TestSaveMetric:
    """Metric saving edge cases."""

    def test_simple_metric_saved(self, tmp_path):
        hook = _make_processor(tmp_path)
        hook.save_metric("test_metric", 42)
        metrics_file = hook.metrics_dir / "test_hook_metrics.jsonl"
        assert metrics_file.exists()
        data = json.loads(metrics_file.read_text().strip())
        assert data["metric"] == "test_metric"
        assert data["value"] == 42
        assert data["hook"] == "test_hook"

    def test_metric_with_metadata(self, tmp_path):
        hook = _make_processor(tmp_path)
        hook.save_metric("test_metric", "value", metadata={"source": "test"})
        metrics_file = hook.metrics_dir / "test_hook_metrics.jsonl"
        data = json.loads(metrics_file.read_text().strip())
        assert data["metadata"]["source"] == "test"

    def test_metric_write_failure_logged(self, tmp_path):
        hook = _make_processor(tmp_path)
        hook.log = MagicMock()
        with patch("builtins.open", side_effect=OSError("disk full")):
            hook.save_metric("test_metric", 42)  # Should not raise
        hook.log.assert_called()

    def test_multiple_metrics_appended(self, tmp_path):
        hook = _make_processor(tmp_path)
        hook.save_metric("m1", 1)
        hook.save_metric("m2", 2)
        metrics_file = hook.metrics_dir / "test_hook_metrics.jsonl"
        lines = metrics_file.read_text().strip().split("\n")
        assert len(lines) == 2


# ============================================================================
# save_session_data
# ============================================================================


class TestSaveSessionData:
    """Session data saving with path validation."""

    def test_save_dict_data(self, tmp_path):
        hook = _make_processor(tmp_path)
        hook.save_session_data("test.json", {"key": "value"})
        # Verify file was created (in a session-specific directory)
        session_dirs = list(hook.log_dir.iterdir())
        assert any(d.is_dir() for d in session_dirs)

    def test_save_string_data(self, tmp_path):
        hook = _make_processor(tmp_path)
        hook.save_session_data("test.txt", "hello world")

    def test_path_traversal_blocked(self, tmp_path):
        hook = _make_processor(tmp_path)
        with pytest.raises(ValueError, match="no path separators"):
            hook.save_session_data("../etc/passwd", "malicious")

    def test_slash_in_filename_blocked(self, tmp_path):
        hook = _make_processor(tmp_path)
        with pytest.raises(ValueError, match="no path separators"):
            hook.save_session_data("sub/file.txt", "data")

    def test_backslash_in_filename_blocked(self, tmp_path):
        hook = _make_processor(tmp_path)
        with pytest.raises(ValueError, match="no path separators"):
            hook.save_session_data("sub\\file.txt", "data")


# ============================================================================
# log rotation
# ============================================================================


class TestLogRotation:
    """Log file rotation at 10MB."""

    def test_log_under_10mb_appended(self, tmp_path):
        hook = _make_processor(tmp_path)
        hook.log("test message")
        assert hook.log_file.exists()
        content = hook.log_file.read_text()
        assert "test message" in content

    def test_log_rotation_at_10mb(self, tmp_path):
        hook = _make_processor(tmp_path)
        # Create a large log file
        hook.log_file.write_text("x" * (10 * 1024 * 1024 + 1))
        hook.log("new message after rotation")
        # Original file should have been rotated
        backups = list(hook.log_dir.glob("test_hook.*.log"))
        assert len(backups) >= 1

    def test_log_write_failure_doesnt_crash(self, tmp_path):
        hook = _make_processor(tmp_path)
        with patch("builtins.open", side_effect=PermissionError("denied")):
            hook.log("this will fail")  # Should not raise


# ============================================================================
# run() lifecycle & error handling
# ============================================================================


class TestRunLifecycle:
    """Main run() method orchestration."""

    def test_run_with_valid_input(self, tmp_path):
        hook = _make_processor(tmp_path, process_return={"result": "ok"})
        buf = StringIO()
        with patch("sys.stdin", StringIO('{"key": "value"}')):
            with patch("sys.stdout", buf):
                with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                    hook.run()
        output = buf.getvalue()
        assert '"result"' in output

    def test_run_process_returns_none(self, tmp_path):
        hook = _make_processor(tmp_path, process_return=None)
        buf = StringIO()
        with patch("sys.stdin", StringIO("{}")):
            with patch("sys.stdout", buf):
                with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                    hook.run()
        assert "{}" in buf.getvalue()

    def test_run_process_returns_non_dict(self, tmp_path):
        hook = _make_processor(tmp_path, process_return="string_result")
        buf = StringIO()
        with patch("sys.stdin", StringIO("{}")):
            with patch("sys.stdout", buf):
                with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                    hook.run()
        output = json.loads(buf.getvalue().strip())
        assert output == {"result": "string_result"}

    def test_run_generic_exception_fails_open(self, tmp_path):
        hook = _make_processor(
            tmp_path, process_side_effect=RuntimeError("unexpected")
        )
        buf = StringIO()
        with patch("sys.stdin", StringIO("{}")):
            with patch("sys.stdout", buf):
                with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                    hook.run()
        # Should output empty dict (fail-open)
        assert "{}" in buf.getvalue()

    def test_run_json_decode_error_fails_open(self, tmp_path):
        hook = _make_processor(
            tmp_path,
            process_side_effect=json.JSONDecodeError("msg", "doc", 0),
        )
        buf = StringIO()
        with patch("sys.stdin", StringIO("{}")):
            with patch("sys.stdout", buf):
                with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                    hook.run()
        assert "{}" in buf.getvalue()

    def test_run_hook_exception_fails_open(self, tmp_path):
        from error_protocol import HookError, HookErrorSeverity, HookException

        error = HookError(
            severity=HookErrorSeverity.ERROR,
            message="test error",
        )
        hook = _make_processor(
            tmp_path,
            process_side_effect=HookException(error),
        )
        buf = StringIO()
        with patch("sys.stdin", StringIO("{}")):
            with patch("sys.stdout", buf):
                with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                    hook.run()
        assert "{}" in buf.getvalue()

    def test_run_debug_mode_shows_traceback(self, tmp_path):
        hook = _make_processor(
            tmp_path, process_side_effect=RuntimeError("debug error")
        )
        buf = StringIO()
        err = StringIO()
        with patch("sys.stdin", StringIO("{}")):
            with patch("sys.stdout", buf):
                with patch("sys.stderr", err):
                    with patch("hook_processor.is_shutdown_in_progress", return_value=False):
                        with patch.dict(os.environ, {"AMPLIHACK_DEBUG": "1"}):
                            hook.run()
        assert "Stack trace" in err.getvalue()


# ============================================================================
# get_session_id
# ============================================================================


class TestGetSessionId:
    """Session ID generation."""

    def test_session_id_format(self, tmp_path):
        hook = _make_processor(tmp_path)
        sid = hook.get_session_id()
        # Format: YYYYMMDD_HHMMSS_ffffff
        parts = sid.split("_")
        assert len(parts) == 3
        assert len(parts[0]) == 8  # date
        assert len(parts[1]) == 6  # time
        assert len(parts[2]) == 6  # microseconds

    def test_session_ids_unique(self, tmp_path):
        hook = _make_processor(tmp_path)
        ids = {hook.get_session_id() for _ in range(10)}
        # All should be unique (microsecond resolution)
        assert len(ids) == 10


# ============================================================================
# _write_error_to_stderr
# ============================================================================


class TestWriteErrorToStderr:
    """Structured error output."""

    def test_error_written_to_stderr(self, tmp_path):
        hook = _make_processor(tmp_path)
        from error_protocol import HookError, HookErrorSeverity

        error = HookError(
            severity=HookErrorSeverity.WARNING,
            message="test warning",
            context="test context",
            suggestion="try again",
        )
        err = StringIO()
        with patch("sys.stderr", err):
            hook._write_error_to_stderr(error)
        output = err.getvalue()
        assert "HOOK ERROR" in output
        assert "test warning" in output
        assert "test context" in output
        assert "try again" in output

    def test_error_without_optional_fields(self, tmp_path):
        hook = _make_processor(tmp_path)
        from error_protocol import HookError, HookErrorSeverity

        error = HookError(
            severity=HookErrorSeverity.ERROR,
            message="bare error",
        )
        err = StringIO()
        with patch("sys.stderr", err):
            hook._write_error_to_stderr(error)
        output = err.getvalue()
        assert "bare error" in output
