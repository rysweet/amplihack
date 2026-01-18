#!/usr/bin/env python3
"""
Tests for HookProcessor - TDD approach for BrokenPipeError handling.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)

This test file focuses on the write_output() method's BrokenPipeError handling.
Tests are written BEFORE implementation (TDD) - they will FAIL until the fix is applied.
"""

import errno
import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

# Add hooks directory to path for imports
hooks_dir = Path(__file__).parent.parent
sys.path.insert(0, str(hooks_dir))

from hook_processor import HookProcessor


# Concrete test implementation of abstract HookProcessor
class TestHook(HookProcessor):
    """Concrete implementation for testing purposes"""

    def __init__(self):
        # Skip parent init for simple tests
        self.hook_name = "test_hook"

    def process(self, input_data):
        """Simple pass-through processor"""
        return input_data


class TestWriteOutputNormalOperation:
    """Unit tests (60%) - Normal operation without errors"""

    def test_write_output_writes_json_to_stdout(self):
        """Test write_output() writes valid JSON to stdout with open pipe"""
        hook = TestHook()
        test_data = {"status": "success", "message": "test"}

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            hook.write_output(test_data)

            # Verify output
            output = mock_stdout.getvalue()
            assert output == '{"status": "success", "message": "test"}\n'

    def test_write_output_includes_newline(self):
        """Test write_output() includes newline after JSON"""
        hook = TestHook()
        test_data = {"key": "value"}

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            hook.write_output(test_data)

            # Verify newline present
            output = mock_stdout.getvalue()
            assert output.endswith("\n")

    def test_write_output_flushes_stdout(self):
        """Test write_output() calls flush to ensure data is written"""
        hook = TestHook()
        test_data = {"key": "value"}

        mock_stdout = Mock()
        with patch("sys.stdout", mock_stdout):
            hook.write_output(test_data)

            # Verify flush was called
            mock_stdout.flush.assert_called_once()

    def test_write_output_handles_empty_dict(self):
        """Test write_output() handles empty dictionary (fail-open behavior)"""
        hook = TestHook()
        test_data = {}

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            hook.write_output(test_data)

            # Verify empty dict written
            output = mock_stdout.getvalue()
            assert output == "{}\n"

    def test_write_output_handles_complex_nested_data(self):
        """Test write_output() handles complex nested JSON structures"""
        hook = TestHook()
        test_data = {
            "permissionDecision": "allow",
            "metadata": {"tools": ["read", "write"], "count": 42},
            "nested": {"deeper": {"value": True}},
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            hook.write_output(test_data)

            # Verify complete structure written
            output = mock_stdout.getvalue()
            parsed = json.loads(output.strip())
            assert parsed == test_data


class TestWriteOutputBrokenPipeError:
    """Unit tests (60%) - BrokenPipeError handling (TDD - WILL FAIL until fix)"""

    def test_broken_pipe_error_is_silently_absorbed(self):
        """Test BrokenPipeError during flush is silently absorbed (fail-open)

        This test verifies the core fix: when Claude Code closes the pipe,
        we should NOT raise an exception but silently succeed.

        TDD: This WILL FAIL until we add try/except for BrokenPipeError.
        """
        hook = TestHook()
        test_data = {"status": "success"}

        mock_stdout = Mock()
        # Simulate pipe closure during flush
        mock_stdout.flush.side_effect = BrokenPipeError("Broken pipe")

        with patch("sys.stdout", mock_stdout):
            # Should NOT raise - fail-open behavior
            hook.write_output(test_data)  # Should succeed silently

            # Verify write and newline still called before error
            mock_stdout.write.assert_has_calls([call("\n")])

    def test_broken_pipe_error_during_json_dump(self):
        """Test BrokenPipeError during json.dump is absorbed

        If pipe closes during the initial JSON write, we should
        handle it gracefully.

        TDD: This WILL FAIL until we add try/except for BrokenPipeError.
        """
        hook = TestHook()
        test_data = {"status": "success"}

        with patch("sys.stdout"):
            with patch("json.dump") as mock_dump:
                mock_dump.side_effect = BrokenPipeError("Broken pipe")

                # Should NOT raise - fail-open behavior
                hook.write_output(test_data)  # Should succeed silently

    def test_broken_pipe_error_logs_no_error(self):
        """Test BrokenPipeError is silent - no error logging

        Philosophy: Fail-open gracefully. The pipe closure is expected
        during shutdown, so we don't log it as an error.

        TDD: This WILL FAIL until we implement silent absorption.
        """
        hook = TestHook()
        test_data = {"status": "success"}

        mock_stdout = Mock()
        mock_stdout.flush.side_effect = BrokenPipeError("Broken pipe")

        with patch("sys.stdout", mock_stdout):
            # Should succeed without any exceptions
            try:
                hook.write_output(test_data)
            except BrokenPipeError:
                pytest.fail("BrokenPipeError should be absorbed, not raised")


class TestWriteOutputIOError:
    """Unit tests (60%) - IOError handling (generic I/O errors)"""

    def test_ioerror_is_silently_absorbed(self):
        """Test generic IOError is absorbed (fail-open)

        IOError is the base class for many I/O errors including
        BrokenPipeError. We should handle it gracefully.

        TDD: This WILL FAIL until we add try/except for IOError.
        """
        hook = TestHook()
        test_data = {"status": "success"}

        mock_stdout = Mock()
        mock_stdout.flush.side_effect = OSError("I/O error")

        with patch("sys.stdout", mock_stdout):
            # Should NOT raise
            hook.write_output(test_data)

    def test_ioerror_during_write_is_absorbed(self):
        """Test IOError during write operation is absorbed

        TDD: This WILL FAIL until we add try/except for IOError.
        """
        hook = TestHook()
        test_data = {"key": "value"}

        with patch("sys.stdout"):
            with patch("json.dump") as mock_dump:
                mock_dump.side_effect = OSError("Write failed")

                # Should NOT raise
                hook.write_output(test_data)


class TestWriteOutputOSError:
    """Unit tests (60%) - OSError handling (EPIPE errno 32)"""

    def test_oserror_epipe_is_silently_absorbed(self):
        """Test OSError with errno EPIPE is absorbed

        EPIPE is the underlying error code for broken pipe.
        We should handle it gracefully.

        TDD: This WILL FAIL until we add try/except for OSError.
        """
        hook = TestHook()
        test_data = {"status": "success"}

        mock_stdout = Mock()
        # Simulate EPIPE
        epipe_error = OSError(errno.EPIPE, "Broken pipe")
        mock_stdout.flush.side_effect = epipe_error

        with patch("sys.stdout", mock_stdout):
            # Should NOT raise
            hook.write_output(test_data)

    def test_oserror_non_epipe_is_propagated(self):
        """Test OSError with non-EPIPE errno is raised

        We should ONLY catch EPIPE (errno 32). Other OS errors
        should propagate so we know about real problems.

        TDD: This test should PASS even before fix (validates we
        don't catch too broadly).
        """
        hook = TestHook()
        test_data = {"status": "success"}

        mock_stdout = Mock()
        # Simulate different OS error (not EPIPE)
        other_error = OSError(5, "Input/output error")
        mock_stdout.flush.side_effect = other_error

        with patch("sys.stdout", mock_stdout):
            # SHOULD raise - not a pipe closure error
            with pytest.raises(OSError) as exc_info:
                hook.write_output(test_data)

            assert exc_info.value.errno == 5


class TestWriteOutputErrorPropagation:
    """Unit tests (60%) - Verify other exceptions still propagate"""

    def test_value_error_propagates(self):
        """Test ValueError is NOT caught - only pipe-related errors

        We should NOT catch generic exceptions. Only BrokenPipeError,
        IOError, and EPIPE should be absorbed.

        This test should PASS (validates we're not catching too broadly).
        """
        hook = TestHook()
        test_data = {"status": "success"}

        mock_stdout = Mock()
        mock_stdout.flush.side_effect = ValueError("Invalid value")

        with patch("sys.stdout", mock_stdout):
            # SHOULD raise - not a pipe error
            with pytest.raises(ValueError):
                hook.write_output(test_data)

    def test_type_error_propagates(self):
        """Test TypeError is NOT caught

        This test should PASS (validates we're not catching too broadly).
        """
        hook = TestHook()
        test_data = {"status": "success"}

        with patch("json.dump") as mock_dump:
            mock_dump.side_effect = TypeError("Not JSON serializable")

            # SHOULD raise - not a pipe error
            with pytest.raises(TypeError):
                hook.write_output(test_data)

    def test_keyboard_interrupt_propagates(self):
        """Test KeyboardInterrupt is NOT caught (critical for user control)

        User interrupts (Ctrl+C) should ALWAYS propagate.

        This test should PASS (validates we're not catching too broadly).
        """
        hook = TestHook()
        test_data = {"status": "success"}

        mock_stdout = Mock()
        mock_stdout.flush.side_effect = KeyboardInterrupt()

        with patch("sys.stdout", mock_stdout):
            # SHOULD raise - user interrupt must propagate
            with pytest.raises(KeyboardInterrupt):
                hook.write_output(test_data)

    def test_system_exit_propagates(self):
        """Test SystemExit is NOT caught (critical for process control)

        This test should PASS (validates we're not catching too broadly).
        """
        hook = TestHook()
        test_data = {"status": "success"}

        mock_stdout = Mock()
        mock_stdout.flush.side_effect = SystemExit(1)

        with patch("sys.stdout", mock_stdout):
            # SHOULD raise - system exit must propagate
            with pytest.raises(SystemExit):
                hook.write_output(test_data)


class TestWriteOutputIntegration:
    """Integration tests (30%) - Multiple components working together"""

    def test_write_output_with_real_json_serialization(self):
        """Integration test: Real JSON serialization + pipe closure handling

        This verifies that our error handling doesn't break normal JSON
        serialization when the pipe closes.

        TDD: This WILL FAIL until we implement the fix.
        """
        hook = TestHook()
        test_data = {
            "permissionDecision": "allow",
            "tools": ["read_file", "write_file"],
            "metadata": {"timestamp": "2024-12-14T12:00:00Z"},
        }

        mock_stdout = Mock()
        # Let json.dump write to mock, then close pipe during flush
        mock_stdout.flush.side_effect = BrokenPipeError("Broken pipe")

        with patch("sys.stdout", mock_stdout):
            # Should handle gracefully
            hook.write_output(test_data)

            # Verify json.dump was called with correct data
            # (even though flush failed)
            calls = mock_stdout.write.call_args_list
            assert len(calls) > 0  # At least the newline was written

    def test_write_output_sequence_with_pipe_closure(self):
        """Integration test: Multiple writes, pipe closes on last one

        Simulates real scenario where hook writes several outputs,
        and pipe closes during the final write.

        TDD: This WILL FAIL until we implement the fix.
        """
        hook = TestHook()

        outputs = [
            {"step": 1, "status": "processing"},
            {"step": 2, "status": "processing"},
            {"step": 3, "status": "complete"},  # Pipe closes here
        ]

        call_count = 0

        def flush_with_final_failure():
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise BrokenPipeError("Broken pipe")

        mock_stdout = Mock()
        mock_stdout.flush.side_effect = flush_with_final_failure

        with patch("sys.stdout", mock_stdout):
            # First two should succeed, third should fail-open
            for output in outputs:
                hook.write_output(output)

            # All three writes should complete without exception
            assert call_count == 3


class TestWriteOutputEndToEnd:
    """E2E tests (10%) - Complete workflows"""

    @patch("sys.stdout")
    def test_complete_hook_lifecycle_with_pipe_closure(self, mock_stdout):
        """E2E test: Full hook lifecycle ending in pipe closure

        Simulates complete hook execution:
        1. Read input
        2. Process data
        3. Write output
        4. Pipe closes during write

        TDD: This WILL FAIL until we implement the fix.
        """
        hook = TestHook()

        # Simulate pipe closure during output flush
        mock_stdout.flush.side_effect = BrokenPipeError("Broken pipe")

        # Complete workflow should handle gracefully
        input_data = {"tool": "read_file", "path": "/test/file.txt"}
        output_data = hook.process(input_data)
        hook.write_output(output_data)  # Should not raise

        # Verify flush was attempted
        mock_stdout.flush.assert_called()

    def test_hook_graceful_shutdown_scenario(self):
        """E2E test: Simulates Claude Code shutdown scenario

        This is the real-world scenario from issue #1874:
        1. Hook processes input successfully
        2. Hook writes output successfully
        3. Claude Code reads output and closes pipe
        4. Hook attempts flush, gets BrokenPipeError
        5. Hook should exit cleanly (no hang, no error)

        TDD: This WILL FAIL until we implement the fix.
        """
        hook = TestHook()

        # Simulate Claude Code behavior
        class MockClaudeCodeStdout:
            """Simulates Claude Code's pipe closure behavior"""

            def __init__(self):
                self.data_written = []
                self.closed = False

            def write(self, data):
                if not self.closed:
                    self.data_written.append(data)

            def flush(self):
                # Claude Code closes pipe after reading
                self.closed = True
                raise BrokenPipeError("Broken pipe")

        mock_stdout = MockClaudeCodeStdout()

        with patch("sys.stdout", mock_stdout):
            with patch("json.dump") as mock_dump:
                # Let json.dump write to our mock
                def write_json(obj, f):
                    f.write(json.dumps(obj))

                mock_dump.side_effect = write_json

                # This should complete without hanging or raising
                test_data = {"permissionDecision": "allow"}
                hook.write_output(test_data)

        # Verify data was written before pipe closed
        assert len(mock_stdout.data_written) > 0


# Test discovery helpers
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
