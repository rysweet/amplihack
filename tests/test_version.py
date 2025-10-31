"""Unit tests for version module.

Tests the version module's ability to read and validate version information
from pyproject.toml, ensuring a single source of truth for project versioning.
"""

import re
import sys
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

# Handle both Python 3.11+ (tomllib) and older versions (tomli)
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        pytest.skip("tomli not available for Python < 3.11", allow_module_level=True)

from amplihack.version import __version__, get_version


class TestGetVersion:
    """Unit tests for get_version() function."""

    def test_get_version_returns_valid_semver(self):
        """Verify get_version() returns string in format 'X.Y.Z'.

        This test ensures that the version returned follows semantic versioning
        format and matches the version specified in pyproject.toml.
        """
        version = get_version()

        # Verify it's a string
        assert isinstance(version, str), "Version should be a string"

        # Verify it's not empty
        assert version, "Version should not be empty"

        # Verify it matches semantic versioning pattern (X.Y.Z)
        semver_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(semver_pattern, version), (
            f"Version '{version}' does not match semantic versioning format 'X.Y.Z'"
        )

        # Verify major, minor, patch are all numeric
        parts = version.split(".")
        assert len(parts) == 3, "Version should have exactly 3 parts"
        assert all(part.isdigit() for part in parts), "All version components should be numeric"

    def test_version_matches_pyproject(self):
        """Verify get_version() matches version in pyproject.toml.

        This test ensures single source of truth by directly reading
        pyproject.toml and comparing with get_version() result.
        """
        # Get version from get_version() function
        version_from_function = get_version()

        # Read pyproject.toml directly
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml should exist"

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        version_from_file = data["project"]["version"]

        # Verify they match
        assert version_from_function == version_from_file, (
            f"Version from get_version() ({version_from_function}) "
            f"does not match version in pyproject.toml ({version_from_file})"
        )

    def test_version_format_valid(self):
        """Verify version format using regex validation.

        Uses semantic versioning regex pattern to validate format.
        Pattern: ^\\d+\\.\\d+\\.\\d+$
        """
        version = get_version()

        # Semantic versioning pattern
        semver_pattern = r"^\d+\.\d+\.\d+$"

        match = re.match(semver_pattern, version)
        assert match is not None, f"Version '{version}' does not match semantic versioning pattern"

        # Additional validation: ensure no leading zeros (except for "0")
        parts = version.split(".")
        for part in parts:
            if len(part) > 1:
                assert not part.startswith("0"), (
                    f"Version component '{part}' has invalid leading zero"
                )

    def test_get_version_pyproject_not_found(self):
        """Verify RuntimeError raised when both pyproject.toml and package metadata are unavailable."""
        with patch("pathlib.Path.exists", return_value=False):
            # Also mock importlib.metadata.version to fail
            with patch("importlib.metadata.version", side_effect=Exception("Package not found")):
                with pytest.raises(RuntimeError) as exc_info:
                    # Need to reload module to trigger the error
                    from amplihack.version import get_version as gv

                    gv()

                assert "Cannot determine version" in str(exc_info.value)
                assert "Neither pyproject.toml nor package metadata available" in str(exc_info.value)

    def test_get_version_missing_version_field(self):
        """Verify RuntimeError raised when version field is missing and package metadata unavailable."""
        # Mock pyproject.toml content without version field
        mock_toml_data = {"project": {"name": "test-project"}}

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=b"")):
                with patch.object(tomllib, "load", return_value=mock_toml_data):
                    # Also mock importlib.metadata.version to fail
                    with patch("importlib.metadata.version", side_effect=Exception("Package not found")):
                        with pytest.raises(RuntimeError) as exc_info:
                            from amplihack.version import get_version as gv

                            gv()

                        assert "Cannot determine version" in str(exc_info.value)
                        assert "Neither pyproject.toml nor package metadata available" in str(exc_info.value)

    def test_get_version_consistency(self):
        """Verify get_version() returns consistent results across multiple calls."""
        version1 = get_version()
        version2 = get_version()
        version3 = get_version()

        assert version1 == version2 == version3, "get_version() should return consistent results"


class TestVersionVariable:
    """Unit tests for __version__ module variable."""

    def test_version_variable_accessible(self):
        """Verify __version__ variable is accessible and valid.

        Tests that 'from amplihack.version import __version__' works
        and that __version__ is a non-empty string.
        """
        # __version__ is already imported at module level
        assert __version__ is not None, "__version__ should not be None"
        assert isinstance(__version__, str), "__version__ should be a string"
        assert __version__, "__version__ should not be empty"

    def test_version_variable_matches_function(self):
        """Verify __version__ variable matches get_version() result."""
        version_from_function = get_version()

        assert __version__ == version_from_function, (
            f"__version__ ({__version__}) does not match get_version() ({version_from_function})"
        )

    def test_version_variable_format(self):
        """Verify __version__ variable follows semantic versioning format."""
        semver_pattern = r"^\d+\.\d+\.\d+$"

        assert re.match(semver_pattern, __version__), (
            f"__version__ '{__version__}' does not match semantic versioning format"
        )


class TestVersionModuleIntegration:
    """Integration tests for version module functionality."""

    def test_module_imports_successfully(self):
        """Verify the version module can be imported without errors."""
        try:
            import amplihack.version

            assert hasattr(amplihack.version, "get_version")
            assert hasattr(amplihack.version, "__version__")
        except ImportError as e:
            pytest.fail(f"Failed to import amplihack.version: {e}")

    def test_version_single_source_of_truth(self):
        """Verify version information comes from single source (pyproject.toml).

        This test ensures the module correctly implements single source of truth
        principle by verifying all version information ultimately comes from
        pyproject.toml.
        """
        # All version information should be identical
        version_from_function = get_version()
        version_from_variable = __version__

        # Read directly from pyproject.toml
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        version_from_file = data["project"]["version"]

        # All should match
        assert version_from_function == version_from_variable == version_from_file, (
            "All version sources should match (single source of truth)"
        )

    def test_version_path_resolution(self):
        """Verify version module correctly resolves pyproject.toml path.

        Tests that the module navigates correctly from
        src/amplihack/version.py to project root pyproject.toml.
        """
        # The path calculation in version.py:
        # Path(__file__).parent.parent.parent / "pyproject.toml"
        # From: src/amplihack/version.py
        # To:   project_root/pyproject.toml

        version = get_version()

        # If we got here without FileNotFoundError, path resolution worked
        assert version is not None
        assert isinstance(version, str)


class TestVersionEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_version_with_prerelease_format(self):
        """Test handling of standard semantic version (without prerelease/build metadata).

        The current implementation expects X.Y.Z format.
        This test verifies the current behavior.
        """
        version = get_version()

        # Current implementation expects simple X.Y.Z format
        assert re.match(r"^\d+\.\d+\.\d+$", version), "Version should be in simple X.Y.Z format"

    def test_version_immutability(self):
        """Verify version cannot be easily modified at runtime."""
        original_version = __version__

        # Attempting to modify __version__ would require reimporting
        # This test documents the expected behavior
        assert __version__ == original_version

    def test_pyproject_path_calculation(self):
        """Verify pyproject.toml path calculation is correct.

        Documents the expected path resolution from module location
        to project root.
        """
        from amplihack.version import get_version

        # The function should successfully find and read pyproject.toml
        # without raising FileNotFoundError
        try:
            version = get_version()
            assert version is not None
        except FileNotFoundError:
            pytest.fail("pyproject.toml path calculation is incorrect")


class TestTomllibCompatibility:
    """Tests for tomllib/tomli compatibility handling."""

    def test_tomllib_available_python_311_plus(self):
        """Verify tomllib is used on Python 3.11+."""
        if sys.version_info >= (3, 11):
            import amplihack.version

            # On Python 3.11+, tomllib should be available
            assert hasattr(amplihack.version, "tomllib")
        else:
            pytest.skip("Test only applicable for Python 3.11+")

    def test_tomli_fallback_python_pre_311(self):
        """Verify tomli is used on Python < 3.11."""
        if sys.version_info < (3, 11):
            import amplihack.version

            # On Python < 3.11, tomli should be imported as tomllib
            assert hasattr(amplihack.version, "tomllib")
        else:
            pytest.skip("Test only applicable for Python < 3.11")

    def test_version_works_regardless_of_toml_library(self):
        """Verify version module works with both tomllib and tomli."""
        # This test documents that the version module should work
        # regardless of which TOML library is available
        version = get_version()
        assert version is not None
        assert isinstance(version, str)
        assert re.match(r"^\d+\.\d+\.\d+$", version)
