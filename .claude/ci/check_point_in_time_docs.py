#!/usr/bin/env python3
"""
Point-in-Time Documentation Detector

Detects documentation that contains temporal references, indicating it may
become outdated and should be in PR descriptions rather than committed.

Exit Codes:
    0: No point-in-time documentation issues (warnings only, does not block CI)
"""

import subprocess
import sys
from pathlib import Path

import yaml


class PointInTimeDocsDetector:
    """Detects point-in-time documentation."""

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
            return config

    def _get_changed_docs(self) -> list[str]:
        """
        Get list of changed documentation files in current branch.

        Returns:
            List of changed .md file paths
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
            # Filter for markdown files
            return [f for f in files if f.endswith(".md") and f]

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
                return [f for f in files if f.endswith(".md") and f]

            except subprocess.CalledProcessError as e:
                print(f"WARNING: Could not determine changed files: {e}")
                return []

    def _scan_file_for_temporal_refs(self, filepath: Path) -> list[tuple[int, str, str]]:
        """
        Scan a file for temporal references.

        Args:
            filepath: Path to file to scan

        Returns:
            List of (line_number, line_content, matched_indicator)
        """
        matches = []
        indicators = self.config.get("point_in_time_indicators", [])

        if not filepath.exists():
            return matches

        try:
            with open(filepath, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line_lower = line.lower()
                    for indicator in indicators:
                        if indicator.lower() in line_lower:
                            matches.append((line_num, line.strip(), indicator))
                            break  # Only report first match per line

        except (UnicodeDecodeError, PermissionError) as e:
            print(f"WARNING: Could not read {filepath}: {e}")

        return matches

    def _is_root_file(self, filepath: str) -> bool:
        """
        Check if file is in project root.

        Args:
            filepath: Relative path to file

        Returns:
            True if file is in root directory
        """
        return "/" not in filepath

    def analyze(self) -> tuple[bool, list[dict]]:
        """
        Analyze documentation for point-in-time references.

        Returns:
            Tuple of (has_issues, warnings)
        """
        warnings = []
        changed_docs = self._get_changed_docs()

        if not changed_docs:
            return False, warnings

        for doc_path in changed_docs:
            full_path = self.repo_root / doc_path
            matches = self._scan_file_for_temporal_refs(full_path)

            if matches:
                is_root = self._is_root_file(doc_path)

                warning = {"file": doc_path, "is_root": is_root, "matches": matches}
                warnings.append(warning)

        has_issues = len(warnings) > 0
        return has_issues, warnings

    def generate_report(self) -> str:
        """
        Generate a human-readable report.

        Returns:
            Report string
        """
        has_issues, warnings = self.analyze()

        if not has_issues:
            return (
                "✅ Point-in-Time Documentation Check: PASSED\n"
                "No temporal references detected in documentation.\n"
            )

        report = [
            "⚠️  Point-in-Time Documentation Check: WARNINGS\n",
            f"Found {len(warnings)} file(s) with temporal references:\n",
            "",
        ]

        for warning in warnings:
            filepath = warning["file"]
            is_root = warning["is_root"]
            matches = warning["matches"]

            if is_root:
                report.append(f"❌ {filepath} (ROOT - Should not be committed)")
            else:
                report.append(f"⚠️  {filepath}")

            report.append(f"   Found {len(matches)} temporal reference(s):")

            # Show first 3 matches
            for line_num, line_content, indicator in matches[:3]:
                report.append(f'   Line {line_num}: "{indicator}" in: {line_content[:60]}')

            if len(matches) > 3:
                report.append(f"   ... and {len(matches) - 3} more")

            report.append("")

        report.extend(
            [
                "---",
                "Point-in-time documentation contains temporal references that will",
                "become outdated. Consider:",
                "",
                "1. For root directory files: Remove or move to docs/ subdirectory",
                "2. For transient status: Include in PR description instead",
                "3. For permanent docs: Remove temporal language, focus on timeless content",
                "",
                "Temporal indicators checked:",
            ]
        )

        indicators = self.config.get("point_in_time_indicators", [])
        for indicator in indicators[:10]:  # Show first 10
            report.append(f"  - {indicator}")

        if len(indicators) > 10:
            report.append(f"  ... and {len(indicators) - 10} more")

        report.extend(
            [
                "",
                "These warnings do not block CI, but should be addressed.",
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
    detector = PointInTimeDocsDetector(repo_root, config_path)

    # Generate and print report
    report = detector.generate_report()
    print(report)

    # Always exit 0 (warnings only, don't block CI)
    sys.exit(0)


if __name__ == "__main__":
    main()
