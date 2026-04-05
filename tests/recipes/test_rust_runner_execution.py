"""Tests for Rust runner command execution and streamed output handling."""

from __future__ import annotations

import io
import json
import os
import stat
import subprocess
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.recipes.models import StepStatus
from amplihack.recipes.rust_runner import RustRunnerNotFoundError, run_recipe_via_rust
from amplihack.recipes.rust_runner_execution import (
    _atomic_write_json,
    _progress_file_path,
    _recipe_log_path,
    _validate_path_within_tmpdir,
    _write_progress_file,
    read_progress_file,
)


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
    def test_forwards_pythonpath_and_seeds_claude_project_dir(self, mock_run, mock_find):
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

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.Popen")
    def test_progress_mode_announces_and_writes_recipe_log(self, mock_popen, mock_find, tmp_path):
        class FakePopen:
            def __init__(self, stdout: str, stderr: str, returncode: int = 0):
                self.stdout = io.StringIO(stdout)
                self.stderr = io.StringIO(stderr)
                self._returncode = returncode

            def wait(self, timeout=None):
                return self._returncode

        mock_popen.return_value = FakePopen(
            stdout=self._make_rust_output(),
            stderr="▶ classify-and-decompose (agent)\n  [agent] still running\n",
        )

        streamed_stderr = io.StringIO()
        with (
            patch(
                "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                return_value=str(tmp_path),
            ),
            patch.object(sys, "stderr", streamed_stderr),
        ):
            run_recipe_via_rust("smart-orchestrator", progress=True)

        stderr_text = streamed_stderr.getvalue()
        prefix = "[amplihack] recipe log: "
        log_line = next(line for line in stderr_text.splitlines() if line.startswith(prefix))
        log_path = Path(log_line[len(prefix) :])

        assert log_path.exists(), "progress=True should create a persistent recipe log"
        assert mock_popen.call_args.kwargs["env"]["AMPLIHACK_RECIPE_LOG"] == str(log_path)

        log_text = log_path.read_text(encoding="utf-8")
        assert "--- amplihack recipe log: smart-orchestrator" in log_text
        assert "[stderr] ▶ classify-and-decompose (agent)" in log_text
        assert "[stderr]   [agent] still running" in log_text
        assert "[stdout]" in log_text

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.Popen")
    def test_progress_mode_reuses_cached_progress_path(self, mock_popen, mock_find, tmp_path):
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

        cached_paths: list[Path | None] = []
        progress_path = tmp_path / "amplihack-progress-smart_orchestrator-123.json"

        def capture_write(*args, **kwargs):
            cached_paths.append(kwargs.get("_cached_path"))
            return progress_path

        with (
            patch(
                "amplihack.recipes.rust_runner_execution._progress_file_path",
                return_value=progress_path,
            ) as mock_progress_path,
            patch(
                "amplihack.recipes.rust_runner_execution._write_progress_file",
                side_effect=capture_write,
            ),
        ):
            run_recipe_via_rust("smart-orchestrator", progress=True)

        assert mock_progress_path.call_count == 1
        assert cached_paths == [progress_path, progress_path]


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

    def test_write_progress_file_uses_atomic_replace_for_progress_and_sidecar(self, tmp_path):
        pid = os.getpid()
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        state_file = state_dir / "ws-4032.json"
        state_file.write_text(
            json.dumps({"checkpoint_id": "checkpoint-after-review-feedback"}),
            encoding="utf-8",
        )
        progress_sidecar = state_dir / "ws-4032.progress.json"
        real_replace = os.replace

        with (
            patch(
                "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                return_value=str(tmp_path),
            ),
            patch.dict(
                os.environ,
                {
                    "AMPLIHACK_WORKSTREAM_ISSUE": "4032",
                    "AMPLIHACK_WORKSTREAM_PROGRESS_FILE": str(progress_sidecar),
                    "AMPLIHACK_WORKSTREAM_STATE_FILE": str(state_file),
                },
                clear=False,
            ),
            patch(
                "amplihack.recipes.rust_runner_execution.os.replace",
                side_effect=real_replace,
            ) as mock_replace,
        ):
            progress_path = _write_progress_file(
                "default-workflow",
                current_step=12,
                total_steps=23,
                step_name="step-12-run-precommit",
                elapsed_seconds=42.0,
                status="running",
                pid=pid,
            )

        replaced_targets = {Path(call.args[1]).resolve() for call in mock_replace.call_args_list}
        assert progress_path.resolve() in replaced_targets
        assert progress_sidecar.resolve() in replaced_targets

    def test_write_progress_file_writes_durable_workstream_sidecar(self, tmp_path):
        pid = os.getpid()
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        state_file = state_dir / "ws-4032.json"
        state_file.write_text(
            json.dumps({"checkpoint_id": "checkpoint-after-review-feedback"}),
            encoding="utf-8",
        )
        progress_sidecar = state_dir / "ws-4032.progress.json"

        with (
            patch(
                "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                return_value=str(tmp_path),
            ),
            patch.dict(
                os.environ,
                {
                    "AMPLIHACK_WORKSTREAM_ISSUE": "4032",
                    "AMPLIHACK_WORKSTREAM_PROGRESS_FILE": str(progress_sidecar),
                    "AMPLIHACK_WORKSTREAM_STATE_FILE": str(state_file),
                },
                clear=False,
            ),
        ):
            _write_progress_file(
                "default-workflow",
                current_step=12,
                total_steps=23,
                step_name="step-12-run-precommit",
                elapsed_seconds=42.0,
                status="running",
                pid=pid,
            )

        sidecar = json.loads(progress_sidecar.read_text(encoding="utf-8"))
        assert sidecar["issue"] == 4032
        assert sidecar["recipe_name"] == "default-workflow"
        assert sidecar["step_name"] == "step-12-run-precommit"
        assert sidecar["checkpoint_id"] == "checkpoint-after-review-feedback"
        assert sidecar["pid"] == pid

    def test_write_progress_file_reuses_cached_workstream_state_until_file_changes(self, tmp_path):
        pid = os.getpid()
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        state_file = state_dir / "ws-4032.json"
        state_file.write_text(json.dumps({"checkpoint_id": "checkpoint-one"}), encoding="utf-8")
        progress_sidecar = state_dir / "ws-4032.progress.json"
        resolved_state_file = state_file.resolve()
        original_read_text = Path.read_text
        read_count = 0

        def counting_read_text(self, *args, **kwargs):
            nonlocal read_count
            if self == resolved_state_file:
                read_count += 1
            return original_read_text(self, *args, **kwargs)

        with (
            patch(
                "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                return_value=str(tmp_path),
            ),
            patch.dict(
                os.environ,
                {
                    "AMPLIHACK_WORKSTREAM_ISSUE": "4032",
                    "AMPLIHACK_WORKSTREAM_PROGRESS_FILE": str(progress_sidecar),
                    "AMPLIHACK_WORKSTREAM_STATE_FILE": str(state_file),
                },
                clear=False,
            ),
            patch.object(Path, "read_text", new=counting_read_text),
        ):
            _write_progress_file(
                "default-workflow",
                current_step=1,
                total_steps=23,
                step_name="step-01-prepare-workspace",
                elapsed_seconds=1.0,
                status="running",
                pid=pid,
            )
            _write_progress_file(
                "default-workflow",
                current_step=2,
                total_steps=23,
                step_name="step-02-clarify-requirements",
                elapsed_seconds=2.0,
                status="running",
                pid=pid,
            )
            state_file.write_text(json.dumps({"checkpoint_id": "checkpoint-two"}), encoding="utf-8")
            _write_progress_file(
                "default-workflow",
                current_step=3,
                total_steps=23,
                step_name="step-03-investigate",
                elapsed_seconds=3.0,
                status="running",
                pid=pid,
            )

        sidecar = json.loads(progress_sidecar.read_text(encoding="utf-8"))
        assert read_count == 2
        assert sidecar["checkpoint_id"] == "checkpoint-two"


class TestPathTraversalPrevention:
    """Verify that crafted recipe names cannot escape the temp directory."""

    def test_normal_name_stays_in_tmpdir(self, tmp_path):
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            path = _progress_file_path("default-workflow", pid=1)
            assert str(path.resolve()).startswith(str(tmp_path.resolve()))

    def test_dotdot_in_recipe_name_is_sanitised(self, tmp_path):
        """Path components like '..' are sanitised to underscores."""
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            path = _progress_file_path("../../etc/passwd", pid=1)
            assert str(path.resolve()).startswith(str(tmp_path.resolve()))
            assert "etc" not in str(path)

    def test_log_path_dotdot_sanitised(self, tmp_path):
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            path = _recipe_log_path("../../etc/shadow", pid=1)
            assert str(path.resolve()).startswith(str(tmp_path.resolve()))

    def test_validate_path_rejects_escape(self, tmp_path):
        """Direct call to _validate_path_within_tmpdir rejects paths outside tmpdir."""
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            with pytest.raises(ValueError, match="escapes temp directory"):
                _validate_path_within_tmpdir(Path("/etc/passwd"))

    def test_very_long_recipe_name_truncated(self, tmp_path):
        long_name = "a" * 200
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            path = _progress_file_path(long_name, pid=1)
            # The sanitised stem should be at most 64 chars
            filename = path.name
            # "amplihack-progress-" prefix + 64 chars + "-1.json" suffix
            assert len(filename) <= len("amplihack-progress-") + 64 + len("-1.json")


class TestAtomicWriteJson:
    """Verify atomic write semantics for progress files."""

    def test_atomic_write_creates_file_with_correct_content(self, tmp_path):
        target = tmp_path / "test.json"
        payload = {"key": "value", "num": 42}
        _atomic_write_json(target, payload)
        assert target.exists()
        assert json.loads(target.read_text()) == payload

    def test_atomic_write_file_permissions(self, tmp_path):
        target = tmp_path / "perms.json"
        _atomic_write_json(target, {"test": True})
        mode = stat.S_IMODE(target.stat().st_mode)
        assert mode == 0o600

    def test_atomic_write_overwrites_existing(self, tmp_path):
        target = tmp_path / "overwrite.json"
        _atomic_write_json(target, {"version": 1})
        _atomic_write_json(target, {"version": 2})
        assert json.loads(target.read_text())["version"] == 2

    def test_atomic_write_no_temp_files_left_on_success(self, tmp_path):
        target = tmp_path / "clean.json"
        _atomic_write_json(target, {"clean": True})
        # Only the target file should exist
        files = list(tmp_path.iterdir())
        assert files == [target]

    def test_atomic_write_fallback_on_readonly_parent(self, tmp_path):
        """When the parent dir doesn't allow mkstemp, the fallback direct write kicks in.

        We simulate this by patching tempfile.mkstemp to raise OSError.
        """
        target = tmp_path / "fallback.json"
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.mkstemp",
            side_effect=OSError("simulated mkstemp failure"),
        ):
            _atomic_write_json(target, {"fallback": True})
        assert json.loads(target.read_text()) == {"fallback": True}


class TestConcurrentSidecarWrites:
    """Verify that concurrent progress writes do not corrupt data."""

    def test_concurrent_writes_produce_valid_json(self, tmp_path):
        """Multiple threads writing progress files concurrently must each produce valid JSON."""
        errors: list[str] = []
        iterations = 20

        def writer(thread_id: int) -> None:
            for i in range(iterations):
                with patch(
                    "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                    return_value=str(tmp_path),
                ):
                    path = _write_progress_file(
                        "concurrent-test",
                        current_step=i,
                        total_steps=iterations,
                        step_name=f"step-{i}",
                        elapsed_seconds=float(i),
                        status="running",
                        pid=thread_id,
                    )
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                        if not isinstance(data, dict):
                            errors.append(f"Thread {thread_id} iter {i}: not a dict")
                    except (json.JSONDecodeError, OSError) as exc:
                        errors.append(f"Thread {thread_id} iter {i}: {exc}")

        threads = [threading.Thread(target=writer, args=(tid,)) for tid in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent write errors: {errors}"

    def test_concurrent_writes_to_same_pid_no_crash(self, tmp_path):
        """Multiple threads targeting the same PID (same file) must not crash."""
        errors: list[str] = []

        def writer(thread_id: int) -> None:
            for i in range(30):
                try:
                    with patch(
                        "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                        return_value=str(tmp_path),
                    ):
                        _write_progress_file(
                            "same-pid-test",
                            current_step=i,
                            total_steps=30,
                            step_name=f"step-{i}-t{thread_id}",
                            elapsed_seconds=float(i),
                            status="running",
                            pid=999,
                        )
                except Exception as exc:
                    errors.append(f"Thread {thread_id} iter {i}: {exc}")

        threads = [threading.Thread(target=writer, args=(tid,)) for tid in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent same-PID write errors: {errors}"


class TestReadProgressFile:
    """Verify graceful handling of malformed/corrupt progress files."""

    def test_read_valid_file(self, tmp_path):
        f = tmp_path / "good.json"
        payload = {"recipe_name": "test", "current_step": 1, "status": "running", "pid": 123}
        f.write_text(json.dumps(payload))
        result = read_progress_file(f)
        assert result == payload

    def test_read_missing_file(self, tmp_path):
        result = read_progress_file(tmp_path / "nonexistent.json")
        assert result is None

    def test_read_empty_file(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("")
        assert read_progress_file(f) is None

    def test_read_malformed_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{truncated")
        assert read_progress_file(f) is None

    def test_read_json_array_instead_of_object(self, tmp_path):
        f = tmp_path / "array.json"
        f.write_text("[1,2,3]")
        assert read_progress_file(f) is None

    def test_read_missing_required_keys(self, tmp_path):
        f = tmp_path / "partial.json"
        f.write_text(json.dumps({"recipe_name": "test"}))
        assert read_progress_file(f) is None

    def test_read_binary_garbage(self, tmp_path):
        f = tmp_path / "garbage.json"
        f.write_bytes(b"\x00\xff\xfe\x80garbage")
        assert read_progress_file(f) is None

    def test_read_permission_denied(self, tmp_path):
        f = tmp_path / "noperm.json"
        f.write_text(json.dumps({"recipe_name": "x", "current_step": 0, "status": "r", "pid": 1}))
        f.chmod(0o000)
        try:
            assert read_progress_file(f) is None
        finally:
            f.chmod(0o644)  # Restore for cleanup


class TestRestrictedEnvironmentBehavior:
    """Verify graceful degradation when the filesystem is restricted."""

    def test_write_progress_to_readonly_dir_does_not_raise(self, tmp_path):
        """Progress writes to a read-only directory should degrade silently (log only)."""
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)
        try:
            with patch(
                "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
                return_value=str(readonly_dir),
            ):
                # Should not raise -- the function logs and returns the path.
                path = _write_progress_file(
                    "readonly-test",
                    current_step=1,
                    total_steps=1,
                    step_name="step-1",
                    elapsed_seconds=0.1,
                    status="running",
                    pid=42,
                )
                assert path is not None
        finally:
            readonly_dir.chmod(0o755)

    def test_write_progress_missing_parent_dir_does_not_raise(self, tmp_path):
        """If the tmpdir doesn't exist, _write_progress_file degrades gracefully."""
        nonexistent = tmp_path / "does" / "not" / "exist"
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(nonexistent),
        ):
            # Should not raise
            path = _write_progress_file(
                "missing-dir-test",
                current_step=1,
                total_steps=1,
                step_name="step-1",
                elapsed_seconds=0.1,
                status="running",
                pid=42,
            )
            assert path is not None
