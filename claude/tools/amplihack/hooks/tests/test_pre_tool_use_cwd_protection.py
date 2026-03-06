#!/usr/bin/env python3
"""
Tests for CWD protection features in pre_tool_use hook.

Tests cover:
- CWD deletion blocking (rm -rf, rmdir)
- CWD rename/move blocking (mv)
- Path extraction helpers
"""

import sys
from pathlib import Path
from unittest.mock import patch

try:
    import pytest
except ImportError:
    pytest = None

sys.path.insert(0, str(Path(__file__).parent.parent))

from pre_tool_use import _MV_RE, PreToolUseHook


class TestCwdDeletionBlocking:
    """Test CWD deletion protection."""

    def test_blocks_rm_rf_on_cwd(self, tmp_path):
        """Should block rm -rf that would delete CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "project")):
            result = hook._check_cwd_deletion(f"rm -rf {tmp_path}")

        assert result.get("block") is True
        assert "BLOCKED" in result.get("message", "")

    def test_allows_rm_rf_on_unrelated_dir(self, tmp_path):
        """Should allow rm -rf on directory not containing CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        unrelated = tmp_path / "unrelated"
        unrelated.mkdir()

        with patch("os.getcwd", return_value=str(tmp_path / "project")):
            result = hook._check_cwd_deletion(f"rm -rf {unrelated}")

        assert result == {}

    def test_blocks_rmdir_on_cwd(self, tmp_path):
        """Should block rmdir that would delete CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path)):
            result = hook._check_cwd_deletion(f"rmdir {tmp_path}")

        assert result.get("block") is True


class TestCwdRenameBlocking:
    """Test CWD rename/move protection."""

    def test_blocks_mv_on_cwd(self, tmp_path):
        """Should block mv that would rename CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "myproject")):
            result = hook._check_cwd_rename(f"mv {tmp_path} /tmp/newname")

        assert result.get("block") is True
        assert "BLOCKED" in result.get("message", "")
        assert "rename" in result.get("message", "").lower()

    def test_blocks_mv_on_parent_of_cwd(self, tmp_path):
        """Should block mv on parent directory of CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        parent = tmp_path / "parent"
        parent.mkdir()
        child = parent / "child"
        child.mkdir()

        with patch("os.getcwd", return_value=str(child)):
            result = hook._check_cwd_rename(f"mv {parent} {tmp_path}/newparent")

        assert result.get("block") is True

    def test_allows_mv_on_unrelated_dir(self, tmp_path):
        """Should allow mv on directory not containing CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        unrelated = tmp_path / "unrelated"
        unrelated.mkdir()

        with patch("os.getcwd", return_value=str(tmp_path / "project")):
            result = hook._check_cwd_rename(f"mv {unrelated} {tmp_path}/renamed")

        assert result == {}

    def test_allows_mv_on_file(self, tmp_path):
        """Should allow mv on regular files."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        test_file = tmp_path / "test.txt"
        test_file.touch()

        with patch("os.getcwd", return_value=str(tmp_path)):
            result = hook._check_cwd_rename(f"mv {test_file} {tmp_path}/renamed.txt")

        assert result == {}

    def test_blocks_mv_with_full_path(self, tmp_path):
        """Should detect mv with /bin/mv full path."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path)):
            result = hook._check_cwd_rename(f"/bin/mv {tmp_path} /tmp/newname")

        assert result.get("block") is True

    def test_blocks_mv_with_glob_pattern(self, tmp_path):
        """Should block mv with glob pattern that could affect CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        # Create a parent directory structure
        parent = tmp_path / "parent"
        parent.mkdir()
        child = parent / "child"
        child.mkdir()

        with patch("os.getcwd", return_value=str(child)):
            # Glob pattern that could match the parent directory
            result = hook._check_cwd_rename(f"mv {tmp_path}/par* /tmp/newname")

        assert result.get("block") is True

    def test_allows_mv_with_glob_unrelated_to_cwd(self, tmp_path):
        """Should allow mv with glob pattern that can't affect CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        # CWD is in /tmp_path/project, glob is for /tmp_path/other*
        other = tmp_path / "other"
        other.mkdir()

        with patch("os.getcwd", return_value=str(tmp_path / "project")):
            result = hook._check_cwd_rename(f"mv {tmp_path}/oth* /tmp/newname")

        assert result == {}

    def test_blocks_mv_in_command_chain(self, tmp_path):
        """Should detect mv in command chain with && or ;."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path)):
            # Test with &&
            result = hook._check_cwd_rename(f"echo hello && mv {tmp_path} /tmp/new")
            assert result.get("block") is True

            # Test with ;
            result = hook._check_cwd_rename(f"echo hello; mv {tmp_path} /tmp/new")
            assert result.get("block") is True

    def test_handles_inaccessible_cwd(self, tmp_path):
        """Should handle case when CWD is inaccessible."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", side_effect=OSError("CWD deleted")):
            result = hook._check_cwd_rename("mv /some/path /other/path")

        # Should return empty dict (allow) rather than crash
        assert result == {}


class TestMvPathExtraction:
    """Test mv source path extraction."""

    def test_extracts_simple_source(self):
        """Should extract source from simple mv command."""
        paths = PreToolUseHook._extract_mv_source_paths("mv /src/path /dst/path")
        assert paths == ["/src/path"]

    def test_extracts_source_with_flags(self):
        """Should extract source, skipping flags."""
        paths = PreToolUseHook._extract_mv_source_paths("mv -f /src/path /dst/path")
        assert paths == ["/src/path"]

        paths = PreToolUseHook._extract_mv_source_paths("mv -v -i /src/path /dst/path")
        assert paths == ["/src/path"]

    def test_handles_target_directory_flag(self):
        """Should handle -t flag correctly."""
        # With -t, the argument after -t is the target, all remaining are sources
        paths = PreToolUseHook._extract_mv_source_paths("mv -t /target/dir /src/path")
        assert paths == ["/src/path"]

    def test_extracts_from_full_path_mv(self):
        """Should extract source from /bin/mv command."""
        paths = PreToolUseHook._extract_mv_source_paths("/bin/mv /src/path /dst/path")
        assert paths == ["/src/path"]

        paths = PreToolUseHook._extract_mv_source_paths("/usr/bin/mv /src/path /dst/path")
        assert paths == ["/src/path"]

    def test_handles_quoted_paths(self):
        """Should handle quoted paths."""
        paths = PreToolUseHook._extract_mv_source_paths('mv "/path with spaces" /dst')
        assert paths == ["/path with spaces"]

    def test_returns_empty_for_no_paths(self):
        """Should return empty list when no paths found."""
        paths = PreToolUseHook._extract_mv_source_paths("mv")
        assert paths == []

        paths = PreToolUseHook._extract_mv_source_paths("mv -v")
        assert paths == []

    def test_extracts_multiple_sources(self):
        """Should extract all source paths from multi-source mv."""
        paths = PreToolUseHook._extract_mv_source_paths("mv /src1 /src2 /src3 /dest/")
        assert paths == ["/src1", "/src2", "/src3"]

    def test_extracts_multiple_sources_with_t_flag(self):
        """Should extract all sources with -t flag."""
        paths = PreToolUseHook._extract_mv_source_paths("mv -t /dest/ /src1 /src2")
        assert paths == ["/src1", "/src2"]


class TestMvRegex:
    """Test mv command detection regex."""

    def test_matches_simple_mv(self):
        """Should match simple mv command."""
        assert _MV_RE.search("mv src dst")

    def test_matches_mv_with_flags(self):
        """Should match mv with flags."""
        assert _MV_RE.search("mv -f src dst")
        assert _MV_RE.search("mv -v -i src dst")

    def test_matches_full_path_mv(self):
        """Should match /bin/mv and /usr/bin/mv."""
        assert _MV_RE.search("/bin/mv src dst")
        assert _MV_RE.search("/usr/bin/mv src dst")

    def test_matches_mv_after_separator(self):
        """Should match mv after command separators."""
        assert _MV_RE.search("echo hi && mv src dst")
        assert _MV_RE.search("echo hi; mv src dst")

    def test_matches_sudo_mv(self):
        """Should match sudo mv commands."""
        assert _MV_RE.search("sudo mv src dst")
        assert _MV_RE.search("sudo -u root mv src dst")
        assert _MV_RE.search("sudo /bin/mv src dst")

    def test_matches_env_var_prefix(self):
        """Should match mv with environment variable prefix."""
        assert _MV_RE.search("VAR=1 mv src dst")
        assert _MV_RE.search("FOO=bar BAZ=qux mv src dst")

    def test_no_match_for_non_mv(self):
        """Should not match commands that aren't mv."""
        assert not _MV_RE.search("mvn clean install")
        assert not _MV_RE.search("movement src dst")


class TestIntegration:
    """Integration tests for pre_tool_use hook."""

    def test_process_blocks_mv_cwd(self, tmp_path):
        """Should block mv CWD via process method."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        input_data = {
            "toolUse": {
                "name": "Bash",
                "input": {"command": f"mv {tmp_path} /tmp/newname"},
            }
        }

        with patch("os.getcwd", return_value=str(tmp_path)):
            with patch.object(hook, "_select_strategy", return_value=None):
                result = hook.process(input_data)

        assert result.get("block") is True

    def test_process_allows_safe_mv(self, tmp_path):
        """Should allow mv that doesn't affect CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        unrelated = tmp_path / "unrelated"
        unrelated.mkdir()

        input_data = {
            "toolUse": {
                "name": "Bash",
                "input": {"command": f"mv {unrelated} {tmp_path}/renamed"},
            }
        }

        with patch("os.getcwd", return_value=str(tmp_path / "project")):
            with patch.object(hook, "_select_strategy", return_value=None):
                result = hook.process(input_data)

        assert result == {}

    def test_blocks_sudo_mv_cwd(self, tmp_path):
        """Should block sudo mv that would affect CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path)):
            result = hook._check_cwd_rename(f"sudo mv {tmp_path} /tmp/newname")

        assert result.get("block") is True

    def test_blocks_multi_source_mv_with_cwd(self, tmp_path):
        """Should block mv when CWD is among multiple sources."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        other = tmp_path / "other"
        other.mkdir()

        # CWD is second source
        with patch("os.getcwd", return_value=str(tmp_path)):
            result = hook._check_cwd_rename(f"mv {other} {tmp_path} /dest/")

        assert result.get("block") is True


def main():
    """Run tests."""
    if pytest is None:
        print("pytest not installed, skipping tests")
        return 1

    return pytest.main([__file__, "-v"])


if __name__ == "__main__":
    sys.exit(main())
