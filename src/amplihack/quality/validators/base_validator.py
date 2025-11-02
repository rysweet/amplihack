"""Base validator abstract class for quality checks."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional


class Severity(Enum):
    """Issue severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue found in a file."""

    file_path: str
    line: Optional[int]
    column: Optional[int]
    severity: Severity
    code: str
    message: str
    tool: str

    def __str__(self) -> str:
        """Format issue as string."""
        location = f"{self.file_path}"
        if self.line:
            location += f":{self.line}"
        if self.column:
            location += f":{self.column}"
        return f"{location} [{self.severity.value}] {self.code}: {self.message}"


@dataclass
class ValidationResult:
    """Result of validation."""

    validator: str
    file_path: str
    passed: bool
    issues: List[ValidationIssue]
    duration_ms: int
    skipped: bool = False
    skip_reason: Optional[str] = None

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for issue in self.issues if issue.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for issue in self.issues if issue.severity == Severity.WARNING)


class BaseValidator(ABC):
    """Abstract base class for file validators."""

    def __init__(self, timeout: int = 5):
        """Initialize validator.

        Args:
            timeout: Maximum execution time in seconds (default: 5)
        """
        self.timeout = timeout

    @abstractmethod
    def name(self) -> str:
        """Return validator name.

        Returns:
            Name of the validator
        """
        pass

    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions.

        Returns:
            List of file extensions (e.g., ['.py', '.pyi'])
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if validator tool is available.

        Returns:
            True if tool is installed and available
        """
        pass

    @abstractmethod
    def validate(self, file_path: Path) -> ValidationResult:
        """Validate a file.

        Args:
            file_path: Path to file to validate

        Returns:
            ValidationResult with issues found
        """
        pass

    def can_validate(self, file_path: Path) -> bool:
        """Check if this validator can validate the given file.

        Args:
            file_path: Path to file

        Returns:
            True if file extension is supported
        """
        return file_path.suffix in self.supported_extensions()
