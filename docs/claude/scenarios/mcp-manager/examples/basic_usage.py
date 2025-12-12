#!/usr/bin/env python3
"""Basic usage examples for MCP Manager.

This script demonstrates programmatic usage of the MCP Manager library.
"""

from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_manager import (
    read_config,
    write_config,
    backup_config,
    list_servers,
    enable_server,
    disable_server,
    validate_config,
)


def example_list_servers():
    """Example: List all MCP servers."""
    print("=" * 60)
    print("Example 1: List all MCP servers")
    print("=" * 60)

    config_path = Path(".claude/settings.json")

    try:
        config = read_config(config_path)
        servers = list_servers(config)

        print(f"\nFound {len(servers)} MCP servers:\n")

        for server in servers:
            status = "✓ Enabled" if server.enabled else "✗ Disabled"
            print(f"  {server.name}: {status}")
            print(f"    Command: {server.command}")
            print(f"    Args: {' '.join(server.args)}")
            if server.env:
                print(f"    Env: {', '.join(server.env.keys())}")
            print()

    except FileNotFoundError:
        print("  No configuration file found")
    except Exception as e:
        print(f"  Error: {e}")


def example_enable_server():
    """Example: Enable a server with backup."""
    print("=" * 60)
    print("Example 2: Enable a server (with automatic backup)")
    print("=" * 60)

    config_path = Path(".claude/settings.json")
    server_name = "test-server"

    try:
        # Read current config
        config = read_config(config_path)

        # Create backup before modifying
        backup_path = backup_config(config_path)
        print(f"\n✓ Created backup: {backup_path.name}")

        # Enable the server
        new_config = enable_server(config, server_name)

        # Validate before writing
        errors = validate_config(new_config)
        if errors:
            print(f"\n✗ Validation failed:")
            for error in errors:
                print(f"  - {error}")
            return

        # Write new config
        write_config(config_path, new_config)
        print(f"✓ Successfully enabled server: {server_name}")

    except ValueError as e:
        print(f"\n✗ Error: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")


def example_validate_config():
    """Example: Validate configuration."""
    print("=" * 60)
    print("Example 3: Validate configuration")
    print("=" * 60)

    config_path = Path(".claude/settings.json")

    try:
        config = read_config(config_path)
        errors = validate_config(config)

        if not errors:
            print("\n✓ Configuration is valid!")
        else:
            print(f"\n✗ Found {len(errors)} validation errors:\n")
            for error in errors:
                print(f"  - {error}")

    except Exception as e:
        print(f"\n✗ Error reading config: {e}")


def example_safe_modification():
    """Example: Safe modification with rollback on error."""
    print("=" * 60)
    print("Example 4: Safe modification with error handling")
    print("=" * 60)

    config_path = Path(".claude/settings.json")
    server_name = "example-server"

    try:
        # Read config
        config = read_config(config_path)

        # Create backup
        backup_path = backup_config(config_path)
        print(f"\n✓ Created backup: {backup_path.name}")

        try:
            # Attempt modification
            new_config = disable_server(config, server_name)

            # Validate
            errors = validate_config(new_config)
            if errors:
                raise ValueError(f"Validation failed: {errors}")

            # Write
            write_config(config_path, new_config)
            print(f"✓ Successfully disabled: {server_name}")

        except Exception as e:
            # Rollback on any error
            from mcp_manager import restore_config
            restore_config(backup_path, config_path)
            print(f"✗ Error occurred, rolled back to backup: {e}")

    except Exception as e:
        print(f"\n✗ Fatal error: {e}")


def main():
    """Run all examples."""
    examples = [
        example_list_servers,
        example_validate_config,
        # Uncomment to run modification examples:
        # example_enable_server,
        # example_safe_modification,
    ]

    for example_func in examples:
        example_func()
        print("\n")


if __name__ == "__main__":
    main()

