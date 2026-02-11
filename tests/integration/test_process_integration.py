"""Integration tests for ProcessManager with real command execution.

These tests execute REAL commands (not mocks) to verify:
1. Cross-platform compatibility (Unix and Windows)
2. Shell injection prevention with actual shell injection attempts
3. npm/npx/node command execution on Windows without shell=True

Philosophy:
- Integration tests use REAL commands to verify behavior
- Security tests attempt ACTUAL injection attacks (safely)
- Tests must pass on both Unix and Windows
"""

import os

import pytest

from amplihack.utils.process import ProcessManager


class TestRealCommandExecution:
    """Test real command execution without mocking."""

    def test_simple_command_executes(self):
        """Verify basic commands execute successfully."""
        if ProcessManager.is_windows():
            result = ProcessManager.run_command(["cmd", "/c", "echo", "hello"])
        else:
            result = ProcessManager.run_command(["echo", "hello"])

        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_python_version_command(self):
        """Verify Python commands work cross-platform."""
        result = ProcessManager.run_command(["python", "--version"])

        assert result.returncode == 0
        assert "Python" in result.stdout or "Python" in result.stderr

    def test_command_with_arguments(self):
        """Verify commands with multiple arguments work."""
        result = ProcessManager.run_command(
            ["python", "-c", "print('test output')"]
        )

        assert result.returncode == 0
        assert "test output" in result.stdout

    def test_working_directory_respected(self, tmp_path):
        """Verify cwd parameter changes working directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        if ProcessManager.is_windows():
            result = ProcessManager.run_command(
                ["cmd", "/c", "dir", "/b"],
                cwd=str(tmp_path)
            )
            assert "test.txt" in result.stdout
        else:
            result = ProcessManager.run_command(
                ["ls"],
                cwd=str(tmp_path)
            )
            assert "test.txt" in result.stdout

    def test_environment_variables_passed(self):
        """Verify custom environment variables are passed."""
        custom_env = os.environ.copy()
        custom_env["TEST_VAR"] = "test_value"

        if ProcessManager.is_windows():
            result = ProcessManager.run_command(
                ["cmd", "/c", "echo", "%TEST_VAR%"],
                env=custom_env
            )
        else:
            result = ProcessManager.run_command(
                ["sh", "-c", "echo $TEST_VAR"],
                env=custom_env
            )

        assert "test_value" in result.stdout


class TestWindowsNpmIntegration:
    """Integration tests for Windows npm/npx/node commands."""

    @pytest.mark.skipif(
        not ProcessManager.is_windows(),
        reason="Windows-specific npm test"
    )
    def test_npm_version_command_works(self):
        """Verify npm --version works without shell=True on Windows."""
        try:
            result = ProcessManager.run_command(["npm", "--version"])
            assert result.returncode == 0
            # Output should be version number like "10.2.4"
            assert result.stdout.strip().replace(".", "").isdigit()
        except FileNotFoundError:
            pytest.skip("npm not installed on this Windows system")

    @pytest.mark.skipif(
        not ProcessManager.is_windows(),
        reason="Windows-specific npx test"
    )
    def test_npx_version_command_works(self):
        """Verify npx --version works without shell=True on Windows."""
        try:
            result = ProcessManager.run_command(["npx", "--version"])
            assert result.returncode == 0
            # npx version output
            assert result.stdout.strip().replace(".", "").isdigit()
        except FileNotFoundError:
            pytest.skip("npx not installed on this Windows system")

    @pytest.mark.skipif(
        not ProcessManager.is_windows(),
        reason="Windows-specific node test"
    )
    def test_node_version_command_works(self):
        """Verify node --version works without shell=True on Windows."""
        try:
            result = ProcessManager.run_command(["node", "--version"])
            assert result.returncode == 0
            # Node version like "v20.10.0"
            assert result.stdout.strip().startswith("v")
        except FileNotFoundError:
            pytest.skip("node not installed on this Windows system")


class TestShellInjectionActualAttempts:
    """Test that shell injection attacks fail safely with REAL execution.

    These tests attempt ACTUAL shell injection attacks to verify they
    are neutralized and treated as literal arguments.
    """

    def test_semicolon_injection_fails_safely(self):
        """Verify semicolon command separator is treated as literal."""
        # Attempt to inject a second command via semicolon
        malicious_arg = "; echo PWNED"

        # This should try to run Python with a literal filename containing semicolon
        # The semicolon should NOT be interpreted as a command separator
        result = ProcessManager.run_command(
            ["python", "-c", f"print('arg: {malicious_arg}')"]
        )

        # The command should succeed (Python prints the argument)
        assert result.returncode == 0
        assert "; echo PWNED" in result.stdout
        # Crucially, "PWNED" should appear as part of the print, NOT as separate command output
        assert result.stdout.count("PWNED") == 1  # Only in the print statement

    def test_pipe_injection_fails_safely(self):
        """Verify pipe character is treated as literal, not pipe operator."""
        malicious_arg = "| cat /etc/passwd"

        result = ProcessManager.run_command(
            ["python", "-c", f"print('arg: {malicious_arg}')"]
        )

        # Should succeed, with pipe as literal character
        assert result.returncode == 0
        assert "| cat /etc/passwd" in result.stdout

    @pytest.mark.skipif(
        ProcessManager.is_windows(),
        reason="Unix-specific test"
    )
    def test_command_substitution_fails_safely_unix(self):
        """Verify $(cmd) is treated as literal on Unix."""
        malicious_arg = "$(whoami)"

        result = ProcessManager.run_command(
            ["echo", malicious_arg]
        )

        # Should output literal "$(whoami)", NOT the result of whoami command
        assert result.returncode == 0
        assert "$(whoami)" in result.stdout

    @pytest.mark.skipif(
        not ProcessManager.is_windows(),
        reason="Windows-specific test"
    )
    def test_ampersand_injection_fails_safely_windows(self):
        """Verify & command separator is treated as literal on Windows."""
        malicious_arg = "& echo PWNED"

        result = ProcessManager.run_command(
            ["cmd", "/c", "echo", malicious_arg]
        )

        # Should output literal "& echo PWNED", NOT execute echo PWNED
        assert result.returncode == 0
        # The output should contain the literal string, not a separate execution
        assert "& echo PWNED" in result.stdout


class TestCommandListValidation:
    """Test that commands must be list[str], not strings."""

    def test_command_must_be_list_not_string(self):
        """Verify that passing string instead of list raises error."""
        # ProcessManager.run_command expects list[str]
        # Passing a string should fail (subprocess.run will raise FileNotFoundError or TypeError)
        with pytest.raises((TypeError, FileNotFoundError)):
            # This should fail because "echo hello" is a string, not list
            # subprocess.run will try to execute a file named "echo hello" (FileNotFoundError)
            ProcessManager.run_command("echo hello")  # type: ignore


class TestCrossPlatformPathHandling:
    """Test that paths are handled correctly across platforms."""

    def test_absolute_paths_work(self, tmp_path):
        """Verify absolute paths work on both Unix and Windows."""
        test_file = tmp_path / "script.py"
        test_file.write_text("print('hello from script')")

        result = ProcessManager.run_command(
            ["python", str(test_file)]
        )

        assert result.returncode == 0
        assert "hello from script" in result.stdout

    def test_relative_paths_with_cwd(self, tmp_path):
        """Verify relative paths work with cwd parameter."""
        script_path = tmp_path / "script.py"
        script_path.write_text("print('relative path test')")

        result = ProcessManager.run_command(
            ["python", "script.py"],
            cwd=str(tmp_path)
        )

        assert result.returncode == 0
        assert "relative path test" in result.stdout


class TestErrorHandling:
    """Test error handling for invalid commands."""

    def test_nonexistent_command_raises_error(self):
        """Verify FileNotFoundError for non-existent commands."""
        with pytest.raises(FileNotFoundError):
            ProcessManager.run_command(["this_command_does_not_exist_12345"])

    def test_command_with_bad_arguments(self):
        """Verify commands with invalid arguments return non-zero."""
        result = ProcessManager.run_command(
            ["python", "--invalid-flag-xyz"],
            capture_output=True
        )

        # Should fail (non-zero exit code)
        assert result.returncode != 0

    def test_empty_command_list_handled(self):
        """Verify empty command list doesn't crash."""
        # This should raise an error or handle gracefully
        # subprocess.run([]) typically raises IndexError or ValueError
        try:
            result = ProcessManager.run_command([])
            # If it doesn't raise, should at least fail
            assert result.returncode != 0
        except (IndexError, ValueError, FileNotFoundError):
            # Expected - empty command list is invalid
            pass


class TestOutputCapture:
    """Test stdout/stderr capture behavior."""

    def test_stdout_captured_by_default(self):
        """Verify stdout is captured by default."""
        result = ProcessManager.run_command(
            ["python", "-c", "print('stdout test')"]
        )

        assert "stdout test" in result.stdout
        assert result.stdout.strip() == "stdout test"

    def test_stderr_captured(self):
        """Verify stderr is captured."""
        result = ProcessManager.run_command(
            ["python", "-c", "import sys; sys.stderr.write('stderr test\\n')"]
        )

        assert "stderr test" in result.stderr

    def test_capture_output_false_returns_none(self):
        """Verify capture_output=False doesn't capture output."""
        result = ProcessManager.run_command(
            ["python", "-c", "print('test')"],
            capture_output=False
        )

        # When capture_output=False, stdout/stderr should be None
        assert result.stdout is None
        assert result.stderr is None


@pytest.mark.skipif(
    not ProcessManager.is_windows(),
    reason="Windows-specific integration test"
)
class TestWindowsSpecificBehavior:
    """Windows-specific integration tests."""

    def test_cmd_commands_work(self):
        """Verify Windows cmd.exe commands execute."""
        result = ProcessManager.run_command(
            ["cmd", "/c", "echo", "Windows test"]
        )

        assert result.returncode == 0
        assert "Windows test" in result.stdout

    def test_powershell_commands_work(self):
        """Verify PowerShell commands execute."""
        try:
            result = ProcessManager.run_command(
                ["powershell", "-Command", "Write-Output 'PowerShell test'"]
            )

            assert result.returncode == 0
            assert "PowerShell test" in result.stdout
        except FileNotFoundError:
            pytest.skip("PowerShell not available")

    def test_windows_path_separators(self, tmp_path):
        """Verify Windows path separators work correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Use Windows-style path separator
        windows_path = str(tmp_path).replace("/", "\\")

        result = ProcessManager.run_command(
            ["cmd", "/c", "dir", "/b"],
            cwd=windows_path
        )

        assert "test.txt" in result.stdout


@pytest.mark.skipif(
    ProcessManager.is_windows(),
    reason="Unix-specific integration test"
)
class TestUnixSpecificBehavior:
    """Unix-specific integration tests."""

    def test_shell_commands_via_sh(self):
        """Verify Unix shell commands work via sh -c."""
        result = ProcessManager.run_command(
            ["sh", "-c", "echo 'Unix test'"]
        )

        assert result.returncode == 0
        assert "Unix test" in result.stdout

    def test_bash_commands_if_available(self):
        """Verify bash commands work if bash is available."""
        try:
            result = ProcessManager.run_command(
                ["bash", "-c", "echo 'Bash test'"]
            )

            assert result.returncode == 0
            assert "Bash test" in result.stdout
        except FileNotFoundError:
            pytest.skip("bash not available")

    def test_unix_path_separators(self, tmp_path):
        """Verify Unix path separators work correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = ProcessManager.run_command(
            ["ls"],
            cwd=str(tmp_path)
        )

        assert "test.txt" in result.stdout
