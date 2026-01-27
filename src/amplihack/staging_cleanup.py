"""Legacy skill directory cleanup executor.

This module removes safe legacy skill directories that cause false "deprecated" warnings.
"""

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .staging_safety import is_safe_to_delete

logger = logging.getLogger(__name__)


@dataclass
class CleanupResult:
    """Result of cleanup operation."""

    cleaned: list[Path] = field(default_factory=list)  # Successfully removed
    skipped: list[tuple[Path, str]] = field(default_factory=list)  # Skipped with reason
    errors: list[tuple[Path, str]] = field(default_factory=list)  # Failed with error


def cleanup_legacy_skills(
    dry_run: bool = False, legacy_dirs: list[Path] | None = None
) -> CleanupResult:
    """Remove safe legacy skill directories.

    Checks these locations (by default):
    - ~/.claude/skills/
    - ~/.claude/plugins/marketplaces/amplihack/.claude/skills/

    Algorithm:
    1. For each directory:
        a. Check if exists
        b. Run safety check
        c. If safe → remove entire directory
        d. If unsafe → skip with reason
        e. If uncertain → skip with warning
    2. Return summary of actions taken

    Args:
        dry_run: If True, only report what would be deleted
        legacy_dirs: Optional list of directories to check. If None, uses default locations.

    Returns:
        CleanupResult with cleaned/skipped/errors

    Side Effects:
        - Deletes directories when safe and not dry_run
        - Logs all actions to debug log
    """
    result = CleanupResult()

    # Use provided directories or default to standard legacy locations
    if legacy_dirs is None:
        home = Path.home()
        legacy_dirs = [
            home / ".claude" / "skills",
            home / ".claude" / "plugins" / "marketplaces" / "amplihack" / ".claude" / "skills",
        ]

    for directory in legacy_dirs:
        # Skip if doesn't exist
        if not directory.exists():
            logger.debug(f"Directory does not exist, skipping: {directory}")
            continue

        # Run safety check
        safety = is_safe_to_delete(directory)

        if safety.status == "safe":
            # Safe to delete
            if dry_run:
                logger.info(f"[DRY-RUN] Would remove: {directory}")
                result.cleaned.append(directory)
            else:
                try:
                    logger.debug(f"Removing legacy skill directory: {directory}")
                    shutil.rmtree(directory)
                    result.cleaned.append(directory)
                    logger.info(f"Removed legacy skill directory: {directory}")
                except Exception as e:
                    logger.error(f"Failed to remove {directory}: {e}")
                    result.errors.append((directory, str(e)))

        elif safety.status == "unsafe":
            # Unsafe to delete - skip
            logger.debug(f"Skipping unsafe directory: {directory} ({safety.reason})")
            result.skipped.append((directory, safety.reason))

        else:  # uncertain
            # Uncertain - skip with warning
            logger.warning(f"Skipping uncertain directory: {directory} ({safety.reason})")
            result.skipped.append((directory, safety.reason))

    return result
