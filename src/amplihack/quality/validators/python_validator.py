"""Python file validator using Ruff."""

import json
import subprocess
import time
from pathlib import Path
from typing import List

from .base_validator import BaseValidator, Severity, ValidationIssue, ValidationResult


class PythonValidator(BaseValidator):
    """Validator for Python files using Ruff."""

    def name(self) -> str:
        """Return validator name."""
        return "python"

    def supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return [".py", ".pyi"]

    def is_available(self) -> bool:
        """Check if Ruff is available."""
        try:
            result = subprocess.run(
                ["ruff", "--version"],
                capture_output=True,
                timeout=2,
                check=False,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate Python file using Ruff.

        Args:
            file_path: Path to Python file

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
                skip_reason="Ruff not available",
            )

        try:
            # Run ruff with JSON output for structured parsing
            result = subprocess.run(
                ["ruff", "check", "--output-format=json", str(file_path)],
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Parse JSON output
            issues = []
            if result.stdout:
                try:
                    ruff_output = json.loads(result.stdout)
                    for item in ruff_output:
                        # Map Ruff severity to our severity
                        severity = Severity.ERROR
                        if item.get("type") == "Warning":
                            severity = Severity.WARNING

                        issues.append(
                            ValidationIssue(
                                file_path=str(file_path),
                                line=item.get("location", {}).get("row"),
                                column=item.get("location", {}).get("column"),
                                severity=severity,
                                code=item.get("code", ""),
                                message=item.get("message", ""),
                                tool="ruff",
                            )
                        )
                except json.JSONDecodeError:
                    pass

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
