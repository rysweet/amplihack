"""Tests for quality checker."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.quality import QualityChecker, QualityConfig, ValidationResult
from amplihack.quality.validators import PythonValidator, Severity, ValidationIssue


class TestQualityChecker:
    """Tests for QualityChecker."""

    def test_initialization_default_config(self):
        """Test initialization with default config."""
        checker = QualityChecker()
        assert checker.config is not None
        assert len(checker._validators) > 0

    def test_initialization_custom_config(self):
        """Test initialization with custom config."""
        config = QualityConfig(validators=["python"])
        checker = QualityChecker(config)
        assert len(checker._validators) == 1

    def test_is_excluded_matches_pattern(self):
        """Test is_excluded with matching pattern."""
        checker = QualityChecker()
        assert checker.is_excluded(Path("__pycache__/test.py"))
        assert checker.is_excluded(Path(".venv/lib/test.py"))

    def test_is_excluded_no_match(self):
        """Test is_excluded with non-matching pattern."""
        checker = QualityChecker()
        assert not checker.is_excluded(Path("src/test.py"))

    def test_find_validator_python(self):
        """Test finding validator for Python file."""
        checker = QualityChecker()
        validator = checker.find_validator(Path("test.py"))
        assert validator is not None
        assert validator.name() == "python"

    def test_find_validator_json(self):
        """Test finding validator for JSON file."""
        checker = QualityChecker()
        validator = checker.find_validator(Path("test.json"))
        assert validator is not None
        assert validator.name() == "json"

    def test_find_validator_unsupported(self):
        """Test finding validator for unsupported file."""
        checker = QualityChecker()
        validator = checker.find_validator(Path("test.txt"))
        assert validator is None

    def test_check_file_disabled(self):
        """Test check_file when quality checks disabled."""
        config = QualityConfig(enabled=False)
        checker = QualityChecker(config)
        result = checker.check_file(Path("test.py"))
        assert result is None

    def test_check_file_excluded(self):
        """Test check_file for excluded file."""
        checker = QualityChecker()
        result = checker.check_file(Path("__pycache__/test.py"))
        assert result is None

    def test_check_file_nonexistent(self):
        """Test check_file for nonexistent file."""
        checker = QualityChecker()
        result = checker.check_file(Path("nonexistent.py"))
        assert result is None

    def test_check_file_valid_json(self, tmp_path):
        """Test check_file with valid JSON."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')

        checker = QualityChecker()
        result = checker.check_file(json_file)

        assert result is not None
        assert result.passed is True

    def test_check_file_invalid_json(self, tmp_path):
        """Test check_file with invalid JSON."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": invalid}')

        checker = QualityChecker()
        result = checker.check_file(json_file)

        assert result is not None
        assert result.passed is False
        assert len(result.issues) > 0

    def test_check_files_multiple(self, tmp_path):
        """Test check_files with multiple files."""
        json1 = tmp_path / "test1.json"
        json1.write_text('{"key": "value"}')
        json2 = tmp_path / "test2.json"
        json2.write_text('{"key": "value2"}')

        checker = QualityChecker()
        results = checker.check_files([json1, json2])

        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_get_summary_all_passed(self):
        """Test get_summary with all passed."""
        results = [
            ValidationResult(
                validator="python",
                file_path="test.py",
                passed=True,
                issues=[],
                duration_ms=10,
            )
        ]

        checker = QualityChecker()
        summary = checker.get_summary(results)

        assert summary["total_files"] == 1
        assert summary["passed"] == 1
        assert summary["failed"] == 0
        assert summary["total_errors"] == 0

    def test_get_summary_with_failures(self):
        """Test get_summary with failures."""
        results = [
            ValidationResult(
                validator="python",
                file_path="test.py",
                passed=False,
                issues=[
                    ValidationIssue(
                        file_path="test.py",
                        line=1,
                        column=1,
                        severity=Severity.ERROR,
                        code="E001",
                        message="Test error",
                        tool="test",
                    )
                ],
                duration_ms=10,
            )
        ]

        checker = QualityChecker()
        summary = checker.get_summary(results)

        assert summary["total_files"] == 1
        assert summary["passed"] == 0
        assert summary["failed"] == 1
        assert summary["total_errors"] == 1

    def test_get_summary_with_skipped(self):
        """Test get_summary with skipped files."""
        results = [
            ValidationResult(
                validator="python",
                file_path="test.py",
                passed=True,
                issues=[],
                duration_ms=0,
                skipped=True,
                skip_reason="Tool not available",
            )
        ]

        checker = QualityChecker()
        summary = checker.get_summary(results)

        assert summary["total_files"] == 1
        assert summary["skipped"] == 1
