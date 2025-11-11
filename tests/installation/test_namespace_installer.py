"""Tests for NamespaceInstaller module."""

import os
from pathlib import Path
import pytest
import shutil
import tempfile

from amplihack.installation.namespace_installer import (
    install_to_namespace,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def source_files(temp_dir):
    """Create source files for installation."""
    source_dir = temp_dir / "source"
    source_dir.mkdir()

    # Create minimal valid installation files
    (source_dir / "CLAUDE.md").write_text("# Amplihack Config")

    agents_dir = source_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "architect.md").write_text("# Architect Agent")
    (agents_dir / "builder.md").write_text("# Builder Agent")

    commands_dir = source_dir / "commands"
    commands_dir.mkdir()
    (commands_dir / "ultrathink.md").write_text("# UltraThink Command")

    return source_dir


def test_install_to_empty_namespace(temp_dir, source_files):
    """Test installation to empty namespace directory."""
    target_dir = temp_dir / ".claude"
    target_dir.mkdir()

    result = install_to_namespace(source_files, target_dir, force=False)

    assert result.success
    assert result.installed_path == target_dir / "amplihack"
    assert result.installed_path.exists()
    assert len(result.files_installed) > 0
    assert len(result.errors) == 0

    # Verify key files were installed
    assert (result.installed_path / "CLAUDE.md").exists()
    assert (result.installed_path / "agents" / "architect.md").exists()
    assert (result.installed_path / "commands" / "ultrathink.md").exists()


def test_install_fails_without_force(temp_dir, source_files):
    """Test that installation fails if namespace exists and force=False."""
    target_dir = temp_dir / ".claude"
    amplihack_dir = target_dir / "amplihack"
    amplihack_dir.mkdir(parents=True)

    # Create existing file
    (amplihack_dir / "existing.txt").write_text("existing")

    result = install_to_namespace(source_files, target_dir, force=False)

    assert not result.success
    assert len(result.errors) > 0
    assert "already installed" in result.errors[0].lower()

    # Existing file should still be there
    assert (amplihack_dir / "existing.txt").exists()


def test_install_with_force_overwrites(temp_dir, source_files):
    """Test that force=True overwrites existing installation."""
    target_dir = temp_dir / ".claude"
    amplihack_dir = target_dir / "amplihack"
    amplihack_dir.mkdir(parents=True)

    # Create existing file that should be removed
    existing_file = amplihack_dir / "old_file.txt"
    existing_file.write_text("old content")

    result = install_to_namespace(source_files, target_dir, force=True)

    assert result.success
    assert len(result.errors) == 0

    # Old file should be gone
    assert not existing_file.exists()

    # New files should be present
    assert (amplihack_dir / "CLAUDE.md").exists()
    assert (amplihack_dir / "agents" / "architect.md").exists()


def test_install_preserves_structure(temp_dir, source_files):
    """Test that directory structure is preserved during installation."""
    target_dir = temp_dir / ".claude"
    target_dir.mkdir()

    result = install_to_namespace(source_files, target_dir)

    assert result.success

    # Verify nested structure
    amplihack_dir = target_dir / "amplihack"
    assert (amplihack_dir / "agents").is_dir()
    assert (amplihack_dir / "commands").is_dir()
    assert (amplihack_dir / "agents" / "architect.md").is_file()


def test_install_handles_permission_errors(temp_dir, source_files):
    """Test graceful handling of permission errors."""
    import sys

    if sys.platform == "win32":
        pytest.skip("Permission test not applicable on Windows")

    target_dir = temp_dir / ".claude"
    target_dir.mkdir()

    # Make target directory read-only
    os.chmod(target_dir, 0o444)

    try:
        result = install_to_namespace(source_files, target_dir)

        # Should fail gracefully with error message
        assert not result.success
        assert len(result.errors) > 0
    finally:
        # Restore permissions for cleanup
        os.chmod(target_dir, 0o755)


def test_install_missing_source(temp_dir):
    """Test behavior when source directory doesn't exist."""
    target_dir = temp_dir / ".claude"
    target_dir.mkdir()

    missing_source = temp_dir / "nonexistent"

    result = install_to_namespace(missing_source, target_dir)

    assert not result.success
    assert "not found" in result.errors[0].lower()


def test_install_creates_parent_directories(temp_dir, source_files):
    """Test that parent directories are created if needed."""
    target_dir = temp_dir / ".claude"
    # Don't create target_dir - it should be created automatically

    result = install_to_namespace(source_files, target_dir)

    assert result.success
    assert target_dir.exists()
    assert (target_dir / "amplihack").exists()


def test_install_incomplete_source(temp_dir):
    """Test validation fails with incomplete source."""
    source_dir = temp_dir / "incomplete"
    source_dir.mkdir()

    # Create source without required files (missing agents/)
    (source_dir / "CLAUDE.md").write_text("# Config")

    target_dir = temp_dir / ".claude"
    target_dir.mkdir()

    result = install_to_namespace(source_dir, target_dir)

    assert not result.success
    assert "incomplete" in result.errors[0].lower()


def test_install_reports_installed_files(temp_dir, source_files):
    """Test that all installed files are reported."""
    target_dir = temp_dir / ".claude"
    target_dir.mkdir()

    result = install_to_namespace(source_files, target_dir)

    assert result.success
    assert len(result.files_installed) >= 4  # CLAUDE.md + 2 agents + 1 command

    # Verify paths are relative to target_dir
    for file_path in result.files_installed:
        assert not file_path.is_absolute()
        assert str(file_path).startswith("amplihack")
