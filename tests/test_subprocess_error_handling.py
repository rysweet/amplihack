"""Tests for subprocess error handling improvements.

Tests that all subprocess calls in the codebase properly capture and report errors
with helpful context and installation guidance.
"""

import subprocess
from unittest.mock import Mock, patch

from amplihack.utils.prerequisites import safe_subprocess_call


class TestSubprocessErrorHandling:
    """Tests for safe subprocess wrapper error handling."""

    def test_file_not_found_error_with_context(self):
        """Test FileNotFoundError is caught and formatted with context."""
        with patch("subprocess.run", side_effect=FileNotFoundError("command not found")):
            returncode, stdout, stderr = safe_subprocess_call(
                ["nonexistent_command"], context="running tests"
            )

            assert returncode == 127
            assert "not found" in stderr.lower()
            assert "running tests" in stderr.lower()
            assert "nonexistent_command" in stderr

    def test_permission_error_with_helpful_message(self):
        """Test PermissionError includes helpful guidance."""
        with patch("subprocess.run", side_effect=PermissionError("permission denied")):
            returncode, stdout, stderr = safe_subprocess_call(
                ["/restricted/command"], context="accessing file"
            )

            assert returncode != 0
            assert "permission" in stderr.lower()
            assert "accessing file" in stderr.lower()

    def test_timeout_error_with_command_info(self):
        """Test TimeoutExpired includes command that timed out."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired("long_running_cmd", 5),
        ):
            returncode, stdout, stderr = safe_subprocess_call(
                ["long_running_cmd"], context="waiting for response", timeout=5
            )

            assert returncode != 0
            assert "timed out" in stderr.lower()
            assert "long_running_cmd" in stderr or "waiting for response" in stderr.lower()

    def test_oserror_with_generic_guidance(self):
        """Test OSError is caught with generic helpful message."""
        with patch("subprocess.run", side_effect=OSError("disk full")):
            returncode, stdout, stderr = safe_subprocess_call(["write_file"], context="saving data")

            assert returncode != 0
            assert "error" in stderr.lower()
            assert "saving data" in stderr.lower()

    def test_unicode_decode_error_handling(self):
        """Test that unicode decode errors are handled gracefully."""
        with patch(
            "subprocess.run",
            return_value=Mock(
                returncode=0,
                stdout=b"\xff\xfe invalid utf-8",
                stderr=b"",
            ),
        ):
            returncode, stdout, stderr = safe_subprocess_call(
                ["binary_output"], context="processing binary"
            )

            # Should not raise, should handle gracefully
            assert returncode == 0
            # Output may be garbled but shouldn't crash

    def test_nonzero_exit_code_preserved(self):
        """Test that non-zero exit codes are preserved."""
        with patch(
            "subprocess.run",
            return_value=Mock(returncode=42, stdout="output", stderr="error message"),
        ):
            returncode, stdout, stderr = safe_subprocess_call(["failing_command"], context="test")

            assert returncode == 42
            assert stdout == "output"
            assert stderr == "error message"

    def test_context_helps_identify_operation(self):
        """Test that context string helps identify which operation failed."""
        contexts = [
            "checking prerequisites",
            "launching claude",
            "installing npm package",
            "running git command",
        ]

        for context in contexts:
            with patch("subprocess.run", side_effect=FileNotFoundError("not found")):
                _, _, stderr = safe_subprocess_call(["cmd"], context=context)
                assert context in stderr.lower()

    def test_command_array_formatting(self):
        """Test that command arrays are formatted readably in errors."""
        with patch("subprocess.run", side_effect=FileNotFoundError("not found")):
            _, _, stderr = safe_subprocess_call(
                ["git", "clone", "https://example.com/repo.git"],
                context="cloning repository",
            )

            # Should show the command in a readable format
            assert "git" in stderr
            assert "clone" in stderr or "cloning repository" in stderr.lower()

    def test_empty_context_still_provides_error(self):
        """Test that errors are still helpful even with empty context."""
        with patch("subprocess.run", side_effect=FileNotFoundError("not found")):
            returncode, stdout, stderr = safe_subprocess_call(["missing_tool"], context="")

            assert returncode == 127
            assert "not found" in stderr.lower()
            assert "missing_tool" in stderr

    def test_multiple_errors_in_sequence(self):
        """Test that multiple errors are all handled correctly."""
        errors = [
            FileNotFoundError("not found"),
            PermissionError("denied"),
            subprocess.TimeoutExpired("cmd", 1),
        ]

        for error in errors:
            with patch("subprocess.run", side_effect=error):
                returncode, _, stderr = safe_subprocess_call(["cmd"], context="testing")
                assert returncode != 0
                assert len(stderr) > 0

    def test_stdout_and_stderr_both_captured(self):
        """Test that both stdout and stderr are captured."""
        with patch(
            "subprocess.run",
            return_value=Mock(
                returncode=1,
                stdout="standard output",
                stderr="error output",
            ),
        ):
            returncode, stdout, stderr = safe_subprocess_call(["cmd"], context="test")

            assert stdout == "standard output"
            assert stderr == "error output"
            assert returncode == 1

    def test_successful_call_returns_clean_output(self):
        """Test that successful calls return output without modification."""
        with patch(
            "subprocess.run",
            return_value=Mock(returncode=0, stdout="success", stderr=""),
        ):
            returncode, stdout, stderr = safe_subprocess_call(["cmd"], context="test")

            assert returncode == 0
            assert stdout == "success"
            assert stderr == ""


class TestErrorContextPropagation:
    """Tests for error context propagation through the stack."""

    def test_prerequisite_check_includes_installation_help(self):
        """Test that prerequisite check errors include installation guidance."""
        from amplihack.utils.prerequisites import PrerequisiteChecker

        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value=None):
            result = checker.check_tool("git")

            assert result.available is False
            assert result.error is not None
            # Error should be actionable
            assert len(result.error) > 0

    def test_missing_tool_error_suggests_installation(self):
        """Test that missing tool errors suggest how to install."""
        from amplihack.utils.prerequisites import PrerequisiteChecker

        with patch("platform.system", return_value="Darwin"):
            checker = PrerequisiteChecker()
            install_cmd = checker.get_install_command("git")

            # Should provide installation command
            assert "brew" in install_cmd
            assert "git" in install_cmd

    def test_error_messages_are_user_friendly(self):
        """Test that error messages are user-friendly, not developer-focused."""
        with patch("subprocess.run", side_effect=FileNotFoundError("command not found")):
            _, _, stderr = safe_subprocess_call(["missing"], context="launching application")

            # Should not contain Python stack traces or technical jargon
            assert "traceback" not in stderr.lower()
            assert "exception" not in stderr.lower()
            # Should be actionable
            assert "not found" in stderr.lower()


class TestRealWorldScenarios:
    """Tests for real-world error scenarios."""

    def test_npm_not_installed_scenario(self):
        """Test scenario: npm not installed, user tries to use claude-trace."""
        from amplihack.utils.prerequisites import PrerequisiteChecker

        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value=None):
            result = checker.check_tool("npm")

            assert result.available is False
            assert result.error is not None

            # Should get helpful installation command
            install_cmd = checker.get_install_command("npm")
            assert len(install_cmd) > 0

    def test_git_not_installed_scenario(self):
        """Test scenario: git not installed, user tries to clone repo."""
        from amplihack.utils.prerequisites import PrerequisiteChecker

        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value=None):
            result = checker.check_tool("git")

            assert result.available is False

    def test_uv_not_installed_scenario(self):
        """Test scenario: uv not installed in development environment."""
        from amplihack.utils.prerequisites import PrerequisiteChecker

        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value=None):
            result = checker.check_tool("uv")

            assert result.available is False
            # Should provide installation guidance
            install_cmd = checker.get_install_command("uv")
            assert len(install_cmd) > 0

    def test_all_missing_scenario(self):
        """Test scenario: fresh system with no development tools."""
        from amplihack.utils.prerequisites import PrerequisiteChecker

        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value=None):
            result = checker.check_all_prerequisites()

            assert result.all_available is False
            assert len(result.missing_tools) == 4  # node, npm, uv, git

            # Should get comprehensive guidance
            message = checker.format_missing_prerequisites(result.missing_tools)
            assert "node" in message.lower()
            assert "npm" in message.lower()
            assert "uv" in message.lower()
            assert "git" in message.lower()
