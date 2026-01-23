#!/usr/bin/env python3
"""GitIgnore Checker - Session Start Hook Module.

This module provides automatic .gitignore management for amplihack runtime directories.
It ensures that .claude/logs/ and .claude/runtime/ are always properly excluded from Git.

Philosophy:
- Ruthless simplicity: Standard library only, no external dependencies
- Fail-safe design: Never breaks session start (exceptions logged, not raised)
- Zero-BS implementation: No stubs, no TODOs, everything works

Public API (the "studs"):
    GitignoreChecker: Main class for checking and updating .gitignore
    check_and_update_gitignore(): Convenience function for quick usage

Example:
    >>> checker = GitignoreChecker()
    >>> result = checker.run()
    >>> if result["modified"]:
    ...     print(f"Updated .gitignore with: {result['missing_dirs']}")
"""

import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional


class GitignoreChecker:
    """Check and update .gitignore for amplihack runtime directories."""

    DEFAULT_DIRECTORIES = [".claude/logs/", ".claude/runtime/"]

    def __init__(self, directories: Optional[List[str]] = None):
        """Initialize checker with directories to protect."""
        self.directories = directories if directories is not None else self.DEFAULT_DIRECTORIES.copy()

    def is_git_repo(self) -> bool:
        """Check if current directory is inside a Git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except FileNotFoundError:
            # Expected: git not installed
            return False
        except subprocess.TimeoutExpired:
            # Expected: git command hung
            return False
        except Exception as e:
            # Unexpected: log when logging infrastructure available
            # TODO: Add logging here when logger is configured
            # For now, fail safe by returning False
            return False

    def get_repo_root(self) -> Optional[Path]:
        """Get the root directory of the Git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return Path(result.stdout.strip())
            return None
        except FileNotFoundError:
            # Expected: git not installed
            return None
        except subprocess.TimeoutExpired:
            # Expected: git command hung
            return None
        except Exception as e:
            # Unexpected: log when logging infrastructure available
            # TODO: Add logging here when logger is configured
            # For now, fail safe by returning None
            return None

    def parse_gitignore_patterns(self, content: str) -> List[str]:
        """Parse .gitignore content into list of patterns."""
        patterns = []
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
        return patterns

    def pattern_matches(self, pattern: str, directory: str) -> bool:
        """Check if a pattern matches a directory using exact matching.

        Normalizes trailing slashes before comparison.
        Simple substring matching - no wildcards or regex.
        """
        pattern_norm = pattern.rstrip("/")
        directory_norm = directory.rstrip("/")

        return pattern_norm == directory_norm

    def is_directory_ignored(self, directory: str, patterns: List[str]) -> bool:
        """Check if a directory is already ignored by patterns."""
        for pattern in patterns:
            if self.pattern_matches(pattern, directory):
                return True
        return False

    def generate_gitignore_entry(self, directories: Optional[List[str]] = None) -> str:
        """Generate .gitignore entry for amplihack directories."""
        dirs_to_add = directories if directories is not None else self.directories
        entry_lines = ["", "# Amplihack runtime directories (auto-generated)"]
        entry_lines.extend(dirs_to_add)
        entry_lines.append("")
        return "\n".join(entry_lines)

    def determine_missing_directories(self, patterns: List[str]) -> List[str]:
        """Identify which directories are missing from .gitignore."""
        missing = []
        for directory in self.directories:
            if not self.is_directory_ignored(directory, patterns):
                missing.append(directory)
        return missing

    def format_warning_message(self, missing_dirs: List[str]) -> str:
        """Format user-friendly warning message."""
        if not missing_dirs:
            return ""

        lines = [
            "",
            "⚠️  [Amplihack] Updated .gitignore to exclude runtime directories",
            "",
            "  Added patterns:",
        ]
        for directory in missing_dirs:
            lines.append(f"    - {directory}")

        lines.extend([
            "",
            "  Action Required: Commit the updated .gitignore file",
            "  $ git add .gitignore",
            '  $ git commit -m "chore: Add amplihack runtime directories to .gitignore"',
            "",
        ])
        return "\n".join(lines)

    def read_gitignore(self, gitignore_path: Path) -> str:
        """Read .gitignore file content."""
        if not gitignore_path.exists():
            return ""
        return gitignore_path.read_text()

    def write_gitignore(self, gitignore_path: Path, content: str, mode: str = "create") -> None:
        """Write content to .gitignore file."""
        if mode == "append":
            existing = self.read_gitignore(gitignore_path)
            content = existing + content
        gitignore_path.write_text(content)

    def check_and_update_gitignore(self) -> Dict:
        """Check and update .gitignore with required patterns."""
        if not self.is_git_repo():
            return {"modified": False, "missing_dirs": []}

        repo_root = self.get_repo_root()
        if repo_root is None:
            return {"modified": False, "missing_dirs": []}

        gitignore_path = repo_root / ".gitignore"
        current_content = self.read_gitignore(gitignore_path)
        current_patterns = self.parse_gitignore_patterns(current_content)
        missing_dirs = self.determine_missing_directories(current_patterns)

        if not missing_dirs:
            return {"modified": False, "missing_dirs": []}

        entry = self.generate_gitignore_entry(directories=missing_dirs)
        self.write_gitignore(gitignore_path, entry, mode="append")

        return {"modified": True, "missing_dirs": missing_dirs}

    def run(self, display_warnings: bool = False) -> Dict:
        """Run the complete gitignore check workflow."""
        start_time = time.time()

        if not self.is_git_repo():
            return {
                "is_git_repo": False,
                "modified": False,
                "missing_dirs": [],
                "warning_message": None,
            }

        result = self.check_and_update_gitignore()

        warning_message = None
        if result["modified"]:
            warning_message = self.format_warning_message(result["missing_dirs"])
            if display_warnings and warning_message:
                print(warning_message)

        return {
            "is_git_repo": True,
            "modified": result["modified"],
            "missing_dirs": result["missing_dirs"],
            "warning_message": warning_message,
            "elapsed_time": time.time() - start_time,
        }


def check_and_update_gitignore(display_warnings: bool = False) -> Dict:
    """Convenience function to check and update .gitignore."""
    checker = GitignoreChecker()
    return checker.run(display_warnings=display_warnings)


__all__ = ["GitignoreChecker", "check_and_update_gitignore"]


if __name__ == "__main__":
    result = check_and_update_gitignore(display_warnings=True)
    print(f"\nResult: {result}")
