"""Settings generation and merging."""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional


class SettingsGenerator:
    """Generates and merges settings for Claude Code plugins.

    This generator:
    - Creates settings from plugin manifests
    - Performs deep merging of settings dictionaries
    - Writes formatted JSON settings files
    """

    # Plugin name pattern (lowercase letters, numbers, hyphens)
    NAME_PATTERN = re.compile(r'^[a-z0-9-]+$')

    def generate(
        self,
        plugin_manifest: Dict[str, Any],
        user_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate settings from plugin manifest.

        Args:
            plugin_manifest: Plugin manifest dictionary
            user_settings: Optional user settings to merge with defaults

        Returns:
            Generated settings dictionary

        Raises:
            ValueError: If plugin name is invalid or circular reference detected
        """
        # Check for circular references
        self._check_circular_reference(plugin_manifest)

        # Validate plugin name if present
        if 'name' in plugin_manifest:
            if not self.NAME_PATTERN.match(str(plugin_manifest['name'])):
                raise ValueError(
                    f"Invalid plugin name: {plugin_manifest['name']} "
                    "(must be lowercase letters, numbers, hyphens only)"
                )

        settings = {}

        # Add MCP servers if present in manifest
        if 'mcpServers' in plugin_manifest:
            settings['mcpServers'] = self._resolve_paths_in_dict(
                plugin_manifest['mcpServers']
            )

        # Add enabled plugins array for /plugin command discoverability
        if plugin_manifest.get('name'):
            plugin_name = plugin_manifest.get('name')
            settings['enabledPlugins'] = [plugin_name]

        # Add plugin metadata
        if plugin_manifest:
            if 'plugins' not in settings:
                settings['plugins'] = {}

            plugin_name = plugin_manifest.get('name', 'unknown')
            settings['plugins'][plugin_name] = {
                'version': plugin_manifest.get('version'),
                'description': plugin_manifest.get('description'),
            }

        # Merge with user settings if provided
        if user_settings:
            settings = self.merge_settings(settings, user_settings)

        return settings

    def merge_settings(
        self,
        base: Dict[str, Any],
        overlay: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two settings dictionaries.

        Args:
            base: Base settings dictionary
            overlay: Settings to overlay (takes precedence)

        Returns:
            Merged settings dictionary
        """
        if not base:
            return dict(overlay) if overlay else {}

        if not overlay:
            return dict(base)

        # Create copy to avoid modifying originals
        merged = dict(base)

        for key, value in overlay.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Deep merge nested dictionaries
                merged[key] = self.merge_settings(merged[key], value)
            elif key in merged and isinstance(merged[key], list) and isinstance(value, list):
                # Concatenate lists (could also replace based on strategy)
                merged[key] = merged[key] + value
            else:
                # Overlay value takes precedence
                merged[key] = value

        return merged

    def write_settings(
        self,
        settings: Dict[str, Any],
        target_path: Path
    ) -> bool:
        """Write settings to JSON file.

        Args:
            settings: Settings dictionary to write
            target_path: Path to write settings file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create parent directories
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Serialize to JSON with formatting
            json_content = json.dumps(settings, indent=2)

            # Write to file
            target_path.write_text(json_content)

            return True

        except (PermissionError, OSError, TypeError):
            return False

    def _check_circular_reference(self, data: Any, seen: Optional[set] = None) -> None:
        """Check for circular references in data structure.

        Args:
            data: Data to check
            seen: Set of object IDs already seen

        Raises:
            ValueError: If circular reference detected
        """
        if seen is None:
            seen = set()

        # Get object ID
        obj_id = id(data)

        # Check if we've seen this object before
        if obj_id in seen:
            raise ValueError("Circular reference detected in manifest")

        # Add to seen set
        seen.add(obj_id)

        # Recursively check nested structures
        if isinstance(data, dict):
            for value in data.values():
                self._check_circular_reference(value, seen)
        elif isinstance(data, list):
            for item in data:
                self._check_circular_reference(item, seen)

    def _resolve_paths_in_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve relative paths in dictionary to absolute paths.

        Args:
            data: Dictionary potentially containing paths

        Returns:
            Dictionary with resolved paths
        """
        resolved = {}

        for key, value in data.items():
            if key in {'cwd', 'path', 'script'} and isinstance(value, str):
                # Resolve relative paths
                path = Path(value)
                if not path.is_absolute():
                    # Make absolute (relative to current directory)
                    resolved[key] = str(path.resolve())
                else:
                    resolved[key] = value
            elif isinstance(value, dict):
                # Recursively resolve nested dicts
                resolved[key] = self._resolve_paths_in_dict(value)
            else:
                resolved[key] = value

        return resolved
