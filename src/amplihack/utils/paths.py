"""Path resolution utilities."""

import os
import sys
from pathlib import Path
from typing import List, Optional


class FrameworkPathResolver:
    """Resolves framework file paths for both local and UVX deployments."""

    @staticmethod
    def find_framework_root() -> Optional[Path]:
        """Find the framework root directory.

        Returns:
            Path to framework root if found, None otherwise.
        """
        # Strategy 1: Check current working directory and parents (local deployment)
        current = Path.cwd()
        while current != current.parent:
            if (current / ".claude").exists():
                return current
            current = current.parent

        # Strategy 2: Check environment variable (UVX deployment)
        if "AMPLIHACK_ROOT" in os.environ:
            env_path = Path(os.environ["AMPLIHACK_ROOT"])
            if env_path.exists() and (env_path / ".claude").exists():
                return env_path

        # Strategy 3: If UVX deployment detected, attempt staging
        if FrameworkPathResolver.is_uvx_deployment():
            try:
                # Import here to avoid circular imports
                from .uvx_staging import stage_uvx_framework

                # Attempt to stage framework files
                if stage_uvx_framework():
                    # Check if staging worked
                    if (Path.cwd() / ".claude").exists():
                        return Path.cwd()
            except ImportError:
                pass  # uvx_staging not available

        return None

    @staticmethod
    def resolve_framework_file(relative_path: str) -> Optional[Path]:
        """Resolve a framework file path relative to framework root.

        Args:
            relative_path: Path relative to framework root (e.g., ".claude/context/USER_PREFERENCES.md")

        Returns:
            Absolute path to file if found, None otherwise.
        """
        framework_root = FrameworkPathResolver.find_framework_root()
        if not framework_root:
            return None

        file_path = framework_root / relative_path
        return file_path if file_path.exists() else None

    @staticmethod
    def resolve_preferences_file() -> Optional[Path]:
        """Convenience method to find USER_PREFERENCES.md file.

        Returns:
            Path to USER_PREFERENCES.md if found, None otherwise.
        """
        return FrameworkPathResolver.resolve_framework_file(".claude/context/USER_PREFERENCES.md")

    @staticmethod
    def resolve_workflow_file() -> Optional[Path]:
        """Convenience method to find DEFAULT_WORKFLOW.md file.

        Returns:
            Path to DEFAULT_WORKFLOW.md if found, None otherwise.
        """
        return FrameworkPathResolver.resolve_framework_file(".claude/workflow/DEFAULT_WORKFLOW.md")

    @staticmethod
    def is_uvx_deployment() -> bool:
        """Check if running in UVX deployment.

        Returns:
            True if likely running in UVX, False otherwise.
        """
        # Try using the more comprehensive UVX staging detection
        try:
            from .uvx_staging import is_uvx_deployment

            return is_uvx_deployment()
        except ImportError:
            # Fallback to original logic
            return (
                "UV_PYTHON" in os.environ
                or any("uv" in path for path in sys.path)
                or not (Path.cwd() / ".claude").exists()
            )


class PathResolver:
    """Utilities for resolving and manipulating paths."""

    @staticmethod
    def resolve_path(path_str: str) -> Path:
        """Resolve a path string to absolute Path object.

        Args:
            path_str: Path string (can be relative or with ~ for home).

        Returns:
            Resolved absolute Path object.
        """
        path = Path(path_str).expanduser()
        return path.resolve()

    @staticmethod
    def find_file_upward(filename: str, start_path: Optional[Path] = None) -> Optional[Path]:
        """Find a file by searching upward from start path.

        Args:
            filename: Name of file to find.
            start_path: Starting directory. Defaults to current directory.

        Returns:
            Path to file if found, None otherwise.
        """
        if start_path is None:
            start_path = Path.cwd()

        current = Path(start_path).resolve()

        while current != current.parent:
            target = current / filename
            if target.exists() and target.is_file():
                return target
            current = current.parent

        # Check root directory
        target = current / filename
        if target.exists() and target.is_file():
            return target

        return None

    @staticmethod
    def find_directory_upward(dirname: str, start_path: Optional[Path] = None) -> Optional[Path]:
        """Find a directory by searching upward from start path.

        Args:
            dirname: Name of directory to find.
            start_path: Starting directory. Defaults to current directory.

        Returns:
            Path to directory if found, None otherwise.
        """
        if start_path is None:
            start_path = Path.cwd()

        current = Path(start_path).resolve()

        while current != current.parent:
            target = current / dirname
            if target.exists() and target.is_dir():
                return target
            current = current.parent

        # Check root directory
        target = current / dirname
        if target.exists() and target.is_dir():
            return target

        return None

    @staticmethod
    def ensure_directory(path: Path) -> Path:
        """Ensure a directory exists, creating it if necessary.

        Args:
            path: Path to directory.

        Returns:
            Path object for the directory.
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def get_relative_path(path: Path, base: Optional[Path] = None) -> Path:
        """Get relative path from base directory.

        Args:
            path: Path to make relative.
            base: Base directory. Defaults to current directory.

        Returns:
            Relative path from base.
        """
        if base is None:
            base = Path.cwd()

        try:
            return path.relative_to(base)
        except ValueError:
            # Paths don't share a common base
            return path

    @staticmethod
    def list_files(directory: Path, pattern: str = "*", recursive: bool = False) -> List[Path]:
        """List files in a directory matching pattern.

        Args:
            directory: Directory to search.
            pattern: Glob pattern for matching files.
            recursive: Whether to search recursively.

        Returns:
            List of matching file paths.
        """
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            return []

        if recursive:
            pattern = "**/" + pattern
            return list(directory.glob(pattern))
        else:
            return list(directory.glob(pattern))
