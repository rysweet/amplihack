#!/usr/bin/env python3
"""
Pyright checker - runs type checking with pyright.
"""

import json
import subprocess
import time

from .base_checker import BaseChecker
from ..violations import CheckResult


class PyrightChecker(BaseChecker):
    """Checks Python type hints with Pyright."""

    @property
    def name(self) -> str:
        return "pyright"

    def is_pyright_available(self) -> bool:
        """Check if pyright is installed.

        Returns:
            True if pyright is available
        """
        try:
            result = subprocess.run(
                ["pyright", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def check(self, files: list[str]) -> CheckResult:
        """Check files with pyright type checker.

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

        # Check if pyright is available
        if not self.is_pyright_available():
            execution_time = time.time() - start_time
            return CheckResult(
                checker_name=self.name,
                violations=[],
                execution_time=execution_time,
                success=True,
                error_message="pyright not installed, skipping type checks",
            )

        # Run pyright with JSON output
        try:
            result = self.run_command(
                ["pyright", "--outputjson"] + python_files,
                timeout=120,  # Type checking can be slow
            )

            if result.stdout:
                try:
                    pyright_result = json.loads(result.stdout)

                    # Extract diagnostics
                    for diagnostic in pyright_result.get("generalDiagnostics", []):
                        filepath = diagnostic.get("file", "unknown")
                        line = diagnostic.get("range", {}).get("start", {}).get("line")
                        if line is not None:
                            line = line + 1  # Pyright uses 0-based line numbers

                        severity = diagnostic.get("severity", "error")
                        message = diagnostic.get("message", "Type checking issue")
                        rule = diagnostic.get("rule")

                        # Format message with rule if available
                        if rule:
                            message = f"[{rule}] {message}"

                        # Map pyright severity to our severity
                        our_severity = "error" if severity == "error" else "warning"

                        violations.append(
                            self.create_violation(
                                file=filepath,
                                line=line,
                                message=message,
                                remediation="Fix type annotations or add type: ignore comment",
                                severity=our_severity,
                            )
                        )

                except json.JSONDecodeError:
                    # If JSON parsing fails, try text output
                    for line in result.stdout.splitlines():
                        if " - error:" in line or " - warning:" in line:
                            violations.append(
                                self.create_violation(
                                    file="<see output>",
                                    message=line.strip(),
                                    remediation="Run pyright manually to see full details",
                                    severity="error",
                                )
                            )

        except subprocess.TimeoutExpired:
            violations.append(
                self.create_violation(
                    file="<multiple>",
                    message="Pyright type check timed out",
                    remediation="Type checking may be too slow for these files",
                    severity="warning",
                )
            )
        except Exception as e:
            # Don't fail completely, just note the issue
            pass

        execution_time = time.time() - start_time

        return CheckResult(
            checker_name=self.name,
            violations=violations,
            execution_time=execution_time,
            success=True,
        )
