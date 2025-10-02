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

    # If in UVX mode, ensure we use --add-dir for the ORIGINAL directory
    if is_uvx_deployment():
        original_cwd = os.environ.get("AMPLIHACK_ORIGINAL_CWD", os.getcwd())
        # Validate the original CWD before using it
        validated_cwd = _validate_and_sanitize_path(original_cwd, "AMPLIHACK_ORIGINAL_CWD")
        if validated_cwd and "--add-dir" not in (claude_args or []):
            claude_args = ["--add-dir", validated_cwd] + (claude_args or [])
        elif not validated_cwd:
            print(
                "Warning: Could not validate AMPLIHACK_ORIGINAL_CWD, using current directory",
                file=sys.stderr,
            )
            claude_args = ["--add-dir", os.getcwd()] + (claude_args or [])

    proxy_manager = None
    system_prompt_path = None

    # Set up proxy if configuration provided
    if args.with_proxy_config:
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

    return launcher.launch_interactive()


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
  amplihack install -- --verbose             # Install with Claude args forwarded""",
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
        "--checkout-repo",
        metavar="GITHUB_URI",
        help="Clone a GitHub repository and use it as working directory. Supports: owner/repo, https://github.com/owner/repo, git@github.com:owner/repo",
    )
    launch_parser.add_argument(
        "--docker",
        action="store_true",
        help="Run amplihack in Docker container for isolated execution",
    )

    # UVX helper command
    uvx_parser = subparsers.add_parser("uvx-help", help="Get help with UVX deployment")
    uvx_parser.add_argument("--find-path", action="store_true", help="Find UVX installation path")
    uvx_parser.add_argument("--info", action="store_true", help="Show UVX staging information")

    # Hidden local install command
    local_install_parser = subparsers.add_parser("_local_install", help=argparse.SUPPRESS)
    local_install_parser.add_argument("repo_root", help="Repository root directory")

    return parser


def _validate_and_sanitize_path(path: str, var_name: str) -> Optional[str]:
    """Validate and sanitize path with security hardening.

    Args:
        path: Path to validate
        var_name: Variable name for logging

    Returns:
        Sanitized path if valid, None if invalid
    """
    try:
        if not path or not isinstance(path, str):
            return None

        # Basic security checks
        if len(path) > 4096:  # Max path length
            print(f"Warning: {var_name} exceeds maximum length", file=sys.stderr)
            return None

        # Path traversal protection
        if ".." in path or path.count("/") > 20:
            print(f"Warning: {var_name} contains suspicious path patterns", file=sys.stderr)
            return None

        # Must be absolute path
        if not os.path.isabs(path):
            print(f"Warning: {var_name} must be absolute path", file=sys.stderr)
            return None

        # Character validation (allow common path characters)
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/_.-~")
        if not all(c in allowed_chars for c in path):
            print(f"Warning: {var_name} contains invalid characters", file=sys.stderr)
            return None

        return path.strip()

    except Exception:
        return None


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for amplihack CLI.

    Args:
        argv: Command line arguments. Uses sys.argv if None.

    Returns:
        Exit code.
    """
    # Initialize UVX staging if needed (before parsing args)
    if is_uvx_deployment():
        import tempfile

        temp_dir = tempfile.mkdtemp(prefix="amplihack_uvx_")
        temp_claude_dir = os.path.join(temp_dir, ".claude")
        original_cwd = os.getcwd()

        # Validate and sanitize the original working directory
        validated_cwd = _validate_and_sanitize_path(original_cwd, "AMPLIHACK_ORIGINAL_CWD")
        if not validated_cwd:
            print("Error: Invalid working directory for UVX deployment", file=sys.stderr)
            return 1

        # Set required environment variables with validated paths
        os.environ["AMPLIHACK_ORIGINAL_CWD"] = validated_cwd
        os.environ["UVX_LAUNCH_DIRECTORY"] = validated_cwd
        os.chdir(temp_dir)

        if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
            print(f"UVX mode: Created temp Claude environment at {temp_dir}")
            print(f"Changed working directory to {temp_dir}")

        # Stage framework files to the temp .claude directory
        # Use the built-in _local_install function to copy framework files
        # Find the amplihack package location
        from . import copytree_manifest

        amplihack_src = None
        for path in sys.path:
            test_path = os.path.join(path, "amplihack", ".claude")
            if os.path.exists(test_path):
                amplihack_src = os.path.join(path, "amplihack")
                break

        if amplihack_src:
            copied = copytree_manifest(amplihack_src, temp_claude_dir, ".claude")
            if copied:
                settings_path = os.path.join(temp_claude_dir, "settings.json")
                import json

                # Create settings.json with amplihack hooks
                settings = {
                    "hooks": {
                        "SessionStart": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": ".claude/tools/amplihack/hooks/session_start.py",
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
                                        "command": ".claude/tools/amplihack/hooks/stop.py",
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
                                        "command": ".claude/tools/amplihack/hooks/post_tool_use.py",
                                    }
                                ],
                            }
                        ],
                        "PreCompact": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": ".claude/tools/amplihack/hooks/pre_compact.py",
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
                original_cwd = os.environ.get("AMPLIHACK_ORIGINAL_CWD", os.getcwd())
                # Validate the original CWD before using it
                validated_cwd = _validate_and_sanitize_path(original_cwd, "AMPLIHACK_ORIGINAL_CWD")
                if validated_cwd and "--add-dir" not in claude_args:
                    claude_args = ["--add-dir", validated_cwd] + claude_args
                elif not validated_cwd:
                    print(
                        "Warning: Could not validate AMPLIHACK_ORIGINAL_CWD, using current directory",
                        file=sys.stderr,
                    )
                    if "--add-dir" not in claude_args:
                        claude_args = ["--add-dir", os.getcwd()] + claude_args

            # Check if Docker should be used for direct launch
            if DockerManager.should_use_docker():
                print("Docker mode enabled via AMPLIHACK_USE_DOCKER")
                docker_manager = DockerManager()
                docker_args = ["launch", "--"] + claude_args
                return docker_manager.run_command(docker_args)

            launcher = ClaudeLauncher(claude_args=claude_args)
            return launcher.launch_interactive()
        else:
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
        return launch_command(args, claude_args)

    elif args.command == "uvx-help":
        from .commands.uvx_helper import find_uvx_installation_path, print_uvx_usage_instructions

        if args.find_path:
            path = find_uvx_installation_path()
            if path:
                print(str(path))
                return 0
            else:
                print("UVX installation path not found", file=sys.stderr)
                return 1
        elif args.info:
            # Show UVX staging information
            print("\nUVX Information:")
            print(f"  Is UVX: {is_uvx_deployment()}")
            print("\nEnvironment Variables:")
            print(f"  AMPLIHACK_ROOT={os.environ.get('AMPLIHACK_ROOT', '(not set)')}")
            return 0
        else:
            print_uvx_usage_instructions()
            return 0

    else:
        create_parser().print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
