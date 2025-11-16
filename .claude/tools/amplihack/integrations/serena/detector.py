"""Prerequisite detection for Serena MCP integration.

This module detects system prerequisites and configuration paths
for the Serena MCP server integration.
"""

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from .errors import PlatformNotSupportedError


@dataclass
class SerenaDetectionResult:
    """Results from detecting Serena prerequisites.

    Attributes:
        uv_available: Whether uv is installed and in PATH
        uv_path: Path to uv executable (if available)
        serena_available: Whether Serena is accessible via uvx
        serena_path: Conceptual path (always uvx invocation, not a real path)
        platform: Detected platform (linux/macos/windows/wsl)
        mcp_config_path: Path to Claude Desktop MCP configuration file
        config_exists: Whether the MCP config file already exists
    """

    uv_available: bool
    uv_path: Optional[Path]
    serena_available: bool
    serena_path: Optional[str]
    platform: str
    mcp_config_path: Optional[Path]
    config_exists: bool

    def is_ready(self) -> bool:
        """Check if all prerequisites are met for Serena integration.

        Returns:
            True if uv is available, Serena is accessible, and MCP config path is known
        """
        return self.uv_available and self.serena_available and self.mcp_config_path is not None

    def get_status_summary(self) -> str:
        """Generate a human-readable status summary.

        Returns:
            Multi-line string with status of all prerequisites
        """
        lines = [
            f"Platform: {self.platform}",
            f"uv available: {'Yes' if self.uv_available else 'No'}",
        ]
        if self.uv_path:
            lines.append(f"uv path: {self.uv_path}")
        lines.append(f"Serena accessible: {'Yes' if self.serena_available else 'No'}")
        if self.mcp_config_path:
            lines.append(f"MCP config path: {self.mcp_config_path}")
            lines.append(f"Config exists: {'Yes' if self.config_exists else 'No'}")
        else:
            lines.append("MCP config path: Not found")
        return "\n".join(lines)


class SerenaDetector:
    """Detects prerequisites and configuration for Serena MCP integration."""

    # Platform-specific MCP configuration paths
    MCP_CONFIG_PATHS = {
        "linux": Path.home() / ".config" / "Claude" / "claude_desktop_config.json",
        "macos": Path.home()
        / "Library"
        / "Application Support"
        / "Claude"
        / "claude_desktop_config.json",
        "windows": Path(os.getenv("APPDATA", "")) / "Claude" / "claude_desktop_config.json",
    }

    def detect_all(self) -> SerenaDetectionResult:
        """Perform complete detection of all prerequisites.

        Returns:
            SerenaDetectionResult with all detection results
        """
        detected_platform = self.detect_platform()
        uv_available, uv_path = self.detect_uv()
        serena_available, serena_path = self.detect_serena()
        mcp_config_path = self.get_mcp_config_path()
        config_exists = mcp_config_path.exists() if mcp_config_path else False

        return SerenaDetectionResult(
            uv_available=uv_available,
            uv_path=uv_path,
            serena_available=serena_available,
            serena_path=serena_path,
            platform=detected_platform,
            mcp_config_path=mcp_config_path,
            config_exists=config_exists,
        )

    def detect_uv(self) -> Tuple[bool, Optional[Path]]:
        """Detect if uv is installed and available in PATH.

        Returns:
            Tuple of (is_available, path_to_uv)
        """
        uv_path = shutil.which("uv")
        if uv_path:
            return True, Path(uv_path)
        return False, None

    def detect_serena(self) -> Tuple[bool, Optional[str]]:
        """Detect if Serena is accessible via uvx.

        Returns:
            Tuple of (is_available, invocation_string)
        """
        try:
            result = subprocess.run(
                [
                    "uvx",
                    "--from",
                    "git+https://github.com/oraios/serena",
                    "serena",
                    "--help",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0:
                return True, "uvx --from git+https://github.com/oraios/serena serena"
            return False, None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False, None

    def detect_platform(self) -> str:
        """Detect the current platform.

        Returns:
            Platform identifier: 'linux', 'macos', 'windows', or 'wsl'

        Raises:
            PlatformNotSupportedError: If platform cannot be determined
        """
        system = platform.system().lower()

        # Check for WSL (Windows Subsystem for Linux)
        if system == "linux" and self._is_wsl():
            return "wsl"

        # Map platform names
        platform_map = {
            "linux": "linux",
            "darwin": "macos",
            "windows": "windows",
        }

        detected = platform_map.get(system)
        if detected:
            return detected

        raise PlatformNotSupportedError(system)

    def _is_wsl(self) -> bool:
        """Check if running under Windows Subsystem for Linux.

        Returns:
            True if running in WSL, False otherwise
        """
        try:
            with open("/proc/version") as f:
                version_info = f.read().lower()
                return "microsoft" in version_info or "wsl" in version_info
        except (FileNotFoundError, PermissionError, OSError):
            return False

    def get_mcp_config_path(self) -> Optional[Path]:
        """Get the MCP configuration file path for the current platform.

        Returns:
            Path to claude_desktop_config.json, or None if cannot be determined
        """
        detected_platform = self.detect_platform()

        # For WSL, use Linux path (config is in the Linux filesystem)
        lookup_platform = "linux" if detected_platform == "wsl" else detected_platform

        config_path = self.MCP_CONFIG_PATHS.get(lookup_platform)
        return config_path
