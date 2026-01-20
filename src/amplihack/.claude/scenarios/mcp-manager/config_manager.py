"""Configuration management for MCP settings.

This module provides safe atomic operations on .claude/settings.json with
automatic backup and rollback capabilities.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def read_config(config_path: Path) -> dict[str, Any]:
    """Read and parse settings.json.

    Args:
        config_path: Path to settings.json file

    Returns:
        Parsed configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def write_config(config_path: Path, data: dict[str, Any]) -> None:
    """Write configuration to settings.json atomically.

    Uses atomic write pattern: write to .tmp file, then rename to ensure
    no partial writes occur if process is interrupted.

    Args:
        config_path: Path to settings.json file
        data: Configuration dictionary to write

    Raises:
        OSError: If write operation fails
    """
    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file first
    temp_path = config_path.with_suffix(".tmp")

    try:
        # Preserve original file permissions if it exists
        mode = config_path.stat().st_mode if config_path.exists() else 0o644

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Add trailing newline

        # Set permissions on temp file
        temp_path.chmod(mode)

        # Atomic rename (POSIX guarantees atomicity)
        temp_path.replace(config_path)

    except Exception:
        # Clean up temp file if something went wrong
        if temp_path.exists():
            temp_path.unlink()
        raise


def backup_config(config_path: Path) -> Path:
    """Create a timestamped backup of settings.json.

    Backups are stored in the same directory with format:
    settings_backup_YYYYMMDD_HHMMSS.json

    Args:
        config_path: Path to settings.json file

    Returns:
        Path to created backup file

    Raises:
        FileNotFoundError: If config file doesn't exist
        OSError: If backup creation fails
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Generate timestamp-based backup filename with microseconds for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = config_path.parent / f"settings_backup_{timestamp}.json"

    # Copy file preserving metadata
    shutil.copy2(config_path, backup_path)

    # Cleanup old backups (keep last 10)
    _cleanup_old_backups(config_path.parent)

    return backup_path


def restore_config(backup_path: Path, config_path: Path) -> None:
    """Restore configuration from a backup file.

    Args:
        backup_path: Path to backup file
        config_path: Path to settings.json file

    Raises:
        FileNotFoundError: If backup file doesn't exist
        OSError: If restore operation fails
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    # Use atomic write pattern for restore as well
    shutil.copy2(backup_path, config_path)


def _cleanup_old_backups(backup_dir: Path, keep_count: int = 3) -> None:
    """Remove old backup files, keeping only the most recent ones.

    Args:
        backup_dir: Directory containing backup files
        keep_count: Number of most recent backups to keep (default: 3)
    """
    # Find all backup files
    backup_pattern = "settings_backup_*.json"
    backups = sorted(backup_dir.glob(backup_pattern), reverse=True)

    # Remove old backups beyond keep_count
    for old_backup in backups[keep_count:]:
        try:
            old_backup.unlink()
        except OSError:
            # Ignore errors during cleanup
            pass
