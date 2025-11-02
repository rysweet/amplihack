"""Markdown file validator using markdownlint."""

import json
import subprocess
import time
from pathlib import Path
from typing import List

from .base_validator import BaseValidator, Severity, ValidationIssue, ValidationResult


class MarkdownValidator(BaseValidator):
    """Validator for Markdown files using markdownlint-cli."""

    def name(self) -> str:
        """Return validator name."""
        return "markdown"

    def supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return [".md", ".markdown"]

    def is_available(self) -> bool:
        """Check if markdownlint is available."""
        try:
            result = subprocess.run(
                ["markdownlint", "--version"],
                capture_output=True,
                timeout=2,
                check=False,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate Markdown file using markdownlint.

        Args:
            file_path: Path to Markdown file

        Returns:
            ValidationResult with any issues found
        """
        start_time = time.time()

        if not self.is_available():
            return ValidationResult(
                validator=self.name(),
                file_path=str(file_path),
                passed=True,
                issues=[],
                duration_ms=0,
                skipped=True,
                skip_reason="markdownlint not available",
            )

        try:
            # Run markdownlint with JSON output
            result = subprocess.run(
                ["markdownlint", "--json", str(file_path)],
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Parse output
            issues = []
            if result.stdout:
                try:
                    # markdownlint outputs JSON as {filename: [issues]}
                    output = json.loads(result.stdout)
                    file_issues = output.get(str(file_path), [])

                    for item in file_issues:
                        issues.append(
                            ValidationIssue(
                                file_path=str(file_path),
                                line=item.get("lineNumber"),
                                column=item.get("column"),
                                severity=Severity.WARNING,  # markdownlint doesn't distinguish
                                code=",".join(item.get("ruleNames", [])),
                                message=item.get("ruleDescription", ""),
                                tool="markdownlint",
                            )
                        )
                except json.JSONDecodeError:
                    # Try parsing line-by-line format if JSON fails
                    for line in result.stdout.decode().splitlines():
                        if ":" in line:
                            parts = line.split(":", 3)
                            if len(parts) >= 4:
                                issues.append(
                                    ValidationIssue(
                                        file_path=str(file_path),
                                        line=int(parts[1]) if parts[1].isdigit() else None,
                                        column=int(parts[2]) if parts[2].isdigit() else None,
                                        severity=Severity.WARNING,
                                        code="MD",
                                        message=parts[3].strip(),
                                        tool="markdownlint",
                                    )
                                )

            return ValidationResult(
                validator=self.name(),
                file_path=str(file_path),
                passed=len(issues) == 0,
                issues=issues,
                duration_ms=duration_ms,
            )

        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return ValidationResult(
                validator=self.name(),
                file_path=str(file_path),
                passed=True,
                issues=[],
                duration_ms=duration_ms,
                skipped=True,
                skip_reason=f"Timeout after {self.timeout}s",
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ValidationResult(
                validator=self.name(),
                file_path=str(file_path),
                passed=True,
                issues=[],
                duration_ms=duration_ms,
                skipped=True,
                skip_reason=f"Error: {str(e)}",
            )
