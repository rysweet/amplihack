"""UVX settings management for fresh installations.

This module handles the creation and management of settings.json files
specifically for UVX installations to ensure bypass permissions are
properly configured out-of-the-box.
"""

import json
import shutil
from pathlib import Path
from typing import Any


class UVXSettingsManager:
    """Manages settings.json creation and updates for UVX installations."""

    def __init__(self):
        """Initialize the UVX settings manager."""
        self._template_path = Path(__file__).parent / "uvx_settings_template.json"

    def should_use_uvx_template(self, target_settings_path: Path) -> bool:
        """Determine if we should use the UVX template for this installation.

        Args:
            target_settings_path: Path where settings.json will be created

        Returns:
            True if we should use the UVX template, False otherwise
        """
        # Use UVX template if settings.json doesn't exist (fresh installation)
        if not target_settings_path.exists():
            return True

        # Check if existing settings.json lacks bypass permissions
        try:
            with open(target_settings_path, encoding="utf-8") as f:
                existing_settings = json.load(f)

            permissions = existing_settings.get("permissions", {})
            default_mode = permissions.get("defaultMode", "askPermissions")

            # If defaultMode is not bypassPermissions, this is likely a fresh installation
            # or a settings file that needs bypass permissions enabled
            return default_mode != "bypassPermissions"

        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            # If we can't read the existing settings, use UVX template
            return True

    def create_uvx_settings(self, target_path: Path, preserve_existing: bool = True) -> bool:
        """Create UVX-optimized settings.json file.

        Args:
            target_path: Path where to create settings.json
            preserve_existing: If True, backup existing settings before replacing

        Returns:
            True if settings were created successfully, False otherwise
        """
        try:
            # Preserve MCP-related settings from existing settings if present
            existing_mcp_servers = None
            existing_mcp_enabled = None
            if preserve_existing and target_path.exists():
                backup_path = target_path.with_suffix(".json.backup.uvx")
                shutil.copy2(target_path, backup_path)

                # Extract MCP settings to preserve
                try:
                    with open(target_path, encoding="utf-8") as f:
                        existing = json.load(f)
                        existing_mcp_servers = existing.get("mcpServers")
                        existing_mcp_enabled = existing.get("enableAllProjectMcpServers")
                except (OSError, json.JSONDecodeError):
                    pass

            # Load the UVX template
            with open(self._template_path, encoding="utf-8") as f:
                uvx_template = json.load(f)

            # Restore preserved MCP settings
            if existing_mcp_servers:
                uvx_template["mcpServers"] = existing_mcp_servers
            if existing_mcp_enabled is not None:
                uvx_template["enableAllProjectMcpServers"] = existing_mcp_enabled

            # Write the UVX-optimized settings
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(uvx_template, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            # Log error but don't crash the staging process
            import sys

            print(f"[UVX Settings] Warning: Failed to create UVX settings: {e}", file=sys.stderr)
            return False

    def merge_with_existing_settings(
        self, target_path: Path, existing_settings: dict[str, Any]
    ) -> bool:
        """Merge UVX template with existing settings, preserving user customizations.

        Args:
            target_path: Path where to write merged settings
            existing_settings: Existing settings dictionary to merge with

        Returns:
            True if merge was successful, False otherwise
        """
        try:
            # Load the UVX template
            with open(self._template_path, encoding="utf-8") as f:
                uvx_template = json.load(f)

            # Merge settings, prioritizing UVX template for permissions and core tools
            merged_settings = existing_settings.copy()

            # Always use UVX template permissions for bypass behavior
            merged_settings["permissions"] = uvx_template["permissions"].copy()

            # Merge tool allowlists - add UVX tools to existing allow list
            if "permissions" in existing_settings and "allow" in existing_settings["permissions"]:
                # Combine existing allowed tools with UVX template tools
                existing_allow = set(existing_settings["permissions"]["allow"])
                uvx_allow = set(uvx_template["permissions"]["allow"])
                merged_settings["permissions"]["allow"] = sorted(existing_allow | uvx_allow)

            # Preserve existing hooks but ensure amplihack hooks are present
            if "hooks" in existing_settings:
                # Use existing hooks structure, but add amplihack hooks if missing
                merged_hooks = existing_settings["hooks"].copy()

                # Add essential amplihack hooks if not present
                uvx_hooks = uvx_template["hooks"]
                for hook_name, hook_config in uvx_hooks.items():
                    if hook_name not in merged_hooks:
                        merged_hooks[hook_name] = hook_config

                merged_settings["hooks"] = merged_hooks
            else:
                # Use UVX template hooks if none exist
                merged_settings["hooks"] = uvx_template["hooks"]

            # Write merged settings
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(merged_settings, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            import sys

            print(f"[UVX Settings] Warning: Failed to merge settings: {e}", file=sys.stderr)
            return False

    def get_template_settings(self) -> dict[str, Any] | None:
        """Get the UVX template settings as a dictionary.

        Returns:
            Dictionary containing UVX template settings, or None if failed to load
        """
        try:
            with open(self._template_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None


# Global instance for easy access
uvx_settings_manager = UVXSettingsManager()
