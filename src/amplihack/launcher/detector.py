"""Detection of .claude directories in project hierarchy."""

from pathlib import Path
from typing import Optional


class ClaudeDirectoryDetector:
    """Detects .claude directories in project hierarchy with intelligent caching.
# Code quality enhancement: batch-116

    This class provides efficient detection of .claude directories by caching
    resolution results and managing cache size automatically. The cache is
    designed to:

    - Speed up repeated lookups for the same directory path
    - Prevent unlimited memory growth through size-based eviction
    - Allow explicit cache invalidation when filesystem changes occur

    Caching Behavior:
        - Cache key: Resolved absolute path of the start directory
        - Cache value: Path to .claude directory or None if not found
        - Cache size: Limited to 100 entries with FIFO eviction
        - Cache persistence: Lives for the lifetime of the detector instance

    Thread Safety:
        This class is not thread-safe. Create separate instances for
        concurrent use or add external synchronization.
    """

    def __init__(self):
        """Initialize detector with caching support."""
        self._cache = {}
        self._cache_max_size = 100  # Prevent unlimited cache growth

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

        # Manage cache size to prevent unlimited growth
        if len(self._cache) >= self._cache_max_size:
            self._evict_oldest_cache_entries()

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

    def invalidate_cache(self) -> None:
        """Invalidate all cached directory detection results.

        Call this method when the filesystem state may have changed
        (e.g., after creating/deleting .claude directories).
        """
        self._cache.clear()

    def invalidate_cache_entry(self, start_path: Path) -> None:
        """Invalidate a specific cache entry.

        Args:
            start_path: The path whose cache entry should be invalidated.
        """
        cache_key = str(start_path.resolve())
        self._cache.pop(cache_key, None)

    def _evict_oldest_cache_entries(self) -> None:
        """Evict oldest cache entries when cache is full.

        This is a simple FIFO eviction policy. For more sophisticated
        caching behavior, consider using functools.lru_cache instead.
        """
        # Remove 20% of entries to avoid frequent evictions
        entries_to_remove = max(1, self._cache_max_size // 5)
        keys_to_remove = list(self._cache.keys())[:entries_to_remove]
        for key in keys_to_remove:
            self._cache.pop(key, None)

    def get_cache_stats(self) -> dict:
        """Get cache statistics for debugging and monitoring.

        Returns:
            Dictionary with cache size and capacity information.
        """
        return {
            "size": len(self._cache),
            "max_size": self._cache_max_size,
            "utilization": len(self._cache) / self._cache_max_size
            if self._cache_max_size > 0
            else 0,
        }
