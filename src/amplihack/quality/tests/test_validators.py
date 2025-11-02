"""Tests for quality validators."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.quality.validators import (
    JSONValidator,
    MarkdownValidator,
    PythonValidator,
    Severity,
    ShellValidator,
    YAMLValidator,
)


class TestPythonValidator:
    """Tests for PythonValidator."""

    def test_name(self):
        """Test validator name."""
        validator = PythonValidator()
        assert validator.name() == "python"

    def test_supported_extensions(self):
        """Test supported extensions."""
        validator = PythonValidator()
        assert ".py" in validator.supported_extensions()
        assert ".pyi" in validator.supported_extensions()

    def test_can_validate_python_file(self):
        """Test can_validate for Python file."""
        validator = PythonValidator()
        assert validator.can_validate(Path("test.py"))
        assert validator.can_validate(Path("test.pyi"))
        assert not validator.can_validate(Path("test.txt"))

    @patch("subprocess.run")
    def test_is_available_true(self, mock_run):
        """Test is_available when ruff is installed."""
        mock_run.return_value = MagicMock(returncode=0)
        validator = PythonValidator()
        assert validator.is_available() is True

    @patch("subprocess.run")
    def test_is_available_false(self, mock_run):
        """Test is_available when ruff is not installed."""
        mock_run.side_effect = FileNotFoundError()
        validator = PythonValidator()
        assert validator.is_available() is False

    @patch("subprocess.run")
    def test_validate_no_issues(self, mock_run):
        """Test validation with no issues."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"[]"
        )
        validator = PythonValidator()
        result = validator.validate(Path("test.py"))

        assert result.passed is True
        assert len(result.issues) == 0

    @patch("subprocess.run")
    def test_validate_with_issues(self, mock_run):
        """Test validation with issues."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=b'[{"code": "F401", "message": "Unused import", "location": {"row": 1, "column": 1}, "type": "Error"}]'
        )
        validator = PythonValidator()
        result = validator.validate(Path("test.py"))

        assert result.passed is False
        assert len(result.issues) == 1
        assert result.issues[0].code == "F401"
        assert result.issues[0].severity == Severity.ERROR


class TestShellValidator:
    """Tests for ShellValidator."""

    def test_name(self):
        """Test validator name."""
        validator = ShellValidator()
        assert validator.name() == "shell"

    def test_supported_extensions(self):
        """Test supported extensions."""
        validator = ShellValidator()
        assert ".sh" in validator.supported_extensions()
        assert ".bash" in validator.supported_extensions()


class TestMarkdownValidator:
    """Tests for MarkdownValidator."""

    def test_name(self):
        """Test validator name."""
        validator = MarkdownValidator()
        assert validator.name() == "markdown"

    def test_supported_extensions(self):
        """Test supported extensions."""
        validator = MarkdownValidator()
        assert ".md" in validator.supported_extensions()
        assert ".markdown" in validator.supported_extensions()


class TestYAMLValidator:
    """Tests for YAMLValidator."""

    def test_name(self):
        """Test validator name."""
        validator = YAMLValidator()
        assert validator.name() == "yaml"

    def test_supported_extensions(self):
        """Test supported extensions."""
        validator = YAMLValidator()
        assert ".yaml" in validator.supported_extensions()
        assert ".yml" in validator.supported_extensions()


class TestJSONValidator:
    """Tests for JSONValidator."""

    def test_name(self):
        """Test validator name."""
        validator = JSONValidator()
        assert validator.name() == "json"

    def test_supported_extensions(self):
        """Test supported extensions."""
        validator = JSONValidator()
        assert ".json" in validator.supported_extensions()

    def test_is_available(self):
        """Test is_available (always True for JSON)."""
        validator = JSONValidator()
        assert validator.is_available() is True

    def test_validate_valid_json(self, tmp_path):
        """Test validation of valid JSON."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')

        validator = JSONValidator()
        result = validator.validate(json_file)

        assert result.passed is True
        assert len(result.issues) == 0

    def test_validate_invalid_json(self, tmp_path):
        """Test validation of invalid JSON."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": invalid}')

        validator = JSONValidator()
        result = validator.validate(json_file)

        assert result.passed is False
        assert len(result.issues) == 1
        assert result.issues[0].severity == Severity.ERROR
