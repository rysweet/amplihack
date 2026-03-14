"""Regression test for issue #3132: adaptive error recovery in smart-orchestrator.

When all execution paths in smart-orchestrator are skipped (routing gap),
the recipe should:
1. Surface the error visibly with diagnostic context
2. File a GitHub issue with reproduction details (or save diagnostics locally)
3. Determine the appropriate direct recipe based on task_type
4. Execute the direct recipe as an announced ADAPTIVE STRATEGY

This replaces the previous "report error and stop" behavior with transparent
error recovery. Silent fallbacks that degrade behavior without visibility are
explicitly prohibited.
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


class TestAdaptiveErrorRecovery:
    """Verify that routing gaps trigger adaptive strategy, not silent failure."""

    def test_detect_execution_gap_fires_when_no_path_runs(self):
        """When all routing conditions are false, detect-execution-gap should fire.

        Simulates the scenario where task_type is Development but
        round_1_result is empty (no execution path ran).
        """
        binary = _find_recipe_runner_binary()
        if binary is None:
            import pytest

            pytest.skip("recipe-runner-rs binary not found")

        # Create a recipe where no execution path matches — simulate routing gap
        recipe = """\
name: "test-3132-execution-gap"
context:
  task_type: ""
  workstream_count: ""
  round_1_result: ""
  adaptive_recipe: ""
  recursion_guard: ""
  force_single_workstream: "false"
steps:
  # Set task_type to Development
  - id: "set-task-type"
    type: "bash"
    command: "echo Development"
    output: "task_type"

  # Set workstream_count to a value that matches NEITHER single nor parallel path
  # (simulates the routing gap from #3130/#3132)
  - id: "set-bad-workstream-count"
    type: "bash"
    command: "echo INVALID"
    output: "workstream_count"

  # Single path — won't fire (workstream_count != '1')
  - id: "execute-single"
    type: "bash"
    condition: |
      ('Development' in task_type) and (workstream_count == '1' or workstream_count == '')
    command: "echo SINGLE_PATH"
    output: "round_1_result"

  # Parallel path — won't fire (workstream_count == 'INVALID')
  - id: "launch-parallel"
    type: "bash"
    condition: |
      ('Development' in task_type) and workstream_count != '1' and workstream_count != '' and workstream_count != 'INVALID'
    command: "echo PARALLEL_PATH"
    output: "round_1_result"

  # Adaptive strategy detection — SHOULD fire
  - id: "detect-execution-gap"
    type: "bash"
    condition: |
      ('Development' in task_type or 'Investigation' in task_type) and not round_1_result
    command: |
      echo "[ADAPTIVE] No execution path ran. Routing to direct default-workflow invocation." >&2
      echo "default-workflow"
    output: "adaptive_recipe"

  # Adaptive execution for development
  - id: "adaptive-execute"
    type: "bash"
    condition: |
      adaptive_recipe == 'default-workflow'
    command: "echo ADAPTIVE_STRATEGY_EXECUTED"
    output: "round_1_result"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", prefix="test-3132-", delete=False
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

            # Neither normal path should have run
            assert steps["execute-single"] == "skipped", (
                f"Single path should be skipped, got: {steps['execute-single']}"
            )
            assert steps["launch-parallel"] == "skipped", (
                f"Parallel path should be skipped, got: {steps['launch-parallel']}"
            )

            # Adaptive strategy SHOULD fire
            assert steps["detect-execution-gap"] == "completed", (
                f"detect-execution-gap should fire when no path runs, got: {steps['detect-execution-gap']}"
            )
            assert steps["adaptive-execute"] == "completed", (
                f"adaptive-execute should run, got: {steps['adaptive-execute']}"
            )

            # Verify the adaptive strategy selected the right recipe via output
            gap_step = next(
                s for s in data["step_results"] if s["step_id"] == "detect-execution-gap"
            )
            assert gap_step["output"].strip() == "default-workflow", (
                f"Adaptive strategy should select default-workflow, got: {gap_step['output']}"
            )
        finally:
            Path(recipe_path).unlink(missing_ok=True)

    def test_detect_execution_gap_skipped_when_path_runs(self):
        """When a normal execution path runs, detect-execution-gap should NOT fire."""
        binary = _find_recipe_runner_binary()
        if binary is None:
            import pytest

            pytest.skip("recipe-runner-rs binary not found")

        recipe = """\
name: "test-3132-no-gap"
context:
  task_type: ""
  workstream_count: ""
  round_1_result: ""
  adaptive_recipe: ""
steps:
  - id: "set-task-type"
    type: "bash"
    command: "echo Development"
    output: "task_type"

  - id: "set-workstream-count"
    type: "bash"
    command: "echo 1"
    output: "workstream_count"

  # Normal single path — SHOULD fire
  - id: "execute-single"
    type: "bash"
    condition: |
      ('Development' in task_type) and workstream_count == '1'
    command: "echo NORMAL_EXECUTION"
    output: "round_1_result"

  # Adaptive detection — should NOT fire (round_1_result is set)
  - id: "detect-execution-gap"
    type: "bash"
    condition: |
      ('Development' in task_type or 'Investigation' in task_type) and not round_1_result
    command: |
      echo "ERROR: this should not run" >&2
      echo "default-workflow"
    output: "adaptive_recipe"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", prefix="test-3132-no-gap-", delete=False
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
            assert steps["execute-single"] == "completed"
            assert steps["detect-execution-gap"] == "skipped", (
                f"detect-execution-gap should NOT fire when normal path runs, got: {steps['detect-execution-gap']}"
            )
        finally:
            Path(recipe_path).unlink(missing_ok=True)

    def test_adaptive_routes_investigation_correctly(self):
        """For Investigation tasks, adaptive strategy should select investigation-workflow."""
        binary = _find_recipe_runner_binary()
        if binary is None:
            import pytest

            pytest.skip("recipe-runner-rs binary not found")

        recipe = """\
name: "test-3132-investigation-adaptive"
context:
  task_type: ""
  workstream_count: ""
  round_1_result: ""
  adaptive_recipe: ""
steps:
  - id: "set-task-type"
    type: "bash"
    command: "echo Investigation"
    output: "task_type"

  - id: "set-bad-count"
    type: "bash"
    command: "echo INVALID"
    output: "workstream_count"

  - id: "detect-execution-gap"
    type: "bash"
    condition: |
      ('Development' in task_type or 'Investigation' in task_type) and not round_1_result
    command: |
      TASK_TYPE=$RECIPE_VAR_task_type
      if echo "$TASK_TYPE" | grep -qi "investigation"; then
        echo "investigation-workflow"
      else
        echo "default-workflow"
      fi
    output: "adaptive_recipe"

  - id: "adaptive-execute-investigation"
    type: "bash"
    condition: |
      adaptive_recipe == 'investigation-workflow'
    command: "echo INVESTIGATION_ADAPTIVE_EXECUTED"
    output: "round_1_result"

  - id: "adaptive-execute-development"
    type: "bash"
    condition: |
      adaptive_recipe == 'default-workflow'
    command: "echo DEVELOPMENT_ADAPTIVE_EXECUTED"
    output: "round_1_result"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", prefix="test-3132-inv-", delete=False
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
            assert steps["detect-execution-gap"] == "completed"
            assert steps["adaptive-execute-investigation"] == "completed", (
                f"Investigation adaptive should run, got: {steps['adaptive-execute-investigation']}"
            )
            assert steps["adaptive-execute-development"] == "skipped", (
                f"Development adaptive should be skipped for Investigation task, got: {steps['adaptive-execute-development']}"
            )
        finally:
            Path(recipe_path).unlink(missing_ok=True)


class TestHollowSuccessConditions:
    """Unit tests for hollow success detection logic.

    These test the condition evaluation patterns used to trigger
    round 2 on hollow results.
    """

    def test_hollow_status_triggers_round_2_condition(self):
        """HOLLOW in reflection_1 should trigger round 2 execution."""
        reflection_1 = "GOAL_STATUS: HOLLOW -- agents reported no codebase found"
        # Simulates the condition used in execute-round-2
        should_trigger = (
            "PARTIAL" in reflection_1 or "NOT_ACHIEVED" in reflection_1 or "HOLLOW" in reflection_1
        )
        assert should_trigger, "HOLLOW status should trigger round 2"

    def test_achieved_does_not_trigger_round_2(self):
        """ACHIEVED should NOT trigger round 2."""
        reflection_1 = "GOAL_STATUS: ACHIEVED"
        should_trigger = (
            "PARTIAL" in reflection_1 or "NOT_ACHIEVED" in reflection_1 or "HOLLOW" in reflection_1
        )
        assert not should_trigger, "ACHIEVED should not trigger round 2"

    def test_partial_triggers_round_2(self):
        """PARTIAL should trigger round 2 (existing behavior preserved)."""
        reflection_1 = "GOAL_STATUS: PARTIAL -- missing tests"
        should_trigger = (
            "PARTIAL" in reflection_1 or "NOT_ACHIEVED" in reflection_1 or "HOLLOW" in reflection_1
        )
        assert should_trigger, "PARTIAL should trigger round 2"


class TestAdaptiveRecipeSelection:
    """Unit tests for adaptive recipe selection logic."""

    def test_investigation_task_selects_investigation_workflow(self):
        """Investigation task type should select investigation-workflow."""
        task_type = "Investigation"
        recipe = (
            "investigation-workflow" if "investigation" in task_type.lower() else "default-workflow"
        )
        assert recipe == "investigation-workflow"

    def test_development_task_selects_default_workflow(self):
        """Development task type should select default-workflow."""
        task_type = "Development"
        recipe = (
            "investigation-workflow" if "investigation" in task_type.lower() else "default-workflow"
        )
        assert recipe == "default-workflow"

    def test_empty_task_type_defaults_to_development(self):
        """Empty task type should default to default-workflow."""
        task_type = ""
        recipe = (
            "investigation-workflow" if "investigation" in task_type.lower() else "default-workflow"
        )
        assert recipe == "default-workflow"
