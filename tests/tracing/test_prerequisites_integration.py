"""
Tests for prerequisites integration with native binary detection.

Tests that prerequisites checker properly detects and reports native binary
with trace support status.

This is TDD - tests written before implementation.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from amplihack.launcher.claude_binary_manager import BinaryInfo, ClaudeBinaryManager
from amplihack.utils.prerequisites import PrerequisiteChecker, ToolCheckResult


# =============================================================================
# Native Binary Detection in Prerequisites Tests
# =============================================================================


def test_prerequisites_detects_native_binary():
    """Test that prerequisites checker detects native binary."""
    checker = PrerequisiteChecker()

    with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
        result = checker.check_native_binary()

        assert result.installed is True
        assert result.name == "rustyclawd" or result.name == "native_binary"


def test_prerequisites_reports_no_native_binary():
    """Test that prerequisites reports when no native binary found."""
    checker = PrerequisiteChecker()

    with patch("shutil.which", return_value=None):
        result = checker.check_native_binary()

        assert result.installed is False


def test_prerequisites_reports_binary_version():
    """Test that prerequisites reports native binary version."""
    checker = PrerequisiteChecker()

    with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="rustyclawd 0.1.0", returncode=0)

            result = checker.check_native_binary()

            assert result.version == "0.1.0" or "0.1.0" in str(result)


def test_prerequisites_reports_trace_support():
    """Test that prerequisites reports trace support capability."""
    checker = PrerequisiteChecker()

    with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
        result = checker.check_native_binary()

        # Should indicate trace support (exact API TBD)
        assert hasattr(result, "supports_trace") or "trace" in str(result).lower()


def test_prerequisites_integrates_with_binary_manager():
    """Test that prerequisites uses binary manager for detection."""
    checker = PrerequisiteChecker()
    manager = ClaudeBinaryManager()

    with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
        # Both should detect same binary
        prereq_result = checker.check_native_binary()
        binary_info = manager.detect_native_binary()

        assert prereq_result.installed is True
        assert binary_info is not None
        assert str(binary_info.path) in str(prereq_result.path or prereq_result)


# =============================================================================
# Prerequisite Result Enhancement Tests
# =============================================================================


def test_tool_check_result_includes_trace_capability():
    """Test that ToolCheckResult includes trace capability info."""
    result = ToolCheckResult(
        name="rustyclawd",
        installed=True,
        path="/usr/local/bin/rustyclawd",
        version="0.1.0",
        supports_trace=True,  # New field
    )

    assert result.supports_trace is True


def test_prerequisites_summary_includes_trace_info():
    """Test that prerequisites summary includes trace info."""
    checker = PrerequisiteChecker()

    with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
        result = checker.check_all()

        # Summary should mention trace capability
        summary = str(result)
        assert "trace" in summary.lower() or "rustyclawd" in summary.lower()


# =============================================================================
# Installation Guidance Tests
# =============================================================================


def test_prerequisites_provides_native_binary_installation_guidance():
    """Test that prerequisites provides installation guidance."""
    checker = PrerequisiteChecker()

    with patch("shutil.which", return_value=None):
        result = checker.check_native_binary()

        # Should provide installation guidance
        assert hasattr(result, "installation_guide") or hasattr(result, "message")


def test_prerequisites_explains_trace_benefits():
    """Test that prerequisites explains trace logging benefits."""
    checker = PrerequisiteChecker()

    guidance = checker.get_native_binary_guidance()

    # Should explain trace capability
    assert "trace" in guidance.lower() or "logging" in guidance.lower()


# =============================================================================
# Platform-Specific Detection Tests
# =============================================================================


@pytest.mark.skipif(not hasattr(pytest, "param"), reason="Parametrize test")
@pytest.mark.parametrize(
    "platform,expected_binary",
    [
        ("linux", "rustyclawd"),
        ("darwin", "rustyclawd"),
        ("win32", "rustyclawd.exe"),
    ],
)
def test_prerequisites_detects_platform_specific_binary(platform, expected_binary):
    """Test platform-specific binary detection."""
    checker = PrerequisiteChecker()

    with patch("sys.platform", platform):
        with patch("shutil.which", return_value=f"/usr/local/bin/{expected_binary}"):
            result = checker.check_native_binary()

            assert result.installed is True
            assert expected_binary in str(result.path)


# =============================================================================
# Error Handling Tests
# =============================================================================


def test_prerequisites_handles_binary_detection_errors():
    """Test handling of binary detection errors."""
    checker = PrerequisiteChecker()

    with patch("shutil.which", side_effect=OSError("Permission denied")):
        result = checker.check_native_binary()

        # Should handle gracefully
        assert result.installed is False
        assert "error" in str(result).lower() or "permission" in str(result).lower()


def test_prerequisites_handles_version_check_timeout():
    """Test handling of version check timeout."""
    checker = PrerequisiteChecker()

    with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
        with patch("subprocess.run", side_effect=TimeoutError()):
            result = checker.check_native_binary()

            # Should still report as installed but without version
            assert result.installed is True
            assert result.version is None or result.version == "unknown"


# =============================================================================
# Check All Prerequisites Tests
# =============================================================================


def test_check_all_includes_native_binary():
    """Test that check_all includes native binary check."""
    checker = PrerequisiteChecker()

    with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
        result = checker.check_all()

        # Should include native binary in results
        assert any("rustyclawd" in str(tool).lower() or "native" in str(tool).lower() for tool in result.tools)


def test_check_all_graceful_without_native_binary():
    """Test that check_all is graceful when native binary not found."""
    checker = PrerequisiteChecker()

    with patch("shutil.which", return_value=None):
        result = checker.check_all()

        # Should still complete successfully
        assert result is not None
        # Native binary should be listed as optional


# =============================================================================
# Interactive Installer Integration Tests
# =============================================================================


def test_interactive_installer_offers_native_binary():
    """Test that interactive installer offers to install native binary."""
    from amplihack.utils.prerequisites import InteractiveInstaller

    installer = InteractiveInstaller()

    with patch("builtins.input", return_value="n"):  # User declines
        result = installer.install_native_binary()

        # Should handle user declining
        assert result is not None


def test_interactive_installer_provides_install_instructions():
    """Test that installer provides clear installation instructions."""
    from amplihack.utils.prerequisites import InteractiveInstaller

    installer = InteractiveInstaller()

    instructions = installer.get_native_binary_install_instructions()

    # Should provide clear instructions
    assert "rustyclawd" in instructions.lower() or "install" in instructions.lower()
    assert "cargo" in instructions.lower() or "binary" in instructions.lower()


# =============================================================================
# Fallback Behavior Tests
# =============================================================================


def test_prerequisites_indicates_fallback_to_python():
    """Test that prerequisites indicates fallback to Python implementation."""
    checker = PrerequisiteChecker()

    with patch("shutil.which", return_value=None):
        result = checker.check_native_binary()

        # Should indicate fallback available
        assert "fallback" in str(result).lower() or "python" in str(result).lower()


def test_prerequisites_explains_performance_difference():
    """Test that prerequisites explains performance difference."""
    checker = PrerequisiteChecker()

    guidance = checker.get_native_binary_guidance()

    # Should explain performance benefits
    assert "performance" in guidance.lower() or "faster" in guidance.lower() or "native" in guidance.lower()
