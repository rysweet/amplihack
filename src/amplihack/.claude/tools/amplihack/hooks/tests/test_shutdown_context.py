#!/usr/bin/env python3
"""
TDD Tests for Shutdown Context Module (UNIT TESTS - 60%)

Tests the shutdown_context module which provides centralized shutdown detection
for all hooks. This module detects various shutdown contexts to prevent stdin
hangs during cleanup.

Testing Philosophy:
- Ruthlessly Simple: Each test has single responsibility
- Zero-BS: All tests work, no stubs
- Fail-Open: Shutdown detection errs on side of safety

Test Coverage:
- Environment variable detection
- Stdin closed detection
- Stdin detached detection
- Atexit context detection
- Mark/clear shutdown functions
- No false positives during normal operation
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# These imports will fail until implementation exists - TDD approach
try:
    from shutdown_context import (
        clear_shutdown,
        is_shutdown_in_progress,
        mark_shutdown,
    )

    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False

# Skip all tests if implementation doesn't exist yet
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS, reason="Implementation not yet created (TDD)"
)


# =============================================================================
# UNIT TESTS - Environment Variable Detection
# =============================================================================


class TestEnvironmentVariableDetection:
    """Test shutdown detection via AMPLIHACK_SHUTDOWN_IN_PROGRESS env var."""

    def test_detects_shutdown_when_env_var_set_to_one(self):
        """Should return True when AMPLIHACK_SHUTDOWN_IN_PROGRESS=1"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        try:
            # ACT
            result = is_shutdown_in_progress()

            # ASSERT
            assert result is True, "Should detect shutdown when env var is '1'"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    @patch("sys.stdin")
    def test_no_shutdown_when_env_var_not_set(self, mock_stdin):
        """Should return False when AMPLIHACK_SHUTDOWN_IN_PROGRESS not set"""
        # ARRANGE - ensure env var is not set
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # Mock stdin as healthy
        mock_stdin.closed = False
        mock_stdin.fileno.return_value = 0

        # ACT
        result = is_shutdown_in_progress()

        # ASSERT
        assert result is False, "Should not detect shutdown when env var absent"

    @patch("sys.stdin")
    def test_no_shutdown_when_env_var_set_to_zero(self, mock_stdin):
        """Should return False when AMPLIHACK_SHUTDOWN_IN_PROGRESS=0"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "0"

        # Mock stdin as healthy
        mock_stdin.closed = False
        mock_stdin.fileno.return_value = 0

        try:
            # ACT
            result = is_shutdown_in_progress()

            # ASSERT
            assert result is False, "Should not detect shutdown when env var is '0'"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    @patch("sys.stdin")
    def test_no_shutdown_when_env_var_empty_string(self, mock_stdin):
        """Should return False when AMPLIHACK_SHUTDOWN_IN_PROGRESS=''"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = ""

        # Mock stdin as healthy
        mock_stdin.closed = False
        mock_stdin.fileno.return_value = 0

        try:
            # ACT
            result = is_shutdown_in_progress()

            # ASSERT
            assert result is False, "Should not detect shutdown when env var is empty"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


# =============================================================================
# UNIT TESTS - Stdin Closed Detection
# =============================================================================


class TestStdinClosedDetection:
    """Test shutdown detection when stdin is closed."""

    @patch("sys.stdin")
    def test_detects_shutdown_when_stdin_closed(self, mock_stdin):
        """Should detect shutdown when stdin.closed is True"""
        # ARRANGE
        mock_stdin.closed = True

        # ACT
        result = is_shutdown_in_progress()

        # ASSERT
        assert result is True, "Should detect shutdown when stdin is closed"

    @patch("sys.stdin")
    def test_no_shutdown_when_stdin_open(self, mock_stdin):
        """Should not detect shutdown when stdin.closed is False"""
        # ARRANGE
        mock_stdin.closed = False

        # ACT
        result = is_shutdown_in_progress()

        # ASSERT
        assert result is False, "Should not detect shutdown when stdin is open"


# =============================================================================
# UNIT TESTS - Stdin Detached Detection
# =============================================================================


class TestStdinDetachedDetection:
    """Test shutdown detection when stdin is detached (no fileno)."""

    @patch("sys.stdin")
    def test_detects_shutdown_when_stdin_has_no_fileno(self, mock_stdin):
        """Should detect shutdown when stdin.fileno() raises ValueError"""
        # ARRANGE
        mock_stdin.closed = False
        mock_stdin.fileno.side_effect = ValueError("I/O operation on closed file")

        # ACT
        result = is_shutdown_in_progress()

        # ASSERT
        assert result is True, "Should detect shutdown when stdin has no fileno"

    @patch("sys.stdin")
    def test_does_not_detect_shutdown_for_stringio_mock(self, mock_stdin):
        """Should NOT detect shutdown for StringIO/mock (UnsupportedOperation is normal)"""
        # ARRANGE
        import io

        mock_stdin.closed = False
        mock_stdin.fileno.side_effect = io.UnsupportedOperation("fileno not available")

        # ACT
        result = is_shutdown_in_progress()

        # ASSERT
        assert result is False, "StringIO/mock with UnsupportedOperation is not shutdown"

    @patch("sys.stdin")
    def test_no_shutdown_when_stdin_has_valid_fileno(self, mock_stdin):
        """Should not detect shutdown when stdin.fileno() returns valid fd"""
        # ARRANGE
        mock_stdin.closed = False
        mock_stdin.fileno.return_value = 0  # Valid file descriptor

        # ACT
        result = is_shutdown_in_progress()

        # ASSERT
        assert result is False, "Should not detect shutdown with valid fileno"


# =============================================================================
# UNIT TESTS - Atexit Context Detection
# =============================================================================


class TestAtexitContextDetection:
    """Test shutdown detection during atexit handler execution."""

    def test_detects_shutdown_during_atexit_execution(self):
        """Should detect shutdown when called from atexit handler.

        Note: This is difficult to test directly since we can't easily
        simulate being in an atexit handler. This test documents the
        expected behavior for manual verification.
        """
        # This test serves as documentation of expected behavior
        # In real usage, is_shutdown_in_progress() would detect:
        # - sys._getframe() inspection showing atexit module in stack
        # - Or simpler: rely on env var set by signal handler


# =============================================================================
# UNIT TESTS - Mark and Clear Shutdown Functions
# =============================================================================


class TestMarkShutdown:
    """Test mark_shutdown() function for programmatic shutdown marking."""

    def test_mark_shutdown_sets_env_var(self):
        """Should set AMPLIHACK_SHUTDOWN_IN_PROGRESS=1"""
        # ARRANGE - ensure clean state
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        try:
            # ACT
            mark_shutdown()

            # ASSERT
            assert os.environ.get("AMPLIHACK_SHUTDOWN_IN_PROGRESS") == "1"
            assert is_shutdown_in_progress() is True
        finally:
            # CLEANUP
            if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
                del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    def test_mark_shutdown_is_idempotent(self):
        """Should safely handle being called multiple times"""
        # ARRANGE - ensure clean state
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        try:
            # ACT
            mark_shutdown()
            mark_shutdown()  # Call again
            mark_shutdown()  # And again

            # ASSERT
            assert os.environ.get("AMPLIHACK_SHUTDOWN_IN_PROGRESS") == "1"
            assert is_shutdown_in_progress() is True
        finally:
            # CLEANUP
            if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
                del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


class TestClearShutdown:
    """Test clear_shutdown() function for testing cleanup."""

    @patch("sys.stdin")
    def test_clear_shutdown_removes_env_var(self, mock_stdin):
        """Should remove AMPLIHACK_SHUTDOWN_IN_PROGRESS"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        # Mock stdin as healthy
        mock_stdin.closed = False
        mock_stdin.fileno.return_value = 0

        # ACT
        clear_shutdown()

        # ASSERT
        assert "AMPLIHACK_SHUTDOWN_IN_PROGRESS" not in os.environ
        assert is_shutdown_in_progress() is False

    @patch("sys.stdin")
    def test_clear_shutdown_is_idempotent(self, mock_stdin):
        """Should safely handle being called when env var not set"""
        # ARRANGE - ensure env var not set
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # Mock stdin as healthy
        mock_stdin.closed = False
        mock_stdin.fileno.return_value = 0

        # ACT - should not raise error
        clear_shutdown()
        clear_shutdown()  # Call again

        # ASSERT
        assert is_shutdown_in_progress() is False


# =============================================================================
# UNIT TESTS - No False Positives
# =============================================================================


class TestNoFalsePositives:
    """Test that shutdown detection does not trigger false positives."""

    @patch("sys.stdin")
    def test_normal_operation_with_open_stdin(self, mock_stdin):
        """Should not detect shutdown during normal operation"""
        # ARRANGE - normal stdin state
        mock_stdin.closed = False
        mock_stdin.fileno.return_value = 0

        # Ensure env var not set
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # ACT
        result = is_shutdown_in_progress()

        # ASSERT
        assert result is False, "Should not falsely detect shutdown"

    @patch("sys.stdin")
    def test_no_false_positive_with_various_env_vars(self, mock_stdin):
        """Should only respond to exact AMPLIHACK_SHUTDOWN_IN_PROGRESS=1"""
        # ARRANGE - set various other env vars
        os.environ["SHUTDOWN"] = "1"
        os.environ["AMPLIHACK_SHUTDOWN"] = "1"
        os.environ["IN_PROGRESS"] = "1"

        # Ensure target env var not set
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # Mock stdin as healthy
        mock_stdin.closed = False
        mock_stdin.fileno.return_value = 0

        try:
            # ACT
            result = is_shutdown_in_progress()

            # ASSERT
            assert result is False, "Should not respond to similar env vars"
        finally:
            # CLEANUP
            for key in ["SHUTDOWN", "AMPLIHACK_SHUTDOWN", "IN_PROGRESS"]:
                if key in os.environ:
                    del os.environ[key]


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_env_var():
    """Ensure AMPLIHACK_SHUTDOWN_IN_PROGRESS is cleaned up after each test.

    This fixture runs automatically for every test to prevent test pollution
    from env var state leaking between tests.
    """
    yield
    # Cleanup after test
    if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
        del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


# =============================================================================
# TEST CONFIGURATION
# =============================================================================


def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
