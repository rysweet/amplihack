"""Shell script validator using ShellCheck."""

import json
import subprocess
import time
from pathlib import Path
from typing import List

from .base_validator import BaseValidator, Severity, ValidationIssue, ValidationResult


class ShellValidator(BaseValidator):
    """Validator for shell scripts using ShellCheck."""

    def name(self) -> str:
        """Return validator name."""
        return "shell"

    def supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return [".sh", ".bash"]

    def is_available(self) -> bool:
        """Check if ShellCheck is available."""
        try:
            result = subprocess.run(
                ["shellcheck", "--version"],
                capture_output=True,
                timeout=2,
                check=False,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate shell script using ShellCheck.

        Args:
            file_path: Path to shell script

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
                skip_reason="ShellCheck not available",
            )

        try:
            # Run shellcheck with JSON output
            result = subprocess.run(
                ["shellcheck", "--format=json", str(file_path)],
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Parse JSON output
            issues = []
            if result.stdout:
                try:
                    shellcheck_output = json.loads(result.stdout)
                    for item in shellcheck_output:
                        # Map ShellCheck level to our severity
                        level = item.get("level", "info")
                        if level == "error":
                            severity = Severity.ERROR
                        elif level == "warning":
                            severity = Severity.WARNING
                        else:
                            severity = Severity.INFO

                        issues.append(
                            ValidationIssue(
                                file_path=str(file_path),
                                line=item.get("line"),
                                column=item.get("column"),
                                severity=severity,
                                code=f"SC{item.get('code', 0)}",
                                message=item.get("message", ""),
                                tool="shellcheck",
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
