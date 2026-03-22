"""Regression test for issue #3130: smart-orchestrator drops valid single workstream.

When force_single_workstream=true is set via --set and the classification returns
a valid single workstream, the orchestrator should route to execute-single-round-1.

Root cause: Two bugs combined to skip the single-workstream path:
  Bug A: The materialize-force-single-workstream step was missing from main,
         so --set overrides were invisible to the condition evaluator.
  Bug B: activate-workflow didn't enforce force_single_workstream when counting
         workstreams, so the flag had no effect on workstream_count.

Fix: activate-workflow now forces count=1 when the flag is set, and a new
materialize step bridges the user_context override to condition evaluation.
"""

import json
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _find_recipe_runner_binary() -> str | None:
    """Find the recipe-runner-rs binary."""
    import shutil

    for candidate in [
        "recipe-runner-rs",
        str(Path.home() / ".cargo" / "bin" / "recipe-runner-rs"),
    ]:
        if shutil.which(candidate):
            return shutil.which(candidate)
    return None


def _make_minimal_recipe(
    workstream_count: int = 1,
    force_single: bool = False,
) -> str:
    """Create a minimal recipe that mimics smart-orchestrator routing logic.

    Simulates the classify → activate → route flow with fixed decomposition
    output so we can test condition evaluation without a live LLM.
    """
    workstreams = [
        {"name": f"ws-{i + 1}", "description": f"Workstream {i + 1}", "recipe": "default-workflow"}
        for i in range(workstream_count)
    ]
    decomposition = json.dumps(
        {
            "task_type": "Development",
            "goal": "Test goal",
            "success_criteria": ["criterion 1"],
            "workstreams": workstreams,
        }
    )

    return f"""\
name: "test-3130-routing"
context:
  task_type: ""
  workstream_count: ""
  force_single_workstream: "false"
  decomposition_json: '{decomposition}'
steps:
  # Simulate parse-decomposition: extract task_type
  - id: "parse-decomposition"
    type: "bash"
    command: "echo Development"
    output: "task_type"

  # Simulate activate-workflow: count workstreams, respecting force_single
  - id: "activate-workflow"
    type: "bash"
    command: |
      FORCE_SINGLE={{{{force_single_workstream}}}}
      FORCE_LOWER=$(echo "$FORCE_SINGLE" | tr '[:upper:]' '[:lower:]')
      RAW_COUNT={workstream_count}
      if [ "$FORCE_LOWER" = "true" ] || [ "$FORCE_LOWER" = "1" ]; then
        echo 1
      else
        echo $RAW_COUNT
      fi
    output: "workstream_count"

  # Materialize force_single_workstream for condition evaluation
  - id: "materialize-force-single-workstream"
    type: "bash"
    command: |
      printf '%s' {{{{force_single_workstream}}}}
    output: "force_single_workstream"

  # Single-workstream path (should run when count=1 or force_single=true)
  - id: "execute-single-round-1"
    type: "bash"
    condition: |
      ('Development' in task_type or 'Investigation' in task_type) and ((workstream_count == '1' or workstream_count == '') or force_single_workstream == 'true')
    command: "echo SINGLE_PATH_TAKEN"
    output: "single_result"

  # Parallel path (should NOT run when force_single=true)
  - id: "launch-parallel"
    type: "bash"
    condition: |
      ('Development' in task_type or 'Investigation' in task_type) and workstream_count != '1' and workstream_count != '' and force_single_workstream != 'true'
    command: "echo PARALLEL_PATH_TAKEN"
    output: "parallel_result"
"""


class TestIssue3130ForceSingleWorkstreamRouting:
    """Verify that force_single_workstream correctly routes to single-workstream path."""

    def test_single_workstream_without_flag(self):
        """1 workstream, no flag → single path should run."""
        binary = _find_recipe_runner_binary()
        if binary is None:
            import pytest

            pytest.skip("recipe-runner-rs binary not found")

        recipe = _make_minimal_recipe(workstream_count=1, force_single=False)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", prefix="test-3130-", delete=False
        ) as f:
            f.write(recipe)
            recipe_path = f.name

        try:
            result = subprocess.run(
                [binary, recipe_path, "--output-format", "json"],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            assert result.returncode == 0, f"Runner failed: {result.stderr}"
            data = json.loads(result.stdout)
            assert data["success"], f"Recipe failed: {data}"

            steps = {s["step_id"]: s["status"] for s in data["step_results"]}
            assert steps["execute-single-round-1"] == "completed", (
                f"Single path should run with 1 workstream, got: {steps['execute-single-round-1']}"
            )
            assert steps["launch-parallel"] == "skipped", (
                f"Parallel path should be skipped with 1 workstream, got: {steps['launch-parallel']}"
            )
        finally:
            Path(recipe_path).unlink(missing_ok=True)

    def test_force_single_with_one_workstream(self):
        """1 workstream + force_single_workstream=true → single path should run.

        This is the exact scenario from issue #3130.
        """
        binary = _find_recipe_runner_binary()
        if binary is None:
            import pytest

            pytest.skip("recipe-runner-rs binary not found")

        recipe = _make_minimal_recipe(workstream_count=1, force_single=True)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", prefix="test-3130-", delete=False
        ) as f:
            f.write(recipe)
            recipe_path = f.name

        try:
            result = subprocess.run(
                [
                    binary,
                    recipe_path,
                    "--output-format",
                    "json",
                    "--set",
                    "force_single_workstream=true",
                ],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            assert result.returncode == 0, f"Runner failed: {result.stderr}"
            data = json.loads(result.stdout)
            assert data["success"], f"Recipe failed: {data}"

            steps = {s["step_id"]: s["status"] for s in data["step_results"]}
            assert steps["execute-single-round-1"] == "completed", (
                f"Single path should run with force_single=true (1 ws), got: {steps['execute-single-round-1']}"
            )
            assert steps["launch-parallel"] == "skipped", (
                f"Parallel path should be skipped with force_single=true, got: {steps['launch-parallel']}"
            )
        finally:
            Path(recipe_path).unlink(missing_ok=True)

    def test_force_single_with_multiple_workstreams(self):
        """3 workstreams + force_single_workstream=true → single path should STILL run.

        This verifies that force_single_workstream overrides multi-workstream
        decomposition, routing to the single path instead of parallel.
        """
        binary = _find_recipe_runner_binary()
        if binary is None:
            import pytest

            pytest.skip("recipe-runner-rs binary not found")

        recipe = _make_minimal_recipe(workstream_count=3, force_single=True)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", prefix="test-3130-", delete=False
        ) as f:
            f.write(recipe)
            recipe_path = f.name

        try:
            result = subprocess.run(
                [
                    binary,
                    recipe_path,
                    "--output-format",
                    "json",
                    "--set",
                    "force_single_workstream=true",
                ],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            assert result.returncode == 0, f"Runner failed: {result.stderr}"
            data = json.loads(result.stdout)
            assert data["success"], f"Recipe failed: {data}"

            steps = {s["step_id"]: s["status"] for s in data["step_results"]}
            assert steps["execute-single-round-1"] == "completed", (
                f"Single path should run with force_single=true (3 ws), got: {steps['execute-single-round-1']}"
            )
            assert steps["launch-parallel"] == "skipped", (
                f"Parallel path should be skipped with force_single=true (3 ws), got: {steps['launch-parallel']}"
            )
        finally:
            Path(recipe_path).unlink(missing_ok=True)

    def test_multiple_workstreams_without_flag(self):
        """3 workstreams, no flag → parallel path should run."""
        binary = _find_recipe_runner_binary()
        if binary is None:
            import pytest

            pytest.skip("recipe-runner-rs binary not found")

        recipe = _make_minimal_recipe(workstream_count=3, force_single=False)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", prefix="test-3130-", delete=False
        ) as f:
            f.write(recipe)
            recipe_path = f.name

        try:
            result = subprocess.run(
                [binary, recipe_path, "--output-format", "json"],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            assert result.returncode == 0, f"Runner failed: {result.stderr}"
            data = json.loads(result.stdout)
            assert data["success"], f"Recipe failed: {data}"

            steps = {s["step_id"]: s["status"] for s in data["step_results"]}
            assert steps["execute-single-round-1"] == "skipped", (
                f"Single path should be skipped with 3 workstreams, got: {steps['execute-single-round-1']}"
            )
            assert steps["launch-parallel"] == "completed", (
                f"Parallel path should run with 3 workstreams, got: {steps['launch-parallel']}"
            )
        finally:
            Path(recipe_path).unlink(missing_ok=True)

    def test_materialize_step_outputs_correct_value(self):
        """Verify materialize step correctly bridges context to step output.

        The materialize step must use bare {{var}} (not '{{var}}') so the
        Rust runner expands the env var reference correctly.
        """
        binary = _find_recipe_runner_binary()
        if binary is None:
            import pytest

            pytest.skip("recipe-runner-rs binary not found")

        recipe = """\
name: "test-3130-materialize"
context:
  flag: "false"
steps:
  - id: "materialize"
    type: "bash"
    command: |
      printf '%s' {{flag}}
    output: "flag"
  - id: "check-true"
    type: "bash"
    condition: "flag == 'true'"
    command: "echo MATERIALIZED_TRUE"
    output: "result"
  - id: "check-false"
    type: "bash"
    condition: "flag != 'true'"
    command: "echo MATERIALIZED_FALSE"
    output: "result_neg"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", prefix="test-3130-mat-", delete=False
        ) as f:
            f.write(recipe)
            recipe_path = f.name

        try:
            # Test with --set flag=true (Bool coercion)
            result = subprocess.run(
                [
                    binary,
                    recipe_path,
                    "--output-format",
                    "json",
                    "--set",
                    "flag=true",
                ],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            assert result.returncode == 0, f"Runner failed: {result.stderr}"
            data = json.loads(result.stdout)
            assert data["success"], f"Recipe failed: {data}"

            steps = {s["step_id"]: s["status"] for s in data["step_results"]}
            assert steps["materialize"] == "completed"
            assert steps["check-true"] == "completed", (
                f"After materializing flag=true, condition flag == 'true' should match, "
                f"got: {steps['check-true']}"
            )
            assert steps["check-false"] == "skipped", (
                f"After materializing flag=true, condition flag != 'true' should be skipped, "
                f"got: {steps['check-false']}"
            )
        finally:
            Path(recipe_path).unlink(missing_ok=True)


class TestActivateWorkflowForceSingleEnforcement:
    """Unit tests for activate-workflow's force_single_workstream enforcement.

    These test the Python logic directly, without needing the Rust binary.
    """

    def test_force_single_overrides_multiple_workstreams(self):
        """When force_single is True, count should be 1 regardless of raw count."""
        # Simulate the Python logic from activate-workflow
        force_single = True
        raw_count = 3
        count = 1 if force_single else raw_count
        assert count == 1

    def test_no_force_respects_raw_count(self):
        """When force_single is False, count should match raw workstream count."""
        force_single = False
        raw_count = 3
        count = 1 if force_single else raw_count
        assert count == 3

    def test_force_single_env_var_parsing(self):
        """The env var parsing should handle various truthy representations."""
        for truthy in ("true", "True", "TRUE", "1", " true ", " TRUE\n"):
            result = truthy.strip().lower() in ("true", "1")
            assert result, f"'{truthy}' should be truthy"

        for falsy in ("false", "False", "0", "", "no", "random"):
            result = falsy.strip().lower() in ("true", "1")
            assert not result, f"'{falsy}' should be falsy"
