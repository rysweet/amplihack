"""Argument parser setup for plugin commands.

Philosophy:
- Clear command structure: amplihack plugin <subcommand>
- Standard argparse patterns
- Delegates execution to cli_handlers

Public API (the "studs"):
    setup_plugin_commands: Register plugin subcommands
"""

import argparse

from .cli_handlers import (
    plugin_install_command,
    plugin_uninstall_command,
    plugin_verify_command,
)


def setup_plugin_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register plugin management commands.

    Args:
        subparsers: Main argument parser's subparsers object

    Example:
        >>> parser = argparse.ArgumentParser()
        >>> subparsers = parser.add_subparsers()
        >>> setup_plugin_commands(subparsers)
        >>> args = parser.parse_args(['plugin', 'install', 'source'])
    """
    # Create plugin parent command
    plugin_parser = subparsers.add_parser(
        'plugin',
        help='Manage Claude Code plugins',
        description='Install, uninstall, and verify Claude Code plugins'
    )

    # Create subcommands under 'plugin'
    plugin_subparsers = plugin_parser.add_subparsers(
        dest='plugin_command',
        help='Plugin subcommands'
    )

    # Install command
    install_parser = plugin_subparsers.add_parser(
        'install',
        help='Install a plugin from source',
        description='Install a Claude Code plugin from Git URL or local path'
    )
    install_parser.add_argument(
        'source',
        help='Plugin source (Git URL or local path)'
    )
    install_parser.add_argument(
        '--force',
        action='store_true',
        help='Force installation, overwriting existing plugin'
    )
    install_parser.set_defaults(func=plugin_install_command)

    # Uninstall command
    uninstall_parser = plugin_subparsers.add_parser(
        'uninstall',
        help='Uninstall a plugin',
        description='Remove an installed Claude Code plugin'
    )
    uninstall_parser.add_argument(
        'plugin_name',
        help='Name of the plugin to uninstall'
    )
    uninstall_parser.set_defaults(func=plugin_uninstall_command)

    # Verify command
    verify_parser = plugin_subparsers.add_parser(
        'verify',
        help='Verify plugin installation',
        description='Check if a plugin is correctly installed and discoverable'
    )
    verify_parser.add_argument(
        'plugin_name',
        help='Name of the plugin to verify'
    )
    verify_parser.set_defaults(func=plugin_verify_command)


__all__ = ["setup_plugin_commands"]
