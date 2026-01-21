"""Enhanced CLI for amplihack with proxy and launcher support."""

import argparse
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path

from . import copytree_manifest
from .docker import DockerManager
from .launcher import ClaudeLauncher
from .launcher.session_tracker import SessionTracker
from .plugin_cli import (
    plugin_install_command,
    plugin_uninstall_command,
    plugin_verify_command,
    setup_plugin_commands,
)
from .plugin_manager import PluginManager
from .proxy import ProxyConfig, ProxyManager
from .utils import is_uvx_deployment
from .utils.claude_cli import get_claude_cli_path

# Platform-specific emoji support
IS_WINDOWS = platform.system() == "Windows"
EMOJI = {
    "check": "[OK]" if IS_WINDOWS else "✓",
}


def add_plugin_args_for_uvx(claude_args: list[str] | None = None) -> list[str]:
    """Add --plugin-dir and --add-dir arguments for UVX deployment.

    Args:
        claude_args: Existing Claude arguments

    Returns:
        Updated arguments with plugin directory added
    """
    if not is_uvx_deployment():
        return claude_args or []

    result_args = list(claude_args or [])
    original_cwd = os.environ.get("AMPLIHACK_ORIGINAL_CWD", os.getcwd())
    plugin_root = str(Path.home() / ".amplihack" / ".claude")

    # Add --add-dir for project access
    if "--add-dir" not in result_args:
        result_args = ["--add-dir", original_cwd] + result_args

    # Add --plugin-dir to load amplihack as a plugin
    if "--plugin-dir" not in result_args:
        result_args = ["--plugin-dir", plugin_root] + result_args

    return result_args


def launch_command(args: argparse.Namespace, claude_args: list[str] | None = None) -> int:
    """Handle the launch command.

    Args:
        args: Parsed command line arguments.
        claude_args: Additional arguments to forward to Claude.

    Returns:
        Exit code.
    """
    # Detect nesting BEFORE any .claude/ operations
    from .launcher.nesting_detector import NestingDetector
    from .launcher.session_tracker import SessionTracker
    from .launcher.auto_stager import AutoStager

    detector = NestingDetector()
    nesting_result = detector.detect_nesting(Path.cwd(), sys.argv)

    # Auto-stage if nested execution in source repo detected
    original_cwd = None
    if nesting_result.requires_staging:
        print("\n🚨 SELF-MODIFICATION PROTECTION ACTIVATED")
        print("   Running nested in amplihack source repository")
        print("   Auto-staging .claude/ to temp directory for safety")

        stager = AutoStager()
        original_cwd = Path.cwd()
        staging_result = stager.stage_for_nested_execution(
            original_cwd,
            f"nested-{os.getpid()}"
        )

        print(f"   📁 Staged to: {staging_result.temp_root}")
        print("   Your original .claude/ files are protected")

        # CRITICAL: Change to temp directory so all .claude/ operations happen there
        os.chdir(staging_result.temp_root)
        print(f"   📂 CWD changed to: {staging_result.temp_root}\n")

    # Start session tracking
    tracker = SessionTracker()
    is_auto_mode = getattr(args, "auto", False)

    session_id = tracker.start_session(
        pid=os.getpid(),
        launch_dir=str(Path.cwd()),
        argv=sys.argv,
        is_auto_mode=is_auto_mode,
        is_nested=nesting_result.is_nested,
        parent_session_id=nesting_result.parent_session_id,
    )

    # Wrap execution in try/finally to ensure session is marked complete/crashed
    try:
        result = _launch_command_impl(args, claude_args, session_id, tracker)
        tracker.complete_session(session_id)
        return result
    except Exception as e:
        tracker.crash_session(session_id)
        raise
    finally:
        # Restore original CWD if we staged
        if original_cwd is not None:
            try:
                os.chdir(original_cwd)
            except Exception as e:
                # Best effort - log error but don't fail on CWD restore
                logging.debug(f"Failed to restore CWD to {original_cwd}: {e}")


def _launch_command_impl(args: argparse.Namespace, claude_args: list[str] | None, session_id: str, tracker: SessionTracker) -> int:
    """Internal implementation of launch_command with session tracking.

    Args:
        args: Parsed command line arguments.
        claude_args: Additional arguments to forward to Claude.
        session_id: Session ID from tracker
        tracker: SessionTracker instance

    Returns:
        Exit code.
    """
    # Set environment variable for Neo4j opt-in (Why: Makes flag accessible to session hooks)
    if getattr(args, "use_graph_mem", False):
        os.environ["AMPLIHACK_USE_GRAPH_MEM"] = "1"
        print("Neo4j graph memory enabled")

        # Set container name if provided
        if getattr(args, "use_memory_db", None):
            # Store in environment for session hooks to access
            os.environ["NEO4J_CONTAINER_NAME_CLI"] = args.use_memory_db
            print(f"Using Neo4j container: {args.use_memory_db}")

    # Check if Docker should be used (CLI flag takes precedence over env var)
    use_docker = getattr(args, "docker", False) or DockerManager.should_use_docker()

    # Handle --no-reflection flag (disable always wins priority)
    if getattr(args, "no_reflection", False):
        os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    # Handle --auto flag (for Neo4j container selection non-interactive mode)
    if getattr(args, "auto", False):
        os.environ["AMPLIHACK_AUTO_MODE"] = "1"

    if use_docker:
        print(
            "Docker mode enabled"
            + (
                " via --docker flag"
                if getattr(args, "docker", False)
                else " via AMPLIHACK_USE_DOCKER"
            )
        )
        docker_manager = DockerManager()

        # Build command arguments for Docker
        docker_args = ["launch"]
        if getattr(args, "with_proxy_config", None):
            docker_args.extend(["--with-proxy-config", args.with_proxy_config])
        if getattr(args, "checkout_repo", None):
            docker_args.extend(["--checkout-repo", args.checkout_repo])
        if claude_args:
            docker_args.append("--")
            docker_args.extend(claude_args)

        return docker_manager.run_command(docker_args)

    # In UVX mode, Claude uses --add-dir for both project directory and plugin directory

    proxy_manager = None
    system_prompt_path = None

    # Set up proxy if configuration provided
    if args.with_proxy_config:
        # For UVX mode, resolve relative paths from original directory
        if not Path(args.with_proxy_config).is_absolute():
            original_cwd = os.environ.get("AMPLIHACK_ORIGINAL_CWD", os.getcwd())
            config_path = Path(original_cwd) / args.with_proxy_config
            config_path = config_path.resolve()
        else:
            config_path = Path(args.with_proxy_config).resolve()

        if not config_path.exists():
            print(f"Error: Proxy configuration file not found: {config_path}")
            return 1

        print(f"Loading proxy configuration from: {config_path}")
        proxy_config = ProxyConfig(config_path)

        if not proxy_config.validate():
            print(
                "Error: Invalid proxy configuration. Check that OPENAI_API_KEY is set in your .env file"
            )
            return 1

        # Check if built-in proxy should be used
        use_builtin_proxy = getattr(args, "builtin_proxy", False)  # noqa: F841
        proxy_manager = ProxyManager(proxy_config)

        # When using proxy, automatically use Azure persistence prompt
        default_prompt = Path(__file__).parent / "prompts" / "azure_persistence.md"
        if default_prompt.exists():
            system_prompt_path = default_prompt
            print("Auto-appending Azure persistence prompt for proxy integration")

    # Launch Claude with checkout repo if specified
    launcher = ClaudeLauncher(
        proxy_manager=proxy_manager,
        append_system_prompt=system_prompt_path,
        checkout_repo=getattr(args, "checkout_repo", None),
        claude_args=claude_args,
        verbose=False,  # Interactive mode does not use --verbose
    )

    # Check if claude_args contains a prompt (-p) - if so, use non-interactive mode
    has_prompt = claude_args and ("-p" in claude_args)
    if has_prompt:
        exit_code = launcher.launch()
    else:
        exit_code = launcher.launch_interactive()

    # Mark session as complete
    tracker.complete_session(session_id)
    return exit_code


def handle_auto_mode(sdk: str, args: argparse.Namespace, cmd_args: list[str] | None) -> int | None:
    """Handle auto mode for claude, copilot, or codex commands.

    Args:
        sdk: "claude", "copilot", or "codex"
        args: Parsed arguments
        cmd_args: Command arguments (for extracting prompt)

    Returns:
        Exit code if auto mode, None if not auto mode
    """
    if not getattr(args, "auto", False):
        return None

    # Disable reflection in auto mode (Issue #1146)
    # Reflection is interactive and blocks autonomous execution
    # Note: --no-reflection flag (Issue #1147) is also handled in non-auto mode paths
    os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    from .launcher.auto_mode import AutoMode

    # Extract prompt from args
    prompt = None
    if cmd_args and "-p" in cmd_args:
        idx = cmd_args.index("-p")
        if idx + 1 < len(cmd_args):
            prompt = cmd_args[idx + 1]

    if not prompt:
        print(f'Error: --auto requires a prompt. Use: amplihack {sdk} --auto -- -p "your prompt"')
        return 1

    # Check if UI mode is enabled
    ui_mode = getattr(args, "ui", False)

    auto = AutoMode(sdk, prompt, args.max_turns, ui_mode=ui_mode)
    return auto.run()


def handle_append_instruction(args: argparse.Namespace) -> int:
    """Handle --append flag to inject instructions into running auto mode.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0=success, 1=error)
    """
    if not getattr(args, "append", None):
        return 0

    from .launcher.append_handler import AppendError, append_instructions

    instruction = args.append

    try:
        result = append_instructions(instruction)

        # Print success message
        print(f"{EMOJI['check']} Instruction appended to session: {result.session_id}")
        print(f"  File: {result.filename}")
        print("  The auto mode session will process this on its next turn.")
        return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1

    except AppendError as e:
        print(f"Error: {e}")
        return 1

    except Exception as e:
        print(f"Error: Failed to append instruction: {e}")
        return 1


def parse_args_with_passthrough(
    argv: list[str] | None = None,
) -> "tuple[argparse.Namespace, list[str]]":
    """Parse arguments with support for -- separator for Claude argument forwarding.

    Args:
        argv: Command line arguments. Uses sys.argv if None.

    Returns:
        Tuple of (parsed_args, claude_args) where claude_args are arguments after --
    """
    if argv is None:
        argv = sys.argv[1:]

    # Split arguments on -- separator
    try:
        separator_index = argv.index("--")
        amplihack_args = argv[:separator_index]
        claude_args = argv[separator_index + 1 :]
    except ValueError:
        # No -- separator found
        amplihack_args = argv
        claude_args = []

    parser = create_parser()

    # If no amplihack command specified and we have claude_args, default to launch
    if not amplihack_args and claude_args:
        amplihack_args = ["launch"]
    elif not amplihack_args:
        # No command and no claude args - show help
        pass

    args = parser.parse_args(amplihack_args)
    return args, claude_args


def add_auto_mode_args(parser: argparse.ArgumentParser) -> None:
    """Add auto mode arguments to a parser.

    Args:
        parser: ArgumentParser to add arguments to.
    """
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run in autonomous agentic mode with iterative loop (clarify → plan → execute → evaluate). Usage: --auto -- -p 'your task'. See docs/AUTO_MODE.md for details.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Max turns for auto mode (default: 10). Guidance: 5-10 for simple tasks, 10-15 for medium complexity, 15-30 for complex tasks.",
    )
    parser.add_argument(
        "--append",
        metavar="PROMPT",
        help="Append new instructions to a running auto mode session. Finds the active auto mode log directory in the current project and injects the new prompt.",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Enable interactive UI mode for auto mode (requires Rich library). Shows real-time execution state, logs, and allows prompt injection.",
    )


def add_common_sdk_args(parser: argparse.ArgumentParser) -> None:
    """Add common SDK arguments to a parser.

    Args:
        parser: ArgumentParser to add arguments to.
    """
    parser.add_argument(
        "--no-reflection",
        action="store_true",
        help="Disable post-session reflection analysis. Reflection normally runs after sessions to capture insights and learnings.",
    )


def add_claude_specific_args(parser: argparse.ArgumentParser) -> None:
    """Add Claude-specific arguments to a parser.

    Args:
        parser: ArgumentParser to add arguments to.
    """
    parser.add_argument(
        "--with-proxy-config",
        metavar="PATH",
        help="Path to .env file with proxy configuration (for Azure OpenAI integration with auto persistence prompt)",
    )
    parser.add_argument(
        "--builtin-proxy",
        action="store_true",
        help="Use built-in proxy server with OpenAI Responses API support instead of external claude-code-proxy",
    )
    parser.add_argument(
        "--checkout-repo",
        metavar="GITHUB_URI",
        help="Clone a GitHub repository and use it as working directory. Supports: owner/repo, https://github.com/owner/repo, git@github.com:owner/repo",
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Run amplihack in Docker container for isolated execution",
    )


def add_neo4j_args(parser: argparse.ArgumentParser) -> None:
    """Add Neo4j graph memory arguments to a parser.

    Args:
        parser: ArgumentParser to add arguments to.
    """
    parser.add_argument(
        "--use-graph-mem",
        action="store_true",
        help="Enable Neo4j graph memory system (opt-in). Requires Docker. See docs/NEO4J.md for setup.",
    )
    parser.add_argument(
        "--use-memory-db",
        metavar="NAME",
        help="Specify Neo4j container name (e.g., amplihack-myproject). Works with --use-graph-mem.",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for amplihack CLI.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="amplihack",
        description="Amplihack CLI - Enhanced tools for Claude Code development",
        epilog="""Examples:
  amplihack                                    # Launch Claude directly
  amplihack -- --model claude-3-opus-20240229 # Forward model argument to Claude
  amplihack -- --verbose                      # Forward verbose flag to Claude
  amplihack launch -- --help                  # Get Claude help
  amplihack install                           # Install amplihack (no forwarding)
  amplihack install -- --verbose             # Install with Claude args forwarded

Auto Mode Examples:
  amplihack launch --auto -- -p "implement user authentication"
  amplihack claude --auto --max-turns 20 -- -p "refactor the API module"
  amplihack copilot --auto -- -p "add logging to all services"
  amplihack codex --auto -- -p "optimize database queries"
  amplihack amplifier --auto -- -p "build a REST API"

Amplifier Examples:
  amplihack amplifier                                        # Launch Amplifier with amplihack bundle
  amplihack amplifier -- -p "explain this code"              # Non-interactive with prompt
  amplihack amplifier -- resume SESSION_ID                   # Resume a session
  amplihack amplifier -- --model gpt-4o                      # Use specific model
  amplihack amplifier -- --model gpt-4o -p "explain this"    # Model + prompt

For comprehensive auto mode documentation, see docs/AUTO_MODE.md""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Install command (existing)
    subparsers.add_parser("install", help="Install amplihack agents and tools to ~/.claude")

    # Uninstall command (existing)
    subparsers.add_parser("uninstall", help="Remove amplihack agents and tools from ~/.claude")

    # Launch command (new)
    launch_parser = subparsers.add_parser(
        "launch", help="Launch Claude Code with optional proxy configuration"
    )
    add_claude_specific_args(launch_parser)
    add_auto_mode_args(launch_parser)
    add_neo4j_args(launch_parser)
    add_common_sdk_args(launch_parser)

    # Claude command (alias for launch)
    claude_parser = subparsers.add_parser("claude", help="Launch Claude Code (alias for launch)")
    add_claude_specific_args(claude_parser)
    add_auto_mode_args(claude_parser)
    add_neo4j_args(claude_parser)
    add_common_sdk_args(claude_parser)

    # RustyClawd command (Rust implementation)
    rustyclawd_parser = subparsers.add_parser(
        "RustyClawd", help="Launch RustyClawd (Rust implementation)"
    )
    add_claude_specific_args(rustyclawd_parser)
    add_auto_mode_args(rustyclawd_parser)
    add_neo4j_args(rustyclawd_parser)
    add_common_sdk_args(rustyclawd_parser)

    # Copilot command
    copilot_parser = subparsers.add_parser("copilot", help="Launch GitHub Copilot CLI")
    add_auto_mode_args(copilot_parser)
    add_common_sdk_args(copilot_parser)

    # Codex command
    codex_parser = subparsers.add_parser("codex", help="Launch OpenAI Codex CLI")
    add_auto_mode_args(codex_parser)
    add_common_sdk_args(codex_parser)

    # Amplifier command
    # Note: All amplifier-specific args (--model, --provider, --resume, etc.) should be
    # passed after "--" separator, just like other CLI tools (claude, codex, copilot)
    amplifier_parser = subparsers.add_parser(
        "amplifier", help="Launch Microsoft Amplifier with amplihack bundle"
    )
    add_auto_mode_args(amplifier_parser)
    add_common_sdk_args(amplifier_parser)

    # UVX helper command
    uvx_parser = subparsers.add_parser("uvx-help", help="Get help with UVX deployment")
    uvx_parser.add_argument("--find-path", action="store_true", help="Find UVX installation path")
    uvx_parser.add_argument("--info", action="store_true", help="Show UVX staging information")

    # Hidden local install command
    local_install_parser = subparsers.add_parser("_local_install", help=argparse.SUPPRESS)
    local_install_parser.add_argument("repo_root", help="Repository root directory")

    # Plugin management commands
    plugin_parser = subparsers.add_parser("plugin", help="Plugin management commands")
    plugin_subparsers = plugin_parser.add_subparsers(
        dest="plugin_command", help="Plugin subcommands"
    )

    # Install plugin command
    install_parser = plugin_subparsers.add_parser(
        "install", help="Install plugin from git URL or local path"
    )
    install_parser.add_argument("source", help="Git URL or local directory path")
    install_parser.add_argument("--force", action="store_true", help="Overwrite existing plugin")

    # Uninstall plugin command
    uninstall_parser = plugin_subparsers.add_parser(
        "uninstall", help="Remove plugin"
    )
    uninstall_parser.add_argument("plugin_name", help="Name of plugin to remove")

    # Link plugin command
    link_parser = plugin_subparsers.add_parser(
        "link", help="Link installed plugin to Claude Code settings"
    )
    link_parser.add_argument(
        "plugin_name",
        nargs="?",
        default="amplihack",
        help="Plugin name to link (default: amplihack)",
    )

    # Verify plugin command
    verify_parser = plugin_subparsers.add_parser(
        "verify", help="Verify plugin installation and discoverability"
    )
    verify_parser.add_argument(
        "plugin_name",
        nargs="?",
        default="amplihack",
        help="Plugin name to verify (default: amplihack)",
    )

    # Memory tree visualization command
    memory_parser = subparsers.add_parser("memory", help="Memory system commands")
    memory_subparsers = memory_parser.add_subparsers(
        dest="memory_command", help="Memory subcommands"
    )

    tree_parser = memory_subparsers.add_parser("tree", help="Visualize memory graph as tree")
    tree_parser.add_argument("--session", help="Filter by session ID")
    tree_parser.add_argument(
        "--type",
        choices=["conversation", "decision", "pattern", "context", "learning", "artifact"],
        help="Filter by memory type",
    )
    tree_parser.add_argument("--depth", type=int, help="Maximum tree depth")
    tree_parser.add_argument(
        "--backend", choices=["kuzu", "sqlite"], default="kuzu", help="Memory backend to use"
    )

    # Clean subcommand
    clean_parser = memory_subparsers.add_parser(
        "clean",
        help="Clean up test sessions",
        epilog="Examples:\n"
        "  amplihack memory clean --pattern 'test_*'     # Clean test sessions\n"
        "  amplihack memory clean --pattern 'demo_*'     # Clean demo sessions\n"
        "  amplihack memory clean --pattern '*_temp'     # Clean temporary sessions\n"
        "  amplihack memory clean --pattern 'dev_*' --no-dry-run  # Actually delete dev sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    clean_parser.add_argument(
        "--pattern",
        default="test_*",
        help="Session ID pattern to match (supports * wildcards, default: test_*)",
    )
    clean_parser.add_argument(
        "--backend", choices=["kuzu", "sqlite"], default="kuzu", help="Memory backend to use"
    )
    clean_parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually delete sessions (default is dry-run mode)",
    )
    clean_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt (use with --no-dry-run)",
    )

    # Mode detection commands
    mode_parser = subparsers.add_parser("mode", help="Claude installation mode commands")
    mode_subparsers = mode_parser.add_subparsers(
        dest="mode_command", help="Mode subcommands"
    )

    # Detect mode command
    detect_parser = mode_subparsers.add_parser(
        "detect", help="Detect current Claude installation mode"
    )

    # Migrate to plugin command
    to_plugin_parser = mode_subparsers.add_parser(
        "to-plugin", help="Migrate from local to plugin mode"
    )

    # Migrate to local command
    to_local_parser = mode_subparsers.add_parser(
        "to-local", help="Create local .claude/ from plugin"
    )

    return parser


def _fallback_to_directory_copy(reason: str = "Plugin installation failed") -> str:
    """Fallback to directory copy mode when plugin installation is not available.

    Args:
        reason: Reason for fallback (for debug logging)

    Returns:
        Path to temporary .claude directory

    Raises:
        SystemExit: If directory copy fails
    """
    import amplihack

    if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
        print(f"   Reason: {reason}")

    temp_claude_dir = str(Path.home() / ".amplihack" / ".claude")
    amplihack_src = Path(amplihack.__file__).parent
    Path(temp_claude_dir).mkdir(parents=True, exist_ok=True)
    copied = copytree_manifest(str(amplihack_src), temp_claude_dir, ".claude")
    if not copied:
        print("❌ Failed to copy .claude directory")
        sys.exit(1)

    return temp_claude_dir


def main(argv: list[str] | None = None) -> int:
    """Main entry point for amplihack CLI.

    Args:
        argv: Command line arguments. Uses sys.argv if None.

    Returns:
        Exit code.
    """
    # Initialize UVX staging if needed (before parsing args)
    temp_claude_dir = None
    if is_uvx_deployment():
        # Stage Claude environment in current directory for UVX zero-install

        # Save original directory (which is now also the working directory)
        original_cwd = os.getcwd()

        # Safety: Check for git conflicts before copying
        from . import ESSENTIAL_DIRS
        from .safety import GitConflictDetector, SafeCopyStrategy

        detector = GitConflictDetector(original_cwd)
        conflict_result = detector.detect_conflicts(ESSENTIAL_DIRS)

        # Plugin architecture: Deploy to centralized location ~/.amplihack/.claude/
        plugin_install_dir = os.path.join(os.path.expanduser("~"), ".amplihack", ".claude")

        strategy_manager = SafeCopyStrategy()
        copy_strategy = strategy_manager.determine_target(
            original_target=plugin_install_dir,
            has_conflicts=conflict_result.has_conflicts,
            conflicting_files=conflict_result.conflicting_files,
        )

        # Bug #1 Fix: Respect user cancellation (Issue #1940)
        # When user responds 'n' to conflict prompt, should_proceed=False
        # Exit gracefully with code 0 (user-initiated cancellation, not an error)
        if not copy_strategy.should_proceed:
            print("\n❌ Operation cancelled - cannot proceed without updating .claude/ directory")
            print("   Commit your changes and try again\n")
            sys.exit(0)

        temp_claude_dir = str(copy_strategy.target_dir)

        # Set CLAUDE_PLUGIN_ROOT for hook path resolution
        os.environ["CLAUDE_PLUGIN_ROOT"] = temp_claude_dir

        # Store original_cwd for auto mode (always set, regardless of conflicts)
        os.environ["AMPLIHACK_ORIGINAL_CWD"] = original_cwd

        if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
            print(f"UVX mode: Using plugin architecture")
            print(f"Working directory remains: {original_cwd}")

        # Setup plugin architecture
        # .claude-plugin is copied to src/amplihack/.claude-plugin/ by build_hooks.py
        import amplihack
        amplihack_package = Path(amplihack.__file__).parent

        # For local installations (pip/uvx), use directory copy mode
        # Note: `claude plugin install` expects marketplace plugin names (e.g., "amplihack"),
        # not local filesystem paths. It's only used when users run: claude plugin install amplihack
        # The .claude-plugin/plugin.json manifest enables that marketplace discovery.
        if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
            print(f"📦 Setting up amplihack from local installation")

        temp_claude_dir = str(Path(original_cwd) / ".claude")
        amplihack_src = Path(amplihack.__file__).parent
        Path(temp_claude_dir).mkdir(parents=True, exist_ok=True)
        copied = copytree_manifest(str(amplihack_src), temp_claude_dir, ".claude")
        if not copied:
            print("❌ Failed to copy .claude directory")
            sys.exit(1)

            # 3. Generate settings.json in project's .claude/ that references plugin
            local_claude_dir = Path(original_cwd) / ".claude"
            temp_claude_dir = str(local_claude_dir)
            local_claude_dir.mkdir(parents=True, exist_ok=True)

            settings_path = local_claude_dir / "settings.json"
            import json

            # Set CLAUDE_PLUGIN_ROOT for path resolution
            os.environ["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

            # Create settings.json with plugin references
            settings = {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/session_start.py",
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
                                    "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/stop.py",
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
                                    "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/post_tool_use.py",
                                }
                            ],
                        }
                    ],
                    "PreCompact": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/pre_compact.py",
                                    "timeout": 30000,
                                }
                            ]
                        }
                    ],
                }
            }

            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=2)

            if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
                print(f"Created settings.json at {settings_path}")
                print(f"Settings reference plugin at {plugin_root}")

        # Smart PROJECT.md initialization for UVX mode
        try:
            from .utils.project_initializer import InitMode, initialize_project_md

            result = initialize_project_md(Path(original_cwd), mode=InitMode.FORCE)
            if result.success and result.action_taken.value in ["initialized", "regenerated"]:
                if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
                    print(
                        f"PROJECT.md {result.action_taken.value} for {Path(original_cwd).name}"
                    )
        except Exception as e:
            if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
                print(f"Warning: PROJECT.md initialization failed: {e}")

    args, claude_args = parse_args_with_passthrough(argv)

    if not args.command:
        # If we have claude_args but no command, default to launching Claude directly
        if claude_args:
            # If in UVX mode, use --plugin-dir to load amplihack as a plugin
            if is_uvx_deployment():
                claude_args = add_plugin_args_for_uvx(claude_args)

            # Check if Docker should be used for direct launch
            if DockerManager.should_use_docker():
                print("Docker mode enabled via AMPLIHACK_USE_DOCKER")
                docker_manager = DockerManager()
                docker_args = ["launch", "--"] + claude_args
                return docker_manager.run_command(docker_args)

            launcher = ClaudeLauncher(claude_args=claude_args, verbose=False)
            return launcher.launch_interactive()
        create_parser().print_help()
        return 1

    # Import the original functions for backward compatibility
    from . import _local_install, uninstall

    if args.command == "install":
        # Use the existing install logic
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
        # Handle append mode FIRST (before any other initialization)
        if getattr(args, "append", None):
            return handle_append_instruction(args)

        # If in UVX mode, ensure we use --add-dir for BOTH the original directory AND plugin directory
        if is_uvx_deployment():
            claude_args = add_plugin_args_for_uvx(claude_args)

        # CRITICAL: Detect nesting BEFORE any .claude/ operations (including auto mode!)
        from .launcher.nesting_detector import NestingDetector
        from .launcher.auto_stager import AutoStager

        detector = NestingDetector()
        nesting_result = detector.detect_nesting(Path.cwd(), sys.argv)

        # Auto-stage if nested/source repo detected
        saved_cwd = None
        if nesting_result.requires_staging:
            print("\n🚨 SELF-MODIFICATION PROTECTION ACTIVATED")
            print(f"   Reason: {'Nested execution' if nesting_result.is_nested else 'Running in amplihack source repo'}")
            print("   Auto-staging .claude/ to temp directory for safety")

            stager = AutoStager()
            saved_cwd = Path.cwd()
            staging_result = stager.stage_for_nested_execution(saved_cwd, f"protected-{os.getpid()}")

            print(f"   📁 Staged to: {staging_result.temp_root}")
            os.chdir(staging_result.temp_root)
            print(f"   📂 CWD: {staging_result.temp_root}")
            print("   Your original .claude/ files are PROTECTED\n")

        try:
            # If in UVX mode, ensure we use --add-dir for the ORIGINAL directory
            if is_uvx_deployment():
                # Get the original directory (before we changed to temp)
                original_cwd = os.environ.get("AMPLIHACK_ORIGINAL_CWD", saved_cwd or os.getcwd())
                # Add --add-dir to claude_args if not already present
                if claude_args and "--add-dir" not in claude_args:
                    claude_args = ["--add-dir", str(original_cwd)] + claude_args
                elif not claude_args:
                    claude_args = ["--add-dir", str(original_cwd)]

            # Handle auto mode
            exit_code = handle_auto_mode("claude", args, claude_args)
            if exit_code is not None:
                return exit_code

            return launch_command(args, claude_args)
        finally:
            # Restore CWD if we staged
            if saved_cwd is not None:
                try:
                    os.chdir(saved_cwd)
                except Exception as e:
                    # Best effort - log error but don't fail on CWD restore
                    logging.debug(f"Failed to restore CWD to {saved_cwd}: {e}")

    elif args.command == "claude":
        # Handle append mode FIRST (before any other initialization)
        if getattr(args, "append", None):
            return handle_append_instruction(args)

        # Claude is an alias for launch
        if is_uvx_deployment():
            claude_args = add_plugin_args_for_uvx(claude_args)

        # Handle auto mode
        exit_code = handle_auto_mode("claude", args, claude_args)
        if exit_code is not None:
            return exit_code

        return launch_command(args, claude_args)

    elif args.command == "RustyClawd":
        # Handle append mode FIRST (before any other initialization)
        if getattr(args, "append", None):
            return handle_append_instruction(args)

        # Force RustyClawd usage (Rust implementation of Claude Code)
        os.environ["AMPLIHACK_USE_RUSTYCLAWD"] = "1"
        print("Using RustyClawd (Rust implementation)")

        # RustyClawd launcher setup (similar to claude command)
        if is_uvx_deployment():
            claude_args = add_plugin_args_for_uvx(claude_args)

        # Handle auto mode
        exit_code = handle_auto_mode("claude", args, claude_args)  # Reuse claude auto mode
        if exit_code is not None:
            return exit_code

        return launch_command(args, claude_args)

    elif args.command == "copilot":
        from .launcher.copilot import launch_copilot

        # Handle append mode FIRST (before any other initialization)
        if getattr(args, "append", None):
            return handle_append_instruction(args)

        # Handle auto mode
        exit_code = handle_auto_mode("copilot", args, claude_args)
        if exit_code is not None:
            return exit_code

        # Handle --no-reflection flag (disable always wins priority)
        if getattr(args, "no_reflection", False):
            os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

        # Normal copilot launch
        has_prompt = claude_args and "-p" in claude_args
        return launch_copilot(claude_args, interactive=not has_prompt)

    elif args.command == "codex":
        from .launcher.codex import launch_codex

        # Handle append mode FIRST (before any other initialization)
        if getattr(args, "append", None):
            return handle_append_instruction(args)

        # Handle auto mode
        exit_code = handle_auto_mode("codex", args, claude_args)
        if exit_code is not None:
            return exit_code

        # Handle --no-reflection flag (disable always wins priority)
        if getattr(args, "no_reflection", False):
            os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

        # Normal codex launch
        has_prompt = claude_args and "-p" in claude_args
        return launch_codex(claude_args, interactive=not has_prompt)

    elif args.command == "amplifier":
        from .launcher.amplifier import launch_amplifier, launch_amplifier_auto

        # Early exit: append mode
        if getattr(args, "append", None):
            return handle_append_instruction(args)

        # Environment setup
        if getattr(args, "no_reflection", False):
            os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

        # All amplifier args come after -- separator (claude_args)
        # Extract prompt from args if present (for auto mode check)
        prompt = None
        if claude_args and "-p" in claude_args:
            idx = claude_args.index("-p")
            if idx + 1 < len(claude_args):
                prompt = claude_args[idx + 1]

        # Auto mode - Amplifier manages its own execution loop
        if getattr(args, "auto", False):
            if not prompt:
                print('Error: --auto requires a prompt via -- -p "prompt"')
                return 1
            return launch_amplifier_auto(prompt)

        # Normal launch - pass all args after -- directly to amplifier
        return launch_amplifier(args=claude_args or [])

    elif args.command == "uvx-help":
        from .commands.uvx_helper import find_uvx_installation_path, print_uvx_usage_instructions

        if args.find_path:
            path = find_uvx_installation_path()
            if path:
                print(str(path))
                return 0
            print("UVX installation path not found", file=sys.stderr)
            return 1
        if args.info:
            # Show UVX staging information
            print("\nUVX Information:")
            print(f"  Is UVX: {is_uvx_deployment()}")
            print("\nEnvironment Variables:")
            print(f"  AMPLIHACK_ROOT={os.environ.get('AMPLIHACK_ROOT', '(not set)')}")
            return 0
        print_uvx_usage_instructions()
        return 0

    elif args.command == "plugin":
        if args.plugin_command == "install":
            return plugin_install_command(args)
        elif args.plugin_command == "uninstall":
            return plugin_uninstall_command(args)
        elif args.plugin_command == "verify":
            return plugin_verify_command(args)
        elif args.plugin_command == "link":
            plugin_name = args.plugin_name
            plugin_root = Path.home() / ".amplihack" / "plugins"
            plugin_path = plugin_root / plugin_name

            if not plugin_path.exists():
                print(f"Error: Plugin not found at {plugin_path}")
                print(f"Install the plugin first with: amplihack install")
                return 1

            # Create plugin manager and link plugin
            manager = PluginManager(plugin_root=plugin_root)
            if manager._register_plugin(plugin_name):
                print(f"{EMOJI['check']} Plugin linked successfully: {plugin_name}")
                print(f"  Settings updated in: ~/.claude/settings.json")
                print(f"  Plugin should now appear in /plugin command")
                return 0
            else:
                print(f"Error: Failed to link plugin: {plugin_name}")
                return 1

        else:
            create_parser().print_help()
            return 1

    elif args.command == "memory":
        if args.memory_command == "tree":
            from .memory.cli_visualize import visualize_memory_tree
            from .memory.models import MemoryType

            # Select backend
            if args.backend == "kuzu":
                try:
                    from .memory.backends.kuzu_backend import KuzuBackend

                    backend = KuzuBackend()
                    backend.initialize()
                except ImportError:
                    print(
                        "Error: Kùzu backend not available. Kuzu should be installed automatically with amplihack."
                    )
                    print("Fallin' back to SQLite backend...")
                    from .memory.database import MemoryDatabase

                    backend = MemoryDatabase()
                    backend.initialize()
            else:
                from .memory.database import MemoryDatabase

                backend = MemoryDatabase()
                backend.initialize()

            # Convert type string to enum if provided
            memory_type = None
            if args.type:
                memory_type = MemoryType(args.type)

            # Visualize
            visualize_memory_tree(
                backend=backend,
                session_id=args.session,
                memory_type=memory_type,
                depth=args.depth,
            )

            # Cleanup
            if hasattr(backend, "close"):
                backend.close()

            return 0

        if args.memory_command == "clean":
            from .memory.cli_cleanup import cleanup_memory_sessions

            # Select backend
            if args.backend == "kuzu":
                try:
                    from .memory.backends.kuzu_backend import KuzuBackend

                    backend = KuzuBackend()
                    backend.initialize()
                except ImportError:
                    print("Error: Kùzu backend not available. Install with: pip install amplihack")
                    return 1
            else:
                from .memory.database import MemoryDatabase

                backend = MemoryDatabase()
                backend.initialize()

            # Run cleanup
            result = cleanup_memory_sessions(
                backend=backend,
                pattern=args.pattern,
                dry_run=not args.no_dry_run,
                confirm=args.confirm,
            )

            # Cleanup backend
            if hasattr(backend, "close"):
                backend.close()

            # Return non-zero if there were errors
            return 1 if result["errors"] > 0 else 0

        create_parser().print_help()
        return 1

    elif args.command == "mode":
        from .mode_detector import ModeDetector, MigrationHelper

        detector = ModeDetector()

        if args.mode_command == "detect":
            mode = detector.detect()
            claude_dir = detector.get_claude_dir(mode)

            print(f"Claude installation mode: {mode.value}")
            if claude_dir:
                print(f"Using .claude directory: {claude_dir}")
            else:
                print("No .claude installation found")
                print("Install amplihack with: amplihack install")
            return 0

        elif args.mode_command == "to-plugin":
            migrator = MigrationHelper()
            project_dir = Path.cwd()

            if not migrator.can_migrate_to_plugin(project_dir):
                print("Cannot migrate to plugin mode:")
                if not detector.has_local_installation():
                    print("  - No local .claude/ directory found")
                if not detector.has_plugin_installation():
                    print("  - Plugin not installed (run: amplihack install)")
                return 1

            print(f"This will remove local .claude/ directory: {project_dir / '.claude'}")
            print("Plugin installation will be used instead.")
            response = input("Continue? (y/N): ")

            if response.lower() != 'y':
                print("Migration cancelled")
                return 0

            if migrator.migrate_to_plugin(project_dir):
                print(f"{EMOJI['check']} Migrated to plugin mode successfully")
                print("Local .claude/ removed, using plugin installation")
                return 0
            else:
                print("Migration failed")
                return 1

        elif args.mode_command == "to-local":
            migrator = MigrationHelper()
            project_dir = Path.cwd()
            info = migrator.get_migration_info(project_dir)

            if not info["can_migrate_to_local"]:
                print("Cannot create local .claude/ directory:")
                if info["has_local"]:
                    print("  - Local .claude/ already exists")
                if not info["has_plugin"]:
                    print("  - Plugin not installed (run: amplihack install)")
                return 1

            print(f"This will create local .claude/ directory in: {project_dir}")
            print(f"Copying from plugin: {info['plugin_path']}")
            response = input("Continue? (y/N): ")

            if response.lower() != 'y':
                print("Migration cancelled")
                return 0

            if migrator.migrate_to_local(project_dir):
                print(f"{EMOJI['check']} Local .claude/ created successfully")
                print("Now using project-local installation")
                return 0
            else:
                print("Migration failed")
                return 1

        else:
            create_parser().print_help()
            return 1

    else:
        create_parser().print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
