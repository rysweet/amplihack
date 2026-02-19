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
                        "command": "$HOME/.amplihack/.claude/tools/amplihack/hooks/session_start.py",
                        "timeout": 10,
                    }
                ]
            }
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "$HOME/.amplihack/.claude/tools/amplihack/hooks/stop.py",
                        "timeout": 120,
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
                        "command": "$HOME/.amplihack/.claude/tools/amplihack/hooks/post_tool_use.py",
                    }
                ],
            }
        ],
        "PreCompact": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "$HOME/.amplihack/.claude/tools/amplihack/hooks/pre_compact.py",
                        "timeout": 30,
                    }
                ]
            }
        ],
    },
}


def validate_hook_paths(hook_system, hooks_to_validate, hooks_dir_path):
    """Validate that all hook files exist before configuration.

    Args:
        hook_system: Name of the hook system (e.g., "amplihack", "xpia")
        hooks_to_validate: List of dicts with keys: type, file, timeout (optional), matcher (optional)
        hooks_dir_path: Absolute path to hooks directory

    Returns:
        Tuple of (all_valid: bool, missing_hooks: list[str])
    """
    missing_hooks = []

    for hook_info in hooks_to_validate:
        hook_file = hook_info["file"]
        hook_path = os.path.join(hooks_dir_path, hook_file)

        expanded_path = os.path.expanduser(os.path.expandvars(hook_path))

        if not os.path.exists(expanded_path):
            missing_hooks.append(f"{hook_system}/{hook_file} (expected at {expanded_path})")

    return (len(missing_hooks) == 0, missing_hooks)


def update_hook_paths(settings, hook_system, hooks_to_update, hooks_dir_path):
    """Update hook paths for a given hook system (amplihack or xpia).

    This function ensures all hook paths in settings.json are absolute paths,
    enabling hooks to work from ANY working directory (cross-codebase functionality).

    Path expansion behavior:
    - Expands ~ (tilde) to user home directory via os.path.expanduser()
    - Expands $VAR and ${VAR} environment variables via os.path.expandvars()
    - Converts relative paths to absolute using os.path.join()

    This is CRITICAL for cross-directory execution:
    - Hooks must work when Claude Code runs from ANY codebase
    - Relative paths would break when working directory changes
    - Absolute paths guarantee hooks are always found

    Args:
        settings: Settings dictionary to update
        hook_system: Name of the hook system (e.g., "amplihack", "xpia")
        hooks_to_update: List of dicts with keys: type, file, timeout (optional), matcher (optional)
        hooks_dir_path: MUST be absolute path to hooks directory after expansion
                       (e.g., "/home/user/.amplihack/.claude/tools/amplihack/hooks")

    Returns:
        Number of hooks updated
    """
    hooks_updated = 0

    for hook_info in hooks_to_update:
        hook_type = hook_info["type"]
        hook_file = hook_info["file"]
        timeout = hook_info.get("timeout")
        matcher = hook_info.get("matcher")

        # CRITICAL: Path expansion ensures cross-directory execution
        # Expand environment variables ($HOME) and user directory (~) to absolute paths
        # This ensures hooks work from ANY working directory (cross-codebase functionality)
        hook_path = os.path.abspath(
            os.path.expanduser(os.path.expandvars(f"{hooks_dir_path}/{hook_file}"))
        )

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
                            # Update hook path only if changed
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

    # Try to use SettingsManager for backup functionality
    try:
        from amplihack.launcher.settings_manager import SettingsManager

        settings_manager = SettingsManager(
            settings_path=Path(settings_path),
            session_id=f"install_{int(time.time())}",
            non_interactive=True,
        )

        success, backup_path = settings_manager.create_backup()
        if success and backup_path:
            print(f"  💾 Backup created at {backup_path}")
        else:
            print("  ⚠️  Could not create backup - continuing anyway")

    except ImportError:
        print("  ⚠️  Settings manager unavailable - continuing without backup")
        if is_uvx:
            print("  🚀 UVX environment detected - auto-configuring hooks")

    # Load existing settings or use template
    if os.path.exists(settings_path):
        try:
            with open(settings_path, encoding="utf-8") as f:
                settings = json.load(f)
            print("  📋 Found existing settings.json")
        except Exception as e:
            print(f"  ⚠️  Could not read existing settings.json: {e}")
            print("  🔧 Creating new settings.json from template")
            settings = SETTINGS_TEMPLATE.copy()
    else:
        print("  🔧 Creating new settings.json")
        settings = SETTINGS_TEMPLATE.copy()

    # Validate amplihack hook paths before configuration
    hooks_updated = 0
    amplihack_hooks_abs = os.path.join(HOME, ".amplihack", ".claude", "tools", "amplihack", "hooks")

    # Validate amplihack hooks exist
    all_valid, missing_hooks = validate_hook_paths(
        "amplihack", HOOK_CONFIGS["amplihack"], amplihack_hooks_abs
    )

    if not all_valid:
        print("  ❌ Hook validation failed - missing required hooks:")
        for missing in missing_hooks:
            print(f"     • {missing}")
        print("  💡 Please reinstall amplihack to restore missing hooks")
        return False

    # Update amplihack hook paths (absolute paths for plugin mode compatibility)
    hooks_updated += update_hook_paths(
        settings, "amplihack", HOOK_CONFIGS["amplihack"], amplihack_hooks_abs
    )

    # Update XPIA hook paths if XPIA hooks directory exists (absolute paths for consistency)
    xpia_hooks_abs = os.path.join(HOME, ".amplihack", ".claude", "tools", "xpia", "hooks")
    if os.path.exists(xpia_hooks_abs):
        print("  🔒 XPIA security hooks directory found")

        # Validate XPIA hooks before configuration
        xpia_valid, xpia_missing = validate_hook_paths("xpia", HOOK_CONFIGS["xpia"], xpia_hooks_abs)

        if not xpia_valid:
            print("  ⚠️  XPIA hook validation failed - missing hooks:")
            for missing in xpia_missing:
                print(f"     • {missing}")
            print("  ⚠️  Skipping XPIA configuration - install XPIA properly to enable")
        else:
            xpia_updated = update_hook_paths(settings, "xpia", HOOK_CONFIGS["xpia"], xpia_hooks_abs)
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


__all__ = ["ensure_settings_json", "update_hook_paths", "validate_hook_paths", "SETTINGS_TEMPLATE"]
