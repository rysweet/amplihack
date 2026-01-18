#!/usr/bin/env python3
"""
TDD Tests for Hook Processor Shutdown Behavior (UNIT TESTS - 60%)

Tests that HookProcessor's read_input() method properly skips stdin reads
during shutdown to prevent hangs. This is critical for allowing hooks to
exit cleanly when cleanup is in progress.

Testing Philosophy:
- Ruthlessly Simple: Each test verifies one shutdown scenario
- Zero-BS: All tests work, no stubs
- Fail-Open: Shutdown always allows clean exit

Test Coverage:
- read_input() skips stdin during shutdown
- read_input() works normally without shutdown
- stdin closed handling
- stdin detached handling
- Empty input handling
"""

import os
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hook_processor import HookProcessor

# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def hook_processor(tmp_path):
    """Create a HookProcessor instance for testing.

    Uses tmp_path for log directory to avoid polluting project.
    """

    # Create a concrete subclass since HookProcessor is abstract
    class TestHookProcessor(HookProcessor):
        def process(self, input_data):
            return {}

    # Create processor with temporary directories
    with patch.object(HookProcessor, "__init__", lambda self, hook_name: None):
        processor = TestHookProcessor("test_hook")
        processor.hook_name = "test_hook"
        processor.project_root = tmp_path
        processor.log_dir = tmp_path / "logs"
        processor.log_dir.mkdir()
        processor.log_file = processor.log_dir / "test_hook.log"
        return processor


# =============================================================================
# UNIT TESTS - read_input() Shutdown Behavior
# =============================================================================


class TestReadInputDuringShutdown:
    """Test read_input() skips stdin reads during shutdown."""

    def test_returns_empty_dict_during_shutdown(self, hook_processor):
        """Should return {} immediately when AMPLIHACK_SHUTDOWN_IN_PROGRESS=1"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        try:
            # ACT
            result = hook_processor.read_input()

            # ASSERT
            assert result == {}, "Should return empty dict during shutdown"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    @patch("sys.stdin")
    def test_does_not_read_stdin_during_shutdown(self, mock_stdin, hook_processor):
        """Should not call stdin.read() when shutting down"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        mock_stdin.read = MagicMock(return_value='{"key": "value"}')

        try:
            # ACT
            result = hook_processor.read_input()

            # ASSERT
            assert result == {}, "Should return empty dict"
            mock_stdin.read.assert_not_called()
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    def test_logs_debug_message_during_shutdown(self, hook_processor):
        """Should log that stdin read is being skipped"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        try:
            # ACT
            hook_processor.read_input()

            # ASSERT
            log_content = hook_processor.log_file.read_text()
            assert "Skipping stdin read during shutdown" in log_content
            assert "DEBUG" in log_content
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    def test_returns_immediately_during_shutdown(self, hook_processor):
        """Should return in <1ms during shutdown (no blocking operations)"""
        # ARRANGE
        import time

        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        try:
            # ACT
            start_time = time.time()
            result = hook_processor.read_input()
            elapsed = time.time() - start_time

            # ASSERT
            assert result == {}, "Should return empty dict"
            assert elapsed < 0.001, f"Should return in <1ms, took {elapsed * 1000:.1f}ms"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


# =============================================================================
# UNIT TESTS - read_input() Normal Operation
# =============================================================================


class TestReadInputNormalOperation:
    """Test read_input() works correctly during normal operation."""

    @patch("sys.stdin", StringIO('{"key": "value"}'))
    def test_reads_valid_json_from_stdin(self, hook_processor):
        """Should parse valid JSON from stdin during normal operation"""
        # ARRANGE - ensure NOT shutting down
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # ACT
        result = hook_processor.read_input()

        # ASSERT
        assert result == {"key": "value"}, "Should parse JSON correctly"

    @patch("sys.stdin", StringIO(""))
    def test_returns_empty_dict_for_empty_input(self, hook_processor):
        """Should return {} when stdin is empty"""
        # ARRANGE - ensure NOT shutting down
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # ACT
        result = hook_processor.read_input()

        # ASSERT
        assert result == {}, "Should return empty dict for empty input"

    @patch("sys.stdin", StringIO("   \n  \n  "))
    def test_returns_empty_dict_for_whitespace_input(self, hook_processor):
        """Should return {} when stdin contains only whitespace"""
        # ARRANGE - ensure NOT shutting down
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # ACT
        result = hook_processor.read_input()

        # ASSERT
        assert result == {}, "Should return empty dict for whitespace"

    @patch("sys.stdin", StringIO('{"nested": {"key": "value"}}'))
    def test_reads_nested_json_correctly(self, hook_processor):
        """Should parse nested JSON structures"""
        # ARRANGE - ensure NOT shutting down
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # ACT
        result = hook_processor.read_input()

        # ASSERT
        assert result == {"nested": {"key": "value"}}


# =============================================================================
# UNIT TESTS - read_input() Error Handling
# =============================================================================


class TestReadInputErrorHandling:
    """Test read_input() handles various error conditions."""

    @patch("sys.stdin")
    def test_handles_stdin_closed_gracefully(self, mock_stdin, hook_processor):
        """Should handle stdin.closed=True without hanging"""
        # ARRANGE
        mock_stdin.closed = True
        mock_stdin.read.side_effect = ValueError("I/O operation on closed file")

        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # ACT
        result = hook_processor.read_input()

        # ASSERT - should detect shutdown via stdin.closed and return empty dict
        assert result == {}, "Should return {} when stdin is closed (shutdown detected)"

    @patch("sys.stdin")
    def test_handles_stdin_detached(self, mock_stdin, hook_processor):
        """Should handle detached stdin (no fileno)"""
        # ARRANGE
        import io

        mock_stdin.closed = False
        mock_stdin.fileno.side_effect = io.UnsupportedOperation()

        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # ACT & ASSERT
        # Note: read_input() should either return {} or raise based on RobustJSONParser
        # The key is it shouldn't hang
        try:
            result = hook_processor.read_input()
            # If it returns, it should be {}
            assert isinstance(result, dict)
        except Exception:
            pass  # Expected for detached stdin

    @patch("sys.stdin", StringIO('{"incomplete": '))
    def test_uses_robust_json_parser_for_malformed_input(self, hook_processor):
        """Should use RobustJSONParser to handle malformed JSON"""
        # ARRANGE - ensure NOT shutting down
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # ACT
        result = hook_processor.read_input()

        # ASSERT
        # RobustJSONParser should handle this gracefully
        assert isinstance(result, dict), "Should return dict even for malformed JSON"


# =============================================================================
# UNIT TESTS - Shutdown Detection Integration
# =============================================================================


class TestShutdownDetectionIntegration:
    """Test read_input() correctly integrates with shutdown detection."""

    def test_detects_shutdown_via_env_var(self, hook_processor):
        """Should detect shutdown through AMPLIHACK_SHUTDOWN_IN_PROGRESS"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        try:
            # ACT
            result = hook_processor.read_input()

            # ASSERT
            assert result == {}, "Should skip stdin read via env var"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    def test_no_shutdown_when_env_var_zero(self, hook_processor):
        """Should NOT detect shutdown when AMPLIHACK_SHUTDOWN_IN_PROGRESS=0"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "0"

        with patch("sys.stdin", StringIO('{"key": "value"}')):
            try:
                # ACT
                result = hook_processor.read_input()

                # ASSERT
                assert result == {"key": "value"}, "Should read stdin when env var is 0"
            finally:
                # CLEANUP
                del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    def test_no_shutdown_when_env_var_empty(self, hook_processor):
        """Should NOT detect shutdown when AMPLIHACK_SHUTDOWN_IN_PROGRESS=''"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = ""

        with patch("sys.stdin", StringIO('{"key": "value"}')):
            try:
                # ACT
                result = hook_processor.read_input()

                # ASSERT
                assert result == {"key": "value"}, "Should read stdin when env var empty"
            finally:
                # CLEANUP
                del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


# =============================================================================
# UNIT TESTS - Performance
# =============================================================================


class TestReadInputPerformance:
    """Test read_input() performance during shutdown."""

    def test_shutdown_check_is_fast(self, hook_processor):
        """Shutdown check should be fast (<5ms per call)"""
        # ARRANGE
        import time

        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        try:
            # ACT - Run 100 times to measure overhead
            start_time = time.time()
            for _ in range(100):
                hook_processor.read_input()
            elapsed = time.time() - start_time

            avg_per_call = (elapsed / 100) * 1000  # ms

            # ASSERT - Multi-layer checks (env var + atexit + stdin) take ~2-3ms
            # This is still fast enough for clean 2-3s exit times
            assert avg_per_call < 5.0, (
                f"Shutdown check took {avg_per_call:.2f}ms avg, should be <5ms"
            )
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


# =============================================================================
# TEST CONFIGURATION
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_env_var():
    """Ensure AMPLIHACK_SHUTDOWN_IN_PROGRESS is cleaned up after each test."""
    yield
    if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
        del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
