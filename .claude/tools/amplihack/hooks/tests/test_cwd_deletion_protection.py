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

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add hooks directory to path for imports
hooks_dir = Path(__file__).parent.parent
sys.path.insert(0, str(hooks_dir))

from pre_tool_use import PreToolUseHook


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
            result = hook.process(
                self._make_input(f"cd / && rm -rf {tmp_path / 'work'}")
            )
            assert result.get("block") is True

    def test_blocks_piped_rm_rf_cwd(self, tmp_path):
        """rm -rf CWD in a piped command must be blocked."""
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("os.getcwd", return_value=str(tmp_path / "work")):
            result = hook.process(
                self._make_input(f"echo yes | rm -rf {tmp_path / 'work'}")
            )
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

        result = hook.process(
            {"toolUse": {"name": "Read", "input": {"file_path": "/some/file"}}}
        )
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
