#!/usr/bin/env python3
"""
Extract version from pyproject.toml

Simple utility script to extract the version string from pyproject.toml.
Used by GitHub Actions workflows for version management.

Usage:
    python scripts/get_version.py
    python scripts/get_version.py path/to/pyproject.toml

Exit codes:
    0: Success, version printed to stdout
    1: Error (file not found or version not found)
"""

import re
import sys
from pathlib import Path


def get_version(pyproject_path: Path) -> str | None:
    """
    Extract version string from pyproject.toml file.

    Args:
        pyproject_path: Path to pyproject.toml file

    Returns:
        Version string (e.g., "0.5.7") or None if not found
    """
    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found", file=sys.stderr)
        return None

    try:
        content = pyproject_path.read_text()
        # Match: version = "X.Y.Z"
        pattern = r'^\s*version\s*=\s*"([^"]+)"'
        match = re.search(pattern, content, re.MULTILINE)

        if match:
            return match.group(1)
        else:
            print("Error: Version not found in pyproject.toml", file=sys.stderr)
            return None

    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return None


def main() -> int:
    """
    Main entry point.

    Returns:
        0 if version extracted successfully, 1 if error
    """
    # Get path from command line or use default
    if len(sys.argv) > 1:
        pyproject_path = Path(sys.argv[1])
    else:
        pyproject_path = Path("pyproject.toml")

    version = get_version(pyproject_path)

    if version:
        print(version)
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
