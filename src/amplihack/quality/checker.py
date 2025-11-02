"""Quality checker orchestrator."""

import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Type

from .config import QualityConfig
from .validators import (
    BaseValidator,
    JSONValidator,
    MarkdownValidator,
    PythonValidator,
    ShellValidator,
    ValidationResult,
    YAMLValidator,
)


class QualityChecker:
    """Orchestrator for running quality checks on files."""

    # Map validator names to classes
    VALIDATOR_MAP: Dict[str, Type[BaseValidator]] = {
        "python": PythonValidator,
        "shell": ShellValidator,
        "markdown": MarkdownValidator,
        "yaml": YAMLValidator,
        "json": JSONValidator,
    }

    def __init__(self, config: Optional[QualityConfig] = None):
        """Initialize quality checker.

        Args:
            config: Quality configuration (default: load from pyproject.toml)
        """
        self.config = config or QualityConfig.from_pyproject()
        self._validators: List[BaseValidator] = []
        self._initialize_validators()

    def _initialize_validators(self):
        """Initialize validators based on configuration."""
        timeout = self.config.timeout

        for validator_name in self.config.validators:
            validator_class = self.VALIDATOR_MAP.get(validator_name)
            if validator_class:
                validator = validator_class(timeout=timeout)
                self._validators.append(validator)

    def is_excluded(self, file_path: Path) -> bool:
        """Check if file should be excluded from checks.

        Args:
            file_path: Path to file

        Returns:
            True if file matches any exclude pattern
        """
        file_str = str(file_path)

        for pattern in self.config.exclude:
            # Use both full path and individual parts for matching
            if fnmatch.fnmatch(file_str, pattern):
                return True
            # Also check if any part of the path matches
            for part in file_path.parts:
                if fnmatch.fnmatch(part, pattern.strip("*/")):
                    return True

        return False

    def find_validator(self, file_path: Path) -> Optional[BaseValidator]:
        """Find appropriate validator for file.

        Args:
            file_path: Path to file

        Returns:
            Validator instance or None if no validator supports this file type
        """
        for validator in self._validators:
            if validator.can_validate(file_path):
                return validator

        return None

    def check_file(self, file_path: Path) -> Optional[ValidationResult]:
        """Run quality checks on a single file.

        Args:
            file_path: Path to file to check

        Returns:
            ValidationResult or None if file should be skipped
        """
        if not self.config.enabled:
            return None

        # Convert to Path if string
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Skip if file doesn't exist
        if not file_path.exists():
            return None

        # Skip if excluded
        if self.is_excluded(file_path):
            return None

        # Find validator
        validator = self.find_validator(file_path)
        if not validator:
            return None

        # Skip if validator not available
        if not validator.is_available():
            return ValidationResult(
                validator=validator.name(),
                file_path=str(file_path),
                passed=True,
                issues=[],
                duration_ms=0,
                skipped=True,
                skip_reason=f"{validator.name()} validator not available",
            )

        # Run validation
        return validator.validate(file_path)

    def check_files(self, file_paths: List[Path]) -> List[ValidationResult]:
        """Run quality checks on multiple files.

        Args:
            file_paths: List of file paths to check

        Returns:
            List of ValidationResults (skips excluded files)
        """
        results = []

        for file_path in file_paths:
            result = self.check_file(file_path)
            if result:
                results.append(result)

        return results

    def get_summary(self, results: List[ValidationResult]) -> Dict[str, any]:
        """Generate summary of validation results.

        Args:
            results: List of ValidationResults

        Returns:
            Summary dictionary with counts and statistics
        """
        total_files = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed and not r.skipped)
        skipped = sum(1 for r in results if r.skipped)

        total_errors = sum(r.error_count for r in results)
        total_warnings = sum(r.warning_count for r in results)
        total_duration_ms = sum(r.duration_ms for r in results)

        return {
            "total_files": total_files,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "total_duration_ms": total_duration_ms,
            "average_duration_ms": total_duration_ms // total_files if total_files > 0 else 0,
        }
