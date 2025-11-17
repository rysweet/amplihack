"""Version manifest for amplihack package and .claude directory.

This file tracks versions to detect mismatches between the installed
package and a project's .claude directory.

Updated automatically during release process.
"""

from datetime import datetime, timezone

# Package version (from __init__.py)
VERSION = "0.1.0"  # TODO: Sync with __init__.py in CI

# Claude directory version (git commit hash)
# This changes whenever files in .claude/ are modified
CLAUDE_DIR_VERSION = "9b0cac42"  # Current commit

# Last update timestamp (ISO 8601 UTC) - static constant set during release
LAST_UPDATED = "2025-11-16T00:00:00+00:00"  # Will be updated by CI/release process


def get_version_info() -> dict:
    """Get version information as dictionary.

    Returns:
        dict with keys: version, claude_dir_version, last_updated
    """
    return {
        "version": VERSION,
        "claude_dir_version": CLAUDE_DIR_VERSION,
        "last_updated": LAST_UPDATED,
    }
