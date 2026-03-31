"""Gadugi outside-in tests for Issue #3539 — Fix startup warnings.

Executes the behavioral assertions defined in:
  - issue-3539-no-startup-stderr-warnings.yaml
  - issue-3539-dep-check-quiet-and-worktree-import.yaml

Verifies that core amplihack modules import silently without emitting
WARNING messages to stderr, and that the new worktree.git_utils package
is properly accessible.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

GADUGI_DIR = Path(__file__).parent
SRC_DIR = Path(__file__).parent.parent.parent / "src"


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def scenario1():
    return load_yaml(GADUGI_DIR / "issue-3539-no-startup-stderr-warnings.yaml")


@pytest.fixture
def scenario2():
    return load_yaml(GADUGI_DIR / "issue-3539-dep-check-quiet-and-worktree-import.yaml")


# ──────────────────────────────────────────────────────────────────────────────
# YAML structure validation
# ──────────────────────────────────────────────────────────────────────────────


class TestScenarioStructure:
    """Validate gadugi YAML scenario files have correct structure."""

    def test_scenario1_has_required_fields(self, scenario1):
        s = scenario1["scenario"]
        assert s["name"]
        assert s["type"] in ("cli", "unit")
        assert "steps" in s
        assert len(s["steps"]) >= 3

    def test_scenario2_has_required_fields(self, scenario2):
        s = scenario2["scenario"]
        assert s["name"]
        assert s["type"] in ("cli", "unit")
        assert "steps" in s
        assert len(s["steps"]) >= 4

    def test_scenario1_tagged_correctly(self, scenario1):
        tags = scenario1["scenario"].get("tags", [])
        assert "startup-warnings" in tags
        assert "issue-3539" in tags

    def test_scenario2_tagged_correctly(self, scenario2):
        tags = scenario2["scenario"].get("tags", [])
        assert "dep-check" in tags
        assert "worktree" in tags


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 1: No startup stderr warnings — silent import
# ──────────────────────────────────────────────────────────────────────────────


class TestNoStartupStderrWarnings:
    """Verify key modules import without emitting WARNING to stderr."""

    def _capture_stderr_during_import(self, module_name: str) -> str:
        """Import module_name in a subprocess and return stderr output."""
        result = subprocess.run(
            [sys.executable, "-c", f"import {module_name}"],
            capture_output=True,
            text=True,
            cwd=str(SRC_DIR),
            env={**__import__("os").environ, "PYTHONPATH": str(SRC_DIR)},
        )
        return result.stderr

    def test_dep_check_no_warning_on_import(self):
        """dep_check must not emit WARNING before install attempt."""
        stderr = self._capture_stderr_during_import("amplihack.dep_check")
        assert "WARNING" not in stderr, f"dep_check emitted WARNING: {stderr!r}"
        assert "agent_framework not available" not in stderr, (
            f"dep_check still leaks availability message: {stderr!r}"
        )

    def test_microsoft_sdk_no_agent_framework_warning_on_import(self):
        """microsoft_sdk must not emit 'agent_framework not available' WARNING.

        Note: other unrelated warnings (e.g. amplihack_memory) are not in scope
        for Issue #3539 and are intentionally excluded from this assertion.
        """
        stderr = self._capture_stderr_during_import(
            "amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk"
        )
        # Only check for the specific warning this PR fixes — not all WARNINGs
        assert "agent_framework not available" not in stderr, (
            f"microsoft_sdk still emits 'agent_framework not available': {stderr!r}"
        )

    def test_re_enable_prompt_no_fallback_warning(self):
        """re_enable_prompt must not print 'git_utils not available' fallback warning."""
        stderr = self._capture_stderr_during_import("amplihack.power_steering.re_enable_prompt")
        assert "WARNING" not in stderr, f"re_enable_prompt emitted WARNING: {stderr!r}"
        assert "git_utils not available" not in stderr, (
            f"re_enable_prompt still uses fallback path: {stderr!r}"
        )
        assert "fallback runtime dir" not in stderr, (
            f"re_enable_prompt still uses fallback runtime dir: {stderr!r}"
        )

    def test_full_import_set_produces_zero_warning_lines(self):
        """Importing dep_check + session together must produce zero WARNING lines."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import amplihack.dep_check; import amplihack.session",
            ],
            capture_output=True,
            text=True,
            cwd=str(SRC_DIR),
            env={**__import__("os").environ, "PYTHONPATH": str(SRC_DIR)},
        )
        warning_lines = [line for line in result.stderr.splitlines() if "WARNING" in line]
        assert not warning_lines, (
            f"Found {len(warning_lines)} WARNING line(s) on stderr: {warning_lines}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 2: dep_check quiet pre-install check + worktree git_utils import
# ──────────────────────────────────────────────────────────────────────────────


class TestDepCheckQuietAndWorktreeImport:
    """Verify _collect_dep_status and worktree.git_utils behavior."""

    def test_collect_dep_status_returns_dep_check_result(self):
        """_collect_dep_status() must return DepCheckResult without printing."""
        # Import via subprocess to get a clean stderr capture
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from amplihack.dep_check import _collect_dep_status; "
                    "r = _collect_dep_status(); "
                    "print(type(r).__name__)"
                ),
            ],
            capture_output=True,
            text=True,
            cwd=str(SRC_DIR),
            env={**__import__("os").environ, "PYTHONPATH": str(SRC_DIR)},
        )
        assert result.returncode == 0, f"_collect_dep_status crashed: {result.stderr}"
        assert "DepCheckResult" in result.stdout, (
            f"Expected DepCheckResult, got stdout={result.stdout!r}"
        )
        warning_lines = [line for line in result.stderr.splitlines() if "WARNING" in line]
        assert not warning_lines, f"_collect_dep_status emitted WARNING(s): {warning_lines}"

    def test_worktree_git_utils_importable(self):
        """amplihack.worktree.git_utils must be importable as a package module."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from amplihack.worktree.git_utils import get_shared_runtime_dir; "
                    "print('OK'); print(callable(get_shared_runtime_dir))"
                ),
            ],
            capture_output=True,
            text=True,
            cwd=str(SRC_DIR),
            env={**__import__("os").environ, "PYTHONPATH": str(SRC_DIR)},
        )
        assert result.returncode == 0, f"worktree.git_utils import failed: {result.stderr}"
        assert "OK" in result.stdout
        assert "True" in result.stdout

    def test_worktree_package_importable(self):
        """amplihack.worktree must be importable as a package."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import amplihack.worktree; print('WORKTREE_PKG_OK')",
            ],
            capture_output=True,
            text=True,
            cwd=str(SRC_DIR),
            env={**__import__("os").environ, "PYTHONPATH": str(SRC_DIR)},
        )
        assert result.returncode == 0, f"worktree package import failed: {result.stderr}"
        assert "WORKTREE_PKG_OK" in result.stdout

    def test_worktree_init_exists(self):
        """src/amplihack/worktree/__init__.py must exist (package, not bare module)."""
        init_path = SRC_DIR / "amplihack" / "worktree" / "__init__.py"
        assert init_path.exists(), f"Missing {init_path} — worktree is not a package"

    def test_worktree_git_utils_module_exists(self):
        """src/amplihack/worktree/git_utils.py must exist."""
        module_path = SRC_DIR / "amplihack" / "worktree" / "git_utils.py"
        assert module_path.exists(), f"Missing {module_path}"

    def test_get_shared_runtime_dir_returns_string(self):
        """get_shared_runtime_dir() must return a non-empty string without crashing."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from amplihack.worktree.git_utils import get_shared_runtime_dir; "
                    "import os; r = get_shared_runtime_dir(os.getcwd()); "
                    "print('TYPE=' + type(r).__name__); print('NONEMPTY=' + str(bool(r)))"
                ),
            ],
            capture_output=True,
            text=True,
            cwd=str(SRC_DIR),
            env={**__import__("os").environ, "PYTHONPATH": str(SRC_DIR)},
        )
        assert result.returncode == 0, f"get_shared_runtime_dir() crashed: {result.stderr}"
        assert "TYPE=str" in result.stdout
        assert "NONEMPTY=True" in result.stdout
        assert "Error" not in result.stderr
