"""Unit tests for platform compatibility checking.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- Platform detection logic (sys.platform based)
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
    """Test platform detection logic.

    is_native_windows() uses sys.platform (not platform.system or /proc/version).
    On native Windows Python: sys.platform == "win32".
    On WSL Python: sys.platform == "linux".
    """

    def test_detect_native_windows(self):
        """Detect native Windows via sys.platform == 'win32'."""
        with patch("amplihack.launcher.platform_check.sys") as mock_sys:
            mock_sys.platform = "win32"
            assert is_native_windows() is True

    def test_detect_linux_not_windows(self):
        """Linux (including WSL) returns False — sys.platform is 'linux'."""
        with patch("amplihack.launcher.platform_check.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert is_native_windows() is False

    def test_detect_macos_not_windows(self):
        """macOS returns False — sys.platform is 'darwin'."""
        with patch("amplihack.launcher.platform_check.sys") as mock_sys:
            mock_sys.platform = "darwin"
            assert is_native_windows() is False

    def test_wsl_not_detected_as_native_windows(self):
        """WSL Python has sys.platform == 'linux', not 'win32'."""
        with patch("amplihack.launcher.platform_check.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert is_native_windows() is False


class TestCompatibilityCheck:
    """Test check_platform_compatibility function."""

    def test_native_windows_partial_support(self):
        """Native Windows returns compatible=True with warning message."""
        with patch("amplihack.launcher.platform_check.is_native_windows", return_value=True):
            result = check_platform_compatibility()
            assert result.compatible is True
            assert result.platform_name == "Windows (native, partial)"
            assert result.is_wsl is False
            assert result.message != ""
            assert "partial support" in result.message

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
    """Test warning message content for partial Windows support."""

    def test_windows_message_mentions_fleet_limitation(self):
        """Windows warning mentions fleet is unavailable."""
        with patch("amplihack.launcher.platform_check.is_native_windows", return_value=True):
            result = check_platform_compatibility()
            assert "fleet" in result.message.lower()

    def test_windows_message_contains_documentation_link(self):
        """Windows warning includes WSL documentation link."""
        with patch("amplihack.launcher.platform_check.is_native_windows", return_value=True):
            result = check_platform_compatibility()
            assert "https://learn.microsoft.com/en-us/windows/wsl/install" in result.message

    def test_windows_message_mentions_arm64_kuzu(self):
        """Windows warning mentions ARM64 kuzu workaround."""
        with patch("amplihack.launcher.platform_check.is_native_windows", return_value=True):
            result = check_platform_compatibility()
            assert "ARM64" in result.message
            assert "kuzu" in result.message


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
