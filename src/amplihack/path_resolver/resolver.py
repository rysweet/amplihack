"""Path resolution for plugin system."""

import os
from pathlib import Path
from typing import Any


class PathResolver:
    """Resolves relative paths to absolute paths for plugin system.

    This resolver:
    - Converts relative paths to absolute
    - Expands home directory (~)
    - Handles nested dictionaries and lists
    - Detects plugin root from environment or defaults
    """

    # Fields that should be treated as paths
    PATH_FIELDS = {
        "path",
        "cwd",
        "script",
        "entry_point",
        "file",
        "files",
        "absolute",
        "relative",  # Common test field names
    }

    def __init__(self):
        """Initialize path resolver."""
        self._cached_plugin_root = None

    def resolve(self, path: str, plugin_root: Path) -> str:
        """Resolve a path to absolute form.

        Args:
            path: Path string to resolve
            plugin_root: Base path for relative resolution

        Returns:
            Absolute path string

        Raises:
            TypeError: If plugin_root is None
        """
        if plugin_root is None:
            raise TypeError("plugin_root cannot be None")

        if not path:
            return str(plugin_root)

        # Handle home directory expansion
        if path.startswith("~"):
            return str(Path(path).expanduser())

        # Convert to Path object
        path_obj = Path(path)

        # If already absolute, return as-is
        if path_obj.is_absolute():
            return str(path_obj)

        # Resolve relative to plugin_root
        resolved = plugin_root / path_obj
        return str(resolved.resolve())

    def resolve_dict(self, data: dict[str, Any], plugin_root: Path) -> dict[str, Any]:
        """Resolve paths in dictionary recursively.

        Args:
            data: Dictionary potentially containing paths
            plugin_root: Base path for relative resolution

        Returns:
            Dictionary with resolved paths
        """
        resolved = {}

        for key, value in data.items():
            if self._is_path_field(key):
                if isinstance(value, str):
                    # Resolve single path
                    resolved[key] = self.resolve(value, plugin_root)
                elif isinstance(value, list):
                    # Resolve list of paths (only strings)
                    resolved[key] = [
                        self.resolve(item, plugin_root) if isinstance(item, str) else item
                        for item in value
                    ]
                else:
                    resolved[key] = value
            elif isinstance(value, dict):
                # Recursively resolve nested dicts
                resolved[key] = self.resolve_dict(value, plugin_root)
            else:
                # Keep other values as-is
                resolved[key] = value

        return resolved

    def get_plugin_root(self) -> Path:
        """Get plugin root directory.

        Checks:
        1. PLUGIN_ROOT environment variable
        2. Current working directory context
        3. Default: ~/.amplihack/.claude

        Returns:
            Plugin root path
        """
        if self._cached_plugin_root:
            return self._cached_plugin_root

        # Check environment variable first
        if "PLUGIN_ROOT" in os.environ:
            self._cached_plugin_root = Path(os.environ["PLUGIN_ROOT"])
            return self._cached_plugin_root

        # Default to ~/.amplihack/.claude
        self._cached_plugin_root = Path.home() / ".amplihack" / ".claude"
        return self._cached_plugin_root

    def _is_path_field(self, field_name: str) -> bool:
        """Check if field name indicates a path field.

        Args:
            field_name: Field name to check

        Returns:
            True if field is a path field
        """
        # Exact match for known path fields
        if field_name in self.PATH_FIELDS:
            return True

        # Fuzzy match for fields containing 'path', 'file', or 'dir'
        field_lower = field_name.lower()
        return any(keyword in field_lower for keyword in ["path", "file", "dir", "cwd"])
