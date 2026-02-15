#!/usr/bin/env python3
"""
Extract version from pyproject.toml

Simple utility script to extract the version string from pyproject.toml.
Used by GitHub Actions workflows for version management.

Usage:
    python scripts/get_version.py                      # Read from pyproject.toml
    python scripts/get_version.py path/to/file.toml    # Read from specified file
    cat file.toml | python scripts/get_version.py -    # Read from stdin

Exit codes:
    0: Success, version printed to stdout
    1: Error (file not found or version not found)
"""

import re
import sys
from pathlib import Path


def extract_version_from_content(content: str) -> str | None:
    """
    Extract version string from pyproject.toml content.

    Args:
        content: Contents of pyproject.toml file

    Returns:
        Version string (e.g., "0.5.7") or None if not found
    """
    # Match: version = "X.Y.Z"
    pattern = r'^\s*version\s*=\s*"([^"]+)"'
    match = re.search(pattern, content, re.MULTILINE)

    if match:
        return match.group(1)
    else:
        return None


def get_version_from_file(pyproject_path: Path) -> str | None:
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
        return extract_version_from_content(content)

    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return None


def get_version_from_stdin() -> str | None:
    """
    Extract version string from stdin.

    Returns:
        Version string (e.g., "0.5.7") or None if not found
    """
    try:
        content = sys.stdin.read()
        if not content:
            print("Error: No content received from stdin", file=sys.stderr)
            return None
        return extract_version_from_content(content)

    except Exception as e:
        print(f"Error reading stdin: {e}", file=sys.stderr)
        return None


def main() -> int:
    """
    Main entry point.

    Returns:
        0 if version extracted successfully, 1 if error
    """
    # Determine source: stdin or file
    if len(sys.argv) > 1 and sys.argv[1] == "-":
        # Read from stdin
        version = get_version_from_stdin()
    elif len(sys.argv) > 1:
        # Read from specified file
        pyproject_path = Path(sys.argv[1])
        version = get_version_from_file(pyproject_path)
    else:
        # Read from default location
        pyproject_path = Path("pyproject.toml")
        version = get_version_from_file(pyproject_path)

    if version:
        print(version)
        return 0
    else:
        print("Error: Version not found", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
