"""Tests for config_manager module."""

import json

import pytest
from config_manager import backup_config, read_config, restore_config, write_config


@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary config file for testing."""
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
        ],
        "hooks": {},
    }

    config_path.write_text(json.dumps(config, indent=2))
    return config_path


def test_read_config(temp_config):
    """Test reading configuration file."""
    config = read_config(temp_config)

    assert isinstance(config, dict)
    assert "enabledMcpjsonServers" in config
    assert len(config["enabledMcpjsonServers"]) == 1
    assert config["enabledMcpjsonServers"][0]["name"] == "test-server"


def test_read_config_not_found(tmp_path):
    """Test reading non-existent config file."""
    config_path = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError):
        read_config(config_path)


def test_read_config_invalid_json(tmp_path):
    """Test reading invalid JSON config file."""
    config_path = tmp_path / "invalid.json"
    config_path.write_text("{invalid json")

    with pytest.raises(json.JSONDecodeError):
        read_config(config_path)


def test_write_config(tmp_path):
    """Test writing configuration file."""
    config_path = tmp_path / ".claude" / "settings.json"
    config = {"enabledMcpjsonServers": [], "test": "data"}

    write_config(config_path, config)

    assert config_path.exists()
    written_data = json.loads(config_path.read_text())
    assert written_data == config


def test_write_config_atomic(tmp_path):
    """Test that write is atomic (uses temp file)."""
    config_path = tmp_path / "settings.json"
    config = {"test": "data"}

    write_config(config_path, config)

    # Ensure no .tmp file remains
    temp_path = config_path.with_suffix(".tmp")
    assert not temp_path.exists()

    # Verify content
    assert config_path.exists()
    written_data = json.loads(config_path.read_text())
    assert written_data == config


def test_write_config_preserves_permissions(tmp_path):
    """Test that write preserves file permissions."""
    config_path = tmp_path / "settings.json"
    config_path.write_text("{}")
    config_path.chmod(0o600)

    original_mode = config_path.stat().st_mode

    write_config(config_path, {"updated": True})

    new_mode = config_path.stat().st_mode
    assert new_mode == original_mode


def test_backup_config(temp_config):
    """Test creating config backup."""
    backup_path = backup_config(temp_config)

    assert backup_path.exists()
    assert backup_path.name.startswith("settings_backup_")
    assert backup_path.suffix == ".json"

    # Verify backup content matches original
    original_data = json.loads(temp_config.read_text())
    backup_data = json.loads(backup_path.read_text())
    assert backup_data == original_data


def test_backup_config_not_found(tmp_path):
    """Test backing up non-existent config."""
    config_path = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError):
        backup_config(config_path)


def test_backup_cleanup(temp_config):
    """Test that old backups are cleaned up."""
    # Create 12 backups (should keep only 10 most recent)
    # Timestamps include microseconds for uniqueness
    backups = []
    for i in range(12):
        backup_path = backup_config(temp_config)
        backups.append(backup_path)

    # Check that only 3 backups remain (reduced from 10 per philosophy)
    backup_dir = temp_config.parent
    backup_files = list(backup_dir.glob("settings_backup_*.json"))
    assert len(backup_files) == 3

    # Verify oldest backups were removed (12 created, 3 kept = 9 removed)
    remaining_backups = [b.name for b in backup_files]
    for old_backup in backups[:9]:
        assert old_backup.name not in remaining_backups


def test_restore_config(temp_config):
    """Test restoring config from backup."""
    # Create backup
    backup_path = backup_config(temp_config)

    # Modify original
    modified_config = {"modified": True}
    write_config(temp_config, modified_config)

    # Restore from backup
    restore_config(backup_path, temp_config)

    # Verify original content restored
    restored_data = json.loads(temp_config.read_text())
    assert "enabledMcpjsonServers" in restored_data
    assert restored_data["enabledMcpjsonServers"][0]["name"] == "test-server"


def test_restore_config_not_found(tmp_path):
    """Test restoring from non-existent backup."""
    backup_path = tmp_path / "nonexistent_backup.json"
    config_path = tmp_path / "settings.json"

    with pytest.raises(FileNotFoundError):
        restore_config(backup_path, config_path)
