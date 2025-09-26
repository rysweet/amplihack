"""Detection of .claude directories in project hierarchy."""

from pathlib import Path
from typing import Optional


class ClaudeDirectoryDetector:
    """Detects .claude directories in project hierarchy."""

    def __init__(self):
        """Initialize detector with caching support."""
        self._cache = {}

    def find_claude_directory(self, start_path: Optional[Path] = None) -> Optional[Path]:
        """Find .claude directory in current or parent directories with caching.

        Args:
            start_path: Starting directory for search. Defaults to current directory.

        Returns:
            Path to .claude directory if found, None otherwise.
        """
        if start_path is None:
            start_path = Path.cwd()

        # Use start path as cache key
        cache_key = str(start_path.resolve())
        if cache_key in self._cache:
            return self._cache[cache_key]

        current = Path(start_path).resolve()

        # Check current and all parent directories
        while current != current.parent:
            claude_dir = current / ".claude"
            if claude_dir.exists() and claude_dir.is_dir():
                self._cache[cache_key] = claude_dir
                return claude_dir
            current = current.parent

        # Check root directory
        claude_dir = current / ".claude"
        result = claude_dir if (claude_dir.exists() and claude_dir.is_dir()) else None
        self._cache[cache_key] = result
        return result

    def has_claude_directory(self, path: Optional[Path] = None) -> bool:
        """Check if a .claude directory exists in the hierarchy.

        Args:
            path: Starting directory for search. Defaults to current directory.

        Returns:
            True if .claude directory found, False otherwise.
        """
        return self.find_claude_directory(path) is not None

    @staticmethod
    def get_project_root(claude_dir: Path) -> Path:
        """Get the project root directory containing the .claude directory.

        Args:
            claude_dir: Path to .claude directory.

        Returns:
            Path to project root directory.
        """
        return claude_dir.parent
