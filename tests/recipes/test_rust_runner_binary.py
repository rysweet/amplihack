"""Tests for Rust runner binary discovery, installation, and version checks."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import pytest

from amplihack.recipes.rust_runner import (
    RustRunnerVersionError,
    check_runner_version,
    ensure_rust_recipe_runner,
    find_rust_binary,
    get_runner_version,
    is_rust_runner_available,
    run_recipe_via_rust,
)


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


class TestRunnerVersionChecks:
    """Tests for runner version discovery and enforcement."""

    @patch("subprocess.run")
    def test_get_runner_version_parses_semver_output(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="recipe-runner 0.2.5\n",
            stderr="",
        )

        assert get_runner_version("/usr/bin/recipe-runner-rs") == "0.2.5"

    @patch("subprocess.run", side_effect=OSError("boom"))
    def test_get_runner_version_returns_none_on_subprocess_error(self, mock_run):
        assert get_runner_version("/usr/bin/recipe-runner-rs") is None

    @patch("amplihack.recipes.rust_runner_binary.get_runner_version", return_value="0.0.9")
    def test_check_runner_version_rejects_old_runner(self, _mock_version):
        assert check_runner_version("/usr/bin/recipe-runner-rs") is False

    @patch("amplihack.recipes.rust_runner_binary.get_runner_version", return_value=None)
    def test_check_runner_version_rejects_unknown_runner_version(self, _mock_version):
        assert check_runner_version("/usr/bin/recipe-runner-rs") is False

    @patch("amplihack.recipes.rust_runner_binary.get_runner_version", return_value="dev-build")
    def test_check_runner_version_rejects_unparseable_version(self, _mock_version):
        assert check_runner_version("/usr/bin/recipe-runner-rs") is False

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("amplihack.recipes.rust_runner_binary.get_runner_version", return_value="0.0.9")
    @patch("amplihack.recipes.rust_runner_binary.ensure_rust_recipe_runner", return_value=False)
    def test_run_recipe_raises_when_runner_version_is_too_old(
        self,
        _mock_ensure,
        _mock_get_version,
        _mock_find,
    ):
        with pytest.raises(RustRunnerVersionError, match="0.0.9"):
            run_recipe_via_rust("test-recipe")

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("amplihack.recipes.rust_runner_binary.get_runner_version", return_value=None)
    @patch("amplihack.recipes.rust_runner_binary.ensure_rust_recipe_runner", return_value=False)
    def test_run_recipe_raises_when_runner_version_is_unknown(
        self,
        _mock_ensure,
        _mock_get_version,
        _mock_find,
    ):
        with pytest.raises(RustRunnerVersionError, match="Could not determine"):
            run_recipe_via_rust("test-recipe")

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("amplihack.recipes.rust_runner_binary.get_runner_version", return_value="dev-build")
    @patch("amplihack.recipes.rust_runner_binary.ensure_rust_recipe_runner", return_value=False)
    def test_run_recipe_raises_when_runner_version_is_unparseable(
        self,
        _mock_ensure,
        _mock_get_version,
        _mock_find,
    ):
        with pytest.raises(RustRunnerVersionError, match="unparseable version 'dev-build'"):
            run_recipe_via_rust("test-recipe")


_VALID_RUST_OUTPUT = json.dumps(
    {
        "recipe_name": "test-recipe",
        "success": True,
        "step_results": [
            {"step_id": "s1", "status": "Completed", "output": "ok", "error": ""},
        ],
        "context": {},
    }
)


class TestAutoUpdate:
    """Tests for the auto-update path triggered on version mismatch in _find_rust_binary()."""

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch(
        "amplihack.recipes.rust_runner_binary.get_runner_version",
        side_effect=["0.0.9", "0.3.4"],
    )
    @patch("amplihack.recipes.rust_runner_binary.ensure_rust_recipe_runner", return_value=True)
    @patch("subprocess.run")
    def test_auto_update_success_proceeds_to_execution(
        self, mock_run, _mock_ensure, _mock_version, _mock_find
    ):
        """Outdated binary + successful auto-update still executes the recipe."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=_VALID_RUST_OUTPUT, stderr=""
        )

        result = run_recipe_via_rust("test-recipe")

        assert result.success is True
        _mock_ensure.assert_called_once()

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("amplihack.recipes.rust_runner_binary.get_runner_version", return_value="0.0.9")
    @patch("amplihack.recipes.rust_runner_binary.ensure_rust_recipe_runner", return_value=False)
    def test_auto_update_failure_raises_version_error(
        self, _mock_ensure, _mock_version, _mock_find
    ):
        """Outdated binary + failed update still raises the version error."""
        with pytest.raises(RustRunnerVersionError, match="0.0.9"):
            run_recipe_via_rust("test-recipe")

    @patch.dict("os.environ", {"RECIPE_RUNNER_AUTO_UPDATE": "0"})
    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary", return_value="/usr/bin/recipe-runner-rs"
    )
    @patch("amplihack.recipes.rust_runner_binary.get_runner_version", return_value="0.0.9")
    @patch("amplihack.recipes.rust_runner_binary.ensure_rust_recipe_runner", return_value=True)
    def test_auto_update_disabled_raises_immediately(self, mock_ensure, _mock_version, _mock_find):
        """RECIPE_RUNNER_AUTO_UPDATE=0 skips auto-update and raises immediately."""
        with pytest.raises(RustRunnerVersionError, match="0.0.9"):
            run_recipe_via_rust("test-recipe")

        mock_ensure.assert_not_called()
