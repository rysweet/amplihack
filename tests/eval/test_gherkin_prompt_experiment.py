import json
import os

import pytest

from amplihack.eval.gherkin_prompt_experiment import (
    default_gherkin_manifest_path,
    evaluate_gherkin_artifact,
    load_default_gherkin_manifest,
    main,
    run_gherkin_prompt_experiment,
)
from amplihack.eval.tla_prompt_experiment import (
    ConditionMetrics,
    ConditionRunResult,
    materialize_condition_packets,
    summarize_condition_results,
    write_condition_result,
)


def test_default_gherkin_manifest_path_points_to_experiment_home():
    manifest_path = default_gherkin_manifest_path()
    assert manifest_path.name == "manifest.json"
    assert "experiments/hive_mind/gherkin_prompt_language" in str(manifest_path)


def test_default_gherkin_manifest_loads_scoped_generation_target():
    manifest = load_default_gherkin_manifest()
    assert manifest.experiment_id == "gherkin-prompt-language-v2"
    assert manifest.experiment_home == "experiments/hive_mind/gherkin_prompt_language"
    assert manifest.generation_target.target_id == "recipe_step_executor"


def test_default_gherkin_manifest_resolves_prompt_and_spec_assets():
    manifest = load_default_gherkin_manifest()
    spec_path = manifest.resolve_asset_path(manifest.spec_asset)
    refinement_path = manifest.resolve_asset_path(manifest.refinement_asset or "")
    assert spec_path.name == "recipe_step_executor.feature"
    assert refinement_path.name == "recipe_step_executor_acceptance_criteria.md"
    for prompt_variant in manifest.prompt_variants:
        assert manifest.resolve_asset_path(prompt_variant.path).exists()


def test_expand_smoke_matrix_returns_one_repeat_per_model_variant_pair():
    manifest = load_default_gherkin_manifest()
    conditions = manifest.expand_matrix(smoke=True)
    assert len(conditions) == 8  # 4 variants x 2 models x 1 repeat
    repeat_indices = {c.repeat_index for c in conditions}
    assert repeat_indices == {1}
    variant_ids = {c.prompt_variant_id for c in conditions}
    assert variant_ids == {
        "english",
        "gherkin_only",
        "gherkin_plus_english",
        "gherkin_plus_acceptance",
    }
    model_ids = {c.model_id for c in conditions}
    assert model_ids == {"claude-opus-4.6", "gpt-5.4"}


def test_expand_full_matrix_uses_full_repeat_count():
    manifest = load_default_gherkin_manifest()
    conditions = manifest.expand_matrix(smoke=False)
    assert len(conditions) == 24  # 4 variants x 2 models x 3 repeats
    repeat_indices = {c.repeat_index for c in conditions}
    assert repeat_indices == {1, 2, 3}


def test_prompt_bundle_appends_gherkin_spec_when_variant_requires_it():
    manifest = load_default_gherkin_manifest()

    english_bundle = manifest.load_prompt_bundle(
        "english",
        spec_section_header="Behavioral specification",
        spec_fence_lang="gherkin",
    )
    english_text = english_bundle.combined_text()
    assert "## Behavioral specification" not in english_text
    assert "Feature:" not in english_text

    gherkin_bundle = manifest.load_prompt_bundle(
        "gherkin_only",
        spec_section_header="Behavioral specification",
        spec_fence_lang="gherkin",
    )
    gherkin_text = gherkin_bundle.combined_text()
    assert "## Behavioral specification" in gherkin_text
    assert "```gherkin" in gherkin_text
    assert "Feature: Recipe Step Executor" in gherkin_text

    acceptance_bundle = manifest.load_prompt_bundle(
        "gherkin_plus_acceptance",
        spec_section_header="Behavioral specification",
        spec_fence_lang="gherkin",
    )
    acceptance_text = acceptance_bundle.combined_text()
    assert "## Behavioral specification" in acceptance_text
    assert "## Refinement guidance" in acceptance_text
    assert "Acceptance Criteria" in acceptance_text


def test_materialize_condition_packets_writes_prompt_spec_and_metadata(tmp_path):
    manifest = load_default_gherkin_manifest()
    packets = materialize_condition_packets(tmp_path, smoke=True, manifest=manifest)
    assert len(packets) == 8

    # Check a gherkin_plus_acceptance condition has all expected files.
    acceptance_packets = [
        p for p in packets if p.condition.prompt_variant_id == "gherkin_plus_acceptance"
    ]
    assert len(acceptance_packets) == 2  # one per model
    packet = acceptance_packets[0]
    assert os.path.isfile(packet.prompt_file)
    assert os.path.isfile(packet.spec_file)
    assert os.path.isfile(packet.metadata_file)
    assert packet.refinement_file is not None
    assert os.path.isfile(packet.refinement_file)


# ---------------------------------------------------------------------------
# Evaluator tests
# ---------------------------------------------------------------------------

IDEAL_EXECUTOR_ARTIFACT = """
# Recipe Step Executor

## Core Implementation

```python
import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any

@dataclass
class StepResult:
    id: str
    status: str = "pending"  # completed, failed, skipped, timed_out
    output: Any = None
    attempt_count: int = 0
    failure_reason: str | None = None
    retry_delays: list[float] = field(default_factory=list)

class RecipeStepExecutor:
    def __init__(self, context: dict | None = None):
        self.context = dict(context or {})
        self.results: dict[str, StepResult] = {}

    def _resolve_templates(self, text: str) -> str:
        \"\"\"Replace {{step_id}} with context.get(step_id, '').\"\"\"
        def replacer(match):
            key = match.group(1)
            return str(self.context.get(key, ""))
        return re.sub(r"\\{\\{(\\w+)\\}\\}", replacer, text)

    def _evaluate_condition(self, condition: str) -> bool:
        \"\"\"Evaluate condition expression against context dict.
        Missing key -> NameError/KeyError -> return false (skip).\"\"\"
        if not condition:
            return True
        try:
            return bool(eval(condition, {"__builtins__": {}}, self.context))
        except (NameError, KeyError, TypeError):
            return False

    def _check_dependencies(self, step: dict) -> str | None:
        \"\"\"Check blockedBy dependencies. Returns failure reason or None.
        Failed/timed_out dependency -> 'dependency_failed'.
        Skipped dependency -> does not propagate (returns None).\"\"\"
        blocked_by = step.get("blockedBy", [])
        if isinstance(blocked_by, str):
            blocked_by = [b.strip() for b in blocked_by.split(",")]
        for dep_id in blocked_by:
            dep_result = self.results.get(dep_id)
            if dep_result is None:
                return "dependency_failed"
            if dep_result.status in ("failed", "timed_out"):
                return "dependency_failed"
            # skipped -> does not propagate, continue checking
        return None

    async def _execute_step_command(self, command: str, timeout_seconds: int) -> str:
        \"\"\"Execute a step command with timeout enforcement.\"\"\"
        resolved = self._resolve_templates(command)
        try:
            async with asyncio.timeout(timeout_seconds):
                # Simulate command execution
                if resolved.startswith("echo "):
                    return resolved[5:].strip('"').strip("'")
                elif resolved.startswith("exit "):
                    code = int(resolved.split()[1])
                    if code != 0:
                        raise RuntimeError(f"Command exited with code {code}")
                    return ""
                elif "sleep(" in resolved:
                    secs = float(resolved.split("(")[1].rstrip(")"))
                    await asyncio.sleep(secs)
                    return ""
                elif "fail_then_succeed" in resolved:
                    # Simulated: fails N times then succeeds
                    raise RuntimeError("Simulated failure")
                elif "fail_then_return" in resolved:
                    raise RuntimeError("Simulated failure")
                elif "always_fail" in resolved:
                    raise RuntimeError("Always fails")
                else:
                    return resolved
        except asyncio.TimeoutError:
            raise TimeoutError("Step timed out")

    async def _run_step_with_retry(self, step: dict) -> StepResult:
        step_id = step["id"]
        max_retries = step.get("max_retries", 0)
        timeout_seconds = step.get("timeout_seconds", 60)
        result = StepResult(id=step_id)

        for attempt in range(1 + max_retries):
            result.attempt_count = attempt + 1
            try:
                if step.get("sub_recipe"):
                    output = await self._run_sub_recipe(step)
                else:
                    output = await self._execute_step_command(
                        step.get("command", ""), timeout_seconds
                    )
                result.status = "completed"
                result.output = output
                self.context[step_id] = output
                return result
            except TimeoutError:
                result.status = "timed_out"
                # Timed-out steps are NOT retried
                return result
            except Exception as e:
                if attempt < max_retries:
                    delay = 2 ** attempt  # 1s, 2s, 4s exponential backoff
                    result.retry_delays.append(delay)
                    await asyncio.sleep(delay)
                else:
                    result.status = "failed"
                    result.failure_reason = str(e)
                    return result

        return result

    async def _run_sub_recipe(self, step: dict) -> str:
        \"\"\"Execute a sub-recipe in a child context.
        Child inherits parent context. Outputs isolated unless propagate_outputs.
        Failed sub-recipe never propagates outputs.\"\"\"
        sub_recipe_def = step["sub_recipe"]
        propagate = step.get("propagate_outputs", False)

        # Child context is a copy of parent
        child_executor = RecipeStepExecutor(context=dict(self.context))
        child_executor.context = dict(self.context)  # fresh copy

        # Execute sub-recipe
        await child_executor.execute(sub_recipe_def)

        # Check if any child step failed
        child_failed = any(
            r.status in ("failed", "timed_out")
            for r in child_executor.results.values()
        )

        if child_failed:
            raise RuntimeError("Sub-recipe failed")

        # Propagate outputs only on success and if opted in
        if propagate and not child_failed:
            for key, value in child_executor.context.items():
                if key not in self.context:
                    self.context[key] = value

        return "sub_recipe_completed"

    async def execute(self, recipe: list[dict]) -> dict[str, StepResult]:
        \"\"\"Execute all steps respecting dependencies, conditions, retries.\"\"\"
        # Build dependency graph for topological ordering
        step_map = {s["id"]: s for s in recipe}

        for step in recipe:
            step_id = step["id"]

            # Check dependencies
            dep_failure = self._check_dependencies(step)
            if dep_failure:
                self.results[step_id] = StepResult(
                    id=step_id,
                    status="failed",
                    failure_reason=dep_failure,
                )
                continue

            # Check condition
            condition = step.get("condition", "")
            if condition and not self._evaluate_condition(condition):
                self.results[step_id] = StepResult(id=step_id, status="skipped")
                continue

            # Execute with retry
            result = await self._run_step_with_retry(step)
            self.results[step_id] = result

        return self.results
```

## Tests

```python
import asyncio
import pytest
from recipe_step_executor import RecipeStepExecutor, StepResult

# --- Feature: Conditional Execution ---

def test_unconditional_step_always_executes():
    executor = RecipeStepExecutor()
    recipe = [{"id": "step_a", "command": 'echo "hello"'}]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "completed"
    assert executor.context["step_a"] == "hello"

def test_condition_true_executes():
    executor = RecipeStepExecutor(context={"env": "prod"})
    recipe = [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "completed"

def test_condition_false_skips():
    executor = RecipeStepExecutor(context={"env": "staging"})
    recipe = [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "skipped"
    assert "step_a" not in executor.context

def test_condition_missing_key_skips():
    executor = RecipeStepExecutor()
    recipe = [{"id": "step_a", "command": 'echo "go"', "condition": "feature_flag == True"}]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "skipped"

# --- Feature: Step Dependencies ---

def test_dependency_ordering():
    executor = RecipeStepExecutor()
    recipe = [
        {"id": "step_a", "command": 'echo "first"'},
        {"id": "step_b", "command": 'echo "second"', "blockedBy": "step_a"},
    ]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_b"].status == "completed"

def test_failed_dependency_propagates():
    executor = RecipeStepExecutor()
    recipe = [
        {"id": "step_a", "command": "exit 1"},
        {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
    ]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "failed"
    assert results["step_b"].status == "failed"
    assert results["step_b"].failure_reason == "dependency_failed"

def test_skipped_dependency_does_not_propagate():
    executor = RecipeStepExecutor(context={"env": "staging"})
    recipe = [
        {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
        {"id": "step_b", "command": 'echo "runs"', "blockedBy": "step_a"},
    ]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "skipped"
    assert results["step_b"].status == "completed"

# --- Feature: Retry with Backoff ---

def test_retry_with_exponential_backoff():
    executor = RecipeStepExecutor()
    recipe = [{"id": "step_a", "command": "fail_then_succeed(2)", "max_retries": 3}]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "completed"
    assert results["step_a"].attempt_count == 3
    assert results["step_a"].retry_delays == pytest.approx([1, 2], abs=0.5)

def test_retry_exhaustion_fails():
    executor = RecipeStepExecutor()
    recipe = [{"id": "step_a", "command": "always_fail", "max_retries": 2}]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "failed"
    assert results["step_a"].attempt_count == 3

# --- Feature: Timeout Handling ---

def test_timeout_terminates_step():
    executor = RecipeStepExecutor()
    recipe = [{"id": "step_a", "command": "sleep(30)", "timeout_seconds": 2}]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "timed_out"

def test_timed_out_step_not_retried():
    executor = RecipeStepExecutor()
    recipe = [{"id": "step_a", "command": "sleep(30)", "timeout_seconds": 2, "max_retries": 3}]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "timed_out"
    assert results["step_a"].attempt_count == 1

def test_timeout_propagates_as_failure_to_dependents():
    executor = RecipeStepExecutor()
    recipe = [
        {"id": "step_a", "command": "sleep(30)", "timeout_seconds": 2},
        {"id": "step_b", "command": 'echo "blocked"', "blockedBy": "step_a"},
    ]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "timed_out"
    assert results["step_b"].status == "failed"
    assert results["step_b"].failure_reason == "dependency_failed"

# --- Feature: Output Capture ---

def test_output_stored_in_context():
    executor = RecipeStepExecutor()
    recipe = [{"id": "step_a", "command": 'echo "result_42"'}]
    results = asyncio.run(executor.execute(recipe))
    assert executor.context["step_a"] == "result_42"

def test_template_resolution_in_subsequent_step():
    executor = RecipeStepExecutor()
    recipe = [
        {"id": "step_a", "command": 'echo "world"'},
        {"id": "step_b", "command": 'echo "hello {{step_a}}"', "blockedBy": "step_a"},
    ]
    results = asyncio.run(executor.execute(recipe))
    assert executor.context["step_b"] == "hello world"

# --- Feature: Sub-Recipe Delegation ---

def test_sub_recipe_inherits_parent_context():
    executor = RecipeStepExecutor(context={"base_url": "http://api.example.com"})
    child_recipe = [{"id": "child_1", "command": 'echo "url={{base_url}}"'}]
    recipe = [{"id": "step_a", "sub_recipe": child_recipe}]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "completed"

def test_child_outputs_not_propagated_by_default():
    child_recipe = [{"id": "child_1", "command": 'echo "secret"'}]
    executor = RecipeStepExecutor()
    recipe = [{"id": "step_a", "sub_recipe": child_recipe, "propagate_outputs": False}]
    results = asyncio.run(executor.execute(recipe))
    assert "child_1" not in executor.context

def test_child_outputs_propagated_when_opted_in():
    child_recipe = [{"id": "child_1", "command": 'echo "visible"'}]
    executor = RecipeStepExecutor()
    recipe = [{"id": "step_a", "sub_recipe": child_recipe, "propagate_outputs": True}]
    results = asyncio.run(executor.execute(recipe))
    assert executor.context.get("child_1") == "visible"

def test_failed_sub_recipe_no_propagation():
    child_recipe = [
        {"id": "child_1", "command": 'echo "before_fail"'},
        {"id": "child_2", "command": "exit 1"},
    ]
    executor = RecipeStepExecutor()
    recipe = [{"id": "step_a", "sub_recipe": child_recipe, "propagate_outputs": True}]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "failed"
    assert "child_1" not in executor.context

# --- Cross-Feature Interaction Tests ---

def test_interaction_condition_on_retried_output():
    \"\"\"Condition references output from retried step — uses final successful value.\"\"\"
    executor = RecipeStepExecutor()
    recipe = [
        {"id": "step_a", "command": 'fail_then_return(2, "ready")', "max_retries": 3},
        {"id": "step_b", "command": 'echo "proceeding"', "blockedBy": "step_a",
         "condition": "step_a == 'ready'"},
    ]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "completed"
    assert executor.context["step_a"] == "ready"
    assert results["step_b"].status == "completed"

def test_interaction_timeout_blocks_conditional():
    \"\"\"Timed-out step blocks conditional — blocked step fails (dependency), not skipped.\"\"\"
    executor = RecipeStepExecutor()
    recipe = [
        {"id": "step_a", "command": "sleep(30)", "timeout_seconds": 2},
        {"id": "step_b", "command": 'echo "gated"', "blockedBy": "step_a",
         "condition": "step_a == 'done'"},
    ]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "timed_out"
    assert results["step_b"].status == "failed"
    assert results["step_b"].failure_reason == "dependency_failed"

def test_interaction_condition_refs_skipped_step():
    \"\"\"Condition referencing skipped step evaluates to false — step is skipped.\"\"\"
    executor = RecipeStepExecutor(context={"env": "staging"})
    recipe = [
        {"id": "step_a", "command": 'echo "prod_cfg"', "condition": "env == 'prod'"},
        {"id": "step_b", "command": 'echo "use_cfg"', "blockedBy": "step_a",
         "condition": "step_a is not None"},
    ]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "skipped"
    assert results["step_b"].status == "skipped"

def test_interaction_sub_recipe_failure_triggers_parent_retry():
    \"\"\"Sub-recipe failure triggers parent retry — entire sub-recipe re-runs.\"\"\"
    executor = RecipeStepExecutor()
    child_recipe = [{"id": "child_1", "command": "fail_then_succeed(1)"}]
    recipe = [{"id": "step_a", "sub_recipe": child_recipe, "max_retries": 2}]
    results = asyncio.run(executor.execute(recipe))
    assert results["step_a"].status == "completed"
    assert results["step_a"].attempt_count == 2

def test_interaction_template_with_retried_output():
    \"\"\"Output template references retried step's final value.\"\"\"
    executor = RecipeStepExecutor()
    recipe = [
        {"id": "step_a", "command": 'fail_then_return(1, "v2")', "max_retries": 2},
        {"id": "step_b", "command": 'echo "got {{step_a}}"', "blockedBy": "step_a"},
    ]
    results = asyncio.run(executor.execute(recipe))
    assert executor.context["step_a"] == "v2"
    assert executor.context["step_b"] == "got v2"
```

This implementation follows the Gherkin behavioral specification scenarios for the
recipe step executor, covering all 6 features and their cross-feature interactions.
"""


def test_evaluate_gherkin_artifact_scores_ideal_executor_implementation():
    evaluation = evaluate_gherkin_artifact(IDEAL_EXECUTOR_ARTIFACT)
    metrics = evaluation.metrics

    # Feature checks should pass.
    assert evaluation.checks["condition_evaluation"] is True
    assert evaluation.checks["condition_skip_on_false"] is True
    assert evaluation.checks["dependency_graph"] is True
    assert evaluation.checks["fail_propagation"] is True
    assert evaluation.checks["retry_mechanism"] is True
    assert evaluation.checks["timeout_enforcement"] is True
    assert evaluation.checks["output_capture"] is True
    assert evaluation.checks["template_resolution"] is True
    assert evaluation.checks["sub_recipe_execution"] is True
    assert evaluation.checks["sub_recipe_isolation"] is True

    # Test generation.
    assert evaluation.checks["has_tests"] is True
    assert metrics.test_generation == 1.0

    # Composite scores should be high for ideal artifact.
    assert metrics.baseline_score >= 0.8
    assert metrics.behavioral_alignment >= 0.8
    assert metrics.scenario_coverage >= 0.8


def test_evaluate_gherkin_artifact_penalizes_off_topic_output():
    off_topic = """
    # Todo List Application
    def create_todo(title):
        return {"title": title, "done": False}

    def delete_todo(id):
        todos.pop(id)
    """
    evaluation = evaluate_gherkin_artifact(off_topic)
    metrics = evaluation.metrics

    assert metrics.scenario_coverage == 0.0
    assert metrics.edge_case_handling == 0.0
    assert metrics.test_generation == 0.0
    assert metrics.baseline_score < 0.1


def test_evaluate_gherkin_artifact_partial_implementation():
    """Test that partial implementations get partial scores."""
    partial = """
    # Partial Recipe Step Executor - only conditions and dependencies

    class RecipeStepExecutor:
        def __init__(self, context=None):
            self.context = dict(context or {})
            self.results = {}

        def _evaluate_condition(self, condition):
            if not condition:
                return True
            try:
                return bool(eval(condition, {"__builtins__": {}}, self.context))
            except (NameError, KeyError):
                return False  # missing key -> skip

        def _check_dependencies(self, step):
            blocked_by = step.get("blockedBy", [])
            for dep_id in blocked_by:
                dep = self.results.get(dep_id)
                if dep and dep["status"] == "failed":
                    return "dependency_failed"
                # skip does not propagate failure
            return None

        async def execute(self, recipe):
            for step in recipe:
                dep_failure = self._check_dependencies(step)
                if dep_failure:
                    self.results[step["id"]] = {"status": "failed", "failure_reason": dep_failure}
                    continue
                condition = step.get("condition", "")
                if condition and not self._evaluate_condition(condition):
                    self.results[step["id"]] = {"status": "skipped"}
                    continue
                output = await self._run(step)
                self.context[step["id"]] = output
                self.results[step["id"]] = {"status": "completed"}
    """
    evaluation = evaluate_gherkin_artifact(partial)
    metrics = evaluation.metrics

    # Has conditions and dependencies, but not retry, timeout, sub-recipe.
    assert evaluation.checks["condition_evaluation"] is True
    assert evaluation.checks["dependency_graph"] is True
    assert metrics.scenario_coverage > 0.0
    assert metrics.scenario_coverage < 1.0


def test_evaluate_gherkin_artifact_spec_alignment_detects_gherkin_references():
    with_reference = """
    # Implementation based on the Gherkin feature scenarios
    # Given/When/Then patterns from the .feature file guided the design.
    """
    evaluation = evaluate_gherkin_artifact(with_reference)
    assert evaluation.checks["spec_alignment"] is True

    without_reference = """
    # Recipe step executor implementation
    # Standard patterns
    """
    evaluation = evaluate_gherkin_artifact(without_reference)
    assert evaluation.checks["spec_alignment"] is False


def test_condition_metrics_gherkin_fields_round_trip():
    """Verify Gherkin-specific metrics serialize and deserialize correctly."""
    metrics = ConditionMetrics(
        baseline_score=0.85,
        specification_coverage=0.9,
        scenario_coverage=1.0,
        step_implementation=0.857,
        edge_case_handling=0.8,
        test_generation=1.0,
        behavioral_alignment=0.917,
    )
    data = metrics.to_dict()
    assert data["scenario_coverage"] == 1.0
    assert data["step_implementation"] == 0.857
    assert data["edge_case_handling"] == 0.8
    assert data["test_generation"] == 1.0
    assert data["behavioral_alignment"] == 0.917
    # TLA+-specific fields should not be present (they are None).
    assert "invariant_compliance" not in data
    assert "proof_alignment" not in data

    restored = ConditionMetrics.from_dict(data)
    assert restored.scenario_coverage == 1.0
    assert restored.behavioral_alignment == 0.917
    assert restored.invariant_compliance is None


def test_condition_run_result_round_trip_with_gherkin_metrics(tmp_path):
    from amplihack.eval.tla_prompt_experiment import ExperimentCondition, load_condition_result

    condition = ExperimentCondition(
        experiment_id="gherkin-prompt-language-v2",
        target_id="recipe_step_executor",
        model_id="claude-opus-4.6",
        model_sdk="claude",
        prompt_variant_id="gherkin_only",
        repeat_index=1,
        prompt_path="prompts/recipe_step_executor_gherkin_only.md",
        spec_path="specs/recipe_step_executor.feature",
    )
    metrics = ConditionMetrics(
        baseline_score=0.85,
        specification_coverage=0.9,
        scenario_coverage=1.0,
        step_implementation=0.857,
        edge_case_handling=0.8,
        test_generation=1.0,
        behavioral_alignment=0.917,
    )
    result = ConditionRunResult(
        condition=condition,
        status="completed",
        metrics=metrics,
        notes=["generation_provider=replay"],
    )
    output_file = tmp_path / "run_result.json"
    write_condition_result(output_file, result)
    restored = load_condition_result(output_file)
    assert restored.status == "completed"
    assert restored.metrics.scenario_coverage == 1.0
    assert restored.metrics.behavioral_alignment == 0.917
    assert restored.metrics.invariant_compliance is None


def test_summarize_gherkin_results_groups_by_model_and_prompt_variant():
    from amplihack.eval.tla_prompt_experiment import ExperimentCondition

    def make_result(model_id, variant_id, scenario_cov, edge_case):
        condition = ExperimentCondition(
            experiment_id="gherkin-prompt-language-v2",
            target_id="recipe_step_executor",
            model_id=model_id,
            model_sdk="claude",
            prompt_variant_id=variant_id,
            repeat_index=1,
            prompt_path="p.md",
            spec_path="s.feature",
        )
        return ConditionRunResult(
            condition=condition,
            status="completed",
            metrics=ConditionMetrics(
                baseline_score=0.8,
                scenario_coverage=scenario_cov,
                edge_case_handling=edge_case,
            ),
        )

    results = [
        make_result("claude-opus-4.6", "gherkin_only", 1.0, 0.8),
        make_result("claude-opus-4.6", "english", 0.6, 0.4),
        make_result("gpt-5.4", "gherkin_only", 0.8, 0.6),
        make_result("gpt-5.4", "english", 0.4, 0.2),
    ]
    summary = summarize_condition_results(results)
    assert summary.completed_conditions == 4
    assert "gherkin_only" in summary.by_prompt_variant
    assert "english" in summary.by_prompt_variant
    assert "scenario_coverage" in summary.by_prompt_variant["gherkin_only"]
    assert "edge_case_handling" in summary.by_prompt_variant["gherkin_only"]


def test_run_gherkin_prompt_experiment_requires_live_opt_in():
    with pytest.raises(ValueError, match="allow_live"):
        run_gherkin_prompt_experiment("/tmp/test-run")


def test_run_gherkin_prompt_experiment_replay_mode_writes_reports(tmp_path):
    """Full end-to-end: materialize, write ideal artifacts, run experiment."""
    manifest = load_default_gherkin_manifest()

    # Materialize condition packets.
    packets_dir = tmp_path / "packets"
    packets = materialize_condition_packets(packets_dir, smoke=True, manifest=manifest)
    assert len(packets) == 8

    # Write ideal artifact into each condition directory (replay mode).
    for packet in packets:
        from pathlib import Path

        artifact_file = Path(packet.condition_dir) / "generated_artifact.md"
        artifact_file.write_text(IDEAL_EXECUTOR_ARTIFACT)

    # Run experiment in replay mode.
    run_dir = tmp_path / "run"
    report = run_gherkin_prompt_experiment(
        run_dir,
        smoke=True,
        manifest=manifest,
        replay_dir=packets_dir,
    )

    assert report.experiment_id == "gherkin-prompt-language-v2"
    assert report.completed_conditions == 8
    assert report.failed_conditions == 0
    assert report.replay_mode is True

    # Check that output files exist.
    assert (run_dir / "experiment_report.json").exists()
    assert (run_dir / "experiment_report.md").exists()
    assert (run_dir / "matrix.json").exists()

    # Verify Gherkin-specific metrics are present in summary.
    summary = report.summary
    assert "scenario_coverage" in summary.metric_summary
    assert "edge_case_handling" in summary.metric_summary
    assert "test_generation" in summary.metric_summary
    assert "behavioral_alignment" in summary.metric_summary

    # Verify each condition was evaluated correctly.
    for condition_id_dir in sorted(run_dir.iterdir()):
        if not condition_id_dir.is_dir():
            continue
        eval_file = condition_id_dir / "evaluation.json"
        if eval_file.exists():
            eval_data = json.loads(eval_file.read_text())
            assert eval_data["evaluation_kind"] == "heuristic_signal_v2"
            assert "scenario_coverage" in eval_data["metrics"]


def test_main_prints_matrix_on_default_invocation(capsys):
    exit_code = main([])
    assert exit_code == 0
    output = capsys.readouterr().out
    data = json.loads(output)
    assert data["experiment_id"] == "gherkin-prompt-language-v2"
    assert data["target_id"] == "recipe_step_executor"
    assert len(data["conditions"]) == 24  # full matrix
