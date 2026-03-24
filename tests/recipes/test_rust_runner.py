"""Tests for rust_runner.py — startup banners and progress file lifecycle.

Covers:
- Preparing/launching banners emitted to stderr
- Progress file cleanup on completion
- get_recipe_progress() reading from progress files
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.recipes.rust_runner import (
    _cleanup_progress_file,
    run_recipe_via_rust,
)
from amplihack.recipes.rust_runner_execution import _write_progress_file


@pytest.fixture(autouse=True)
def _mock_runner_version_check():
    """Keep tests focused on banners/progress, not version gating."""
    with patch(
        "amplihack.recipes.rust_runner.runner_binary.raise_for_runner_version",
        return_value=None,
    ):
        yield


def _make_rust_output(*, success: bool = True) -> str:
    return json.dumps(
        {
            "recipe_name": "test-recipe",
            "success": success,
            "step_results": [
                {"step_id": "s1", "status": "Completed", "output": "ok", "error": ""},
            ],
            "context": {"result": "done"},
        }
    )


class TestStartupBanners:
    """Verify that run_recipe_via_rust emits [recipe-runner] banners to stderr."""

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.run")
    def test_preparing_banner_emitted(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=_make_rust_output(), stderr=""
        )

        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("my-recipe")

        output = captured.getvalue()
        assert "[recipe-runner] Preparing recipe 'my-recipe'..." in output

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.run")
    def test_launching_banner_emitted(self, mock_run, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=_make_rust_output(), stderr=""
        )

        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("my-recipe")

        output = captured.getvalue()
        assert "[recipe-runner] Launching recipe 'my-recipe'" in output
        assert f"(pid {os.getpid()})" in output

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.run")
    def test_banners_appear_before_execution(self, mock_run, mock_find):
        """Both banners should appear: Preparing first, then Launching."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=_make_rust_output(), stderr=""
        )

        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("my-recipe")

        output = captured.getvalue()
        preparing_pos = output.index("[recipe-runner] Preparing")
        launching_pos = output.index("[recipe-runner] Launching")
        assert preparing_pos < launching_pos


class TestProgressFileLifecycle:
    """Verify progress file creation, reading, and cleanup."""

    def test_write_and_read_progress_file(self, tmp_path):
        """_write_progress_file creates a readable JSON file."""
        pid = os.getpid()
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            path = _write_progress_file(
                "smart-orchestrator",
                current_step=3,
                total_steps=10,
                step_name="step-03-build",
                elapsed_seconds=12.5,
                status="running",
                pid=pid,
            )

        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["recipe_name"] == "smart-orchestrator"
        assert payload["current_step"] == 3
        assert payload["total_steps"] == 10
        assert payload["step_name"] == "step-03-build"
        assert payload["status"] == "running"
        assert payload["pid"] == pid

    def test_cleanup_progress_file_removes_file(self, tmp_path):
        """_cleanup_progress_file removes the progress file."""
        pid = os.getpid()
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            path = _write_progress_file(
                "test-recipe",
                current_step=1,
                total_steps=5,
                step_name="s1",
                elapsed_seconds=1.0,
                status="completed",
                pid=pid,
            )
            assert path.exists()

            _cleanup_progress_file("test-recipe")

        assert not path.exists()

    def test_cleanup_progress_file_noop_when_missing(self):
        """_cleanup_progress_file does not raise when file is already gone."""
        # Should not raise
        _cleanup_progress_file("nonexistent-recipe-xyz")

    def test_write_progress_file_catches_oserror(self, tmp_path):
        """_write_progress_file is best-effort and catches OSError."""
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value="/nonexistent/impossible/path",
        ):
            # Should not raise — catches OSError internally
            path = _write_progress_file(
                "test-recipe",
                current_step=1,
                total_steps=1,
                step_name="s1",
                elapsed_seconds=0.0,
                status="running",
            )
            # Path is returned but may not exist
            assert isinstance(path, Path)

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.run")
    def test_progress_file_cleaned_on_success(self, mock_run, mock_find, tmp_path):
        """run_recipe_via_rust cleans up the progress file after completion."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=_make_rust_output(), stderr=""
        )

        pid = os.getpid()
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            # Pre-create a progress file to verify it gets cleaned
            _write_progress_file(
                "test-recipe",
                current_step=1,
                total_steps=1,
                step_name="s1",
                elapsed_seconds=1.0,
                status="running",
                pid=pid,
            )
            run_recipe_via_rust("test-recipe")

        progress_files = list(tmp_path.glob("amplihack-progress-test_recipe-*.json"))
        assert len(progress_files) == 0

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.run")
    def test_progress_file_cleaned_on_failure(self, mock_run, mock_find, tmp_path):
        """Progress file is cleaned even when the recipe fails."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error: boom"
        )

        pid = os.getpid()
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            _write_progress_file(
                "test-recipe",
                current_step=1,
                total_steps=1,
                step_name="s1",
                elapsed_seconds=1.0,
                status="running",
                pid=pid,
            )
            with pytest.raises(RuntimeError):
                run_recipe_via_rust("test-recipe")

        progress_files = list(tmp_path.glob("amplihack-progress-test_recipe-*.json"))
        assert len(progress_files) == 0


class TestGetRecipeProgress:
    """Tests for get_recipe_progress() in dev_intent_router.

    The dev_intent_router lives under .claude/tools/ (not a regular Python
    package), so we load it via importlib.util.spec_from_file_location.
    """

    @staticmethod
    def _load_router():
        import importlib.util

        router_path = (
            Path(__file__).resolve().parents[2]
            / ".claude"
            / "tools"
            / "amplihack"
            / "hooks"
            / "dev_intent_router.py"
        )
        if not router_path.exists():
            pytest.skip(f"dev_intent_router.py not found at {router_path}")
        spec = importlib.util.spec_from_file_location("dev_intent_router", str(router_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_returns_none_when_no_files(self, tmp_path):
        router = self._load_router()

        with patch.object(router._tempfile, "gettempdir", return_value=str(tmp_path)):
            result = router.get_recipe_progress("nonexistent-recipe")

        assert result is None

    def test_reads_most_recent_progress_file(self, tmp_path):
        """get_recipe_progress reads the latest progress file."""
        router = self._load_router()

        # Write a progress file via the execution module
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            _write_progress_file(
                "smart-orchestrator",
                current_step=5,
                total_steps=10,
                step_name="step-05-build",
                elapsed_seconds=30.0,
                status="running",
                pid=os.getpid(),
            )

        # Read it via get_recipe_progress
        with patch.object(router._tempfile, "gettempdir", return_value=str(tmp_path)):
            result = router.get_recipe_progress("smart-orchestrator")

        assert result is not None
        assert result["current_step"] == 5
        assert result["step_name"] == "step-05-build"
        assert result["status"] == "running"

    def test_returns_expected_schema(self, tmp_path):
        """get_recipe_progress returns a dict with the expected keys."""
        router = self._load_router()

        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            _write_progress_file(
                "default-workflow",
                current_step=2,
                total_steps=5,
                step_name="step-02",
                elapsed_seconds=8.0,
                status="completed",
                pid=os.getpid(),
            )

        with patch.object(router._tempfile, "gettempdir", return_value=str(tmp_path)):
            result = router.get_recipe_progress("default-workflow")

        assert result is not None
        assert set(result.keys()) == {
            "current_step",
            "total_steps",
            "step_name",
            "elapsed_seconds",
            "status",
        }
