#!/usr/bin/env python3
"""
Large file checker - detects files exceeding size limits.
"""

import time

from .base_checker import BaseChecker
from ..violations import CheckResult


class LargeFileChecker(BaseChecker):
    """Checks for files exceeding size limits."""

    # Default size limits (in bytes)
    DEFAULT_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    WARNING_SIZE = 5 * 1024 * 1024  # 5MB

    def __init__(self, project_root, max_size: int = DEFAULT_MAX_SIZE):
        """Initialize with custom size limit if needed.

        Args:
            project_root: Project root path
            max_size: Maximum file size in bytes (default 10MB)
        """
        super().__init__(project_root)
        self.max_size = max_size

    @property
    def name(self) -> str:
        return "large-file"

    def check(self, files: list[str]) -> CheckResult:
        """Check files for excessive size.

        Args:
            files: List of file paths to check

        Returns:
            CheckResult with any violations found
        """
        start_time = time.time()
        violations = []

        for filepath in files:
            if not self.file_exists(filepath):
                continue

            try:
                full_path = self.project_root / filepath
                file_size = full_path.stat().st_size

                if file_size > self.max_size:
                    size_mb = file_size / (1024 * 1024)
                    max_mb = self.max_size / (1024 * 1024)
                    violations.append(
                        self.create_violation(
                            file=filepath,
                            message=f"File is too large: {size_mb:.2f}MB (max: {max_mb:.0f}MB)",
                            remediation="Consider using Git LFS for large files or reduce file size",
                            severity="error",
                        )
                    )
                elif file_size > self.WARNING_SIZE:
                    size_mb = file_size / (1024 * 1024)
                    violations.append(
                        self.create_violation(
                            file=filepath,
                            message=f"File is large: {size_mb:.2f}MB",
                            remediation="Consider if this file should be in version control",
                            severity="warning",
                        )
                    )

            except Exception as e:
                violations.append(
                    self.create_violation(
                        file=filepath,
                        message=f"Failed to check file size: {str(e)}",
                        remediation="Ensure file exists and is accessible",
                        severity="warning",
                    )
                )

        execution_time = time.time() - start_time

        return CheckResult(
            checker_name=self.name,
            violations=violations,
            execution_time=execution_time,
            success=True,
        )
