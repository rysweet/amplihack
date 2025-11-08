"""Enhanced CLI for amplihack with proxy and launcher support."""

import argparse
import os
import sys
from pathlib import Path
from typing import Callable, List, Optional

from .docker import DockerManager
from .launcher import ClaudeLauncher
from .proxy import ProxyConfig, ProxyManager
from .utils import is_uvx_deployment


def launch_command(args: argparse.Namespace, claude_args: Optional[List[str]] = None) -> int:
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


def handle_sdk_command(
    sdk: str,
    args: argparse.Namespace,
    claude_args: Optional[List[str]],
    launch_func: Callable,
    use_interactive_flag: bool = False,
) -> int:
    """Handle common SDK command logic for launch/claude/copilot/codex.

    Args:
        sdk: SDK name ("claude", "copilot", "codex")
        args: Parsed command line arguments
        claude_args: Additional arguments to forward to the SDK
        launch_func: Function to call for launching the SDK
        use_interactive_flag: If True, call launch_func(claude_args, interactive=bool)
                             If False, call launch_func(args, claude_args)

    Returns:
        Exit code
    """
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
    exit_code = handle_auto_mode(sdk, args, claude_args)
    if exit_code is not None:
        return exit_code

    # Handle --no-reflection flag (disable always wins priority)
    if getattr(args, "no_reflection", False):
        os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    # Launch the SDK with appropriate signature
    if use_interactive_flag:
        # For copilot/codex: launch_func(claude_args, interactive=bool)
        has_prompt = claude_args and "-p" in claude_args
        return launch_func(claude_args, interactive=not has_prompt)
    else:
        # For launch/claude: launch_func(args, claude_args)
        return launch_func(args, claude_args)


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
    launch_parser.add_argument(
        "--with-proxy-config",
        metavar="PATH",
        help="Path to .env file with proxy configuration (for Azure OpenAI integration with auto persistence prompt)",
    )
    launch_parser.add_argument(
        "--builtin-proxy",
        action="store_true",
        help="Use built-in proxy server with OpenAI Responses API support instead of external claude-code-proxy",
    )
    launch_parser.add_argument(
        "--checkout-repo",
        metavar="GITHUB_URI",
        help="Clone a GitHub repository and use it as working directory. Supports: owner/repo, https://github.com/owner/repo, git@github.com:owner/repo",
    )
    launch_parser.add_argument(
        "--docker",
        action="store_true",
        help="Run amplihack in Docker container for isolated execution",
    )
    launch_parser.add_argument(
        "--auto",
        action="store_true",
        help="Run in autonomous agentic mode with iterative loop (clarify → plan → execute → evaluate). Usage: --auto -- -p 'your task'. See docs/AUTO_MODE.md for details.",
    )
    launch_parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Max turns for auto mode (default: 10). Guidance: 5-10 for simple tasks, 10-15 for medium complexity, 15-30 for complex tasks.",
    )
    launch_parser.add_argument(
        "--append",
        metavar="PROMPT",
        help="Append new instructions to a running auto mode session. Finds the active auto mode log directory in the current project and injects the new prompt.",
    )
    launch_parser.add_argument(
        "--ui",
        action="store_true",
        help="Enable interactive UI mode for auto mode (requires Rich library). Shows real-time execution state, logs, and allows prompt injection.",
    )
    launch_parser.add_argument(
        "--use-graph-mem",
        action="store_true",
        help="Enable Neo4j graph memory system (opt-in). Requires Docker. See docs/NEO4J.md for setup.",
    )
    launch_parser.add_argument(
        "--use-memory-db",
        metavar="NAME",
        help="Specify Neo4j container name (e.g., amplihack-myproject). Works with --use-graph-mem.",
    )
    launch_parser.add_argument(
        "--no-reflection",
        action="store_true",
        help="Disable post-session reflection analysis. Reflection normally runs after sessions to capture insights and learnings.",
    )

    # Claude command (alias for launch)
    claude_parser = subparsers.add_parser("claude", help="Launch Claude Code (alias for launch)")
    claude_parser.add_argument("--with-proxy-config", metavar="PATH")
    claude_parser.add_argument("--builtin-proxy", action="store_true")
    claude_parser.add_argument("--checkout-repo", metavar="GITHUB_URI")
    claude_parser.add_argument("--docker", action="store_true")
    claude_parser.add_argument(
        "--auto",
        action="store_true",
        help="Run in autonomous agentic mode. Usage: --auto -- -p 'your task'. See docs/AUTO_MODE.md for details.",
    )
    claude_parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Max turns for auto mode (default: 10). Guidance: 5-10 for simple tasks, 10-15 for medium complexity, 15-30 for complex tasks.",
    )
    claude_parser.add_argument(
        "--append",
        metavar="PROMPT",
        help="Append new instructions to a running auto mode session. Finds the active auto mode log directory in the current project and injects the new prompt.",
    )
    claude_parser.add_argument(
        "--ui",
        action="store_true",
        help="Enable interactive UI mode for auto mode (requires Rich library). Shows real-time execution state, logs, and allows prompt injection.",
    )
    claude_parser.add_argument(
        "--use-graph-mem",
        action="store_true",
        help="Enable Neo4j graph memory system (opt-in). Requires Docker. See docs/NEO4J.md for setup.",
    )
    claude_parser.add_argument(
        "--use-memory-db",
        metavar="NAME",
        help="Specify Neo4j container name (e.g., amplihack-myproject). Works with --use-graph-mem.",
    )
    claude_parser.add_argument(
        "--no-reflection",
        action="store_true",
        help="Disable post-session reflection analysis. Reflection normally runs after sessions to capture insights and learnings.",
    )

    # Copilot command
    copilot_parser = subparsers.add_parser("copilot", help="Launch GitHub Copilot CLI")
    copilot_parser.add_argument(
        "--auto",
        action="store_true",
        help="Run in autonomous agentic mode. Usage: --auto -- -p 'your task'. See docs/AUTO_MODE.md for details.",
    )
    copilot_parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Max turns for auto mode (default: 10). Guidance: 5-10 for simple tasks, 10-15 for medium complexity, 15-30 for complex tasks.",
    )
    copilot_parser.add_argument(
        "--append",
        metavar="PROMPT",
        help="Append new instructions to a running auto mode session. Finds the active auto mode log directory in the current project and injects the new prompt.",
    )
    copilot_parser.add_argument(
        "--ui",
        action="store_true",
        help="Enable interactive UI mode for auto mode (requires Rich library). Shows real-time execution state, logs, and allows prompt injection.",
    )
    copilot_parser.add_argument(
        "--no-reflection",
        action="store_true",
        help="Disable post-session reflection analysis. Reflection normally runs after sessions to capture insights and learnings.",
    )

    # Codex command
    codex_parser = subparsers.add_parser("codex", help="Launch OpenAI Codex CLI")
    codex_parser.add_argument(
        "--auto",
        action="store_true",
        help="Run in autonomous agentic mode. Usage: --auto -- -p 'your task'. See docs/AUTO_MODE.md for details.",
    )
    codex_parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Max turns for auto mode (default: 10). Guidance: 5-10 for simple tasks, 10-15 for medium complexity, 15-30 for complex tasks.",
    )
    codex_parser.add_argument(
        "--append",
        metavar="PROMPT",
        help="Append new instructions to a running auto mode session. Finds the active auto mode log directory in the current project and injects the new prompt.",
    )
    codex_parser.add_argument(
        "--ui",
        action="store_true",
        help="Enable interactive UI mode for auto mode (requires Rich library). Shows real-time execution state, logs, and allows prompt injection.",
    )
    codex_parser.add_argument(
        "--no-reflection",
        action="store_true",
        help="Disable post-session reflection analysis. Reflection normally runs after sessions to capture insights and learnings.",
    )

    # UVX helper command
    uvx_parser = subparsers.add_parser("uvx-help", help="Get help with UVX deployment")
    uvx_parser.add_argument("--find-path", action="store_true", help="Find UVX installation path")
    uvx_parser.add_argument("--info", action="store_true", help="Show UVX staging information")

    # Hidden local install command
    local_install_parser = subparsers.add_parser("_local_install", help=argparse.SUPPRESS)
    local_install_parser.add_argument("repo_root", help="Repository root directory")

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

        # Store it for later use (though now it's the same as current directory)
        os.environ["AMPLIHACK_ORIGINAL_CWD"] = original_cwd

        # Use .claude directory in current working directory instead of temp
        temp_claude_dir = os.path.join(original_cwd, ".claude")

        if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
            print(f"UVX mode: Staging Claude environment in current directory: {original_cwd}")
            print(f"Working directory remains: {original_cwd}")

        # Stage framework files to the current directory's .claude directory
        # Find the amplihack package location
        # Find amplihack package location for .claude files
        import amplihack

        from . import copytree_manifest

        amplihack_src = os.path.dirname(os.path.abspath(amplihack.__file__))

        # Copy .claude contents to temp .claude directory
        # Note: copytree_manifest copies TO the dst, not INTO dst/.claude
        copied = copytree_manifest(amplihack_src, temp_claude_dir, ".claude")

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
        return handle_sdk_command("claude", args, claude_args, launch_command)

    elif args.command == "claude":
        return handle_sdk_command("claude", args, claude_args, launch_command)

    elif args.command == "copilot":
        from .launcher.copilot import launch_copilot

        return handle_sdk_command("copilot", args, claude_args, launch_copilot, use_interactive_flag=True)

    elif args.command == "codex":
        from .launcher.codex import launch_codex

        return handle_sdk_command("codex", args, claude_args, launch_codex, use_interactive_flag=True)

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

    else:
        create_parser().print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
