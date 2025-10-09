"""
Test UVX packaging functionality.

These tests validate that the framework can be packaged and deployed via UVX
with all required files accessible.
"""

import subprocess
import tempfile
import zipfile
from pathlib import Path

# Note: This test file is designed to work with or without pytest
# When pytest is available, tests can be run via pytest
# When not available, tests can be run as regular Python functions


class TestUVXPackaging:
    """Test UVX packaging and deployment functionality."""

    def test_package_build_completes_without_errors(self):
        """Test that the package builds without setuptools errors.

        This test validates that our pyproject.toml configuration
        doesn't cause packaging failures.
        """
        # This test should fail initially due to problematic data-files config
        result = subprocess.run(
            ["python", "-m", "build", "--wheel"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0, f"Package build failed: {result.stderr}"
        assert "error: can't copy" not in result.stderr
        assert "doesn't exist or not a regular file" not in result.stderr

    def test_framework_files_available_in_package(self):
        """Test that all framework files are included in the built package.

        Validates that the user's requirement for ALL files to be
        available is met.
        """
        # Build package first
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                ["python", "-m", "build", "--wheel", "--outdir", temp_dir],
                check=False,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0

            # Find the built wheel
            wheel_files = list(Path(temp_dir).glob("*.whl"))
            assert len(wheel_files) == 1, "Expected exactly one wheel file"

            # Extract wheel and check contents
            wheel_path = wheel_files[0]
            extract_dir = Path(temp_dir) / "extracted"
            with zipfile.ZipFile(str(wheel_path), "r") as zip_ref:
                zip_ref.extractall(str(extract_dir))

            # Check for critical framework files
            expected_files = [
                "CLAUDE.md",
                "DISCOVERIES.md",
                ".claude/workflow/DEFAULT_WORKFLOW.md",
                ".claude/agents/amplihack/core/architect.md",
                "docs",
                "examples",
                "Specs",
            ]

            for expected_file in expected_files:
                # Check if file/directory exists in package
                found = any(expected_file in str(path) for path in extract_dir.rglob("*"))
                assert found, f"Required file/directory not found in package: {expected_file}"

    # Note: This test may take time as it involves UVX installation
    def test_uvx_installation_succeeds(self):
        """Test that UVX can install the package from git.

        This is the critical end-to-end test that validates
        the entire UVX deployment workflow works.
        """
        # This test will fail initially due to packaging issues
        # Note: This test requires git repo to be pushed

        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to install via UVX (this should fail initially)
            result = subprocess.run(
                [
                    "uvx",
                    "--from",
                    "git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding@fix/issue-105-uvx-packaging-fix",
                    "amplihack",
                    "--help",
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=temp_dir,
                timeout=120,  # UVX installations can take time
            )

            assert result.returncode == 0, f"UVX installation failed: {result.stderr}"
            assert "error: can't copy" not in result.stderr
            assert "doesn't exist or not a regular file" not in result.stderr
            assert "usage:" in result.stdout.lower()  # Help output should appear

    def test_pyproject_toml_config_valid(self):
        """Test that pyproject.toml configuration is valid setuptools config."""
        import tomllib

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        # Validate setuptools configuration exists
        assert "tool" in config
        assert "setuptools" in config["tool"]

        # Check that we don't have problematic data-files configurations
        setuptools_config = config["tool"]["setuptools"]

        if "data-files" in setuptools_config:
            data_files = setuptools_config["data-files"]
            # If data-files exist, ensure they don't reference non-existent paths
            for target, sources in data_files.items():
                for source in sources:
                    if "**/*" in source:
                        # Glob patterns should not be used for directories
                        raise AssertionError(f"Problematic glob pattern in data-files: {source}")
