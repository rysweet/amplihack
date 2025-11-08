#!/usr/bin/env python3
"""
Merge conflict checker - detects unresolved merge conflict markers.
"""

import re
import time

from .base_checker import BaseChecker
from ..violations import CheckResult


class MergeConflictChecker(BaseChecker):
    """Checks for unresolved merge conflict markers."""

    # Standard Git conflict markers
    CONFLICT_PATTERNS = [
        re.compile(r"^<{7} "),  # <<<<<<< HEAD
        re.compile(r"^={7}$"),  # =======
        re.compile(r"^>{7} "),  # >>>>>>> branch
    ]

    @property
    def name(self) -> str:
        return "merge-conflict"

    def check(self, files: list[str]) -> CheckResult:
        """Check files for merge conflict markers.

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
                    for pattern in self.CONFLICT_PATTERNS:
                        if pattern.match(line):
                            violations.append(
                                self.create_violation(
                                    file=filepath,
                                    line=line_num,
                                    message=f"Unresolved merge conflict marker found: {line.strip()}",
                                    remediation="Resolve the merge conflict and remove conflict markers",
                                    severity="error",
                                )
                            )
                            break  # Only report once per line

            except Exception as e:
                violations.append(
                    self.create_violation(
                        file=filepath,
                        message=f"Failed to check file: {str(e)}",
                        remediation="Ensure file is readable",
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
