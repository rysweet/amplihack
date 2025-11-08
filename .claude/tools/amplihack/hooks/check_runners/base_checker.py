#!/usr/bin/env python3
"""
Base class for quality checkers.
All checkers extend this to provide consistent interface.
"""

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ..violations import CheckResult, Violation


class BaseChecker(ABC):
    """Abstract base class for quality checkers.

    All checkers must implement:
    - check(): Run the actual quality check
    - name property: Return checker name for identification
    """

    def __init__(self, project_root: Path):
        """Initialize checker with project root.

        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this checker.

        Returns:
            Checker name (e.g., "ruff", "pyright")
        """

    @abstractmethod
    def check(self, files: list[str]) -> CheckResult:
        """Run quality check on specified files.

        Args:
            files: List of file paths relative to project root

        Returns:
            CheckResult containing any violations found
        """

    def run_command(
        self,
        command: list[str],
        cwd: Optional[Path] = None,
        timeout: int = 60,
    ) -> subprocess.CompletedProcess:
        """Run a shell command with timeout and error handling.

        Args:
            command: Command and arguments to run
            cwd: Working directory (defaults to project_root)
            timeout: Timeout in seconds (default 60)

        Returns:
            CompletedProcess result

        Raises:
            subprocess.TimeoutExpired: If command times out
            subprocess.SubprocessError: For other command failures
        """
        if cwd is None:
            cwd = self.project_root

        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # Don't raise on non-zero exit
        )

    def is_python_file(self, filepath: str) -> bool:
        """Check if file is a Python file.

        Args:
            filepath: Path to check

        Returns:
            True if file is Python (.py, .pyi)
        """
        return filepath.endswith((".py", ".pyi"))

    def filter_python_files(self, files: list[str]) -> list[str]:
        """Filter list to only Python files.

        Args:
            files: List of file paths

        Returns:
            Filtered list containing only Python files
        """
        return [f for f in files if self.is_python_file(f)]

    def file_exists(self, filepath: str) -> bool:
        """Check if file exists relative to project root.

        Args:
            filepath: File path relative to project root

        Returns:
            True if file exists
        """
        full_path = self.project_root / filepath
        return full_path.exists()

    def read_file_lines(self, filepath: str) -> list[str]:
        """Read file lines for content-based checks.

        Args:
            filepath: File path relative to project root

        Returns:
            List of lines in the file

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = self.project_root / filepath
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.readlines()

    def create_violation(
        self,
        file: str,
        message: str,
        remediation: str,
        line: Optional[int] = None,
        severity: str = "error",
    ) -> Violation:
        """Helper to create a violation with checker info.

        This is a convenience method that subclasses can use to create
        violations without having to specify the checker name and type
        each time.

        Args:
            file: File path relative to project root
            message: Violation message
            remediation: How to fix the violation
            line: Line number (optional)
            severity: Severity level (default "error")

        Returns:
            Violation instance
        """
        # Import here to avoid circular dependency
        from ..violations import ViolationType

        # Map checker names to violation types
        type_map = {
            "ruff": ViolationType.LINTING,
            "pyright": ViolationType.TYPE_ERROR,
            "secrets": ViolationType.SECRET,
            "whitespace": ViolationType.WHITESPACE,
            "merge-conflict": ViolationType.MERGE_CONFLICT,
            "large-file": ViolationType.LARGE_FILE,
        }

        violation_type = type_map.get(self.name, ViolationType.LINTING)

        return Violation(
            file=file,
            line=line,
            type=violation_type,
            message=message,
            remediation=remediation,
            severity=severity,
            checker=self.name,
        )
