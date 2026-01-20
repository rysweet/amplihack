import json
import os
import shutil
from pathlib import Path

HOME = str(Path.home())
CLAUDE_DIR = os.path.join(HOME, ".claude")
CLI_NAME = "amplihack_cli.py"
CLI_SRC = os.path.abspath(__file__)

MANIFEST_JSON = os.path.join(CLAUDE_DIR, "install", "amplihack-manifest.json")

# Essential directories that must be copied during installation
ESSENTIAL_DIRS = [
    "agents/amplihack",  # Specialized agents
    "commands/amplihack",  # Slash commands
    "tools/amplihack",  # Hooks and utilities
    "tools/xpia",  # XPIA security hooks (Issue #458)
    "context",  # Philosophy, patterns, project info
    "workflow",  # DEFAULT_WORKFLOW.md
    "skills",  # Claude Code Skills (12 production skills)
    "templates",  # Investigation & architecture doc templates
    "scenarios",  # Production scenario tools
    "docs",  # Investigation examples and documentation
    "schemas",  # JSON/YAML schemas for validation
    "config",  # Configuration files for tools
    "../.claude-plugin",  # Plugin manifest directory (Issue #1948)
]

# Essential files that must be copied (relative to .claude/)
ESSENTIAL_FILES = [
    "tools/statusline.sh",  # StatusLine script for Claude Code status bar
    "../CLAUDE.md",  # Root-level CLAUDE.md (Issue #1746)
    "AMPLIHACK.md",  # Framework instructions at .claude/AMPLIHACK.md (Issue #1948)
]

# Runtime directories that need to be created
RUNTIME_DIRS = [
    "runtime",
    "runtime/logs",
    "runtime/metrics",
    "runtime/security",
    "runtime/analysis",
]

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

# Hook configurations for amplihack and xpia systems
HOOK_CONFIGS = {
    "amplihack": [
        {"type": "SessionStart", "file": "session_start.py", "timeout": 10000},
        {"type": "Stop", "file": "stop.py", "timeout": 30000},
        {"type": "PostToolUse", "file": "post_tool_use.py", "matcher": "*"},
        {"type": "PreCompact", "file": "pre_compact.py", "timeout": 30000},
    ],
    "xpia": [
        {"type": "SessionStart", "file": "session_start.py", "timeout": 10000},
        {"type": "PostToolUse", "file": "post_tool_use.py", "matcher": "*"},
        {"type": "PreToolUse", "file": "pre_tool_use.py", "matcher": "*"},
    ],
}


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
                import stat
                import sys

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
                import stat

                current_perms = os.stat(target_file).st_mode
                new_perms = current_perms | stat.S_IXUSR | stat.S_IXGRP
                os.chmod(target_file, new_perms)
            print(f"  ✅ Copied {file_path}")
            copied.append(file_path)
        except Exception as e:
            print(f"  ⚠️  Could not copy {file_path}: {e}")

    # Handle CLAUDE.md separately with preservation logic (Issue #1746)
    from pathlib import Path

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


def write_manifest(files: list[str], dirs: list[str]) -> None:
    """Write manifest file with list of files and directories."""
    os.makedirs(os.path.dirname(MANIFEST_JSON), exist_ok=True)
    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump({"files": files, "dirs": dirs}, f, indent=2)


def read_manifest() -> tuple[list[str], list[str]]:
    """Read manifest file and return files and directories lists."""
    try:
        with open(MANIFEST_JSON, encoding="utf-8") as f:
            mf = json.load(f)
            return mf.get("files", []), mf.get("dirs", [])
    except (OSError, json.JSONDecodeError):
        return [], []


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


def all_rel_dirs(base: str) -> set[str]:
    """Get all relative directory paths from base directory."""
    result = set()
    for r, dirs, _files in os.walk(base):
        rel = os.path.relpath(r, CLAUDE_DIR)
        result.add(rel)
    return result


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
    import sys

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
                import sys

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
                session_id=f"install_{int(__import__('time').time())}",
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
            import time

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


def verify_hooks():
    """Verify that all hook files exist."""
    all_exist = True

    for hook_system, hooks in HOOK_CONFIGS.items():
        hooks_dir = os.path.join(CLAUDE_DIR, "tools", hook_system, "hooks")

        # Skip XPIA if directory doesn't exist (optional feature)
        if hook_system == "xpia" and not os.path.exists(hooks_dir):
            print("  ℹ️  XPIA security hooks not installed (optional feature)")
            continue

        # Print header with appropriate icon
        icon = "🔒" if hook_system == "xpia" else "📋"
        print(f"  {icon} {hook_system.capitalize()} hooks:")

        system_all_exist = True
        for hook_info in hooks:
            hook_file = hook_info["file"]
            hook_path = os.path.join(hooks_dir, hook_file)
            if os.path.exists(hook_path):
                print(f"    ✅ {hook_file} found")
            else:
                print(f"    ❌ {hook_file} missing")
                system_all_exist = False

        # Only mark all_exist as False if amplihack hooks are missing
        if hook_system == "amplihack" and not system_all_exist:
            all_exist = False

        # Additional message for XPIA if all hooks found
        if hook_system == "xpia" and system_all_exist:
            print("  🔒 XPIA security hooks configured")

    return all_exist


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


def _local_install(repo_root, profile_uri=None):
    """
    Install amplihack files from the given repo_root directory.
    This provides a comprehensive installation that mirrors the shell script.

    Args:
        repo_root: Path to the repository root or package directory
        profile_uri: Optional profile URI to use for filtering (None = use configured profile)
    """
    print("\n🚀 Starting amplihack installation...")
    print(f"   Source: {repo_root}")
    print(f"   Target: {CLAUDE_DIR}\n")

    # NEW: Create staging manifest based on profile
    try:
        # Import staging module from source repo during installation
        import sys

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
        from profile_management.staging import create_staging_manifest

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
    settings_ok = ensure_settings_json()

    # Step 6: Verify hook files exist
    print("\n🔍 Verifying hook files:")
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


def filecmp(f1, f2):
    try:
        if os.path.getsize(f1) != os.path.getsize(f2):
            return False
        with open(f1, "rb") as file1, open(f2, "rb") as file2:
            return file1.read() == file2.read()
    except Exception:
        return False


def main():
    # Import and use the enhanced CLI
    from .cli import main as cli_main

    return cli_main()
