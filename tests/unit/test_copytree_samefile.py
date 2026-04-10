"""Tests for copytree_manifest same-file guard (issue #4296).

Verifies that copytree_manifest returns early without raising
shutil.SameFileError when source and destination resolve to the
same directory.
"""

import os
import shutil

import pytest

from amplihack.install import copytree_manifest


class TestCopytreeManifestSameFileGuard:
    """copytree_manifest must not crash when source == dest."""

    def test_same_directory_does_not_raise(self, tmp_path):
        """Calling copytree_manifest where source == dest should skip, not crash."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        sub = claude_dir / "bin"
        sub.mkdir()
        (sub / "run.sh").write_text("test script")

        # repo_root = tmp_path, dst = tmp_path, rel_top = ".claude"
        # => source_dir and target_dir both resolve to tmp_path/.claude/bin
        # This MUST NOT raise shutil.SameFileError
        result = copytree_manifest(
            repo_root=str(tmp_path),
            dst=str(tmp_path),
            rel_top=".claude",
        )

        # Function should succeed (returning list) without exception
        assert isinstance(result, list)
        # Original file should still exist
        assert (sub / "run.sh").read_text() == "test script"

    def test_same_directory_via_symlink_does_not_raise(self, tmp_path):
        """Same-file guard handles symlinked paths."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        claude_dir = real_dir / ".claude"
        claude_dir.mkdir()
        (claude_dir / "bin").mkdir()
        (claude_dir / "bin" / "run.sh").write_text("data")

        link_dir = tmp_path / "link"
        link_dir.symlink_to(real_dir)

        # repo_root = real_dir, dst = link_dir => same underlying path
        result = copytree_manifest(
            repo_root=str(real_dir),
            dst=str(link_dir),
            rel_top=".claude",
        )

        assert isinstance(result, list)
        assert (claude_dir / "bin" / "run.sh").read_text() == "data"

    def test_different_directories_still_copies(self, tmp_path):
        """Normal copy (different source/dest) still works."""
        source = tmp_path / "source"
        source.mkdir()
        claude_dir = source / ".claude"
        claude_dir.mkdir()
        # Use a real dir from ESSENTIAL_DIRS
        (claude_dir / "bin").mkdir()
        (claude_dir / "bin" / "run.sh").write_text("hello")

        dest = tmp_path / "dest"
        dest.mkdir()

        result = copytree_manifest(
            repo_root=str(source),
            dst=str(dest),
            rel_top=".claude",
        )

        assert len(result) > 0
        assert (dest / "bin" / "run.sh").read_text() == "hello"
