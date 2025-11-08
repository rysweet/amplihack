#!/usr/bin/env python3
"""
Data structures for quality check violations.
Provides common violation representation across all checkers.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ViolationType(Enum):
    """Types of quality violations that can be detected."""

    FORMATTING = "formatting"
    LINTING = "linting"
    TYPE_ERROR = "type_error"
    SECRET = "secret"
    WHITESPACE = "whitespace"
    MERGE_CONFLICT = "merge_conflict"
    LARGE_FILE = "large_file"


@dataclass
class Violation:
    """Represents a single quality violation found in code.

    Attributes:
        file: Path to the file containing the violation (relative to repo root)
        line: Line number where violation occurs (None for file-level violations)
        type: Type of violation from ViolationType enum
        message: Human-readable description of the violation
        remediation: Suggested fix or action to resolve the violation
        severity: Severity level (error, warning, info)
        checker: Name of the checker that detected this violation
    """

    file: str
    type: ViolationType
    message: str
    remediation: str
    checker: str
    line: Optional[int] = None
    severity: str = "error"

    def __str__(self) -> str:
        """Format violation for human-readable output."""
        location = f"{self.file}"
        if self.line is not None:
            location += f":{self.line}"

        return f"""
{self.severity.upper()}: {self.type.value}
  Location: {location}
  Checker: {self.checker}
  Message: {self.message}
  Fix: {self.remediation}
"""

    def to_dict(self) -> dict:
        """Convert violation to dictionary for JSON serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "type": self.type.value,
            "message": self.message,
            "remediation": self.remediation,
            "severity": self.severity,
            "checker": self.checker,
        }


@dataclass
class CheckResult:
    """Result from running a quality checker.

    Attributes:
        checker_name: Name of the checker that ran
        violations: List of violations found (empty if no violations)
        execution_time: Time taken to run the checker in seconds
        success: Whether the checker ran successfully (False if checker crashed)
        error_message: Error message if checker failed to run
    """

    checker_name: str
    violations: list[Violation]
    execution_time: float
    success: bool = True
    error_message: Optional[str] = None

    @property
    def has_violations(self) -> bool:
        """Check if this result contains any violations."""
        return len(self.violations) > 0

    def to_dict(self) -> dict:
        """Convert result to dictionary for JSON serialization."""
        return {
            "checker_name": self.checker_name,
            "violations": [v.to_dict() for v in self.violations],
            "execution_time": self.execution_time,
            "success": self.success,
            "error_message": self.error_message,
            "violation_count": len(self.violations),
        }
