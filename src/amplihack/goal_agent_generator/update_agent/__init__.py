"""
Update Agent - Update existing goal agents with improvements.

Public interface for updating agents.
"""

from .version_detector import VersionDetector
from .changeset_generator import ChangesetGenerator
from .backup_manager import BackupManager
from .selective_updater import SelectiveUpdater

__all__ = [
    "VersionDetector",
    "ChangesetGenerator",
    "BackupManager",
    "SelectiveUpdater",
]
