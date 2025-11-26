"""Enhanced CLI for amplihack with proxy and launcher support."""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from .docker import DockerManager
from .launcher import ClaudeLauncher
from .proxy import ProxyConfig, ProxyManager
from .utils import is_uvx_deployment


def ensure_ultrathink_command(prompt: str) -> str:
    """Ensure prompt starts with /amplihack:ultrathink command for orchestration.

    If prompt already starts with a slash command, returns unchanged.
    Otherwise prepends /amplihack:ultrathink to enable workflow orchestration.

    Args:
        prompt: The user's prompt string.

    Returns:
        Transformed prompt with /amplihack:ultrathink prepended (or unchanged if already a slash command).

    Examples:
        >>> ensure_ultrathink_command("implement feature X")
        "/amplihack:ultrathink implement feature X"
        >>> ensure_ultrathink_command("/analyze src")
        "/analyze src"
        >>> ensure_ultrathink_command("  test  ")
        "/amplihack:ultrathink test"
    """
    # Strip whitespace
    prompt = prompt.strip()

    # Return empty if prompt is empty after stripping
    if not prompt:
        return ""

    # If starts with slash, it's already a command - return unchanged
    if prompt.startswith("/"):
        return prompt

    # Prepend ultrathink command for orchestration
    return f"/amplihack:ultrathink {prompt}"


def wrap_prompt_with_ultrathink(
    claude_args: Optional[List[str]], no_ultrathink: bool = False
) -> Optional[List[str]]:
    """Wrap prompt in claude_args with /amplihack:ultrathink command.

    Modifies the prompt passed via -p flag to use workflow orchestration.

    Args:
        claude_args: Command line arguments to pass to Claude (may contain -p prompt).
        no_ultrathink: If True, skip wrapping (for simple tasks or opt-out).

    Returns:
        Modified claude_args with wrapped prompt, or original if no prompt or opt-out.
    """
    # No-op if no args or opt-out
    if not claude_args or no_ultrathink:
        return claude_args

    # Find -p flag and wrap its value
    try:
        p_index = claude_args.index("-p")
        if p_index + 1 < len(claude_args):
            original_prompt = claude_args[p_index + 1]
            wrapped_prompt = ensure_ultrathink_command(original_prompt)

            # Only modify if transformation occurred
            if wrapped_prompt != original_prompt:
                # Create new list to avoid mutating original
                new_args = claude_args.copy()
                new_args[p_index + 1] = wrapped_prompt
                return new_args
    except ValueError:
        # -p flag not found, return unchanged
        pass

    return claude_args


def launch_command(args: argparse.Namespace, claude_args: Optional[List[str]] = None) -> int:
    """Handle the launch command.

    Args:
        args: Parsed command line arguments.
        claude_args: Additional arguments to forward to Claude.

    Returns:
        Exit code.
    """
    # Handle graph backend selection (new unified approach)
    graph_backend = getattr(args, "graph_backend", "auto")
    enable_neo4j = getattr(args, "enable_neo4j_memory", False)
    use_graph_mem = getattr(args, "use_graph_mem", False)  # Deprecated

    # Set environment variable for graph backend selection
    if graph_backend != "auto":
        os.environ["AMPLIHACK_GRAPH_BACKEND"] = graph_backend
        print(f"Graph backend set to: {graph_backend}")
    elif enable_neo4j or use_graph_mem:
        os.environ["AMPLIHACK_GRAPH_BACKEND"] = "neo4j"
        os.environ["AMPLIHACK_ENABLE_NEO4J_MEMORY"] = "1"
        if use_graph_mem:
            print(
                "WARNING: --use-graph-mem is deprecated. Please use --graph-backend neo4j instead."
            )
        print("Graph backend set to: neo4j")

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


def handle_auto_mode(
    sdk: str, args: argparse.Namespace, cmd_args: Optional[List[str]]
) -> Optional[int]:
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

    # Extract timeout from args
    query_timeout = getattr(args, "query_timeout_minutes", 5.0)

    auto = AutoMode(
        sdk, prompt, args.max_turns, ui_mode=ui_mode, query_timeout_minutes=query_timeout
    )
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
        print(f"✓ Instruction appended to session: {result.session_id}")
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
    argv: Optional[List[str]] = None,
) -> "tuple[argparse.Namespace, List[str]]":
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
    parser.add_argument(
        "--query-timeout-minutes",
        type=float,
        default=5.0,
        metavar="MINUTES",
        help=(
            "Timeout for each SDK query in minutes (default: 5.0). "
            "Prevents indefinite hangs in complex sessions. "
            "Use higher values (10-15) for very long-running operations."
        ),
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
    parser.add_argument(
        "--no-ultrathink",
        action="store_true",
        help="Skip /amplihack:ultrathink workflow orchestration for simple tasks. By default, all prompts are wrapped with /ultrathink for maximum effectiveness.",
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


def add_graph_backend_args(parser: argparse.ArgumentParser) -> None:
    """Add graph backend selection arguments to a parser.

    Args:
        parser: ArgumentParser to add arguments to.
    """
    parser.add_argument(
        "--graph-backend",
        choices=["kuzu", "neo4j", "auto"],
        default="auto",
        metavar="BACKEND",
        help=(
            "Select graph database backend for memory system. "
            "Options: kuzu (embedded, zero-config), neo4j (Docker), auto (default). "
            "Kùzu is auto-installed if needed."
        ),
    )
    parser.add_argument(
        "--enable-neo4j-memory",
        action="store_true",
        help="Enable Neo4j graph memory (alias for --graph-backend neo4j).",
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
    add_graph_backend_args(launch_parser)
    add_common_sdk_args(launch_parser)
    launch_parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Profile URI to use for this launch (overrides configured profile)",
    )

    # Claude command (alias for launch)
    claude_parser = subparsers.add_parser("claude", help="Launch Claude Code (alias for launch)")
    add_claude_specific_args(claude_parser)
    add_auto_mode_args(claude_parser)
    add_neo4j_args(claude_parser)
    add_graph_backend_args(claude_parser)
    add_common_sdk_args(claude_parser)
    claude_parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Profile URI to use for this launch (overrides configured profile)",
    )

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

    # Remote execution command
    remote_parser = subparsers.add_parser("remote", help="Execute on remote Azure VMs via azlin")
    remote_parser.add_argument("remote_command", choices=["auto", "ultrathink"], help="Command")
    remote_parser.add_argument("prompt", help="Task prompt")
    remote_parser.add_argument("--max-turns", type=int, default=10, help="Max turns")
    remote_parser.add_argument("--vm-size", default="m", help="VM size: s/m/l/xl")
    remote_parser.add_argument("--region", help="Azure region")
    remote_parser.add_argument("--keep-vm", action="store_true", help="Keep VM")
    remote_parser.add_argument("--timeout", type=int, default=120, help="Timeout")

    # Goal Agent Generator command
    new_parser = subparsers.add_parser(
        "new", help="Generate a new goal-seeking agent from a prompt file"
    )
    new_parser.add_argument(
        "--file", "-f", type=str, required=True, help="Path to prompt.md file containing goal"
    )
    new_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output directory for goal agent (default: ./goal_agents)",
    )
    new_parser.add_argument(
        "--name", "-n", type=str, default=None, help="Custom name for goal agent"
    )
    new_parser.add_argument(
        "--skills-dir",
        type=str,
        default=None,
        help="Custom skills directory (default: .claude/agents/amplihack)",
    )
    new_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    # Hidden local install command
    local_install_parser = subparsers.add_parser("_local_install", help=argparse.SUPPRESS)
    local_install_parser.add_argument("repo_root", help="Repository root directory")
    local_install_parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Profile URI to use for this install (overrides configured profile)",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
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

        # Check if user declined to proceed
        if not copy_strategy.should_proceed:
            print("\n❌ Cannot proceed without updating .claude/ directory")
            print("   Commit your changes and try again\n")
            sys.exit(1)

        temp_claude_dir = str(copy_strategy.target_dir)

        # Set CLAUDE_PROJECT_DIR to help Claude Code find .claude directory
        # Needed for both temp mode (hooks) and working mode (command discovery)
        os.environ["CLAUDE_PROJECT_DIR"] = str(copy_strategy.target_dir.parent)
        if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
            mode = "temp" if copy_strategy.use_temp else "working"
            print(f"Set CLAUDE_PROJECT_DIR={copy_strategy.target_dir.parent} ({mode} mode)")

        # Store original_cwd for auto mode (always set, regardless of conflicts)
        os.environ["AMPLIHACK_ORIGINAL_CWD"] = original_cwd

        if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
            print(f"UVX mode: Staging Claude environment in current directory: {original_cwd}")
            print(f"Working directory remains: {original_cwd}")

        # Stage framework files to the current directory's .claude directory
        # Find the amplihack package location
        import amplihack

        from . import ESSENTIAL_DIRS, copytree_manifest

        amplihack_src = os.path.dirname(os.path.abspath(amplihack.__file__))

        # NEW: Create staging manifest based on profile (if available)
        manifest = None
        profile_uri = os.environ.get("AMPLIHACK_PROFILE")

        if profile_uri:
            try:
                # Try to load profile for filtering
                claude_tools_path = os.path.join(amplihack_src, ".claude", "tools", "amplihack")
                if os.path.exists(claude_tools_path):
                    sys.path.insert(0, claude_tools_path)
                    from profile_management.staging import create_staging_manifest

                    manifest = create_staging_manifest(ESSENTIAL_DIRS, profile_uri)
                    if manifest.profile_name != "all" and not manifest.profile_name.endswith(
                        "(fallback)"
                    ):
                        print(f"📦 Using profile: {manifest.profile_name}")
            except Exception as e:
                # Fall back to full staging on errors
                print(f"ℹ️  Profile loading failed ({e}), using full staging")

        # Copy .claude contents to temp .claude directory
        # Note: copytree_manifest copies TO the dst, not INTO dst/.claude
        copied = copytree_manifest(amplihack_src, temp_claude_dir, ".claude", manifest=manifest)

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

        # Create settings.json with appropriate paths based on staging mode
        if copied:
            settings_path = os.path.join(temp_claude_dir, "settings.json")
            import json

            # Load settings from template (includes statusLine and all hooks)
            template_path = Path(__file__).parent / "utils" / "uvx_settings_template.json"
            try:
                with open(template_path) as f:
                    settings = json.load(f)

                # Always replace relative paths with $CLAUDE_PROJECT_DIR for UVX mode
                # This ensures Claude Code can find .claude regardless of working directory
                def replace_paths(obj):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if (
                                key == "command"
                                and isinstance(value, str)
                                and value.startswith(".claude/")
                            ):
                                obj[key] = value.replace(".claude/", "$CLAUDE_PROJECT_DIR/.claude/")
                            else:
                                replace_paths(value)
                    elif isinstance(obj, list):
                        for item in obj:
                            replace_paths(item)

                replace_paths(settings)

            except (FileNotFoundError, json.JSONDecodeError) as e:
                # Fallback to minimal settings if template not found
                print(f"Warning: Could not load settings template: {e}", file=sys.stderr)
                # Always use $CLAUDE_PROJECT_DIR in UVX mode
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
                    }
                }

            # Write settings.json
            os.makedirs(temp_claude_dir, exist_ok=True)
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=2)

            if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
                print(f"UVX staging completed to {temp_claude_dir}")
                print("Created settings.json with $CLAUDE_PROJECT_DIR paths")

    args, claude_args = parse_args_with_passthrough(argv)

    # Wrap prompts with /amplihack:ultrathink by default (unless --no-ultrathink is set)
    # This enables workflow orchestration for all prompts
    no_ultrathink = getattr(args, "no_ultrathink", False)
    claude_args = wrap_prompt_with_ultrathink(claude_args, no_ultrathink)

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
        # Install from the package's .claude directory (wherever uvx installed it)
        # This ensures we use the exact version the user installed via uvx --from git+...@branch

        # Find package location using __file__
        # __file__ is amplihack/cli.py, so parent is amplihack/
        package_dir = Path(__file__).resolve().parent
        claude_source = package_dir / ".claude"

        if claude_source.exists():
            # Use package's .claude directory (amplihack/.claude/)
            # _local_install expects repo root, so pass package_dir (which contains .claude/)
            _local_install(str(package_dir))
            return 0
        # Fallback: Clone from GitHub (for old installations)
        import subprocess
        import tempfile

        print("⚠️  Package .claude/ not found, cloning from GitHub...")
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
        profile_uri = getattr(args, "profile", None)
        _local_install(args.repo_root, profile_uri=profile_uri)
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

    elif args.command == "new":
        from .goal_agent_generator.cli import new_goal_agent

        # Convert string paths to Path objects
        file_path = Path(args.file)
        output_path = Path(args.output) if args.output else None
        skills_path = Path(args.skills_dir) if args.skills_dir else None

        # Call the goal agent generator CLI
        return new_goal_agent.callback(
            file=file_path,
            output=output_path,
            name=args.name,
            skills_dir=skills_path,
            verbose=args.verbose,
        )

    elif args.command == "remote":
        # Execute remote command
        claude_dir = Path.cwd() / ".claude"
        if not claude_dir.exists():
            print("Error: .claude directory not found", file=sys.stderr)
            return 1

        sys.path.insert(0, str(claude_dir / "tools" / "amplihack"))

        try:
            from remote.cli import execute_remote_workflow
            from remote.orchestrator import VMOptions

            vm_options = VMOptions(
                size=args.vm_size,
                region=args.region,
                keep_vm=args.keep_vm,
            )

            execute_remote_workflow(
                repo_path=Path.cwd(),
                command=args.remote_command,
                prompt=args.prompt,
                max_turns=args.max_turns,
                vm_options=vm_options,
                timeout=args.timeout,
            )
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    else:
        create_parser().print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
