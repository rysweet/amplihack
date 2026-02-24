"""Exclusion list manager for silent degradation audits.

Manages dual-scope exclusion lists (global + per-codebase) with pattern matching
for filtering audit findings. Supports glob and regex patterns for flexible
exclusion rules.
"""

import json
import re
from pathlib import Path
from typing import Any


class ExclusionManager:
    """Manages exclusion lists and pattern matching for audit findings."""

    def __init__(self):
        """Initialize the exclusion manager."""
        self.exclusions: list[dict[str, Any]] = []

    def _validate_pattern(self, pattern: str) -> bool:
        """Validate that pattern doesn't escape intended scope.

        Args:
            pattern: Glob or regex pattern to validate

        Returns:
            True if pattern is safe

        Raises:
            ValueError: If pattern contains unsafe sequences
        """
        if pattern.startswith("/"):
            raise ValueError(f"Unsafe pattern (absolute path): {pattern}")
        if ".." in pattern:
            raise ValueError(f"Unsafe pattern (parent directory): {pattern}")
        return True

    def load_exclusions(
        self, global_path: Path | None = None, repo_path: Path | None = None
    ) -> list[dict[str, Any]]:
        """Load and merge exclusions from global and repository-specific files.

        Args:
            global_path: Path to global exclusions file (optional)
            repo_path: Path to repository-specific exclusions file (optional)

        Returns:
            List of merged exclusion entries

        Example exclusion entry:
            {
                "pattern": "*.test.js",
                "reason": "Test files excluded from production audits",
                "wave": 1,
                "category": "dependency-failures",
                "type": "glob"
            }
        """
        exclusions = []

        if global_path and global_path.exists():
            try:
                with open(global_path) as f:
                    global_exclusions = json.load(f)
                    if isinstance(global_exclusions, list):
                        # Validate patterns for security
                        for excl in global_exclusions:
                            if "pattern" in excl:
                                self._validate_pattern(excl["pattern"])
                        exclusions.extend(global_exclusions)
            except (OSError, json.JSONDecodeError, ValueError) as e:
                print(f"Warning: Could not load global exclusions: {e}")

        if repo_path and repo_path.exists():
            try:
                with open(repo_path) as f:
                    repo_exclusions = json.load(f)
                    if isinstance(repo_exclusions, list):
                        # Validate patterns for security
                        for excl in repo_exclusions:
                            if "pattern" in excl:
                                self._validate_pattern(excl["pattern"])
                        exclusions.extend(repo_exclusions)
            except (OSError, json.JSONDecodeError, ValueError) as e:
                print(f"Warning: Could not load repo exclusions: {e}")

        self.exclusions = exclusions
        return exclusions

    def filter_findings(
        self, findings: list[dict[str, Any]], exclusions: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Filter findings against exclusion list.

        Args:
            findings: List of audit findings to filter
            exclusions: Optional specific exclusion list (uses loaded if None)

        Returns:
            List of findings after applying exclusions
        """
        if exclusions is None:
            exclusions = self.exclusions

        if not exclusions:
            return findings

        filtered = []
        for finding in findings:
            if not self._is_excluded(finding, exclusions):
                filtered.append(finding)

        return filtered

    def add_exclusion(
        self,
        finding: dict[str, Any],
        reason: str,
        wave: int,
        exclusion_file: Path,
    ) -> bool:
        """Add a new exclusion based on a finding.

        Args:
            finding: The finding to create an exclusion for
            reason: Human-readable reason for exclusion
            wave: Wave number where exclusion was added
            exclusion_file: Path to exclusion file to append to

        Returns:
            True if exclusion was added successfully
        """
        pattern = finding.get("file", finding.get("pattern", "*"))

        # Validate pattern for security
        try:
            self._validate_pattern(pattern)
        except ValueError as e:
            print(f"Error: Invalid exclusion pattern: {e}")
            return False

        exclusion = {
            "pattern": pattern,
            "reason": reason,
            "wave": wave,
            "category": finding.get("category", "unknown"),
            "type": "glob" if "*" in finding.get("file", "") else "exact",
        }

        try:
            existing = []
            if exclusion_file.exists():
                with open(exclusion_file) as f:
                    existing = json.load(f)

            existing.append(exclusion)

            with open(exclusion_file, "w") as f:
                json.dump(existing, f, indent=2)

            self.exclusions.append(exclusion)
            return True

        except (OSError, json.JSONDecodeError) as e:
            print(f"Error adding exclusion: {e}")
            return False

    def matches_exclusion(self, finding: dict[str, Any], exclusion: dict[str, Any]) -> bool:
        """Check if a finding matches an exclusion pattern.

        Args:
            finding: The finding to check
            exclusion: The exclusion pattern to match against

        Returns:
            True if finding matches exclusion
        """
        return self._is_excluded(finding, [exclusion])

    def _is_excluded(self, finding: dict[str, Any], exclusions: list[dict[str, Any]]) -> bool:
        """Internal method to check if finding is excluded."""
        file_path = finding.get("file", "")
        category = finding.get("category", "")
        description = finding.get("description", "")

        for exclusion in exclusions:
            pattern = exclusion.get("pattern", "")
            excl_category = exclusion.get("category")
            excl_type = exclusion.get("type", "glob")

            if excl_category and excl_category != category:
                continue

            if excl_type == "glob":
                if self._glob_match(file_path, pattern):
                    return True
            elif excl_type == "regex":
                if self._regex_match(file_path, pattern):
                    return True
                if self._regex_match(description, pattern):
                    return True
            elif excl_type == "exact":
                if file_path == pattern:
                    return True

        return False

    def _glob_match(self, path: str, pattern: str) -> bool:
        """Match path against glob pattern."""
        from fnmatch import fnmatch

        return fnmatch(path, pattern)

    def _regex_match(self, text: str, pattern: str) -> bool:
        """Match text against regex pattern."""
        try:
            return bool(re.search(pattern, text))
        except re.error:
            return False


def load_exclusions(
    global_path: Path | None = None, repo_path: Path | None = None
) -> list[dict[str, Any]]:
    """Convenience function to load exclusions.

    Args:
        global_path: Path to global exclusions file
        repo_path: Path to repository-specific exclusions file

    Returns:
        List of merged exclusion entries
    """
    manager = ExclusionManager()
    return manager.load_exclusions(global_path, repo_path)


def filter_findings(
    findings: list[dict[str, Any]], exclusions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Convenience function to filter findings.

    Args:
        findings: List of audit findings
        exclusions: List of exclusion patterns

    Returns:
        Filtered list of findings
    """
    manager = ExclusionManager()
    manager.exclusions = exclusions
    return manager.filter_findings(findings)
