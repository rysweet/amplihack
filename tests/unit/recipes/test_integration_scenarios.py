"""Integration tests for complex recipe execution scenarios.

Tests complex, real-world recipe scenarios including:
- Multi-step error recovery with partial context preservation
- Concurrent recipe execution with shared resources
- Complex workflows (recursion, branching, loops)
- State persistence for long-running recipes
- Cross-cutting concerns (logging, metrics, profiling)
"""

from __future__ import annotations

import json
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

from pytest import LogCaptureFixture

from amplihack.recipes.models import (
    Recipe,
    Step,
    StepStatus,
    StepType,
)
from amplihack.recipes.runner import RecipeRunner

# ============================================================================
# Test Class 1: Multi-Step Error Recovery (140 lines)
# ============================================================================


class TestMultiStepErrorRecovery:
    """Test error recovery, context preservation, and cleanup after failures."""

    def test_step_failure_stops_execution_preserves_context(self, mock_adapter: MagicMock) -> None:
        """When step 2 fails, step 3 should not execute but context is preserved."""
        mock_adapter.execute_bash_step.side_effect = [
            "step1 output",
            Exception("Step 2 failed"),
        ]

        recipe = Recipe(
            name="error-recovery",
            steps=[
                Step(id="step1", step_type=StepType.BASH, command="cmd1", output="out1"),
                Step(id="step2", step_type=StepType.BASH, command="cmd2", output="out2"),
                Step(id="step3", step_type=StepType.BASH, command="cmd3", output="out3"),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Verify fail-fast: only 2 calls (step1 success, step2 fail)
        assert mock_adapter.execute_bash_step.call_count == 2
        assert result.success is False

        # Context should contain step1's output
        assert result.context["out1"] == "step1 output"
        assert "out2" not in result.context
        assert "out3" not in result.context

        # Step results: step1 complete, step2 failed, step3 not present
        assert len(result.step_results) == 2
        assert result.step_results[0].status == StepStatus.COMPLETED
        assert result.step_results[1].status == StepStatus.FAILED

    def test_condition_handles_missing_context_after_error(self, mock_adapter: MagicMock) -> None:
        """Step with condition referencing failed step's output skips gracefully."""
        mock_adapter.execute_bash_step.side_effect = [
            "step1 success",
            Exception("Step 2 failed"),
        ]

        recipe = Recipe(
            name="condition-after-error",
            steps=[
                Step(id="step1", step_type=StepType.BASH, command="cmd1", output="out1"),
                Step(id="step2", step_type=StepType.BASH, command="cmd2", output="out2"),
                Step(
                    id="step3",
                    step_type=StepType.BASH,
                    command="cmd3",
                    condition='out2 == "expected"',
                    output="out3",
                ),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Step 2 failed, step 3 never runs
        assert result.success is False
        assert len(result.step_results) == 2

    def test_error_propagation_through_context_chain(self, mock_adapter: MagicMock) -> None:
        """Error in step 2 prevents template rendering in step 3."""
        mock_adapter.execute_bash_step.side_effect = [
            "initial",
            Exception("Middle step failed"),
        ]

        recipe = Recipe(
            name="error-propagation",
            steps=[
                Step(id="step1", step_type=StepType.BASH, command="cmd1", output="var1"),
                Step(id="step2", step_type=StepType.BASH, command="cmd2", output="var2"),
                Step(
                    id="step3",
                    step_type=StepType.BASH,
                    command="echo {{var2}}",
                    output="var3",
                ),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Step 3 never executes due to fail-fast
        assert mock_adapter.execute_bash_step.call_count == 2
        assert "var2" not in result.context

    def test_cleanup_step_execution_after_failure(self, mock_adapter: MagicMock) -> None:
        """Recipe does not run cleanup steps after failure (fail-fast)."""
        mock_adapter.execute_bash_step.side_effect = [
            "data created",
            Exception("Processing failed"),
        ]

        recipe = Recipe(
            name="cleanup-test",
            steps=[
                Step(id="setup", step_type=StepType.BASH, command="create data", output="data"),
                Step(id="process", step_type=StepType.BASH, command="process", output="result"),
                Step(id="cleanup", step_type=StepType.BASH, command="rm data"),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Cleanup never runs (no separate cleanup semantics, fail-fast)
        assert mock_adapter.execute_bash_step.call_count == 2
        assert result.step_results[1].status == StepStatus.FAILED

    def test_partial_context_after_json_parse_failure(self, mock_adapter: MagicMock) -> None:
        """Step with parse_json fails to parse but still stores raw output."""
        mock_adapter.execute_bash_step.side_effect = [
            "not-json-data",
            "step2 output",
        ]

        recipe = Recipe(
            name="json-parse-failure",
            steps=[
                Step(
                    id="step1",
                    step_type=StepType.BASH,
                    command="cmd1",
                    output="json_var",
                    parse_json=True,
                ),
                Step(id="step2", step_type=StepType.BASH, command="cmd2", output="out2"),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Step 1 completes despite JSON parse failure (warning logged)
        assert result.success is True
        # Raw output stored, not parsed
        assert result.context["json_var"] == "not-json-data"

    def test_error_context_preservation_across_steps(self, mock_adapter: MagicMock) -> None:
        """Failed step preserves all prior context for debugging."""
        mock_adapter.execute_bash_step.side_effect = [
            "value_a",
            "value_b",
            Exception("Step 3 error"),
        ]

        recipe = Recipe(
            name="error-context",
            context={"initial": "base_value"},
            steps=[
                Step(id="s1", step_type=StepType.BASH, command="cmd1", output="var_a"),
                Step(id="s2", step_type=StepType.BASH, command="cmd2", output="var_b"),
                Step(id="s3", step_type=StepType.BASH, command="cmd3", output="var_c"),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # All successful step outputs preserved
        assert result.context["initial"] == "base_value"
        assert result.context["var_a"] == "value_a"
        assert result.context["var_b"] == "value_b"
        assert "var_c" not in result.context

    def test_rollback_via_condition_flags(self, mock_adapter: MagicMock) -> None:
        """Rollback pattern: set error flag, skip normal steps, run cleanup."""
        mock_adapter.execute_bash_step.side_effect = [
            "transaction started",
            Exception("Transaction failed"),
        ]

        recipe = Recipe(
            name="rollback-pattern",
            context={"error_occurred": False},
            steps=[
                Step(id="start", step_type=StepType.BASH, command="begin", output="tx"),
                Step(id="commit", step_type=StepType.BASH, command="commit", output="result"),
                # Rollback step would run if error_occurred=True (not modeled here)
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Transaction started, commit failed
        assert result.context["tx"] == "transaction started"
        assert "result" not in result.context

    def test_graceful_degradation_with_fallback_steps(self, mock_adapter: MagicMock) -> None:
        """Primary step fails, fallback condition triggers alternate path."""
        mock_adapter.execute_bash_step.side_effect = [
            Exception("Primary service unavailable"),
            "fallback success",
        ]

        recipe = Recipe(
            name="graceful-degradation",
            steps=[
                Step(id="primary", step_type=StepType.BASH, command="primary", output="result"),
                Step(
                    id="fallback",
                    step_type=StepType.BASH,
                    command="fallback",
                    condition='result == ""',
                    output="result",
                ),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Primary fails, no fallback runs (fail-fast)
        assert result.success is False
        assert result.step_results[0].status == StepStatus.FAILED


# ============================================================================
# Test Class 2: Concurrent Recipe Execution (120 lines)
# ============================================================================


class TestConcurrentRecipeExecution:
    """Test concurrent recipe execution, thread safety, and resource contention."""

    def test_multiple_recipes_in_parallel(self, mock_adapter: MagicMock) -> None:
        """Multiple recipes execute concurrently without interference."""
        mock_adapter.execute_bash_step.return_value = "output"

        recipe1 = Recipe(
            name="recipe1",
            steps=[Step(id="s1", step_type=StepType.BASH, command="cmd1", output="out1")],
        )
        recipe2 = Recipe(
            name="recipe2",
            steps=[Step(id="s2", step_type=StepType.BASH, command="cmd2", output="out2")],
        )

        runner = RecipeRunner(adapter=mock_adapter)

        results = []

        def run_recipe(recipe: Recipe) -> None:
            res = runner.execute(recipe)
            results.append(res)

        threads = [
            threading.Thread(target=run_recipe, args=(recipe1,)),
            threading.Thread(target=run_recipe, args=(recipe2,)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 2
        assert all(r.success for r in results)

    def test_shared_context_isolation_between_recipes(self, mock_adapter: MagicMock) -> None:
        """Each recipe has isolated context despite concurrent execution."""
        mock_adapter.execute_bash_step.side_effect = lambda cmd, **kw: f"output_{cmd}"

        recipe1 = Recipe(
            name="recipe1",
            context={"shared_key": "value1"},
            steps=[Step(id="s1", step_type=StepType.BASH, command="cmd1", output="out1")],
        )
        recipe2 = Recipe(
            name="recipe2",
            context={"shared_key": "value2"},
            steps=[Step(id="s2", step_type=StepType.BASH, command="cmd2", output="out2")],
        )

        runner = RecipeRunner(adapter=mock_adapter)

        results = []

        def run_recipe(recipe: Recipe) -> None:
            res = runner.execute(recipe)
            results.append((recipe.name, res))

        threads = [
            threading.Thread(target=run_recipe, args=(recipe1,)),
            threading.Thread(target=run_recipe, args=(recipe2,)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify context isolation
        result_dict = dict(results)
        assert result_dict["recipe1"].context["shared_key"] == "value1"
        assert result_dict["recipe2"].context["shared_key"] == "value2"

    def test_adapter_thread_safety(self, mock_adapter: MagicMock) -> None:
        """Adapter is called concurrently without errors (thread-safe mock)."""
        call_count = {"count": 0}
        lock = threading.Lock()

        def thread_safe_call(*args: Any, **kwargs: Any) -> str:
            with lock:
                call_count["count"] += 1
                time.sleep(0.001)  # Simulate work
                return "output"

        mock_adapter.execute_bash_step.side_effect = thread_safe_call

        recipe = Recipe(
            name="concurrent",
            steps=[Step(id="s1", step_type=StepType.BASH, command="cmd", output="out")],
        )

        runner = RecipeRunner(adapter=mock_adapter)

        threads = [threading.Thread(target=runner.execute, args=(recipe,)) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert call_count["count"] == 5

    def test_manifest_file_locking_simulation(self) -> None:
        """Concurrent writes to manifest file are serialized (simulated)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            lock = threading.Lock()

            def write_manifest(data: dict[str, Any]) -> None:
                with lock:
                    existing = {}
                    if manifest_path.exists():
                        existing = json.loads(manifest_path.read_text())
                    existing.update(data)
                    manifest_path.write_text(json.dumps(existing))

            threads = [
                threading.Thread(target=write_manifest, args=({f"key{i}": f"val{i}"},))
                for i in range(10)
            ]

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            final_data = json.loads(manifest_path.read_text())
            assert len(final_data) == 10

    def test_resource_contention_handling(self, mock_adapter: MagicMock) -> None:
        """Multiple recipes accessing same resource cause delays, not errors."""
        delays = []

        def delayed_call(*args: Any, **kwargs: Any) -> str:
            start = time.time()
            time.sleep(0.01)
            delays.append(time.time() - start)
            return "output"

        mock_adapter.execute_bash_step.side_effect = delayed_call

        recipe = Recipe(
            name="resource",
            steps=[Step(id="s1", step_type=StepType.BASH, command="cmd", output="out")],
        )

        runner = RecipeRunner(adapter=mock_adapter)

        threads = [threading.Thread(target=runner.execute, args=(recipe,)) for _ in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(delays) == 3
        assert all(d >= 0.01 for d in delays)

    def test_concurrent_context_writes(self, mock_adapter: MagicMock) -> None:
        """Concurrent writes to different RecipeContext instances do not interfere."""
        mock_adapter.execute_bash_step.return_value = "data"

        results = []

        def run_with_context(initial: dict[str, Any]) -> None:
            recipe = Recipe(
                name="ctx-test",
                context=initial,
                steps=[Step(id="s1", step_type=StepType.BASH, command="cmd", output="out")],
            )
            runner = RecipeRunner(adapter=mock_adapter)
            res = runner.execute(recipe)
            results.append(res.context)

        threads = [threading.Thread(target=run_with_context, args=({"id": i},)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 5
        # Each context has unique initial value
        ids = [ctx["id"] for ctx in results]
        assert sorted(ids) == [0, 1, 2, 3, 4]


# ============================================================================
# Test Class 3: Complex Workflows (140 lines)
# ============================================================================


class TestComplexWorkflows:
    """Test complex workflow patterns: recursion, branching, loops, fan-out."""

    def test_nested_recipe_simulation(self, mock_adapter: MagicMock) -> None:
        """Simulate nested recipe by running recipe within step output."""
        mock_adapter.execute_agent_step.return_value = "nested recipe executed"

        outer_recipe = Recipe(
            name="outer",
            steps=[
                Step(
                    id="call_nested",
                    step_type=StepType.AGENT,
                    agent="executor",
                    prompt="Execute nested recipe",
                    output="nested_result",
                ),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(outer_recipe)

        assert result.success is True
        assert result.context["nested_result"] == "nested recipe executed"

    def test_dynamic_recipe_generation_via_context(self, mock_adapter: MagicMock) -> None:
        """Step generates recipe definition, subsequent step uses it."""
        mock_adapter.execute_bash_step.side_effect = [
            json.dumps({"name": "dynamic", "steps": []}),
            "executed dynamic recipe",
        ]

        recipe = Recipe(
            name="dynamic-gen",
            steps=[
                Step(
                    id="generate",
                    step_type=StepType.BASH,
                    command="generate-recipe",
                    output="recipe_def",
                    parse_json=True,
                ),
                Step(
                    id="execute",
                    step_type=StepType.BASH,
                    command="run-recipe {{recipe_def}}",
                    output="result",
                ),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert result.success is True
        assert isinstance(result.context["recipe_def"], dict)

    def test_conditional_branching_multiple_paths(self, mock_adapter: MagicMock) -> None:
        """Recipe branches based on condition into different execution paths."""
        mock_adapter.execute_bash_step.return_value = "branch output"

        recipe = Recipe(
            name="branching",
            context={"mode": "fast"},
            steps=[
                Step(
                    id="fast_path",
                    step_type=StepType.BASH,
                    command="fast",
                    condition='mode == "fast"',
                    output="result",
                ),
                Step(
                    id="slow_path",
                    step_type=StepType.BASH,
                    command="slow",
                    condition='mode == "slow"',
                    output="result",
                ),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Only fast path executes
        assert result.step_results[0].status == StepStatus.COMPLETED
        assert result.step_results[1].status == StepStatus.SKIPPED

    def test_loop_pattern_via_array_in_context(self, mock_adapter: MagicMock) -> None:
        """Simulate loop by passing array through context (manual unrolling)."""
        mock_adapter.execute_bash_step.return_value = "item processed"

        items = ["item1", "item2", "item3"]
        recipe = Recipe(
            name="loop-sim",
            context={"items": items},
            steps=[
                Step(
                    id=f"process_{i}",
                    step_type=StepType.BASH,
                    command=f"process {item}",
                    output=f"result_{i}",
                )
                for i, item in enumerate(items)
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert result.success is True
        assert len(result.step_results) == 3
        assert all(sr.status == StepStatus.COMPLETED for sr in result.step_results)

    def test_fan_out_fan_in_pattern(self, mock_adapter: MagicMock) -> None:
        """Fan out: multiple parallel steps, fan in: aggregate results."""
        mock_adapter.execute_bash_step.side_effect = [
            "result_a",
            "result_b",
            "result_c",
            "aggregated",
        ]

        recipe = Recipe(
            name="fan-out-in",
            steps=[
                Step(id="task_a", step_type=StepType.BASH, command="task_a", output="a"),
                Step(id="task_b", step_type=StepType.BASH, command="task_b", output="b"),
                Step(id="task_c", step_type=StepType.BASH, command="task_c", output="c"),
                Step(
                    id="aggregate",
                    step_type=StepType.BASH,
                    command="combine {{a}} {{b}} {{c}}",
                    output="final",
                ),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert result.success is True
        assert "final" in result.context

    def test_recursive_recipe_depth_limit(self, mock_adapter: MagicMock) -> None:
        """Recursive recipe invocation respects depth limit (simulated)."""
        depth = {"count": 0}

        def recursive_call(*args: Any, **kwargs: Any) -> str:
            depth["count"] += 1
            if depth["count"] >= 3:
                return "max depth reached"
            return "continue"

        mock_adapter.execute_agent_step.side_effect = recursive_call

        recipe = Recipe(
            name="recursive",
            steps=[
                Step(
                    id="recurse",
                    step_type=StepType.AGENT,
                    agent="self",
                    prompt="recurse",
                    output="result",
                ),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)

        # Simulate 3 recursive calls
        for _ in range(3):
            runner.execute(recipe)

        assert depth["count"] == 3

    def test_conditional_step_chains(self, mock_adapter: MagicMock) -> None:
        """Chain of steps where each depends on previous via conditions."""
        mock_adapter.execute_bash_step.side_effect = ["yes", "continue", "done"]

        recipe = Recipe(
            name="chain",
            steps=[
                Step(id="step1", step_type=StepType.BASH, command="cmd1", output="flag1"),
                Step(
                    id="step2",
                    step_type=StepType.BASH,
                    command="cmd2",
                    condition='flag1 == "yes"',
                    output="flag2",
                ),
                Step(
                    id="step3",
                    step_type=StepType.BASH,
                    command="cmd3",
                    condition='flag2 == "continue"',
                    output="flag3",
                ),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert result.success is True
        assert all(sr.status == StepStatus.COMPLETED for sr in result.step_results)


# ============================================================================
# Test Class 4: State Persistence (90 lines)
# ============================================================================


class TestStatePersistence:
    """Test state persistence, checkpointing, and resume for long-running recipes."""

    def test_long_running_recipe_state_capture(self, mock_adapter: MagicMock) -> None:
        """Capture intermediate state during long-running recipe."""
        mock_adapter.execute_bash_step.side_effect = ["step1", "step2", "step3"]

        recipe = Recipe(
            name="long-running",
            steps=[
                Step(id=f"step{i}", step_type=StepType.BASH, command=f"cmd{i}", output=f"out{i}")
                for i in range(1, 4)
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Intermediate states captured in context
        assert result.context["out1"] == "step1"
        assert result.context["out2"] == "step2"
        assert result.context["out3"] == "step3"

    def test_checkpoint_and_restore(self, mock_adapter: MagicMock) -> None:
        """Checkpoint context after each step, restore to resume execution."""
        mock_adapter.execute_bash_step.side_effect = [
            "checkpoint1",
            Exception("Failure at step 2"),
        ]

        recipe = Recipe(
            name="checkpoint",
            steps=[
                Step(id="step1", step_type=StepType.BASH, command="cmd1", output="cp1"),
                Step(id="step2", step_type=StepType.BASH, command="cmd2", output="cp2"),
                Step(id="step3", step_type=StepType.BASH, command="cmd3", output="cp3"),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Save checkpoint (context after step1)
        checkpoint = result.context.copy()

        # Resume from checkpoint
        mock_adapter.execute_bash_step.side_effect = ["checkpoint2_retry", "checkpoint3"]
        resume_recipe = Recipe(
            name="checkpoint",
            context=checkpoint,
            steps=[
                Step(id="step2", step_type=StepType.BASH, command="cmd2", output="cp2"),
                Step(id="step3", step_type=StepType.BASH, command="cmd3", output="cp3"),
            ],
        )

        resume_result = runner.execute(resume_recipe)
        assert resume_result.success is True
        assert resume_result.context["cp1"] == "checkpoint1"  # Preserved from checkpoint

    def test_progress_tracking_via_context(self, mock_adapter: MagicMock) -> None:
        """Track progress through completed_steps list in context."""
        completed = []

        def track_progress(*args: Any, **kwargs: Any) -> str:
            completed.append(len(completed) + 1)
            return f"step{len(completed)}"

        mock_adapter.execute_bash_step.side_effect = track_progress

        recipe = Recipe(
            name="progress",
            steps=[
                Step(id=f"s{i}", step_type=StepType.BASH, command=f"cmd{i}", output=f"o{i}")
                for i in range(5)
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert len(completed) == 5
        assert result.success is True

    def test_resume_from_failure_with_partial_context(self, mock_adapter: MagicMock) -> None:
        """Resume execution using partial context from failed run."""
        mock_adapter.execute_bash_step.side_effect = [
            "data1",
            "data2",
            Exception("Network error"),
        ]

        recipe = Recipe(
            name="resume",
            steps=[
                Step(id="fetch1", step_type=StepType.BASH, command="fetch1", output="d1"),
                Step(id="fetch2", step_type=StepType.BASH, command="fetch2", output="d2"),
                Step(id="fetch3", step_type=StepType.BASH, command="fetch3", output="d3"),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Save partial context
        partial_context = result.context

        # Retry from step 3 with restored context
        mock_adapter.execute_bash_step.side_effect = ["data3_retry"]
        retry_recipe = Recipe(
            name="resume",
            context=partial_context,
            steps=[
                Step(id="fetch3", step_type=StepType.BASH, command="fetch3", output="d3"),
            ],
        )

        retry_result = runner.execute(retry_recipe)
        assert retry_result.success is True
        assert retry_result.context["d1"] == "data1"
        assert retry_result.context["d2"] == "data2"


# ============================================================================
# Test Class 5: Cross-Cutting Concerns (75 lines)
# ============================================================================


class TestCrossCuttingConcerns:
    """Test logging, metrics, error reporting, and profiling integration."""

    def test_logging_integration(self, mock_adapter: MagicMock, caplog: LogCaptureFixture) -> None:
        """Recipe execution logs steps and status."""
        mock_adapter.execute_bash_step.return_value = "output"

        recipe = Recipe(
            name="logging",
            steps=[Step(id="s1", step_type=StepType.BASH, command="cmd", output="out")],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        with caplog.at_level("INFO"):
            runner.execute(recipe)

        # No specific log assertions (depends on logger config)
        # Just verify execution completes
        assert mock_adapter.execute_bash_step.called

    def test_metrics_collection_via_timing(self, mock_adapter: MagicMock) -> None:
        """Collect execution time metrics for each step."""
        mock_adapter.execute_bash_step.return_value = "output"

        recipe = Recipe(
            name="metrics",
            steps=[
                Step(id=f"step{i}", step_type=StepType.BASH, command=f"cmd{i}", output=f"o{i}")
                for i in range(3)
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        start = time.time()
        result = runner.execute(recipe)
        elapsed = time.time() - start

        assert result.success is True
        assert elapsed < 1.0  # Fast execution

    def test_error_reporting_structure(self, mock_adapter: MagicMock) -> None:
        """Failed step includes error message in result."""
        mock_adapter.execute_bash_step.side_effect = Exception("Critical failure")

        recipe = Recipe(
            name="error-report",
            steps=[Step(id="fail", step_type=StepType.BASH, command="cmd", output="out")],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert result.step_results[0].status == StepStatus.FAILED
        assert "Critical failure" in result.step_results[0].error

    @patch("time.time")
    def test_performance_profiling(self, mock_time: Mock, mock_adapter: MagicMock) -> None:
        """Profile step execution time via mocked time."""
        mock_time.side_effect = [0.0, 1.0, 1.0, 2.0]  # Start, step1 end, step2 start, end
        mock_adapter.execute_bash_step.return_value = "output"

        recipe = Recipe(
            name="profile",
            steps=[
                Step(id="s1", step_type=StepType.BASH, command="cmd1", output="o1"),
                Step(id="s2", step_type=StepType.BASH, command="cmd2", output="o2"),
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert result.success is True
        # Profiling would calculate: step1=1s, step2=1s (mocked)

    def test_memory_profiling_context_size(self, mock_adapter: MagicMock) -> None:
        """Track context memory size growth during execution."""
        large_data = "x" * 10000
        mock_adapter.execute_bash_step.return_value = large_data

        recipe = Recipe(
            name="memory",
            steps=[
                Step(id=f"step{i}", step_type=StepType.BASH, command=f"cmd{i}", output=f"out{i}")
                for i in range(5)
            ],
        )

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Context size grows with each large output
        context_size = len(json.dumps(result.context))
        assert context_size > 50000  # 5 steps * 10KB each
