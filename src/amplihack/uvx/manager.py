"""UVX manager for handling --add-dir integration with Claude Code.

This module provides the UVXManager class that:
1. Detects UVX environments using comprehensive checks
2. Resolves framework paths for --add-dir arguments
3. Integrates with launcher to add --add-dir arguments
4. Provides environment variables for session hooks
"""

import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional

from ..utils.uvx_detection import detect_uvx_deployment, resolve_framework_paths
from ..utils.uvx_models import (
    PathResolutionResult,
    UVXConfiguration,
    UVXDetectionState,
)

logger = logging.getLogger(__name__)


class UVXManager:
    """Manages UVX environment detection and Claude command enhancement."""

    def __init__(self, force_staging: bool = False) -> None:
        """Initialize UVX manager.

        Args:
            force_staging: If True, always use staging approach instead of --add-dir
        """
        self.force_staging = force_staging
        self._config = UVXConfiguration()
        self._detection_state: Optional[UVXDetectionState] = None
        self._path_resolution: Optional[PathResolutionResult] = None
        self._lock = threading.RLock()  # Reentrant lock for thread safety

    def _ensure_detection(self) -> None:
        """Ensure detection has been performed (thread-safe)."""
        with self._lock:
            if self._detection_state is None:
                self._detection_state = detect_uvx_deployment(self._config)
                logger.debug(f"UVX detection result: {self._detection_state.result.name}")
                for reason in self._detection_state.detection_reasons:
                    logger.debug(f"  - {reason}")

    def _ensure_path_resolution(self) -> None:
        """Ensure path resolution has been performed."""
        self._ensure_detection()
        if self._path_resolution is None and self._detection_state:
            self._path_resolution = resolve_framework_paths(self._detection_state, self._config)
            if self._path_resolution.is_successful and self._path_resolution.location:
                logger.debug(f"Framework path resolved: {self._path_resolution.location.root_path}")
            else:
                logger.debug("Framework path resolution failed")
                for attempt in self._path_resolution.attempts:
                    logger.debug(f"  - {attempt['strategy']}: {attempt['notes']}")

    def is_uvx_environment(self) -> bool:
        """Detect if we're running in a UVX environment.

        Returns:
            True if UVX environment detected, False otherwise
        """
        self._ensure_detection()
        return self._detection_state.is_uvx_deployment if self._detection_state else False

    def get_framework_path(self) -> Optional[Path]:
        """Get the framework root path.

        Returns:
            Path to framework root, or None if not resolvable
        """
        self._ensure_path_resolution()
        if (
            self._path_resolution
            and self._path_resolution.is_successful
            and self._path_resolution.location
        ):
            return self._path_resolution.location.root_path
        return None

    def should_use_add_dir(self) -> bool:
        """Determine if --add-dir should be used.

        Returns:
            True if --add-dir should be used, False otherwise
        """
        if self.force_staging:
            logger.debug(
                "UVX --add-dir disabled: force_staging=True (user requested staging mode explicitly)"
            )
            return False

        if not self.is_uvx_environment():
            logger.debug(
                "UVX --add-dir disabled: not running in UVX environment "
                "(AMPLIHACK_IN_UVX not set or detection failed)"
            )
            return False

        framework_path = self.get_framework_path()
        if not framework_path:
            logger.debug(
                "UVX --add-dir disabled: framework path not found "
                "(path resolution failed or framework not installed)"
            )
            return False

        # Check if path is safe
        if not self.validate_path_security(framework_path):
            logger.warning(
                f"UVX --add-dir disabled: path failed security validation "
                f"(path='{framework_path}', may be outside safe directories or contain symlinks)"
            )
            return False

        logger.debug(
            f"UVX --add-dir enabled: framework_path='{framework_path}' "
            f"(validated and safe to use)"
        )
        return True

    def should_use_staging(self) -> bool:
        """Determine if staging approach should be used.

        Returns:
            True if staging should be used, False otherwise
        """
        if self.force_staging:
            return True

        self._ensure_path_resolution()
        if self._path_resolution and self._path_resolution.requires_staging:
            return True

        # If we're in UVX but can't use --add-dir, we need staging
        if self.is_uvx_environment() and not self.should_use_add_dir():
            return True

        return False

    def get_add_dir_args(self) -> List[str]:
        """Get --add-dir arguments for Claude command.

        Returns:
            List of command arguments, empty if not applicable
        """
        if not self.should_use_add_dir():
            return []

        framework_path = self.get_framework_path()
        if not framework_path:
            return []

        # Return the --add-dir argument with the framework path
        return ["--add-dir", str(framework_path)]

    def validate_path_security(self, path: Optional[Path]) -> bool:
        """Validate that a path is safe (no directory traversal).

        Args:
            path: The path to validate

        Returns:
            True if path is safe, False otherwise
        """
        if path is None:
            return False

        try:
            # Convert to absolute path for validation
            abs_path = path.resolve()
            path_str = str(abs_path)

            # Check for path traversal in the original path string
            # We check the original path (not resolved) to catch obvious traversal attempts
            original_str = str(path)

            # Check for obvious traversal patterns (multiple ../ in sequence)
            # This catches "../../../etc" patterns while allowing legitimate paths
            # like "/usr/local/my..app/" that happen to contain ".."
            if "/../" in original_str or original_str.startswith("../"):
                logger.warning(f"Path contains directory traversal pattern: {path}")
                return False

            # Check for null bytes (path injection)
            if "\x00" in path_str:
                logger.warning(f"Path contains null bytes: {path}")
                return False

            # Reject sensitive system directories
            # Note: On macOS, Path.resolve() may add /System/Volumes/Data prefix
            # So we need to check the actual path components
            suspicious_prefixes = [
                "/etc",
                "/private/etc",
                "/root",
                "/private/root",
                "/sys",
                "/proc",
                "/dev",
                "/boot",
                "/usr/bin",
                "/usr/sbin",
                "/bin",
                "/sbin",
                "/var/root",  # macOS root home
                "/System/Library",  # macOS system files (but not /System/Volumes/Data)
                "/Library/Security",  # macOS security
            ]

            # Remove macOS data volume prefix if present for checking
            check_path = path_str
            if check_path.startswith("/System/Volumes/Data"):
                check_path = check_path[len("/System/Volumes/Data") :]

            for prefix in suspicious_prefixes:
                if check_path == prefix or check_path.startswith(prefix + "/"):
                    logger.warning(f"Path targets system directory: {abs_path}")
                    return False

            logger.debug(f"Path validation passed: {path}")
            return True

        except (OSError, ValueError) as e:
            logger.error(f"Path validation error: {e}")
            return False

    def enhance_claude_command(self, base_command: List[str]) -> List[str]:
        """Enhance Claude command with --add-dir parameter if appropriate.

        Args:
            base_command: Original Claude command

        Returns:
            Enhanced command with --add-dir if appropriate
        """
        add_dir_args = self.get_add_dir_args()
        if not add_dir_args:
            return base_command

        # Create enhanced command
        enhanced = base_command.copy()
        enhanced.extend(add_dir_args)

        logger.info(f"Enhanced command with --add-dir: {' '.join(enhanced)}")
        return enhanced

    def get_detection_state(self) -> UVXDetectionState:
        """Get the current UVX detection state.

        Returns:
            UVXDetectionState with detection results
        """
        self._ensure_detection()
        assert self._detection_state is not None, (
            "Detection state should be set after _ensure_detection()"
        )
        return self._detection_state

    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables to set for UVX mode.

        Returns:
            Dictionary of environment variables
        """
        env_vars = {}

        # Only set environment variables if we have a valid framework path
        framework_path = self.get_framework_path()
        if framework_path:
            env_vars["AMPLIHACK_PROJECT_ROOT"] = str(framework_path)
            logger.debug(f"Set AMPLIHACK_PROJECT_ROOT={framework_path}")

        return env_vars
