"""Enhanced CLI for amplihack with proxy and launcher support.

This is the main entry point for the amplihack CLI. The implementation
is split across several modules for maintainability:

- cli_parser: Argument parsing and subcommand definitions
- cli_launcher: Launch/session management and auto mode
- cli_plugin: Plugin installation, marketplace setup, and UVX staging
- cli_staging: Framework staging, auto-update preference, and global settings
- cli_commands: Command dispatch handlers for utility subcommands
- cli_sdk_commands: Command handlers for SDK launches (copilot, codex, amplifier)

All public symbols are re-exported here for backward compatibility.
Existing imports like ``from amplihack.cli import X`` continue to work.
"""

import logging
import os
import subprocess  # noqa: F401 - needed for test patching at amplihack.cli.subprocess
import sys
from pathlib import Path

from .docker import DockerManager
from .launcher import ClaudeLauncher
from .staging_cleanup import cleanup_legacy_skills  # noqa: F401 - test compat
from .utils import is_uvx_deployment
from .utils.claude_cli import get_claude_cli_path  # noqa: F401 - test compat

# Re-export all public symbols for backward compatibility
from .cli_commands import (  # noqa: F401
    handle_amplifier_command,
    handle_codex_command,
    handle_copilot_command,
    handle_memory_command,
    handle_mode_command,
    handle_new_command,
    handle_plugin_command,
    handle_recipe_command,
    handle_uvx_help_command,
)
from .cli_launcher import (  # noqa: F401
    handle_append_instruction,
    handle_auto_mode,
    launch_command,
)
from .cli_parser import (  # noqa: F401
    EMOJI,
    IS_WINDOWS,
    _CLAUDE_COMMANDS,
    add_auto_mode_args,
    add_claude_specific_args,
    add_common_sdk_args,
    create_parser,
    parse_args_with_passthrough,
)
from .cli_plugin import (  # noqa: F401
    add_plugin_args_for_uvx,
    configure_amplihack_marketplace as _configure_amplihack_marketplace,
    debug_print as _debug_print,
    fallback_to_directory_copy as _fallback_to_directory_copy,
    init_uvx_staging,
    verify_claude_cli_ready as _verify_claude_cli_ready,
)
from .cli_staging import (  # noqa: F401
    ensure_amplihack_staged as _ensure_amplihack_staged,
    fix_global_statusline_path as _fix_global_statusline_path,
    read_auto_update_preference as _read_auto_update_preference,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for amplihack CLI.

    Args:
        argv: Command line arguments. Uses sys.argv if None.

    Returns:
        Exit code.
    """
    # Platform compatibility check FIRST (fail-fast before any operations)
    from .launcher.platform_check import check_platform_compatibility

    platform_result = check_platform_compatibility()
    if not platform_result.compatible:
        print(platform_result.message, file=sys.stderr)
        return 1

    # Auto-update check (only for uv tool installs, not uvx)
    if not is_uvx_deployment():
        from .auto_update import check_for_updates, prompt_and_upgrade

        try:
            from . import __version__

            cache_dir = Path.home() / ".amplihack" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)

            update_info = check_for_updates(
                current_version=__version__,
                cache_dir=cache_dir,
                check_interval_hours=24,
                timeout_seconds=5,
            )

            if update_info and update_info.is_newer:
                restart_args = sys.argv[1:] if argv is None else (argv if argv else [])
                if prompt_and_upgrade(update_info, restart_args):
                    return 0

        except Exception as e:
            logger.debug(f"Update check failed: {e}")

    # Parse arguments FIRST to determine which command is being run
    args, claude_args = parse_args_with_passthrough(argv)

    # Auto-install missing blarify dependencies (scip-python, etc.)
    if not hasattr(args, "command") or args.command in (None, "launch"):
        try:
            from .memory.kuzu.indexing.dependency_installer import DependencyInstaller

            installer = DependencyInstaller(quiet=False)
            installer.install_all_auto_installable()
            installer.show_system_dependency_help()
        except Exception as e:
            logger.warning(f"Failed to auto-install dependencies: {e}")

    # Initialize UVX staging if needed
    if is_uvx_deployment():
        init_uvx_staging(args)

    if not args.command:
        return _handle_no_command(claude_args)

    return _dispatch_command(args, claude_args)


def _handle_no_command(claude_args: list[str]) -> int:
    """Handle the case where no subcommand is specified."""
    if claude_args:
        if is_uvx_deployment():
            claude_args = add_plugin_args_for_uvx(claude_args)

        if DockerManager.should_use_docker():
            print("Docker mode enabled via AMPLIHACK_USE_DOCKER")
            docker_manager = DockerManager()
            docker_args = ["launch", "--"] + claude_args
            return docker_manager.run_command(docker_args)

        launcher = ClaudeLauncher(claude_args=claude_args, verbose=False)
        return launcher.launch_interactive()
    create_parser().print_help()
    return 1


def _dispatch_command(args, claude_args: list[str]) -> int:
    """Dispatch to the appropriate command handler."""
    from . import _local_install, uninstall

    if args.command == "install":
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            repo_url = "https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding"
            try:
                subprocess.check_call(["git", "clone", "--depth", "1", repo_url, tmp])
                _local_install(tmp)
                return 0
            except subprocess.CalledProcessError as e:
                print(f"Failed to install: {e}")
                return 1

    elif args.command == "uninstall":
        uninstall()
        return 0

    elif args.command == "_local_install":
        _local_install(args.repo_root)
        return 0

    elif args.command == "launch":
        return _handle_launch_command(args, claude_args)

    elif args.command == "claude":
        return _handle_claude_command(args, claude_args)

    elif args.command == "RustyClawd":
        return _handle_rustyclawd_command(args, claude_args)

    elif args.command == "copilot":
        return handle_copilot_command(args, claude_args)

    elif args.command == "codex":
        return handle_codex_command(args, claude_args)

    elif args.command == "amplifier":
        return handle_amplifier_command(args, claude_args)

    elif args.command == "uvx-help":
        return handle_uvx_help_command(args)

    elif args.command == "plugin":
        return handle_plugin_command(args)

    elif args.command == "memory":
        return handle_memory_command(args)

    elif args.command == "new":
        return handle_new_command(args)

    elif args.command == "recipe":
        return handle_recipe_command(args)

    elif args.command == "mode":
        return handle_mode_command(args)

    else:
        create_parser().print_help()
        return 1


def _handle_launch_command(args, claude_args: list[str]) -> int:
    """Handle the 'launch' subcommand with nesting detection."""
    if getattr(args, "append", None):
        return handle_append_instruction(args)

    if is_uvx_deployment():
        claude_args = add_plugin_args_for_uvx(claude_args)

    from .launcher.auto_stager import AutoStager
    from .launcher.nesting_detector import NestingDetector

    detector = NestingDetector()
    nesting_result = detector.detect_nesting(Path.cwd(), sys.argv)

    saved_cwd = None
    if nesting_result.requires_staging:
        print("\n\U0001f6a8 SELF-MODIFICATION PROTECTION ACTIVATED")
        print(
            f"   Reason: {'Nested execution' if nesting_result.is_nested else 'Running in amplihack source repo'}"
        )
        print("   Auto-staging .claude/ to temp directory for safety")

        stager = AutoStager()
        saved_cwd = Path.cwd()
        staging_result = stager.stage_for_nested_execution(
            saved_cwd, f"protected-{os.getpid()}"
        )

        print(f"   \U0001f4c1 Staged to: {staging_result.temp_root}")
        os.chdir(staging_result.temp_root)
        print(f"   \U0001f4c2 CWD: {staging_result.temp_root}")
        print("   Your original .claude/ files are PROTECTED\n")

    try:
        if is_uvx_deployment():
            original_cwd = os.environ.get("AMPLIHACK_ORIGINAL_CWD", saved_cwd or os.getcwd())
            if claude_args and "--add-dir" not in claude_args:
                claude_args = ["--add-dir", str(original_cwd)] + claude_args
            elif not claude_args:
                claude_args = ["--add-dir", str(original_cwd)]

        exit_code = handle_auto_mode("claude", args, claude_args)
        if exit_code is not None:
            return exit_code

        return launch_command(args, claude_args)
    finally:
        if saved_cwd is not None:
            try:
                os.chdir(saved_cwd)
            except Exception as e:
                logging.debug(f"Failed to restore CWD to {saved_cwd}: {e}")


def _handle_claude_command(args, claude_args: list[str]) -> int:
    """Handle the 'claude' subcommand (alias for launch)."""
    if getattr(args, "append", None):
        return handle_append_instruction(args)

    if is_uvx_deployment():
        claude_args = add_plugin_args_for_uvx(claude_args)

    exit_code = handle_auto_mode("claude", args, claude_args)
    if exit_code is not None:
        return exit_code

    return launch_command(args, claude_args)


def _handle_rustyclawd_command(args, claude_args: list[str]) -> int:
    """Handle the 'RustyClawd' subcommand."""
    if getattr(args, "append", None):
        return handle_append_instruction(args)

    if not getattr(args, "subprocess_safe", False):
        _ensure_amplihack_staged()

    os.environ["AMPLIHACK_USE_RUSTYCLAWD"] = "1"
    print("Using RustyClawd (Rust implementation)")

    if is_uvx_deployment():
        claude_args = add_plugin_args_for_uvx(claude_args)

    exit_code = handle_auto_mode("claude", args, claude_args)
    if exit_code is not None:
        return exit_code

    return launch_command(args, claude_args)


if __name__ == "__main__":
    sys.exit(main())
