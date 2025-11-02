"""YAML file validator using yamllint."""

import subprocess
import time
from pathlib import Path
from typing import List

from .base_validator import BaseValidator, Severity, ValidationIssue, ValidationResult


class YAMLValidator(BaseValidator):
    """Validator for YAML files using yamllint."""

    def name(self) -> str:
        """Return validator name."""
        return "yaml"

    def supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return [".yaml", ".yml"]

    def is_available(self) -> bool:
        """Check if yamllint is available."""
        try:
            result = subprocess.run(
                ["yamllint", "--version"],
                capture_output=True,
                timeout=2,
                check=False,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate YAML file using yamllint.

        Args:
            file_path: Path to YAML file

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
                skip_reason="yamllint not available",
            )

        try:
            # Run yamllint with parsable format
            result = subprocess.run(
                ["yamllint", "-f", "parsable", str(file_path)],
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Parse output (format: file:line:col: [severity] message (code))
            issues = []
            if result.stdout:
                for line in result.stdout.decode().splitlines():
                    if ":" in line:
                        try:
                            parts = line.split(":", 3)
                            if len(parts) >= 4:
                                # Extract location and message
                                line_num = int(parts[1]) if parts[1].isdigit() else None
                                col_num = int(parts[2]) if parts[2].isdigit() else None
                                message_part = parts[3].strip()

                                # Parse severity and message
                                severity = Severity.WARNING
                                if "[error]" in message_part:
                                    severity = Severity.ERROR
                                    message_part = message_part.replace("[error]", "").strip()
                                elif "[warning]" in message_part:
                                    message_part = message_part.replace("[warning]", "").strip()

                                # Extract code from message (usually in parentheses)
                                code = "yamllint"
                                if "(" in message_part and ")" in message_part:
                                    code_start = message_part.rfind("(")
                                    code_end = message_part.rfind(")")
                                    code = message_part[code_start + 1 : code_end]
                                    message_part = message_part[:code_start].strip()

                                issues.append(
                                    ValidationIssue(
                                        file_path=str(file_path),
                                        line=line_num,
                                        column=col_num,
                                        severity=severity,
                                        code=code,
                                        message=message_part,
                                        tool="yamllint",
                                    )
                                )
                        except (ValueError, IndexError):
                            continue

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
