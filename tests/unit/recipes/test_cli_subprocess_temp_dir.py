"""Tests for CLISubprocessAdapter temp directory isolation (#2758).

When the recipe runner's CLISubprocessAdapter runs agent steps inside a nested
Claude Code session, it must use a temporary working directory to avoid file
write races on sessions.jsonl, settings.json, and Blarify indexing.

These tests verify:
1. Agent steps use a temp directory instead of the parent working directory.
2. Session tree env vars are propagated to child processes.
3. Temp directories are cleaned up after execution.
4. Bash steps also get session tree env var propagation.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter


class TestAgentStepTempDirIsolation:
    """Verify agent steps run in an isolated temp directory (#2758)."""

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_agent_step_uses_temp_dir(self, mock_popen: MagicMock, tmp_path: Path) -> None:
        """Agent step cwd should be a temp directory, not the parent working dir."""
        mock_proc = MagicMock()
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        adapter = CLISubprocessAdapter()

        with patch("amplihack.recipes.adapters.cli_subprocess.Path") as mock_path_cls:
            mock_output_dir = MagicMock()
            mock_output_file = MagicMock()
            mock_output_file.read_text.return_value = "output text"
            mock_output_dir.__truediv__ = MagicMock(return_value=mock_output_file)
            mock_output_dir.iterdir.return_value = iter([])
            mock_path_instance = MagicMock()
            mock_path_instance.__truediv__ = MagicMock(return_value=mock_output_dir)
            mock_path_cls.return_value = mock_path_instance

            adapter.execute_agent_step("Do something", working_dir=str(tmp_path))

        # The cwd passed to Popen should NOT be the parent working_dir
        popen_kwargs = mock_popen.call_args[1]
        actual_cwd = popen_kwargs.get("cwd")
        assert actual_cwd != str(tmp_path), (
            f"Agent step cwd should be a temp dir, not the parent working dir {tmp_path}"
        )
        # It should be a temp directory path
        assert actual_cwd is not None
        assert "recipe-agent-" in str(actual_cwd), (
            f"Expected temp dir with 'recipe-agent-' prefix, got: {actual_cwd}"
        )


class TestSessionTreeEnvPropagation:
    """Verify session tree env vars are propagated to child processes."""

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_agent_step_propagates_session_tree_vars(
        self, mock_popen: MagicMock, tmp_path: Path
    ) -> None:
        """Agent step child env should include session tree context."""
        mock_proc = MagicMock()
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        adapter = CLISubprocessAdapter()

        # Set up env vars that should be propagated
        test_env = {
            "AMPLIHACK_TREE_ID": "test-tree-123",
            "AMPLIHACK_SESSION_DEPTH": "1",
            "AMPLIHACK_MAX_DEPTH": "5",
            "AMPLIHACK_MAX_SESSIONS": "8",
        }

        with (
            patch.dict(os.environ, test_env, clear=False),
            patch("amplihack.recipes.adapters.cli_subprocess.Path") as mock_path_cls,
        ):
            mock_output_dir = MagicMock()
            mock_output_file = MagicMock()
            mock_output_file.read_text.return_value = "done"
            mock_output_dir.__truediv__ = MagicMock(return_value=mock_output_file)
            mock_output_dir.iterdir.return_value = iter([])
            mock_path_instance = MagicMock()
            mock_path_instance.__truediv__ = MagicMock(return_value=mock_output_dir)
            mock_path_cls.return_value = mock_path_instance

            adapter.execute_agent_step("Task", working_dir=str(tmp_path))

        child_env = mock_popen.call_args[1].get("env", {})

        # Tree ID should be propagated
        assert child_env.get("AMPLIHACK_TREE_ID") == "test-tree-123"
        # Depth should be incremented by 1
        assert child_env.get("AMPLIHACK_SESSION_DEPTH") == "2"
        # Limits should be passed through
        assert child_env.get("AMPLIHACK_MAX_DEPTH") == "5"
        assert child_env.get("AMPLIHACK_MAX_SESSIONS") == "8"

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_agent_step_generates_tree_id_when_missing(
        self, mock_popen: MagicMock, tmp_path: Path
    ) -> None:
        """When no AMPLIHACK_TREE_ID is set, one should be generated."""
        mock_proc = MagicMock()
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        adapter = CLISubprocessAdapter()

        # Ensure no tree ID is set
        env_without_tree = {
            k: v
            for k, v in os.environ.items()
            if k not in ("AMPLIHACK_TREE_ID", "AMPLIHACK_SESSION_DEPTH")
        }

        with (
            patch.dict(os.environ, env_without_tree, clear=True),
            patch("amplihack.recipes.adapters.cli_subprocess.Path") as mock_path_cls,
        ):
            mock_output_dir = MagicMock()
            mock_output_file = MagicMock()
            mock_output_file.read_text.return_value = "done"
            mock_output_dir.__truediv__ = MagicMock(return_value=mock_output_file)
            mock_output_dir.iterdir.return_value = iter([])
            mock_path_instance = MagicMock()
            mock_path_instance.__truediv__ = MagicMock(return_value=mock_output_dir)
            mock_path_cls.return_value = mock_path_instance

            adapter.execute_agent_step("Task", working_dir=str(tmp_path))

        child_env = mock_popen.call_args[1].get("env", {})

        # A tree ID should have been generated
        assert "AMPLIHACK_TREE_ID" in child_env
        assert len(child_env["AMPLIHACK_TREE_ID"]) > 0
        # Depth should be "1" (0 + 1)
        assert child_env.get("AMPLIHACK_SESSION_DEPTH") == "1"

    @patch("subprocess.run")
    def test_bash_step_propagates_session_tree_vars(self, mock_run: MagicMock) -> None:
        """Bash step child env should include session tree context."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        adapter = CLISubprocessAdapter()

        test_env = {
            "AMPLIHACK_TREE_ID": "bash-tree-456",
            "AMPLIHACK_SESSION_DEPTH": "2",
            "AMPLIHACK_MAX_DEPTH": "4",
            "AMPLIHACK_MAX_SESSIONS": "6",
        }

        with patch.dict(os.environ, test_env, clear=False):
            adapter.execute_bash_step("echo test")

        child_env = mock_run.call_args[1].get("env", {})

        # Session tree vars should be propagated (depth incremented)
        assert child_env.get("AMPLIHACK_TREE_ID") == "bash-tree-456"
        assert child_env.get("AMPLIHACK_SESSION_DEPTH") == "3"
        assert child_env.get("AMPLIHACK_MAX_DEPTH") == "4"
        assert child_env.get("AMPLIHACK_MAX_SESSIONS") == "6"


class TestTempDirCleanup:
    """Verify temp directories are cleaned up after agent step execution."""

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_temp_dir_cleaned_up_on_success(self, mock_popen: MagicMock, tmp_path: Path) -> None:
        """Temp dir should be removed after successful agent step."""
        mock_proc = MagicMock()
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        adapter = CLISubprocessAdapter()

        # Track what temp dirs get created
        created_dirs: list[str] = []
        original_mkdtemp = tempfile.mkdtemp

        def tracking_mkdtemp(**kwargs):
            d = original_mkdtemp(**kwargs)
            created_dirs.append(d)
            return d

        with (
            patch(
                "amplihack.recipes.adapters.cli_subprocess.tempfile.mkdtemp",
                side_effect=tracking_mkdtemp,
            ),
            patch("amplihack.recipes.adapters.cli_subprocess.Path") as mock_path_cls,
        ):
            mock_output_dir = MagicMock()
            mock_output_file = MagicMock()
            mock_output_file.read_text.return_value = "output"
            mock_output_dir.__truediv__ = MagicMock(return_value=mock_output_file)
            mock_output_dir.iterdir.return_value = iter([])
            mock_path_instance = MagicMock()
            mock_path_instance.__truediv__ = MagicMock(return_value=mock_output_dir)
            mock_path_cls.return_value = mock_path_instance

            adapter.execute_agent_step("Task", working_dir=str(tmp_path))

        # The temp dir should have been created
        assert len(created_dirs) == 1
        # And should be cleaned up (not exist anymore)
        assert not os.path.exists(created_dirs[0]), (
            f"Temp dir {created_dirs[0]} should have been cleaned up"
        )

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_temp_dir_cleaned_up_on_failure(self, mock_popen: MagicMock, tmp_path: Path) -> None:
        """Temp dir should be removed even when agent step fails."""
        mock_proc = MagicMock()
        mock_proc.wait.return_value = None
        mock_proc.returncode = 1  # Failure
        mock_popen.return_value = mock_proc

        adapter = CLISubprocessAdapter()

        created_dirs: list[str] = []
        original_mkdtemp = tempfile.mkdtemp

        def tracking_mkdtemp(**kwargs):
            d = original_mkdtemp(**kwargs)
            created_dirs.append(d)
            return d

        with (
            patch(
                "amplihack.recipes.adapters.cli_subprocess.tempfile.mkdtemp",
                side_effect=tracking_mkdtemp,
            ),
            patch("amplihack.recipes.adapters.cli_subprocess.Path") as mock_path_cls,
        ):
            mock_output_dir = MagicMock()
            mock_output_file = MagicMock()
            mock_output_file.read_text.return_value = "error output"
            mock_output_dir.__truediv__ = MagicMock(return_value=mock_output_file)
            mock_output_dir.iterdir.return_value = iter([])
            mock_path_instance = MagicMock()
            mock_path_instance.__truediv__ = MagicMock(return_value=mock_output_dir)
            mock_path_cls.return_value = mock_path_instance

            with pytest.raises(RuntimeError):
                adapter.execute_agent_step("Fail task", working_dir=str(tmp_path))

        # Temp dir should still be cleaned up
        assert len(created_dirs) == 1
        assert not os.path.exists(created_dirs[0]), (
            f"Temp dir {created_dirs[0]} should have been cleaned up on failure"
        )


class TestCLAUDECODEEnvRemoval:
    """Verify CLAUDECODE is still removed from child environment."""

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_claudecode_removed_from_agent_env(self, mock_popen: MagicMock, tmp_path: Path) -> None:
        """CLAUDECODE env var must not be passed to child agent processes."""
        mock_proc = MagicMock()
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        adapter = CLISubprocessAdapter()

        with (
            patch.dict(os.environ, {"CLAUDECODE": "1"}, clear=False),
            patch("amplihack.recipes.adapters.cli_subprocess.Path") as mock_path_cls,
        ):
            mock_output_dir = MagicMock()
            mock_output_file = MagicMock()
            mock_output_file.read_text.return_value = "done"
            mock_output_dir.__truediv__ = MagicMock(return_value=mock_output_file)
            mock_output_dir.iterdir.return_value = iter([])
            mock_path_instance = MagicMock()
            mock_path_instance.__truediv__ = MagicMock(return_value=mock_output_dir)
            mock_path_cls.return_value = mock_path_instance

            adapter.execute_agent_step("Task", working_dir=str(tmp_path))

        child_env = mock_popen.call_args[1].get("env", {})
        assert "CLAUDECODE" not in child_env

    @patch("subprocess.run")
    def test_claudecode_removed_from_bash_env(self, mock_run: MagicMock) -> None:
        """CLAUDECODE env var must not be passed to child bash processes."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        adapter = CLISubprocessAdapter()

        with patch.dict(os.environ, {"CLAUDECODE": "1"}, clear=False):
            adapter.execute_bash_step("echo test")

        child_env = mock_run.call_args[1].get("env", {})
        assert "CLAUDECODE" not in child_env
