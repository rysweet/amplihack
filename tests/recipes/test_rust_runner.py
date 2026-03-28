"""Tests for the Rust recipe runner integration (rust_runner.py).

Covers:
- Binary discovery (find_rust_binary, is_rust_runner_available)
- Recipe execution via Rust binary (run_recipe_via_rust)
- JSON output parsing and error handling
- Engine selection in run_recipe_by_name
- Configurable install timeout
- Empty step_results and exception paths
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import amplihack
import amplihack.recipes as recipes_module
import amplihack.recipes.rust_runner as rust_runner_module
import amplihack.recipes.rust_runner_execution as rust_runner_execution_module
from amplihack.recipes.models import StepStatus
from amplihack.recipes.rust_runner import (
    RustRunnerNotFoundError,
    _redact_command_for_log,
    _write_progress_file,
    ensure_rust_recipe_runner,
    find_rust_binary,
    is_rust_runner_available,
    run_recipe_via_rust,
)


@pytest.fixture(autouse=True)
def _restore_amplihack_modules(monkeypatch):
    """Protect string-based patches after helper tests purge amplihack from sys.modules."""
    monkeypatch.setitem(sys.modules, "amplihack", amplihack)
    monkeypatch.setitem(sys.modules, "amplihack.recipes", recipes_module)
    monkeypatch.setitem(sys.modules, "amplihack.recipes.rust_runner", rust_runner_module)
    monkeypatch.setitem(
        sys.modules,
        "amplihack.recipes.rust_runner_execution",
        rust_runner_execution_module,
    )
    yield


@pytest.fixture(autouse=True)
def _mock_runner_version_check(monkeypatch):
    """Keep rust_runner tests focused on runner behavior, not binary version gating."""
    monkeypatch.setattr(rust_runner_module, "check_runner_version", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(rust_runner_module, "raise_for_runner_version", lambda *_args, **_kwargs: None)
    yield


@pytest.fixture(autouse=True)
def _seed_execution_root_for_legacy_runner_tests(monkeypatch, request):
    """Keep legacy runner tests focused on command plumbing, not root validation."""
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


def _import_dev_intent_router():
    """Import dev_intent_router from its non-package location."""
    hooks_dir = Path(__file__).parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
    spec = importlib.util.spec_from_file_location(
        "dev_intent_router", hooks_dir / "dev_intent_router.py"
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ============================================================================
# find_rust_binary
# ============================================================================


class TestFindRustBinary:
    """Tests for find_rust_binary()."""

    @patch.dict("os.environ", {"RECIPE_RUNNER_RS_PATH": "/custom/recipe-runner-rs"})
    @patch(
        "shutil.which",
        side_effect=lambda p: str(p) if str(p) == "/custom/recipe-runner-rs" else "/other/binary",
    )
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
    @patch(
        "shutil.which",
        side_effect=lambda p: "/usr/bin/recipe-runner-rs" if p == "recipe-runner-rs" else None,
    )
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

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
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

    def test_rejects_world_writable_binary(self, tmp_path):
        binary = tmp_path / "recipe-runner-rs"
        binary.write_text("", encoding="utf-8")
        binary.chmod(0o777)

        with patch("amplihack.recipes.rust_runner.find_rust_binary", return_value=str(binary)):
            with pytest.raises(RuntimeError, match="world-writable"):
                run_recipe_via_rust("test-recipe")

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
    def test_normalizes_relative_recipe_dirs_against_working_dir(
        self, mock_run, mock_find, tmp_path
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )
        working_dir = tmp_path / "worktree"
        working_dir.mkdir()
        run_recipe_via_rust(
            "test-recipe",
            recipe_dirs=["amplifier-bundle/recipes"],
            working_dir=str(working_dir),
        )
        cmd = mock_run.call_args[0][0]
        idx = cmd.index("-R")
        assert cmd[idx + 1] == str(working_dir / "amplifier-bundle/recipes")

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("subprocess.run")
    def test_injects_execution_root_into_context_and_cwd(self, mock_run, mock_find, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._make_rust_output(),
            stderr="",
        )

        run_recipe_via_rust(
            "test-recipe",
            user_context={"task_description": "hello"},
            working_dir=str(tmp_path),
        )

        cmd = mock_run.call_args[0][0]
        kwargs = mock_run.call_args.kwargs
        execution_root_flag = f"execution_root={tmp_path.resolve()}"
        assert execution_root_flag in cmd
        assert kwargs["cwd"] == str(tmp_path.resolve())

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
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )
        ensure_rust_recipe_runner(quiet=True)
        assert mock_run.call_args[1].get("timeout") == 120


# ============================================================================
# Engine selection (run_recipe_by_name)
# ============================================================================


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
            args=[],
            returncode=0,
            stdout="",
            stderr="",
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
            args=[],
            returncode=1,
            stdout="",
            stderr="error",
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
        # Banner emitted to stderr by both run_recipe_via_rust and _execute_rust_command
        captured = streamed_stderr.getvalue()
        assert "[amplihack]" in captured, "startup banner must appear in stderr"
        assert "test-recipe" in captured, "recipe name must appear in banner"
        # Progress lines still streamed
        assert "▶ classify-and-decompose" in captured
        # Issue #3049: no timeout should be passed to process.wait()
        assert fake.timeout is None


# ============================================================================
# Progress file tests
# ============================================================================


class TestProgressFile:
    """Tests for _write_progress_file() and get_recipe_progress()."""

    def test_write_progress_file_creates_file(self, tmp_path):
        """_write_progress_file() creates the file at the expected temp path."""
        pid = os.getpid()
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            path = _write_progress_file(
                "test-recipe",
                current_step=1,
                total_steps=5,
                step_name="init",
                elapsed_seconds=1.5,
                status="running",
                pid=pid,
            )
        assert path.exists(), "progress file must be created"
        # Filename must embed recipe name and PID
        assert "test-recipe" in path.name or "test_recipe" in path.name
        assert str(pid) in path.name

    def test_write_progress_file_correct_schema(self, tmp_path):
        """_write_progress_file() writes valid JSON with all required fields."""
        pid = os.getpid()
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            path = _write_progress_file(
                "my-recipe",
                current_step=2,
                total_steps=10,
                step_name="build",
                elapsed_seconds=3.7,
                status="completed",
                pid=pid,
                last_output_at=2.5,
                silent_for_seconds=1.2,
            )
        data = json.loads(path.read_text())
        assert data["recipe_name"] == "my-recipe"
        assert data["current_step"] == 2
        assert data["total_steps"] == 10
        assert data["step_name"] == "build"
        assert abs(data["elapsed_seconds"] - 3.7) < 0.05
        assert data["status"] == "completed"
        assert data["pid"] == pid
        assert data["runner_pid"] == pid
        assert data["owner_uid"] == (os.geteuid() if hasattr(os, "geteuid") else None)
        assert "updated_at" in data
        assert abs(data["last_output_at"] - 2.5) < 0.05
        assert abs(data["silent_for_seconds"] - 1.2) < 0.05

    def test_get_recipe_progress_reads_file_back(self, tmp_path):
        """get_recipe_progress() reads back progress written by _write_progress_file()."""
        pid = os.getpid()
        # Write the progress file into tmp_path
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            _write_progress_file(
                "workflow-recipe",
                current_step=3,
                total_steps=7,
                step_name="test-step",
                elapsed_seconds=12.0,
                status="running",
                pid=pid,
                last_output_at=9.0,
                silent_for_seconds=3.0,
                last_heartbeat_at=8.0,
                heartbeat_interval_seconds=15,
                heartbeat_silence_seconds=30,
            )

        # Now query via get_recipe_progress, patching gettempdir in dev_intent_router
        router = _import_dev_intent_router()
        with patch.object(router._tempfile, "gettempdir", return_value=str(tmp_path)):
            result = router.get_recipe_progress("workflow-recipe")

        assert result is not None, "should find the progress file"
        assert result["current_step"] == 3
        assert result["total_steps"] == 7
        assert result["step_name"] == "test-step"
        assert abs(result["elapsed_seconds"] - 12.0) < 0.05
        assert result["status"] == "running"

    def test_get_recipe_progress_returns_none_when_no_file(self, tmp_path):
        """get_recipe_progress() returns None when no matching file exists."""
        router = _import_dev_intent_router()
        with patch.object(router._tempfile, "gettempdir", return_value=str(tmp_path)):
            result = router.get_recipe_progress("nonexistent-recipe")
        assert result is None

    def test_get_recipe_progress_none_recipe_name_finds_any(self, tmp_path):
        """get_recipe_progress(None) returns the most recent progress file."""
        pid = os.getpid()
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            _write_progress_file(
                "some-recipe",
                current_step=1,
                total_steps=3,
                step_name="first",
                elapsed_seconds=0.5,
                status="running",
                pid=pid,
            )

        router = _import_dev_intent_router()
        with patch.object(router._tempfile, "gettempdir", return_value=str(tmp_path)):
            result = router.get_recipe_progress()  # recipe_name=None

        assert result is not None
        assert result["step_name"] == "first"
        assert result["status"] == "running"

    def test_get_recipe_progress_includes_parallel_status_sidecar(self, tmp_path):
        """Parallel status sidecars should not break basic progress discovery."""
        pid = os.getpid()
        parallel_status_path = tmp_path / "parallel-status-explicit.json"
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            _write_progress_file(
                "workflow-recipe",
                current_step=1,
                total_steps=2,
                step_name="launch-parallel-round-1",
                elapsed_seconds=4.0,
                status="running",
                pid=pid,
                last_output_at=3.0,
                silent_for_seconds=1.0,
                last_heartbeat_at=2.5,
                heartbeat_interval_seconds=15,
                heartbeat_silence_seconds=30,
                parallel_status_path=str(parallel_status_path),
            )

        parallel_status_path.write_text(
            json.dumps(
                {
                    "counts": {"total": 2, "running": 1, "completed": 1, "failed": 0},
                    "workstreams": [
                        {"issue": 101, "status": "running"},
                        {"issue": 102, "status": "completed"},
                    ],
                }
            ),
            encoding="utf-8",
        )

        router = _import_dev_intent_router()
        with patch.object(router._tempfile, "gettempdir", return_value=str(tmp_path)):
            result = router.get_recipe_progress("workflow-recipe")

        assert result is not None
        assert result["step_name"] == "launch-parallel-round-1"
        assert result["status"] == "running"
        assert "parallel_status" not in result

    def test_get_recipe_progress_prefers_explicit_parallel_status_file(self, tmp_path):
        """Explicit sidecar env vars should not break basic progress lookup."""
        pid = os.getpid()
        with patch(
            "amplihack.recipes.rust_runner_execution.tempfile.gettempdir",
            return_value=str(tmp_path),
        ):
            _write_progress_file(
                "workflow-recipe",
                current_step=1,
                total_steps=2,
                step_name="launch-parallel-round-1",
                elapsed_seconds=4.0,
                status="running",
                pid=pid,
                last_output_at=3.0,
                silent_for_seconds=1.0,
            )

        auto_discovered_path = tmp_path / "amplihack-parallel-status-auto.json"
        auto_discovered_path.write_text(
            json.dumps({"counts": {"total": 9, "running": 9, "completed": 0, "failed": 0}}),
            encoding="utf-8",
        )
        explicit_status_path = tmp_path / "parallel-status-explicit.json"
        explicit_status_path.write_text(
            json.dumps({"counts": {"total": 2, "running": 1, "completed": 1, "failed": 0}}),
            encoding="utf-8",
        )

        router = _import_dev_intent_router()
        with (
            patch.object(router._tempfile, "gettempdir", return_value=str(tmp_path)),
            patch.dict(os.environ, {"AMPLIHACK_PARALLEL_STATUS_FILE": str(explicit_status_path)}),
        ):
            result = router.get_recipe_progress("workflow-recipe")

        assert result is not None
        assert result["step_name"] == "launch-parallel-round-1"
        assert result["status"] == "running"
        assert "parallel_status" not in result
