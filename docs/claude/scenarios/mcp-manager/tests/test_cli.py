"""Tests for CLI module."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cli import (
    cmd_add,
    cmd_disable,
    cmd_enable,
    cmd_export,
    cmd_import,
    cmd_list,
    cmd_remove,
    cmd_show,
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

    monkeypatch.setattr("cli.get_config_path", mock_get_config)
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

    monkeypatch.setattr("cli.get_config_path", mock_get_config)

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

    monkeypatch.setattr("cli.get_config_path", mock_get_config)

    args = Mock()
    result = cmd_validate(args)

    assert result == 1

    captured = capsys.readouterr()
    assert "validation errors" in captured.err


def test_main_list(capsys):
    """Test main function with list command."""
    with patch("cli.cmd_list", return_value=0) as mock_list:
        result = main(["list"])

        assert result == 0
        mock_list.assert_called_once()


def test_main_enable(capsys):
    """Test main function with enable command."""
    with patch("cli.cmd_enable", return_value=0) as mock_enable:
        result = main(["enable", "test-server"])

        assert result == 0
        mock_enable.assert_called_once()


def test_main_disable(capsys):
    """Test main function with disable command."""
    with patch("cli.cmd_disable", return_value=0) as mock_disable:
        result = main(["disable", "test-server"])

        assert result == 0
        mock_disable.assert_called_once()


def test_main_validate(capsys):
    """Test main function with validate command."""
    with patch("cli.cmd_validate", return_value=0) as mock_validate:
        result = main(["validate"])

        assert result == 0
        mock_validate.assert_called_once()


def test_main_no_command(capsys):
    """Test main function without command."""
    # After making command required, argparse exits with SystemExit(2)
    with pytest.raises(SystemExit) as exc_info:
        main([])

    assert exc_info.value.code == 2


def test_main_invalid_command(capsys):
    """Test main function with invalid command."""
    # argparse exits with SystemExit(2) for invalid commands
    with pytest.raises(SystemExit) as exc_info:
        main(["invalid"])

    assert exc_info.value.code == 2


# Tests for new commands (add, remove, show, export, import)

def test_cmd_add(mock_config_path, capsys):
    """Test add command."""
    args = Mock()
    args.name = "new-server"
    args.server_command = "python"
    args.server_args = ["-m", "module"]
    args.env = ["API_KEY=test123"]
    args.disabled = False

    result = cmd_add(args)

    assert result == 0

    # Verify server was added
    updated_config = json.loads(mock_config_path.read_text())
    assert len(updated_config["enabledMcpjsonServers"]) == 2
    assert updated_config["enabledMcpjsonServers"][1]["name"] == "new-server"
    assert updated_config["enabledMcpjsonServers"][1]["command"] == "python"
    assert updated_config["enabledMcpjsonServers"][1]["env"] == {"API_KEY": "test123"}

    captured = capsys.readouterr()
    assert "Successfully added" in captured.out


def test_cmd_add_disabled(mock_config_path, capsys):
    """Test add command with disabled flag."""
    args = Mock()
    args.name = "new-server"
    args.server_command = "python"
    args.server_args = []
    args.env = None
    args.disabled = True

    result = cmd_add(args)

    assert result == 0

    # Verify server was added as disabled
    updated_config = json.loads(mock_config_path.read_text())
    assert updated_config["enabledMcpjsonServers"][1]["enabled"] is False

    captured = capsys.readouterr()
    assert "disabled" in captured.out


def test_cmd_add_duplicate(mock_config_path, capsys):
    """Test add command with duplicate name."""
    args = Mock()
    args.name = "test-server"  # Already exists
    args.server_command = "python"
    args.server_args = []
    args.env = None
    args.disabled = False

    result = cmd_add(args)

    assert result == 1

    captured = capsys.readouterr()
    assert "already exists" in captured.err


def test_cmd_add_invalid_env(mock_config_path, capsys):
    """Test add command with invalid environment variable format."""
    args = Mock()
    args.name = "new-server"
    args.server_command = "python"
    args.server_args = []
    args.env = ["INVALID"]  # Missing = sign
    args.disabled = False

    result = cmd_add(args)

    assert result == 1

    captured = capsys.readouterr()
    assert "Invalid environment variable format" in captured.err


def test_cmd_add_creates_backup(mock_config_path):
    """Test that add command creates backup."""
    backup_dir = mock_config_path.parent
    initial_backups = list(backup_dir.glob("settings_backup_*.json"))

    args = Mock()
    args.name = "new-server"
    args.server_command = "python"
    args.server_args = []
    args.env = None
    args.disabled = False

    cmd_add(args)

    final_backups = list(backup_dir.glob("settings_backup_*.json"))
    assert len(final_backups) == len(initial_backups) + 1


def test_cmd_remove(mock_config_path, capsys, monkeypatch):
    """Test remove command with force flag."""
    args = Mock()
    args.name = "test-server"
    args.force = True

    result = cmd_remove(args)

    assert result == 0

    # Verify server was removed
    updated_config = json.loads(mock_config_path.read_text())
    assert len(updated_config["enabledMcpjsonServers"]) == 0

    captured = capsys.readouterr()
    assert "Successfully removed" in captured.out


def test_cmd_remove_with_confirmation(mock_config_path, capsys, monkeypatch):
    """Test remove command with user confirmation."""
    # Mock user input to confirm
    monkeypatch.setattr("builtins.input", lambda _: "y")

    args = Mock()
    args.name = "test-server"
    args.force = False

    result = cmd_remove(args)

    assert result == 0

    captured = capsys.readouterr()
    assert "Successfully removed" in captured.out


def test_cmd_remove_cancelled(mock_config_path, capsys, monkeypatch):
    """Test remove command cancelled by user."""
    # Mock user input to cancel
    monkeypatch.setattr("builtins.input", lambda _: "n")

    args = Mock()
    args.name = "test-server"
    args.force = False

    result = cmd_remove(args)

    assert result == 0

    # Verify server was NOT removed
    updated_config = json.loads(mock_config_path.read_text())
    assert len(updated_config["enabledMcpjsonServers"]) == 1

    captured = capsys.readouterr()
    assert "Cancelled" in captured.out


def test_cmd_remove_not_found(mock_config_path, capsys):
    """Test remove command with non-existent server."""
    args = Mock()
    args.name = "nonexistent"
    args.force = True

    result = cmd_remove(args)

    assert result == 1

    captured = capsys.readouterr()
    assert "Server not found" in captured.err


def test_cmd_remove_creates_backup(mock_config_path):
    """Test that remove command creates backup."""
    backup_dir = mock_config_path.parent
    initial_backups = list(backup_dir.glob("settings_backup_*.json"))

    args = Mock()
    args.name = "test-server"
    args.force = True

    cmd_remove(args)

    final_backups = list(backup_dir.glob("settings_backup_*.json"))
    assert len(final_backups) == len(initial_backups) + 1


def test_cmd_show(mock_config_path, capsys):
    """Test show command."""
    args = Mock()
    args.name = "test-server"

    result = cmd_show(args)

    assert result == 0

    captured = capsys.readouterr()
    assert "test-server" in captured.out
    assert "node" in captured.out
    assert "server.js" in captured.out
    assert "Enabled:" in captured.out


def test_cmd_show_not_found(mock_config_path, capsys):
    """Test show command with non-existent server."""
    args = Mock()
    args.name = "nonexistent"

    result = cmd_show(args)

    assert result == 1

    captured = capsys.readouterr()
    assert "Server not found" in captured.err


def test_cmd_export_to_stdout(mock_config_path, capsys):
    """Test export command to stdout."""
    args = Mock()
    args.output = None
    args.format = "json"

    result = cmd_export(args)

    assert result == 0

    captured = capsys.readouterr()
    assert "test-server" in captured.out
    assert '"servers"' in captured.out
    assert '"metadata"' in captured.out


def test_cmd_export_to_file(mock_config_path, tmp_path, capsys):
    """Test export command to file."""
    output_file = tmp_path / "export.json"

    args = Mock()
    args.output = str(output_file)
    args.format = "json"

    result = cmd_export(args)

    assert result == 0
    assert output_file.exists()

    # Verify file contents
    export_data = json.loads(output_file.read_text())
    assert "servers" in export_data
    assert len(export_data["servers"]) == 1
    assert export_data["servers"][0]["name"] == "test-server"

    captured = capsys.readouterr()
    assert "Exported 1 server(s)" in captured.out


def test_cmd_export_empty(tmp_path, monkeypatch, capsys):
    """Test export command with no servers."""
    config_path = tmp_path / "settings.json"
    config_path.write_text(json.dumps({"enabledMcpjsonServers": []}, indent=2))

    def mock_get_config():
        return config_path

    monkeypatch.setattr("cli.get_config_path", mock_get_config)

    args = Mock()
    args.output = None
    args.format = "json"

    result = cmd_export(args)

    assert result == 1

    captured = capsys.readouterr()
    assert "No servers to export" in captured.err


def test_cmd_import_replace(mock_config_path, tmp_path, capsys):
    """Test import command (replace mode)."""
    # Create export file
    export_file = tmp_path / "import.json"
    export_data = {
        "metadata": {"server_count": 1},
        "servers": [
            {
                "name": "imported-server",
                "command": "python",
                "args": ["-m", "module"],
                "enabled": True,
            }
        ],
    }
    export_file.write_text(json.dumps(export_data, indent=2))

    args = Mock()
    args.input = str(export_file)
    args.merge = False
    args.format = "json"

    result = cmd_import(args)

    assert result == 0

    # Verify servers were replaced
    updated_config = json.loads(mock_config_path.read_text())
    assert len(updated_config["enabledMcpjsonServers"]) == 1
    assert updated_config["enabledMcpjsonServers"][0]["name"] == "imported-server"

    captured = capsys.readouterr()
    assert "Successfully imported" in captured.out


def test_cmd_import_merge(mock_config_path, tmp_path, capsys):
    """Test import command (merge mode)."""
    # Create export file
    export_file = tmp_path / "import.json"
    export_data = {
        "metadata": {"server_count": 1},
        "servers": [
            {
                "name": "imported-server",
                "command": "python",
                "args": ["-m", "module"],
                "enabled": True,
            }
        ],
    }
    export_file.write_text(json.dumps(export_data, indent=2))

    args = Mock()
    args.input = str(export_file)
    args.merge = True
    args.format = "json"

    result = cmd_import(args)

    assert result == 0

    # Verify servers were merged
    updated_config = json.loads(mock_config_path.read_text())
    assert len(updated_config["enabledMcpjsonServers"]) == 2
    assert updated_config["enabledMcpjsonServers"][0]["name"] == "test-server"
    assert updated_config["enabledMcpjsonServers"][1]["name"] == "imported-server"

    captured = capsys.readouterr()
    assert "Successfully imported" in captured.out


def test_cmd_import_duplicate_without_merge(mock_config_path, tmp_path, capsys):
    """Test import command with duplicate names without merge."""
    # Create export file with duplicate name
    export_file = tmp_path / "import.json"
    export_data = {
        "metadata": {"server_count": 1},
        "servers": [
            {
                "name": "test-server",  # Already exists
                "command": "python",
                "args": [],
                "enabled": True,
            }
        ],
    }
    export_file.write_text(json.dumps(export_data, indent=2))

    args = Mock()
    args.input = str(export_file)
    args.merge = False
    args.format = "json"

    result = cmd_import(args)

    assert result == 1

    captured = capsys.readouterr()
    assert "Duplicate server names found" in captured.err


def test_cmd_import_file_not_found(mock_config_path, capsys):
    """Test import command with non-existent file."""
    args = Mock()
    args.input = "/nonexistent/file.json"
    args.merge = False
    args.format = "json"

    result = cmd_import(args)

    assert result == 1

    captured = capsys.readouterr()
    assert "Import file not found" in captured.err


def test_cmd_import_creates_backup(mock_config_path, tmp_path):
    """Test that import command creates backup."""
    # Create export file
    export_file = tmp_path / "import.json"
    export_data = {
        "metadata": {"server_count": 1},
        "servers": [
            {
                "name": "imported-server",
                "command": "python",
                "args": [],
                "enabled": True,
            }
        ],
    }
    export_file.write_text(json.dumps(export_data, indent=2))

    backup_dir = mock_config_path.parent
    initial_backups = list(backup_dir.glob("settings_backup_*.json"))

    args = Mock()
    args.input = str(export_file)
    args.merge = False
    args.format = "json"

    cmd_import(args)

    final_backups = list(backup_dir.glob("settings_backup_*.json"))
    assert len(final_backups) == len(initial_backups) + 1


def test_main_add(capsys):
    """Test main function with add command."""
    with patch("cli.cmd_add", return_value=0) as mock_add:
        # Test requires at least name and command arguments
        result = main(["add", "test-server", "node"])

        assert result == 0
        mock_add.assert_called_once()


def test_main_remove(capsys):
    """Test main function with remove command."""
    with patch("cli.cmd_remove", return_value=0) as mock_remove:
        result = main(["remove", "test-server"])

        assert result == 0
        mock_remove.assert_called_once()


def test_main_show(capsys):
    """Test main function with show command."""
    with patch("cli.cmd_show", return_value=0) as mock_show:
        result = main(["show", "test-server"])

        assert result == 0
        mock_show.assert_called_once()


def test_main_export(capsys):
    """Test main function with export command."""
    with patch("cli.cmd_export", return_value=0) as mock_export:
        result = main(["export"])

        assert result == 0
        mock_export.assert_called_once()


def test_main_import(capsys):
    """Test main function with import command."""
    with patch("cli.cmd_import", return_value=0) as mock_import:
        result = main(["import", "file.json"])

        assert result == 0
        mock_import.assert_called_once()

