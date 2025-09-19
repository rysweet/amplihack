"""Path resolution utilities."""

from pathlib import Path
from typing import List, Optional


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
