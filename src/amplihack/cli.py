"""Enhanced CLI for amplihack with proxy and launcher support."""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from .launcher import ClaudeLauncher
from .proxy import ProxyConfig, ProxyManager
from .utils import is_uvx_deployment, stage_uvx_framework


def launch_command(args: argparse.Namespace) -> int:
    """Handle the launch command.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code.
    """
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
    )

    return launcher.launch_interactive()


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for amplihack CLI.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="amplihack", description="Amplihack CLI - Enhanced tools for Claude Code development"
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

    # UVX helper command
    uvx_parser = subparsers.add_parser("uvx-help", help="Get help with UVX deployment")
    uvx_parser.add_argument("--find-path", action="store_true", help="Find UVX installation path")
    uvx_parser.add_argument("--info", action="store_true", help="Show UVX staging information")

    # Hidden local install command
    local_install_parser = subparsers.add_parser("_local_install", help=argparse.SUPPRESS)
    local_install_parser.add_argument("repo_root", help="Repository root directory")

    return parser


def main(argv: Optional[list] = None) -> int:
    """Main entry point for amplihack CLI.

    Args:
        argv: Command line arguments. Uses sys.argv if None.

    Returns:
        Exit code.
    """
    # Initialize UVX staging if needed (before parsing args)
    if is_uvx_deployment():
        if stage_uvx_framework():
            if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
                print("UVX staging completed")

    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
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
        return launch_command(args)

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
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
