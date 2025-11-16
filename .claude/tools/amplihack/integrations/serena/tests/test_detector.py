"""Unit tests for Serena detector."""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from ..detector import SerenaDetectionResult, SerenaDetector
from ..errors import PlatformNotSupportedError


class TestSerenaDetectionResult:
    """Tests for SerenaDetectionResult dataclass."""

    def test_is_ready_all_requirements_met(self):
        """Test is_ready returns True when all prerequisites are met."""
        result = SerenaDetectionResult(
            uv_available=True,
            uv_path=Path("/usr/bin/uv"),
            serena_available=True,
            serena_path="uvx --from git+https://github.com/oraios/serena serena",
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=True,
        )
        assert result.is_ready() is True

    def test_is_ready_missing_uv(self):
        """Test is_ready returns False when uv is not available."""
        result = SerenaDetectionResult(
            uv_available=False,
            uv_path=None,
            serena_available=True,
            serena_path="uvx --from git+https://github.com/oraios/serena serena",
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=False,
        )
        assert result.is_ready() is False

    def test_is_ready_missing_serena(self):
        """Test is_ready returns False when Serena is not accessible."""
        result = SerenaDetectionResult(
            uv_available=True,
            uv_path=Path("/usr/bin/uv"),
            serena_available=False,
            serena_path=None,
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=False,
        )
        assert result.is_ready() is False

    def test_is_ready_missing_config_path(self):
        """Test is_ready returns False when MCP config path is not found."""
        result = SerenaDetectionResult(
            uv_available=True,
            uv_path=Path("/usr/bin/uv"),
            serena_available=True,
            serena_path="uvx --from git+https://github.com/oraios/serena serena",
            platform="linux",
            mcp_config_path=None,
            config_exists=False,
        )
        assert result.is_ready() is False

    def test_get_status_summary(self):
        """Test get_status_summary generates readable output."""
        result = SerenaDetectionResult(
            uv_available=True,
            uv_path=Path("/usr/bin/uv"),
            serena_available=True,
            serena_path="uvx --from git+https://github.com/oraios/serena serena",
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=True,
        )
        summary = result.get_status_summary()
        assert "Platform: linux" in summary
        assert "uv available: Yes" in summary
        assert "Serena accessible: Yes" in summary
        assert "Config exists: Yes" in summary


class TestSerenaDetector:
    """Tests for SerenaDetector class."""

    def test_detect_uv_available(self):
        """Test detect_uv when uv is in PATH."""
        detector = SerenaDetector()
        with patch("shutil.which", return_value="/usr/bin/uv"):
            available, path = detector.detect_uv()
            assert available is True
            assert path == Path("/usr/bin/uv")

    def test_detect_uv_not_available(self):
        """Test detect_uv when uv is not in PATH."""
        detector = SerenaDetector()
        with patch("shutil.which", return_value=None):
            available, path = detector.detect_uv()
            assert available is False
            assert path is None

    def test_detect_serena_available(self):
        """Test detect_serena when Serena is accessible."""
        detector = SerenaDetector()
        mock_result = Mock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            available, path = detector.detect_serena()
            assert available is True
            assert path == "uvx --from git+https://github.com/oraios/serena serena"

    def test_detect_serena_not_available(self):
        """Test detect_serena when Serena is not accessible."""
        detector = SerenaDetector()
        mock_result = Mock()
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result):
            available, path = detector.detect_serena()
            assert available is False
            assert path is None

    def test_detect_serena_timeout(self):
        """Test detect_serena handles timeout gracefully."""
        detector = SerenaDetector()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            available, path = detector.detect_serena()
            assert available is False
            assert path is None

    def test_detect_serena_file_not_found(self):
        """Test detect_serena handles FileNotFoundError gracefully."""
        detector = SerenaDetector()
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            available, path = detector.detect_serena()
            assert available is False
            assert path is None

    def test_detect_platform_linux(self):
        """Test detect_platform for Linux."""
        detector = SerenaDetector()
        with patch("platform.system", return_value="Linux"):
            with patch.object(detector, "_is_wsl", return_value=False):
                platform_name = detector.detect_platform()
                assert platform_name == "linux"

    def test_detect_platform_wsl(self):
        """Test detect_platform for WSL."""
        detector = SerenaDetector()
        with patch("platform.system", return_value="Linux"):
            with patch.object(detector, "_is_wsl", return_value=True):
                platform_name = detector.detect_platform()
                assert platform_name == "wsl"

    def test_detect_platform_macos(self):
        """Test detect_platform for macOS."""
        detector = SerenaDetector()
        with patch("platform.system", return_value="Darwin"):
            platform_name = detector.detect_platform()
            assert platform_name == "macos"

    def test_detect_platform_windows(self):
        """Test detect_platform for Windows."""
        detector = SerenaDetector()
        with patch("platform.system", return_value="Windows"):
            platform_name = detector.detect_platform()
            assert platform_name == "windows"

    def test_detect_platform_unsupported(self):
        """Test detect_platform raises exception for unsupported platform."""
        detector = SerenaDetector()
        with patch("platform.system", return_value="FreeBSD"):
            with pytest.raises(PlatformNotSupportedError):
                detector.detect_platform()

    def test_is_wsl_true(self):
        """Test _is_wsl returns True when running in WSL."""
        detector = SerenaDetector()
        with patch(
            "builtins.open",
            MagicMock(
                return_value=MagicMock(
                    __enter__=MagicMock(
                        return_value=MagicMock(
                            read=MagicMock(return_value="Linux version 5.10.0-microsoft-standard")
                        )
                    ),
                    __exit__=MagicMock(),
                )
            ),
        ):
            assert detector._is_wsl() is True

    def test_is_wsl_false(self):
        """Test _is_wsl returns False when not running in WSL."""
        detector = SerenaDetector()
        with patch(
            "builtins.open",
            MagicMock(
                return_value=MagicMock(
                    __enter__=MagicMock(
                        return_value=MagicMock(
                            read=MagicMock(return_value="Linux version 5.10.0-generic")
                        )
                    ),
                    __exit__=MagicMock(),
                )
            ),
        ):
            assert detector._is_wsl() is False

    def test_is_wsl_file_not_found(self):
        """Test _is_wsl returns False when /proc/version doesn't exist."""
        detector = SerenaDetector()
        with patch("builtins.open", side_effect=FileNotFoundError()):
            assert detector._is_wsl() is False

    def test_get_mcp_config_path_linux(self):
        """Test get_mcp_config_path returns correct path for Linux."""
        detector = SerenaDetector()
        with patch.object(detector, "detect_platform", return_value="linux"):
            config_path = detector.get_mcp_config_path()
            assert config_path == Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    def test_get_mcp_config_path_macos(self):
        """Test get_mcp_config_path returns correct path for macOS."""
        detector = SerenaDetector()
        with patch.object(detector, "detect_platform", return_value="macos"):
            config_path = detector.get_mcp_config_path()
            assert (
                config_path
                == Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )

    def test_get_mcp_config_path_windows(self):
        """Test get_mcp_config_path returns correct path for Windows."""
        detector = SerenaDetector()
        with patch.object(detector, "detect_platform", return_value="windows"):
            with patch.dict(os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
                config_path = detector.get_mcp_config_path()
                assert (
                    config_path
                    == Path("C:\\Users\\Test\\AppData\\Roaming")
                    / "Claude"
                    / "claude_desktop_config.json"
                )

    def test_get_mcp_config_path_wsl(self):
        """Test get_mcp_config_path uses Linux path for WSL."""
        detector = SerenaDetector()
        with patch.object(detector, "detect_platform", return_value="wsl"):
            config_path = detector.get_mcp_config_path()
            assert config_path == Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    def test_detect_all_success(self):
        """Test detect_all returns complete detection results."""
        detector = SerenaDetector()
        with patch.object(detector, "detect_platform", return_value="linux"):
            with patch.object(detector, "detect_uv", return_value=(True, Path("/usr/bin/uv"))):
                with patch.object(
                    detector,
                    "detect_serena",
                    return_value=(True, "uvx --from git+https://github.com/oraios/serena serena"),
                ):
                    with patch.object(
                        detector,
                        "get_mcp_config_path",
                        return_value=Path("/home/user/.config/Claude/claude_desktop_config.json"),
                    ):
                        with patch("pathlib.Path.exists", return_value=True):
                            result = detector.detect_all()
                            assert result.uv_available is True
                            assert result.serena_available is True
                            assert result.platform == "linux"
                            assert result.config_exists is True
                            assert result.is_ready() is True
