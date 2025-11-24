"""Tests for CLI module."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ..cli import (
    cmd_disable,
    cmd_enable,
    cmd_list,
    cmd_validate,
    format_table,
    get_config_path,
    main,
)


def test_format_table():
    """Test ASCII table formatting."""
    headers = ["Name", "Status"]
    rows = [
        ["server-1", "Enabled"],
        ["server-2", "Disabled"],
    ]

    result = format_table(headers, rows)

    assert "Name" in result
    assert "Status" in result
    assert "server-1" in result
    assert "server-2" in result
    assert "+" in result  # Table borders
    assert "|" in result  # Table separators


def test_format_table_empty():
    """Test formatting empty table."""
    result = format_table(["Name"], [])

    assert result == "No data to display"


def test_get_config_path():
    """Test getting config path."""
    path = get_config_path()

    assert isinstance(path, Path)
    assert path.name == "settings.json"
    assert ".claude" in str(path)


@pytest.fixture
def mock_config_path(tmp_path, monkeypatch):
    """Mock get_config_path to return temp path."""
    config_dir = tmp_path / ".claude"
    config_dir.mkdir()
    config_path = config_dir / "settings.json"

    config = {
        "enabledMcpjsonServers": [
            {
                "name": "test-server",
                "command": "node",
                "args": ["server.js"],
                "enabled": True,
            }
        ]
    }
    config_path.write_text(json.dumps(config, indent=2))

    def mock_get_config():
        return config_path

    monkeypatch.setattr("mcp_manager.cli.get_config_path", mock_get_config)
    return config_path


def test_cmd_list(mock_config_path, capsys):
    """Test list command."""
    args = Mock()
    result = cmd_list(args)

    assert result == 0

    captured = capsys.readouterr()
    assert "test-server" in captured.out
    assert "node" in captured.out


def test_cmd_list_empty(tmp_path, monkeypatch, capsys):
    """Test list command with no servers."""
    config_path = tmp_path / "settings.json"
    config_path.write_text(json.dumps({"enabledMcpjsonServers": []}, indent=2))

    def mock_get_config():
        return config_path

    monkeypatch.setattr("mcp_manager.cli.get_config_path", mock_get_config)

    args = Mock()
    result = cmd_list(args)

    assert result == 0

    captured = capsys.readouterr()
    assert "No MCP servers configured" in captured.out


def test_cmd_enable(mock_config_path, capsys):
    """Test enable command."""
    # First disable the server
    config = json.loads(mock_config_path.read_text())
    config["enabledMcpjsonServers"][0]["enabled"] = False
    mock_config_path.write_text(json.dumps(config, indent=2))

    args = Mock()
    args.name = "test-server"

    result = cmd_enable(args)

    assert result == 0

    # Verify server is enabled
    updated_config = json.loads(mock_config_path.read_text())
    assert updated_config["enabledMcpjsonServers"][0]["enabled"] is True

    captured = capsys.readouterr()
    assert "Successfully enabled" in captured.out


def test_cmd_enable_not_found(mock_config_path, capsys):
    """Test enable command with non-existent server."""
    args = Mock()
    args.name = "nonexistent"

    result = cmd_enable(args)

    assert result == 1

    captured = capsys.readouterr()
    assert "Server not found" in captured.err


def test_cmd_enable_creates_backup(mock_config_path):
    """Test that enable command creates backup."""
    backup_dir = mock_config_path.parent
    initial_backups = list(backup_dir.glob("settings_backup_*.json"))

    args = Mock()
    args.name = "test-server"

    cmd_enable(args)

    final_backups = list(backup_dir.glob("settings_backup_*.json"))
    assert len(final_backups) == len(initial_backups) + 1


def test_cmd_disable(mock_config_path, capsys):
    """Test disable command."""
    args = Mock()
    args.name = "test-server"

    result = cmd_disable(args)

    assert result == 0

    # Verify server is disabled
    updated_config = json.loads(mock_config_path.read_text())
    assert updated_config["enabledMcpjsonServers"][0]["enabled"] is False

    captured = capsys.readouterr()
    assert "Successfully disabled" in captured.out


def test_cmd_disable_not_found(mock_config_path, capsys):
    """Test disable command with non-existent server."""
    args = Mock()
    args.name = "nonexistent"

    result = cmd_disable(args)

    assert result == 1

    captured = capsys.readouterr()
    assert "Server not found" in captured.err


def test_cmd_validate(mock_config_path, capsys):
    """Test validate command with valid config."""
    args = Mock()

    result = cmd_validate(args)

    assert result == 0

    captured = capsys.readouterr()
    assert "Configuration is valid" in captured.out


def test_cmd_validate_invalid(tmp_path, monkeypatch, capsys):
    """Test validate command with invalid config."""
    config_path = tmp_path / "settings.json"
    config = {
        "enabledMcpjsonServers": [
            {"name": "", "command": "node", "args": []}  # Invalid: empty name
        ]
    }
    config_path.write_text(json.dumps(config, indent=2))

    def mock_get_config():
        return config_path

    monkeypatch.setattr("mcp_manager.cli.get_config_path", mock_get_config)

    args = Mock()
    result = cmd_validate(args)

    assert result == 1

    captured = capsys.readouterr()
    assert "validation errors" in captured.err


def test_main_list(capsys):
    """Test main function with list command."""
    with patch("mcp_manager.cli.cmd_list", return_value=0) as mock_list:
        result = main(["list"])

        assert result == 0
        mock_list.assert_called_once()


def test_main_enable(capsys):
    """Test main function with enable command."""
    with patch("mcp_manager.cli.cmd_enable", return_value=0) as mock_enable:
        result = main(["enable", "test-server"])

        assert result == 0
        mock_enable.assert_called_once()


def test_main_disable(capsys):
    """Test main function with disable command."""
    with patch("mcp_manager.cli.cmd_disable", return_value=0) as mock_disable:
        result = main(["disable", "test-server"])

        assert result == 0
        mock_disable.assert_called_once()


def test_main_validate(capsys):
    """Test main function with validate command."""
    with patch("mcp_manager.cli.cmd_validate", return_value=0) as mock_validate:
        result = main(["validate"])

        assert result == 0
        mock_validate.assert_called_once()


def test_main_no_command(capsys):
    """Test main function without command."""
    result = main([])

    assert result == 1

    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "usage:" in captured.err.lower()


def test_main_invalid_command(capsys):
    """Test main function with invalid command."""
    result = main(["invalid"])

    assert result == 1

