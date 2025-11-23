"""Command-line interface for MCP manager.

Provides commands to list, enable, disable, and validate MCP servers.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .config_manager import backup_config, read_config, restore_config, write_config
from .mcp_operations import (
    MCPServer,
    disable_server,
    enable_server,
    list_servers,
    validate_config,
)


def get_config_path() -> Path:
    """Get the path to settings.json.

    Returns:
        Path to .claude/settings.json relative to worktree root
    """
    # Assume we're in .claude/scenarios/mcp-manager, go up to .claude
    scenarios_dir = Path(__file__).parent.parent.parent
    return scenarios_dir / "settings.json"


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format data as ASCII table.

    Args:
        headers: Column headers
        rows: Data rows

    Returns:
        Formatted table string
    """
    if not rows:
        return "No data to display"

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Build separator
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    # Build header
    header_cells = [f" {h:<{col_widths[i]}} " for i, h in enumerate(headers)]
    header_line = "|" + "|".join(header_cells) + "|"

    # Build data rows
    data_lines = []
    for row in rows:
        cells = [f" {str(cell):<{col_widths[i]}} " for i, cell in enumerate(row)]
        data_lines.append("|" + "|".join(cells) + "|")

    # Assemble table
    return "\n".join([separator, header_line, separator] + data_lines + [separator])


def cmd_list(args: argparse.Namespace) -> int:
    """List all MCP servers.

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        config_path = get_config_path()
        config = read_config(config_path)
        servers = list_servers(config)

        if not servers:
            print("No MCP servers configured")
            return 0

        # Prepare table data
        headers = ["Name", "Command", "Args", "Enabled", "Env Vars"]
        rows = []

        for server in servers:
            args_str = " ".join(server.args) if server.args else "(none)"
            enabled_str = "Yes" if server.enabled else "No"
            env_str = ", ".join(server.env.keys()) if server.env else "(none)"

            rows.append([
                server.name,
                server.command,
                args_str[:40] + "..." if len(args_str) > 40 else args_str,
                enabled_str,
                env_str[:30] + "..." if len(env_str) > 30 else env_str,
            ])

        print(format_table(headers, rows))
        return 0

    except Exception as e:
        print(f"Error listing servers: {e}", file=sys.stderr)
        return 1


def cmd_enable(args: argparse.Namespace) -> int:
    """Enable an MCP server.

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        config_path = get_config_path()

        # Read current config
        config = read_config(config_path)

        # Create backup
        backup_path = backup_config(config_path)
        print(f"Created backup: {backup_path.name}")

        try:
            # Enable server
            new_config = enable_server(config, args.name)

            # Validate before writing
            errors = validate_config(new_config)
            if errors:
                print("Validation errors:", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                raise ValueError("Configuration validation failed")

            # Write new config
            write_config(config_path, new_config)
            print(f"Successfully enabled server: {args.name}")
            return 0

        except Exception as e:
            # Rollback on error
            restore_config(backup_path, config_path)
            print(f"Error enabling server (rolled back): {e}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_disable(args: argparse.Namespace) -> int:
    """Disable an MCP server.

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        config_path = get_config_path()

        # Read current config
        config = read_config(config_path)

        # Create backup
        backup_path = backup_config(config_path)
        print(f"Created backup: {backup_path.name}")

        try:
            # Disable server
            new_config = disable_server(config, args.name)

            # Validate before writing
            errors = validate_config(new_config)
            if errors:
                print("Validation errors:", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                raise ValueError("Configuration validation failed")

            # Write new config
            write_config(config_path, new_config)
            print(f"Successfully disabled server: {args.name}")
            return 0

        except Exception as e:
            # Rollback on error
            restore_config(backup_path, config_path)
            print(f"Error disabling server (rolled back): {e}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate MCP configuration.

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        config_path = get_config_path()
        config = read_config(config_path)

        errors = validate_config(config)

        if not errors:
            print("✓ Configuration is valid")
            return 0
        else:
            print("Configuration validation errors:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error validating configuration: {e}", file=sys.stderr)
        return 1


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        prog="mcp-manager",
        description="Manage MCP server configurations",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List command
    subparsers.add_parser("list", help="List all MCP servers")

    # Enable command
    enable_parser = subparsers.add_parser("enable", help="Enable an MCP server")
    enable_parser.add_argument("name", help="Server name to enable")

    # Disable command
    disable_parser = subparsers.add_parser("disable", help="Disable an MCP server")
    disable_parser.add_argument("name", help="Server name to disable")

    # Validate command
    subparsers.add_parser("validate", help="Validate MCP configuration")

    # Parse arguments
    args = parser.parse_args(argv)

    # Dispatch to command handler
    if args.command == "list":
        return cmd_list(args)
    elif args.command == "enable":
        return cmd_enable(args)
    elif args.command == "disable":
        return cmd_disable(args)
    elif args.command == "validate":
        return cmd_validate(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
