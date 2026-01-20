"""Installation logic for amplihack.

Philosophy:
- Single responsibility: Handle installation of amplihack to ~/.claude
- Self-contained: All installation logic in one place
- Regeneratable: Can be rebuilt from specification

Public API (the "studs"):
    copytree_manifest: Copy essential directories with optional profile filtering
    create_runtime_dirs: Create runtime directories for logs, metrics, etc.
    _local_install: Main installation entry point
    ensure_dirs: Ensure base Claude directory exists
"""

import json
import os
import shutil
import stat
import sys
from pathlib import Path

# Import constants from package root
from . import (
    CLAUDE_DIR,
    ESSENTIAL_DIRS,
    ESSENTIAL_FILES,
    MANIFEST_JSON,
    RUNTIME_DIRS,
)


def ensure_dirs() -> None:
    """Ensure that the Claude directory exists.

    Creates the CLAUDE_DIR directory if it doesn't exist, including any
    necessary parent directories.
    """
    os.makedirs(CLAUDE_DIR, exist_ok=True)


def copytree_manifest(
    repo_root: str, dst: str, rel_top: str = ".claude", manifest=None
) -> list[str]:
    """Copy all essential directories from repo to destination.

    Args:
        repo_root: Path to the repository root or package directory
        dst: Destination directory (usually ~/.claude)
        rel_top: Relative path to .claude directory
        manifest: Optional StagingManifest for profile-based filtering

    Returns:
        List of copied directory paths relative to dst
    """
    # Try two essential locations only:
    # 1. Direct path (package or repo root)
    # 2. Parent directory (for src/amplihack case)

    direct_path = os.path.join(repo_root, rel_top)
    parent_path = os.path.join(repo_root, "..", rel_top)

    if os.path.exists(direct_path):
        base = direct_path
    elif os.path.exists(parent_path):
        base = parent_path
    else:
        print(f"  ❌ .claude not found at {direct_path} or {parent_path}")
        return []

    copied = []

    # Use manifest dirs if provided, otherwise use ESSENTIAL_DIRS
    dirs_to_copy = manifest.dirs_to_stage if manifest else ESSENTIAL_DIRS
    file_filter = manifest.file_filter if manifest else None

    for dir_path in dirs_to_copy:
        source_dir = os.path.join(base, dir_path)

        # Skip if source doesn't exist
        if not os.path.exists(source_dir):
            print(f"  ⚠️  Warning: {dir_path} not found in source, skipping")
            continue

        target_dir = os.path.join(dst, dir_path)

        # Create parent directories if needed
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)

        # Remove existing target if it exists
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)

        # Copy the directory with optional file filtering
        try:
            # If file_filter is provided, use it to filter which files to copy
            if file_filter:

                def ignore_function(directory, contents):
                    """Filter function for shutil.copytree to skip files based on profile.

                    Error handling at system boundary: Catches any errors from file_filter
                    and fails open (includes file on error).
                    """
                    ignored = []
                    for item in contents:
                        item_path = Path(directory) / item
                        # Skip files that don't pass the filter
                        if item_path.is_file():
                            try:
                                # Call file_filter - errors handled here at boundary
                                should_copy = file_filter(item_path)
                                if not should_copy:
                                    ignored.append(item)
                            except Exception:
                                # Fail-open: Include file on any error
                                pass
                    return ignored

                shutil.copytree(source_dir, target_dir, dirs_exist_ok=True, ignore=ignore_function)
            else:
                shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)

            # Fix: Set execute permissions on hook Python files
            # This fixes the "Permission denied" error when hooks are copied
            # to other directories (e.g., project .claude dirs)
            if dir_path.startswith("tools/"):
                # Skip on Windows - uses different permission model
                if sys.platform == "win32":
                    print("  ℹ️  Skipping POSIX permissions on Windows")
                else:
                    files_updated = 0
                    permission_errors = 0

                    # Don't follow symlinks for security
                    for root, _dirs, files in os.walk(target_dir, followlinks=False):
                        # Match exact hooks directory name (not just substring)
                        if os.path.basename(root) == "hooks":
                            for file in files:
                                if file.endswith(".py"):
                                    file_path = os.path.join(root, file)
                                    try:
                                        current_perms = os.stat(file_path).st_mode
                                        # User and group only (more secure than user+group+other)
                                        new_perms = current_perms | stat.S_IXUSR | stat.S_IXGRP
                                        os.chmod(file_path, new_perms)
                                        files_updated += 1
                                    except (OSError, PermissionError) as e:
                                        permission_errors += 1
                                        print(f"  ⚠️  Could not chmod {file}: {e}")

                    if files_updated > 0:
                        print(f"  🔐 Set execute permissions on {files_updated} hook files")
                    if permission_errors > 0:
                        print(f"  ⚠️  {permission_errors} permission errors (hooks may not execute)")

            copied.append(dir_path)
            print(f"  ✅ Copied {dir_path}")
        except Exception as e:
            print(f"  ❌ Failed to copy {dir_path}: {e}")

    # Also copy settings.json if it exists and target doesn't have one
    settings_src = os.path.join(base, "settings.json")
    settings_dst = os.path.join(dst, "settings.json")

    if os.path.exists(settings_src) and not os.path.exists(settings_dst):
        try:
            shutil.copy2(settings_src, settings_dst)
            print("  ✅ Copied settings.json")
        except Exception as e:
            print(f"  ⚠️  Could not copy settings.json: {e}")

    # Copy essential files (like statusline.sh)
    for file_path in ESSENTIAL_FILES:
        # Skip CLAUDE.md - handled separately with preservation logic (Issue #1746)
        if file_path == "../CLAUDE.md":
            continue

        source_file = os.path.join(base, file_path)
        target_file = os.path.join(dst, file_path)

        if not os.path.exists(source_file):
            print(f"  ⚠️  Warning: {file_path} not found in source, skipping")
            continue

        # Create parent directory if needed
        os.makedirs(os.path.dirname(target_file), exist_ok=True)

        try:
            shutil.copy2(source_file, target_file)
            # Set execute permission for shell scripts
            if file_path.endswith(".sh") and sys.platform != "win32":
                current_perms = os.stat(target_file).st_mode
                new_perms = current_perms | stat.S_IXUSR | stat.S_IXGRP
                os.chmod(target_file, new_perms)
            print(f"  ✅ Copied {file_path}")
            copied.append(file_path)
        except Exception as e:
            print(f"  ⚠️  Could not copy {file_path}: {e}")

    # Handle CLAUDE.md separately with preservation logic (Issue #1746)
    try:
        from .utils.claude_md_preserver import HandleMode, handle_claude_md

        source_claude = os.path.join(base, "..", "CLAUDE.md")
        if os.path.exists(source_claude):
            result = handle_claude_md(
                source_claude=Path(source_claude),
                target_dir=Path(dst).parent,  # dst is .claude/, we want parent (project root)
                mode=HandleMode.AUTO,
            )
            if result.success:
                print(f"  ✅ {result.message}")
                if result.backup_path:
                    print(f"     💾 Backup: {result.backup_path}")
                copied.append("CLAUDE.md")
            else:
                print(f"  ⚠️  {result.message}")
    except Exception as e:
        print(f"  ⚠️  Could not handle CLAUDE.md: {e}")

    return copied


def create_runtime_dirs():
    """Create necessary runtime directories."""
    for dir_path in RUNTIME_DIRS:
        full_path = os.path.join(CLAUDE_DIR, dir_path)
        try:
            os.makedirs(full_path, exist_ok=True)
            if not os.path.exists(full_path):
                print(f"  ❌ Failed to create {dir_path}")
            else:
                print(f"  ✅ Runtime directory {dir_path} ready")
        except Exception as e:
            print(f"  ❌ Error creating {dir_path}: {e}")


def all_rel_dirs(base: str) -> set[str]:
    """Get all relative directory paths from base directory."""
    result = set()
    for r, dirs, _files in os.walk(base):
        rel = os.path.relpath(r, CLAUDE_DIR)
        result.add(rel)
    return result


def get_all_files_and_dirs(root_dirs: list[str]) -> tuple[list[str], list[str]]:
    """Get all files and directories from root directories.

    Args:
        root_dirs: List of root directory paths to scan

    Returns:
        Tuple of (sorted file paths, sorted directory paths)
    """
    all_files = []
    all_dirs = set()
    for d in root_dirs:
        if not os.path.exists(d):
            continue
        for r, dirs, files in os.walk(d):
            rel_dir = os.path.relpath(r, CLAUDE_DIR)
            all_dirs.add(rel_dir)
            for f in files:
                rel_path = os.path.relpath(os.path.join(r, f), CLAUDE_DIR)
                all_files.append(rel_path)
    return sorted(all_files), sorted(all_dirs)


def write_manifest(files: list[str], dirs: list[str]) -> None:
    """Write manifest file with list of files and directories."""
    os.makedirs(os.path.dirname(MANIFEST_JSON), exist_ok=True)
    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump({"files": files, "dirs": dirs}, f, indent=2)


def _local_install(repo_root, profile_uri=None):
    """Install amplihack files from the given repo_root directory.

    This provides a comprehensive installation that mirrors the shell script.

    Args:
        repo_root: Path to the repository root or package directory
        profile_uri: Optional profile URI to use for filtering (None = use configured profile)
    """
    print("\n🚀 Starting amplihack installation...")
    print(f"   Source: {repo_root}")
    print(f"   Target: {CLAUDE_DIR}\n")

    # CRITICAL: Detect self-modification risk BEFORE copying files
    # Inline detection (can't import nesting_detector - not installed yet)
    is_auto_mode = "--auto" in sys.argv
    is_source_repo = False

    # Check if we're in amplihack source repo
    pyproject_path = os.path.join(os.getcwd(), "pyproject.toml")
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, 'r') as f:
                content = f.read()
                is_source_repo = 'name = "amplihack"' in content
        except Exception:
            pass

    # If auto-mode in source repo, skip installation (protection already staged .claude/)
    if is_auto_mode and is_source_repo:
        print("🛡️  Self-modification protection: Skipping .claude/ installation")
        print("   (Running in amplihack source - .claude/ already staged to temp)\n")
        return

    # NEW: Create staging manifest based on profile
    try:
        # Import staging module from source repo during installation
        # Find .claude directory in repo_root
        direct_path = os.path.join(repo_root, ".claude")
        parent_path = os.path.join(repo_root, "..", ".claude")

        if os.path.exists(direct_path):
            claude_source = direct_path
        elif os.path.exists(parent_path):
            claude_source = parent_path
        else:
            raise ImportError("Cannot find .claude directory in source repo")

        # Add tools/amplihack directory to sys.path temporarily
        profile_mgmt_dir = os.path.join(claude_source, "tools", "amplihack")
        if profile_mgmt_dir not in sys.path:
            sys.path.insert(0, profile_mgmt_dir)

        # Now import staging module (from tools/amplihack/)
        from profile_management.staging import (
            create_staging_manifest,  # type: ignore[import-not-found]
        )

        manifest = create_staging_manifest(ESSENTIAL_DIRS, profile_uri)

        if manifest.profile_name != "all" and not manifest.profile_name.endswith("(fallback)"):
            print(f"📦 Using profile: {manifest.profile_name}\n")
    except Exception as e:
        # If profile management isn't available, use full installation
        print(f"ℹ️  Profile management unavailable ({e}), using full installation\n")
        from collections.abc import Callable
        from dataclasses import dataclass

        @dataclass
        class StagingManifest:
            dirs_to_stage: list[str]
            file_filter: Callable | None
            profile_name: str

        manifest = StagingManifest(
            dirs_to_stage=ESSENTIAL_DIRS, file_filter=None, profile_name="all"
        )

    # Step 1: Ensure base directory exists
    ensure_dirs()

    # Step 2: Track existing directories for manifest
    pre_dirs = all_rel_dirs(CLAUDE_DIR)

    # Step 3: Copy all essential directories (filtered by profile)
    print("📁 Copying essential directories:")
    copied_dirs = copytree_manifest(repo_root, CLAUDE_DIR, manifest=manifest)

    if not copied_dirs:
        print("\n❌ No directories were copied. Installation may be incomplete.")
        print("   Please check that the source repository is valid.\n")
        return

    # Step 3.5: Smart PROJECT.md initialization
    print("\n📝 Initializing PROJECT.md:")
    try:
        from .utils.project_initializer import InitMode, initialize_project_md

        # Use FORCE mode during installation to fix amplihack-describing PROJECT.md
        result = initialize_project_md(Path(CLAUDE_DIR).parent, mode=InitMode.FORCE)

        if result.success:
            if result.action_taken.value in ["initialized", "regenerated"]:
                print(f"   ✅ PROJECT.md {result.action_taken.value} using {result.method.value}")
            elif result.action_taken.value == "offered":
                print(f"   ℹ️  {result.message}")
            else:
                print("   ✅ PROJECT.md valid (skipped)")
        else:
            print(f"   ⚠️  {result.message}")
    except Exception as e:
        print(f"   ⚠️  PROJECT.md initialization failed: {e}")

    # Step 4: Create runtime directories
    print("\n📂 Creating runtime directories:")
    create_runtime_dirs()

    # Step 5: Configure settings.json
    print("\n⚙️  Configuring settings.json:")
    from .settings import ensure_settings_json

    settings_ok = ensure_settings_json()

    # Step 6: Verify hook files exist
    print("\n🔍 Verifying hook files:")
    from .hook_verification import verify_hooks  # type: ignore[attr-defined]

    hooks_ok = verify_hooks()

    # Step 7: Generate manifest for uninstall
    print("\n📝 Generating uninstall manifest:")

    # Build list of all directories to track
    all_essential = []
    for dir_path in ESSENTIAL_DIRS:
        full_path = os.path.join(CLAUDE_DIR, dir_path)
        if os.path.exists(full_path):
            all_essential.append(full_path)

    # Also track runtime dirs that were created
    for dir_path in RUNTIME_DIRS:
        full_path = os.path.join(CLAUDE_DIR, dir_path)
        if os.path.exists(full_path):
            all_essential.append(full_path)

    files, post_dirs = get_all_files_and_dirs(all_essential)
    new_dirs = sorted(set(post_dirs) - pre_dirs)
    write_manifest(files, new_dirs)
    print(f"   Manifest written to {MANIFEST_JSON}")

    # Step 8: Final summary
    print("\n" + "=" * 60)
    if settings_ok and hooks_ok and len(copied_dirs) > 0:
        print("✅ Amplihack installation completed successfully!")
        print(f"\n📍 Installed to: {CLAUDE_DIR}")
        print("\n📦 Components installed:")
        for dir_path in sorted(copied_dirs):
            print(f"   • {dir_path}")
        print("\n🎯 Features enabled:")
        print("   • Session start hook")
        print("   • Stop hook")
        print("   • Post-tool-use hook")
        print("   • Pre-compact hook")
        print("   • Runtime logging and metrics")
        print("\n💡 To uninstall: amplihack uninstall")
    else:
        print("⚠️  Installation completed with warnings")
        if not settings_ok:
            print("   • Settings.json configuration had issues")
        if not hooks_ok:
            print("   • Some hook files are missing")
        if len(copied_dirs) == 0:
            print("   • No directories were copied")
        print("\n💡 You may need to manually verify the installation")
    print("=" * 60 + "\n")


__all__ = [
    "copytree_manifest",
    "create_runtime_dirs",
    "_local_install",
    "ensure_dirs",
    "get_all_files_and_dirs",
    "write_manifest",
]
