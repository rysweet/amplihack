"""Unit tests for platform compatibility checking.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- Platform detection logic
- Message formatting
- WSL detection
"""

from unittest.mock import patch

from amplihack.launcher.platform_check import (
    PlatformCheckResult,
    check_platform_compatibility,
    is_native_windows,
)


class TestPlatformDetection:
    """Test platform detection logic."""

    def test_detect_native_windows(self):
        """Detect native Windows (not WSL)."""
        with (
            patch("platform.system", return_value="Windows"),
            patch("pathlib.Path.exists", return_value=False),
        ):
            assert is_native_windows() is True

    def test_detect_wsl_via_proc_version(self):
        """Detect WSL via /proc/version containing 'microsoft'."""
        with (
            patch("platform.system", return_value="Windows"),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="Linux version 5.10.0-microsoft-standard"),
        ):
            assert is_native_windows() is False

    def test_detect_wsl_via_wsl_keyword(self):
        """Detect WSL via /proc/version containing 'wsl'."""
        with (
            patch("platform.system", return_value="Windows"),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="Linux version 5.15.0-1-wsl2"),
        ):
            assert is_native_windows() is False

    def test_detect_macos(self):
        """macOS is not native Windows."""
        with patch("platform.system", return_value="Darwin"):
            assert is_native_windows() is False

    def test_detect_linux(self):
        """Linux is not native Windows."""
        with patch("platform.system", return_value="Linux"):
            assert is_native_windows() is False

    def test_handle_proc_version_read_error(self):
        """Handle errors reading /proc/version gracefully."""
        with (
            patch("platform.system", return_value="Windows"),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")),
        ):
            # Should return True (native Windows) when can't confirm WSL
            assert is_native_windows() is True


class TestCompatibilityCheck:
    """Test check_platform_compatibility function."""

    def test_native_windows_incompatible(self):
        """Native Windows is incompatible."""
        with patch("amplihack.launcher.platform_check.is_native_windows", return_value=True):
            result = check_platform_compatibility()
            assert result.compatible is False
            assert result.platform_name == "Windows (native)"
            assert result.is_wsl is False
            assert "WSL" in result.message
            assert "wsl --install" in result.message

    def test_macos_compatible(self):
        """macOS is compatible."""
        with (
            patch("platform.system", return_value="Darwin"),
            patch("amplihack.launcher.platform_check.is_native_windows", return_value=False),
        ):
            result = check_platform_compatibility()
            assert result.compatible is True
            assert result.platform_name == "macOS"
            assert result.is_wsl is False
            assert result.message == ""

    def test_linux_compatible(self):
        """Linux is compatible."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("amplihack.launcher.platform_check.is_native_windows", return_value=False),
            patch("pathlib.Path.exists", return_value=False),
        ):
            result = check_platform_compatibility()
            assert result.compatible is True
            assert result.platform_name == "Linux"
            assert result.is_wsl is False
            assert result.message == ""

    def test_wsl_compatible(self):
        """WSL is compatible."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("amplihack.launcher.platform_check.is_native_windows", return_value=False),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="Linux version 5.10.0-microsoft-standard"),
        ):
            result = check_platform_compatibility()
            assert result.compatible is True
            assert result.platform_name == "Linux (WSL)"
            assert result.is_wsl is True
            assert result.message == ""


class TestMessageContent:
    """Test error message content and formatting."""

    def test_windows_message_contains_install_instructions(self):
        """Windows error message includes WSL installation instructions."""
        with patch("amplihack.launcher.platform_check.is_native_windows", return_value=True):
            result = check_platform_compatibility()
            assert "wsl --install" in result.message
            assert "PowerShell" in result.message
            assert "Administrator" in result.message

    def test_windows_message_contains_documentation_link(self):
        """Windows error message includes Microsoft documentation link."""
        with patch("amplihack.launcher.platform_check.is_native_windows", return_value=True):
            result = check_platform_compatibility()
            assert "https://learn.microsoft.com/en-us/windows/wsl/install" in result.message

    def test_windows_message_explains_requirement(self):
        """Windows error message explains Unix requirement."""
        with patch("amplihack.launcher.platform_check.is_native_windows", return_value=True):
            result = check_platform_compatibility()
            assert (
                "Unix-like environment" in result.message or "amplihack requires" in result.message
            )


class TestDataClass:
    """Test PlatformCheckResult data class."""

    def test_result_structure(self):
        """PlatformCheckResult has expected fields."""
        result = PlatformCheckResult(
            compatible=True, platform_name="Linux", is_wsl=False, message=""
        )
        assert result.compatible is True
        assert result.platform_name == "Linux"
        assert result.is_wsl is False
        assert result.message == ""

    def test_result_default_message(self):
        """Message field defaults to empty string."""
        result = PlatformCheckResult(compatible=True, platform_name="macOS", is_wsl=False)
        assert result.message == ""
