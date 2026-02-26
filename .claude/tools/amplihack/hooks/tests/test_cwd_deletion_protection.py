#!/usr/bin/env python3
"""
Tests for CWD deletion protection in pre_tool_use hook.

Prevents the agent from deleting its own working directory.
Issue: #2276

Testing pyramid:
- 60% Unit tests (path matching logic)
- 30% Integration tests (full hook invocation)
- 10% Edge cases (symlinks, relative paths)
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add hooks directory to path for imports
hooks_dir = Path(__file__).parent.parent
sys.path.insert(0, str(hooks_dir))

from pre_tool_use import _MV_RE, PreToolUseHook

# ============================================================================
# UNIT TESTS - CWD Deletion Detection
# ============================================================================


class TestCwdDeletionDetection:
    """Unit tests for detecting commands that would delete the CWD."""

    def _make_input(self, command: str) -> dict:
        return {"toolUse": {"name": "Bash", "input": {"command": command}}}

    def test_blocks_rm_rf_on_cwd(self, tmp_path):
        """rm -rf <cwd> must be blocked."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "worktrees" / "feat")):
            result = hook.process(self._make_input(f"rm -rf {tmp_path / 'worktrees' / 'feat'}"))
            assert result.get("block") is True

    def test_blocks_rm_rf_on_parent_of_cwd(self, tmp_path):
        """rm -rf <parent-of-cwd> must be blocked (would destroy CWD)."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "worktrees" / "feat")):
            result = hook.process(self._make_input(f"rm -rf {tmp_path / 'worktrees'}"))
            assert result.get("block") is True

    def test_allows_rm_rf_on_unrelated_dir(self, tmp_path):
        """rm -rf on unrelated directory should be allowed."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "worktrees" / "feat")):
            result = hook.process(self._make_input(f"rm -rf {tmp_path / 'other' / 'dir'}"))
            assert result.get("block") is not True

    def test_blocks_rm_r_on_cwd(self, tmp_path):
        """rm -r <cwd> (without -f) must also be blocked."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "work")):
            result = hook.process(self._make_input(f"rm -r {tmp_path / 'work'}"))
            assert result.get("block") is True

    def test_blocks_rm_fr_on_cwd(self, tmp_path):
        """rm -fr <cwd> (flag order reversed) must be blocked."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "work")):
            result = hook.process(self._make_input(f"rm -fr {tmp_path / 'work'}"))
            assert result.get("block") is True

    def test_blocks_rmdir_on_cwd(self, tmp_path):
        """rmdir <cwd> must be blocked."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "work")):
            result = hook.process(self._make_input(f"rmdir {tmp_path / 'work'}"))
            assert result.get("block") is True

    def test_allows_rm_single_file(self, tmp_path):
        """rm <file> (no recursive flag) should be allowed."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path)):
            result = hook.process(self._make_input(f"rm {tmp_path / 'file.txt'}"))
            assert result.get("block") is not True

    def test_allows_non_rm_commands(self, tmp_path):
        """Non-rm commands should pass through."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path)):
            result = hook.process(self._make_input("ls -la"))
            assert result.get("block") is not True

    def test_blocks_chained_command_with_rm_rf_cwd(self, tmp_path):
        """Commands chained with && or ; containing rm -rf CWD must be blocked."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "work")):
            result = hook.process(self._make_input(f"cd / && rm -rf {tmp_path / 'work'}"))
            assert result.get("block") is True

    def test_blocks_piped_rm_rf_cwd(self, tmp_path):
        """rm -rf CWD in a piped command must be blocked."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "work")):
            result = hook.process(self._make_input(f"echo yes | rm -rf {tmp_path / 'work'}"))
            assert result.get("block") is True


# ============================================================================
# INTEGRATION TESTS - Full Hook Flow
# ============================================================================


class TestCwdDeletionFullHook:
    """Integration tests verifying CWD protection works within full hook flow."""

    def _make_input(self, command: str) -> dict:
        return {"toolUse": {"name": "Bash", "input": {"command": command}}}

    def test_cwd_protection_doesnt_break_git_checks(self, tmp_path):
        """CWD protection must not interfere with existing git commit checks."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path)):
            with patch("subprocess.run") as mock_run:
                from unittest.mock import Mock

                mock_run.return_value = Mock(returncode=0, stdout="feature/test\n", stderr="")
                result = hook.process(self._make_input("git commit -m 'test'"))
                assert result.get("block") is not True

    def test_non_bash_tools_still_unaffected(self, tmp_path):
        """Non-Bash tools must still pass through."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        result = hook.process({"toolUse": {"name": "Read", "input": {"file_path": "/some/file"}}})
        assert result.get("block") is not True

    def test_error_message_is_clear(self, tmp_path):
        """Blocked message should clearly explain what happened."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "work")):
            result = hook.process(self._make_input(f"rm -rf {tmp_path / 'work'}"))
            assert result.get("block") is True
            msg = result.get("message", "")
            assert "working directory" in msg.lower() or "cwd" in msg.lower()


# ============================================================================
# EDGE CASES
# ============================================================================


class TestCwdDeletionEdgeCases:
    """Edge case tests for CWD deletion protection."""

    def _make_input(self, command: str) -> dict:
        return {"toolUse": {"name": "Bash", "input": {"command": command}}}

    def test_dot_path_blocked(self, tmp_path):
        """rm -rf . should be blocked (refers to CWD)."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path)):
            result = hook.process(self._make_input("rm -rf ."))
            assert result.get("block") is True

    def test_dot_dot_blocked_if_parent_is_cwd(self, tmp_path):
        """rm -rf .. should be blocked if it would delete CWD's parent."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        cwd = tmp_path / "sub" / "dir"
        with patch("os.getcwd", return_value=str(cwd)):
            # .. from cwd resolves to tmp_path/sub, which is parent of CWD
            result = hook.process(self._make_input("rm -rf .."))
            assert result.get("block") is True

    def test_git_worktree_remove_with_rm_rf(self, tmp_path):
        """Worktree cleanup via rm -rf should be blocked if it targets CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        worktree = tmp_path / "worktrees" / "feat" / "my-feature"
        with patch("os.getcwd", return_value=str(worktree)):
            result = hook.process(self._make_input(f"rm -rf {worktree}"))
            assert result.get("block") is True

    def test_allows_worktree_cleanup_not_cwd(self, tmp_path):
        """Worktree cleanup should be allowed if target is NOT the CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        cwd = tmp_path / "worktrees" / "feat" / "current"
        other = tmp_path / "worktrees" / "feat" / "other-branch"
        with patch("os.getcwd", return_value=str(cwd)):
            result = hook.process(self._make_input(f"rm -rf {other}"))
            assert result.get("block") is not True

    def test_trailing_slash_handled(self, tmp_path):
        """rm -rf /path/to/dir/ (trailing slash) should still be caught."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "work")):
            result = hook.process(self._make_input(f"rm -rf {tmp_path / 'work'}/"))
            assert result.get("block") is True


# ============================================================================
# UNIT TESTS - CWD Rename/Move Detection
# ============================================================================


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

        parent = tmp_path / "parent"
        parent.mkdir()
        child = parent / "child"
        child.mkdir()

        with patch("os.getcwd", return_value=str(child)):
            result = hook._check_cwd_rename(f"mv {tmp_path}/par* /tmp/newname")

        assert result.get("block") is True

    def test_allows_mv_with_glob_unrelated_to_cwd(self, tmp_path):
        """Should allow mv with glob pattern that can't affect CWD."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

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
            result = hook._check_cwd_rename(f"echo hello && mv {tmp_path} /tmp/new")
            assert result.get("block") is True

            result = hook._check_cwd_rename(f"echo hello; mv {tmp_path} /tmp/new")
            assert result.get("block") is True

    def test_handles_inaccessible_cwd(self, tmp_path):
        """Should handle case when CWD is inaccessible."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", side_effect=OSError("CWD deleted")):
            result = hook._check_cwd_rename("mv /some/path /other/path")

        assert result == {}


# ============================================================================
# UNIT TESTS - mv Path Extraction
# ============================================================================


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


# ============================================================================
# UNIT TESTS - mv Regex
# ============================================================================


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


# ============================================================================
# INTEGRATION TESTS - mv Protection via Full Hook
# ============================================================================


class TestCwdRenameFullHook:
    """Integration tests verifying mv/rename protection works in full hook flow."""

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

        with patch("os.getcwd", return_value=str(tmp_path)):
            result = hook._check_cwd_rename(f"mv {other} {tmp_path} /dest/")

        assert result.get("block") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
