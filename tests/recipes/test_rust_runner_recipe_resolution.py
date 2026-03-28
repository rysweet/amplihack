"""Tests for Rust runner recipe targeting and public API forwarding."""

from __future__ import annotations

import json
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import amplihack
import amplihack.recipes as recipes_module
import amplihack.recipes.rust_runner as rust_runner_module
from amplihack.recipes.rust_runner import (
    RustRunnerNotFoundError,
    _resolve_recipe_target,
    run_recipe_via_rust,
)


@pytest.fixture(autouse=True)
def _restore_amplihack_modules(monkeypatch):
    """Protect string-based patches after helper tests purge amplihack from sys.modules."""
    monkeypatch.setitem(sys.modules, "amplihack", amplihack)
    monkeypatch.setitem(sys.modules, "amplihack.recipes", recipes_module)
    monkeypatch.setitem(sys.modules, "amplihack.recipes.rust_runner", rust_runner_module)
    yield


@pytest.fixture(autouse=True)
def _mock_runner_version_check(monkeypatch):
    """Keep recipe-resolution tests focused on targeting, not binary version gating."""
    monkeypatch.setattr(rust_runner_module, "check_runner_version", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(rust_runner_module, "raise_for_runner_version", lambda *_args, **_kwargs: None)
    yield


@pytest.fixture(autouse=True)
def _seed_execution_root_for_legacy_runner_tests(monkeypatch, request):
    if request.node.get_closest_marker("strict_execution_root"):
        yield
        return

    original_resolve = rust_runner_module._resolve_execution_root

    def _fake_validate_runner_execution_root(
        execution_root: str, *, authoritative_repo: str | None = None
    ) -> dict[str, object]:
        resolved = Path(execution_root).resolve()
        authoritative = (
            Path(authoritative_repo).resolve() if authoritative_repo is not None else resolved
        )
        return {
            "execution_root": str(resolved),
            "authoritative_repo_path": str(authoritative),
            "expected_gh_account": "",
            "owner_kind": "authoritative-repo",
            "git_initialized": True,
            "marker_path": "",
        }

    def _resolve_with_default(*, working_dir: str, user_context: dict[str, object] | None):
        context = dict(user_context) if user_context is not None else {}
        context.setdefault("execution_root", str(Path(working_dir).resolve()))
        return original_resolve(working_dir=working_dir, user_context=context)

    monkeypatch.setattr(
        rust_runner_module,
        "validate_runner_execution_root",
        _fake_validate_runner_execution_root,
    )
    monkeypatch.setattr(rust_runner_module, "_resolve_execution_root", _resolve_with_default)
    yield


class TestEngineSelection:
    """Tests for run_recipe_by_name — always uses Rust runner."""

    @staticmethod
    def _context(root: str | None = None) -> dict[str, str]:
        return {"execution_root": root or str(Path(".").resolve())}

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_always_uses_rust(self, mock_rust):
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        run_recipe_by_name("test", user_context=self._context())
        mock_rust.assert_called_once()

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_adapter_kwarg_accepted_but_ignored(self, mock_rust):
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        run_recipe_by_name("test", user_context=self._context(), adapter=MagicMock())
        mock_rust.assert_called_once()

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_forwards_recipe_dirs(self, mock_rust):
        """Issue #3002: run_recipe_by_name must forward recipe_dirs."""
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        run_recipe_by_name("test", user_context=self._context(), recipe_dirs=["/custom/recipes"])
        mock_rust.assert_called_once_with(
            name="test",
            user_context=self._context(),
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
        run_recipe_by_name("test", user_context=self._context("/some/path"), working_dir="/some/path")
        _, kwargs = mock_rust.call_args
        assert kwargs["working_dir"] == "/some/path"

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_forwards_auto_stage(self, mock_rust):
        """Issue #3002: run_recipe_by_name must forward auto_stage."""
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        run_recipe_by_name("test", user_context=self._context(), auto_stage=False)
        _, kwargs = mock_rust.call_args
        assert kwargs["auto_stage"] is False

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_forwards_progress(self, mock_rust):
        """Issue #3024: run_recipe_by_name must forward progress mode."""
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        run_recipe_by_name("test", user_context=self._context(), progress=True)
        _, kwargs = mock_rust.call_args
        assert kwargs["progress"] is True

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_passes_recipe_name_directly_to_rust(self, mock_rust):
        """Recipe name is passed directly to Rust binary — it does its own discovery."""
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        run_recipe_by_name("default-workflow", user_context=self._context())

        _, kwargs = mock_rust.call_args
        assert kwargs["name"] == "default-workflow"

    @patch(
        "amplihack.recipes.run_recipe_via_rust", side_effect=RustRunnerNotFoundError("not found")
    )
    def test_rust_not_found_raises(self, mock_rust):
        from amplihack.recipes import run_recipe_by_name

        with pytest.raises(RustRunnerNotFoundError):
            run_recipe_by_name("test", user_context=self._context())

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
