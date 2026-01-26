#!/usr/bin/env python3
"""
Unrelated Changes Detector

Detects PRs that mix unrelated changes across different concerns.
Uses heuristic-based semantic analysis to identify scope mixing.

Exit Codes:
    0: No unrelated changes detected (warnings only, does not block CI)
"""

import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml


class UnrelatedChangesDetector:
    """Detects unrelated changes in a PR."""

    def __init__(self, repo_root: Path, config_path: Path):
        """
        Initialize the detector.

        Args:
            repo_root: Path to repository root
            config_path: Path to root-hygiene-config.yml
        """
        self.repo_root = repo_root
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            print(f"ERROR: Config file not found: {self.config_path}")
            sys.exit(1)

        with open(self.config_path) as f:
            config = yaml.safe_load(f)
            return config.get("unrelated_change_detection", {})

    def _get_changed_files(self) -> list[str]:
        """
        Get list of changed files in current branch.

        Returns:
            List of changed file paths
        """
        try:
            # Get the merge base with main/master
            result = subprocess.run(
                ["git", "merge-base", "HEAD", "origin/main"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            merge_base = result.stdout.strip()

            # Get changed files since merge base
            result = subprocess.run(
                ["git", "diff", "--name-only", merge_base, "HEAD"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            files = result.stdout.strip().split("\n")
            return [f for f in files if f]

        except subprocess.CalledProcessError:
            # Fallback: try master branch
            try:
                result = subprocess.run(
                    ["git", "merge-base", "HEAD", "origin/master"],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                merge_base = result.stdout.strip()

                result = subprocess.run(
                    ["git", "diff", "--name-only", merge_base, "HEAD"],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                files = result.stdout.strip().split("\n")
                return [f for f in files if f]

            except subprocess.CalledProcessError as e:
                print(f"WARNING: Could not determine changed files: {e}")
                return []

    def _classify_file(self, filepath: str) -> set[str]:
        """
        Classify a file into scope categories.

        Args:
            filepath: Path to file

        Returns:
            Set of scope categories (ci, docs, tests, src, config, scripts)
        """
        scopes = set()
        scope_indicators = self.config.get("scope_indicators", {})

        for scope_name, patterns in scope_indicators.items():
            for pattern in patterns:
                # Check if filepath matches pattern
                if pattern.endswith("/"):
                    # Directory pattern
                    if filepath.startswith(pattern):
                        scopes.add(scope_name)
                else:
                    # File pattern
                    if pattern in filepath or filepath.endswith(pattern):
                        scopes.add(scope_name)

        # If no scope matched, classify as 'other'
        if not scopes:
            scopes.add("other")

        return scopes

    def _categorize_changes(self, files: list[str]) -> dict[str, list[str]]:
        """
        Categorize changed files by scope.

        Args:
            files: List of changed file paths

        Returns:
            Dictionary mapping scope to list of files
        """
        categories = defaultdict(list)

        for filepath in files:
            scopes = self._classify_file(filepath)
            for scope in scopes:
                categories[scope].append(filepath)

        return dict(categories)

    def _are_scopes_related(self, scopes: set[str]) -> bool:
        """
        Check if a set of scopes are related.

        Args:
            scopes: Set of scope names

        Returns:
            True if scopes are related
        """
        related_scopes = self.config.get("related_scopes", [])

        # Convert scopes to sorted tuple for comparison
        scopes_sorted = tuple(sorted(scopes))

        for related_group in related_scopes:
            related_group_sorted = tuple(sorted(related_group))
            # Check if scopes is a subset of a related group
            if set(scopes_sorted).issubset(set(related_group_sorted)):
                return True

        # If only one scope, it's related to itself
        if len(scopes) <= 1:
            return True

        return False

    def _should_warn(self, scopes: set[str]) -> bool:
        """
        Check if scope combination should trigger a warning.

        Args:
            scopes: Set of scope names

        Returns:
            True if should warn
        """
        warn_combinations = self.config.get("warn_on_combinations", [])

        for warn_combo in warn_combinations:
            if set(warn_combo).issubset(scopes):
                return True

        return False

    def analyze(self) -> tuple[bool, list[str], dict[str, list[str]]]:
        """
        Analyze changes for unrelated modifications.

        Returns:
            Tuple of (has_issues, warnings, categories)
        """
        warnings = []
        files = self._get_changed_files()

        if not files:
            return False, warnings, {}

        categories = self._categorize_changes(files)
        scopes = set(categories.keys())

        # Skip if only 'other' scope
        if scopes == {"other"}:
            return False, warnings, categories

        # Check if scopes are related
        if not self._are_scopes_related(scopes):
            warnings.append(
                f"⚠️  Potentially unrelated changes detected\n"
                f"   Scopes: {', '.join(sorted(scopes))}\n"
                f"   These changes may be addressing different concerns."
            )

        # Check for explicit warning combinations
        if self._should_warn(scopes):
            warnings.append(
                f"⚠️  Broad scope mixing detected\n"
                f"   Scopes: {', '.join(sorted(scopes))}\n"
                f"   Consider splitting this PR into focused changes."
            )

        has_issues = len(warnings) > 0
        return has_issues, warnings, categories

    def generate_report(self) -> str:
        """
        Generate a human-readable report.

        Returns:
            Report string
        """
        has_issues, warnings, categories = self.analyze()

        if not has_issues:
            return "✅ Unrelated Changes Check: PASSED\nChanges appear to be focused and related.\n"

        report = [
            "⚠️  Unrelated Changes Check: WARNINGS\n",
            f"Found {len(warnings)} potential issue(s):\n",
            "",
        ]

        for warning in warnings:
            report.append(warning)
            report.append("")

        # Add change summary
        report.append("Change Summary by Scope:")
        for scope, files in sorted(categories.items()):
            report.append(f"  {scope}: {len(files)} file(s)")

        report.extend(
            [
                "",
                "---",
                "These warnings do not block CI, but should be considered.",
                "PRs should ideally focus on a single concern or related concerns.",
                "",
                "Consider:",
                "- Splitting unrelated changes into separate PRs",
                "- Ensuring changes serve a cohesive purpose",
                "- Documenting why multiple scopes are necessary",
            ]
        )

        return "\n".join(report)


def main():
    """Main entry point."""
    # Determine repository root
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]  # Go up from .claude/ci/ to root

    # Load configuration
    config_path = repo_root / ".github" / "root-hygiene-config.yml"

    # Create detector
    detector = UnrelatedChangesDetector(repo_root, config_path)

    # Generate and print report
    report = detector.generate_report()
    print(report)

    # Always exit 0 (warnings only, don't block CI)
    sys.exit(0)


if __name__ == "__main__":
    main()
