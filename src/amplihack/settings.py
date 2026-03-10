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
import shlex
import shutil
import sys
import time
from pathlib import Path

# Import constants from package root
from . import CLAUDE_DIR, HOME, HOOK_CONFIGS, RUST_HOOK_MAP

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
        "PreToolUse": [
            {
                "matcher": "*",
                "hooks": [
                    {
                        "type": "command",
                        "command": "$HOME/.amplihack/.claude/tools/amplihack/hooks/pre_tool_use.py",
                    }
                ],
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
        "UserPromptSubmit": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "$HOME/.amplihack/.claude/tools/amplihack/hooks/workflow_classification_reminder.py",
                        "timeout": 5,
                    }
                ]
            },
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "$HOME/.amplihack/.claude/tools/amplihack/hooks/user_prompt_submit.py",
                        "timeout": 10,
                    }
                ]
            },
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


def find_rust_hook_binary():
    """Locate the amplihack-hooks Rust binary.

    Search order:
    1. PATH (via shutil.which)
    2. ~/.amplihack/bin/amplihack-hooks
    3. ~/.cargo/bin/amplihack-hooks

    Returns:
        Absolute path to the binary, or None if not found.
    """
    # 1. Check PATH
    on_path = shutil.which("amplihack-hooks")
    if on_path:
        return os.path.abspath(on_path)

    # 2. Check ~/.amplihack/bin/
    amplihack_bin = os.path.expanduser("~/.amplihack/bin/amplihack-hooks")
    if os.path.isfile(amplihack_bin) and os.access(amplihack_bin, os.X_OK):
        return os.path.abspath(amplihack_bin)

    # 3. Check ~/.cargo/bin/
    cargo_bin = os.path.expanduser("~/.cargo/bin/amplihack-hooks")
    if os.path.isfile(cargo_bin) and os.access(cargo_bin, os.X_OK):
        return os.path.abspath(cargo_bin)

    return None


def get_hook_engine():
    """Get the configured hook engine.

    Returns "rust" or "python" based on AMPLIHACK_HOOK_ENGINE env var.
    Default is "python" when unset.
    """
    engine = os.environ.get("AMPLIHACK_HOOK_ENGINE", "python").lower()
    if engine not in ("python", "rust"):
        print(f"  ⚠️  Unknown AMPLIHACK_HOOK_ENGINE={engine!r}, using 'python'", file=sys.stderr)
        return "python"
    return engine


def update_hook_paths(settings, hook_system, hooks_to_update, hooks_dir_path,
                     hook_engine=None):
    """Update hook paths for a given hook system (amplihack or xpia).

    This function ensures all hook paths in settings.json are absolute paths,
    enabling hooks to work from ANY working directory (cross-codebase functionality).

    When hook_engine is "rust" and the hook has a Rust equivalent (per RUST_HOOK_MAP),
    the command is set to the Rust multicall binary: ``<binary_path> <subcommand>``.
    Hooks without a Rust equivalent (e.g., workflow_classification_reminder.py) still
    use Python. If the Rust binary is not found, raises FileNotFoundError (NO fallback).

    Args:
        settings: Settings dictionary to update
        hook_system: Name of the hook system (e.g., "amplihack", "xpia")
        hooks_to_update: List of dicts with keys: type, file, timeout (optional), matcher (optional)
        hooks_dir_path: MUST be absolute path to hooks directory after expansion
                       (e.g., "/home/user/.amplihack/.claude/tools/amplihack/hooks")
        hook_engine: "rust" or "python" (default: from AMPLIHACK_HOOK_ENGINE env var)

    Returns:
        Number of hooks updated

    Raises:
        FileNotFoundError: If hook_engine is "rust" but amplihack-hooks binary not found
    """
    if hook_engine is None:
        hook_engine = get_hook_engine()

    rust_binary = None
    if hook_engine == "rust":
        rust_binary = find_rust_hook_binary()
        if rust_binary is None:
            raise FileNotFoundError(
                "AMPLIHACK_HOOK_ENGINE=rust but amplihack-hooks binary not found. "
                "Install it from https://github.com/rysweet/amplihack-rs or set "
                "AMPLIHACK_HOOK_ENGINE=python."
            )

    hooks_updated = 0

    for hook_info in hooks_to_update:
        hook_type = hook_info["type"]
        hook_file = hook_info["file"]
        timeout = hook_info.get("timeout")
        matcher = hook_info.get("matcher")

        # Determine the hook command based on engine
        rust_subcommand = RUST_HOOK_MAP.get(hook_file) if hook_engine == "rust" else None

        if rust_subcommand and rust_binary:
            hook_path = f"{shlex.quote(rust_binary)} {rust_subcommand}"
        else:
            # Python engine (or hook has no Rust equivalent)
            hook_path = os.path.abspath(
                os.path.expanduser(os.path.expandvars(f"{hooks_dir_path}/{hook_file}"))
            )

        if "hooks" not in settings:
            settings["hooks"] = {}

        # Build the hook config entry
        hook_config = {
            "type": "command",
            "command": hook_path,
        }
        if timeout:
            hook_config["timeout"] = timeout

        wrapper = (
            {"matcher": matcher, "hooks": [hook_config]} if matcher else {"hooks": [hook_config]}
        )

        if hook_type not in settings["hooks"]:
            # New hook type — add it
            settings["hooks"][hook_type] = [wrapper]
            hooks_updated += 1
        else:
            # Hook type exists — check if THIS specific file is already present
            # Match by both basename AND system directory to prevent cross-system overwrites
            found = False
            hook_configs = settings["hooks"][hook_type]
            for config in hook_configs:
                if "hooks" in config:
                    for hook in config["hooks"]:
                        cmd = hook.get("command", "")
                        # Match: same basename AND same system ownership
                        if os.path.basename(cmd) == hook_file and hook_system in cmd:
                            found = True
                            if cmd != hook_path:
                                hook["command"] = hook_path
                                if timeout and "timeout" not in hook:
                                    hook["timeout"] = timeout
                                hooks_updated += 1
                                print(f"  🔄 Updated {hook_type} hook path")
                            break
                        # Also match Rust commands being replaced (engine switch)
                        elif "amplihack-hooks" in cmd:
                            rust_subcmd = RUST_HOOK_MAP.get(hook_file)
                            if rust_subcmd and rust_subcmd in cmd:
                                found = True
                                if cmd != hook_path:
                                    hook["command"] = hook_path
                                    if timeout and "timeout" not in hook:
                                        hook["timeout"] = timeout
                                    hooks_updated += 1
                                    print(f"  🔄 Updated {hook_type} hook path")
                                break
                if found:
                    break

            if not found:
                # This hook file is not yet configured — append it
                settings["hooks"][hook_type].append(wrapper)
                hooks_updated += 1

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
    try:
        hooks_updated += update_hook_paths(
            settings, "amplihack", HOOK_CONFIGS["amplihack"], amplihack_hooks_abs
        )
    except FileNotFoundError as e:
        print(f"  ❌ {e}", file=sys.stderr)
        return False

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
