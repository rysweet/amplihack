"""Tests for interactive installation features.

Tests cover:
- InteractiveInstaller class
- InstallationResult and InstallationAuditEntry data structures
- Interactive installation workflow
- Audit logging
- Security features (no shell=True, hardcoded commands)
- Edge cases (non-TTY, declined, failed installations)
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

try:
    import pytest
except ImportError:
    raise ImportError("pytest is required to run tests. Install with: pip install pytest")

from amplihack.utils.prerequisites import (
    InstallationAuditEntry,
    InstallationResult,
    InteractiveInstaller,
    Platform,
    PrerequisiteChecker,
)


# ============================================================================
# UNIT TESTS - Data Structures
# ============================================================================


class TestInstallationDataStructures:
    """Unit tests for installation data structures."""

    def test_installation_result_creation(self):
        """Test InstallationResult data structure."""
        result = InstallationResult(
            tool="node",
            success=True,
            command_executed=["brew", "install", "node"],
            stdout="Node.js installed",
            stderr="",
            exit_code=0,
            timestamp="2025-01-01T00:00:00Z",
            user_approved=True,
        )

        assert result.tool == "node"
        assert result.success is True
        assert result.command_executed == ["brew", "install", "node"]
        assert result.exit_code == 0
        assert result.user_approved is True

    def test_installation_audit_entry_creation(self):
        """Test InstallationAuditEntry data structure."""
        entry = InstallationAuditEntry(
            timestamp="2025-01-01T00:00:00Z",
            tool="git",
            platform="macos",
            command=["brew", "install", "git"],
            user_approved=True,
            success=True,
            exit_code=0,
            error_message=None,
        )

        assert entry.tool == "git"
        assert entry.platform == "macos"
        assert entry.user_approved is True
        assert entry.success is True
        assert entry.error_message is None


# ============================================================================
# UNIT TESTS - InteractiveInstaller
# ============================================================================


class TestInteractiveInstallerInit:
    """Unit tests for InteractiveInstaller initialization."""

    def test_init_with_platform(self):
        """Test InteractiveInstaller initialization."""
        installer = InteractiveInstaller(Platform.MACOS)
        assert installer.platform == Platform.MACOS
        assert installer.audit_log_path.name == "installation_audit.jsonl"

    def test_audit_log_path_in_home(self):
        """Test that audit log is in .claude/runtime/logs."""
        installer = InteractiveInstaller(Platform.LINUX)
        assert ".claude" in str(installer.audit_log_path)
        assert "runtime/logs" in str(installer.audit_log_path)


class TestIsInteractiveEnvironment:
    """Unit tests for interactive environment detection."""

    def test_is_interactive_with_tty(self):
        """Test interactive detection with TTY."""
        installer = InteractiveInstaller(Platform.MACOS)
        with patch("sys.stdin.isatty", return_value=True), patch.dict(
            "os.environ", {}, clear=True
        ):
            assert installer.is_interactive_environment() is True

    def test_is_not_interactive_without_tty(self):
        """Test non-interactive detection without TTY."""
        installer = InteractiveInstaller(Platform.MACOS)
        with patch("sys.stdin.isatty", return_value=False):
            assert installer.is_interactive_environment() is False

    def test_is_not_interactive_in_ci(self):
        """Test non-interactive detection in CI environment."""
        installer = InteractiveInstaller(Platform.MACOS)
        with patch("sys.stdin.isatty", return_value=True), patch.dict(
            "os.environ", {"CI": "true"}
        ):
            assert installer.is_interactive_environment() is False

    def test_detects_github_actions(self):
        """Test detection of GitHub Actions CI."""
        installer = InteractiveInstaller(Platform.LINUX)
        with patch("sys.stdin.isatty", return_value=True), patch.dict(
            "os.environ", {"GITHUB_ACTIONS": "true"}
        ):
            assert installer.is_interactive_environment() is False


class TestPromptForApproval:
    """Unit tests for user approval prompts."""

    def test_prompt_approval_yes(self):
        """Test user approves installation with 'yes'."""
        installer = InteractiveInstaller(Platform.MACOS)
        with patch("builtins.input", return_value="y"):
            approved = installer.prompt_for_approval("node", ["brew", "install", "node"])
            assert approved is True

    def test_prompt_approval_no(self):
        """Test user declines installation with 'no'."""
        installer = InteractiveInstaller(Platform.MACOS)
        with patch("builtins.input", return_value="n"):
            approved = installer.prompt_for_approval("node", ["brew", "install", "node"])
            assert approved is False

    def test_prompt_approval_default_no(self):
        """Test default is 'no' when user presses enter."""
        installer = InteractiveInstaller(Platform.MACOS)
        with patch("builtins.input", return_value=""):
            approved = installer.prompt_for_approval("git", ["brew", "install", "git"])
            assert approved is False

    def test_prompt_approval_retry_invalid(self):
        """Test prompt retries on invalid input."""
        installer = InteractiveInstaller(Platform.LINUX)
        with patch("builtins.input", side_effect=["invalid", "y"]):
            approved = installer.prompt_for_approval("npm", ["sudo", "apt", "install", "npm"])
            assert approved is True


class TestExecuteInstallCommand:
    """Unit tests for command execution."""

    def test_execute_command_success(self):
        """Test successful command execution."""
        installer = InteractiveInstaller(Platform.MACOS)
        mock_result = Mock(returncode=0, stdout="Success", stderr="")

        with patch("subprocess.run", return_value=mock_result):
            result = installer._execute_install_command(["echo", "test"])
            assert result.returncode == 0
            assert result.stdout == "Success"

    def test_execute_command_uses_stdin(self):
        """Test that command execution uses sys.stdin for interactivity."""
        installer = InteractiveInstaller(Platform.LINUX)
        with patch("subprocess.run") as mock_run:
            installer._execute_install_command(["sudo", "apt", "install", "git"])
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["stdin"] == sys.stdin

    def test_execute_command_no_shell(self):
        """Test that command execution does NOT use shell=True."""
        installer = InteractiveInstaller(Platform.MACOS)
        with patch("subprocess.run") as mock_run:
            installer._execute_install_command(["brew", "install", "node"])
            call_kwargs = mock_run.call_args[1]
            assert "shell" not in call_kwargs or call_kwargs["shell"] is False


class TestAuditLogging:
    """Unit tests for audit logging."""

    def test_log_audit_creates_directory(self):
        """Test that audit logging creates directory if needed."""
        installer = InteractiveInstaller(Platform.MACOS)
        entry = InstallationAuditEntry(
            timestamp="2025-01-01T00:00:00Z",
            tool="node",
            platform="macos",
            command=["brew", "install", "node"],
            user_approved=True,
            success=True,
            exit_code=0,
        )

        with patch("pathlib.Path.mkdir") as mock_mkdir, patch(
            "builtins.open", mock_open()
        ) as mock_file:
            installer._log_audit(entry)
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_log_audit_writes_jsonl(self):
        """Test that audit entries are written as JSONL."""
        installer = InteractiveInstaller(Platform.LINUX)
        entry = InstallationAuditEntry(
            timestamp="2025-01-01T00:00:00Z",
            tool="git",
            platform="linux",
            command=["sudo", "apt", "install", "git"],
            user_approved=False,
            success=False,
            exit_code=-1,
            error_message="User declined",
        )

        mock_file_handle = mock_open()
        with patch("pathlib.Path.mkdir"), patch("builtins.open", mock_file_handle):
            installer._log_audit(entry)

            # Check that write was called with JSON + newline
            written_data = "".join(
                call.args[0] for call in mock_file_handle().write.call_args_list
            )
            assert written_data.endswith("\n")
            parsed = json.loads(written_data.strip())
            assert parsed["tool"] == "git"
            assert parsed["user_approved"] is False


class TestInstallTool:
    """Unit tests for install_tool method."""

    def test_install_tool_non_interactive(self):
        """Test install_tool in non-interactive environment."""
        installer = InteractiveInstaller(Platform.MACOS)
        with patch.object(installer, "is_interactive_environment", return_value=False):
            result = installer.install_tool("node")
            assert result.success is False
            assert result.user_approved is False
            assert "Non-interactive" in result.stderr

    def test_install_tool_no_command_available(self):
        """Test install_tool when no command is available for platform."""
        installer = InteractiveInstaller(Platform.UNKNOWN)
        with patch.object(installer, "is_interactive_environment", return_value=True):
            result = installer.install_tool("node")
            assert result.success is False
            assert "No installation command available" in result.stderr

    def test_install_tool_user_declines(self):
        """Test install_tool when user declines installation."""
        installer = InteractiveInstaller(Platform.MACOS)
        with patch.object(
            installer, "is_interactive_environment", return_value=True
        ), patch.object(installer, "prompt_for_approval", return_value=False), patch.object(
            installer, "_log_audit"
        ) as mock_log:
            result = installer.install_tool("git")
            assert result.success is False
            assert result.user_approved is False
            assert "declined" in result.stderr.lower()
            mock_log.assert_called_once()

    def test_install_tool_success(self):
        """Test successful tool installation."""
        installer = InteractiveInstaller(Platform.MACOS)
        mock_subprocess_result = Mock(returncode=0, stdout="Installed", stderr="")

        with patch.object(
            installer, "is_interactive_environment", return_value=True
        ), patch.object(installer, "prompt_for_approval", return_value=True), patch.object(
            installer, "_execute_install_command", return_value=mock_subprocess_result
        ), patch.object(
            installer, "_log_audit"
        ) as mock_log:
            result = installer.install_tool("node")
            assert result.success is True
            assert result.user_approved is True
            assert result.exit_code == 0
            mock_log.assert_called_once()

    def test_install_tool_failure(self):
        """Test failed tool installation."""
        installer = InteractiveInstaller(Platform.LINUX)
        mock_subprocess_result = Mock(
            returncode=1, stdout="", stderr="Package not found"
        )

        with patch.object(
            installer, "is_interactive_environment", return_value=True
        ), patch.object(installer, "prompt_for_approval", return_value=True), patch.object(
            installer, "_execute_install_command", return_value=mock_subprocess_result
        ), patch.object(
            installer, "_log_audit"
        ):
            result = installer.install_tool("npm")
            assert result.success is False
            assert result.user_approved is True
            assert result.exit_code == 1
            assert "Package not found" in result.stderr

    def test_install_tool_exception_handling(self):
        """Test install_tool handles exceptions gracefully."""
        installer = InteractiveInstaller(Platform.MACOS)

        with patch.object(
            installer, "is_interactive_environment", return_value=True
        ), patch.object(installer, "prompt_for_approval", return_value=True), patch.object(
            installer, "_execute_install_command", side_effect=Exception("Unexpected error")
        ), patch.object(
            installer, "_log_audit"
        ):
            result = installer.install_tool("uv")
            assert result.success is False
            assert result.user_approved is True
            assert "Unexpected error" in result.stderr


# ============================================================================
# INTEGRATION TESTS - PrerequisiteChecker.check_and_install
# ============================================================================


class TestCheckAndInstall:
    """Integration tests for check_and_install method."""

    def test_check_and_install_all_available(self):
        """Test check_and_install when all prerequisites available."""
        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value="/usr/bin/tool"), patch(
            "amplihack.utils.prerequisites.get_claude_cli_path", return_value="/usr/bin/claude"
        ):
            result = checker.check_and_install(interactive=True)
            assert result.all_available is True

    def test_check_and_install_non_interactive_mode(self):
        """Test check_and_install with interactive=False."""
        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value=None):
            result = checker.check_and_install(interactive=False)
            assert result.all_available is False
            assert len(result.missing_tools) > 0

    def test_check_and_install_non_interactive_environment(self):
        """Test check_and_install in non-interactive environment."""
        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value=None), patch(
            "sys.stdin.isatty", return_value=False
        ):
            result = checker.check_and_install(interactive=True)
            assert result.all_available is False

    def test_check_and_install_with_installations(self):
        """Test check_and_install installs missing tools."""
        checker = PrerequisiteChecker()

        # Mock initial check shows missing tools
        mock_initial_result = Mock(
            all_available=False,
            missing_tools=[Mock(tool="node"), Mock(tool="npm")],
            available_tools=[],
        )

        # Mock successful installations
        mock_install_result_node = Mock(
            success=True, user_approved=True, stderr=""
        )
        mock_install_result_npm = Mock(
            success=True, user_approved=True, stderr=""
        )

        # Mock final check shows all available
        mock_final_result = Mock(
            all_available=True, missing_tools=[], available_tools=[Mock(), Mock()]
        )

        with patch.object(
            checker, "check_all_prerequisites", side_effect=[mock_initial_result, mock_final_result]
        ), patch(
            "amplihack.utils.prerequisites.InteractiveInstaller"
        ) as mock_installer_class:
            mock_installer = Mock()
            mock_installer.is_interactive_environment.return_value = True
            mock_installer.install_tool.side_effect = [
                mock_install_result_node,
                mock_install_result_npm,
            ]
            mock_installer_class.return_value = mock_installer

            result = checker.check_and_install(interactive=True)

            assert result.all_available is True
            assert mock_installer.install_tool.call_count == 2

    def test_check_and_install_user_declines_all(self):
        """Test check_and_install when user declines all installations."""
        checker = PrerequisiteChecker()

        mock_initial_result = Mock(
            all_available=False,
            missing_tools=[Mock(tool="git")],
            available_tools=[],
        )

        mock_install_result = Mock(
            success=False, user_approved=False, stderr="User declined"
        )

        with patch.object(
            checker, "check_all_prerequisites", return_value=mock_initial_result
        ), patch(
            "amplihack.utils.prerequisites.InteractiveInstaller"
        ) as mock_installer_class:
            mock_installer = Mock()
            mock_installer.is_interactive_environment.return_value = True
            mock_installer.install_tool.return_value = mock_install_result
            mock_installer_class.return_value = mock_installer

            result = checker.check_and_install(interactive=True)

            assert result.all_available is False


# ============================================================================
# SECURITY TESTS
# ============================================================================


class TestSecurityFeatures:
    """Tests for security features."""

    def test_install_commands_are_lists(self):
        """Test that INSTALL_COMMANDS use List[str] not strings."""
        for platform, commands in PrerequisiteChecker.INSTALL_COMMANDS.items():
            if platform == Platform.UNKNOWN:
                continue
            for tool, command in commands.items():
                assert isinstance(command, list), f"{platform}.{tool} must be List[str]"
                assert all(
                    isinstance(arg, str) for arg in command
                ), f"{platform}.{tool} args must be strings"

    def test_no_shell_injection_in_commands(self):
        """Test that commands don't contain shell operators."""
        dangerous_chars = [";", "&", "|", "$", "`", "(", ")"]
        for platform, commands in PrerequisiteChecker.INSTALL_COMMANDS.items():
            if platform == Platform.UNKNOWN:
                continue
            for tool, command in commands.items():
                command_str = " ".join(command)
                for char in dangerous_chars:
                    if char in command_str and tool != "uv":  # uv uses pipe in sh -c
                        assert False, f"{platform}.{tool} contains dangerous char: {char}"

    def test_audit_log_path_secure(self):
        """Test that audit log is in user's home directory."""
        installer = InteractiveInstaller(Platform.MACOS)
        assert str(installer.audit_log_path).startswith(str(Path.home()))


# ============================================================================
# EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_install_tool_with_empty_tool_name(self):
        """Test install_tool with empty tool name."""
        installer = InteractiveInstaller(Platform.MACOS)
        with patch.object(installer, "is_interactive_environment", return_value=True):
            result = installer.install_tool("")
            assert result.success is False

    def test_install_tool_with_unknown_platform(self):
        """Test install_tool on unknown platform."""
        installer = InteractiveInstaller(Platform.UNKNOWN)
        with patch.object(installer, "is_interactive_environment", return_value=True):
            result = installer.install_tool("node")
            assert result.success is False
            assert "No installation command" in result.stderr

    def test_audit_log_handles_io_errors(self):
        """Test that audit logging handles I/O errors gracefully."""
        installer = InteractiveInstaller(Platform.LINUX)
        entry = InstallationAuditEntry(
            timestamp="2025-01-01T00:00:00Z",
            tool="git",
            platform="linux",
            command=["sudo", "apt", "install", "git"],
            user_approved=True,
            success=True,
            exit_code=0,
        )

        with patch("pathlib.Path.mkdir"), patch(
            "builtins.open", side_effect=PermissionError("No write access")
        ):
            # Should not raise exception - should handle gracefully
            installer._log_audit(entry)  # Should complete without error
