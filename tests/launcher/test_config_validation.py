"""Tests for validate_and_repair_copilot_config (issue #3671).

Ensures that installed_plugins entries in config.json are validated
and repaired before launching nested Copilot agents.
"""

import json
from pathlib import Path

from amplihack.launcher.copilot import (
    REQUIRED_PLUGIN_FIELDS,
    validate_and_repair_copilot_config,
)


def _write_config(copilot_home: Path, config: dict) -> Path:
    """Write config.json and return the file path."""
    config_file = copilot_home / "config.json"
    config_file.write_text(json.dumps(config, indent=2) + "\n")
    return config_file


# --- Happy path ---


def test_no_repair_needed(tmp_path: Path) -> None:
    """All fields present and correct — no write should happen."""
    config = {
        "installed_plugins": [
            {
                "name": "amplihack",
                "marketplace": "local",
                "version": "1.0.0",
                "enabled": True,
                "cache_path": "/some/path",
                "source": "local",
                "installed_at": "2025-06-15T10:30:00+00:00",
            }
        ]
    }
    config_file = _write_config(tmp_path, config)
    original = config_file.read_text()

    assert validate_and_repair_copilot_config(tmp_path) is True
    # File should NOT be rewritten (write-only-when-dirty)
    assert config_file.read_text() == original


def test_no_installed_plugins_key(tmp_path: Path) -> None:
    """Config without installed_plugins key — nothing to validate."""
    _write_config(tmp_path, {"some_other_key": "value"})
    assert validate_and_repair_copilot_config(tmp_path) is True


def test_no_config_file(tmp_path: Path) -> None:
    """No config.json at all — returns True (nothing to fix)."""
    assert validate_and_repair_copilot_config(tmp_path) is True


# --- Repair scenarios ---


def test_missing_installed_at(tmp_path: Path) -> None:
    """Missing installed_at triggers repair with epoch default."""
    config = {
        "installed_plugins": [
            {
                "name": "amplihack",
                "marketplace": "local",
                "version": "1.0.0",
                "enabled": True,
                "cache_path": "/some/path",
                "source": "local",
                # installed_at deliberately missing
            }
        ]
    }
    _write_config(tmp_path, config)

    assert validate_and_repair_copilot_config(tmp_path) is True

    repaired = json.loads((tmp_path / "config.json").read_text())
    assert repaired["installed_plugins"][0]["installed_at"] == "1970-01-01T00:00:00+00:00"


def test_missing_name(tmp_path: Path) -> None:
    """Missing name gets default 'unknown'."""
    config = {
        "installed_plugins": [
            {
                "marketplace": "local",
                "version": "1.0.0",
                "enabled": True,
                "cache_path": "/some/path",
                "source": "local",
                "installed_at": "2025-01-01T00:00:00+00:00",
            }
        ]
    }
    _write_config(tmp_path, config)

    assert validate_and_repair_copilot_config(tmp_path) is True

    repaired = json.loads((tmp_path / "config.json").read_text())
    assert repaired["installed_plugins"][0]["name"] == "unknown"


def test_missing_all_fields_except_name(tmp_path: Path) -> None:
    """Entry with only name — all other fields backfilled."""
    config = {"installed_plugins": [{"name": "some-plugin"}]}
    _write_config(tmp_path, config)

    assert validate_and_repair_copilot_config(tmp_path) is True

    repaired = json.loads((tmp_path / "config.json").read_text())
    entry = repaired["installed_plugins"][0]
    assert entry["name"] == "some-plugin"  # preserved
    for field, default in REQUIRED_PLUGIN_FIELDS.items():
        if field == "name":
            continue
        assert entry[field] == default


def test_multiple_plugins_repaired(tmp_path: Path) -> None:
    """Repairs multiple broken entries, not just the first."""
    config = {
        "installed_plugins": [
            {"name": "plugin-a"},  # missing most fields
            {"name": "plugin-b"},  # missing most fields
        ]
    }
    _write_config(tmp_path, config)

    assert validate_and_repair_copilot_config(tmp_path) is True

    repaired = json.loads((tmp_path / "config.json").read_text())
    for entry in repaired["installed_plugins"]:
        for field in REQUIRED_PLUGIN_FIELDS:
            assert field in entry


def test_existing_values_not_overwritten(tmp_path: Path) -> None:
    """Valid existing values must be preserved — only fill gaps."""
    config = {
        "installed_plugins": [
            {
                "name": "custom-plugin",
                "marketplace": "npm",
                "version": "2.3.4",
                "enabled": True,
                "cache_path": "/custom/path",
                "source": "npm",
                "installed_at": "2025-03-15T12:00:00+00:00",
            }
        ]
    }
    _write_config(tmp_path, config)

    assert validate_and_repair_copilot_config(tmp_path) is True

    repaired = json.loads((tmp_path / "config.json").read_text())
    entry = repaired["installed_plugins"][0]
    assert entry["name"] == "custom-plugin"
    assert entry["marketplace"] == "npm"
    assert entry["version"] == "2.3.4"
    assert entry["cache_path"] == "/custom/path"
    assert entry["source"] == "npm"
    assert entry["installed_at"] == "2025-03-15T12:00:00+00:00"


# --- Edge cases ---


def test_non_dict_entries_skipped(tmp_path: Path) -> None:
    """Non-dict entries (null, string, int) don't crash validation."""
    config = {
        "installed_plugins": [
            None,
            "not-a-dict",
            42,
            {"name": "real-plugin"},
        ]
    }
    _write_config(tmp_path, config)

    assert validate_and_repair_copilot_config(tmp_path) is True

    repaired = json.loads((tmp_path / "config.json").read_text())
    # The real entry should be repaired
    real_entry = repaired["installed_plugins"][3]
    assert real_entry["name"] == "real-plugin"
    for field in REQUIRED_PLUGIN_FIELDS:
        assert field in real_entry


def test_non_list_installed_plugins(tmp_path: Path) -> None:
    """installed_plugins is not a list — returns True, no crash."""
    config = {"installed_plugins": "not-a-list"}
    _write_config(tmp_path, config)
    assert validate_and_repair_copilot_config(tmp_path) is True


def test_wrong_type_gets_replaced(tmp_path: Path) -> None:
    """enabled as string instead of bool triggers repair."""
    config = {
        "installed_plugins": [
            {
                "name": "amplihack",
                "marketplace": "local",
                "version": "1.0.0",
                "enabled": "true",  # wrong type — should be bool
                "cache_path": "/some/path",
                "source": "local",
                "installed_at": "2025-01-01T00:00:00+00:00",
            }
        ]
    }
    _write_config(tmp_path, config)

    assert validate_and_repair_copilot_config(tmp_path) is True

    repaired = json.loads((tmp_path / "config.json").read_text())
    assert repaired["installed_plugins"][0]["enabled"] is True


# --- Error handling ---


def test_malformed_json(tmp_path: Path) -> None:
    """Malformed JSON returns False, never raises."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{invalid json!!!")

    assert validate_and_repair_copilot_config(tmp_path) is False


def test_permission_error(tmp_path: Path) -> None:
    """Read-only config.json with broken entries returns False."""
    config = {"installed_plugins": [{"name": "broken"}]}
    config_file = _write_config(tmp_path, config)
    config_file.chmod(0o444)

    result = validate_and_repair_copilot_config(tmp_path)
    # Should return False because it can't write the repaired config
    assert result is False

    config_file.chmod(0o644)  # cleanup


def test_empty_plugins_list(tmp_path: Path) -> None:
    """Empty installed_plugins list — nothing to validate."""
    config = {"installed_plugins": []}
    _write_config(tmp_path, config)
    assert validate_and_repair_copilot_config(tmp_path) is True
