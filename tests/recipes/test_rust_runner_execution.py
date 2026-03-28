"""Tests for Rust runner command execution and streamed output handling."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.recipes.models import RecipeResult, StepStatus
from amplihack.recipes.rust_runner import RustRunnerNotFoundError, run_recipe_via_rust
from amplihack.recipes.rust_runner_execution import _write_progress_file


@pytest.fixture(autouse=True)
def _mock_runner_version_check():
    """Keep execution tests focused on command/response behavior, not version gating."""
    with patch(
        "amplihack.recipes.rust_runner.runner_binary.raise_for_runner_version",
        return_value=None,
    ):
        yield


class TestRunRecipeViaRust:
    """Tests for run_recipe_via_rust()."""

    def _make_rust_output(self, *, success=True, steps=None):
        """Helper to create valid Rust binary JSON output."""
        if steps is None:
            steps = [
                {"step_id": "s1", "status": "Completed", "output": "hello", "error": ""},
            ]
        return json.dumps(
            {
                "recipe_name": "test-recipe",
                "success": success,
                "step_results": steps,
                "context": {"result": "done"},
            }
        )

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value=None)
    def test_raises_when_binary_missing(self, mock_find):
        with pytest.raises(RustRunnerNotFoundError, match="recipe-runner-rs binary not found"):
            run_recipe_via_rust("test-recipe")

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_successful_execution(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        result = run_recipe_via_rust("test-recipe")
        assert result.success is True
        assert result.recipe_name == "test-recipe"
        assert len(result.step_results) == 1
        assert result.step_results[0].step_id == "s1"
        assert result.step_results[0].status == StepStatus.COMPLETED

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_passes_dry_run_flag(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust("test-recipe", dry_run=True)
        cmd = mock_run.call_args[0][0]
        assert "--dry-run" in cmd

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_passes_no_auto_stage_flag(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust("test-recipe", auto_stage=False)
        cmd = mock_run.call_args[0][0]
        assert "--no-auto-stage" in cmd

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    @patch(
        "amplihack.recipes.discovery.find_recipe",
        return_value=Path("/recipes/default-workflow.yaml"),
    )
    def test_resolves_recipe_name_to_path(self, mock_find_recipe, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust("default-workflow")
        cmd = mock_run.call_args[0][0]
        assert cmd[1] == "/recipes/default-workflow.yaml"

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_passes_recipe_dirs(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust("test-recipe", recipe_dirs=["/a", "/b"])
        cmd = mock_run.call_args[0][0]
        assert "-R" in cmd
        idx = cmd.index("-R")
        assert cmd[idx + 1] == "/a"

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_normalizes_relative_recipe_dirs_against_working_dir(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust(
            "test-recipe",
            recipe_dirs=["amplifier-bundle/recipes"],
            working_dir="/repo/worktree",
        )
        cmd = mock_run.call_args[0][0]
        idx = cmd.index("-R")
        assert cmd[idx + 1] == "/repo/worktree/amplifier-bundle/recipes"

    @patch.dict("os.environ", {"AMPLIHACK_AGENT_BINARY": "copilot"}, clear=False)
    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_does_not_pass_agent_binary_flag(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust("test-recipe")
        cmd = mock_run.call_args[0][0]
        assert "--agent-binary" not in cmd

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_passes_context_values(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust(
            "test-recipe",
            user_context={
                "name": "world",
                "verbose": True,
                "data": {"key": "val"},
            },
        )
        cmd = mock_run.call_args[0][0]
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        assert "name=world" in set_args
        assert "verbose=true" in set_args
        assert any('"key"' in a for a in set_args)

    @patch.dict("os.environ", {"PATH": "/usr/bin", "PYTHONPATH": "/repo/src"}, clear=True)
    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_forwards_pythonpath_and_seeds_claude_project_dir(
        self, mock_run, mock_find
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )

        run_recipe_via_rust("test-recipe", working_dir="/repo/worktree")

        env = mock_run.call_args.kwargs["env"]
        assert env["PYTHONPATH"] == "/repo/src"
        assert env["CLAUDE_PROJECT_DIR"] == "/repo/worktree"

    @patch.dict(
        "os.environ",
        {"PATH": "/usr/bin", "CLAUDE_PROJECT_DIR": "/already/set"},
        clear=True,
    )
    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_preserves_existing_claude_project_dir(self, mock_run, mock_find):
        """When CLAUDE_PROJECT_DIR is already set, _project_dir_context is a no-op."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )

        run_recipe_via_rust("test-recipe", working_dir="/different/dir")

        env = mock_run.call_args.kwargs["env"]
        assert env["CLAUDE_PROJECT_DIR"] == "/already/set"

    @patch.dict(
        "os.environ",
        {"PATH": "/usr/bin", "CLAUDE_PROJECT_DIR": ""},
        clear=True,
    )
    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_preserves_empty_string_claude_project_dir(self, mock_run, mock_find):
        """Empty string CLAUDE_PROJECT_DIR must be preserved, not overwritten."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )

        run_recipe_via_rust("test-recipe", working_dir="/some/dir")

        env = mock_run.call_args.kwargs["env"]
        assert env["CLAUDE_PROJECT_DIR"] == ""

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_no_run_timeout(self, mock_run, mock_find):
        """Issue #3049: subprocess.run must NOT impose a timeout on recipe execution."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust("test-recipe")
        assert "timeout" not in mock_run.call_args[1], (
            "subprocess.run should not have a timeout kwarg — "
            "the Rust binary manages its own per-step timeouts"
        )

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_nonzero_exit_with_bad_json_raises(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="not json",
            stderr="error: recipe failed",
        )
        with pytest.raises(RuntimeError, match="Rust recipe runner failed"):
            run_recipe_via_rust("test-recipe")

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_signal_kill_raises_clear_message(self, mock_run, mock_find):
        """Exit code -15 (SIGTERM) should produce a clear 'killed by signal' message."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=-15,
            stdout="",
            stderr="▶ step-01\n  [agent] ... working\n  ✓ step-01",
        )
        with pytest.raises(RuntimeError, match="killed by signal SIGTERM"):
            run_recipe_via_rust("test-recipe")

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_zero_exit_with_bad_json_raises(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="not json at all",
            stderr="",
        )
        with pytest.raises(RuntimeError, match="unparseable output"):
            run_recipe_via_rust("test-recipe")

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_status_mapping(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(
                steps=[
                    {"step_id": "a", "status": "Completed", "output": "", "error": ""},
                    {"step_id": "b", "status": "Skipped", "output": "", "error": ""},
                    {"step_id": "c", "status": "Failed", "output": "", "error": "boom"},
                    {"step_id": "d", "status": "unknown_status", "output": "", "error": ""},
                ]
            ),
            stderr="",
        )
        result = run_recipe_via_rust("test-recipe")
        assert result.step_results[0].status == StepStatus.COMPLETED
        assert result.step_results[1].status == StepStatus.SKIPPED
        assert result.step_results[2].status == StepStatus.FAILED
        assert result.step_results[3].status == StepStatus.FAILED  # unknown → FAILED

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_empty_step_results(self, mock_run, mock_find):
        """PR-M5: Empty step_results produces a valid RecipeResult with no steps."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(steps=[]),
            stderr="",
        )
        result = run_recipe_via_rust("test-recipe")
        assert result.step_results == []
        assert result.recipe_name == "test-recipe"

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_invalid_step_results_type_raises(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "recipe_name": "test-recipe",
                    "success": True,
                    "step_results": "not-a-list",
                    "context": {"result": "done"},
                }
            ),
            stderr="",
        )

        with pytest.raises(RuntimeError, match="step_results"):
            run_recipe_via_rust("test-recipe")

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_invalid_success_type_raises(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "recipe_name": "test-recipe",
                    "success": "false",
                    "step_results": [],
                    "context": {"result": "done"},
                }
            ),
            stderr="",
        )

        with pytest.raises(RuntimeError, match="success"):
            run_recipe_via_rust("test-recipe")

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_invalid_step_result_entry_raises(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "recipe_name": "test-recipe",
                    "success": True,
                    "step_results": ["bad-entry"],
                    "context": {"result": "done"},
                }
            ),
            stderr="",
        )

        with pytest.raises(RuntimeError, match=r"step_results\[0\]"):
            run_recipe_via_rust("test-recipe")

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_invalid_context_type_raises(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "recipe_name": "test-recipe",
                    "success": True,
                    "step_results": [],
                    "context": ["bad-context"],
                }
            ),
            stderr="",
        )

        with pytest.raises(RuntimeError, match="context"):
            run_recipe_via_rust("test-recipe")

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run", side_effect=OSError("No such file or directory"))
    def test_oserror_during_subprocess(self, mock_run, mock_find):
        """PR-M5: OSError during subprocess.run propagates cleanly."""
        with pytest.raises(OSError, match="No such file or directory"):
            run_recipe_via_rust("test-recipe")


class TestProgressStreaming:
    """Issue #3024: progress mode should stream stderr instead of buffering it."""

    @staticmethod
    def _make_rust_output() -> str:
        return json.dumps(
            {
                "recipe_name": "test-recipe",
                "success": True,
                "step_results": [
                    {"step_id": "s1", "status": "Completed", "output": "hello", "error": ""},
                ],
                "context": {"result": "done"},
            }
        )

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.Popen")
    def test_progress_mode_streams_stderr(self, mock_popen, mock_find):
        class FakePopen:
            def __init__(self, stdout: str, stderr: str, returncode: int = 0):
                self.stdout = io.StringIO(stdout)
                self.stderr = io.StringIO(stderr)
                self._returncode = returncode
                self.timeout = None

            def wait(self, timeout=None):
                self.timeout = timeout
                return self._returncode

        fake = FakePopen(
            stdout=self._make_rust_output(),
            stderr="▶ classify-and-decompose (agent)\n  [agent] still running\n",
        )
        mock_popen.return_value = fake

        streamed_stderr = io.StringIO()
        with patch.object(sys, "stderr", streamed_stderr):
            result = run_recipe_via_rust("test-recipe", progress=True)

        cmd = mock_popen.call_args[0][0]
        assert "--progress" in cmd
        assert result.success is True
        assert "▶ classify-and-decompose" in streamed_stderr.getvalue()
        # Issue #3049: no timeout should be passed to process.wait()
        assert fake.timeout is None

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.Popen")
    def test_progress_mode_writes_progress_file(self, mock_popen, mock_find, tmp_path):
        """Verify that progress markers in stderr cause progress files to be written.

        Note: run_recipe_via_rust cleans up the progress file on completion,
        so we intercept _write_progress_file to capture what was written.
        """

        class FakePopen:
            def __init__(self, stdout: str, stderr: str, returncode: int = 0):
                self.stdout = io.StringIO(stdout)
                self.stderr = io.StringIO(stderr)
                self._returncode = returncode

            def wait(self, timeout=None):
                return self._returncode

        mock_popen.return_value = FakePopen(
            stdout=self._make_rust_output(),
            stderr="▶ classify-and-decompose (agent)\n✓ classify-and-decompose\n",
        )

        written_payloads: list[dict] = []
        original_write = _write_progress_file

        def capture_write(*args, **kwargs):
            path = original_write(*args, **kwargs)
            if path.exists():
                written_payloads.append(json.loads(path.read_text(encoding="utf-8")))
            return path

        with (
            patch(
                "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                return_value=str(tmp_path),
            ),
            patch(
                "amplihack.recipes.rust_runner_execution._write_progress_file",
                side_effect=capture_write,
            ),
        ):
            run_recipe_via_rust("smart-orchestrator", progress=True)

        assert len(written_payloads) >= 1
        # The last payload should be the "completed" state
        last = written_payloads[-1]
        assert last["recipe_name"] == "smart-orchestrator"
        assert last["current_step"] == 1
        assert last["step_name"] == "classify-and-decompose"
        assert last["status"] == "completed"


class TestRecipeLogPath:
    """Tests for _recipe_log_path() — the persistent log file path helper."""

    def test_returns_path_in_tmp(self, tmp_path):
        from amplihack.recipes.rust_runner_execution import _recipe_log_path

        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            path = _recipe_log_path("smart-orchestrator", pid=42)
        assert path.parent == tmp_path
        assert "amplihack-recipe-" in path.name
        assert "42" in path.name
        assert path.suffix == ".log"

    def test_sanitizes_recipe_name(self, tmp_path):
        from amplihack.recipes.rust_runner_execution import _recipe_log_path

        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            path = _recipe_log_path("my/weird recipe!", pid=1)
        # Slashes and spaces are sanitized; only [a-zA-Z0-9_] survive
        assert " " not in path.name
        assert "!" not in path.name

    def test_extracts_stem_from_path(self, tmp_path):
        from amplihack.recipes.rust_runner_execution import _recipe_log_path

        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            path = _recipe_log_path("/recipes/default-workflow.yaml", pid=1)
        assert "default" in path.name
        assert ".yaml" not in path.name


class TestRecipeLogFileCreation:
    """Tests for log file creation and teeing in _run_rust_process()."""

    def test_progress_mode_creates_log_file(self, tmp_path):
        """_run_rust_process with progress=True should create a log file."""
        from amplihack.recipes.rust_runner_execution import _run_rust_process

        with (
            patch(
                "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                return_value=str(tmp_path),
            ),
            patch("subprocess.Popen") as mock_popen,
        ):
            fake_stdout = io.StringIO('{"recipe_name":"test","success":true}\n')
            fake_stderr = io.StringIO("some stderr\n")
            mock_popen.return_value.stdout = fake_stdout
            mock_popen.return_value.stderr = fake_stderr
            mock_popen.return_value.wait.return_value = 0

            stdout, stderr, rc, log_path = _run_rust_process(
                ["fake-cmd"],
                progress=True,
                env={"PATH": "/usr/bin"},
                recipe_name="test-recipe",
            )

        assert log_path is not None
        assert Path(log_path).exists()
        content = Path(log_path).read_text(encoding="utf-8")
        assert "amplihack recipe log" in content
        assert "test-recipe" in content

    def test_no_progress_returns_none_log_path(self):
        """_run_rust_process with progress=False should return log_path=None."""
        from amplihack.recipes.rust_runner_execution import _run_rust_process

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="out", stderr="err"
            )
            stdout, stderr, rc, log_path = _run_rust_process(
                ["fake-cmd"],
                progress=False,
                env={"PATH": "/usr/bin"},
                recipe_name="test-recipe",
            )

        assert log_path is None

    def test_log_file_contains_stdout_and_stderr(self, tmp_path):
        """Log file should contain [stdout] and [stderr] prefixed lines."""
        from amplihack.recipes.rust_runner_execution import _run_rust_process

        with (
            patch(
                "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                return_value=str(tmp_path),
            ),
            patch("subprocess.Popen") as mock_popen,
        ):
            fake_stdout = io.StringIO("hello stdout\n")
            fake_stderr = io.StringIO("hello stderr\n")
            mock_popen.return_value.stdout = fake_stdout
            mock_popen.return_value.stderr = fake_stderr
            mock_popen.return_value.wait.return_value = 0

            _, _, _, log_path = _run_rust_process(
                ["fake-cmd"],
                progress=True,
                env={"PATH": "/usr/bin"},
                recipe_name="tee-test",
            )

        content = Path(log_path).read_text(encoding="utf-8")
        assert "[stdout] hello stdout" in content
        assert "[stderr] hello stderr" in content

    def test_log_file_has_footer(self, tmp_path):
        """Log file should end with a footer showing exit code and elapsed time."""
        from amplihack.recipes.rust_runner_execution import _run_rust_process

        with (
            patch(
                "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                return_value=str(tmp_path),
            ),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_popen.return_value.stdout = io.StringIO("")
            mock_popen.return_value.stderr = io.StringIO("")
            mock_popen.return_value.wait.return_value = 0

            _, _, _, log_path = _run_rust_process(
                ["fake-cmd"],
                progress=True,
                env={"PATH": "/usr/bin"},
                recipe_name="footer-test",
            )

        content = Path(log_path).read_text(encoding="utf-8")
        assert "exited with code 0" in content
        assert "footer-test" in content

    def test_sets_amplihack_recipe_log_env_var(self, tmp_path):
        """_run_rust_process should set AMPLIHACK_RECIPE_LOG in the env dict."""
        from amplihack.recipes.rust_runner_execution import _run_rust_process

        env = {"PATH": "/usr/bin"}

        with (
            patch(
                "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                return_value=str(tmp_path),
            ),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_popen.return_value.stdout = io.StringIO("")
            mock_popen.return_value.stderr = io.StringIO("")
            mock_popen.return_value.wait.return_value = 0

            _run_rust_process(
                ["fake-cmd"],
                progress=True,
                env=env,
                recipe_name="env-test",
            )

        assert "AMPLIHACK_RECIPE_LOG" in env
        assert env["AMPLIHACK_RECIPE_LOG"].endswith(".log")

    def test_log_creation_failure_degrades_gracefully(self, tmp_path):
        """If log file creation fails, recipe should still execute."""
        from amplihack.recipes.rust_runner_execution import _run_rust_process

        # Point to a non-existent directory to force creation failure
        with (
            patch(
                "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                return_value="/nonexistent/path/that/does/not/exist",
            ),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_popen.return_value.stdout = io.StringIO("output\n")
            mock_popen.return_value.stderr = io.StringIO("")
            mock_popen.return_value.wait.return_value = 0

            stdout, stderr, rc, log_path = _run_rust_process(
                ["fake-cmd"],
                progress=True,
                env={"PATH": "/usr/bin"},
                recipe_name="fail-test",
            )

        assert log_path is None
        assert rc == 0


class TestRecipeResultLogPath:
    """Tests for RecipeResult.log_path field."""

    def test_default_log_path_is_none(self):
        result = RecipeResult(recipe_name="test", success=True)
        assert result.log_path is None

    def test_log_path_stored(self):
        result = RecipeResult(
            recipe_name="test", success=True, log_path="/tmp/test.log"
        )
        assert result.log_path == "/tmp/test.log"

    def test_log_path_in_str_representation(self):
        """log_path should not break __str__."""
        result = RecipeResult(
            recipe_name="test", success=True, log_path="/tmp/test.log"
        )
        text = str(result)
        assert isinstance(text, str)
        assert "test" in text


class TestProgressFiles:
    def test_write_progress_file_writes_expected_schema(self, tmp_path):
        pid = os.getpid()
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            path = _write_progress_file(
                "default-workflow",
                current_step=2,
                total_steps=5,
                step_name="step-02-clarify-requirements",
                elapsed_seconds=3.75,
                status="running",
                pid=pid,
            )

        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["recipe_name"] == "default-workflow"
        assert payload["current_step"] == 2
        assert payload["total_steps"] == 5
        assert payload["step_name"] == "step-02-clarify-requirements"
        assert payload["status"] == "running"
        assert payload["pid"] == pid
        assert "updated_at" in payload
