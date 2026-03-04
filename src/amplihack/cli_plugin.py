"""Plugin installation, marketplace configuration, and UVX plugin helpers.

This module handles Claude Code plugin setup, marketplace registration,
CLI readiness verification, and UVX plugin argument injection.

Public API:
    add_plugin_args_for_uvx: Add --plugin-dir and --add-dir arguments for UVX
    configure_amplihack_marketplace: Configure marketplace in Claude Code settings
    fallback_to_directory_copy: Copy .claude directory to ~/.amplihack/.claude/
    verify_claude_cli_ready: Verify Claude CLI is ready after installation
    debug_print: Print debug message if AMPLIHACK_DEBUG is enabled
"""

import json
import logging
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from .utils import is_uvx_deployment

logger = logging.getLogger(__name__)


def debug_print(message: str) -> None:
    """Print debug message if AMPLIHACK_DEBUG is enabled.

    Args:
        message: Debug message to print
    """
    if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
        print(message)


def verify_claude_cli_ready(
    claude_path: str, max_retries: int = 3, retry_delay: float = 0.5
) -> bool:
    """Verify Claude CLI is ready to use after installation.

    On first install, the binary might need a moment to be fully available.
    This function validates the binary is executable and working.

    Args:
        claude_path: Path to Claude CLI binary
        max_retries: Maximum number of verification attempts
        retry_delay: Delay in seconds between retries

    Returns:
        True if Claude CLI is ready, False otherwise
    """
    from .utils.prerequisites import safe_subprocess_call

    for attempt in range(max_retries):
        try:
            returncode, stdout, stderr = safe_subprocess_call(
                [claude_path, "--version"],
                context="verifying Claude CLI is ready",
                timeout=5,
            )

            if returncode == 0:
                debug_print(f"\u2705 Claude CLI verified ready: {stdout.strip()}")
                return True

            if attempt < max_retries - 1:
                debug_print(
                    f"\u23f3 Claude CLI not ready yet (attempt {attempt + 1}/{max_retries}), retrying..."
                )
                time.sleep(retry_delay)

        except Exception as e:
            if attempt < max_retries - 1:
                debug_print(
                    f"\u23f3 Claude CLI verification error (attempt {attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(retry_delay)
            else:
                debug_print(f"\u274c Claude CLI verification failed after {max_retries} attempts: {e}")

    return False


def add_plugin_args_for_uvx(
    claude_args: list[str] | None = None, use_installed_plugin: bool = False
) -> list[str]:
    """Add --plugin-dir and --add-dir arguments for UVX deployment.

    Args:
        claude_args: Existing Claude arguments
        use_installed_plugin: Deprecated parameter, kept for backward compatibility (ignored)

    Returns:
        Updated arguments with plugin directory added
    """
    if not is_uvx_deployment():
        return claude_args or []

    result_args = list(claude_args or [])
    original_cwd = os.environ.get("AMPLIHACK_ORIGINAL_CWD", os.getcwd())

    # Add --add-dir for project access
    if "--add-dir" not in result_args:
        result_args = ["--add-dir", original_cwd] + result_args

    # ALWAYS add --plugin-dir for plugin discovery (simplified from complex conditional)
    # Claude Code discovers plugins from ~/.amplihack/.claude regardless of installation method
    plugin_root = str(Path.home() / ".amplihack" / ".claude")
    if "--plugin-dir" not in result_args:
        result_args = ["--plugin-dir", plugin_root] + result_args

    return result_args


def configure_amplihack_marketplace() -> bool:
    """Configure amplihack marketplace in Claude Code settings.

    Adds extraKnownMarketplaces entry pointing to amplihack GitHub repo.
    This enables: claude plugin install amplihack

    Returns:
        bool: True if configuration successful, False otherwise
    """
    # Get Claude Code settings path (platform-aware)
    if platform.system() == "Windows":
        settings_path = Path.home() / "AppData" / "Roaming" / "claude-code" / "settings.json"
    else:
        settings_path = Path.home() / ".config" / "claude-code" / "settings.json"

    try:
        # Read existing settings
        if settings_path.exists():
            with open(settings_path) as f:
                settings = json.load(f)
        else:
            settings = {}
            settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Add marketplace if not present
        if "extraKnownMarketplaces" not in settings:
            settings["extraKnownMarketplaces"] = {}
        elif not isinstance(settings["extraKnownMarketplaces"], dict):
            # Auto-repair corrupted settings from old bug (list/array -> dict)
            settings["extraKnownMarketplaces"] = {}

        # Check if amplihack marketplace already exists
        if "amplihack" not in settings["extraKnownMarketplaces"]:
            settings["extraKnownMarketplaces"]["amplihack"] = {
                "source": {
                    "source": "github",
                    "repo": "rysweet/amplihack",
                }
            }

            # Write atomically
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=2)

            if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
                print(f"\u2705 Configured amplihack marketplace in {settings_path}")
        else:
            if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
                print("\u2705 Amplihack marketplace already configured")

        return True

    except Exception as e:
        print(f"\u274c Failed to configure marketplace: {e}")
        return False


def fallback_to_directory_copy(reason: str = "Plugin installation failed") -> str:
    """Copy .claude directory to ~/.amplihack/.claude/ (primary install location).

    This is the primary mechanism for deploying amplihack's .claude components
    to the user's home directory. Used both as a fallback when Claude Code plugin
    installation is unavailable AND as the primary method for amplifier command.

    Args:
        reason: Reason for using directory copy (for debug logging)

    Returns:
        Path to ~/.amplihack/.claude directory

    Raises:
        SystemExit: If directory copy fails
    """
    import amplihack
    from . import copytree_manifest

    if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
        print(f"   Reason: {reason}")

    install_dir = str(Path.home() / ".amplihack" / ".claude")
    amplihack_src = Path(amplihack.__file__).parent
    Path(install_dir).mkdir(parents=True, exist_ok=True)
    copied = copytree_manifest(str(amplihack_src), install_dir, ".claude")
    if not copied:
        print("\u274c Failed to copy .claude directory")
        sys.exit(1)

    return install_dir


def init_uvx_staging(args) -> str | None:
    """Initialize UVX staging: conflict detection, plugin install, PROJECT.md init.

    Args:
        args: Parsed command line arguments (needs ``command`` attribute)

    Returns:
        temp_claude_dir path or None
    """
    from .cli_parser import _CLAUDE_COMMANDS
    from .cli_staging import read_auto_update_preference
    from .utils.claude_cli import get_claude_cli_path

    # Stage Claude environment in current directory for UVX zero-install
    original_cwd = os.getcwd()

    # Safety: Check for git conflicts before copying
    from . import ESSENTIAL_DIRS
    from .safety import GitConflictDetector, SafeCopyStrategy

    detector = GitConflictDetector(original_cwd)
    conflict_result = detector.detect_conflicts(ESSENTIAL_DIRS)

    # Plugin architecture: Deploy to centralized location ~/.amplihack/.claude/
    plugin_install_dir = os.path.join(os.path.expanduser("~"), ".amplihack", ".claude")

    # Check user's auto_update preference to skip conflict prompt
    auto_approve = read_auto_update_preference(plugin_install_dir)

    strategy_manager = SafeCopyStrategy()
    copy_strategy = strategy_manager.determine_target(
        original_target=plugin_install_dir,
        has_conflicts=conflict_result.has_conflicts,
        conflicting_files=conflict_result.conflicting_files,
        auto_approve=auto_approve,
    )

    # Bug #1 Fix: Respect user cancellation (Issue #1940)
    if not copy_strategy.should_proceed:
        print("\n\u274c Operation cancelled - cannot proceed without updating .claude/ directory")
        print("   Commit your changes and try again\n")
        sys.exit(0)

    temp_claude_dir = str(copy_strategy.target_dir)

    # Set CLAUDE_PLUGIN_ROOT for hook path resolution
    os.environ["CLAUDE_PLUGIN_ROOT"] = temp_claude_dir

    # Store original_cwd for auto mode (always set, regardless of conflicts)
    os.environ["AMPLIHACK_ORIGINAL_CWD"] = original_cwd

    if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
        print("UVX mode: Using plugin architecture")
        print(f"Working directory remains: {original_cwd}")

    # Only install Claude Code plugin for Claude-specific commands.
    if args.command in _CLAUDE_COMMANDS:
        temp_claude_dir = install_claude_plugin(temp_claude_dir)

    # Smart PROJECT.md initialization for UVX mode
    try:
        from .utils.project_initializer import InitMode, initialize_project_md

        result = initialize_project_md(Path(original_cwd), mode=InitMode.FORCE)
        if result.success and result.action_taken.value in ["initialized", "regenerated"]:
            if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
                print(f"PROJECT.md {result.action_taken.value} for {Path(original_cwd).name}")
    except Exception as e:
        if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
            print(f"Warning: PROJECT.md initialization failed: {e}")

    return temp_claude_dir


def install_claude_plugin(temp_claude_dir: str | None) -> str | None:
    """Install Claude Code plugin via marketplace or fall back to directory copy.

    Args:
        temp_claude_dir: Current temp claude dir path

    Returns:
        Updated temp_claude_dir (may be None if plugin installed successfully)
    """
    from .utils.claude_cli import get_claude_cli_path

    if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
        print("\U0001f4e6 Setting up amplihack plugin")

    # Step 1: Configure marketplace in Claude Code settings
    if not configure_amplihack_marketplace():
        print("\u26a0\ufe0f  Failed to configure amplihack marketplace")
        print("   Falling back to directory copy mode")
        return fallback_to_directory_copy("Marketplace configuration failed")

    # Step 2: Install plugin using Claude CLI
    claude_path = get_claude_cli_path(auto_install=True)
    if not claude_path:
        print("\u26a0\ufe0f  Claude CLI not available")
        print("   Falling back to directory copy mode")
        return fallback_to_directory_copy("Claude CLI not available")

    # Step 2a: Verify Claude CLI is ready before using it
    if not verify_claude_cli_ready(claude_path):
        print("\u26a0\ufe0f  Claude CLI installed but not responding")
        print("   This can happen on first install - the binary needs to initialize")
        print("   Falling back to directory copy mode")
        return fallback_to_directory_copy("Claude CLI not ready")

    # Fix EXDEV error: Use temp directory on same filesystem as ~/.claude/
    claude_temp_dir = Path.home() / ".claude" / "temp"
    claude_temp_dir.mkdir(parents=True, exist_ok=True)

    # Set TMPDIR for subprocess to avoid cross-device rename errors
    env = os.environ.copy()
    env["TMPDIR"] = str(claude_temp_dir)

    # Step 2b: Sync marketplace to known_marketplaces.json
    marketplace_add_result = subprocess.run(
        [
            claude_path,
            "plugin",
            "marketplace",
            "add",
            "https://github.com/rysweet/amplihack",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )

    if marketplace_add_result.returncode != 0:
        debug_print(
            f"\u26a0\ufe0f  Marketplace add failed (may already exist): {marketplace_add_result.stderr}"
        )
    else:
        debug_print("\u2705 Amplihack marketplace added to known marketplaces")

    # Step 2c: Install plugin from marketplace
    result = subprocess.run(
        [claude_path, "plugin", "install", "amplihack"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )

    if result.returncode != 0:
        print(f"\u26a0\ufe0f  Plugin installation failed: {result.stderr}")
        print("   Falling back to directory copy mode")
        return fallback_to_directory_copy(f"Plugin install error: {result.stderr}")

    debug_print("\u2705 Amplihack plugin installed successfully")
    debug_print(result.stdout)

    # Set CLAUDE_PLUGIN_ROOT for hook resolution
    installed_plugin_path = (
        Path.home()
        / ".claude"
        / "plugins"
        / "cache"
        / "amplihack"
        / "amplihack"
        / "0.9.0"
    )
    os.environ["CLAUDE_PLUGIN_ROOT"] = str(installed_plugin_path)
    return None


__all__ = [
    "add_plugin_args_for_uvx",
    "configure_amplihack_marketplace",
    "debug_print",
    "fallback_to_directory_copy",
    "init_uvx_staging",
    "install_claude_plugin",
    "verify_claude_cli_ready",
]
