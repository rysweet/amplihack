"""Tests for Rust runner recipe targeting and public API forwarding."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.recipes.rust_runner import (
    RustRunnerNotFoundError,
    _resolve_recipe_target,
    run_recipe_via_rust,
)


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

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_forwards_recipe_dirs(self, mock_rust):
        """Issue #3002: run_recipe_by_name must forward recipe_dirs."""
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        run_recipe_by_name("test", recipe_dirs=["/custom/recipes"])
        mock_rust.assert_called_once_with(
            name="test",
            user_context=None,
            dry_run=False,
            recipe_dirs=["/custom/recipes"],
            working_dir=".",
            auto_stage=True,
            progress=False,
        )

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_forwards_working_dir(self, mock_rust):
        """Issue #3002: run_recipe_by_name must forward working_dir."""
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        run_recipe_by_name("test", working_dir="/some/path")
        _, kwargs = mock_rust.call_args
        assert kwargs["working_dir"] == "/some/path"

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_forwards_auto_stage(self, mock_rust):
        """Issue #3002: run_recipe_by_name must forward auto_stage."""
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        run_recipe_by_name("test", auto_stage=False)
        _, kwargs = mock_rust.call_args
        assert kwargs["auto_stage"] is False

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_forwards_progress(self, mock_rust):
        """Issue #3024: run_recipe_by_name must forward progress mode."""
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        run_recipe_by_name("test", progress=True)
        _, kwargs = mock_rust.call_args
        assert kwargs["progress"] is True

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_passes_recipe_name_directly_to_rust(self, mock_rust):
        """Recipe name is passed directly to Rust binary — it does its own discovery."""
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        run_recipe_by_name("default-workflow")

        _, kwargs = mock_rust.call_args
        assert kwargs["name"] == "default-workflow"

    @patch(
        "amplihack.recipes.run_recipe_via_rust", side_effect=RustRunnerNotFoundError("not found")
    )
    def test_rust_not_found_raises(self, mock_rust):
        from amplihack.recipes import run_recipe_by_name

        with pytest.raises(RustRunnerNotFoundError):
            run_recipe_by_name("test")

    def test_python_runner_no_longer_importable(self):
        with pytest.raises(ImportError):
            from amplihack.recipes import RecipeRunner  # noqa: F401

    def test_adapters_no_longer_importable(self):
        with pytest.raises(ImportError):
            from amplihack.recipes.adapters import CLISubprocessAdapter  # noqa: F401

    def test_context_no_longer_importable(self):
        with pytest.raises(ImportError):
            from amplihack.recipes import context  # noqa: F401


class TestPackageBundleDirInjection:
    """Issue #3002: run_recipe_via_rust auto-injects package bundle dir."""

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_auto_injects_package_bundle_dir(self, mock_run, mock_find):
        """When recipe_dirs is None, the package bundle dir should be injected."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "recipe_name": "test",
                    "success": True,
                    "step_results": [],
                    "context": {},
                }
            ),
            stderr="",
        )
        with patch(
            "amplihack.recipes.rust_runner._default_package_recipe_dirs",
            return_value=["/pkg/amplihack/amplifier-bundle/recipes"],
        ):
            run_recipe_via_rust("test")
        cmd = mock_run.call_args[0][0]
        assert "-R" in cmd
        idx = cmd.index("-R")
        assert cmd[idx + 1] == "/pkg/amplihack/amplifier-bundle/recipes"

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_explicit_recipe_dirs_not_overridden(self, mock_run, mock_find):
        """When recipe_dirs is provided explicitly, package dir is NOT injected."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "recipe_name": "test",
                    "success": True,
                    "step_results": [],
                    "context": {},
                }
            ),
            stderr="",
        )
        with patch(
            "amplihack.recipes.rust_runner._default_package_recipe_dirs",
            return_value=["/pkg/amplihack/amplifier-bundle/recipes"],
        ):
            run_recipe_via_rust("test", recipe_dirs=["/my/custom/dir"])
        cmd = mock_run.call_args[0][0]
        r_indices = [i for i, v in enumerate(cmd) if v == "-R"]
        assert len(r_indices) == 1
        assert cmd[r_indices[0] + 1] == "/my/custom/dir"

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_no_injection_when_package_dir_missing(self, mock_run, mock_find):
        """When package bundle dir does not exist, no -R flag is added."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "recipe_name": "test",
                    "success": True,
                    "step_results": [],
                    "context": {},
                }
            ),
            stderr="",
        )
        with patch(
            "amplihack.recipes.rust_runner._default_package_recipe_dirs",
            return_value=[],
        ):
            run_recipe_via_rust("test")
        cmd = mock_run.call_args[0][0]
        assert "-R" not in cmd


class TestNoRunTimeoutInSource:
    """Issue #3049: The _run_timeout helper must not exist in the source."""

    def test_no_run_timeout_function_in_source(self):
        """Verify _run_timeout() was removed from rust_runner.py."""
        import inspect

        import amplihack.recipes.rust_runner as mod

        source = inspect.getsource(mod)
        assert "_run_timeout" not in source, (
            "_run_timeout should be removed — the Rust binary manages its own timeouts"
        )


class TestResolveRecipeTarget:
    """Tests for recipe target resolution and fallbacks."""

    def test_relative_recipe_path_resolves_against_working_dir(self):
        resolved = _resolve_recipe_target(
            "recipes/test.yaml",
            recipe_dirs=None,
            working_dir="/repo/worktree",
        )

        assert resolved == str(Path("/repo/worktree/recipes/test.yaml").resolve())

    @patch(
        "amplihack.recipes.discovery.find_recipe",
        return_value=Path("/recipes/default-workflow.yaml"),
    )
    def test_recipe_name_resolves_via_discovery(self, mock_find_recipe):
        resolved = _resolve_recipe_target(
            "default-workflow",
            recipe_dirs=["/recipes"],
            working_dir="/repo/worktree",
        )

        assert resolved == str(Path("/recipes/default-workflow.yaml").resolve())
        mock_find_recipe.assert_called_once()

    @patch("amplihack.recipes.discovery.find_recipe", side_effect=RuntimeError("lookup failed"))
    def test_recipe_name_falls_back_when_discovery_errors(self, mock_find_recipe):
        resolved = _resolve_recipe_target(
            "default-workflow",
            recipe_dirs=["/recipes"],
            working_dir="/repo/worktree",
        )

        assert resolved == "default-workflow"
        mock_find_recipe.assert_called_once()
