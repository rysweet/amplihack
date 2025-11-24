"""MCP Manager - Tool for managing MCP server configurations.

This package provides safe, atomic operations for managing MCP servers
in Claude Code's settings.json file.

Public API:
    - Config Management: read_config, write_config, backup_config
    - MCP Operations: MCPServer, list_servers, enable_server, disable_server
    - CLI: main (entry point for command-line usage)

Example:
    >>> from mcp_manager import read_config, list_servers
    >>> config = read_config(Path(".claude/settings.json"))
    >>> servers = list_servers(config)
    >>> for server in servers:
    ...     print(f"{server.name}: {server.enabled}")
"""

from .config_manager import backup_config, read_config, restore_config, write_config
from .mcp_operations import (
    MCPServer,
    disable_server,
    enable_server,
    list_servers,
    validate_config,
)
from .cli import main

__all__ = [
    # Config management
    "read_config",
    "write_config",
    "backup_config",
    "restore_config",
    # MCP operations
    "MCPServer",
    "list_servers",
    "enable_server",
    "disable_server",
    "validate_config",
    # CLI entry point
    "main",
]

__version__ = "1.0.0"

