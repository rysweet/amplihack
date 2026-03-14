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
import tempfile
import time
from pathlib import Path

# Import constants from package root
from . import CLAUDE_DIR, HOME, HOOK_CONFIGS, RUST_HOOK_MAP


def write_json_atomic(path, data, indent=2):
    """Write JSON data to a file atomically to prevent data loss on crash.

    Uses write-to-tempfile + fsync + os.replace pattern:
    1. Writes to a temporary file in the same directory
    2. Calls os.fsync() to ensure data is flushed to disk
    3. Uses os.replace() to atomically swap the temp file into place

    Args:
        path: File path (str or Path) to write to
        data: JSON-serializable data
        indent: JSON indentation level (default 2)

    Raises:
        OSError: If the write or rename fails
        TypeError: If data is not JSON-serializable
    """
    path = str(path)
    dir_name = os.path.dirname(path) or "."

    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp", prefix=".settings_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd = None  # os.fdopen takes ownership of the fd
            json.dump(data, f, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
        tmp_path = None  # rename succeeded, don't clean up
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


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


def _strip_managed_hooks(hooks_dict):
    """Remove amplihack/xpia-managed hook entries, preserving user-added hooks.

    Identifies managed hooks by checking if the command path contains
    'tools/amplihack/' or 'tools/xpia/' or unexpanded '$HOME' references.

    Args:
        hooks_dict: The hooks section of settings.json

    Returns:
        Cleaned hooks dict with only non-managed entries retained
    """
    managed_markers = ("tools/amplihack/", "tools/xpia/", "$HOME/.amplihack/")
    cleaned = {}

    for hook_type, hook_configs in hooks_dict.items():
        kept = []
        for config in hook_configs:
            is_managed = False
            for hook in config.get("hooks", []):
                cmd = hook.get("command", "")
                if any(marker in cmd for marker in managed_markers):
                    is_managed = True
                    break
            if not is_managed:
                kept.append(config)
        if kept:
            cleaned[hook_type] = kept

    return cleaned


def _filter_existing_hooks(hooks_list, hooks_dir_path):
    """Filter hook configs to only those whose files exist on disk.

    Args:
        hooks_list: List of hook config dicts with 'file' key
        hooks_dir_path: Absolute path to hooks directory

    Returns:
        List of hook configs where the referenced file exists
    """
    existing = []
    for hook_info in hooks_list:
        hook_file = hook_info["file"]
        hook_path = os.path.join(hooks_dir_path, hook_file)
        expanded_path = os.path.expanduser(os.path.expandvars(hook_path))
        if os.path.exists(expanded_path):
            existing.append(hook_info)
    return existing


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
    2. ~/.amplihack/.claude/bin/amplihack-hooks
    3. ~/.amplihack/bin/amplihack-hooks (legacy)
    4. ~/.cargo/bin/amplihack-hooks

    Returns:
        Absolute path to the binary, or None if not found.
    """
    candidates = [
        shutil.which("amplihack-hooks"),
        os.path.expanduser("~/.amplihack/.claude/bin/amplihack-hooks"),
        os.path.expanduser("~/.amplihack/bin/amplihack-hooks"),
        os.path.expanduser("~/.cargo/bin/amplihack-hooks"),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return os.path.abspath(candidate)

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


def update_hook_paths(settings, hook_system, hooks_to_update, hooks_dir_path, hook_engine=None):
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
                        if os.path.basename(cmd) == hook_file and f"tools/{hook_system}/" in cmd:
                            found = True
                            if cmd != hook_path:
                                hook["command"] = hook_path
                                if timeout and "timeout" not in hook:
                                    hook["timeout"] = timeout
                                hooks_updated += 1
                                print(f"  🔄 Updated {hook_type} hook path")
                            break
                        # Also match Rust commands being replaced (engine switch)
                        if "amplihack-hooks" in cmd:
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
    has_missing_hooks = False
    amplihack_hooks_abs = os.path.join(HOME, ".amplihack", ".claude", "tools", "amplihack", "hooks")

    # Validate amplihack hooks exist
    all_valid, missing_hooks = validate_hook_paths(
        "amplihack", HOOK_CONFIGS["amplihack"], amplihack_hooks_abs
    )

    if not all_valid:
        has_missing_hooks = True
        print("  ⚠️  Some hook files are missing:")
        for missing in missing_hooks:
            print(f"     • {missing}")
        print("  💡 Missing hooks will be skipped - reinstall amplihack to restore them")

    # Filter hooks to only those whose files actually exist on disk
    valid_amplihack_hooks = _filter_existing_hooks(HOOK_CONFIGS["amplihack"], amplihack_hooks_abs)

    # Clear stale amplihack/xpia hook entries before writing valid ones.
    # When settings were loaded from SETTINGS_TEMPLATE, the hooks dict contains
    # entries with unexpanded $HOME paths that don't point to real files.
    # Remove only amplihack/xpia-owned hooks; preserve any user-added custom hooks.
    if "hooks" in settings:
        settings["hooks"] = _strip_managed_hooks(settings["hooks"])
    else:
        settings["hooks"] = {}

    if not valid_amplihack_hooks:
        print("  ❌ No valid amplihack hook files found on disk")
        print("  💡 Please reinstall amplihack to restore missing hooks")
        return False
    else:
        # Update amplihack hook paths (absolute paths for plugin mode compatibility)
        # Only configure hooks whose files exist on disk
        try:
            hooks_updated += update_hook_paths(
                settings, "amplihack", valid_amplihack_hooks, amplihack_hooks_abs
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
            has_missing_hooks = True
            print("  ⚠️  Some XPIA hook files are missing:")
            for missing in xpia_missing:
                print(f"     • {missing}")
            print("  ⚠️  Missing XPIA hooks will be skipped")

        # Filter to only existing XPIA hooks and configure them
        valid_xpia_hooks = _filter_existing_hooks(HOOK_CONFIGS["xpia"], xpia_hooks_abs)
        if valid_xpia_hooks:
            xpia_updated = update_hook_paths(settings, "xpia", valid_xpia_hooks, xpia_hooks_abs)
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

    # Write updated settings atomically to prevent data loss on crash
    try:
        write_json_atomic(settings_path, settings)
        print(f"  ✅ Settings updated ({hooks_updated} hooks configured)")
        return True
    except Exception as e:
        print(f"  ❌ Failed to write settings.json: {e}")
        return False


__all__ = [
    "ensure_settings_json",
    "update_hook_paths",
    "validate_hook_paths",
    "write_json_atomic",
    "SETTINGS_TEMPLATE",
]
