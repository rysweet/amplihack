"""Simple file tracking registry for UVX cleanup operations.

Tracks files created during UVX staging for safe cleanup on exit.
"""

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set

logger = logging.getLogger(__name__)

# Security: Limit registry size to prevent DOS
MAX_TRACKED_PATHS = 10000


@dataclass
class CleanupRegistry:
    """Tracks files to cleanup on exit.

    Simple file-based registry that records paths staged during
    UVX deployment for removal on exit.
    """

    session_id: str
    working_dir: Path
    _paths: Set[Path] = field(default_factory=set)

    def register(self, path: Path) -> bool:
        """Register a path for cleanup.

        Args:
            path: Path to track for cleanup

        Returns:
            True if path was registered, False if invalid
        """
        # Security: Prevent DOS via unbounded registry growth
        if len(self._paths) >= MAX_TRACKED_PATHS:
            logger.warning(f"Registry size limit reached ({MAX_TRACKED_PATHS}), skipping {path}")
            return False

        resolved = path.resolve()
        self._paths.add(resolved)
        return True

    def get_tracked_paths(self) -> List[Path]:
        """Get all tracked paths in deletion-safe order.

        Returns:
            List of paths, sorted deepest-first for safe deletion
        """
        # Sort by path depth (deepest first) for safe deletion
        return sorted(self._paths, key=lambda p: len(p.parts), reverse=True)

    def save(self, registry_path: Path | None = None) -> None:
        """Save registry to disk with secure permissions.

        Args:
            registry_path: Path to save registry (default: tempdir/amplihack-cleanup-{session_id}.json)  # noqa
        """
        if registry_path is None:
            # Use system temp directory (cross-platform)
            temp_dir = Path(tempfile.gettempdir())
            registry_path = temp_dir / f"amplihack-cleanup-{self.session_id}.json"

        data = {
            "session_id": self.session_id,
            "working_directory": str(self.working_dir),
            "paths": [str(p) for p in self._paths],
        }

        # SECURITY: Create with restrictive permissions (owner read/write only)
        # touch with mode 0o600 before writing
        registry_path.touch(mode=0o600, exist_ok=True)
        registry_path.write_text(json.dumps(data, indent=2))

        # Verify permissions were set correctly
        actual_mode = registry_path.stat().st_mode & 0o777
        if actual_mode != 0o600:
            logger.warning(f"Registry file has unexpected permissions: {oct(actual_mode)}")

    @classmethod
    def load(cls, registry_path: Path) -> "CleanupRegistry | None":
        """Load registry from disk with security validation.

        Args:
            registry_path: Path to registry file

        Returns:
            CleanupRegistry if loaded successfully, None on error
        """
        try:
            # SECURITY: Verify file permissions before loading
            stat_info = registry_path.stat()
            file_mode = stat_info.st_mode & 0o777

            # Warn if group/other have any permissions (Unix-like systems)
            if os.name != "nt" and file_mode & 0o077:
                logger.warning(
                    f"Registry file has insecure permissions {oct(file_mode)}: {registry_path}"
                )
                # Continue loading but log warning

            # Load and validate data
            data = json.loads(registry_path.read_text())
            registry = cls(
                session_id=data["session_id"], working_dir=Path(data["working_directory"])
            )
            registry._paths = {Path(p) for p in data["paths"]}
            return registry
        except (FileNotFoundError, json.JSONDecodeError, KeyError, OSError) as e:
            logger.debug(f"Failed to load registry from {registry_path}: {e}")
            return None
