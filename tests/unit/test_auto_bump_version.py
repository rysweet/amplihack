#!/usr/bin/env python3
"""
Tests for auto_bump_version.py script

Tests the automatic version bumping functionality for pyproject.toml
"""

import sys
from pathlib import Path

import pytest

# Add scripts directory to path so we can import the script
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from auto_bump_version import (
    bump_patch_version,
    parse_semantic_version,
    parse_version_from_pyproject,
    update_version_in_pyproject,
)


class TestParseVersionFromPyproject:
    """Test parsing version from pyproject.toml content"""

    def test_parse_valid_version_double_quotes(self):
        content = 'version = "0.4.1"\ndescription = "test"'
        assert parse_version_from_pyproject(content) == "0.4.1"

    def test_parse_valid_version_single_quotes(self):
        content = "version = '0.4.1'\ndescription = 'test'"
        assert parse_version_from_pyproject(content) == "0.4.1"

    def test_parse_version_with_spaces(self):
        content = '  version  =  "0.4.1"  \ndescription = "test"'
        assert parse_version_from_pyproject(content) == "0.4.1"

    def test_parse_version_not_found(self):
        content = 'name = "test"\ndescription = "test"'
        assert parse_version_from_pyproject(content) is None

    def test_parse_version_multiline(self):
        content = """
[project]
name = "test"
version = "1.2.3"
description = "test"
"""
        assert parse_version_from_pyproject(content) == "1.2.3"


class TestParseSemanticVersion:
    """Test parsing semantic version strings"""

    def test_parse_valid_version(self):
        assert parse_semantic_version("0.4.1") == (0, 4, 1)
        assert parse_semantic_version("1.0.0") == (1, 0, 0)
        assert parse_semantic_version("10.20.30") == (10, 20, 30)

    def test_parse_invalid_version(self):
        assert parse_semantic_version("0.4") is None
        assert parse_semantic_version("0.4.1.2") is None
        assert parse_semantic_version("v0.4.1") is None
        assert parse_semantic_version("0.4.1-beta") is None
        assert parse_semantic_version("invalid") is None


class TestBumpPatchVersion:
    """Test bumping patch version"""

    def test_bump_patch(self):
        assert bump_patch_version("0.4.1") == "0.4.2"
        assert bump_patch_version("1.0.0") == "1.0.1"
        assert bump_patch_version("10.20.30") == "10.20.31"

    def test_bump_patch_nine(self):
        assert bump_patch_version("0.4.9") == "0.4.10"
        assert bump_patch_version("0.4.99") == "0.4.100"

    def test_bump_invalid_version(self):
        assert bump_patch_version("0.4") is None
        assert bump_patch_version("invalid") is None


class TestUpdateVersionInPyproject:
    """Test updating version in pyproject.toml file"""

    def test_update_version_success(self, tmp_path, monkeypatch):
        # Create temporary pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        content = """[project]
name = "test"
version = "0.4.1"
description = "test"
"""
        pyproject.write_text(content)

        # Change working directory to tmp_path
        monkeypatch.chdir(tmp_path)

        # Update version
        assert update_version_in_pyproject("0.4.2") is True

        # Verify update
        updated_content = pyproject.read_text()
        assert 'version = "0.4.2"' in updated_content
        assert 'version = "0.4.1"' not in updated_content

    def test_update_version_single_quotes(self, tmp_path, monkeypatch):
        # Create temporary pyproject.toml with single quotes
        pyproject = tmp_path / "pyproject.toml"
        content = """[project]
name = "test"
version = '0.4.1'
description = "test"
"""
        pyproject.write_text(content)

        # Change working directory to tmp_path
        monkeypatch.chdir(tmp_path)

        # Update version
        assert update_version_in_pyproject("0.4.2") is True

        # Verify update - should maintain single quotes
        updated_content = pyproject.read_text()
        assert "version = '0.4.2'" in updated_content

    def test_update_version_file_not_found(self, tmp_path, monkeypatch):
        # Change to empty directory
        monkeypatch.chdir(tmp_path)

        # Try to update version
        assert update_version_in_pyproject("0.4.2") is False

    def test_update_version_preserves_formatting(self, tmp_path, monkeypatch):
        # Create temporary pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        content = """[project]
name = "test"
  version  =  "0.4.1"
description = "test"
"""
        pyproject.write_text(content)

        # Change working directory to tmp_path
        monkeypatch.chdir(tmp_path)

        # Update version
        assert update_version_in_pyproject("0.4.2") is True

        # Verify update preserves spacing
        updated_content = pyproject.read_text()
        assert '  version  =  "0.4.2"' in updated_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
