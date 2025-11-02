"""JSON file validator using Python's json module."""

import json
import time
from pathlib import Path
from typing import List

from .base_validator import BaseValidator, Severity, ValidationIssue, ValidationResult


class JSONValidator(BaseValidator):
    """Validator for JSON files using Python's built-in json module."""

    def name(self) -> str:
        """Return validator name."""
        return "json"

    def supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return [".json"]

    def is_available(self) -> bool:
        """Check if JSON validation is available (always True)."""
        return True

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            ValidationResult with any issues found
        """
        start_time = time.time()
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                json.loads(content)  # Will raise JSONDecodeError if invalid

            duration_ms = int((time.time() - start_time) * 1000)

            return ValidationResult(
                validator=self.name(),
                file_path=str(file_path),
                passed=True,
                issues=[],
                duration_ms=duration_ms,
            )

        except json.JSONDecodeError as e:
            duration_ms = int((time.time() - start_time) * 1000)

            issues.append(
                ValidationIssue(
                    file_path=str(file_path),
                    line=e.lineno,
                    column=e.colno,
                    severity=Severity.ERROR,
                    code="JSONDecodeError",
                    message=e.msg,
                    tool="json",
                )
            )

            return ValidationResult(
                validator=self.name(),
                file_path=str(file_path),
                passed=False,
                issues=issues,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            issues.append(
                ValidationIssue(
                    file_path=str(file_path),
                    line=None,
                    column=None,
                    severity=Severity.ERROR,
                    code="ValidationError",
                    message=str(e),
                    tool="json",
                )
            )

            return ValidationResult(
                validator=self.name(),
                file_path=str(file_path),
                passed=False,
                issues=issues,
                duration_ms=duration_ms,
            )
