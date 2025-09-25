#!/usr/bin/env python3
"""
XPIA Hook Merge Utility

Intelligently merges XPIA security hooks into Claude Code settings.json while
preserving existing user hook configurations.

Following the bricks & studs philosophy:
- Brick: Self-contained hook configuration management
- Stud: Clear contract for settings.json manipulation
- Regeneratable: Can be rebuilt from specification
"""

import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HookConfig:
    """Configuration for a single hook"""

    hook_type: str  # "SessionStart", "PostToolUse", etc.
    command: str
    matcher: Optional[str] = None
    timeout: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON"""
        hook_dict = {"type": "command", "command": self.command}

        if self.timeout is not None:
            hook_dict["timeout"] = self.timeout

        return hook_dict


@dataclass
class MergeResult:
    """Result of hook merge operation"""

    success: bool
    backup_path: Optional[str] = None
    error_message: Optional[str] = None
    hooks_added: int = 0
    hooks_updated: int = 0
    rollback_performed: bool = False


class SettingsJsonError(Exception):
    """Error in settings.json processing"""

    pass


class HookMergeUtility:
    """
    Core utility for merging XPIA security hooks into settings.json

    Handles:
    - Backup and rollback operations
    - Format detection and validation
    - Smart merging without data loss
    - Edge case handling
    """

    def __init__(self, settings_path: Union[str, Path]):
        self.settings_path = Path(settings_path)
        self.backup_dir = self.settings_path.parent / "backups"

    async def merge_hooks(self, xpia_hooks: List[HookConfig]) -> MergeResult:
        """
        Main entry point for merging XPIA hooks into settings.json

        Args:
            xpia_hooks: List of XPIA hooks to integrate

        Returns:
            MergeResult with operation status and rollback information
        """
        result = MergeResult(success=False)

        try:
            # Step 1: Create backup
            backup_path = await self._backup_settings()
            result.backup_path = backup_path
            logger.info(f"Created backup: {backup_path}")

            # Step 2: Load and validate current settings
            current_settings = await self._load_settings()

            # Step 3: Merge XPIA hooks
            merged_settings, hooks_added, hooks_updated = await self._merge_xpia_hooks(
                current_settings, xpia_hooks
            )

            # Step 4: Validate merged settings
            if not self._validate_settings_format(merged_settings):
                raise SettingsJsonError("Merged settings failed validation")

            # Step 5: Write merged settings
            await self._save_settings(merged_settings)

            # Step 6: Verify the saved file is valid
            await self._verify_saved_settings()

            result.success = True
            result.hooks_added = hooks_added
            result.hooks_updated = hooks_updated

            logger.info(
                f"Successfully merged XPIA hooks: {hooks_added} added, {hooks_updated} updated"
            )

        except Exception as e:
            logger.error(f"Hook merge failed: {e}")
            result.error_message = str(e)

            # Attempt rollback if we have a backup
            if result.backup_path and Path(result.backup_path).exists():
                try:
                    await self._restore_settings(result.backup_path)
                    result.rollback_performed = True
                    logger.info("Successfully rolled back to previous settings")
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
                    result.error_message += f" | Rollback failed: {rollback_error}"

        return result

    async def _backup_settings(self) -> str:
        """Create timestamped backup of settings.json"""
        if not self.settings_path.exists():
            # No settings file exists, create placeholder backup
            placeholder_backup = self.backup_dir / f"no_settings_backup_{self._timestamp()}.json"
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            placeholder_backup.write_text("{}")
            return str(placeholder_backup)

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = self.backup_dir / f"settings_backup_{self._timestamp()}.json"

        shutil.copy2(self.settings_path, backup_path)
        return str(backup_path)

    async def _load_settings(self) -> Dict[str, Any]:
        """Load and parse current settings.json"""
        if not self.settings_path.exists():
            logger.info("No settings.json found, creating new configuration")
            return self._create_default_settings()

        try:
            with open(self.settings_path, "r") as f:
                settings = json.load(f)

            # Ensure hooks section exists
            if "hooks" not in settings:
                settings["hooks"] = {}

            return settings

        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load settings.json: {e}, creating new configuration")
            return self._create_default_settings()

    def _create_default_settings(self) -> Dict[str, Any]:
        """Create default settings.json with basic structure"""
        return {
            "permissions": {
                "allow": ["Bash", "TodoWrite", "WebSearch", "WebFetch"],
                "deny": [],
                "defaultMode": "bypassPermissions",
                "additionalDirectories": [".claude", "Specs"],
            },
            "enableAllProjectMcpServers": False,
            "enabledMcpjsonServers": [],
            "hooks": {},
        }

    async def _merge_xpia_hooks(
        self, settings: Dict[str, Any], xpia_hooks: List[HookConfig]
    ) -> tuple[Dict[str, Any], int, int]:
        """
        Merge XPIA hooks into settings while preserving existing hooks

        Returns:
            (merged_settings, hooks_added, hooks_updated)
        """
        hooks_added = 0
        hooks_updated = 0

        for hook_config in xpia_hooks:
            hook_type = hook_config.hook_type
            hook_data = hook_config.to_dict()

            # Add matcher if specified and hook type supports it
            if hook_config.matcher and hook_type == "PostToolUse":
                hook_data["matcher"] = hook_config.matcher

            # Initialize hook type section if it doesn't exist
            if hook_type not in settings["hooks"]:
                settings["hooks"][hook_type] = []

            # Check if this XPIA hook already exists
            existing_xpia_hook = self._find_existing_xpia_hook(
                settings["hooks"][hook_type], hook_config.command
            )

            if existing_xpia_hook is not None:
                # Update existing XPIA hook
                settings["hooks"][hook_type][existing_xpia_hook] = self._create_hook_entry(
                    hook_data, hook_config.matcher
                )
                hooks_updated += 1
                logger.info(f"Updated existing XPIA hook: {hook_type}")
            else:
                # Add new XPIA hook
                hook_entry = self._create_hook_entry(hook_data, hook_config.matcher)
                settings["hooks"][hook_type].append(hook_entry)
                hooks_added += 1
                logger.info(f"Added new XPIA hook: {hook_type}")

        return settings, hooks_added, hooks_updated

    def _find_existing_xpia_hook(self, hook_list: List[Dict], command: str) -> Optional[int]:
        """Find index of existing XPIA hook in hook list"""
        for i, hook_entry in enumerate(hook_list):
            if "hooks" in hook_entry:
                for hook in hook_entry["hooks"]:
                    if hook.get("command", "").endswith("/xpia/hooks/") or "xpia" in hook.get(
                        "command", ""
                    ):
                        return i
        return None

    def _create_hook_entry(
        self, hook_data: Dict[str, Any], matcher: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create hook entry in Claude Code format"""
        entry = {"hooks": [hook_data]}

        if matcher:
            entry["matcher"] = matcher

        return entry

    def _validate_settings_format(self, settings: Dict[str, Any]) -> bool:
        """Validate that settings follow expected format"""
        try:
            # Basic structure validation
            required_keys = ["permissions", "hooks"]
            for key in required_keys:
                if key not in settings:
                    logger.error(f"Missing required key: {key}")
                    return False

            # Validate hooks structure
            hooks = settings["hooks"]
            if not isinstance(hooks, dict):
                logger.error("Hooks section must be a dictionary")
                return False

            # Validate individual hook entries
            for hook_type, hook_list in hooks.items():
                if not isinstance(hook_list, list):
                    logger.error(f"Hook type {hook_type} must be a list")
                    return False

                for hook_entry in hook_list:
                    if not isinstance(hook_entry, dict):
                        logger.error("Hook entry must be a dictionary")
                        return False

                    if "hooks" not in hook_entry:
                        logger.error("Hook entry must contain 'hooks' key")
                        return False

            return True

        except Exception as e:
            logger.error(f"Settings validation failed: {e}")
            return False

    async def _save_settings(self, settings: Dict[str, Any]) -> None:
        """Save merged settings to file"""
        # Ensure parent directory exists
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Write with proper formatting
        with open(self.settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        logger.info(f"Saved merged settings to {self.settings_path}")

    async def _verify_saved_settings(self) -> None:
        """Verify that saved settings file is valid JSON"""
        try:
            with open(self.settings_path, "r") as f:
                json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise SettingsJsonError(f"Saved settings file is invalid: {e}")

    async def _restore_settings(self, backup_path: str) -> None:
        """Restore settings from backup"""
        backup_file = Path(backup_path)

        if not backup_file.exists():
            raise SettingsJsonError(f"Backup file not found: {backup_path}")

        # Handle special case of "no settings" backup
        if backup_file.name.startswith("no_settings_backup_"):
            # Remove the settings file to restore "no settings" state
            if self.settings_path.exists():
                self.settings_path.unlink()
            logger.info("Restored 'no settings' state")
        else:
            shutil.copy2(backup_file, self.settings_path)
            logger.info(f"Restored settings from backup: {backup_path}")

    def _timestamp(self) -> str:
        """Generate timestamp for backup files"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_required_xpia_hooks() -> List[HookConfig]:
    """
    Get list of required XPIA security hooks

    Returns:
        List of HookConfig objects for XPIA security integration
    """
    # Get home directory for absolute paths
    home_dir = os.path.expanduser("~")

    return [
        HookConfig(
            hook_type="SessionStart",
            command=f"{home_dir}/.claude/tools/xpia/hooks/session_start.py",
            timeout=10000,
        ),
        HookConfig(
            hook_type="PostToolUse",
            command=f"{home_dir}/.claude/tools/xpia/hooks/post_tool_use.py",
            matcher="*",
            timeout=3000,
        ),
        HookConfig(
            hook_type="PreToolUse",
            command=f"{home_dir}/.claude/tools/xpia/hooks/pre_tool_use.py",
            matcher="Bash",
            timeout=5000,
        ),
    ]


async def main():
    """CLI interface for hook merge utility"""
    import argparse

    parser = argparse.ArgumentParser(description="Merge XPIA security hooks into settings.json")
    parser.add_argument(
        "--settings", default="~/.claude/settings.json", help="Path to settings.json file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making modifications",
    )

    args = parser.parse_args()
    settings_path = Path(args.settings).expanduser()

    # Initialize utility
    merger = HookMergeUtility(settings_path)

    # Get required XPIA hooks
    xpia_hooks = get_required_xpia_hooks()

    if args.dry_run:
        print("DRY RUN: Would merge the following XPIA hooks:")
        for hook in xpia_hooks:
            print(f"  - {hook.hook_type}: {hook.command}")
        return

    # Perform merge
    result = await merger.merge_hooks(xpia_hooks)

    if result.success:
        print("✅ Successfully merged XPIA hooks:")
        print(f"   Added: {result.hooks_added}")
        print(f"   Updated: {result.hooks_updated}")
        if result.backup_path:
            print(f"   Backup: {result.backup_path}")
    else:
        print(f"❌ Hook merge failed: {result.error_message}")
        if result.rollback_performed:
            print("   Rollback was performed successfully")
        exit(1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
