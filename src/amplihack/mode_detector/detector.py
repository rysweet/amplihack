"""Mode detector for Claude installations.

Philosophy:
- Simple detection with clear precedence (LOCAL > PLUGIN > NONE)
- No complex configuration - just check directories
- Support environment override for testing

Public API (the "studs"):
    ClaudeMode: Enum for installation modes
    ModeDetector: Main detection class
    detect_claude_mode: Convenience function
"""

import os
from enum import Enum
from pathlib import Path
from typing import Optional


class ClaudeMode(Enum):
    """Claude installation mode."""
    LOCAL = "local"    # Project has .claude/ directory
    PLUGIN = "plugin"  # Use plugin from ~/.amplihack/.claude/
    NONE = "none"      # No installation found


class ModeDetector:
    """Detect Claude installation mode with precedence: LOCAL > PLUGIN > NONE."""

    def __init__(self, project_dir: Optional[Path] = None):
        """Initialize detector.

        Args:
            project_dir: Project directory to check (defaults to cwd)
        """
        self.project_dir = project_dir or Path.cwd()
        self.local_claude = self.project_dir / ".claude"
        self.plugin_claude = Path.home() / ".amplihack" / ".claude"

    def detect(self) -> ClaudeMode:
        """Detect which mode to use.

        Precedence:
        1. LOCAL - Project has .claude/ directory
        2. PLUGIN - Plugin installed at ~/.amplihack/.claude/
        3. NONE - No installation found

        Returns:
            ClaudeMode indicating which installation to use
        """
        # Check for explicit override via environment
        override = os.environ.get("AMPLIHACK_MODE")
        if override:
            if override.lower() == "local" and self.has_local_installation():
                return ClaudeMode.LOCAL
            elif override.lower() == "plugin" and self.has_plugin_installation():
                return ClaudeMode.PLUGIN

        # Standard precedence: LOCAL > PLUGIN > NONE
        if self.has_local_installation():
            return ClaudeMode.LOCAL
        elif self.has_plugin_installation():
            return ClaudeMode.PLUGIN
        else:
            return ClaudeMode.NONE

    def get_claude_dir(self, mode: ClaudeMode) -> Optional[Path]:
        """Get .claude directory path for mode.

        Args:
            mode: ClaudeMode to get directory for

        Returns:
            Path to .claude directory or None
        """
        if mode == ClaudeMode.LOCAL:
            return self.local_claude if self.has_local_installation() else None
        elif mode == ClaudeMode.PLUGIN:
            return self.plugin_claude if self.has_plugin_installation() else None
        else:
            return None

    def has_local_installation(self) -> bool:
        """Check if project has valid .claude/ directory.

        Returns:
            True if .claude exists and has essential content
        """
        if not self.local_claude.exists():
            return False

        # Check for essential directories (at least one should exist)
        essential_dirs = ["agents", "commands", "skills", "tools"]
        return any((self.local_claude / d).exists() for d in essential_dirs)

    def has_plugin_installation(self) -> bool:
        """Check if plugin is installed.

        Returns:
            True if plugin exists at ~/.amplihack/.claude/
        """
        if not self.plugin_claude.exists():
            return False

        # Check for plugin manifest
        manifest = self.plugin_claude.parent / ".claude-plugin" / "plugin.json"
        return manifest.exists()


def detect_claude_mode(project_dir: Optional[Path] = None) -> ClaudeMode:
    """Convenience function to detect Claude mode.

    Args:
        project_dir: Project directory (defaults to cwd)

    Returns:
        ClaudeMode indicating which installation to use
    """
    detector = ModeDetector(project_dir)
    return detector.detect()


__all__ = ["ClaudeMode", "ModeDetector", "detect_claude_mode"]
