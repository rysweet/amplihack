"""
Backup Manager - Create and restore backups of agent directories.

Safely backs up agent state before updates.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class BackupManager:
    """Manage backups of agent directories."""

    def __init__(self, agent_dir: Path):
        """
        Initialize backup manager.

        Args:
            agent_dir: Path to agent directory
        """
        self.agent_dir = Path(agent_dir).resolve()
        self.backup_dir = self.agent_dir / ".backups"

    def create_backup(self, label: Optional[str] = None) -> Path:
        """
        Create backup of agent directory.

        Args:
            label: Optional label for backup (default: timestamp)

        Returns:
            Path to backup directory

        Raises:
            IOError: If backup creation fails
        """
        # Create backups directory if needed
        self.backup_dir.mkdir(exist_ok=True)

        # Generate backup name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        if label:
            backup_name = f"{backup_name}_{label}"

        backup_path = self.backup_dir / backup_name

        # Copy directory (excluding backups and cache)
        self._copy_directory(self.agent_dir, backup_path)

        return backup_path

    def restore_backup(self, backup_name: str) -> None:
        """
        Restore from backup.

        Args:
            backup_name: Name of backup to restore

        Raises:
            ValueError: If backup not found
            IOError: If restore fails
        """
        # Sanitize backup name (no path separators)
        if any(char in backup_name for char in ['/', '\\', '..']):
            raise ValueError(f"Invalid backup name: {backup_name}")

        backup_path = (self.backup_dir / backup_name).resolve()

        # Ensure within backup_dir
        if not str(backup_path).startswith(str(self.backup_dir.resolve())):
            raise ValueError(f"Path traversal in backup name: {backup_name}")

        if not backup_path.exists():
            raise ValueError(f"Backup not found: {backup_name}")

        # Create temporary backup of current state
        temp_backup = self.create_backup(label="pre_restore")

        try:
            # Clear current directory (except backups)
            self._clear_directory(self.agent_dir, keep_backups=True)

            # Restore from backup
            self._copy_directory(backup_path, self.agent_dir)

        except Exception as e:
            # Restore from temp backup on failure
            self._clear_directory(self.agent_dir, keep_backups=True)
            self._copy_directory(temp_backup, self.agent_dir)
            raise IOError(f"Restore failed: {e}") from e

    def list_backups(self) -> List[tuple[str, datetime, int]]:
        """
        List available backups.

        Returns:
            List of (name, timestamp, size_kb) tuples
        """
        if not self.backup_dir.exists():
            return []

        backups = []
        for backup_path in self.backup_dir.iterdir():
            if not backup_path.is_dir():
                continue

            # Get timestamp from directory
            stat = backup_path.stat()
            timestamp = datetime.fromtimestamp(stat.st_mtime)

            # Calculate size
            size_kb = self._get_directory_size(backup_path)

            backups.append((backup_path.name, timestamp, size_kb))

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x[1], reverse=True)

        return backups

    def delete_backup(self, backup_name: str) -> None:
        """
        Delete a backup.

        Args:
            backup_name: Name of backup to delete

        Raises:
            ValueError: If backup not found
        """
        # Sanitize backup name (no path separators)
        if any(char in backup_name for char in ['/', '\\', '..']):
            raise ValueError(f"Invalid backup name: {backup_name}")

        backup_path = (self.backup_dir / backup_name).resolve()

        # Ensure within backup_dir
        if not str(backup_path).startswith(str(self.backup_dir.resolve())):
            raise ValueError(f"Path traversal in backup name: {backup_name}")

        if not backup_path.exists():
            raise ValueError(f"Backup not found: {backup_name}")

        shutil.rmtree(backup_path)

    def cleanup_old_backups(self, keep_count: int = 5) -> int:
        """
        Delete old backups, keeping only the most recent.

        Args:
            keep_count: Number of backups to keep

        Returns:
            Number of backups deleted
        """
        backups = self.list_backups()

        if len(backups) <= keep_count:
            return 0

        # Delete oldest backups
        deleted = 0
        for backup_name, _, _ in backups[keep_count:]:
            self.delete_backup(backup_name)
            deleted += 1

        return deleted

    def _copy_directory(self, src: Path, dst: Path) -> None:
        """
        Copy directory recursively, excluding certain patterns.

        Args:
            src: Source directory
            dst: Destination directory
        """
        # Patterns to exclude
        exclude_patterns = [
            ".backups",
            "__pycache__",
            "*.pyc",
            ".git",
            "*.egg-info",
            ".DS_Store",
        ]

        def ignore_patterns(directory: str, names: List[str]) -> List[str]:
            """Return names to ignore."""
            ignored = []
            for name in names:
                if any(self._matches_pattern(name, pattern) for pattern in exclude_patterns):
                    ignored.append(name)
            return ignored

        shutil.copytree(
            src,
            dst,
            ignore=ignore_patterns,
            dirs_exist_ok=True,
        )

    def _clear_directory(self, directory: Path, keep_backups: bool = True) -> None:
        """
        Clear directory contents.

        Args:
            directory: Directory to clear
            keep_backups: Whether to preserve .backups directory
        """
        for item in directory.iterdir():
            # Skip backups if requested
            if keep_backups and item.name == ".backups":
                continue

            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

    def _get_directory_size(self, directory: Path) -> int:
        """
        Calculate directory size in KB.

        Args:
            directory: Directory to measure

        Returns:
            Size in kilobytes
        """
        total_size = 0
        for path in directory.rglob("*"):
            if path.is_file():
                total_size += path.stat().st_size

        return total_size // 1024

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """
        Check if name matches pattern.

        Args:
            name: Name to check
            pattern: Pattern (supports * wildcard)

        Returns:
            True if matches
        """
        if "*" in pattern:
            # Simple wildcard matching
            prefix, suffix = pattern.split("*", 1)
            return name.startswith(prefix) and name.endswith(suffix)
        return name == pattern
