"""Uninstallation logic for amplihack.

Philosophy:
- Single responsibility: Handle uninstallation of amplihack from ~/.claude
- Self-contained: All uninstallation logic in one place
- Regeneratable: Can be rebuilt from specification

Public API (the "studs"):
    uninstall: Uninstall amplihack components from ~/.claude
    read_manifest: Read manifest file and return files and directories lists
    remove_hooks_from_settings: Remove amplihack hooks from settings.json
"""

import json
import os
import shutil

# Import constants from package root
from . import CLAUDE_DIR, MANIFEST_JSON


def read_manifest() -> tuple[list[str], list[str]]:
    """Read manifest file and return files and directories lists."""
    try:
        with open(MANIFEST_JSON, encoding="utf-8") as f:
            mf = json.load(f)
            return mf.get("files", []), mf.get("dirs", [])
    except (OSError, json.JSONDecodeError):
        return [], []


def remove_hooks_from_settings():
    """Remove amplihack hook entries from ~/.claude/settings.json.

    Scans all hook event types in settings.json and removes entries whose
    command references "amplihack" (covers both Python hook paths like
    tools/amplihack/hooks/*.py and the amplihack-hooks Rust binary).
    Non-amplihack hooks (e.g., user-defined or third-party) are preserved.

    Returns:
        Number of hook entries removed.
    """
    settings_path = os.path.join(CLAUDE_DIR, "settings.json")
    if not os.path.isfile(settings_path):
        return 0

    try:
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
    except (OSError, json.JSONDecodeError):
        return 0

    hooks = settings.get("hooks")
    if not hooks or not isinstance(hooks, dict):
        return 0

    removed_count = 0
    empty_event_types = []

    for event_type, entries in hooks.items():
        if not isinstance(entries, list):
            continue

        cleaned_entries = []
        for entry in entries:
            if not isinstance(entry, dict):
                cleaned_entries.append(entry)
                continue

            hook_list = entry.get("hooks", [])
            if not isinstance(hook_list, list):
                cleaned_entries.append(entry)
                continue

            # Check if ANY hook command in this entry references amplihack
            is_amplihack = False
            for hook in hook_list:
                cmd = hook.get("command", "") if isinstance(hook, dict) else ""
                if "amplihack" in cmd:
                    is_amplihack = True
                    break

            if is_amplihack:
                removed_count += 1
            else:
                cleaned_entries.append(entry)

        hooks[event_type] = cleaned_entries
        if not cleaned_entries:
            empty_event_types.append(event_type)

    # Remove empty event type keys
    for event_type in empty_event_types:
        del hooks[event_type]

    # Remove the hooks key entirely if empty
    if not hooks:
        del settings["hooks"]

    if removed_count > 0:
        try:
            from .settings import write_json_atomic

            write_json_atomic(str(settings_path), settings)
        except OSError as e:
            print(f"  ⚠️  Could not write settings.json: {e}")
            return 0

    return removed_count


def uninstall():
    """Uninstall amplihack components from ~/.claude."""
    removed_any = False
    files, dirs = read_manifest()

    # Remove individual files from manifest
    removed_files = 0
    for f in files:
        target = os.path.join(CLAUDE_DIR, f)
        if os.path.isfile(target):
            try:
                os.remove(target)
                removed_files += 1
                removed_any = True
            except Exception as e:
                print(f"  ⚠️  Could not remove file {f}: {e}")

    # Remove directories from manifest (if any)
    for d in sorted(dirs, key=lambda x: -x.count(os.sep)):
        target = os.path.join(CLAUDE_DIR, d)
        if os.path.isdir(target):
            try:
                shutil.rmtree(target, ignore_errors=True)
                removed_any = True
            except Exception as e:
                print(f"  ⚠️  Could not remove directory {d}: {e}")

    # Always try to remove the main amplihack directories
    # This handles cases where the manifest might not track directories properly
    amplihack_dirs = [
        os.path.join(CLAUDE_DIR, "agents", "amplihack"),
        os.path.join(CLAUDE_DIR, "commands", "amplihack"),
        os.path.join(CLAUDE_DIR, "tools", "amplihack"),
        # Don't remove context, workflow, or runtime as they might be shared
    ]

    removed_dirs = 0
    for dir_path in amplihack_dirs:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                removed_dirs += 1
                removed_any = True
            except Exception as e:
                print(f"  ⚠️  Could not remove {dir_path}: {e}")

    # Remove manifest file
    try:
        os.remove(MANIFEST_JSON)
    except Exception:
        pass

    # Remove amplihack hooks from settings.json
    removed_hooks = remove_hooks_from_settings()
    if removed_hooks > 0:
        removed_any = True

    # Report results
    if removed_any:
        print(f"✅ Uninstalled amplihack from {CLAUDE_DIR}")
        if removed_files > 0:
            print(f"   • Removed {removed_files} files")
        if removed_dirs > 0:
            print(f"   • Removed {removed_dirs} amplihack directories")
        if removed_hooks > 0:
            print(f"   • Removed {removed_hooks} hook entries from settings.json")
    else:
        print("Nothing to uninstall.")


__all__ = ["uninstall", "read_manifest", "remove_hooks_from_settings"]
