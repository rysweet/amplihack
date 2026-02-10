#!/usr/bin/env python3
"""
Root Directory File Validator

Validates that only approved files exist in the project root directory.
This ensures a clean, organized repository structure.

Exit Codes:
    0: All root files are approved
    1: Forbidden files found (warnings only, does not block CI)
"""

import fnmatch
import sys
from pathlib import Path

import yaml


class RootFileValidator:
    """Validates files in the project root directory."""

    def __init__(self, repo_root: Path, config_path: Path):
        """
        Initialize the validator.

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
            return yaml.safe_load(f)

    def _get_root_entries(self) -> tuple[set[str], set[str]]:
        """
        Get all files and directories in root.

        Returns:
            Tuple of (files, directories) in root
        """
        files = set()
        directories = set()

        try:
            for entry in self.repo_root.iterdir():
                # Skip .git directory
                if entry.name == ".git":
                    continue

                if entry.is_file():
                    files.add(entry.name)
                elif entry.is_dir():
                    directories.add(entry.name)
        except PermissionError as e:
            print(f"WARNING: Permission denied accessing root: {e}")

        return files, directories

    def _is_allowed(self, filename: str) -> bool:
        """
        Check if a file is allowed in root.

        Args:
            filename: Name of file to check

        Returns:
            True if file is allowed
        """
        allowed_patterns = self.config.get("allowed_patterns", [])

        for pattern in allowed_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True

        return False

    def _check_forbidden(self, filename: str) -> tuple[bool, str, str]:
        """
        Check if a file matches forbidden patterns.

        Args:
            filename: Name of file to check

        Returns:
            Tuple of (is_forbidden, message, suggested_location)
        """
        forbidden_patterns = self.config.get("forbidden_patterns", [])

        for item in forbidden_patterns:
            pattern = item.get("pattern", "")
            if fnmatch.fnmatch(filename, pattern):
                message = item.get("message", "File should not be in root")
                suggested_location = item.get("suggested_location", "appropriate subdirectory")
                return True, message, suggested_location

        return False, "", ""

    def _is_directory_allowed(self, dirname: str) -> bool:
        """
        Check if a directory is allowed in root.

        Args:
            dirname: Name of directory to check

        Returns:
            True if directory is allowed
        """
        allowed_directories = self.config.get("allowed_directories", [])
        return dirname in allowed_directories

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate root directory contents.

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []
        files, directories = self._get_root_entries()

        # Check files
        for filename in sorted(files):
            # First check if explicitly forbidden
            is_forbidden, message, suggested_location = self._check_forbidden(filename)

            if is_forbidden:
                warnings.append(
                    f"❌ {filename}\n   Reason: {message}\n   Suggested: {suggested_location}"
                )
                continue

            # Then check if allowed
            if not self._is_allowed(filename):
                warnings.append(
                    f"⚠️  {filename}\n"
                    f"   Reason: Not in allowlist\n"
                    f"   Action: Review if this belongs in root"
                )

        # Check directories
        for dirname in sorted(directories):
            if not self._is_directory_allowed(dirname):
                warnings.append(
                    f"⚠️  {dirname}/\n"
                    f"   Reason: Directory not in allowlist\n"
                    f"   Action: Review if this belongs in root"
                )

        is_valid = len(warnings) == 0
        return is_valid, warnings

    def generate_report(self) -> str:
        """
        Generate a human-readable report.

        Returns:
            Report string
        """
        is_valid, warnings = self.validate()

        if is_valid:
            return "✅ Root Directory Check: PASSED\nAll root files and directories are approved.\n"

        report = [
            "⚠️  Root Directory Check: WARNINGS\n",
            f"Found {len(warnings)} issue(s) in root directory:\n",
            "",
        ]

        for warning in warnings:
            report.append(warning)
            report.append("")

        report.extend(
            [
                "---",
                "These warnings do not block CI, but should be addressed.",
                "Root directory should contain only essential project files.",
                "",
                "For more information, see:",
                "- .github/root-hygiene-config.yml",
                "- .claude/agents/amplihack/specialized/cleanup.md (Section 6)",
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

    # Create validator
    validator = RootFileValidator(repo_root, config_path)

    # Generate and print report
    report = validator.generate_report()
    print(report)

    # Exit with warning status if issues found (but don't fail CI)
    is_valid, warnings = validator.validate()
    if not is_valid:
        print(f"\n⚠️  Found {len(warnings)} warning(s)")
        print("This check warns but does not block CI.")
        # Exit 0 to not block CI, but print warnings
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
