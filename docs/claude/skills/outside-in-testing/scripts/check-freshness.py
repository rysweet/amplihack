#!/usr/bin/env python3
"""
Check if the embedded gadugi-agentic-test framework version is up-to-date.

This script compares the version embedded in the SKILL.md file against the
latest release on GitHub and warns if an update is available.

Usage:
    python scripts/check-freshness.py
"""

import re
import sys
from pathlib import Path
from typing import Optional, Tuple

try:
    import requests
except ImportError:
    print("Warning: requests library not installed")
    print("Install with: pip install requests")
    sys.exit(1)


# GitHub repository for gadugi-agentic-test
GITHUB_REPO = "rysweet/gadugi-agentic-test"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Skill file path (relative to script location)
SKILL_FILE = Path(__file__).parent.parent / "SKILL.md"


def extract_embedded_version(skill_file: Path) -> Optional[str]:
    """Extract the embedded framework version from SKILL.md frontmatter."""
    try:
        content = skill_file.read_text()

        # Look for embedded_framework_version in YAML frontmatter
        match = re.search(r"^embedded_framework_version:\s*(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()

        return None
    except Exception as e:
        print(f"Error reading skill file: {e}")
        return None


def get_latest_github_version() -> Optional[Tuple[str, str, str]]:
    """
    Fetch the latest release version from GitHub.

    Returns:
        Tuple of (version, release_url, release_notes) or None on failure
    """
    try:
        response = requests.get(GITHUB_API_URL, timeout=10)

        if response.status_code == 404:
            print("No releases found for repository")
            return None

        if response.status_code != 200:
            print(f"GitHub API error: {response.status_code}")
            return None

        data = response.json()
        version = data.get("tag_name", "").lstrip("v")
        release_url = data.get("html_url", "")
        release_notes = data.get("body", "")

        return (version, release_url, release_notes)

    except requests.exceptions.RequestException as e:
        print(f"Network error fetching GitHub release: {e}")
        return None
    except Exception as e:
        print(f"Error parsing GitHub response: {e}")
        return None


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse semantic version string into tuple of integers."""
    try:
        parts = version_str.split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except (ValueError, IndexError):
        return (0, 0, 0)


def compare_versions(embedded: str, latest: str) -> int:
    """
    Compare two semantic versions.

    Returns:
        -1 if embedded < latest (outdated)
         0 if embedded == latest (current)
         1 if embedded > latest (ahead of releases, likely dev version)
    """
    embedded_parts = parse_version(embedded)
    latest_parts = parse_version(latest)

    if embedded_parts < latest_parts:
        return -1
    if embedded_parts > latest_parts:
        return 1
    return 0


def extract_new_features(release_notes: str, limit: int = 5) -> list:
    """Extract feature bullets from release notes."""
    features = []

    # Look for lines starting with - or * (markdown lists)
    lines = release_notes.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith(("- ", "* ")):
            feature = line.lstrip("-*").strip()
            if feature and len(feature) > 10:  # Ignore short lines
                features.append(feature)
                if len(features) >= limit:
                    break

    return features


def main():
    """Main freshness check logic."""
    print("Checking gadugi-agentic-test framework version...")
    print()

    # Extract embedded version
    embedded_version = extract_embedded_version(SKILL_FILE)
    if not embedded_version:
        print("ERROR: Could not find embedded_framework_version in SKILL.md")
        sys.exit(1)

    print(f"Embedded version: {embedded_version}")

    # Fetch latest GitHub version
    github_data = get_latest_github_version()
    if not github_data:
        print()
        print("WARNING: Could not fetch latest version from GitHub")
        print("Check your internet connection or try again later")
        sys.exit(0)

    latest_version, release_url, release_notes = github_data
    print(f"Latest version:   {latest_version}")
    print()

    # Compare versions
    comparison = compare_versions(embedded_version, latest_version)

    if comparison == 0:
        print("✓ You are using the latest version!")
        print()
        print("The skill documentation is up-to-date with the latest framework release.")
        sys.exit(0)

    elif comparison == 1:
        print("ℹ You are ahead of the latest release")
        print()
        print("This may be a development version or pre-release.")
        print(f"Latest stable release: {latest_version}")
        print(f"Release URL: {release_url}")
        sys.exit(0)

    else:  # comparison == -1
        print("⚠ WARNING: Embedded framework version is outdated!")
        print()
        print(f"Embedded version: {embedded_version}")
        print(f"Latest version:   {latest_version}")
        print()

        # Extract new features
        features = extract_new_features(release_notes)
        if features:
            print(f"New features in {latest_version}:")
            for feature in features:
                print(f"  • {feature}")
            print()

        print("To update:")
        print("  1. Install latest framework: pip install --upgrade gadugi-agentic-test")
        print(f"  2. Review release notes: {release_url}")
        print("  3. Update SKILL.md with new version and features")
        print("  4. Update examples if API changed")
        print()

        sys.exit(1)


if __name__ == "__main__":
    main()
