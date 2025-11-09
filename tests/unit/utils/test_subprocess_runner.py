"""Tests for standardized subprocess runner module."""

import os
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.amplihack.utils.subprocess_runner import (
    SubprocessError,
    SubprocessResult,
    SubprocessRunner,
    check_command_exists,
    run_command,
)


class TestSubprocessResult:
    """Tests for SubprocessResult dataclass."""

    def test_result_success_bool(self):
        """Test boolean evaluation of successful result."""
        result = SubprocessResult(
            returncode=0,
            stdout="output",
            stderr="",
            command=["echo", "test"],
            success=True,
        )
        assert bool(result) is True
        assert result.success is True

    def test_result_failure_bool(self):
        """Test boolean evaluation of failed result."""
        result = SubprocessResult(
            returncode=1,
            stdout="",
            stderr="error",
            command=["false"],
            success=False,
        )
        assert bool(result) is False
        assert result.success is False


class TestSubprocessRunner:
    """Tests for SubprocessRunner class."""

    def test_initialization(self):
        """Test SubprocessRunner initialization."""
        runner = SubprocessRunner(
            default_timeout=60,
            log_commands=True,
            capture_output=False,
        )
        assert runner.default_timeout == 60
        assert runner.log_commands is True
        assert runner.capture_output is False

    def test_is_windows(self):
        """Test Windows platform detection."""
        runner = SubprocessRunner()
        # Just verify the method exists and returns a boolean
        result = runner.is_windows()
        assert isinstance(result, bool)

    def test_run_safe_success(self):
        """Test successful command execution."""
        runner = SubprocessRunner(log_commands=False)
        result = runner.run_safe(["echo", "hello"], timeout=5)

        assert result.success is True
        assert result.returncode == 0
        assert "hello" in result.stdout
        assert result.stderr == ""
        assert result.duration is not None
        assert result.duration > 0

    def test_run_safe_failure(self):
        """Test failed command execution."""
        runner = SubprocessRunner(log_commands=False)
        # Use a command that will fail on all platforms
        result = runner.run_safe(
            ["python", "-c", "import sys; sys.exit(42)"],
            timeout=5,
        )

        assert result.success is False
        assert result.returncode == 42
        assert result.duration is not None

    def test_run_safe_with_check_raises(self):
        """Test that check=True raises SubprocessError on failure."""
        runner = SubprocessRunner(log_commands=False)

        with pytest.raises(SubprocessError) as exc_info:
            runner.run_safe(
                ["python", "-c", "import sys; sys.exit(1)"],
                timeout=5,
                check=True,
            )

        assert exc_info.value.result.returncode == 1
        assert "failed with exit code 1" in exc_info.value.message

    def test_run_safe_command_not_found(self):
        """Test handling of non-existent command."""
        runner = SubprocessRunner(log_commands=False)
        result = runner.run_safe(
            ["this_command_definitely_does_not_exist_12345"],
            timeout=5,
        )

        assert result.success is False
        assert result.returncode == 127
        assert result.error_type == "not_found"
        assert "Command not found" in result.stderr

    def test_run_safe_timeout(self):
        """Test timeout handling."""
        runner = SubprocessRunner(log_commands=False)
        # Command that sleeps longer than timeout
        result = runner.run_safe(
            ["python", "-c", "import time; time.sleep(10)"],
            timeout=1,
        )

        assert result.success is False
        assert result.returncode == 124
        assert result.error_type == "timeout"
        assert "timed out" in result.stderr.lower()

    def test_run_safe_with_cwd(self, tmp_path):
        """Test command execution with custom working directory."""
        runner = SubprocessRunner(log_commands=False)
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # Create a test file
        test_file = test_dir / "test.txt"
        test_file.write_text("test content")

        # List files in the directory
        result = runner.run_safe(
            ["ls"] if not runner.is_windows() else ["dir", "/b"],
            cwd=test_dir,
            timeout=5,
        )

        assert result.success is True
        assert "test.txt" in result.stdout

    def test_run_safe_with_env(self):
        """Test command execution with custom environment."""
        runner = SubprocessRunner(log_commands=False)
        result = runner.run_safe(
            ["python", "-c", "import os; print(os.environ.get('TEST_VAR', ''))"],
            env={"TEST_VAR": "test_value"},
            timeout=5,
        )

        assert result.success is True
        assert "test_value" in result.stdout

    def test_run_safe_with_context(self):
        """Test that context is included in error messages."""
        runner = SubprocessRunner(log_commands=False)

        with pytest.raises(SubprocessError) as exc_info:
            runner.run_safe(
                ["python", "-c", "import sys; sys.exit(1)"],
                timeout=5,
                check=True,
                context="testing context message",
            )

        assert "testing context message" in exc_info.value.message

    def test_run_safe_no_capture(self):
        """Test command execution without output capture."""
        runner = SubprocessRunner(log_commands=False)
        result = runner.run_safe(
            ["echo", "hello"],
            capture=False,
            timeout=5,
        )

        assert result.success is True
        assert result.stdout == ""
        assert result.stderr == ""

    def test_check_command_exists_true(self):
        """Test check_command_exists for existing command."""
        runner = SubprocessRunner(log_commands=False)
        # Python should exist in test environment
        assert runner.check_command_exists("python") is True

    def test_check_command_exists_false(self):
        """Test check_command_exists for non-existent command."""
        runner = SubprocessRunner(log_commands=False)
        assert runner.check_command_exists("this_definitely_does_not_exist_12345") is False

    def test_create_process_group_popen(self):
        """Test process group creation."""
        runner = SubprocessRunner(log_commands=False)
        process = runner.create_process_group_popen(
            ["python", "-c", "import time; time.sleep(0.1)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert process is not None
        assert isinstance(process, subprocess.Popen)

        # Clean up
        process.wait(timeout=2)

    def test_terminate_process_group(self):
        """Test process group termination."""
        runner = SubprocessRunner(log_commands=False)
        process = runner.create_process_group_popen(
            ["python", "-c", "import time; time.sleep(10)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Terminate after a brief moment
        time.sleep(0.1)
        runner.terminate_process_group(process, timeout=2)

        # Verify process is terminated
        assert process.poll() is not None

    def test_terminate_process_group_already_terminated(self):
        """Test terminating already terminated process."""
        runner = SubprocessRunner(log_commands=False)
        process = runner.create_process_group_popen(
            ["python", "-c", "print('done')"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for process to complete
        process.wait(timeout=2)

        # Terminating should be safe
        runner.terminate_process_group(process, timeout=1)
        assert process.poll() is not None


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_run_command_success(self):
        """Test run_command convenience function with success."""
        result = run_command(["echo", "test"], timeout=5)

        assert result.success is True
        assert "test" in result.stdout

    def test_run_command_failure(self):
        """Test run_command convenience function with failure."""
        result = run_command(
            ["python", "-c", "import sys; sys.exit(1)"],
            timeout=5,
        )

        assert result.success is False
        assert result.returncode == 1

    def test_run_command_with_check(self):
        """Test run_command with check=True raises on failure."""
        with pytest.raises(SubprocessError):
            run_command(
                ["python", "-c", "import sys; sys.exit(1)"],
                timeout=5,
                check=True,
            )

    def test_check_command_exists_function(self):
        """Test check_command_exists convenience function."""
        # Python should exist
        assert check_command_exists("python") is True

        # Non-existent command should not exist
        assert check_command_exists("this_does_not_exist_12345") is False


class TestErrorHandling:
    """Tests for various error conditions."""

    def test_permission_error_handling(self):
        """Test handling of permission errors."""
        runner = SubprocessRunner(log_commands=False)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = PermissionError("Permission denied")

            result = runner.run_safe(["test"], timeout=5)

            assert result.success is False
            assert result.returncode == 126
            assert result.error_type == "permission"
            assert "Permission denied" in result.stderr

    def test_os_error_handling(self):
        """Test handling of OS errors."""
        runner = SubprocessRunner(log_commands=False)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Some OS error")

            result = runner.run_safe(["test"], timeout=5)

            assert result.success is False
            assert result.error_type == "os_error"
            assert "OS error" in result.stderr

    def test_unexpected_error_handling(self):
        """Test handling of unexpected errors."""
        runner = SubprocessRunner(log_commands=False)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Unexpected error")

            result = runner.run_safe(["test"], timeout=5)

            assert result.success is False
            assert result.error_type == "unexpected"
            assert "Unexpected error" in result.stderr


class TestLogging:
    """Tests for logging functionality."""

    def test_logging_enabled(self, caplog):
        """Test that commands are logged when log_commands=True."""
        runner = SubprocessRunner(log_commands=True)

        with caplog.at_level("DEBUG"):
            runner.run_safe(["echo", "test"], timeout=5)

        # Check that command was logged
        assert any("Running command" in record.message for record in caplog.records)

    def test_logging_disabled(self, caplog):
        """Test that commands are not logged when log_commands=False."""
        runner = SubprocessRunner(log_commands=False)

        with caplog.at_level("DEBUG"):
            runner.run_safe(["echo", "test"], timeout=5)

        # Should not log the command
        assert not any("Running command" in record.message for record in caplog.records)


class TestCrossPlatformCompatibility:
    """Tests for cross-platform compatibility features."""

    def test_windows_detection(self):
        """Test Windows platform detection."""
        # Test the static method directly
        is_win = SubprocessRunner.is_windows()
        assert isinstance(is_win, bool)

    def test_path_conversion(self, tmp_path):
        """Test Path to string conversion in cwd parameter."""
        runner = SubprocessRunner(log_commands=False)

        # Should accept both str and Path
        result1 = runner.run_safe(
            ["python", "-c", "import os; print(os.getcwd())"],
            cwd=str(tmp_path),
            timeout=5,
        )
        result2 = runner.run_safe(
            ["python", "-c", "import os; print(os.getcwd())"],
            cwd=tmp_path,
            timeout=5,
        )

        assert result1.success is True
        assert result2.success is True
        # Both should work the same way
        assert result1.stdout.strip() == result2.stdout.strip()
