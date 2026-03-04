"""Staging, auto-update preference, and global settings helpers for amplihack CLI.

This module handles ensuring the amplihack framework is staged to
~/.amplihack/.claude/, fixing global settings paths, and reading
user auto-update preferences.

Public API:
    ensure_amplihack_staged: Stage .claude/ files to ~/.amplihack/.claude/
    fix_global_statusline_path: Fix statusline path in ~/.claude/settings.json
    read_auto_update_preference: Check if auto_update preference is 'always'
"""

import json
import logging
import os
import sys
from pathlib import Path

from . import copytree_manifest
from .staging_cleanup import cleanup_legacy_skills
from .utils import is_uvx_deployment

logger = logging.getLogger(__name__)


def fix_global_statusline_path() -> None:
    """Fix the global ~/.claude/settings.json statusline path to use ~/.amplihack/.claude/tools/statusline.sh.

    This ensures the statusline works in all directories, not just projects with amplihack installed locally.
    """
    global_settings_path = Path.home() / ".claude" / "settings.json"

    # Only proceed if settings.json exists
    if not global_settings_path.exists():
        return

    try:
        # Read current settings
        with open(global_settings_path, encoding="utf-8") as f:
            settings = json.load(f)

        # Check if statusLine needs updating
        statusline_config = settings.get("statusLine", {})
        current_command = statusline_config.get("command", "")
        correct_command = "~/.amplihack/.claude/tools/statusline.sh"

        # Only update if the command is a project-relative path
        if current_command != correct_command and (
            current_command == ".claude/tools/statusline.sh"
            or current_command == "./claude/tools/statusline.sh"
            or current_command.endswith(".claude/tools/statusline.sh")
        ):
            statusline_config["command"] = correct_command
            settings["statusLine"] = statusline_config

            # Write updated settings
            with open(global_settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
                print(f"\u2713 Updated statusline path in {global_settings_path}")

    except (json.JSONDecodeError, OSError) as e:
        # Fail silently - don't break amplihack commands over this
        if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
            print(f"Warning: Could not update global statusline path: {e}")


def ensure_amplihack_staged() -> None:
    """Ensure .claude/ files are staged to ~/.amplihack/.claude/ for non-Claude commands.

    This function populates the unified staging directory used by copilot, amplifier,
    rustyclawd, and codex commands. Only runs in UVX deployment mode.

    The staging process:
    1. Creates ~/.amplihack/.claude/ if it doesn't exist
    2. Copies essential framework files using copytree_manifest()
    3. Exits with code 1 if staging fails

    Raises:
        SystemExit: With code 1 if staging fails
    """
    # Only run in UVX deployment mode
    if not is_uvx_deployment():
        return

    # Clean up legacy skill directories before staging
    try:
        result = cleanup_legacy_skills()

        # Report cleaned directories (user-visible in debug mode)
        if result.cleaned:
            if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
                print(f"\u2713 Cleaned up {len(result.cleaned)} legacy skill directories")
                for cleaned_dir in result.cleaned:
                    logger.debug(f"  Removed: {cleaned_dir}")

        # Report skipped directories (user-visible, not just debug)
        if result.skipped:
            for skipped_dir, reason in result.skipped:
                logger.info(f"Skipped cleanup of {skipped_dir}: {reason}")

        # Report errors (user-visible, not just debug)
        if result.errors:
            for error_dir, error_msg in result.errors:
                logger.error(f"Failed to clean up {error_dir}: {error_msg}")

    except Exception as e:
        # Log error but don't fail staging
        logger.warning(f"Legacy skills cleanup failed: {e}")

    # Debug logging
    if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
        print("\U0001f4e6 Staging amplihack framework to ~/.amplihack/.claude/")

    # Determine source directory (package installation)
    import amplihack

    amplihack_src = Path(amplihack.__file__).parent

    # Unified staging directory for all commands
    staging_dir = Path.home() / ".amplihack" / ".claude"
    staging_dir.mkdir(parents=True, exist_ok=True)

    # Copy .claude/ files to staging directory
    copied = copytree_manifest(str(amplihack_src), str(staging_dir), ".claude")

    if not copied:
        print("\u274c Failed to stage amplihack framework to ~/.amplihack/.claude/")
        print("   This is required for amplihack commands to work in UVX mode.")
        sys.exit(1)

    # Debug logging
    if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
        print(f"\u2713 Staged {len(copied)} directories to {staging_dir}")

    # Configure Claude Code hooks in ~/.claude/settings.json
    from .settings import ensure_settings_json

    ensure_settings_json()

    # Fix global ~/.claude/settings.json statusline path if needed
    fix_global_statusline_path()


def read_auto_update_preference(plugin_dir: str) -> bool:
    """Check if user's auto_update preference is 'always'.

    Reads from USER_PREFERENCES.md in the plugin directory. If set to 'always',
    returns True to skip the conflict prompt and auto-approve overwrites.

    Args:
        plugin_dir: Path to the .claude plugin directory (e.g. ~/.amplihack/.claude)

    Returns:
        True if auto_update preference is 'always', False otherwise
    """
    try:
        prefs_file = Path(plugin_dir) / "context" / "USER_PREFERENCES.md"
        if not prefs_file.exists():
            return False
        content = prefs_file.read_text(encoding="utf-8")
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.strip() == "### Auto Update" and i + 2 < len(lines):
                return lines[i + 2].strip().lower() == "always"
    except Exception as e:
        logger.debug(f"Could not read auto-update preference: {type(e).__name__}: {e}")
    return False


__all__ = [
    "ensure_amplihack_staged",
    "fix_global_statusline_path",
    "read_auto_update_preference",
]
