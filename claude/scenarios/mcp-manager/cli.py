"""Command-line interface for MCP manager.

Provides commands to list, enable, disable, and validate MCP servers.
"""

import argparse
import sys
from pathlib import Path

from .config_manager import backup_config, read_config, restore_config, write_config
from .mcp_operations import (
    MCPServer,
    add_server,
    disable_server,
    enable_server,
    export_servers,
    get_server,
    import_servers,
    list_servers,
    remove_server,
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
        cells = [f" {cell!s:<{col_widths[i]}} " for i, cell in enumerate(row)]
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

            rows.append(
                [
                    server.name,
                    server.command,
                    args_str[:40] + "..." if len(args_str) > 40 else args_str,
                    enabled_str,
                    env_str[:30] + "..." if len(env_str) > 30 else env_str,
                ]
            )

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
        print("Configuration validation errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Error validating configuration: {e}", file=sys.stderr)
        return 1


def cmd_add(args: argparse.Namespace) -> int:
    """Add a new MCP server.

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Interactive prompts for missing information
        name = args.name
        if not name:
            name = input("Server name (lowercase, no spaces): ").strip()

        command = args.server_command
        if not command:
            command = input("Command to execute: ").strip()

        # Get args (may be empty)
        server_args = args.server_args if args.server_args else []

        # Parse environment variables
        env_vars = {}
        if args.env:
            for env_str in args.env:
                if "=" not in env_str:
                    print(f"Invalid environment variable format: {env_str}", file=sys.stderr)
                    print("Format should be KEY=VALUE", file=sys.stderr)
                    return 1
                key, value = env_str.split("=", 1)
                env_vars[key] = value

        # Determine enabled state
        enabled = not args.disabled

        # Create server object
        server = MCPServer(
            name=name,
            command=command,
            args=server_args,
            enabled=enabled,
            env=env_vars,
        )

        # Read current config
        config_path = get_config_path()
        config = read_config(config_path)

        # Create backup
        backup_path = backup_config(config_path)
        print(f"Created backup: {backup_path.name}")

        try:
            # Add server
            new_config = add_server(config, server)

            # Validate before writing
            errors = validate_config(new_config)
            if errors:
                print("Validation errors:", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                raise ValueError("Configuration validation failed")

            # Write new config
            write_config(config_path, new_config)
            status = "disabled" if not enabled else "enabled"
            print(f"Successfully added server: {name} ({status})")
            return 0

        except ValueError as e:
            restore_config(backup_path, config_path)
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            restore_config(backup_path, config_path)
            print(f"Error adding server (rolled back): {e}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_remove(args: argparse.Namespace) -> int:
    """Remove an MCP server.

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        config_path = get_config_path()
        config = read_config(config_path)

        # Check if server exists first
        server = get_server(config, args.name)
        if not server:
            print(f"Server not found: {args.name}", file=sys.stderr)
            return 1

        # Confirm deletion unless --force
        if not args.force:
            print(f"\nServer to remove: {args.name}")
            print(f"  Command: {server.command}")
            print(f"  Args: {' '.join(server.args) if server.args else '(none)'}")
            response = input("\nAre you sure you want to remove this server? (y/N): ")
            if response.lower() not in ("y", "yes"):
                print("Cancelled")
                return 0

        # Create backup
        backup_path = backup_config(config_path)
        print(f"Created backup: {backup_path.name}")

        try:
            # Remove server
            new_config = remove_server(config, args.name)

            # Validate before writing
            errors = validate_config(new_config)
            if errors:
                print("Validation errors:", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                raise ValueError("Configuration validation failed")

            # Write new config
            write_config(config_path, new_config)
            print(f"Successfully removed server: {args.name}")
            return 0

        except ValueError as e:
            restore_config(backup_path, config_path)
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            restore_config(backup_path, config_path)
            print(f"Error removing server (rolled back): {e}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_show(args: argparse.Namespace) -> int:
    """Show detailed server information.

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        config_path = get_config_path()
        config = read_config(config_path)

        server = get_server(config, args.name)
        if not server:
            print(f"Server not found: {args.name}", file=sys.stderr)
            return 1

        # Display detailed information
        print(f"\nServer: {server.name}")
        print("=" * (len(server.name) + 8))
        print(f"Command:  {server.command}")
        print(f"Args:     {' '.join(server.args) if server.args else '(none)'}")
        print(f"Enabled:  {'Yes' if server.enabled else 'No'}")

        if server.env:
            print("\nEnvironment Variables:")
            for key, value in server.env.items():
                print(f"  {key} = {value}")
        else:
            print("\nEnvironment Variables: (none)")

        return 0

    except Exception as e:
        print(f"Error showing server: {e}", file=sys.stderr)
        return 1


def cmd_export(args: argparse.Namespace) -> int:
    """Export MCP configuration.

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
            print("No servers to export", file=sys.stderr)
            return 1

        # Export to string
        export_data = export_servers(servers, format=args.format)

        # Write to file or stdout
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(export_data, encoding="utf-8")
            print(f"Exported {len(servers)} server(s) to: {output_path}")
        else:
            print(export_data)

        return 0

    except Exception as e:
        print(f"Error exporting configuration: {e}", file=sys.stderr)
        return 1


def cmd_import(args: argparse.Namespace) -> int:
    """Import MCP configuration.

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Read import file
        import_path = Path(args.input)
        if not import_path.exists():
            print(f"Import file not found: {import_path}", file=sys.stderr)
            return 1

        import_data = import_path.read_text(encoding="utf-8")

        # Parse servers
        imported_servers = import_servers(import_data, format=args.format)
        if not imported_servers:
            print("No servers found in import file", file=sys.stderr)
            return 1

        print(f"Found {len(imported_servers)} server(s) in import file")

        # Read current config
        config_path = get_config_path()
        config = read_config(config_path)

        # Check for duplicates
        existing_servers = list_servers(config)
        existing_names = {s.name for s in existing_servers}
        import_names = {s.name for s in imported_servers}
        duplicates = existing_names & import_names

        if duplicates and not args.merge:
            print("\nDuplicate server names found:", file=sys.stderr)
            for name in sorted(duplicates):
                print(f"  - {name}", file=sys.stderr)
            print("\nUse --merge to merge with existing configuration", file=sys.stderr)
            return 1

        # Create backup
        backup_path = backup_config(config_path)
        print(f"Created backup: {backup_path.name}")

        try:
            # Build new config
            if args.merge:
                # Merge mode: add new servers, skip duplicates
                new_config = config
                added_count = 0
                skipped_count = 0

                for server in imported_servers:
                    if server.name in existing_names:
                        print(f"  Skipping duplicate: {server.name}")
                        skipped_count += 1
                    else:
                        new_config = add_server(new_config, server)
                        added_count += 1

                print(f"\nAdded {added_count} server(s), skipped {skipped_count} duplicate(s)")
            else:
                # Replace mode: use only imported servers
                new_config = config.copy()
                new_config["enabledMcpjsonServers"] = []

                for server in imported_servers:
                    new_config = add_server(new_config, server)

                print(f"\nReplaced configuration with {len(imported_servers)} server(s)")

            # Validate before writing
            errors = validate_config(new_config)
            if errors:
                print("Validation errors:", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                raise ValueError("Configuration validation failed")

            # Write new config
            write_config(config_path, new_config)
            print("Successfully imported configuration")
            return 0

        except Exception as e:
            restore_config(backup_path, config_path)
            print(f"Error importing configuration (rolled back): {e}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
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

    subparsers = parser.add_subparsers(dest="command", help="Command to execute", required=True)

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

    # Add command
    add_parser = subparsers.add_parser("add", help="Add MCP server")
    add_parser.add_argument("name", nargs="?", help="Server name")
    add_parser.add_argument("server_command", nargs="?", help="Command to execute")
    add_parser.add_argument("server_args", nargs="*", help="Command arguments")
    add_parser.add_argument("--env", action="append", help="Environment variables (KEY=VALUE)")
    add_parser.add_argument("--disabled", action="store_true", help="Add in disabled state")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove MCP server")
    remove_parser.add_argument("name", help="Server name")
    remove_parser.add_argument("--force", action="store_true", help="Skip confirmation")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show server details")
    show_parser.add_argument("name", help="Server name")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export configuration")
    export_parser.add_argument("output", nargs="?", help="Output file (default: stdout)")
    export_parser.add_argument("--format", default="json", choices=["json"], help="Export format")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import configuration")
    import_parser.add_argument("input", help="Input file")
    import_parser.add_argument("--merge", action="store_true", help="Merge with existing")
    import_parser.add_argument("--format", default="json", choices=["json"], help="Import format")

    # Parse arguments
    args = parser.parse_args(argv)

    # Dispatch to command handler
    if args.command == "list":
        return cmd_list(args)
    if args.command == "enable":
        return cmd_enable(args)
    if args.command == "disable":
        return cmd_disable(args)
    if args.command == "validate":
        return cmd_validate(args)
    if args.command == "add":
        return cmd_add(args)
    if args.command == "remove":
        return cmd_remove(args)
    if args.command == "show":
        return cmd_show(args)
    if args.command == "export":
        return cmd_export(args)
    if args.command == "import":
        return cmd_import(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
