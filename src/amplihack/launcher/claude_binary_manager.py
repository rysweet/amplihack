"""
ClaudeBinaryManager - Native binary detection and command building.

Philosophy:
- Single responsibility: Detect and configure native Claude binaries
- Zero-BS: Working detection and command building, no stubs
- Self-contained: No external dependencies
- Performance: Caching for repeated operations

Public API:
    ClaudeBinaryManager: Main manager class
    BinaryInfo: Binary information dataclass

Created for Issue #2071: Native Binary Migration with Optional Trace Logging
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from ..tracing.trace_logger import DEFAULT_TRACE_FILE


@dataclass
class BinaryInfo:
    """
    Information about a detected Claude binary.

    Attributes:
        name: Binary name (e.g., "rustyclawd", "claude")
        path: Full path to the binary
        version: Version string (optional)
        supports_trace: Whether the binary supports trace logging
    """

    name: str
    path: Path
    version: str | None = None
    supports_trace: bool = False


class ClaudeBinaryManager:
    """
    Manages detection and configuration of native Claude binaries.

    Features:
    - Auto-detection of rustyclawd and claude-cli
    - Version detection
    - Trace support detection
    - Command building with trace flags
    - Caching for performance

    Binary Priority:
    1. CLAUDE_BINARY_PATH environment variable
    2. rustyclawd (Rust implementation, preferred)
    3. claude (official CLI)

    Usage:
        >>> manager = ClaudeBinaryManager()
        >>> binary = manager.detect_native_binary()
        >>> if binary:
        ...     cmd = manager.build_command(binary, enable_trace=True)
    """

    # Binary names to search for (in priority order)
    BINARY_NAMES: ClassVar[list[str]] = ["rustyclawd", "claude"]

    # Binaries known to support trace logging
    TRACE_SUPPORTED_BINARIES: ClassVar[set[str]] = {"rustyclawd"}

    def __init__(self):
        """Initialize the binary manager."""
        # Cache for detected binary to avoid repeated detection
        self._cached_binary: BinaryInfo | None = None
        self._cache_valid = False

    def detect_native_binary(self) -> BinaryInfo | None:
        """
        Detect available native Claude binary.

        Search Order:
        1. CLAUDE_BINARY_PATH environment variable
        2. rustyclawd (Rust implementation)
        3. claude (official CLI)

        Returns:
            BinaryInfo if a valid binary is found, None otherwise
        """
        # Return cached result if available
        if self._cache_valid:
            return self._cached_binary

        # Check environment variable first
        env_path = os.getenv("CLAUDE_BINARY_PATH")
        if env_path:
            binary = self._validate_binary_path(Path(env_path))
            if binary:
                self._cached_binary = binary
                self._cache_valid = True
                return binary

        # Search for binaries in priority order
        for binary_name in self.BINARY_NAMES:
            path_str = shutil.which(binary_name)
            if path_str:
                path = Path(path_str)
                # shutil.which guarantees existence and executability in production
                # But we still validate to support test mocking scenarios
                # Only create BinaryInfo if path actually exists (handles test mocks)
                if path.exists() and os.access(path, os.X_OK):
                    binary = self._create_binary_info(path)
                    self._cached_binary = binary
                    self._cache_valid = True
                    return binary
                # If validation fails, continue to next binary
                continue

        # No binary found
        self._cached_binary = None
        self._cache_valid = True
        return None

    def _validate_binary_path(
        self, path: Path, check_exists: bool = True, check_executable: bool = True
    ) -> BinaryInfo | None:
        """
        Validate that a path points to a valid executable binary.

        Args:
            path: Path to validate
            check_exists: Whether to check if path exists
            check_executable: Whether to check if path is executable

        Returns:
            BinaryInfo if valid, None otherwise
        """
        # Always do basic validation to catch test mocking scenarios
        # Check existence if requested (primarily for env var paths)
        if check_exists:
            try:
                if not path.exists():
                    return None
            except (OSError, RuntimeError):
                # Path validation failed (e.g., broken symlink, permission error)
                return None

        # Check if executable (also ensures it's a file, not a directory)
        if check_executable:
            try:
                if not os.access(path, os.X_OK):
                    return None
            except (OSError, ValueError):
                # Access check failed
                return None

        return self._create_binary_info(path)

    def _create_binary_info(self, path: Path) -> BinaryInfo:
        """
        Create BinaryInfo from a path without validation.

        Args:
            path: Path to binary

        Returns:
            BinaryInfo instance
        """
        # Extract binary name
        binary_name = path.stem

        # Determine if it supports trace
        supports_trace = binary_name in self.TRACE_SUPPORTED_BINARIES

        # Detect version (optional, don't fail if it fails)
        version = None
        try:
            version = self.detect_version(BinaryInfo(name=binary_name, path=path))
        except Exception:
            # Version detection is optional, don't fail
            pass

        return BinaryInfo(
            name=binary_name,
            path=path,
            version=version,
            supports_trace=supports_trace,
        )

    def detect_version(self, binary: BinaryInfo) -> str | None:
        """
        Detect the version of a binary.

        Args:
            binary: Binary to check version for

        Returns:
            Version string if detected, None otherwise
        """
        try:
            # Try --version flag
            result = subprocess.run(
                [str(binary.path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode == 0 and result.stdout:
                return self._parse_version(result.stdout)

        except (subprocess.SubprocessError, OSError):
            pass

        return None

    def _parse_version(self, version_output: str) -> str | None:
        """
        Parse version string from various output formats.

        Args:
            version_output: Raw version output from binary

        Returns:
            Parsed version string or None
        """
        # Try various version patterns
        patterns = [
            r"(\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)",  # Standard semver
            r"v(\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)",  # With 'v' prefix
            r"version[:\s]+(\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)",  # "version: X.Y.Z"
        ]

        for pattern in patterns:
            match = re.search(pattern, version_output, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def build_command(
        self,
        binary: BinaryInfo,
        enable_trace: bool = False,
        trace_file: str | None = None,
        additional_args: list[str] | None = None,
    ) -> list[str]:
        """
        Build command line for launching Claude binary.

        Args:
            binary: Binary information
            enable_trace: Whether to enable trace logging
            trace_file: Path to trace log file (required if enable_trace=True)
            additional_args: Additional arguments to pass to binary

        Returns:
            Command line as list of strings

        Raises:
            ValueError: If trace_file contains null bytes
        """
        # Validate trace file path if provided
        if trace_file and "\0" in trace_file:
            raise ValueError("Invalid trace file path: contains null bytes")

        # Start with binary path
        cmd = [str(binary.path)]

        # Add trace flags if enabled and supported
        if enable_trace and binary.supports_trace:
            if trace_file:
                # Add trace logging flags
                cmd.extend(["--log-file", trace_file])
            # If trace_file is None but tracing is enabled, use default location
            else:
                cmd.extend(["--log-file", str(DEFAULT_TRACE_FILE)])

        # Add additional arguments
        if additional_args:
            cmd.extend(additional_args)

        return cmd

    def invalidate_cache(self) -> None:
        """Invalidate the binary detection cache."""
        self._cache_valid = False
        self._cached_binary = None


__all__ = ["ClaudeBinaryManager", "BinaryInfo"]
