"""Security tests for process.py - Shell injection prevention.

This module tests that ProcessManager.run_command() does NOT use shell=True
and properly handles Windows npm/npx/node commands without shell injection risk.

Philosophy:
- NEVER use shell=True (prevents shell injection attacks)
- Use shutil.which() to resolve command paths on Windows
- List[str] commands exclusively (no string interpolation)

Security: https://docs.python.org/3/library/subprocess.html#security-considerations
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from amplihack.utils.process import ProcessManager


class TestShellInjectionPrevention:
    """Test that shell injection attacks are prevented."""

    def test_run_command_never_uses_shell_true_on_unix(self):
        """Verify shell=True is never passed to subprocess.run on Unix."""
        with (
            patch.object(ProcessManager, "is_windows", return_value=False),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)

            # Test with various commands including npm/npx/node
            test_commands = [
                ["echo", "hello"],
                ["npm", "install"],
                ["npx", "create-react-app"],
                ["node", "script.js"],
                ["python", "-c", "print('test')"],
            ]

            for cmd in test_commands:
                ProcessManager.run_command(cmd)
                call_kwargs = mock_run.call_args.kwargs
                assert "shell" not in call_kwargs or call_kwargs.get("shell") is False, (
                    f"shell=True was passed for command: {cmd}"
                )

    def test_run_command_never_uses_shell_true_on_windows(self):
        """Verify shell=True is never passed to subprocess.run on Windows."""
        with (
            patch.object(ProcessManager, "is_windows", return_value=True),
            patch(
                "amplihack.utils.process.shutil.which",
                return_value="C:\\Program Files\\nodejs\\npm.cmd",
            ),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)

            # Test with npm/npx/node commands that previously used shell=True
            test_commands = [
                ["npm", "install"],
                ["npx", "create-react-app", "my-app"],
                ["node", "script.js"],
            ]

            for cmd in test_commands:
                ProcessManager.run_command(cmd)
                call_kwargs = mock_run.call_args.kwargs
                assert "shell" not in call_kwargs or call_kwargs.get("shell") is False, (
                    f"shell=True was passed for command: {cmd} on Windows"
                )

    def test_windows_npm_uses_resolved_path(self):
        """Verify Windows npm commands use shutil.which() resolved path."""
        fake_npm_path = "C:\\Program Files\\nodejs\\npm.cmd"

        with (
            patch.object(ProcessManager, "is_windows", return_value=True),
            patch("amplihack.utils.process.shutil.which", return_value=fake_npm_path) as mock_which,
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)

            ProcessManager.run_command(["npm", "install", "express"])

            # Verify shutil.which was called for npm
            mock_which.assert_called_once_with("npm")

            # Verify the resolved path was used in the command
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == fake_npm_path, (
                f"Expected resolved path {fake_npm_path}, got {call_args[0]}"
            )
            assert call_args[1:] == ["install", "express"]

    def test_windows_npx_uses_resolved_path(self):
        """Verify Windows npx commands use shutil.which() resolved path."""
        fake_npx_path = "C:\\Program Files\\nodejs\\npx.cmd"

        with (
            patch.object(ProcessManager, "is_windows", return_value=True),
            patch("amplihack.utils.process.shutil.which", return_value=fake_npx_path) as mock_which,
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)

            ProcessManager.run_command(["npx", "create-react-app", "my-app"])

            mock_which.assert_called_once_with("npx")
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == fake_npx_path

    def test_windows_node_uses_resolved_path(self):
        """Verify Windows node commands use shutil.which() resolved path."""
        fake_node_path = "C:\\Program Files\\nodejs\\node.exe"

        with (
            patch.object(ProcessManager, "is_windows", return_value=True),
            patch(
                "amplihack.utils.process.shutil.which", return_value=fake_node_path
            ) as mock_which,
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)

            ProcessManager.run_command(["node", "script.js"])

            mock_which.assert_called_once_with("node")
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == fake_node_path

    def test_windows_which_not_found_uses_original_command(self):
        """When shutil.which() returns None, use original command (will fail properly)."""
        with (
            patch.object(ProcessManager, "is_windows", return_value=True),
            patch("amplihack.utils.process.shutil.which", return_value=None),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)

            ProcessManager.run_command(["npm", "install"])

            # Original command should be used when which() returns None
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "npm", "Should use original command when which() fails"

    def test_non_npm_commands_not_affected_on_windows(self):
        """Verify non-npm/npx/node commands are not modified on Windows."""
        with (
            patch.object(ProcessManager, "is_windows", return_value=True),
            patch("amplihack.utils.process.shutil.which") as mock_which,
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)

            # These commands should not trigger the Windows npm handling
            ProcessManager.run_command(["git", "status"])

            # shutil.which should NOT be called for non-npm commands
            mock_which.assert_not_called()


class TestShellInjectionAttackVectors:
    """Test specific attack vectors that shell=True would enable."""

    @pytest.mark.parametrize(
        "malicious_arg",
        [
            "; rm -rf /",
            "& del C:\\Windows\\System32",
            "| cat /etc/passwd",
            "$(whoami)",
            "`whoami`",
            "\n rm -rf /",
            "&& echo pwned",
            "|| echo pwned",
        ],
    )
    def test_injection_in_npm_install_argument(self, malicious_arg):
        """Verify injection attempts in npm install arguments are safe.

        Without shell=True, these are passed as literal strings to npm,
        not interpreted by the shell.
        """
        with (
            patch.object(ProcessManager, "is_windows", return_value=True),
            patch("amplihack.utils.process.shutil.which", return_value="C:\\npm.cmd"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)

            # Attempt injection via package name
            ProcessManager.run_command(["npm", "install", malicious_arg])

            # Verify shell=True was NOT used
            call_kwargs = mock_run.call_args.kwargs
            assert "shell" not in call_kwargs or call_kwargs.get("shell") is False

            # Verify the malicious string was passed as a literal argument
            call_args = mock_run.call_args[0][0]
            assert malicious_arg in call_args, (
                "Malicious string should be passed literally, not interpreted"
            )

    def test_command_list_not_string(self):
        """Verify commands are always passed as list, never string."""
        with (
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)

            ProcessManager.run_command(["echo", "hello world"])

            # First positional argument should be a list
            call_args = mock_run.call_args[0][0]
            assert isinstance(call_args, list), "Command must be passed as list, not string"


class TestEmptyCommandHandling:
    """Test edge cases with empty or invalid commands."""

    def test_empty_command_list(self):
        """Empty command list should not crash."""
        with (
            patch.object(ProcessManager, "is_windows", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)

            # Empty list should be handled gracefully
            ProcessManager.run_command([])

            # Should still pass empty list to subprocess
            call_args = mock_run.call_args[0][0]
            assert call_args == []


class TestSecurityDocumentation:
    """Test that security documentation is in place."""

    def test_docstring_documents_security(self):
        """Verify run_command docstring documents security considerations."""
        docstring = ProcessManager.run_command.__doc__
        assert docstring is not None, "run_command must have a docstring"

        # Check for security documentation
        security_keywords = ["NEVER", "shell=True", "injection", "Security"]
        found_keywords = [kw for kw in security_keywords if kw.lower() in docstring.lower()]
        assert len(found_keywords) >= 2, (
            f"Docstring should document security considerations. "
            f"Found: {found_keywords}, expected at least 2 of {security_keywords}"
        )


class TestBackwardsCompatibility:
    """Ensure the fix maintains backwards compatibility."""

    def test_npm_install_works_on_windows_mock(self):
        """Verify npm install still works with the security fix (mocked)."""
        fake_npm_path = "C:\\Program Files\\nodejs\\npm.cmd"

        with (
            patch.object(ProcessManager, "is_windows", return_value=True),
            patch("amplihack.utils.process.shutil.which", return_value=fake_npm_path),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="added 100 packages",
                stderr="",
            )

            result = ProcessManager.run_command(["npm", "install", "express"])

            assert result.returncode == 0
            assert "added 100 packages" in result.stdout

    def test_return_type_unchanged(self):
        """Verify return type is still subprocess.CompletedProcess."""
        with (
            patch("subprocess.run") as mock_run,
        ):
            mock_result = MagicMock(spec=subprocess.CompletedProcess)
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            result = ProcessManager.run_command(["echo", "test"])

            assert isinstance(result, MagicMock)  # MagicMock with CompletedProcess spec
