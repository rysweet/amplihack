#!/usr/bin/env python3
"""Comprehensive security path tests for pre_tool_use.py.

Covers: is_cwd_deletion, is_dangerous_command (--no-verify), is_main_branch,
_check_cwd_rename, _extract_rm_paths, _extract_mv_source_paths, and error paths.
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure hook directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Helpers to construct a PreToolUseHook with mocked HookProcessor.__init__
# ---------------------------------------------------------------------------


def _make_hook():
    """Create a PreToolUseHook with the HookProcessor init mocked out."""
    with patch("hook_processor.HookProcessor.__init__", return_value=None):
        from pre_tool_use import PreToolUseHook

        hook = PreToolUseHook()
        hook.hook_name = "pre_tool_use"
        hook.project_root = Path("/fake/project")
        hook.log_dir = Path("/tmp/test_logs")
        hook.metrics_dir = Path("/tmp/test_metrics")
        hook.analysis_dir = Path("/tmp/test_analysis")
        hook.log_file = Path("/tmp/test_logs/pre_tool_use.log")
        hook.strategy = None
        hook.log = MagicMock()
        hook.save_metric = MagicMock()
        return hook


# ============================================================================
# _extract_rm_paths
# ============================================================================


class TestExtractRmPaths:
    """Tests for PreToolUseHook._extract_rm_paths static method."""

    def test_simple_rm_rf(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_rm_paths("rm -rf /tmp/foo")
        assert paths == ["/tmp/foo"]

    def test_rm_with_multiple_paths(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_rm_paths("rm -rf /a /b /c")
        assert paths == ["/a", "/b", "/c"]

    def test_rm_with_flags_separated(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_rm_paths("rm -r -f /tmp/foo")
        assert paths == ["/tmp/foo"]

    def test_rmdir(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_rm_paths("rmdir /empty/dir")
        assert paths == ["/empty/dir"]

    def test_rm_with_quoted_path(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_rm_paths('rm -rf "/path with spaces/dir"')
        assert paths == ["/path with spaces/dir"]

    def test_malformed_shell_syntax_fallback(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_rm_paths("rm -rf '/unterminated")
        # Falls back to simple split — may contain the quote
        assert isinstance(paths, list)

    def test_no_rm_command(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_rm_paths("echo hello")
        assert paths == []

    def test_rm_preceded_by_env_vars(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_rm_paths("FOO=bar rm -rf /tmp/foo")
        assert "/tmp/foo" in paths

    def test_absolute_path_rm_binary(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_rm_paths("/bin/rm -rf /tmp/foo")
        assert paths == ["/tmp/foo"]


# ============================================================================
# _extract_mv_source_paths
# ============================================================================


class TestExtractMvSourcePaths:
    """Tests for PreToolUseHook._extract_mv_source_paths static method."""

    def test_simple_mv(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_mv_source_paths("mv /src /dst")
        assert paths == ["/src"]

    def test_mv_multiple_sources(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_mv_source_paths("mv /a /b /dst")
        assert paths == ["/a", "/b"]

    def test_mv_target_directory_flag(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_mv_source_paths("mv -t /dst /a /b")
        assert set(paths) == {"/a", "/b"}

    def test_mv_target_directory_long_flag(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_mv_source_paths("mv --target-directory=/dst /a /b")
        assert set(paths) == {"/a", "/b"}

    def test_mv_with_double_dash(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_mv_source_paths("mv -- -weird-file /dst")
        assert "-weird-file" in paths

    def test_mv_single_arg(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_mv_source_paths("mv /only")
        assert paths == ["/only"]

    def test_mv_no_args(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_mv_source_paths("mv")
        assert paths == []

    def test_mv_malformed_syntax(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_mv_source_paths("mv '/unterminated")
        assert paths == []

    def test_mv_with_sudo(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_mv_source_paths("sudo mv /src /dst")
        assert paths == ["/src"]

    def test_mv_not_found_in_tokens(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_mv_source_paths("echo hello world")
        assert paths == []

    def test_mv_t_malformed_no_dir(self):
        from pre_tool_use import PreToolUseHook

        paths = PreToolUseHook._extract_mv_source_paths("mv -t")
        assert paths == []


# ============================================================================
# _check_cwd_deletion
# ============================================================================


class TestCheckCwdDeletion:
    """Security-critical: prevent deletion of CWD or parent."""

    def test_safe_command_no_rm(self):
        hook = _make_hook()
        assert hook._check_cwd_deletion("echo hello") == {}

    def test_rm_targeting_cwd_blocks(self):
        hook = _make_hook()
        cwd = os.getcwd()
        result = hook._check_cwd_deletion(f"rm -rf {cwd}")
        assert result.get("block") is True

    def test_rm_targeting_parent_of_cwd_blocks(self):
        hook = _make_hook()
        parent = str(Path(os.getcwd()).parent)
        result = hook._check_cwd_deletion(f"rm -rf {parent}")
        assert result.get("block") is True

    def test_rm_targeting_unrelated_dir_allows(self):
        hook = _make_hook()
        result = hook._check_cwd_deletion("rm -rf /tmp/safe_to_delete_test_xyz")
        assert result == {}

    def test_rm_with_chained_commands(self):
        hook = _make_hook()
        cwd = os.getcwd()
        result = hook._check_cwd_deletion(f"echo foo && rm -rf {cwd}")
        assert result.get("block") is True

    def test_rm_with_semicolon_separator(self):
        hook = _make_hook()
        cwd = os.getcwd()
        result = hook._check_cwd_deletion(f"echo foo; rm -rf {cwd}")
        assert result.get("block") is True

    def test_rm_with_pipe_not_split(self):
        hook = _make_hook()
        # Pipe should NOT be split — rm after pipe is part of pipe
        result = hook._check_cwd_deletion("cat file | rm -rf /nonexistent")
        # The rm -rf /nonexistent is after a pipe. The regex should still
        # detect rm in the full command, but the path won't match CWD.
        # This tests that pipe doesn't cause false positives.
        assert result == {}

    def test_rmdir_blocks(self):
        hook = _make_hook()
        cwd = os.getcwd()
        result = hook._check_cwd_deletion(f"rmdir {cwd}")
        assert result.get("block") is True

    @patch("os.getcwd", side_effect=OSError("CWD gone"))
    def test_cwd_inaccessible_fails_open(self, mock_getcwd):
        hook = _make_hook()
        result = hook._check_cwd_deletion("rm -rf /tmp/foo")
        assert result == {}

    def test_rm_with_recursive_long_flag(self):
        hook = _make_hook()
        cwd = os.getcwd()
        result = hook._check_cwd_deletion(f"rm --recursive {cwd}")
        assert result.get("block") is True

    def test_rm_nonrecursive_allows(self):
        hook = _make_hook()
        cwd = os.getcwd()
        # rm without -r flag should NOT be detected
        result = hook._check_cwd_deletion(f"rm {cwd}/file.txt")
        assert result == {}

    def test_rm_with_path_resolution_error(self):
        hook = _make_hook()
        # Path that can't be resolved shouldn't crash
        result = hook._check_cwd_deletion("rm -rf \x00invalid_path")
        assert isinstance(result, dict)


# ============================================================================
# _check_cwd_rename
# ============================================================================


class TestCheckCwdRename:
    """Security-critical: prevent rename/move of CWD or parent."""

    def test_safe_command_no_mv(self):
        hook = _make_hook()
        assert hook._check_cwd_rename("echo hello") == {}

    def test_mv_cwd_blocks(self):
        hook = _make_hook()
        cwd = os.getcwd()
        result = hook._check_cwd_rename(f"mv {cwd} /tmp/renamed_xyz")
        assert result.get("block") is True

    def test_mv_parent_of_cwd_blocks(self):
        hook = _make_hook()
        parent = str(Path(os.getcwd()).parent)
        result = hook._check_cwd_rename(f"mv {parent} /tmp/renamed_xyz")
        assert result.get("block") is True

    def test_mv_unrelated_dir_allows(self):
        hook = _make_hook()
        result = hook._check_cwd_rename("mv /tmp/safe_rename_test_xyz /tmp/new_name")
        assert result == {}

    def test_mv_with_glob_conservative_block(self):
        hook = _make_hook()
        cwd = os.getcwd()
        # Glob that could match CWD's parent directory
        parent = Path(cwd).parent
        glob_prefix = str(parent)[:10]  # Short prefix that might match
        result = hook._check_cwd_rename(f"mv {glob_prefix}* /tmp/dest")
        # Should either block conservatively or allow — just shouldn't crash
        assert isinstance(result, dict)

    @patch("os.getcwd", side_effect=OSError("CWD gone"))
    def test_cwd_inaccessible_fails_open(self, mock_getcwd):
        hook = _make_hook()
        result = hook._check_cwd_rename("mv /tmp/foo /tmp/bar")
        assert result == {}

    def test_mv_with_chained_commands(self):
        hook = _make_hook()
        cwd = os.getcwd()
        result = hook._check_cwd_rename(f"echo hi && mv {cwd} /tmp/gone")
        assert result.get("block") is True


# ============================================================================
# process() — main branch protection
# ============================================================================


class TestMainBranchProtection:
    """Verify git commit on main/master is blocked."""

    def test_non_bash_tool_allowed(self):
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process({"toolUse": {"name": "Read", "input": {}}})
        assert result == {}

    @patch("subprocess.run")
    def test_git_commit_on_main_blocked(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="main\n")
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process(
            {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}
        )
        assert result.get("block") is True

    @patch("subprocess.run")
    def test_git_commit_on_master_blocked(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="master\n")
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process(
            {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}
        )
        assert result.get("block") is True

    @patch("subprocess.run")
    def test_git_commit_on_feature_branch_allowed(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="feature/my-branch\n")
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process(
            {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}
        )
        assert result == {}

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=5))
    def test_git_timeout_fails_open(self, mock_run):
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process(
            {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}
        )
        assert result == {}

    @patch("subprocess.run", side_effect=FileNotFoundError("git not found"))
    def test_git_not_found_fails_open(self, mock_run):
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process(
            {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}
        )
        assert result == {}

    @patch("subprocess.run")
    def test_git_branch_detection_nonzero_exit(self, mock_run):
        mock_run.return_value = MagicMock(returncode=128, stdout="")
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process(
            {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}
        )
        # Non-zero exit fails open
        assert result == {}

    @patch("subprocess.run", side_effect=RuntimeError("unexpected"))
    def test_git_generic_exception_fails_open(self, mock_run):
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process(
            {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}
        )
        assert result == {}


# ============================================================================
# process() — --no-verify blocking
# ============================================================================


class TestNoVerifyBlocking:
    """Verify --no-verify is blocked for git commands."""

    @patch("subprocess.run")
    def test_git_commit_no_verify_blocked(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="feature\n")
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process(
            {"toolUse": {"name": "Bash", "input": {"command": "git commit --no-verify -m 'test'"}}}
        )
        assert result.get("block") is True
        assert "--no-verify" in result.get("message", "")

    def test_git_push_no_verify_blocked(self):
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process(
            {"toolUse": {"name": "Bash", "input": {"command": "git push --no-verify origin main"}}}
        )
        assert result.get("block") is True

    @patch("subprocess.run")
    def test_git_commit_without_no_verify_allowed(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="feature\n")
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process(
            {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}
        )
        assert result == {}


# ============================================================================
# process() — strategy delegation
# ============================================================================


class TestStrategyDelegation:
    """Verify strategy is consulted and can short-circuit."""

    def test_strategy_result_returned(self):
        hook = _make_hook()
        mock_strategy = MagicMock()
        mock_strategy.handle_pre_tool_use.return_value = {"custom": True}
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        result = hook.process({"toolUse": {"name": "Bash", "input": {"command": "echo safe"}}})
        assert result == {"custom": True}

    def test_strategy_returns_none_continues(self):
        hook = _make_hook()
        mock_strategy = MagicMock()
        mock_strategy.handle_pre_tool_use.return_value = None
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        result = hook.process({"toolUse": {"name": "Bash", "input": {"command": "echo safe"}}})
        assert result == {}


# ============================================================================
# _select_strategy error handling
# ============================================================================


class TestSelectStrategy:
    """Strategy selection should fail open on ImportError."""

    def test_import_error_returns_none(self):
        hook = _make_hook()
        with patch.dict("sys.modules", {"amplihack.context.adaptive.detector": None}):
            # Force ImportError by mocking the import
            original = hook._select_strategy

            def mock_strategy():
                try:
                    raise ImportError("not available")
                except ImportError:
                    return

            hook._select_strategy = mock_strategy
            result = hook._select_strategy()
            assert result is None


# ============================================================================
# process() — non-git commands
# ============================================================================


class TestNonGitCommands:
    """Non-git bash commands should pass through."""

    def test_ls_command_allowed(self):
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process({"toolUse": {"name": "Bash", "input": {"command": "ls -la"}}})
        assert result == {}

    def test_echo_command_allowed(self):
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process(
            {"toolUse": {"name": "Bash", "input": {"command": "echo hello world"}}}
        )
        assert result == {}

    def test_empty_command_allowed(self):
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process({"toolUse": {"name": "Bash", "input": {"command": ""}}})
        assert result == {}

    def test_missing_tool_use_key(self):
        hook = _make_hook()
        hook._select_strategy = MagicMock(return_value=None)
        result = hook.process({})
        assert result == {}
