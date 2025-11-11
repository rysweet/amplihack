"""Tests for ClaudeMdIntegrator module."""

import time
from pathlib import Path
import pytest
import shutil
import tempfile

from amplihack.installation.claude_md_integrator import (
    integrate_import,
    remove_import,
    IMPORT_STATEMENT,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


def test_add_import_to_existing_file(temp_dir):
    """Test adding import to existing CLAUDE.md."""
    claude_md = temp_dir / "CLAUDE.md"
    claude_md.write_text("# My Config\n\nSome content here\n")

    result = integrate_import(claude_md)

    assert result.success
    assert result.action_taken == "added"
    assert result.backup_path is not None
    assert result.backup_path.exists()

    # Verify import was added
    content = claude_md.read_text()
    assert IMPORT_STATEMENT in content
    assert "My Config" in content  # Original content preserved


def test_create_new_file_with_import(temp_dir):
    """Test creating new CLAUDE.md with import."""
    claude_md = temp_dir / "CLAUDE.md"
    # File doesn't exist

    result = integrate_import(claude_md)

    assert result.success
    assert result.action_taken == "created_new"
    assert claude_md.exists()

    content = claude_md.read_text()
    assert IMPORT_STATEMENT in content


def test_detect_existing_import(temp_dir):
    """Test that existing import is detected."""
    claude_md = temp_dir / "CLAUDE.md"
    claude_md.write_text(f"# Config\n\n{IMPORT_STATEMENT}\n\nMore content\n")

    result = integrate_import(claude_md)

    assert result.success
    assert result.action_taken == "already_present"
    assert result.backup_path is None  # No backup needed


def test_detect_existing_import_with_whitespace(temp_dir):
    """Test detection of import with whitespace variations."""
    claude_md = temp_dir / "CLAUDE.md"

    # Test with leading/trailing whitespace
    claude_md.write_text(f"# Config\n\n  {IMPORT_STATEMENT}  \n\n")

    result = integrate_import(claude_md)

    assert result.success
    assert result.action_taken == "already_present"


def test_remove_import(temp_dir):
    """Test removing import from CLAUDE.md."""
    claude_md = temp_dir / "CLAUDE.md"
    content = f"# Config\n\n{IMPORT_STATEMENT}\n\nOther content\n"
    claude_md.write_text(content)

    result = remove_import(claude_md)

    assert result.success
    assert result.action_taken == "removed"
    assert result.backup_path is not None

    # Verify import was removed
    new_content = claude_md.read_text()
    assert IMPORT_STATEMENT not in new_content
    assert "Other content" in new_content  # Other content preserved


def test_remove_import_not_present(temp_dir):
    """Test removing import when it's not present."""
    claude_md = temp_dir / "CLAUDE.md"
    claude_md.write_text("# Config\n\nNo import here\n")

    result = remove_import(claude_md)

    assert result.success
    assert result.action_taken == "not_present"


def test_backup_creation(temp_dir):
    """Test that backups are created correctly."""
    claude_md = temp_dir / "CLAUDE.md"
    original_content = "# Original\n\nContent\n"
    claude_md.write_text(original_content)

    result = integrate_import(claude_md)

    assert result.success
    assert result.backup_path is not None
    assert result.backup_path.exists()

    # Verify backup contains original content
    backup_content = result.backup_path.read_text()
    assert backup_content == original_content


def test_dry_run_no_changes(temp_dir):
    """Test that dry_run mode doesn't modify files."""
    claude_md = temp_dir / "CLAUDE.md"
    original_content = "# Config\n\nOriginal\n"
    claude_md.write_text(original_content)

    result = integrate_import(claude_md, dry_run=True)

    assert result.success
    assert result.action_taken == "preview"
    assert IMPORT_STATEMENT in result.preview

    # File should be unchanged
    assert claude_md.read_text() == original_content


def test_backup_rotation(temp_dir):
    """Test that old backups are removed (keep last 3)."""
    claude_md = temp_dir / "CLAUDE.md"
    claude_md.write_text("# Original\n")

    # Create multiple backups by modifying file multiple times
    for i in range(5):
        claude_md.write_text(f"# Version {i}\n")
        integrate_import(claude_md, dry_run=False)
        # Remove import to allow adding again
        content = claude_md.read_text().replace(IMPORT_STATEMENT, "")
        claude_md.write_text(content)
        time.sleep(0.01)  # Ensure different timestamps

    # Check backup count
    backups = list(temp_dir.glob("CLAUDE.md.backup.*"))
    assert len(backups) <= 3  # Should keep only 3 most recent


def test_preserve_frontmatter(temp_dir):
    """Test that YAML frontmatter is preserved."""
    claude_md = temp_dir / "CLAUDE.md"
    content = "---\ntitle: My Config\nauthor: User\n---\n\n# Content\n"
    claude_md.write_text(content)

    result = integrate_import(claude_md)

    assert result.success

    new_content = claude_md.read_text()
    assert "---" in new_content
    assert "title: My Config" in new_content
    # Import should be after frontmatter
    frontmatter_end = new_content.find("---", 3) + 3
    import_pos = new_content.find(IMPORT_STATEMENT)
    assert import_pos > frontmatter_end


def test_handle_permission_error(temp_dir):
    """Test graceful handling of permission errors."""
    import sys

    if sys.platform == "win32":
        pytest.skip("Permission test not applicable on Windows")

    claude_md = temp_dir / "CLAUDE.md"
    claude_md.write_text("# Config\n")

    # Make file read-only
    import os

    os.chmod(claude_md, 0o444)

    try:
        result = integrate_import(claude_md)

        # Should fail gracefully
        assert not result.success
        assert result.action_taken == "error"
        assert result.error is not None
    finally:
        # Restore permissions
        os.chmod(claude_md, 0o644)


def test_remove_import_dry_run(temp_dir):
    """Test dry run mode for remove_import."""
    claude_md = temp_dir / "CLAUDE.md"
    original = f"# Config\n\n{IMPORT_STATEMENT}\n\nContent\n"
    claude_md.write_text(original)

    result = remove_import(claude_md, dry_run=True)

    assert result.success
    assert result.action_taken == "preview"

    # File should be unchanged
    assert claude_md.read_text() == original


def test_import_at_top_of_file(temp_dir):
    """Test that import is added at top of file (for precedence)."""
    claude_md = temp_dir / "CLAUDE.md"
    claude_md.write_text("# My Config\n\nContent line 1\nContent line 2\n")

    result = integrate_import(claude_md)

    assert result.success

    lines = claude_md.read_text().split("\n")
    # Import should be at or near the top (first non-empty line after frontmatter)
    assert IMPORT_STATEMENT in lines[:5]


def test_handle_empty_file(temp_dir):
    """Test handling of empty CLAUDE.md file."""
    claude_md = temp_dir / "CLAUDE.md"
    claude_md.write_text("")

    result = integrate_import(claude_md)

    assert result.success
    assert IMPORT_STATEMENT in claude_md.read_text()


def test_handle_whitespace_only_file(temp_dir):
    """Test handling of CLAUDE.md with only whitespace."""
    claude_md = temp_dir / "CLAUDE.md"
    claude_md.write_text("   \n\n  \n")

    result = integrate_import(claude_md)

    assert result.success
    assert IMPORT_STATEMENT in claude_md.read_text()


def test_remove_cleans_extra_blank_lines(temp_dir):
    """Test that removing import doesn't leave excessive blank lines."""
    claude_md = temp_dir / "CLAUDE.md"
    content = f"# Config\n\n{IMPORT_STATEMENT}\n\n\nContent\n"
    claude_md.write_text(content)

    result = remove_import(claude_md)

    assert result.success

    new_content = claude_md.read_text()
    # Should not have triple newlines
    assert "\n\n\n" not in new_content
