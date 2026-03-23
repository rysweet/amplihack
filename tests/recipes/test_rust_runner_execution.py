"""Tests for Rust runner command execution and streamed output handling."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.recipes.models import StepStatus
from amplihack.recipes.rust_runner import RustRunnerNotFoundError, run_recipe_via_rust


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
