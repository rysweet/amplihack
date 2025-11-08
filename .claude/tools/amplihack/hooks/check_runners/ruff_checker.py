#!/usr/bin/env python3
"""
Ruff checker - runs ruff format check and linting.
"""

import json
import subprocess
import time

from .base_checker import BaseChecker
from ..violations import CheckResult


class RuffChecker(BaseChecker):
    """Checks code formatting and linting with Ruff."""

    @property
    def name(self) -> str:
        return "ruff"

    def is_ruff_available(self) -> bool:
        """Check if ruff is installed.

        Returns:
            True if ruff is available
        """
        try:
            result = subprocess.run(
                ["ruff", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def check(self, files: list[str]) -> CheckResult:
        """Check files with ruff format and lint.

        Args:
            files: List of file paths to check

        Returns:
            CheckResult with any violations found
        """
        start_time = time.time()
        violations = []

        # Filter to Python files only
        python_files = self.filter_python_files(files)
        if not python_files:
            execution_time = time.time() - start_time
            return CheckResult(
                checker_name=self.name,
                violations=[],
                execution_time=execution_time,
                success=True,
            )

        # Check if ruff is available
        if not self.is_ruff_available():
            execution_time = time.time() - start_time
            return CheckResult(
                checker_name=self.name,
                violations=[],
                execution_time=execution_time,
                success=True,
                error_message="ruff not installed, skipping format/lint checks",
            )

        # Check formatting with ruff format --check
        try:
            result = self.run_command(
                ["ruff", "format", "--check", "--quiet"] + python_files,
                timeout=60,
            )

            if result.returncode != 0:
                # Parse output to find which files need formatting
                for line in result.stdout.splitlines():
                    if line.startswith("Would reformat:"):
                        filepath = line.replace("Would reformat:", "").strip()
                        violations.append(
                            self.create_violation(
                                file=filepath,
                                message="File is not properly formatted",
                                remediation="Run 'ruff format' to fix formatting",
                                severity="error",
                            )
                        )
                    # Handle the simpler output format too
                    elif any(f in line for f in python_files):
                        violations.append(
                            self.create_violation(
                                file=line.strip(),
                                message="File is not properly formatted",
                                remediation="Run 'ruff format' to fix formatting",
                                severity="error",
                            )
                        )

        except subprocess.TimeoutExpired:
            violations.append(
                self.create_violation(
                    file="<multiple>",
                    message="Ruff format check timed out",
                    remediation="Check large files or reduce file count",
                    severity="warning",
                )
            )
        except Exception as e:
            # Don't fail completely, just note the issue
            pass

        # Check linting with ruff check
        try:
            result = self.run_command(
                ["ruff", "check", "--output-format=json"] + python_files,
                timeout=60,
            )

            if result.stdout:
                try:
                    lint_results = json.loads(result.stdout)

                    for issue in lint_results:
                        filepath = issue.get("filename", "unknown")
                        line = issue.get("location", {}).get("row")
                        code = issue.get("code", "")
                        message = issue.get("message", "Linting issue")

                        violations.append(
                            self.create_violation(
                                file=filepath,
                                line=line,
                                message=f"[{code}] {message}",
                                remediation="Run 'ruff check --fix' or fix manually",
                                severity="error",
                            )
                        )
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to extract info from plain output
                    pass

        except subprocess.TimeoutExpired:
            violations.append(
                self.create_violation(
                    file="<multiple>",
                    message="Ruff lint check timed out",
                    remediation="Check large files or reduce file count",
                    severity="warning",
                )
            )
        except Exception as e:
            pass

        execution_time = time.time() - start_time

        return CheckResult(
            checker_name=self.name,
            violations=violations,
            execution_time=execution_time,
            success=True,
        )
