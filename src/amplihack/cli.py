"""Enhanced CLI for amplihack with proxy and launcher support."""

import argparse
import json
import os
import platform
import sys
from pathlib import Path

from . import copytree_manifest
from .docker import DockerManager
from .launcher import ClaudeLauncher
from .proxy import ProxyConfig, ProxyManager
from .utils import is_uvx_deployment

# Platform-specific emoji support
IS_WINDOWS = platform.system() == "Windows"
EMOJI = {
    "check": "[OK]" if IS_WINDOWS else "✓",
}


def launch_command(args: argparse.Namespace, claude_args: list[str] | None = None) -> int:
    """Handle the launch command.

    Args:
        args: Parsed command line arguments.
        claude_args: Additional arguments to forward to Claude.

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

    # In UVX mode, Claude now runs from the current directory so no --add-dir needed

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
        return launcher.launch()
    return launcher.launch_interactive()


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

    # UVX helper command
    uvx_parser = subparsers.add_parser("uvx-help", help="Get help with UVX deployment")
    uvx_parser.add_argument("--find-path", action="store_true", help="Find UVX installation path")
    uvx_parser.add_argument("--info", action="store_true", help="Show UVX staging information")

    # Hidden local install command
    local_install_parser = subparsers.add_parser("_local_install", help=argparse.SUPPRESS)
    local_install_parser.add_argument("repo_root", help="Repository root directory")

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

    # Sync agents command
    sync_agents_parser = subparsers.add_parser(
        "sync-agents",
        help="Sync .claude/agents/ to .github/agents/ for Copilot CLI",
        epilog="Examples:\n"
        "  amplihack sync-agents                  # Sync agents with status check\n"
        "  amplihack sync-agents --force          # Force overwrite existing agents\n"
        "  amplihack sync-agents --dry-run        # Show what would be converted\n"
        "  amplihack sync-agents --verbose        # Show detailed output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sync_agents_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be converted without making changes"
    )
    sync_agents_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing agents in .github/agents/"
    )
    sync_agents_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed conversion output"
    )

    # Setup Copilot command
    setup_copilot_parser = subparsers.add_parser(
        "setup-copilot",
        help="Set up Copilot CLI integration with agent mirroring",
        epilog="Examples:\n"
        "  amplihack setup-copilot                # Complete Copilot setup\n"
        "  amplihack setup-copilot --skip-sync    # Set up without syncing agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    setup_copilot_parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip agent synchronization during setup"
    )

    # Copilot agent invocation
    copilot_agent_parser = subparsers.add_parser(
        "copilot-agent",
        help="Invoke a Copilot agent from .github/agents/",
        epilog="Examples:\n"
        "  amplihack copilot-agent architect 'Design authentication system'\n"
        "  amplihack copilot-agent builder 'Implement the login feature'\n"
        "  amplihack copilot-agent --list        # List available agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    copilot_agent_parser.add_argument(
        "agent_name",
        nargs="?",
        help="Agent name (e.g., architect, builder, tester)"
    )
    copilot_agent_parser.add_argument(
        "task",
        nargs="?",
        help="Task description for the agent"
    )
    copilot_agent_parser.add_argument(
        "--list",
        action="store_true",
        help="List all available agents"
    )
    copilot_agent_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed invocation output"
    )
    copilot_agent_parser.add_argument(
        "--files",
        nargs="+",
        help="Additional files to include (e.g., --files PHILOSOPHY.md PATTERNS.md)"
    )

    # List Copilot agents (alias for copilot-agent --list)
    list_copilot_agents_parser = subparsers.add_parser(
        "list-copilot-agents",
        help="List all available Copilot agents",
        epilog="Examples:\n"
        "  amplihack list-copilot-agents           # Show all agents\n"
        "  amplihack list-copilot-agents --verbose # Show detailed info",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    list_copilot_agents_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed agent information"
    )

    # Copilot workflow orchestration commands
    copilot_workflow_parser = subparsers.add_parser(
        "copilot-workflow",
        help="Execute amplihack workflows via Copilot CLI",
        epilog="Examples:\n"
        "  amplihack copilot-workflow DEFAULT_WORKFLOW \"Add authentication\"\n"
        "  amplihack copilot-workflow INVESTIGATION_WORKFLOW \"Understand auth flow\"\n"
        "  amplihack copilot-workflow --list      # List available workflows\n"
        "  amplihack copilot-workflow --sessions  # List active sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    copilot_workflow_parser.add_argument(
        "workflow_name",
        nargs="?",
        help="Workflow name (e.g., DEFAULT_WORKFLOW, INVESTIGATION_WORKFLOW)"
    )
    copilot_workflow_parser.add_argument(
        "task_description",
        nargs="?",
        help="Task description for workflow execution"
    )
    copilot_workflow_parser.add_argument(
        "--list",
        action="store_true",
        help="List available workflows"
    )
    copilot_workflow_parser.add_argument(
        "--sessions",
        action="store_true",
        help="List active workflow sessions"
    )
    copilot_workflow_parser.add_argument(
        "--start-step",
        type=int,
        default=0,
        help="Step number to start from (default: 0)"
    )

    # Copilot workflow resume command
    copilot_resume_parser = subparsers.add_parser(
        "copilot-resume",
        help="Resume workflow execution from checkpoint",
        epilog="Examples:\n"
        "  amplihack copilot-resume 20240115-143052\n"
        "  amplihack copilot-resume --list        # List resumable sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    copilot_resume_parser.add_argument(
        "session_id",
        nargs="?",
        help="Session ID to resume (format: YYYYMMDD-HHMMSS)"
    )
    copilot_resume_parser.add_argument(
        "--list",
        action="store_true",
        help="List resumable sessions"
    )

    # Sync commands command
    sync_commands_parser = subparsers.add_parser(
        "sync-commands",
        help="Sync .claude/commands/ to .github/commands/ for Copilot CLI",
        epilog="Examples:\n"
        "  amplihack sync-commands                  # Sync commands with status check\n"
        "  amplihack sync-commands --force          # Force overwrite existing commands\n"
        "  amplihack sync-commands --dry-run        # Show what would be converted\n"
        "  amplihack sync-commands --verbose        # Show detailed output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sync_commands_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be converted without making changes"
    )
    sync_commands_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing commands in .github/commands/"
    )
    sync_commands_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed conversion output"
    )

    # Copilot command invocation
    copilot_command_parser = subparsers.add_parser(
        "copilot-command",
        help="Invoke a Copilot CLI command from .github/commands/",
        epilog="Examples:\n"
        "  amplihack copilot-command amplihack/ultrathink 'analyze this'\n"
        "  amplihack copilot-command ddd/1-plan\n"
        "  amplihack copilot-command amplihack/fix import",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    copilot_command_parser.add_argument(
        "command_name",
        help="Command name (e.g., amplihack/ultrathink, ddd/1-plan)"
    )
    copilot_command_parser.add_argument(
        "args",
        nargs="*",
        help="Arguments to pass to the command"
    )
    copilot_command_parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Command timeout in seconds (default: 300)"
    )

    # List commands
    list_commands_parser = subparsers.add_parser(
        "list-commands",
        help="List all available Copilot commands",
        epilog="Examples:\n"
        "  amplihack list-commands                  # Show all commands\n"
        "  amplihack list-commands --category core  # Filter by category",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    list_commands_parser.add_argument(
        "--category",
        help="Filter by category (core, ddd, custom)"
    )

    return parser


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

        strategy_manager = SafeCopyStrategy()
        copy_strategy = strategy_manager.determine_target(
            original_target=os.path.join(original_cwd, ".claude"),
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

        # Store original_cwd for auto mode (always set, regardless of conflicts)
        os.environ["AMPLIHACK_ORIGINAL_CWD"] = original_cwd

        if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
            print(f"UVX mode: Staging Claude environment in current directory: {original_cwd}")
            print(f"Working directory remains: {original_cwd}")

        # Stage framework files to the current directory's .claude directory
        # Find the amplihack package location
        # Find amplihack package location for .claude files
        import amplihack

        amplihack_src = os.path.dirname(os.path.abspath(amplihack.__file__))

        # Copy .claude contents to temp .claude directory
        # Note: copytree_manifest copies TO the dst, not INTO dst/.claude
        copied = copytree_manifest(amplihack_src, temp_claude_dir, ".claude")

        # Bug #2 Fix: Detect empty copy results (Issue #1940)
        # When copytree_manifest returns empty list, no files were copied
        # This indicates a package installation problem - exit with clear error
        if not copied:
            print("\n❌ Failed to copy .claude files - cannot proceed")
            print(f"   Package location: {amplihack_src}")
            print(f"   Looking for .claude/ at: {amplihack_src}/.claude/")
            print("   This may indicate a package installation problem\n")
            sys.exit(1)

        # Smart PROJECT.md initialization for UVX mode
        if copied:
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

        # Create settings.json with relative paths (Claude will resolve relative to CLAUDE_PROJECT_DIR)
        # When CLAUDE_PROJECT_DIR is set, Claude will use settings.json from that directory only
        if copied:
            settings_path = os.path.join(temp_claude_dir, "settings.json")
            import json

            # Create minimal settings.json with just amplihack hooks
            settings = {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/session_start.py",
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
                                    "command": "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/stop.py",
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
                                    "command": "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/post_tool_use.py",
                                }
                            ],
                        }
                    ],
                    "PreCompact": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/pre_compact.py",
                                    "timeout": 30000,
                                }
                            ]
                        }
                    ],
                }
            }

            # Write settings.json
            os.makedirs(temp_claude_dir, exist_ok=True)
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=2)

            if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
                print(f"UVX staging completed to {temp_claude_dir}")
                print("Created settings.json with relative hook paths")

    args, claude_args = parse_args_with_passthrough(argv)

    if not args.command:
        # If we have claude_args but no command, default to launching Claude directly
        if claude_args:
            # If in UVX mode, ensure we use --add-dir for the ORIGINAL directory
            if is_uvx_deployment():
                # Get the original directory (before we changed to temp)
                original_cwd = os.environ.get("AMPLIHACK_ORIGINAL_CWD", os.getcwd())
                if "--add-dir" not in claude_args:
                    claude_args = ["--add-dir", original_cwd] + claude_args

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
        import subprocess
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

        # If in UVX mode, ensure we use --add-dir for the ORIGINAL directory
        if is_uvx_deployment():
            # Get the original directory (before we changed to temp)
            original_cwd = os.environ.get("AMPLIHACK_ORIGINAL_CWD", os.getcwd())
            # Add --add-dir to claude_args if not already present
            if claude_args and "--add-dir" not in claude_args:
                claude_args = ["--add-dir", original_cwd] + claude_args
            elif not claude_args:
                claude_args = ["--add-dir", original_cwd]

        # Handle auto mode
        exit_code = handle_auto_mode("claude", args, claude_args)
        if exit_code is not None:
            return exit_code

        return launch_command(args, claude_args)

    elif args.command == "claude":
        # Handle append mode FIRST (before any other initialization)
        if getattr(args, "append", None):
            return handle_append_instruction(args)

        # Claude is an alias for launch
        if is_uvx_deployment():
            original_cwd = os.environ.get("AMPLIHACK_ORIGINAL_CWD", os.getcwd())
            if claude_args and "--add-dir" not in claude_args:
                claude_args = ["--add-dir", original_cwd] + claude_args
            elif not claude_args:
                claude_args = ["--add-dir", original_cwd]

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
            original_cwd = os.environ.get("AMPLIHACK_ORIGINAL_CWD", os.getcwd())
            if claude_args and "--add-dir" not in claude_args:
                claude_args = ["--add-dir", original_cwd] + claude_args
            elif not claude_args:
                claude_args = ["--add-dir", original_cwd]

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

    elif args.command == "sync-agents":
        from pathlib import Path
        from .adapters.copilot_agent_converter import convert_agents

        # Check if dry-run
        if args.dry_run:
            print("Dry-run mode: No files will be modified")
            print()

        # Convert agents
        try:
            report = convert_agents(
                source_dir=Path(".claude/agents"),
                target_dir=Path(".github/agents"),
                force=args.force
            )

            # Display summary
            print(f"\nAgent Conversion Summary:")
            print(f"  Total agents: {report.total}")
            print(f"  {EMOJI['check']} Succeeded: {report.succeeded}")
            if report.failed > 0:
                print(f"  ✗ Failed: {report.failed}")
            if report.skipped > 0:
                print(f"  ⊘ Skipped: {report.skipped}")

            # Show errors if any
            if report.errors:
                print(f"\nErrors:")
                for error in report.errors:
                    print(f"  {error}")

            # Show detailed conversions if verbose
            if args.verbose:
                print(f"\nDetailed Results:")
                for conversion in report.conversions:
                    status_icon = {
                        "success": EMOJI['check'],
                        "failed": "✗",
                        "skipped": "⊘"
                    }[conversion.status]
                    print(f"  {status_icon} {conversion.agent_name} - {conversion.status}")
                    if conversion.reason:
                        print(f"     Reason: {conversion.reason}")

            # Show next steps
            if report.succeeded > 0:
                print(f"\nNext steps:")
                print(f"  1. Review converted agents in .github/agents/")
                print(f"  2. Check .github/agents/REGISTRY.json for agent catalog")
                print(f"  3. Use agents in Copilot CLI: copilot -p \"Include @.github/agents/core/architect.md -- Your task\"")

            # Return based on results
            return 0 if report.failed == 0 else 1

        except FileNotFoundError as e:
            print(f"Error: {str(e)}")
            return 1
        except PermissionError as e:
            print(f"Error: {str(e)}")
            return 1
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    elif args.command == "setup-copilot":
        from pathlib import Path

        print("\n" + "=" * 70)
        print("🚀 Copilot CLI Setup")
        print("=" * 70 + "\n")

        # Step 1: Create .github/ directory structure
        print("Step 1: Creating .github/ directory structure...")
        github_dir = Path(".github")
        github_dir.mkdir(exist_ok=True)
        agents_dir = github_dir / "agents"
        agents_dir.mkdir(exist_ok=True)
        commands_dir = github_dir / "commands"
        commands_dir.mkdir(exist_ok=True)
        hooks_dir = github_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        print(f"  {EMOJI['check']} Created {github_dir}/")
        print(f"  {EMOJI['check']} Created {agents_dir}/")
        print(f"  {EMOJI['check']} Created {commands_dir}/")
        print(f"  {EMOJI['check']} Created {hooks_dir}/")

        # Step 2: Sync agents (unless skipped)
        if not args.skip_sync:
            print("\nStep 2: Syncing agents from .claude/agents/ to .github/agents/...")
            try:
                from .adapters.copilot_agent_converter import convert_agents

                report = convert_agents(
                    source_dir=Path(".claude/agents"),
                    target_dir=agents_dir,
                    force=True
                )

                if report.succeeded > 0:
                    print(f"  {EMOJI['check']} Synced {report.succeeded} agents")
                    print(f"  {EMOJI['check']} Generated registry: {agents_dir}/REGISTRY.json")
                else:
                    print(f"  ✗ Sync failed: {report.errors}")
                    return 1

            except Exception as e:
                print(f"  ✗ Sync failed: {e}")
                return 1

            # Step 2.5: Sync commands
            print("\nStep 2.5: Syncing commands from .claude/commands/ to .github/commands/...")
            try:
                from .adapters.copilot_command_converter import convert_commands

                report = convert_commands(
                    source_dir=Path(".claude/commands"),
                    target_dir=commands_dir,
                    force=True
                )

                if report.succeeded > 0:
                    print(f"  {EMOJI['check']} Synced {report.succeeded} commands")
                    print(f"  {EMOJI['check']} Generated registry: {commands_dir}/COMMANDS_REGISTRY.json")
                else:
                    print(f"  ✗ Sync failed: {report.errors}")
                    return 1

            except Exception as e:
                print(f"  ✗ Sync failed: {e}")
                return 1

        else:
            print("\nStep 2: Skipped synchronization (--skip-sync)")

        # Step 3: Copy sample hook configurations (if they don't exist)
        print("\nStep 3: Setting up hook configurations...")
        sample_hooks = {
            "pre-commit.json": {
                "name": "pre-commit-review",
                "trigger": "pre-commit",
                "agent": "reviewer",
                "prompt": "Review staged changes for philosophy compliance",
                "files": [
                    "@.claude/context/PHILOSOPHY.md",
                    "@.claude/context/PATTERNS.md"
                ]
            },
            "amplihack-hooks.json": {
                "copilot_auto_sync_agents": "ask",
                "copilot_sync_on_startup": True
            }
        }

        for hook_file, content in sample_hooks.items():
            hook_path = hooks_dir / hook_file
            if not hook_path.exists():
                hook_path.write_text(json.dumps(content, indent=2))
                print(f"  {EMOJI['check']} Created {hook_path}")
            else:
                print(f"  ⊘ Skipped {hook_path} (already exists)")

        # Step 4: Print completion message with next steps
        print("\n" + "=" * 70)
        print("✅ Setup complete!")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Review .github/copilot-instructions.md")
        print("  2. Test agent invocation:")
        print("     copilot -p \"Your task\" -f @.github/agents/amplihack/core/architect.md")
        print("  3. Configure hooks in .github/hooks/amplihack-hooks.json")
        print("\nDocumentation:")
        print("  Full guide: COPILOT_CLI.md")
        print("  Agent reference: .github/agents/REGISTRY.json")
        print()

        return 0

    elif args.command == "sync-commands":
        from pathlib import Path
        from .adapters.copilot_command_converter import convert_commands

        if args.dry_run:
            print("Dry-run mode: No files will be modified\n")

        try:
            report = convert_commands(
                source_dir=Path(".claude/commands"),
                target_dir=Path(".github/commands"),
                force=args.force
            )

            print(f"\nCommand Conversion Summary:")
            print(f"  Total commands: {report.total}")
            print(f"  {EMOJI['check']} Succeeded: {report.succeeded}")
            if report.failed > 0:
                print(f"  ✗ Failed: {report.failed}")
            if report.skipped > 0:
                print(f"  ⊘ Skipped: {report.skipped}")

            if report.errors:
                print(f"\nErrors:")
                for error in report.errors:
                    print(f"  {error}")

            if args.verbose:
                print(f"\nDetailed Results:")
                for conversion in report.conversions:
                    status_icon = {
                        "success": EMOJI['check'],
                        "failed": "✗",
                        "skipped": "⊘"
                    }[conversion.status]
                    print(f"  {status_icon} {conversion.command_name} - {conversion.status}")
                    if conversion.reason:
                        print(f"     Reason: {conversion.reason}")

            if report.succeeded > 0:
                print(f"\nNext steps:")
                print(f"  1. Review converted commands in .github/commands/")
                print(f"  2. Check .github/commands/COMMANDS_REGISTRY.json")
                print(f"  3. Use: amplihack copilot-command amplihack/ultrathink 'task'")

            return 0 if report.failed == 0 else 1

        except (FileNotFoundError, PermissionError) as e:
            print(f"Error: {str(e)}")
            return 1
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    elif args.command == "copilot-command":
        from .copilot.command_wrapper import invoke_copilot_command

        try:
            result = invoke_copilot_command(
                command_name=args.command_name,
                args=args.args,
                timeout=args.timeout
            )

            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

            return result.returncode

        except FileNotFoundError as e:
            print(f"Error: {str(e)}")
            return 1
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return 1

    elif args.command == "list-commands":
        from pathlib import Path
        from .copilot.command_wrapper import list_available_commands
        import json

        try:
            commands = list_available_commands()

            if not commands:
                print("No commands found. Run 'amplihack sync-commands' first.")
                return 1

            registry_path = Path(".github/commands/COMMANDS_REGISTRY.json")
            registry = {}
            if registry_path.exists():
                registry_data = json.loads(registry_path.read_text())
                registry = {cmd['name']: cmd for cmd in registry_data['commands']}

            if args.category:
                commands = [
                    cmd for cmd in commands
                    if registry.get(cmd, {}).get('category') == args.category
                ]

            print(f"\nAvailable Copilot Commands ({len(commands)} total):")
            print("=" * 70)

            by_category = {}
            for cmd in commands:
                cmd_data = registry.get(cmd, {})
                category = cmd_data.get('category', 'unknown')
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append((cmd, cmd_data.get('description', '')))

            for category in sorted(by_category.keys()):
                print(f"\n{category.upper()}:")
                for cmd, desc in sorted(by_category[category]):
                    print(f"  {cmd}")
                    if desc:
                        print(f"    {desc}")

            print("\nUsage:")
            print("  amplihack copilot-command <command-name> [args...]")
            print("\nExample:")
            print("  amplihack copilot-command amplihack/ultrathink 'analyze code'")

            return 0

        except Exception as e:
            print(f"Error: {str(e)}")
            return 1

    elif args.command == "copilot-workflow":
        from pathlib import Path
        from .copilot import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()

        # Handle --list flag
        if args.list:
            workflows_dir = Path(".claude/workflow")
            if not workflows_dir.exists():
                print("No workflows directory found")
                return 1

            workflows = [f.stem for f in workflows_dir.glob("*.md") if f.stem not in ["README", "templates"]]
            print("\nAvailable Workflows:")
            for workflow in sorted(workflows):
                print(f"  - {workflow}")
            return 0

        # Handle --sessions flag
        if args.sessions:
            sessions = orchestrator.list_sessions()
            if not sessions:
                print("No active workflow sessions")
                return 0

            print("\nActive Workflow Sessions:")
            for session in sessions:
                print(f"\n  Session: {session['session_id']}")
                print(f"  Workflow: {session['workflow']}")
                print(f"  Progress: {session['steps_completed']}/{session['total_steps']} steps")
                print(f"  Current step: {session['current_step']}")
                print(f"  Created: {session['created']}")
            return 0

        # Execute workflow
        if not args.workflow_name or not args.task_description:
            print("Error: workflow_name and task_description are required")
            print("Usage: amplihack copilot-workflow WORKFLOW_NAME \"task description\"")
            return 1

        print(f"\n{'=' * 70}")
        print(f"Executing Workflow: {args.workflow_name}")
        print(f"{'=' * 70}")
        print(f"Task: {args.task_description}\n")

        result = orchestrator.execute_workflow(
            workflow_name=args.workflow_name,
            task_description=args.task_description,
            start_step=args.start_step,
        )

        if result.success:
            print(f"\n{EMOJI['check']} Workflow completed successfully!")
            print(f"  Session: {result.session_id}")
            print(f"  Steps completed: {result.steps_completed}/{result.total_steps}")
            print(f"  State saved: {result.state_path}")
            return 0
        else:
            print(f"\n✗ Workflow failed")
            print(f"  Session: {result.session_id}")
            print(f"  Steps completed: {result.steps_completed}/{result.total_steps}")
            print(f"  Failed at step: {result.current_step}")
            print(f"  Error: {result.error}")
            print(f"\nTo resume: amplihack copilot-resume {result.session_id}")
            return 1

    elif args.command == "copilot-resume":
        from .copilot import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()

        # Handle --list flag
        if args.list:
            sessions = orchestrator.list_sessions()
            if not sessions:
                print("No resumable workflow sessions")
                return 0

            print("\nResumable Workflow Sessions:")
            for session in sessions:
                print(f"\n  Session: {session['session_id']}")
                print(f"  Workflow: {session['workflow']}")
                print(f"  Progress: {session['steps_completed']}/{session['total_steps']} steps")
                print(f"  Current step: {session['current_step']}")
                print(f"  Created: {session['created']}")
            return 0

        # Resume workflow
        if not args.session_id:
            print("Error: session_id is required")
            print("Usage: amplihack copilot-resume SESSION_ID")
            print("Use --list to see available sessions")
            return 1

        print(f"\n{'=' * 70}")
        print(f"Resuming Workflow Session: {args.session_id}")
        print(f"{'=' * 70}\n")

        result = orchestrator.resume_workflow(args.session_id)

        if result.success:
            print(f"\n{EMOJI['check']} Workflow completed successfully!")
            print(f"  Session: {result.session_id}")
            print(f"  Steps completed: {result.steps_completed}/{result.total_steps}")
            print(f"  State saved: {result.state_path}")
            return 0
        else:
            print(f"\n✗ Workflow resume failed")
            print(f"  Session: {result.session_id}")
            print(f"  Steps completed: {result.steps_completed}/{result.total_steps}")
            print(f"  Failed at step: {result.current_step}")
            print(f"  Error: {result.error}")
            return 1

    else:
        create_parser().print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
