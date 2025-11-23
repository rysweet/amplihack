"""Business logic for MCP server management.

This module provides immutable operations on MCP server configurations.
All operations return new configuration dictionaries rather than modifying
the input.
"""

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPServer:
    """Model for an MCP server configuration.

    Attributes:
        name: Unique identifier (kebab-case recommended)
        command: Executable command
        args: Command arguments
        enabled: Whether the server is enabled
        env: Optional environment variables
    """

    name: str
    command: str
    args: list[str]
    enabled: bool = True
    env: dict[str, str] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate server configuration.

        Returns:
            List of validation error messages, empty if valid
        """
        errors = []

        # Required field validation
        if not self.name:
            errors.append("Server name is required")
        elif not isinstance(self.name, str):
            errors.append("Server name must be a string")

        if not self.command:
            errors.append("Command is required")
        elif not isinstance(self.command, str):
            errors.append("Command must be a string")

        if not isinstance(self.args, list):
            errors.append("Args must be a list")
        elif not all(isinstance(arg, str) for arg in self.args):
            errors.append("All args must be strings")

        # Name constraints
        if self.name and (' ' in self.name or self.name != self.name.lower()):
            errors.append("Server name must be lowercase with no spaces")

        # Environment variables validation
        if not isinstance(self.env, dict):
            errors.append("Environment variables must be a dictionary")
        elif self.env and not all(
            isinstance(k, str) and isinstance(v, str)
            for k, v in self.env.items()
        ):
            errors.append("Environment variable keys and values must be strings")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert server to JSON-serializable dictionary.

        Returns:
            Dictionary representation suitable for settings.json
        """
        result = {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "enabled": self.enabled,
        }

        # Only include env if it's not empty
        if self.env:
            result["env"] = self.env

        return result

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "MCPServer":
        """Create MCPServer from settings.json entry.

        Args:
            name: Server name
            data: Dictionary from settings.json

        Returns:
            MCPServer instance
        """
        return cls(
            name=name,
            command=data.get("command", ""),
            args=data.get("args", []),
            enabled=data.get("enabled", True),
            env=data.get("env", {}),
        )


def list_servers(config: dict[str, Any]) -> list[MCPServer]:
    """List all MCP servers from configuration.

    Args:
        config: Configuration dictionary from settings.json

    Returns:
        List of MCPServer instances
    """
    servers = []
    mcp_servers = config.get("enabledMcpjsonServers", [])

    for server_data in mcp_servers:
        if isinstance(server_data, dict):
            name = server_data.get("name", "")
            servers.append(MCPServer.from_dict(name, server_data))

    return servers


def enable_server(config: dict[str, Any], name: str) -> dict[str, Any]:
    """Enable an MCP server (immutable operation).

    Args:
        config: Configuration dictionary from settings.json
        name: Server name to enable

    Returns:
        New configuration dictionary with server enabled

    Raises:
        ValueError: If server not found
    """
    # Make a deep copy of config
    new_config = copy.deepcopy(config)

    # Find and enable the server
    servers = new_config.get("enabledMcpjsonServers", [])
    found = False

    for server_data in servers:
        if isinstance(server_data, dict) and server_data.get("name") == name:
            server_data["enabled"] = True
            found = True
            break

    if not found:
        raise ValueError(f"Server not found: {name}")

    return new_config


def disable_server(config: dict[str, Any], name: str) -> dict[str, Any]:
    """Disable an MCP server (immutable operation).

    Args:
        config: Configuration dictionary from settings.json
        name: Server name to disable

    Returns:
        New configuration dictionary with server disabled

    Raises:
        ValueError: If server not found
    """
    # Make a deep copy of config
    new_config = copy.deepcopy(config)

    # Find and disable the server
    servers = new_config.get("enabledMcpjsonServers", [])
    found = False

    for server_data in servers:
        if isinstance(server_data, dict) and server_data.get("name") == name:
            server_data["enabled"] = False
            found = True
            break

    if not found:
        raise ValueError(f"Server not found: {name}")

    return new_config


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate entire MCP configuration.

    Args:
        config: Configuration dictionary from settings.json

    Returns:
        List of validation error messages, empty if valid
    """
    errors = []

    # Check if enabledMcpjsonServers exists and is a list
    if "enabledMcpjsonServers" not in config:
        errors.append("Missing 'enabledMcpjsonServers' key in configuration")
        return errors

    servers = config.get("enabledMcpjsonServers")
    if not isinstance(servers, list):
        errors.append("'enabledMcpjsonServers' must be a list")
        return errors

    # Validate each server
    seen_names = set()
    for idx, server_data in enumerate(servers):
        if not isinstance(server_data, dict):
            errors.append(f"Server at index {idx} is not a dictionary")
            continue

        name = server_data.get("name", "")
        server = MCPServer.from_dict(name, server_data)
        server_errors = server.validate()

        if server_errors:
            errors.extend(
                [f"Server '{name}' (index {idx}): {err}" for err in server_errors]
            )

        # Check for duplicate names
        if name in seen_names:
            errors.append(f"Duplicate server name: {name}")
        seen_names.add(name)

    return errors
