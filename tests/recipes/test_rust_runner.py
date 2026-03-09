"""Tests for the Rust recipe runner integration (rust_runner.py).

Covers:
- Binary discovery (find_rust_binary, is_rust_runner_available)
- Recipe execution via Rust binary (run_recipe_via_rust)
- JSON output parsing and error handling
- Engine selection in run_recipe_by_name
- Configurable timeouts
- Empty step_results and exception paths
"""

from __future__ import annotations

import json
import os
import subprocess
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from amplihack.recipes.rust_runner import (
    RustRunnerNotFoundError,
    _binary_search_paths,
    _build_rust_command,
    _execute_rust_command,
    _find_rust_binary,
    _redact_command_for_log,
    ensure_rust_recipe_runner,
    find_rust_binary,
    is_rust_runner_available,
    run_recipe_via_rust,
)
from amplihack.recipes.models import StepStatus


# ============================================================================
# find_rust_binary
# ============================================================================


class TestFindRustBinary:
    """Tests for find_rust_binary()."""

    @patch.dict("os.environ", {"RECIPE_RUNNER_RS_PATH": "/custom/recipe-runner-rs"})
    @patch("shutil.which", side_effect=lambda p: str(p) if str(p) == "/custom/recipe-runner-rs" else "/other/binary")
    def test_env_var_takes_priority(self, mock_which):
        result = find_rust_binary()
        assert result == "/custom/recipe-runner-rs"
        # Verify which was only called once (env var path, not search paths)
        mock_which.assert_called_once_with("/custom/recipe-runner-rs")

    @patch.dict("os.environ", {"RECIPE_RUNNER_RS_PATH": "/nonexistent/binary"})
    @patch("shutil.which", return_value=None)
    def test_env_var_invalid_returns_none(self, mock_which):
        result = find_rust_binary()
        assert result is None

    @patch.dict("os.environ", {}, clear=True)
    @patch("shutil.which", side_effect=lambda p: "/usr/bin/recipe-runner-rs" if p == "recipe-runner-rs" else None)
    def test_path_lookup(self, mock_which):
        result = find_rust_binary()
        assert result == "/usr/bin/recipe-runner-rs"

    @patch.dict("os.environ", {}, clear=True)
    @patch("shutil.which", return_value=None)
    def test_not_found(self, mock_which):
        result = find_rust_binary()
        assert result is None


class TestIsRustRunnerAvailable:
    """Tests for is_rust_runner_available()."""

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    def test_available(self, mock_find):
        assert is_rust_runner_available() is True

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value=None)
    def test_not_available(self, mock_find):
        assert is_rust_runner_available() is False


# ============================================================================
# run_recipe_via_rust
# ============================================================================


class TestRunRecipeViaRust:
    """Tests for run_recipe_via_rust()."""

    def _make_rust_output(self, *, success=True, steps=None):
        """Helper to create valid Rust binary JSON output."""
        if steps is None:
            steps = [
                {"step_id": "s1", "status": "Completed", "output": "hello", "error": ""},
            ]
        return json.dumps({
            "recipe_name": "test-recipe",
            "success": success,
            "step_results": steps,
            "context": {"result": "done"},
        })

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value=None)
    def test_raises_when_binary_missing(self, mock_find):
        with pytest.raises(RustRunnerNotFoundError, match="recipe-runner-rs binary not found"):
            run_recipe_via_rust("test-recipe")

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run")
    def test_successful_execution(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        result = run_recipe_via_rust("test-recipe")
        assert result.success is True
        assert result.recipe_name == "test-recipe"
        assert len(result.step_results) == 1
        assert result.step_results[0].step_id == "s1"
        assert result.step_results[0].status == StepStatus.COMPLETED

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run")
    def test_passes_dry_run_flag(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust("test-recipe", dry_run=True)
        cmd = mock_run.call_args[0][0]
        assert "--dry-run" in cmd

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run")
    def test_passes_no_auto_stage_flag(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust("test-recipe", auto_stage=False)
        cmd = mock_run.call_args[0][0]
        assert "--no-auto-stage" in cmd

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run")
    def test_passes_recipe_dirs(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust("test-recipe", recipe_dirs=["/a", "/b"])
        cmd = mock_run.call_args[0][0]
        assert "-R" in cmd
        idx = cmd.index("-R")
        assert cmd[idx + 1] == "/a"

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run")
    def test_passes_context_values(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust("test-recipe", user_context={
            "name": "world",
            "verbose": True,
            "data": {"key": "val"},
        })
        cmd = mock_run.call_args[0][0]
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        assert "name=world" in set_args
        assert "verbose=true" in set_args
        assert any('"key"' in a for a in set_args)

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run")
    def test_default_timeout(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust("test-recipe")
        assert mock_run.call_args[1].get("timeout") == 3600

    @patch.dict("os.environ", {"RECIPE_RUNNER_RUN_TIMEOUT": "60"})
    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run")
    def test_configurable_run_timeout(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        run_recipe_via_rust("test-recipe")
        assert mock_run.call_args[1].get("timeout") == 60

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run")
    def test_nonzero_exit_with_bad_json_raises(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1,
            stdout="not json",
            stderr="error: recipe failed",
        )
        with pytest.raises(RuntimeError, match="Rust recipe runner failed"):
            run_recipe_via_rust("test-recipe")

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run")
    def test_zero_exit_with_bad_json_raises(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="not json at all",
            stderr="",
        )
        with pytest.raises(RuntimeError, match="unparseable output"):
            run_recipe_via_rust("test-recipe")

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run")
    def test_status_mapping(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=self._make_rust_output(steps=[
                {"step_id": "a", "status": "Completed", "output": "", "error": ""},
                {"step_id": "b", "status": "Skipped", "output": "", "error": ""},
                {"step_id": "c", "status": "Failed", "output": "", "error": "boom"},
                {"step_id": "d", "status": "unknown_status", "output": "", "error": ""},
            ]),
            stderr="",
        )
        result = run_recipe_via_rust("test-recipe")
        assert result.step_results[0].status == StepStatus.COMPLETED
        assert result.step_results[1].status == StepStatus.SKIPPED
        assert result.step_results[2].status == StepStatus.FAILED
        assert result.step_results[3].status == StepStatus.FAILED  # unknown → FAILED

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run")
    def test_empty_step_results(self, mock_run, mock_find):
        """PR-M5: Empty step_results produces a valid RecipeResult with no steps."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=self._make_rust_output(steps=[]),
            stderr="",
        )
        result = run_recipe_via_rust("test-recipe")
        assert result.step_results == []
        assert result.recipe_name == "test-recipe"

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run", side_effect=OSError("No such file or directory"))
    def test_oserror_during_subprocess(self, mock_run, mock_find):
        """PR-M5: OSError during subprocess.run propagates cleanly."""
        with pytest.raises(OSError, match="No such file or directory"):
            run_recipe_via_rust("test-recipe")


# ============================================================================
# Helper function tests
# ============================================================================


class TestRedactCommandForLog:
    """Tests for _redact_command_for_log()."""

    def test_masks_set_values(self):
        cmd = ["/bin/rr", "recipe", "--set", "api_key=secret123", "--dry-run"]
        result = _redact_command_for_log(cmd)
        assert "secret123" not in result
        assert "api_key=***" in result
        assert "--dry-run" in result

    def test_no_set_flags(self):
        cmd = ["/bin/rr", "recipe", "--dry-run"]
        result = _redact_command_for_log(cmd)
        assert result == "/bin/rr recipe --dry-run"


class TestConfigurableTimeouts:
    """Tests for configurable timeouts."""

    @patch.dict("os.environ", {"RECIPE_RUNNER_INSTALL_TIMEOUT": "120"})
    @patch("amplihack.recipes.rust_runner.is_rust_runner_available", return_value=False)
    @patch("shutil.which", return_value="/usr/bin/cargo")
    @patch("subprocess.run")
    def test_install_timeout_from_env(self, mock_run, mock_which, mock_avail):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        ensure_rust_recipe_runner(quiet=True)
        assert mock_run.call_args[1].get("timeout") == 120


# ============================================================================
# Engine selection (run_recipe_by_name)
# ============================================================================


class TestEngineSelection:
    """Tests for run_recipe_by_name — always uses Rust runner."""

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_always_uses_rust(self, mock_rust):
        from amplihack.recipes import run_recipe_by_name
        mock_rust.return_value = MagicMock()
        run_recipe_by_name("test")
        mock_rust.assert_called_once()

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_adapter_kwarg_accepted_but_ignored(self, mock_rust):
        from amplihack.recipes import run_recipe_by_name
        mock_rust.return_value = MagicMock()
        run_recipe_by_name("test", adapter=MagicMock())
        mock_rust.assert_called_once()

    @patch("amplihack.recipes.run_recipe_via_rust", side_effect=RustRunnerNotFoundError("not found"))
    def test_rust_not_found_raises(self, mock_rust):
        from amplihack.recipes import run_recipe_by_name
        with pytest.raises(RustRunnerNotFoundError):
            run_recipe_by_name("test")

    def test_python_runner_no_longer_importable(self):
        with pytest.raises(ImportError):
            from amplihack.recipes import RecipeRunner  # noqa: F401

    def test_adapters_no_longer_importable(self):
        with pytest.raises(ModuleNotFoundError):
            from amplihack.recipes.adapters import CLISubprocessAdapter  # noqa: F401

    def test_context_no_longer_importable(self):
        with pytest.raises(ImportError):
            from amplihack.recipes import context  # noqa: F401


# ============================================================================
# ensure_rust_recipe_runner
# ============================================================================


class TestEnsureRustRecipeRunner:
    """Tests for ensure_rust_recipe_runner()."""

    @patch("amplihack.recipes.rust_runner.is_rust_runner_available", return_value=True)
    def test_already_installed(self, mock_avail):
        assert ensure_rust_recipe_runner() is True

    @patch("amplihack.recipes.rust_runner.is_rust_runner_available", return_value=False)
    @patch("shutil.which", return_value=None)
    def test_no_cargo(self, mock_which, mock_avail):
        assert ensure_rust_recipe_runner(quiet=True) is False

    @patch("amplihack.recipes.rust_runner.is_rust_runner_available", return_value=False)
    @patch("shutil.which", return_value="/usr/bin/cargo")
    @patch("subprocess.run")
    def test_cargo_install_success(self, mock_run, mock_which, mock_avail):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        assert ensure_rust_recipe_runner(quiet=True) is True
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "/usr/bin/cargo"
        assert "install" in cmd
        assert "--git" in cmd

    @patch("amplihack.recipes.rust_runner.is_rust_runner_available", return_value=False)
    @patch("shutil.which", return_value="/usr/bin/cargo")
    @patch("subprocess.run")
    def test_cargo_install_failure(self, mock_run, mock_which, mock_avail):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error",
        )
        assert ensure_rust_recipe_runner(quiet=True) is False

    @patch("amplihack.recipes.rust_runner.is_rust_runner_available", return_value=False)
    @patch("shutil.which", return_value="/usr/bin/cargo")
    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cargo", 300))
    def test_cargo_install_timeout(self, mock_run, mock_which, mock_avail):
        assert ensure_rust_recipe_runner(quiet=True) is False


# ============================================================================
# Validation and edge-case tests (C2-PR-9, C2-PR-10)
# ============================================================================


class TestExecutionTimeout:
    """C2-PR-10: TimeoutExpired during recipe execution must propagate."""

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired("recipe-runner", 3600))
    def test_execution_timeout_propagates(self, mock_run, mock_find):
        with pytest.raises(subprocess.TimeoutExpired):
            run_recipe_via_rust(name="test", user_context={})
