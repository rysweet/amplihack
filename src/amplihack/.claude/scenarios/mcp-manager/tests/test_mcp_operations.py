"""Tests for mcp_operations module."""

import copy

import pytest
from mcp_operations import (
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
        name="test",
        command="node",
        args=[],
        env={"key": 123},  # type: ignore
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
        "enabledMcpjsonServers": [{"name": "test", "command": "cmd", "args": [], "enabled": False}],
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
        "enabledMcpjsonServers": [{"name": "test", "command": "cmd", "args": [], "enabled": True}]
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
        "enabledMcpjsonServers": [{"name": "test-server", "command": "node", "args": ["server.js"]}]
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


# Tests for add_server
def test_add_server():
    """Test adding a new server."""
    config = {"enabledMcpjsonServers": []}
    server = MCPServer(name="new-server", command="node", args=["server.js"])

    new_config = add_server(config, server)

    # Verify immutability
    assert config["enabledMcpjsonServers"] == []

    # Verify new server was added
    assert len(new_config["enabledMcpjsonServers"]) == 1
    assert new_config["enabledMcpjsonServers"][0]["name"] == "new-server"


def test_add_server_to_existing():
    """Test adding a server to existing configuration."""
    config = {
        "enabledMcpjsonServers": [
            {"name": "existing", "command": "cmd", "args": [], "enabled": True}
        ]
    }
    server = MCPServer(name="new-server", command="node", args=["server.js"])

    new_config = add_server(config, server)

    assert len(new_config["enabledMcpjsonServers"]) == 2
    assert new_config["enabledMcpjsonServers"][1]["name"] == "new-server"


def test_add_server_duplicate_name():
    """Test adding a server with duplicate name."""
    config = {
        "enabledMcpjsonServers": [{"name": "test", "command": "cmd", "args": [], "enabled": True}]
    }
    server = MCPServer(name="test", command="node", args=[])

    with pytest.raises(ValueError, match="already exists"):
        add_server(config, server)


def test_add_server_invalid():
    """Test adding invalid server."""
    config = {"enabledMcpjsonServers": []}
    server = MCPServer(name="", command="node", args=[])  # Invalid: empty name

    with pytest.raises(ValueError, match="validation failed"):
        add_server(config, server)


def test_add_server_with_env():
    """Test adding server with environment variables."""
    config = {"enabledMcpjsonServers": []}
    server = MCPServer(name="test", command="node", args=[], env={"KEY": "value"})

    new_config = add_server(config, server)

    assert new_config["enabledMcpjsonServers"][0]["env"] == {"KEY": "value"}


def test_add_server_disabled():
    """Test adding server in disabled state."""
    config = {"enabledMcpjsonServers": []}
    server = MCPServer(name="test", command="node", args=[], enabled=False)

    new_config = add_server(config, server)

    assert new_config["enabledMcpjsonServers"][0]["enabled"] is False


# Tests for remove_server
def test_remove_server():
    """Test removing a server."""
    config = {
        "enabledMcpjsonServers": [
            {"name": "test-server", "command": "node", "args": [], "enabled": True},
            {"name": "other-server", "command": "python", "args": [], "enabled": True},
        ]
    }

    new_config = remove_server(config, "test-server")

    # Verify immutability
    assert len(config["enabledMcpjsonServers"]) == 2

    # Verify server was removed
    assert len(new_config["enabledMcpjsonServers"]) == 1
    assert new_config["enabledMcpjsonServers"][0]["name"] == "other-server"


def test_remove_server_not_found():
    """Test removing non-existent server."""
    config = {"enabledMcpjsonServers": []}

    with pytest.raises(ValueError, match="not found"):
        remove_server(config, "nonexistent")


def test_remove_server_immutability():
    """Test that remove_server doesn't modify input."""
    original_config = {
        "enabledMcpjsonServers": [{"name": "test", "command": "cmd", "args": [], "enabled": True}]
    }
    config_copy = copy.deepcopy(original_config)

    new_config = remove_server(original_config, "test")

    # Original config unchanged
    assert original_config == config_copy

    # New config is different
    assert new_config != original_config
    assert len(new_config["enabledMcpjsonServers"]) == 0


# Tests for get_server
def test_get_server_found():
    """Test getting existing server."""
    config = {
        "enabledMcpjsonServers": [
            {"name": "test-server", "command": "node", "args": ["s.js"], "enabled": True}
        ]
    }

    server = get_server(config, "test-server")

    assert server is not None
    assert server.name == "test-server"
    assert server.command == "node"
    assert server.args == ["s.js"]


def test_get_server_not_found():
    """Test getting non-existent server."""
    config = {"enabledMcpjsonServers": []}

    server = get_server(config, "nonexistent")

    assert server is None


def test_get_server_multiple():
    """Test getting server from multiple servers."""
    config = {
        "enabledMcpjsonServers": [
            {"name": "server1", "command": "cmd1", "args": [], "enabled": True},
            {"name": "server2", "command": "cmd2", "args": [], "enabled": True},
            {"name": "server3", "command": "cmd3", "args": [], "enabled": True},
        ]
    }

    server = get_server(config, "server2")

    assert server is not None
    assert server.name == "server2"
    assert server.command == "cmd2"


# Tests for export_servers
def test_export_servers():
    """Test exporting servers to JSON."""
    servers = [
        MCPServer(name="server1", command="node", args=["s1.js"]),
        MCPServer(name="server2", command="python", args=["-m", "s2"]),
    ]

    export_data = export_servers(servers)

    # Verify it's valid JSON
    import json

    data = json.loads(export_data)

    assert "metadata" in data
    assert data["metadata"]["server_count"] == 2
    assert "servers" in data
    assert len(data["servers"]) == 2
    assert data["servers"][0]["name"] == "server1"
    assert data["servers"][1]["name"] == "server2"


def test_export_servers_empty():
    """Test exporting empty server list."""
    servers = []

    export_data = export_servers(servers)

    import json

    data = json.loads(export_data)

    assert data["metadata"]["server_count"] == 0
    assert data["servers"] == []


def test_export_servers_with_env():
    """Test exporting server with environment variables."""
    servers = [MCPServer(name="test", command="node", args=[], env={"KEY": "value"})]

    export_data = export_servers(servers)

    import json

    data = json.loads(export_data)

    assert data["servers"][0]["env"] == {"KEY": "value"}


def test_export_servers_unsupported_format():
    """Test export with unsupported format."""
    servers = [MCPServer(name="test", command="node", args=[])]

    with pytest.raises(ValueError, match="Unsupported export format"):
        export_servers(servers, format="yaml")


# Tests for import_servers
def test_import_servers():
    """Test importing servers from JSON."""
    import_data = """
    {
        "metadata": {
            "export_date": "2024-01-01T00:00:00",
            "tool_version": "1.0.0",
            "server_count": 2
        },
        "servers": [
            {
                "name": "server1",
                "command": "node",
                "args": ["s1.js"],
                "enabled": true
            },
            {
                "name": "server2",
                "command": "python",
                "args": ["-m", "s2"],
                "enabled": false
            }
        ]
    }
    """

    servers = import_servers(import_data)

    assert len(servers) == 2
    assert servers[0].name == "server1"
    assert servers[0].command == "node"
    assert servers[0].enabled is True
    assert servers[1].name == "server2"
    assert servers[1].enabled is False


def test_import_servers_invalid_json():
    """Test importing invalid JSON."""
    import_data = "not valid json"

    with pytest.raises(ValueError, match="Invalid JSON"):
        import_servers(import_data)


def test_import_servers_missing_servers_key():
    """Test importing data without servers key."""
    import_data = '{"metadata": {}}'

    with pytest.raises(ValueError, match="missing 'servers' key"):
        import_servers(import_data)


def test_import_servers_invalid_structure():
    """Test importing data with invalid structure."""
    import_data = '{"servers": "not-a-list"}'

    with pytest.raises(ValueError, match="must be a list"):
        import_servers(import_data)


def test_import_servers_invalid_server():
    """Test importing data with invalid server."""
    import_data = """
    {
        "servers": [
            {
                "name": "invalid name with spaces",
                "command": "",
                "args": []
            }
        ]
    }
    """

    with pytest.raises(ValueError, match="validation failed"):
        import_servers(import_data)


def test_import_servers_no_name():
    """Test importing server without name."""
    import_data = """
    {
        "servers": [
            {
                "command": "node",
                "args": []
            }
        ]
    }
    """

    with pytest.raises(ValueError, match="has no name"):
        import_servers(import_data)


def test_import_servers_unsupported_format():
    """Test import with unsupported format."""
    with pytest.raises(ValueError, match="Unsupported import format"):
        import_servers('{"servers": []}', format="yaml")


def test_import_export_roundtrip():
    """Test that export then import preserves data."""
    original_servers = [
        MCPServer(
            name="server1",
            command="node",
            args=["s1.js", "--port", "3000"],
            enabled=True,
            env={"API_KEY": "test123"},
        ),
        MCPServer(
            name="server2",
            command="python",
            args=["-m", "module"],
            enabled=False,
        ),
    ]

    # Export
    export_data = export_servers(original_servers)

    # Import
    imported_servers = import_servers(export_data)

    # Verify all data preserved
    assert len(imported_servers) == len(original_servers)

    for orig, imported in zip(original_servers, imported_servers, strict=False):
        assert imported.name == orig.name
        assert imported.command == orig.command
        assert imported.args == orig.args
        assert imported.enabled == orig.enabled
        assert imported.env == orig.env
