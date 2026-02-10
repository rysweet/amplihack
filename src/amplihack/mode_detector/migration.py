"""Migration helper for Claude installation modes.

Philosophy:
- Simple directory operations
- User-initiated migration only (no automatic)
- Clear feedback on success/failure

Public API (the "studs"):
    MigrationHelper: Main migration class
"""

import shutil
from pathlib import Path


class MigrationHelper:
    """Help users migrate between Claude installation modes."""

    def __init__(self):
        """Initialize migration helper."""
        self.plugin_claude = Path.home() / ".amplihack" / ".claude"
        self.plugin_root = self.plugin_claude.parent

    def migrate_to_plugin(self, project_dir: Path) -> bool:
        """Migrate project from local to plugin mode.

        Args:
            project_dir: Project directory with .claude/

        Returns:
            True if successful, False otherwise
        """
        local_claude = project_dir / ".claude"

        if not local_claude.exists():
            return False

        if not self.can_migrate_to_plugin(project_dir):
            return False

        try:
            # Remove local .claude/ (user confirms before calling this)
            shutil.rmtree(local_claude)
            return True
        except (PermissionError, OSError):
            return False

    def migrate_to_local(self, project_dir: Path) -> bool:
        """Create local .claude/ from plugin.

        Args:
            project_dir: Project directory to create .claude/ in

        Returns:
            True if successful, False otherwise
        """
        local_claude = project_dir / ".claude"

        if local_claude.exists():
            return False  # Don't overwrite existing

        if not self.plugin_claude.exists():
            return False  # No plugin to copy from

        try:
            # Copy plugin .claude/ to project
            shutil.copytree(self.plugin_claude, local_claude)
            return True
        except (PermissionError, OSError):
            return False

    def can_migrate_to_plugin(self, project_dir: Path) -> bool:
        """Check if project can migrate to plugin mode.

        Args:
            project_dir: Project directory to check

        Returns:
            True if migration is possible
        """
        local_claude = project_dir / ".claude"

        # Must have local installation
        if not local_claude.exists():
            return False

        # Must have plugin installation
        if not self.plugin_claude.exists():
            return False

        # Must have plugin manifest
        manifest = self.plugin_root / ".claude-plugin" / "plugin.json"
        if not manifest.exists():
            return False

        return True

    def get_migration_info(self, project_dir: Path) -> dict:
        """Get information about migration options.

        Args:
            project_dir: Project directory to check

        Returns:
            Dict with migration status and options
        """
        local_claude = project_dir / ".claude"
        has_local = local_claude.exists()
        has_plugin = self.plugin_claude.exists()

        return {
            "has_local": has_local,
            "has_plugin": has_plugin,
            "can_migrate_to_plugin": self.can_migrate_to_plugin(project_dir),
            "can_migrate_to_local": has_plugin and not has_local,
            "local_path": local_claude if has_local else None,
            "plugin_path": self.plugin_claude if has_plugin else None,
        }


__all__ = ["MigrationHelper"]
