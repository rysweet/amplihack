"""Settings management for amplihack.

Philosophy:
- Single responsibility: Manage settings.json configuration
- Self-contained: All settings logic in one place
- Regeneratable: Can be rebuilt from specification

Public API (the "studs"):
    ensure_settings_json: Ensure settings.json exists with proper hook configuration
    update_hook_paths: Update hook paths for a given hook system
    SETTINGS_TEMPLATE: Default settings template
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path

# Import constants from package root
from . import CLAUDE_DIR, HOME, HOOK_CONFIGS

# Settings.json template with proper hook configuration
SETTINGS_TEMPLATE = {
    "permissions": {
        "allow": ["Bash", "TodoWrite", "WebSearch", "WebFetch"],
        "deny": [],
        "defaultMode": "bypassPermissions",
        "additionalDirectories": [".claude", "Specs"],
    },
    "enableAllProjectMcpServers": False,
    "enabledMcpjsonServers": [],
    "hooks": {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "$HOME/.claude/tools/amplihack/hooks/session_start.py",
                        "timeout": 10000,
                    }
                ]
            }
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "$HOME/.claude/tools/amplihack/hooks/stop.py",
                        "timeout": 30000,
                    }
                ]
            }
        ],
        "PostToolUse": [
            {
                "matcher": "*",
                "hooks": [
                    {
                        "type": "command",
                        "command": "$HOME/.claude/tools/amplihack/hooks/post_tool_use.py",
                    }
                ],
            }
        ],
        "PreCompact": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "$HOME/.claude/tools/amplihack/hooks/pre_compact.py",
                        "timeout": 30000,
                    }
                ]
            }
        ],
    },
}


def update_hook_paths(settings, hook_system, hooks_to_update, hooks_dir_path):
    """Update hook paths for a given hook system (amplihack or xpia).

    Args:
        settings: Settings dictionary to update
        hook_system: Name of the hook system (e.g., "amplihack", "xpia")
        hooks_to_update: List of dicts with keys: type, file, timeout (optional), matcher (optional)
        hooks_dir_path: Relative path to hooks directory (e.g., ".claude/tools/xpia/hooks")

    Returns:
        Number of hooks updated
    """
    hooks_updated = 0

    for hook_info in hooks_to_update:
        hook_type = hook_info["type"]
        hook_file = hook_info["file"]
        timeout = hook_info.get("timeout")
        matcher = hook_info.get("matcher")

        # Use forward slashes for relative paths (cross-platform JSON compatibility)
        hook_path = f"{hooks_dir_path}/{hook_file}"

        if hook_type not in settings.get("hooks", {}):
            # Add missing hook configuration
            if "hooks" not in settings:
                settings["hooks"] = {}

            # Create hook config based on type
            hook_config = {
                "type": "command",
                "command": hook_path,
            }
            if timeout:
                hook_config["timeout"] = timeout

            # Wrap in matcher or plain structure
            wrapper = (
                {"matcher": matcher, "hooks": [hook_config]}
                if matcher
                else {"hooks": [hook_config]}
            )
            settings["hooks"][hook_type] = [wrapper]
            hooks_updated += 1
        else:
            # Update existing hook paths
            hook_configs = settings["hooks"][hook_type]
            for config in hook_configs:
                if "hooks" in config:
                    for hook in config["hooks"]:
                        if "command" in hook and hook_system in hook["command"]:
                            # Update hook path
                            old_cmd = hook["command"]
                            if old_cmd != hook_path:
                                hook["command"] = hook_path
                                if timeout and "timeout" not in hook:
                                    hook["timeout"] = timeout
                                hooks_updated += 1
                                print(f"  🔄 Updated {hook_type} hook path")

    return hooks_updated


def ensure_settings_json():
    """Ensure settings.json exists with proper hook configuration."""
    settings_path = os.path.join(CLAUDE_DIR, "settings.json")

    # Detect UVX environment - if running from UVX, auto-approve settings modification
    # UVX runs don't have interactive stdin available
    is_uvx = (
        # Check for UVX environment variables
        os.getenv("UV_TOOL_NAME") is not None
        or os.getenv("UV_TOOL_BIN_DIR") is not None
        # Check if stdin is not a TTY (non-interactive)
        or not sys.stdin.isatty()
    )

    # Try to use SettingsManager if available (for backup/restore functionality)
    settings_manager = None
    backup_path = None
    try:
        # Try different import methods
        try:
            from amplihack.launcher.settings_manager import SettingsManager
        except ImportError:
            try:
                from .launcher.settings_manager import SettingsManager
            except ImportError:
                # Try adding parent to path temporarily
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                try:
                    from amplihack.launcher.settings_manager import SettingsManager
                except ImportError:
                    SettingsManager = None
                finally:
                    sys.path.pop(0)

        if SettingsManager:
            # Create settings manager
            settings_manager = SettingsManager(
                settings_path=Path(settings_path),
                session_id=f"install_{int(time.time())}",
                non_interactive=os.getenv("AMPLIHACK_YES", "0") == "1" or is_uvx,
            )

            # Prompt user for modification (or auto-approve if UVX/non-interactive)
            if not settings_manager.prompt_user_for_modification():
                print("  ⚠️  Settings modification declined by user")
                return False
            if is_uvx:
                print("  🚀 UVX environment detected - auto-configuring hooks")

            # Create backup
            success, backup_path = settings_manager.create_backup()
            if not success:
                # Continue without backup rather than failing
                print("  ⚠️  Could not create backup - continuing anyway")
                backup_path = None
            elif backup_path:
                print(f"  💾 Backup created at {backup_path}")

    except Exception as e:
        # If SettingsManager fails for any reason, continue without it
        print(f"  ⚠️  Settings manager unavailable - continuing without backup: {e}")
        if is_uvx:
            print("  🚀 UVX environment detected - auto-configuring hooks")

    # Load existing settings or use template
    if os.path.exists(settings_path):
        try:
            with open(settings_path, encoding="utf-8") as f:
                settings = json.load(f)
            print("  📋 Found existing settings.json")

            # Back up existing settings
            backup_name = f"settings.json.backup.{int(time.time())}"
            backup_path = os.path.join(CLAUDE_DIR, backup_name)
            shutil.copy2(settings_path, backup_path)
            print(f"  💾 Backed up to {backup_name}")
        except Exception as e:
            print(f"  ⚠️  Could not read existing settings.json: {e}")
            print("  🔧 Creating new settings.json from template")
            settings = SETTINGS_TEMPLATE.copy()
    else:
        print("  🔧 Creating new settings.json")
        settings = SETTINGS_TEMPLATE.copy()

    # Update amplihack hook paths (relative paths for cross-platform compatibility)
    hooks_updated = 0
    amplihack_hooks_rel = ".claude/tools/amplihack/hooks"

    hooks_updated += update_hook_paths(
        settings, "amplihack", HOOK_CONFIGS["amplihack"], amplihack_hooks_rel
    )

    # Update XPIA hook paths if XPIA hooks directory exists
    xpia_hooks_abs = os.path.join(HOME, ".claude", "tools", "xpia", "hooks")
    if os.path.exists(xpia_hooks_abs):
        print("  🔒 XPIA security hooks directory found")

        xpia_hooks_rel = ".claude/tools/xpia/hooks"
        xpia_updated = update_hook_paths(settings, "xpia", HOOK_CONFIGS["xpia"], xpia_hooks_rel)
        hooks_updated += xpia_updated

        if xpia_updated > 0:
            print(f"  🔒 XPIA security hooks configured ({xpia_updated} hooks)")

    # Ensure permissions are set correctly
    if "permissions" not in settings:
        settings["permissions"] = SETTINGS_TEMPLATE["permissions"].copy()
    # Ensure additionalDirectories includes .claude and Specs
    elif "additionalDirectories" not in settings["permissions"]:
        settings["permissions"]["additionalDirectories"] = [".claude", "Specs"]
    else:
        for dir_name in [".claude", "Specs"]:
            if dir_name not in settings["permissions"]["additionalDirectories"]:
                settings["permissions"]["additionalDirectories"].append(dir_name)

    # Write updated settings
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        print(f"  ✅ Settings updated ({hooks_updated} hooks configured)")
        return True
    except Exception as e:
        print(f"  ❌ Failed to write settings.json: {e}")
        return False


__all__ = ["ensure_settings_json", "update_hook_paths", "SETTINGS_TEMPLATE"]
