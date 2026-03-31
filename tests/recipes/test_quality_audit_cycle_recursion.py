"""Runtime-style tests for quality-audit-cycle recursion (#3879).

These tests execute the bash commands embedded in the recipe with controlled
template substitution so we can verify the new explicit recursion edge without
depending on live reviewer-agent availability or rate limits.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

RECIPE_PATH = Path("amplifier-bundle/recipes/quality-audit-cycle.yaml")


@pytest.fixture(scope="module")
def recipe() -> dict:
    if not RECIPE_PATH.exists():
        pytest.skip("quality-audit-cycle.yaml not found")
    return yaml.safe_load(RECIPE_PATH.read_text(encoding="utf-8"))


def _step_by_id(recipe: dict, step_id: str) -> dict:
    for step in recipe["steps"]:
        if step.get("id") == step_id:
            return step
    pytest.fail(f"Step {step_id!r} not found in recipe")


def _render_templates(command: str, values: dict[str, str]) -> str:
    rendered = command
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _run_bash(
    script: str,
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
    timeout: int = 20,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", "-c", script],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
        timeout=timeout,
    )


class TestRecursiveCycleStepRuntime:
    """Exercise the recursive bash step with a fake run_recipe_by_name backend."""

    def test_recursive_step_reinvokes_recipe_and_emits_final_report(self, recipe, tmp_path):
        step = _step_by_id(recipe, "run-recursive-cycle")
        fake_root = tmp_path / "fake_py"
        pkg_dir = fake_root / "amplihack"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

        calls_file = tmp_path / "calls.json"
        (pkg_dir / "recipes.py").write_text(
            """
import json
import os
from pathlib import Path


class Result:
    def __init__(self, context):
        self.context = context


def run_recipe_by_name(name, user_context, progress=False):
    Path(os.environ["CALLS_FILE"]).write_text(
        json.dumps(
            {
                "name": name,
                "user_context": user_context,
                "progress": progress,
            }
        ),
        encoding="utf-8",
    )
    return Result(
        {
            "final_report": {
                "cycle_number": user_context["cycle_number"],
                "recurse_decision": "STOP",
                "summary": "recursive summary",
                "self_improvement_results": "SELF-IMPROVEMENT: CLEAN",
                "target_path": user_context["target_path"],
            }
        }
    )
""".strip()
            + "\n",
            encoding="utf-8",
        )

        cycle_history = '{\n  "cycles": [\n    {"cycle": 1, "validated": []}\n  ]\n}'
        command = _render_templates(
            step["command"],
            {
                "recurse_decision": "CONTINUE:2",
                "cycle_history": cycle_history,
                "repo_path": ".",
                "target_path": str(tmp_path / "target"),
                "min_cycles": "2",
                "max_cycles": "3",
                "validation_threshold": "3",
                "severity_threshold": "medium",
                "module_loc_limit": "300",
                "fix_all_per_cycle": "true",
                "categories": "security,reliability",
                "output_dir": str(tmp_path / "out"),
            },
        )

        env = os.environ.copy()
        env["PYTHONPATH"] = str(fake_root)
        env["CALLS_FILE"] = str(calls_file)

        result = _run_bash(command, tmp_path, env=env)
        assert result.returncode == 0, (
            "run-recursive-cycle should execute successfully with a valid "
            f"CONTINUE target.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        final_report = json.loads(result.stdout)
        assert final_report["cycle_number"] == "2"
        assert final_report["recurse_decision"] == "STOP"
        assert final_report["summary"] == "recursive summary"
        assert final_report["self_improvement_results"] == "SELF-IMPROVEMENT: CLEAN"

        recorded_call = json.loads(calls_file.read_text(encoding="utf-8"))
        assert recorded_call["name"] == "quality-audit-cycle"
        assert recorded_call["progress"] is True
        assert recorded_call["user_context"]["cycle_number"] == "2"
        assert recorded_call["user_context"]["cycle_history"] == f"{cycle_history}\n"
        assert recorded_call["user_context"]["target_path"] == str(tmp_path / "target")

    def test_recursive_step_synthesizes_final_report_when_nested_context_is_legacy(
        self, recipe, tmp_path
    ):
        step = _step_by_id(recipe, "run-recursive-cycle")
        fake_root = tmp_path / "fake_py"
        pkg_dir = fake_root / "amplihack"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

        (pkg_dir / "recipes.py").write_text(
            """
class Result:
    def __init__(self, context):
        self.context = context


def run_recipe_by_name(name, user_context, progress=False):
    return Result(
        {
            "cycle_number": user_context["cycle_number"],
            "recurse_decision": "STOP",
            "summary": "legacy summary",
            "self_improvement_results": "legacy clean",
            "target_path": user_context["target_path"],
        }
    )
""".strip()
            + "\n",
            encoding="utf-8",
        )

        command = _render_templates(
            step["command"],
            {
                "task_description": "legacy fallback smoke",
                "recurse_decision": "CONTINUE:3",
                "cycle_history": '{"cycles":[]}',
                "repo_path": ".",
                "target_path": str(tmp_path / "legacy-target"),
                "min_cycles": "2",
                "max_cycles": "4",
                "validation_threshold": "3",
                "severity_threshold": "medium",
                "module_loc_limit": "300",
                "fix_all_per_cycle": "true",
                "categories": "security,reliability",
                "output_dir": str(tmp_path / "legacy-out"),
            },
        )

        env = os.environ.copy()
        env["PYTHONPATH"] = str(fake_root)

        result = _run_bash(command, tmp_path, env=env)
        assert result.returncode == 0, (
            "run-recursive-cycle should synthesize final_report when the nested "
            f"context uses legacy top-level fields.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        final_report = json.loads(result.stdout)
        assert final_report == {
            "cycle_number": "3",
            "recurse_decision": "STOP",
            "summary": "legacy summary",
            "self_improvement_results": "legacy clean",
            "target_path": str(tmp_path / "legacy-target"),
        }


class TestFinalReportRuntime:
    """Exercise the terminal report-normalization step directly."""

    def test_final_report_step_emits_json_payload(self, recipe, tmp_path):
        step = _step_by_id(recipe, "final-report")
        command = _render_templates(
            step["command"],
            {
                "summary": "Summary line 1\nSummary line 2",
                "self_improvement_results": "SELF-IMPROVEMENT: CLEAN",
                "cycle_number": "2",
                "recurse_decision": "STOP",
                "target_path": str(tmp_path / "target"),
            },
        )

        result = _run_bash(command, tmp_path)
        assert result.returncode == 0, (
            "final-report should emit valid JSON.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        payload = json.loads(result.stdout)
        assert payload == {
            "cycle_number": "2",
            "recurse_decision": "STOP",
            "summary": "Summary line 1\nSummary line 2\n",
            "self_improvement_results": "SELF-IMPROVEMENT: CLEAN\n",
            "target_path": str(tmp_path / "target"),
        }
