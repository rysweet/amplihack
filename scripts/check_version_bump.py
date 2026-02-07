#!/usr/bin/env python3
"""
Version Bump Checker for Amplihack

Validates that pull requests bump the version in pyproject.toml before merging to main.
Uses semantic versioning (major.minor.patch) to ensure version increases.

Exit codes:
    0: Version bumped correctly
    1: Version not bumped, decreased, or invalid format

Usage:
    python scripts/check_version_bump.py
"""

import re
import subprocess
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


def compare_versions(current: Tuple[int, int, int], previous: Tuple[int, int, int]) -> str:
    """
    Compare two semantic versions.

    Args:
        current: Current version tuple (major, minor, patch)
        previous: Previous version tuple (major, minor, patch)

    Returns:
        "increased" if current > previous
        "same" if current == previous
        "decreased" if current < previous
    """
    if current > previous:
        return "increased"
    elif current == previous:
        return "same"
    else:
        return "decreased"


def get_main_branch_version() -> Optional[str]:
    """
    Get version from pyproject.toml on main branch using git.

    Returns:
        Version string from main branch or None if error
    """
    try:
        # Use git show to get pyproject.toml content from main branch
        result = subprocess.run(
            ["git", "show", "origin/main:pyproject.toml"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode != 0:
            print("⚠️  Warning: Could not fetch pyproject.toml from origin/main", file=sys.stderr)
            print(f"   Git error: {result.stderr.strip()}", file=sys.stderr)
            return None

        return parse_version_from_pyproject(result.stdout)

    except subprocess.TimeoutExpired:
        print("⚠️  Warning: Git command timed out", file=sys.stderr)
        return None
    except Exception as e:
        print(f"⚠️  Warning: Error running git: {e}", file=sys.stderr)
        return None


def get_current_branch_version() -> Optional[str]:
    """
    Get version from current working directory's pyproject.toml.

    Returns:
        Version string from current branch or None if error
    """
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        print("❌ Error: pyproject.toml not found in current directory", file=sys.stderr)
        return None

    try:
        content = pyproject_path.read_text()
        return parse_version_from_pyproject(content)
    except Exception as e:
        print(f"❌ Error reading pyproject.toml: {e}", file=sys.stderr)
        return None


def print_error_message(main_version: str, current_version: str, comparison: str):
    """
    Print helpful error message when version check fails.

    Args:
        main_version: Version on main branch
        current_version: Version on current branch
        comparison: Result from compare_versions()
    """
    print("\n" + "=" * 70, file=sys.stderr)
    print("❌ Version Check Failed!", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    if comparison == "same":
        print(f"\nCurrent version in main: {main_version}", file=sys.stderr)
        print(f"Current version in PR:   {current_version}", file=sys.stderr)
        print("\n⚠️  Version not bumped!", file=sys.stderr)
        print(
            "\nPlease bump the version in pyproject.toml (line 8) before merging.", file=sys.stderr
        )

    elif comparison == "decreased":
        print(f"\nCurrent version in main: {main_version}", file=sys.stderr)
        print(f"Current version in PR:   {current_version}", file=sys.stderr)
        print("\n⚠️  Version decreased! This is not allowed.", file=sys.stderr)
        print("\nPlease ensure the version is greater than main branch.", file=sys.stderr)

    print("\n" + "-" * 70, file=sys.stderr)
    print("Semantic Versioning Guide:", file=sys.stderr)
    print("-" * 70, file=sys.stderr)
    print(f"• Patch ({main_version} → ", end="", file=sys.stderr)

    # Calculate example patch version
    main_parsed = parse_semantic_version(main_version)
    if main_parsed:
        major, minor, patch = main_parsed
        print(f"{major}.{minor}.{patch + 1}): Bug fixes, no API changes", file=sys.stderr)
        print(
            f"• Minor ({main_version} → {major}.{minor + 1}.0): New features, backward-compatible",
            file=sys.stderr,
        )
        print(f"• Major ({main_version} → {major + 1}.0.0): Breaking changes", file=sys.stderr)
    else:
        print("?.?.?): See semantic versioning rules", file=sys.stderr)

    print("\n" + "=" * 70 + "\n", file=sys.stderr)


def main() -> int:
    """
    Main entry point for version bump checker.

    Returns:
        0 if version bumped correctly, 1 if not
    """
    # Get versions from both branches
    main_version = get_main_branch_version()
    current_version = get_current_branch_version()

    # Handle missing versions
    if main_version is None:
        print("❌ Error: Could not extract version from main branch", file=sys.stderr)
        return 1

    if current_version is None:
        print("❌ Error: Could not extract version from current branch", file=sys.stderr)
        return 1

    # Parse semantic versions
    main_parsed = parse_semantic_version(main_version)
    current_parsed = parse_semantic_version(current_version)

    if main_parsed is None:
        print(f"❌ Error: Invalid version format in main branch: {main_version}", file=sys.stderr)
        print("   Expected format: X.Y.Z (e.g., 0.2.0)", file=sys.stderr)
        return 1

    if current_parsed is None:
        print(
            f"❌ Error: Invalid version format in current branch: {current_version}",
            file=sys.stderr,
        )
        print("   Expected format: X.Y.Z (e.g., 0.2.1)", file=sys.stderr)
        return 1

    # Compare versions
    comparison = compare_versions(current_parsed, main_parsed)

    if comparison == "increased":
        # Success!
        print(f"✅ Version bumped correctly: {main_version} → {current_version}")
        return 0

    else:
        # Failure - print helpful error message
        print_error_message(main_version, current_version, comparison)
        return 1


if __name__ == "__main__":
    sys.exit(main())
