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


def launch_command(args: argparse.Namespace, claude_args: Optional[List[str]] = None) -> int:
    """Handle the launch command.

    Args:
        args: Parsed command line arguments.
        claude_args: Additional arguments to forward to Claude.

    Returns:
        Exit code.
    """
    # Check if Docker should be used (CLI flag takes precedence over env var)
    use_docker = getattr(args, "docker", False) or DockerManager.should_use_docker()

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
    )

    # Check if claude_args contains a prompt (-p) - if so, use non-interactive mode
    has_prompt = claude_args and ("-p" in claude_args)
    if has_prompt:
        return launcher.launch()
    return launcher.launch_interactive()


def handle_auto_mode(
    sdk: str, args: argparse.Namespace, cmd_args: Optional[List[str]]
) -> Optional[int]:
    """Handle auto mode for claude or copilot commands.

    Args:
        sdk: "claude" or "copilot"
        args: Parsed arguments
        cmd_args: Command arguments (for extracting prompt)

    Returns:
        Exit code if auto mode, None if not auto mode
    """
    if not getattr(args, "auto", False):
        return None

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

    auto = AutoMode(sdk, prompt, args.max_turns)
    return auto.run()


def handle_beads_command(args: argparse.Namespace) -> int:
    """Handle beads subcommands.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 = success, 1 = error)
    """
    import json
    from .memory import BeadsAdapter, BeadsMemoryProvider, BeadsPrerequisites

    # Check if beads command was specified
    if not hasattr(args, "beads_command") or args.beads_command is None:
        print("Error: No beads subcommand specified")
        print("Usage: amplihack beads {init,ready,create,list,update,close,get,status}")
        return 1

    # Handle status command (doesn't require beads to be installed)
    if args.beads_command == "status":
        status = BeadsPrerequisites.verify_setup()

        print("\nBeads Setup Status:")
        print(f"  Installed: {'✓' if status['beads_available'] else '✗'}")
        print(f"  Initialized: {'✓' if status['beads_initialized'] else '✗'}")
        print(f"  Version: {status['version'] or 'N/A'}")
        print(f"  Compatible: {'✓' if status['version_compatible'] else '✗'}")

        if status["errors"]:
            print("\nErrors:")
            for error in status["errors"]:
                print(f"  - {error}")

        if not status["beads_available"]:
            print("\nInstallation Required:")
            print("  Visit: https://github.com/steveyegge/beads")
            print("  Or run: brew install steveyegge/beads/beads")

        return 0

    # Handle init command (requires beads installed but not initialized)
    if args.beads_command == "init":
        result = BeadsPrerequisites.check_installed()
        if not result.is_ok or not result.value:
            print("Error: Beads not installed")
            print("\nInstallation instructions:")
            print("  Visit: https://github.com/steveyegge/beads")
            print("  Or run: brew install steveyegge/beads/beads")
            return 1

        init_result = BeadsPrerequisites.initialize()
        if not init_result.is_ok:
            print(f"Error: Failed to initialize beads: {init_result.error}")
            return 1

        print("✓ Beads initialized successfully")
        print("  Location: .beads/issues.jsonl")
        print("\nYou can now use beads commands:")
        print("  amplihack beads create --title 'Task name'")
        print("  amplihack beads ready")
        print("  amplihack beads list")
        return 0

    # All other commands require beads to be installed and initialized
    adapter = BeadsAdapter()

    if not adapter.is_available():
        print("Error: Beads CLI not found")
        print("\nInstallation instructions:")
        print("  Visit: https://github.com/steveyegge/beads")
        print("  Or run: brew install steveyegge/beads/beads")
        return 1

    if not adapter.check_init():
        print("Error: Beads not initialized in this directory")
        print("Run: amplihack beads init")
        return 1

    provider = BeadsMemoryProvider(adapter)

    # Handle each command
    try:
        if args.beads_command == "ready":
            # Show ready work (no blockers)
            labels = args.labels.split(",") if args.labels else None
            issues = provider.get_ready_work(assignee=args.assignee, labels=labels)

            # Apply limit if specified
            if args.limit and len(issues) > args.limit:
                issues = issues[: args.limit]

            if args.json:
                print(json.dumps(issues, indent=2))
            else:
                if not issues:
                    print("No ready work found")
                else:
                    print(f"\nReady Work ({len(issues)} issues):")
                    for issue in issues:
                        print(f"\n[{issue.get('id', 'N/A')}] {issue.get('title', 'Untitled')}")
                        if issue.get("labels"):
                            print(f"  Labels: {', '.join(issue['labels'])}")
                        if issue.get("assignee"):
                            print(f"  Assignee: {issue['assignee']}")
                        if issue.get("description"):
                            desc = issue["description"]
                            if len(desc) > 100:
                                desc = desc[:97] + "..."
                            print(f"  Description: {desc}")
            return 0

        if args.beads_command == "create":
            # Create issue
            labels = args.labels.split(",") if args.labels else None
            issue_id = provider.create_issue(
                title=args.title,
                description=args.description,
                status=args.status,
                labels=labels,
                assignee=args.assignee,
            )

            if args.json:
                print(json.dumps({"id": issue_id, "title": args.title}))
            else:
                print(f"✓ Created issue: {issue_id}")
                print(f"  Title: {args.title}")
                if args.labels:
                    print(f"  Labels: {args.labels}")
                if args.assignee:
                    print(f"  Assignee: {args.assignee}")
            return 0

        if args.beads_command == "list":
            # List issues
            labels = args.labels.split(",") if args.labels else None

            # Build query parameters
            query_kwargs = {}
            if args.status != "all":
                query_kwargs["status"] = args.status
            if args.assignee:
                query_kwargs["assignee"] = args.assignee
            if labels:
                query_kwargs["labels"] = labels

            issues = adapter.query_issues(**query_kwargs)

            # Apply limit if specified
            if args.limit and len(issues) > args.limit:
                issues = issues[: args.limit]

            if args.json:
                print(json.dumps(issues, indent=2))
            else:
                if not issues:
                    print("No issues found")
                else:
                    print(f"\nIssues ({len(issues)}):")
                    for issue in issues:
                        status = issue.get("status", "unknown")
                        print(
                            f"\n[{issue.get('id', 'N/A')}] {issue.get('title', 'Untitled')} ({status})"
                        )
                        if issue.get("labels"):
                            print(f"  Labels: {', '.join(issue['labels'])}")
                        if issue.get("assignee"):
                            print(f"  Assignee: {issue['assignee']}")
            return 0

        if args.beads_command == "get":
            # Get issue by ID
            issue = provider.get_issue(args.id)

            if not issue:
                print(f"Error: Issue not found: {args.id}")
                return 1

            if args.json:
                print(json.dumps(issue, indent=2))
            else:
                print(f"\nIssue: {issue.get('id', 'N/A')}")
                print(f"  Title: {issue.get('title', 'Untitled')}")
                print(f"  Status: {issue.get('status', 'unknown')}")
                if issue.get("description"):
                    print(f"  Description: {issue['description']}")
                if issue.get("labels"):
                    print(f"  Labels: {', '.join(issue['labels'])}")
                if issue.get("assignee"):
                    print(f"  Assignee: {issue['assignee']}")
                if issue.get("created_at"):
                    print(f"  Created: {issue['created_at']}")
            return 0

        if args.beads_command == "update":
            # Update issue
            update_kwargs = {}
            if args.status:
                update_kwargs["status"] = args.status
            if args.title:
                update_kwargs["title"] = args.title
            if args.description:
                update_kwargs["description"] = args.description
            if args.assignee:
                update_kwargs["assignee"] = args.assignee
            if args.labels:
                update_kwargs["labels"] = args.labels.split(",")

            success = provider.update_issue(args.id, **update_kwargs)

            if args.json:
                print(json.dumps({"success": success, "id": args.id}))
            else:
                if success:
                    print(f"✓ Updated issue: {args.id}")
                    for key, value in update_kwargs.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"Error: Failed to update issue: {args.id}")
                    return 1
            return 0

        if args.beads_command == "close":
            # Close issue
            success = provider.close_issue(args.id, resolution=args.resolution)

            if args.json:
                print(
                    json.dumps({"success": success, "id": args.id, "resolution": args.resolution})
                )
            else:
                if success:
                    print(f"✓ Closed issue: {args.id}")
                    print(f"  Resolution: {args.resolution}")
                else:
                    print(f"Error: Failed to close issue: {args.id}")
                    return 1
            return 0

        print(f"Error: Unknown beads command: {args.beads_command}")
        return 1

    except ValueError as e:
        print(f"Error: Invalid input: {e}")
        return 1
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: Unexpected error: {e}")
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

    # UVX helper command
    uvx_parser = subparsers.add_parser("uvx-help", help="Get help with UVX deployment")
    uvx_parser.add_argument("--find-path", action="store_true", help="Find UVX installation path")
    uvx_parser.add_argument("--info", action="store_true", help="Show UVX staging information")

    # Beads command
    beads_parser = subparsers.add_parser("beads", help="Beads issue tracking for AI agents")
    beads_subparsers = beads_parser.add_subparsers(dest="beads_command", help="Beads subcommands")

    # beads init
    _init_parser = beads_subparsers.add_parser("init", help="Initialize beads in current directory")

    # beads ready
    ready_parser = beads_subparsers.add_parser("ready", help="Show ready work (no blockers)")
    ready_parser.add_argument("--labels", help="Filter by labels (comma-separated)")
    ready_parser.add_argument("--assignee", help="Filter by assignee")
    ready_parser.add_argument(
        "--limit", type=int, default=10, help="Max issues to show (default: 10)"
    )
    ready_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # beads create
    create_parser = beads_subparsers.add_parser("create", help="Create new issue")
    create_parser.add_argument("--title", required=True, help="Issue title")
    create_parser.add_argument("--description", default="", help="Issue description")
    create_parser.add_argument("--labels", help="Labels (comma-separated)")
    create_parser.add_argument("--assignee", help="Assignee name")
    create_parser.add_argument("--status", default="open", help="Issue status (default: open)")
    create_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # beads list
    list_parser = beads_subparsers.add_parser("list", help="List issues")
    list_parser.add_argument(
        "--status",
        choices=["open", "closed", "in_progress", "blocked", "all"],
        default="open",
        help="Filter by status",
    )
    list_parser.add_argument("--labels", help="Filter by labels (comma-separated)")
    list_parser.add_argument("--assignee", help="Filter by assignee")
    list_parser.add_argument("--limit", type=int, help="Max issues to show")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # beads update
    update_parser = beads_subparsers.add_parser("update", help="Update issue")
    update_parser.add_argument("id", help="Issue ID")
    update_parser.add_argument("--status", help="New status")
    update_parser.add_argument("--title", help="New title")
    update_parser.add_argument("--description", help="New description")
    update_parser.add_argument("--assignee", help="New assignee")
    update_parser.add_argument("--labels", help="New labels (comma-separated)")
    update_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # beads close
    close_parser = beads_subparsers.add_parser("close", help="Close issue")
    close_parser.add_argument("id", help="Issue ID")
    close_parser.add_argument(
        "--resolution", default="completed", help="Closure resolution (default: completed)"
    )
    close_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # beads get
    get_parser = beads_subparsers.add_parser("get", help="Get issue by ID")
    get_parser.add_argument("id", help="Issue ID")
    get_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # beads status
    _status_parser = beads_subparsers.add_parser("status", help="Show beads setup status")

    # Hidden local install command
    _local_install_parser = subparsers.add_parser("_local_install", help=argparse.SUPPRESS)
    _local_install_parser.add_argument("repo_root", help="Repository root directory")

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

            launcher = ClaudeLauncher(claude_args=claude_args)
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

        # Handle auto mode
        exit_code = handle_auto_mode("copilot", args, claude_args)
        if exit_code is not None:
            return exit_code

        # Normal copilot launch
        has_prompt = claude_args and "-p" in claude_args
        return launch_copilot(claude_args, interactive=not has_prompt)

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

    elif args.command == "beads":
        return handle_beads_command(args)

    else:
        create_parser().print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
