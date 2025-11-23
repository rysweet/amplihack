"""Tests for mcp_operations module."""

import copy

import pytest

from ..mcp_operations import (
    MCPServer,
    disable_server,
    enable_server,
    list_servers,
    validate_config,
)


def test_mcpserver_creation():
    """Test creating MCPServer instance."""
    server = MCPServer(
        name="test-server",
        command="node",
        args=["server.js"],
        enabled=True,
        env={"KEY": "value"},
    )

    assert server.name == "test-server"
    assert server.command == "node"
    assert server.args == ["server.js"]
    assert server.enabled is True
    assert server.env == {"KEY": "value"}


def test_mcpserver_defaults():
    """Test MCPServer default values."""
    server = MCPServer(name="test", command="cmd", args=[])

    assert server.enabled is True
    assert server.env == {}


def test_mcpserver_validate_valid():
    """Test validation of valid server."""
    server = MCPServer(
        name="test-server",
        command="node",
        args=["server.js"],
    )

    errors = server.validate()
    assert errors == []


def test_mcpserver_validate_missing_name():
    """Test validation with missing name."""
    server = MCPServer(name="", command="node", args=[])

    errors = server.validate()
    assert any("name is required" in err for err in errors)


def test_mcpserver_validate_invalid_name():
    """Test validation with invalid name format."""
    server = MCPServer(name="Test Server", command="node", args=[])

    errors = server.validate()
    assert any("lowercase with no spaces" in err for err in errors)


def test_mcpserver_validate_missing_command():
    """Test validation with missing command."""
    server = MCPServer(name="test", command="", args=[])

    errors = server.validate()
    assert any("Command is required" in err for err in errors)


def test_mcpserver_validate_invalid_args():
    """Test validation with invalid args type."""
    server = MCPServer(name="test", command="node", args="not-a-list")  # type: ignore

    errors = server.validate()
    assert any("Args must be a list" in err for err in errors)


def test_mcpserver_validate_invalid_env():
    """Test validation with invalid env type."""
    server = MCPServer(
        name="test", command="node", args=[], env={"key": 123}  # type: ignore
    )

    errors = server.validate()
    assert any("Environment variable" in err for err in errors)


def test_mcpserver_to_dict():
    """Test converting server to dictionary."""
    server = MCPServer(
        name="test-server",
        command="node",
        args=["server.js", "--port", "3000"],
        enabled=False,
        env={"API_KEY": "test"},
    )

    result = server.to_dict()

    assert result["name"] == "test-server"
    assert result["command"] == "node"
    assert result["args"] == ["server.js", "--port", "3000"]
    assert result["enabled"] is False
    assert result["env"] == {"API_KEY": "test"}


def test_mcpserver_to_dict_no_env():
    """Test to_dict excludes empty env."""
    server = MCPServer(name="test", command="node", args=[])

    result = server.to_dict()

    assert "env" not in result


def test_mcpserver_from_dict():
    """Test creating server from dictionary."""
    data = {
        "name": "test-server",
        "command": "python",
        "args": ["-m", "module"],
        "enabled": False,
        "env": {"KEY": "value"},
    }

    server = MCPServer.from_dict("test-server", data)

    assert server.name == "test-server"
    assert server.command == "python"
    assert server.args == ["-m", "module"]
    assert server.enabled is False
    assert server.env == {"KEY": "value"}


def test_mcpserver_from_dict_defaults():
    """Test from_dict with missing fields uses defaults."""
    data = {"name": "test"}

    server = MCPServer.from_dict("test", data)

    assert server.command == ""
    assert server.args == []
    assert server.enabled is True
    assert server.env == {}


def test_list_servers():
    """Test listing servers from config."""
    config = {
        "enabledMcpjsonServers": [
            {
                "name": "server-1",
                "command": "node",
                "args": ["s1.js"],
                "enabled": True,
            },
            {
                "name": "server-2",
                "command": "python",
                "args": ["-m", "s2"],
                "enabled": False,
            },
        ]
    }

    servers = list_servers(config)

    assert len(servers) == 2
    assert servers[0].name == "server-1"
    assert servers[0].enabled is True
    assert servers[1].name == "server-2"
    assert servers[1].enabled is False


def test_list_servers_empty():
    """Test listing servers from empty config."""
    config = {"enabledMcpjsonServers": []}

    servers = list_servers(config)

    assert servers == []


def test_list_servers_missing_key():
    """Test listing servers when key is missing."""
    config = {}

    servers = list_servers(config)

    assert servers == []


def test_enable_server():
    """Test enabling a server."""
    config = {
        "enabledMcpjsonServers": [
            {"name": "test-server", "command": "node", "args": [], "enabled": False}
        ]
    }

    new_config = enable_server(config, "test-server")

    # Verify immutability - original unchanged
    assert config["enabledMcpjsonServers"][0]["enabled"] is False

    # Verify new config has enabled server
    assert new_config["enabledMcpjsonServers"][0]["enabled"] is True


def test_enable_server_not_found():
    """Test enabling non-existent server."""
    config = {"enabledMcpjsonServers": []}

    with pytest.raises(ValueError, match="Server not found"):
        enable_server(config, "nonexistent")


def test_enable_server_immutability():
    """Test that enable_server doesn't modify input."""
    original_config = {
        "enabledMcpjsonServers": [
            {"name": "test", "command": "cmd", "args": [], "enabled": False}
        ],
        "other_key": "other_value",
    }
    config_copy = copy.deepcopy(original_config)

    new_config = enable_server(original_config, "test")

    # Original config unchanged
    assert original_config == config_copy

    # New config is different
    assert new_config != original_config


def test_disable_server():
    """Test disabling a server."""
    config = {
        "enabledMcpjsonServers": [
            {"name": "test-server", "command": "node", "args": [], "enabled": True}
        ]
    }

    new_config = disable_server(config, "test-server")

    # Verify immutability - original unchanged
    assert config["enabledMcpjsonServers"][0]["enabled"] is True

    # Verify new config has disabled server
    assert new_config["enabledMcpjsonServers"][0]["enabled"] is False


def test_disable_server_not_found():
    """Test disabling non-existent server."""
    config = {"enabledMcpjsonServers": []}

    with pytest.raises(ValueError, match="Server not found"):
        disable_server(config, "nonexistent")


def test_disable_server_immutability():
    """Test that disable_server doesn't modify input."""
    original_config = {
        "enabledMcpjsonServers": [
            {"name": "test", "command": "cmd", "args": [], "enabled": True}
        ]
    }
    config_copy = copy.deepcopy(original_config)

    new_config = disable_server(original_config, "test")

    # Original config unchanged
    assert original_config == config_copy

    # New config is different
    assert new_config != original_config


def test_validate_config_valid():
    """Test validation of valid config."""
    config = {
        "enabledMcpjsonServers": [
            {"name": "test-server", "command": "node", "args": ["server.js"]}
        ]
    }

    errors = validate_config(config)

    assert errors == []


def test_validate_config_missing_key():
    """Test validation with missing enabledMcpjsonServers key."""
    config = {}

    errors = validate_config(config)

    assert len(errors) == 1
    assert "Missing 'enabledMcpjsonServers'" in errors[0]


def test_validate_config_wrong_type():
    """Test validation when enabledMcpjsonServers is not a list."""
    config = {"enabledMcpjsonServers": "not-a-list"}

    errors = validate_config(config)

    assert len(errors) == 1
    assert "must be a list" in errors[0]


def test_validate_config_invalid_server():
    """Test validation with invalid server data."""
    config = {
        "enabledMcpjsonServers": [
            {"name": "", "command": "node", "args": []}  # Missing name
        ]
    }

    errors = validate_config(config)

    assert len(errors) > 0
    assert any("name is required" in err for err in errors)


def test_validate_config_duplicate_names():
    """Test validation detects duplicate server names."""
    config = {
        "enabledMcpjsonServers": [
            {"name": "test", "command": "node", "args": []},
            {"name": "test", "command": "python", "args": []},  # Duplicate
        ]
    }

    errors = validate_config(config)

    assert any("Duplicate server name" in err for err in errors)


def test_validate_config_not_dict():
    """Test validation when server entry is not a dict."""
    config = {
        "enabledMcpjsonServers": [
            "not-a-dict",  # Invalid entry
        ]
    }

    errors = validate_config(config)

    assert any("not a dictionary" in err for err in errors)
