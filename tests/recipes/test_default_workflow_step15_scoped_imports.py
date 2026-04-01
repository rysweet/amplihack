"""TDD contract tests for scoped publish import validation wiring in step-15 (#4064)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RECIPE_PATH = Path("amplifier-bundle/recipes/default-workflow.yaml")


@pytest.fixture(scope="module")
def step_15() -> dict:
    with open(RECIPE_PATH, encoding="utf-8") as handle:
        recipe = yaml.safe_load(handle)

    for step in recipe["steps"]:
        if step.get("id") == "step-15-commit-push":
            return step

    raise KeyError("step-15-commit-push not found")


def test_step_15_builds_publish_scope_before_running_import_validation(step_15: dict):
    command = step_15["command"]

    assert "build_publish_validation_scope.py" in command
    assert re.search(r"check_imports\.py\s+--files-from\b", command), command
    assert command.index("build_publish_validation_scope.py") < command.index("check_imports.py")


def test_step_15_consumes_publish_manifest_and_writes_validation_scope(step_15: dict):
    command = step_15["command"]

    assert "--manifest" in command
    assert "--output" in command


def test_step_15_excludes_claude_scenarios_from_publish_validation_scope(step_15: dict):
    command = step_15["command"]

    assert "--exclude-claude-scenarios" in command


def test_step_15_reports_scope_counts(step_15: dict):
    command = step_15["command"]

    assert "seed_count" in command
    assert "expanded_local_dep_count" in command
    assert "validated_count" in command


def test_step_15_treats_empty_python_scope_as_explicit_success(step_15: dict):
    command = step_15["command"]

    assert re.search(r"-eq\s+0", command), command
    assert "validated_count" in command
    assert "no python" in command.lower() or "empty python surface" in command.lower()


def test_step_15_never_invokes_repo_wide_check_imports_fallback(step_15: dict):
    command = step_15["command"]
    invocations = re.findall(r"[^\n]*check_imports\.py[^\n]*", command)

    assert invocations, "step-15 must invoke check_imports.py"
    assert all("--files-from" in invocation for invocation in invocations), invocations


def test_step_15_runs_scoped_validation_before_git_commit(step_15: dict):
    command = step_15["command"]

    assert "git commit -m" in command
    assert command.index("check_imports.py") < command.index("git commit -m")


def test_step_15_runs_check_imports_with_scrubbed_environment(step_15: dict):
    command = step_15["command"]

    assert "env -i" in command
    assert 'PATH="${PATH:-}"' in command
    assert "PYTHONNOUSERSITE=1" in command
    assert command.index("env -i") < command.index("check_imports.py")


def test_step_15_skips_repo_wide_check_imports_hook_after_scoped_validation(step_15: dict):
    command = step_15["command"]

    assert "SKIP=check-imports" in command
    assert re.search(r"SKIP=check-imports[^\n]*\s+git commit -m", command), command
