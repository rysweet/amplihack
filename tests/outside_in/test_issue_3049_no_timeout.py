"""Outside-in behavioral validation for issue #3049: remove recipe runner timeout.

Verifies that the run-time timeout was removed from rust_runner.py while the
install timeout remains intact.

Uses direct file reading instead of module import to avoid sys.path conflicts
with the .claude/tools namespace overlay (see outside_in/conftest.py).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Resolve the source file relative to the repo root.
_RUST_RUNNER_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "amplihack"
    / "recipes"
    / "rust_runner.py"
)


@pytest.fixture()
def rust_runner_source() -> str:
    """Return the raw source code of rust_runner.py."""
    return _RUST_RUNNER_PATH.read_text()


@pytest.fixture()
def rust_runner_ast(rust_runner_source: str) -> ast.Module:
    """Return the parsed AST of the rust_runner module."""
    return ast.parse(rust_runner_source)


class TestRunTimeoutRemoved:
    """Confirm the run-time timeout has been fully removed."""

    def test_no_run_timeout_function(self, rust_runner_source: str) -> None:
        """_run_timeout helper must not exist in the module."""
        assert "def _run_timeout" not in rust_runner_source

    def test_no_run_timeout_env_var(self, rust_runner_source: str) -> None:
        """RECIPE_RUNNER_RUN_TIMEOUT env var must not be referenced."""
        assert "RECIPE_RUNNER_RUN_TIMEOUT" not in rust_runner_source

    def test_execute_rust_command_subprocess_run_no_timeout(
        self, rust_runner_ast: ast.Module
    ) -> None:
        """subprocess.run inside _execute_rust_command must not have a timeout kwarg."""
        for node in ast.walk(rust_runner_ast):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name != "_execute_rust_command":
                continue
            # Find all subprocess.run calls in this function
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                func = child.func
                # Match subprocess.run(...)
                is_subprocess_run = (
                    isinstance(func, ast.Attribute)
                    and func.attr == "run"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "subprocess"
                )
                if not is_subprocess_run:
                    continue
                kwarg_names = [kw.arg for kw in child.keywords]
                assert "timeout" not in kwarg_names, (
                    "subprocess.run in _execute_rust_command must not have a timeout parameter"
                )
            return  # function found
        pytest.fail("_execute_rust_command function not found in module AST")


class TestInstallTimeoutPreserved:
    """Confirm the install timeout was NOT removed."""

    def test_install_timeout_function_exists(self, rust_runner_source: str) -> None:
        """_install_timeout helper must still be present."""
        assert "def _install_timeout" in rust_runner_source

    def test_install_timeout_env_var_referenced(self, rust_runner_source: str) -> None:
        """RECIPE_RUNNER_INSTALL_TIMEOUT env var must still be referenced."""
        assert "RECIPE_RUNNER_INSTALL_TIMEOUT" in rust_runner_source

    def test_install_timeout_returns_positive_int(self, rust_runner_ast: ast.Module) -> None:
        """_install_timeout function must exist and return an int from env/default."""
        found = False
        for node in ast.walk(rust_runner_ast):
            if isinstance(node, ast.FunctionDef) and node.name == "_install_timeout":
                found = True
                break
        assert found, "_install_timeout function not found in module AST"
