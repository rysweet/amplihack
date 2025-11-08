#!/usr/bin/env python3
"""
Whitespace checker - detects trailing whitespace in files.
"""

import time

from .base_checker import BaseChecker
from ..violations import CheckResult


class WhitespaceChecker(BaseChecker):
    """Checks for trailing whitespace in files."""

    @property
    def name(self) -> str:
        return "whitespace"

    def check(self, files: list[str]) -> CheckResult:
        """Check files for trailing whitespace.

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
                lines = self.read_file_lines(filepath)

                for line_num, line in enumerate(lines, start=1):
                    # Check for trailing whitespace (but not empty lines)
                    if line.rstrip() != line.rstrip("\n\r"):
                        violations.append(
                            self.create_violation(
                                file=filepath,
                                line=line_num,
                                message=f"Line has trailing whitespace",
                                remediation="Run 'ruff format' or manually remove trailing spaces",
                                severity="warning",
                            )
                        )

            except Exception as e:
                # If we can't read a file, create a violation for it
                violations.append(
                    self.create_violation(
                        file=filepath,
                        message=f"Failed to check file: {str(e)}",
                        remediation="Ensure file is readable and properly encoded",
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
