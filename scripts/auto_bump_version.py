#!/usr/bin/env python3
"""
Auto Version Bumper for Amplihack

Automatically bumps the patch version in pyproject.toml when a PR fails version check.
Used by the version-check workflow to automatically fix version bump failures.

Exit codes:
    0: Version bumped successfully
    1: Error occurred during version bump

Usage:
    python scripts/auto_bump_version.py
"""

import re
import sys
from pathlib import Path
from typing import Optional, Tuple


def parse_version_from_pyproject(content: str) -> Optional[str]:
    """
    Extract version string from pyproject.toml content.

    Args:
        content: Contents of pyproject.toml file

    Returns:
        Version string (e.g., "0.2.0") or None if not found
    """
    # Match: version = "X.Y.Z" with optional quotes
    pattern = r'^\s*version\s*=\s*["\']([^"\']+)["\']'

    for line in content.split("\n"):
        match = re.match(pattern, line)
        if match:
            return match.group(1)

    return None


def parse_semantic_version(version_str: str) -> Optional[Tuple[int, int, int]]:
    """
    Parse semantic version string into tuple of integers.

    Args:
        version_str: Version string (e.g., "0.2.0")

    Returns:
        Tuple of (major, minor, patch) or None if invalid format
    """
    # Match: X.Y.Z where X, Y, Z are integers
    pattern = r"^(\d+)\.(\d+)\.(\d+)$"
    match = re.match(pattern, version_str)

    if not match:
        return None

    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def bump_patch_version(version_str: str) -> Optional[str]:
    """
    Bump the patch version of a semantic version string.

    Args:
        version_str: Version string (e.g., "0.2.0")

    Returns:
        Bumped version string (e.g., "0.2.1") or None if invalid format
    """
    parsed = parse_semantic_version(version_str)
    if parsed is None:
        return None

    major, minor, patch = parsed
    return f"{major}.{minor}.{patch + 1}"


def update_version_in_pyproject(new_version: str) -> bool:
    """
    Update the version in pyproject.toml file.

    Args:
        new_version: New version string to set

    Returns:
        True if successful, False otherwise
    """
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        print("❌ Error: pyproject.toml not found in current directory", file=sys.stderr)
        return False

    try:
        content = pyproject_path.read_text()
        
        # Replace version line
        pattern = r'^(\s*version\s*=\s*["\'])([^"\']+)(["\'])'
        
        def replace_version(match):
            return f"{match.group(1)}{new_version}{match.group(3)}"
        
        updated_content = re.sub(pattern, replace_version, content, count=1, flags=re.MULTILINE)
        
        # Verify the replacement happened
        if updated_content == content:
            print("❌ Error: Failed to find and replace version in pyproject.toml", file=sys.stderr)
            return False
        
        # Write back
        pyproject_path.write_text(updated_content)
        return True

    except Exception as e:
        print(f"❌ Error updating pyproject.toml: {e}", file=sys.stderr)
        return False


def main() -> int:
    """
    Main entry point for auto version bumper.

    Returns:
        0 if version bumped successfully, 1 if error
    """
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        print("❌ Error: pyproject.toml not found", file=sys.stderr)
        return 1

    # Read current version
    try:
        content = pyproject_path.read_text()
        current_version = parse_version_from_pyproject(content)

        if current_version is None:
            print("❌ Error: Could not extract current version from pyproject.toml", file=sys.stderr)
            return 1

        # Bump patch version
        new_version = bump_patch_version(current_version)

        if new_version is None:
            print(f"❌ Error: Invalid version format: {current_version}", file=sys.stderr)
            print("   Expected format: X.Y.Z (e.g., 0.2.0)", file=sys.stderr)
            return 1

        # Update the file
        if not update_version_in_pyproject(new_version):
            return 1

        print(f"✅ Version bumped automatically: {current_version} → {new_version}")
        print(f"   Updated pyproject.toml")
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
