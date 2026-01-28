"""Tests for PrerequisiteChecker module.

Tests detection of missing prerequisites and validation that
at least one language can proceed (partial success).
"""

from unittest.mock import Mock, patch

import pytest

from amplihack.memory.kuzu.indexing.prerequisite_checker import (
    LanguageStatus,
    PrerequisiteChecker,
)


class TestPrerequisiteChecker:
    """Test prerequisite detection for indexing tools."""

    @pytest.fixture
    def checker(self):
        """Create PrerequisiteChecker instance."""
        return PrerequisiteChecker()

    def test_detect_missing_scip_python_binary(self, checker):
        """Test detection of missing scip-python binary."""
        # Arrange
        with patch("shutil.which", return_value=None):
            # Act
            result = checker.check_language("python")

            # Assert
            assert result.language == "python"
            assert result.available is False
            assert "scip-python" in result.error_message.lower()
            assert result.missing_tools == ["scip-python"]

    def test_detect_missing_jedi_initialize_params(self, checker):
        """Test detection of missing initialize_params.json for jedi."""
        # Arrange
        with (
            patch("shutil.which", return_value="/usr/bin/python"),
            patch("pathlib.Path.exists", return_value=False),
        ):
            # Act
            result = checker.check_language("python", indexer_type="jedi")

            # Assert
            assert result.language == "python"
            assert result.available is False
            assert "initialize_params.json" in result.error_message
            assert result.missing_tools == ["initialize_params.json"]

    def test_detect_unknown_dotnet_version(self, checker):
        """Test detection of unknown dotnet version 10.0.2."""
        # Arrange
        mock_subprocess = Mock()
        mock_subprocess.returncode = 0
        mock_subprocess.stdout = "10.0.2\n"

        with patch("subprocess.run", return_value=mock_subprocess):
            # Act
            result = checker.check_language("csharp")

            # Assert
            assert result.language == "csharp"
            assert result.available is False
            assert "10.0.2" in result.error_message
            assert "unsupported version" in result.error_message.lower()

    def test_detect_missing_typescript_runtime_dependencies(self, checker):
        """Test detection of missing runtime_dependencies.json for TypeScript."""
        # Arrange
        with (
            patch("shutil.which", return_value="/usr/bin/node"),
            patch("pathlib.Path.exists", return_value=False),
        ):
            # Act
            result = checker.check_language("typescript")

            # Assert
            assert result.language == "typescript"
            assert result.available is False
            assert "runtime_dependencies.json" in result.error_message
            assert result.missing_tools == ["runtime_dependencies.json"]

    def test_at_least_one_language_can_proceed_partial_success(self, checker):
        """Test that at least one language can proceed (partial success)."""
        # Arrange
        languages = ["python", "javascript", "typescript", "csharp"]

        with patch.object(checker, "check_language") as mock_check:
            # Mock results: only javascript succeeds
            mock_check.side_effect = [
                LanguageStatus(
                    language="python",
                    available=False,
                    error_message="scip-python not found",
                    missing_tools=["scip-python"],
                ),
                LanguageStatus(
                    language="javascript",
                    available=True,
                    error_message=None,
                    missing_tools=[],
                ),
                LanguageStatus(
                    language="typescript",
                    available=False,
                    error_message="runtime_dependencies.json not found",
                    missing_tools=["runtime_dependencies.json"],
                ),
                LanguageStatus(
                    language="csharp",
                    available=False,
                    error_message="dotnet version 10.0.2 unsupported",
                    missing_tools=["dotnet"],
                ),
            ]

            # Act
            result = checker.check_all(languages)

            # Assert
            assert result.can_proceed is True
            assert len(result.available_languages) == 1
            assert "javascript" in result.available_languages
            assert len(result.unavailable_languages) == 3
            assert result.partial_success is True

    def test_report_includes_error_messages_for_missing_tools(self, checker):
        """Test that report includes error messages for missing tools."""
        # Arrange
        languages = ["python", "csharp"]

        with patch.object(checker, "check_language") as mock_check:
            mock_check.side_effect = [
                LanguageStatus(
                    language="python",
                    available=False,
                    error_message="scip-python binary not found in PATH",
                    missing_tools=["scip-python"],
                ),
                LanguageStatus(
                    language="csharp",
                    available=False,
                    error_message="dotnet version 10.0.2 is not supported",
                    missing_tools=["dotnet"],
                ),
            ]

            # Act
            result = checker.check_all(languages)
            report = result.generate_report()

            # Assert
            assert "scip-python binary not found in PATH" in report
            assert "dotnet version 10.0.2 is not supported" in report
            assert result.can_proceed is False

    def test_all_languages_unavailable(self, checker):
        """Test scenario where all languages are unavailable."""
        # Arrange
        languages = ["python", "typescript"]

        with patch.object(checker, "check_language") as mock_check:
            mock_check.side_effect = [
                LanguageStatus(
                    language="python",
                    available=False,
                    error_message="scip-python not found",
                    missing_tools=["scip-python"],
                ),
                LanguageStatus(
                    language="typescript",
                    available=False,
                    error_message="runtime_dependencies.json not found",
                    missing_tools=["runtime_dependencies.json"],
                ),
            ]

            # Act
            result = checker.check_all(languages)

            # Assert
            assert result.can_proceed is False
            assert len(result.available_languages) == 0
            assert len(result.unavailable_languages) == 2
            assert result.partial_success is False

    def test_all_languages_available(self, checker):
        """Test scenario where all languages are available."""
        # Arrange
        languages = ["python", "javascript"]

        with patch.object(checker, "check_language") as mock_check:
            mock_check.side_effect = [
                LanguageStatus(
                    language="python",
                    available=True,
                    error_message=None,
                    missing_tools=[],
                ),
                LanguageStatus(
                    language="javascript",
                    available=True,
                    error_message=None,
                    missing_tools=[],
                ),
            ]

            # Act
            result = checker.check_all(languages)

            # Assert
            assert result.can_proceed is True
            assert len(result.available_languages) == 2
            assert len(result.unavailable_languages) == 0
            assert result.partial_success is False

    def test_check_python_with_scip_python(self, checker):
        """Test successful Python check with scip-python."""
        # Arrange
        with patch("shutil.which", return_value="/usr/local/bin/scip-python"):
            # Act
            result = checker.check_language("python")

            # Assert
            assert result.language == "python"
            assert result.available is True
            assert result.error_message is None
            assert result.missing_tools == []

    def test_check_csharp_with_supported_dotnet_version(self, checker):
        """Test successful C# check with supported dotnet version."""
        # Arrange
        mock_subprocess = Mock()
        mock_subprocess.returncode = 0
        mock_subprocess.stdout = "8.0.100\n"

        with patch("subprocess.run", return_value=mock_subprocess):
            # Act
            result = checker.check_language("csharp")

            # Assert
            assert result.language == "csharp"
            assert result.available is True
            assert result.error_message is None
            assert result.missing_tools == []
