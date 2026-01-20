"""Uninstallation logic for amplihack.

Philosophy:
- Single responsibility: Handle uninstallation of amplihack from ~/.claude
- Self-contained: All uninstallation logic in one place
- Regeneratable: Can be rebuilt from specification

Public API (the "studs"):
    uninstall: Uninstall amplihack components from ~/.claude
    read_manifest: Read manifest file and return files and directories lists
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

    # Report results
    if removed_any:
        print(f"✅ Uninstalled amplihack from {CLAUDE_DIR}")
        if removed_files > 0:
            print(f"   • Removed {removed_files} files")
        if removed_dirs > 0:
            print(f"   • Removed {removed_dirs} amplihack directories")
    else:
        print("Nothing to uninstall.")


__all__ = ["uninstall", "read_manifest"]
