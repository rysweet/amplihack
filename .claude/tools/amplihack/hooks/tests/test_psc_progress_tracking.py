# File: amplifier-bundle/tools/amplihack/hooks/tests/test_psc_progress_tracking.py
"""Tests for power_steering_checker.progress_tracking module.

Tests _write_with_retry, _validate_session_id (REQ-SEC-1),
MAX_LINE_BYTES (REQ-SEC-3), semaphore operations,
redirect file handling, atomic creation (REQ-SEC-6), OSError logging (REQ-SEC-5).
"""

import errno
import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker.progress_tracking import (
    MAX_LINE_BYTES,
    ProgressTrackingMixin,
    _validate_session_id,
    _write_with_retry,
)


class TestValidateSessionId:
    """Tests for _validate_session_id() (REQ-SEC-1)."""

    def test_valid_alphanumeric(self):
        assert _validate_session_id("abc123") is True

    def test_valid_with_hyphens(self):
        assert _validate_session_id("session-123-abc") is True

    def test_valid_with_underscores(self):
        assert _validate_session_id("session_123_abc") is True

    def test_valid_uuid_like(self):
        assert _validate_session_id("550e8400-e29b-41d4-a716-446655440000") is True

    def test_valid_max_length(self):
        # 128 chars is valid
        assert _validate_session_id("a" * 128) is True

    def test_rejects_too_long(self):
        # 129 chars is invalid
        assert _validate_session_id("a" * 129) is False

    def test_rejects_empty_string(self):
        assert _validate_session_id("") is False

    def test_rejects_path_traversal(self):
        """REQ-SEC-1: Prevent path traversal via ../etc/passwd."""
        assert _validate_session_id("../../etc/passwd") is False

    def test_rejects_slash(self):
        assert _validate_session_id("session/id") is False

    def test_rejects_dot(self):
        assert _validate_session_id("session.id") is False

    def test_rejects_space(self):
        assert _validate_session_id("session id") is False

    def test_rejects_null_byte(self):
        assert _validate_session_id("session\x00id") is False

    def test_returns_bool_not_exception(self):
        """_validate_session_id should return bool, not raise."""
        result = _validate_session_id("../../../bad")
        assert isinstance(result, bool)
        assert result is False

    def test_single_char_valid(self):
        assert _validate_session_id("a") is True


class TestMaxLineBytes:
    """Tests for MAX_LINE_BYTES constant (REQ-SEC-3)."""

    def test_max_line_bytes_exists(self):
        assert MAX_LINE_BYTES is not None

    def test_max_line_bytes_is_int(self):
        assert isinstance(MAX_LINE_BYTES, int)

    def test_max_line_bytes_is_10mb(self):
        assert MAX_LINE_BYTES == 10 * 1024 * 1024

    def test_max_line_bytes_positive(self):
        assert MAX_LINE_BYTES > 0


class TestWriteWithRetry:
    """Tests for _write_with_retry function."""

    def test_writes_file(self, tmp_path):
        filepath = tmp_path / "test.txt"
        _write_with_retry(filepath, "hello")
        assert filepath.read_text() == "hello"

    def test_appends_in_append_mode(self, tmp_path):
        filepath = tmp_path / "test.txt"
        _write_with_retry(filepath, "line1\n")
        _write_with_retry(filepath, "line2\n", mode="a")
        content = filepath.read_text()
        assert "line1" in content
        assert "line2" in content

    def test_creates_parent_dirs(self, tmp_path):
        filepath = tmp_path / "sub" / "dir" / "test.txt"
        _write_with_retry(filepath, "data")
        assert filepath.exists()

    def test_raises_on_persistent_error(self, tmp_path):
        """After max retries, non-transient OSError propagates."""
        filepath = tmp_path / "test.txt"
        with patch.object(
            Path, "write_text", side_effect=OSError(errno.EACCES, "Permission denied")
        ):
            with pytest.raises(OSError):
                _write_with_retry(filepath, "data")


class MockChecker(ProgressTrackingMixin):
    """Concrete mock class to test ProgressTrackingMixin methods."""

    def __init__(self, tmp_path):
        self.runtime_dir = tmp_path / "runtime"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.project_root = tmp_path
        self.considerations = []
        self._log_messages = []

    def _log(self, message, level="INFO", exc_info=False):
        self._log_messages.append((level, message, exc_info))
        if exc_info:
            logging.getLogger(__name__).warning(message, exc_info=exc_info)

    def _validate_path(self, path, root):
        try:
            path.resolve().relative_to(root.resolve())
            return True
        except ValueError:
            return False


class TestAlreadyRan:
    """Tests for _already_ran() with session ID validation."""

    def test_returns_false_when_no_semaphore(self, tmp_path):
        checker = MockChecker(tmp_path)
        assert checker._already_ran("session123") is False

    def test_returns_true_when_semaphore_exists(self, tmp_path):
        checker = MockChecker(tmp_path)
        semaphore = checker.runtime_dir / ".session123_completed"
        semaphore.touch()
        assert checker._already_ran("session123") is True

    def test_rejects_invalid_session_id(self, tmp_path):
        """REQ-SEC-1: Invalid session ID should fail safely."""
        checker = MockChecker(tmp_path)
        # Path traversal attempt should be rejected (not raise)
        result = checker._already_ran("../../etc/passwd")
        # Should return False (safe default) not raise
        assert result is False


class TestMarkComplete:
    """Tests for _mark_complete() with atomic creation (REQ-SEC-6)."""

    def test_creates_semaphore_file(self, tmp_path):
        checker = MockChecker(tmp_path)
        checker._mark_complete("session123")
        semaphore = checker.runtime_dir / ".session123_completed"
        assert semaphore.exists()

    def test_semaphore_has_restrictive_permissions(self, tmp_path):
        checker = MockChecker(tmp_path)
        checker._mark_complete("session123")
        semaphore = checker.runtime_dir / ".session123_completed"
        mode = oct(semaphore.stat().st_mode & 0o777)
        assert mode == oct(0o600)

    def test_logs_warning_on_oserror(self, tmp_path):
        """REQ-SEC-5: OSError should be logged, not silently swallowed."""
        checker = MockChecker(tmp_path)
        with patch("os.open", side_effect=OSError(errno.ENOSPC, "No space left")):
            checker._mark_complete("session123")
        # Should have logged a warning
        warning_messages = [m for m in checker._log_messages if m[0] == "WARNING"]
        assert len(warning_messages) > 0

    def test_rejects_invalid_session_id(self, tmp_path):
        checker = MockChecker(tmp_path)
        # Should not create file with path traversal
        checker._mark_complete("../../bad")
        assert not any(checker.runtime_dir.glob("*bad*"))


class TestMarkResultsShown:
    """Tests for _mark_results_shown() with atomic creation (REQ-SEC-6)."""

    def test_creates_semaphore_file(self, tmp_path):
        checker = MockChecker(tmp_path)
        checker._mark_results_shown("session123")
        semaphore = checker.runtime_dir / ".session123_results_shown"
        assert semaphore.exists()

    def test_semaphore_has_restrictive_permissions(self, tmp_path):
        checker = MockChecker(tmp_path)
        checker._mark_results_shown("session123")
        semaphore = checker.runtime_dir / ".session123_results_shown"
        mode = oct(semaphore.stat().st_mode & 0o777)
        assert mode == oct(0o600)

    def test_logs_warning_on_oserror(self, tmp_path):
        """REQ-SEC-5: OSError should be logged."""
        checker = MockChecker(tmp_path)
        with patch("os.open", side_effect=OSError(errno.ENOSPC, "No space")):
            checker._mark_results_shown("session123")
        warning_messages = [m for m in checker._log_messages if m[0] == "WARNING"]
        assert len(warning_messages) > 0


class TestGetRedirectFile:
    """Tests for _get_redirect_file() with session ID validation."""

    def test_returns_path_for_valid_id(self, tmp_path):
        checker = MockChecker(tmp_path)
        path = checker._get_redirect_file("session123")
        assert isinstance(path, Path)
        assert "session123" in str(path)

    def test_rejects_path_traversal(self, tmp_path):
        """REQ-SEC-1: Path traversal in session ID should be rejected."""
        checker = MockChecker(tmp_path)
        # Should not return a path that goes outside runtime_dir
        result = checker._get_redirect_file("../../etc")
        # The path returned (if any) should still be safe OR raise
        # Per design, it returns a safe path or logs a warning
        if result is not None:
            # Check it's still within project boundaries
            assert ".." not in str(result).replace(str(tmp_path), "")


class TestWriteSummaryOsErrorLogging:
    """Tests for _write_summary() OSError logging (REQ-SEC-5)."""

    def test_logs_oserror_in_write_summary(self, tmp_path):
        """REQ-SEC-5: _write_summary silent OSError should now log a warning."""
        checker = MockChecker(tmp_path)
        with patch(
            "power_steering_checker.progress_tracking._write_with_retry",
            side_effect=OSError(errno.ENOSPC, "No space"),
        ):
            checker._write_summary("session123", "summary content")
        warning_messages = [m for m in checker._log_messages if m[0] == "WARNING"]
        assert len(warning_messages) > 0
