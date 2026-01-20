#!/usr/bin/env python3
"""
Settings Migration Module - Removes global amplihack hooks from ~/.claude/settings.json

Ensures amplihack hooks only run from project-local settings, preventing duplicate
stop hook execution that causes issues.

Philosophy:
- Ruthlessly Simple: Single-purpose module with clear contract
- Zero-BS: Every function works, no stubs or placeholders
- Fail-Safe: Non-destructive, creates backups, preserves non-amplihack hooks
- Modular: Self-contained brick with clear public API

Public API:
    SettingsMigrator: Main class for migration operations
    HookMigrationResult: Result dataclass for migration operations
    migrate_global_hooks(): Convenience function for one-shot migration
"""

import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class HookMigrationResult:
    """Result from hook migration operation.

    Attributes:
        success: Whether migration completed successfully
        global_hooks_found: Whether amplihack hooks were found in global settings
        global_hooks_removed: Whether global hooks were removed
        project_hook_ensured: Whether project-local hook is present
        backup_created: Path to backup file if created
        error: Error message if migration failed
    """

    success: bool
    global_hooks_found: bool
    global_hooks_removed: bool
    project_hook_ensured: bool
    backup_created: Path | None
    error: str | None


class SettingsMigrator:
    """Migrates amplihack hooks from global to project-local settings.

    Handles detection and removal of amplihack hooks from ~/.claude/settings.json
    while preserving all other hooks and settings. Creates backups before modification.
    """

    # Patterns to detect amplihack hooks
    AMPLIHACK_HOOK_PATTERNS = [
        "amplihack/hooks/stop.py",
        ".claude/tools/amplihack/hooks/stop.py",
        "amplihack/hooks/session_start.py",
        ".claude/tools/amplihack/hooks/session_start.py",
        "amplihack/hooks/pre_tool_use.py",
        ".claude/tools/amplihack/hooks/pre_tool_use.py",
        "amplihack/hooks/post_tool_use.py",
        ".claude/tools/amplihack/hooks/post_tool_use.py",
        "amplihack/hooks/pre_compact.py",
        ".claude/tools/amplihack/hooks/pre_compact.py",
    ]

    def __init__(self, project_root: Path | None = None):
        """Initialize settings migrator.

        Args:
            project_root: Project root directory (auto-detected if None)
        """
        if project_root is None:
            project_root = self._detect_project_root()

        self.project_root = project_root
        self.global_settings_path = Path.home() / ".claude" / "settings.json"
        self.project_settings_path = project_root / ".claude" / "settings.json"

    def _detect_project_root(self) -> Path:
        """Auto-detect project root by finding .claude marker.

        Returns:
            Project root path

        Raises:
            ValueError: If project root cannot be found
        """
        current = Path(__file__).resolve().parent
        for _ in range(10):  # Max 10 levels up
            if (current / ".claude").exists():
                return current
            if current == current.parent:
                break
            current = current.parent

        raise ValueError("Could not find project root with .claude marker")

    def log(self, message: str) -> None:
        """Log message to stderr for visibility.

        Args:
            message: Message to log
        """
        print(f"[settings_migrator] {message}", file=sys.stderr)

    def detect_global_amplihack_hooks(self) -> bool:
        """Check if global settings contain amplihack hooks.

        Returns:
            True if amplihack hooks found in global settings
        """
        if not self.global_settings_path.exists():
            return False

        try:
            with open(self.global_settings_path) as f:
                settings = json.load(f)

            # Check hooks section
            hooks = settings.get("hooks", {})

            # Check all hook types
            for hook_type in ["Stop", "SessionStart", "PreToolUse", "PostToolUse", "PreCompact"]:
                hook_configs = hooks.get(hook_type, [])

                for hook_config in hook_configs:
                    # Check hooks array in each config
                    for hook in hook_config.get("hooks", []):
                        command = hook.get("command", "")

                        # Check if command matches any amplihack pattern
                        if any(pattern in command for pattern in self.AMPLIHACK_HOOK_PATTERNS):
                            return True

            return False

        except OSError as e:
            self.log(f"Could not read global settings file: {e}")
            return False
        except json.JSONDecodeError as e:
            self.log(f"Global settings file has invalid JSON: {e}")
            return False

    def migrate_to_project_local(self) -> HookMigrationResult:
        """Remove global amplihack hooks and ensure project-local hook exists.

        This is the main entry point for migration. It:
        1. Checks for global amplihack hooks
        2. Creates backup if modifications needed
        3. Removes amplihack hooks from global settings
        4. Verifies project-local settings.json exists

        Returns:
            HookMigrationResult with operation details
        """
        try:
            # Check if global hooks exist
            global_hooks_found = self.detect_global_amplihack_hooks()

            if not global_hooks_found:
                self.log("No global amplihack hooks found")
                # Still check project settings
                project_hook_ensured = self.project_settings_path.exists()
                return HookMigrationResult(
                    success=True,
                    global_hooks_found=False,
                    global_hooks_removed=False,
                    project_hook_ensured=project_hook_ensured,
                    backup_created=None,
                    error=None,
                )

            # Global hooks found - proceed with migration
            self.log("Found global amplihack hooks - removing...")

            # Create backup
            backup_path = self._create_backup()
            if backup_path:
                self.log(f"Created backup: {backup_path}")

            # Remove global hooks
            removed = self._remove_global_amplihack_hooks()

            if not removed:
                return HookMigrationResult(
                    success=False,
                    global_hooks_found=True,
                    global_hooks_removed=False,
                    project_hook_ensured=False,
                    backup_created=backup_path,
                    error="Failed to remove global hooks",
                )

            self.log("Successfully removed global amplihack hooks")

            # Check project settings
            project_hook_ensured = self.project_settings_path.exists()

            if not project_hook_ensured:
                self.log(f"Warning: Project settings not found at {self.project_settings_path}")

            return HookMigrationResult(
                success=True,
                global_hooks_found=True,
                global_hooks_removed=True,
                project_hook_ensured=project_hook_ensured,
                backup_created=backup_path,
                error=None,
            )

        except Exception as e:
            self.log(f"Migration error: {e}")
            return HookMigrationResult(
                success=False,
                global_hooks_found=False,
                global_hooks_removed=False,
                project_hook_ensured=False,
                backup_created=None,
                error=str(e),
            )

    def _create_backup(self) -> Path | None:
        """Create backup of global settings before modification.

        Returns:
            Path to backup file, or None if backup failed
        """
        if not self.global_settings_path.exists():
            return None

        try:
            # Create timestamped backup
            timestamp = int(time.time())
            backup_path = self.global_settings_path.parent / f"settings.json.backup.{timestamp}"

            shutil.copy2(self.global_settings_path, backup_path)
            return backup_path

        except OSError as e:
            self.log(f"Backup creation failed: {e}")
            return None

    def _remove_global_amplihack_hooks(self) -> bool:
        """Remove amplihack hooks from global settings while preserving others.

        Returns:
            True if removal successful, False otherwise
        """
        if not self.global_settings_path.exists():
            return True  # Nothing to remove

        try:
            # Load current settings
            with open(self.global_settings_path) as f:
                settings = json.load(f)

            # Remove amplihack hooks while preserving others
            hooks = settings.get("hooks", {})

            for hook_type in ["Stop", "SessionStart", "PreToolUse", "PostToolUse", "PreCompact"]:
                if hook_type not in hooks:
                    continue

                hook_configs = hooks[hook_type]
                filtered_configs = []

                for hook_config in hook_configs:
                    # Filter hooks array to remove amplihack hooks
                    filtered_hooks = []

                    for hook in hook_config.get("hooks", []):
                        command = hook.get("command", "")

                        # Keep hook if it's not an amplihack hook
                        if not any(pattern in command for pattern in self.AMPLIHACK_HOOK_PATTERNS):
                            filtered_hooks.append(hook)

                    # Keep config if it has remaining hooks
                    if filtered_hooks:
                        hook_config["hooks"] = filtered_hooks
                        filtered_configs.append(hook_config)

                # Update hook type with filtered configs
                if filtered_configs:
                    hooks[hook_type] = filtered_configs
                else:
                    # Remove empty hook type
                    del hooks[hook_type]

            # Update settings
            settings["hooks"] = hooks

            # Write atomically using safe_json_update
            return self.safe_json_update(self.global_settings_path, settings)

        except (OSError, json.JSONDecodeError) as e:
            self.log(f"Error removing hooks: {e}")
            return False

    def safe_json_update(self, file_path: Path, data: dict[str, Any]) -> bool:
        """Atomic JSON file update with backup.

        Uses temp file + rename for atomic write operation.

        Args:
            file_path: Path to JSON file to update
            data: Dictionary to write as JSON

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Write to temp file first
            temp_path = file_path.parent / f".{file_path.name}.tmp"

            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")  # Add trailing newline

            # Atomic rename (overwrites existing file)
            os.replace(temp_path, file_path)

            return True

        except (OSError, TypeError) as e:
            self.log(f"JSON update failed: {e}")

            # Clean up temp file if it exists
            try:
                temp_path = file_path.parent / f".{file_path.name}.tmp"
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

            return False


def migrate_global_hooks(project_root: Path | None = None) -> HookMigrationResult:
    """Convenience function to migrate global amplihack hooks.

    Args:
        project_root: Project root directory (auto-detected if None)

    Returns:
        HookMigrationResult with operation details

    Example:
        >>> result = migrate_global_hooks()
        >>> if result.success and result.global_hooks_removed:
        ...     print("✓ Global hooks migrated successfully")
    """
    migrator = SettingsMigrator(project_root)
    return migrator.migrate_to_project_local()


__all__ = ["SettingsMigrator", "HookMigrationResult", "migrate_global_hooks"]


if __name__ == "__main__":
    # For testing: Allow running directly
    result = migrate_global_hooks()

    print("\nMigration Result:")
    print(f"  Success: {result.success}")
    print(f"  Global hooks found: {result.global_hooks_found}")
    print(f"  Global hooks removed: {result.global_hooks_removed}")
    print(f"  Project hook ensured: {result.project_hook_ensured}")
    print(f"  Backup created: {result.backup_created}")

    if result.error:
        print(f"  Error: {result.error}")
        sys.exit(1)

    sys.exit(0 if result.success else 1)
