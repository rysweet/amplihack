"""Tests for prerequisites module - TDD approach.

Following the testing pyramid:
- 60% Unit tests (18 tests)
- 30% Integration tests (9 tests)
- 10% E2E tests (3 tests)
"""

import subprocess
import sys
from unittest.mock import Mock, patch

try:
    import pytest
except ImportError:
    raise ImportError("pytest is required to run tests. Install with: pip install pytest")

# Module under test (will fail until implemented)
from amplihack.utils.prerequisites import (
    Platform,
    PrerequisiteChecker,
    PrerequisiteResult,
    ToolCheckResult,
    safe_subprocess_call,
)

# ============================================================================
# UNIT TESTS (60% - 18 tests)
# ============================================================================


class TestPlatformDetection:
    """Unit tests for platform detection."""

    def test_detect_macos(self):
        """Test macOS platform detection."""
        with patch("platform.system", return_value="Darwin"):
            checker = PrerequisiteChecker()
            assert checker.platform == Platform.MACOS

    def test_detect_linux_not_wsl(self):
        """Test Linux platform detection (non-WSL)."""
        with patch("platform.system", return_value="Linux"), patch(
            "pathlib.Path.exists", return_value=False
        ):
            checker = PrerequisiteChecker()
            assert checker.platform == Platform.LINUX

    def test_detect_wsl(self):
        """Test WSL platform detection."""
        with patch("platform.system", return_value="Linux"), patch(
            "pathlib.Path.exists", return_value=True
        ), patch("pathlib.Path.read_text", return_value="Linux version microsoft"):
            checker = PrerequisiteChecker()
            assert checker.platform == Platform.WSL

    def test_detect_windows(self):
        """Test Windows platform detection."""
        with patch("platform.system", return_value="Windows"):
            checker = PrerequisiteChecker()
            assert checker.platform == Platform.WINDOWS

    def test_detect_unknown_platform(self):
        """Test unknown platform defaults to UNKNOWN."""
        with patch("platform.system", return_value="FreeBSD"):
            checker = PrerequisiteChecker()
            assert checker.platform == Platform.UNKNOWN


class TestToolChecking:
    """Unit tests for individual tool checking."""

    def test_check_tool_found(self):
        """Test checking for a tool that exists."""
        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value="/usr/bin/git"):
            result = checker.check_tool("git")
            assert result.available is True
            assert result.path == "/usr/bin/git"
            assert result.error is None

    def test_check_tool_not_found(self):
        """Test checking for a tool that doesn't exist."""
        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value=None):
            result = checker.check_tool("nonexistent")
            assert result.available is False
            assert result.path is None
            assert result.error is not None

    def test_check_tool_with_version(self):
        """Test checking tool with version verification."""
        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value="/usr/bin/node"), patch(
            "subprocess.run",
            return_value=Mock(returncode=0, stdout="v20.0.0", stderr=""),
        ):
            result = checker.check_tool("node", version_arg="--version")
            assert result.available is True
            assert result.version == "v20.0.0"

    def test_check_all_prerequisites_success(self):
        """Test checking all prerequisites when all are available."""
        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value="/usr/bin/tool"):
            result = checker.check_all_prerequisites()
            assert result.all_available is True
            assert len(result.missing_tools) == 0
            assert len(result.available_tools) == 5  # node, npm, uv, git, claude


class TestInstallationCommands:
    """Unit tests for installation command generation."""

    def test_get_install_command_macos(self):
        """Test macOS installation command generation."""
        with patch("platform.system", return_value="Darwin"):
            checker = PrerequisiteChecker()
            cmd = checker.get_install_command("node")
            assert "brew" in cmd
            assert "node" in cmd

    def test_get_install_command_linux(self):
        """Test Linux installation command generation."""
        with patch("platform.system", return_value="Linux"), patch(
            "pathlib.Path.exists", return_value=False
        ):
            checker = PrerequisiteChecker()
            cmd = checker.get_install_command("git")
            # Should support apt/dnf/pacman
            assert any(pkg_mgr in cmd for pkg_mgr in ["apt", "dnf", "yum", "pacman"])

    def test_get_install_command_windows(self):
        """Test Windows installation command generation."""
        with patch("platform.system", return_value="Windows"):
            checker = PrerequisiteChecker()
            cmd = checker.get_install_command("git")
            assert "winget" in cmd or "choco" in cmd

    def test_get_install_command_unknown_tool(self):
        """Test installation command for unknown tool."""
        checker = PrerequisiteChecker()
        cmd = checker.get_install_command("unknown_tool")
        # Should provide generic guidance
        assert "install" in cmd.lower() or "unknown" in cmd.lower()


class TestErrorFormatting:
    """Unit tests for error message formatting."""

    def test_format_missing_prerequisites_single(self):
        """Test formatting error for single missing prerequisite."""
        checker = PrerequisiteChecker()
        missing = [ToolCheckResult(tool="git", available=False, error="not found")]
        message = checker.format_missing_prerequisites(missing)
        assert "git" in message
        assert "install" in message.lower()

    def test_format_missing_prerequisites_multiple(self):
        """Test formatting error for multiple missing prerequisites."""
        checker = PrerequisiteChecker()
        missing = [
            ToolCheckResult(tool="git", available=False, error="not found"),
            ToolCheckResult(tool="node", available=False, error="not found"),
        ]
        message = checker.format_missing_prerequisites(missing)
        assert "git" in message
        assert "node" in message

    def test_format_includes_platform_specific_commands(self):
        """Test that error formatting includes platform-specific commands."""
        with patch("platform.system", return_value="Darwin"):
            checker = PrerequisiteChecker()
            missing = [ToolCheckResult(tool="git", available=False, error="not found")]
            message = checker.format_missing_prerequisites(missing)
            assert "brew" in message


class TestSubprocessWrapper:
    """Unit tests for safe subprocess wrapper."""

    def test_safe_subprocess_call_success(self):
        """Test safe subprocess call with successful execution."""
        with patch("subprocess.run", return_value=Mock(returncode=0, stdout="", stderr="")):
            returncode, stdout, stderr = safe_subprocess_call(["echo", "test"], context="testing")
            assert returncode == 0
            assert stderr == ""

    def test_safe_subprocess_call_command_not_found(self):
        """Test safe subprocess call with command not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError("command not found")):
            returncode, stdout, stderr = safe_subprocess_call(["nonexistent"], context="testing")
            assert returncode == 127  # Standard "command not found" exit code
            assert "not found" in stderr.lower()

    def test_safe_subprocess_call_timeout(self):
        """Test safe subprocess call with timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
            returncode, stdout, stderr = safe_subprocess_call(
                ["sleep", "100"], context="testing", timeout=1
            )
            assert returncode != 0
            assert "timed out" in stderr.lower()

    def test_safe_subprocess_call_permission_denied(self):
        """Test safe subprocess call with permission error."""
        with patch("subprocess.run", side_effect=PermissionError("permission denied")):
            returncode, stdout, stderr = safe_subprocess_call(["restricted"], context="testing")
            assert returncode != 0
            assert "permission" in stderr.lower()


# ============================================================================
# INTEGRATION TESTS (30% - 9 tests)
# ============================================================================


class TestPrerequisiteIntegration:
    """Integration tests for prerequisite checking workflow."""

    def test_full_check_workflow_all_present(self):
        """Test complete prerequisite check when all tools present."""
        checker = PrerequisiteChecker()
        with patch("shutil.which") as mock_which:
            # Simulate all tools being available
            mock_which.side_effect = lambda x: f"/usr/bin/{x}"
            result = checker.check_all_prerequisites()

            assert result.all_available is True
            assert len(result.available_tools) == 5
            assert len(result.missing_tools) == 0

    def test_full_check_workflow_some_missing(self):
        """Test complete prerequisite check with some tools missing."""
        checker = PrerequisiteChecker()
        with patch("shutil.which") as mock_which:
            # node, npm, and claude missing; uv and git present
            mock_which.side_effect = lambda x: (f"/usr/bin/{x}" if x in ["uv", "git"] else None)
            result = checker.check_all_prerequisites()

            assert result.all_available is False
            assert len(result.missing_tools) == 3
            assert any(t.tool == "node" for t in result.missing_tools)
            assert any(t.tool == "npm" for t in result.missing_tools)
            assert any(t.tool == "claude" for t in result.missing_tools)

    def test_format_and_display_missing(self):
        """Test formatting and displaying missing prerequisites."""
        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value=None):
            result = checker.check_all_prerequisites()
            message = checker.format_missing_prerequisites(result.missing_tools)

            # Should contain all missing tools
            assert "node" in message.lower()
            assert "npm" in message.lower()
            assert "uv" in message.lower()
            assert "git" in message.lower()
            assert "claude" in message.lower()

    def test_prerequisite_check_with_real_subprocess(self):
        """Test prerequisite checking with real subprocess calls."""
        checker = PrerequisiteChecker()
        # Use Python as a known-available tool
        result = checker.check_tool("python" + ("3" if sys.platform != "win32" else ""))
        assert result.available is True
        assert result.path is not None

    def test_platform_specific_install_commands(self):
        """Test that platform detection affects install commands."""
        platforms = [
            ("Darwin", Platform.MACOS, "brew"),
            ("Linux", Platform.LINUX, "apt"),
            ("Windows", Platform.WINDOWS, "winget"),
        ]

        for system, expected_platform, expected_cmd in platforms:
            with patch("platform.system", return_value=system), patch(
                "pathlib.Path.exists", return_value=False
            ):
                checker = PrerequisiteChecker()
                assert checker.platform == expected_platform
                install_cmd = checker.get_install_command("git")
                assert expected_cmd in install_cmd.lower()

    def test_error_context_in_subprocess_wrapper(self):
        """Test that subprocess wrapper includes context in errors."""
        with patch("subprocess.run", side_effect=FileNotFoundError("command not found")):
            _, _, stderr = safe_subprocess_call(["missing"], context="launching Claude")
            assert "launching claude" in stderr.lower()

    def test_prerequisite_result_serialization(self):
        """Test that PrerequisiteResult can be serialized for logging."""
        result = PrerequisiteResult(
            all_available=False,
            missing_tools=[ToolCheckResult(tool="git", available=False, error="not found")],
            available_tools=[ToolCheckResult(tool="node", available=True, path="/usr/bin/node")],
        )

        # Should be representable as a dictionary
        result_dict = {
            "all_available": result.all_available,
            "missing_count": len(result.missing_tools),
            "available_count": len(result.available_tools),
        }
        assert result_dict["all_available"] is False
        assert result_dict["missing_count"] == 1

    def test_multiple_prerequisite_checks_consistent(self):
        """Test that multiple prerequisite checks return consistent results."""
        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value="/usr/bin/tool"):
            result1 = checker.check_all_prerequisites()
            result2 = checker.check_all_prerequisites()

            assert result1.all_available == result2.all_available
            assert len(result1.missing_tools) == len(result2.missing_tools)

    def test_prerequisite_check_handles_path_edge_cases(self):
        """Test prerequisite checking handles path edge cases."""
        checker = PrerequisiteChecker()
        with patch("shutil.which") as mock_which:
            # Simulate tool in path with spaces
            mock_which.return_value = "/path with spaces/tool"
            result = checker.check_tool("tool")
            assert result.available is True
            assert result.path == "/path with spaces/tool"


# ============================================================================
# E2E TESTS (10% - 3 tests)
# ============================================================================


class TestEndToEnd:
    """End-to-end tests for complete prerequisite checking workflows."""

    def test_e2e_all_prerequisites_present(self):
        """E2E: Complete workflow when all prerequisites present."""
        checker = PrerequisiteChecker()
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda x: f"/usr/bin/{x}"

            # Full workflow
            result = checker.check_all_prerequisites()
            if not result.all_available:
                message = checker.format_missing_prerequisites(result.missing_tools)
                pytest.fail(f"Should have all prerequisites: {message}")

            assert result.all_available is True

    def test_e2e_missing_prerequisites_with_guidance(self):
        """E2E: Complete workflow with missing prerequisites and user guidance."""
        with patch("platform.system", return_value="Darwin"):
            checker = PrerequisiteChecker()

            with patch("shutil.which", return_value=None):
                # Check prerequisites
                result = checker.check_all_prerequisites()
                assert result.all_available is False

                # Format user-friendly message
                message = checker.format_missing_prerequisites(result.missing_tools)

                # Message should contain:
                # 1. All missing tools
                assert all(
                    tool in message.lower() for tool in ["node", "npm", "uv", "git", "claude"]
                )
                # 2. Installation commands
                assert "brew install" in message
                # 3. Helpful context
                assert "prerequisite" in message.lower()

    def test_e2e_partial_prerequisites_with_specific_guidance(self):
        """E2E: Workflow with some prerequisites missing, specific guidance provided."""
        with patch("platform.system", return_value="Linux"), patch(
            "pathlib.Path.exists", return_value=False
        ):
            checker = PrerequisiteChecker()

            with patch("shutil.which") as mock_which:
                # Only git and uv present
                mock_which.side_effect = lambda x: (f"/usr/bin/{x}" if x in ["git", "uv"] else None)

                result = checker.check_all_prerequisites()
                assert result.all_available is False
                assert len(result.missing_tools) == 3  # node, npm, and claude

                message = checker.format_missing_prerequisites(result.missing_tools)

                # Should only mention missing tools
                assert "node" in message.lower()
                assert "npm" in message.lower()
                assert "claude" in message.lower()
                # Should not mention available tools
                assert message.count("git") <= 1  # May appear in install command
                assert message.count("uv") <= 1  # May appear in install command


# ============================================================================
# DATA STRUCTURE TESTS
# ============================================================================


class TestDataStructures:
    """Tests for data structures used in prerequisites module."""

    def test_tool_check_result_creation(self):
        """Test ToolCheckResult data structure."""
        result = ToolCheckResult(tool="git", available=True, path="/usr/bin/git", version="2.39.0")
        assert result.tool == "git"
        assert result.available is True
        assert result.path == "/usr/bin/git"
        assert result.version == "2.39.0"

    def test_prerequisite_result_creation(self):
        """Test PrerequisiteResult data structure."""
        result = PrerequisiteResult(all_available=True, missing_tools=[], available_tools=[])
        assert result.all_available is True
        assert len(result.missing_tools) == 0

    def test_platform_enum_values(self):
        """Test Platform enum contains expected values."""
        assert hasattr(Platform, "MACOS")
        assert hasattr(Platform, "LINUX")
        assert hasattr(Platform, "WSL")
        assert hasattr(Platform, "WINDOWS")
        assert hasattr(Platform, "UNKNOWN")
