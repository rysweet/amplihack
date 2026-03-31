"""Tests for gherkin_prompt_experiment.py — Gherkin v2 recipe step executor scoring.

Tests verify that the 6-feature heuristic evaluation correctly scores generated
artifacts based on keyword/pattern matching for:
1. Conditional execution
2. Dependency handling
3. Retry logic
4. Timeout semantics
5. Output capture
6. Sub-recipe delegation

Testing pyramid: 80% unit (fast heuristic checks), 20% integration (manifest + CLI).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from amplihack.eval.gherkin_prompt_experiment import (
    default_gherkin_v2_manifest_path,
    evaluate_gherkin_artifact,
    load_gherkin_v2_manifest,
    main,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


PERFECT_ARTIFACT = """
class RecipeStepExecutor:
    \"\"\"Execute recipe steps with conditions, dependencies, retries, timeouts,
    output capture, and sub-recipe delegation.\"\"\"

    def execute(self, recipe: list[dict], context: dict) -> dict:
        # Build dependency graph and execute in topological order (DAG)
        steps = self._topological_sort(recipe)
        results = {}

        for step in steps:
            step_id = step["id"]

            # Check dependencies - blockedBy
            if not self._dependencies_satisfied(step, results):
                results[step_id] = {"status": "failed", "failure_reason": "dependency_failed"}
                # Failure propagation: blocked by failed step propagates failure
                continue

            # Skip does not propagate - step blocked by skipped dep executes normally

            # Evaluate condition against context dict
            condition = step.get("condition")
            if condition:
                try:
                    if not eval(condition, {}, context):
                        results[step_id] = {"status": "skipped"}
                        continue
                except (NameError, KeyError):
                    # Condition referencing missing key evaluates to false
                    results[step_id] = {"status": "skipped"}
                    continue

            # Handle sub_recipe delegation
            if "sub_recipe" in step:
                child_context = context.copy()  # Child context inherits parent context
                child_result = self.execute(step["sub_recipe"], child_context)
                # Context isolation: child outputs don't propagate unless propagate_outputs
                if step.get("propagate_outputs"):
                    context.update(child_context)
                # Sub-recipe failure means parent step fails - not retried
                if any(r["status"] == "failed" for r in child_result.values()):
                    results[step_id] = {"status": "failed"}
                    continue
                results[step_id] = {"status": "completed"}
                continue

            # Execute with retry and exponential backoff
            max_retries = step.get("max_retries", 0)
            timeout_seconds = step.get("timeout_seconds", 60)
            attempt_count = 0

            for attempt in range(max_retries + 1):
                attempt_count += 1
                try:
                    import asyncio
                    output = asyncio.wait_for(
                        self._run_command(step["command"]),
                        timeout=timeout_seconds
                    )
                    # Output capture: store in context[step_id]
                    context[step_id] = output
                    results[step_id] = {
                        "status": "completed",
                        "output": output,
                        "attempt_count": attempt_count,
                    }
                    break
                except asyncio.TimeoutError:
                    # Timed out - NOT retried even if max_retries set
                    # Timed_out counts as failure for dependency propagation
                    results[step_id] = {
                        "status": "timed_out",
                        "attempt_count": attempt_count,
                    }
                    break  # timeout_no_retry
                except Exception:
                    if attempt < max_retries:
                        import time
                        delay = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        time.sleep(delay)
                        # Retry output replacement - overwrite previous attempt
                        continue
                    # All retries exhausted
                    results[step_id] = {
                        "status": "failed",
                        "attempt_count": attempt_count,
                    }

        return results

    def _topological_sort(self, recipe):
        # DAG-based execution order
        pass

    def _dependencies_satisfied(self, step, results):
        for dep_id in step.get("blockedBy", []):
            dep = results.get(dep_id)
            if dep and dep["status"] in ("failed", "timed_out"):
                return False  # dependency_failed propagation
            # Skipped dependency: proceed normally
        return True


# Template resolution: replace {{step_id}} with context values
def resolve_templates(text, context):
    import re
    def replacer(match):
        key = match.group(1)
        return context.get(key, match.group(0))
    return re.sub(r'\\{\\{(\\w+)\\}\\}', replacer, text)


# Focused tests
import pytest

def test_conditional_execution():
    executor = RecipeStepExecutor()
    context = {"env": "prod"}
    recipe = [{"id": "s1", "command": "echo hello", "condition": "env == 'prod'"}]
    results = executor.execute(recipe, context)
    assert results["s1"]["status"] == "completed"

def test_retry_with_exponential_backoff():
    # Tests retry mechanism with 1s, 2s, 4s delays
    pass

def test_timeout_handling():
    # Timeout terminates and is not retried
    pass

def test_dependency_graph():
    # Step blocked by failed dep is marked dependency_failed
    pass

def test_output_capture():
    # Output stored in context
    pass

def test_sub_recipe_delegation():
    # Sub-recipe runs in child context with isolation
    pass
"""

MINIMAL_ARTIFACT = """
def execute_steps(steps, context):
    for step in steps:
        result = run(step["command"])
        context[step["id"]] = result
"""

EMPTY_ARTIFACT = ""


# ---------------------------------------------------------------------------
# Unit Tests — evaluate_gherkin_artifact scoring
# ---------------------------------------------------------------------------


class TestEvaluateGherkinArtifact:
    """Test the 6-feature heuristic scoring."""

    def test_perfect_artifact_scores_high(self):
        evaluation = evaluate_gherkin_artifact(PERFECT_ARTIFACT)
        metrics = evaluation.metrics
        # A well-written artifact should score > 0.5 on most features
        assert metrics.baseline_score is not None and metrics.baseline_score > 0.5
        assert metrics.invariant_compliance is not None and metrics.invariant_compliance > 0.5
        assert metrics.proof_alignment is not None and metrics.proof_alignment > 0.5
        assert (
            metrics.local_protocol_alignment is not None and metrics.local_protocol_alignment > 0.5
        )
        assert metrics.progress_signal is not None and metrics.progress_signal > 0.5
        assert metrics.specification_coverage is not None and metrics.specification_coverage > 0.5

    def test_minimal_artifact_scores_low(self):
        evaluation = evaluate_gherkin_artifact(MINIMAL_ARTIFACT)
        metrics = evaluation.metrics
        # A minimal artifact should score low across features
        total = sum(
            v
            for v in [
                metrics.baseline_score,
                metrics.invariant_compliance,
                metrics.proof_alignment,
                metrics.local_protocol_alignment,
                metrics.progress_signal,
                metrics.specification_coverage,
            ]
            if v is not None
        )
        assert total < 3.0  # Low aggregate score

    def test_empty_artifact_scores_zero(self):
        evaluation = evaluate_gherkin_artifact(EMPTY_ARTIFACT)
        metrics = evaluation.metrics
        assert metrics.baseline_score == 0.0
        assert metrics.invariant_compliance == 0.0
        assert metrics.proof_alignment == 0.0
        assert metrics.local_protocol_alignment == 0.0
        assert metrics.progress_signal == 0.0
        assert metrics.specification_coverage == 0.0

    def test_checks_are_booleans(self):
        evaluation = evaluate_gherkin_artifact(PERFECT_ARTIFACT)
        for check_name, value in evaluation.checks.items():
            assert isinstance(value, bool), f"Check {check_name} is not bool: {type(value)}"

    def test_notes_contain_missing_signals(self):
        evaluation = evaluate_gherkin_artifact(MINIMAL_ARTIFACT)
        missing_notes = [n for n in evaluation.notes if "Missing heuristic signal" in n]
        assert len(missing_notes) > 0  # Should have some missing signals

    def test_evaluation_to_dict_roundtrip(self):
        evaluation = evaluate_gherkin_artifact(PERFECT_ARTIFACT)
        d = evaluation.to_dict()
        assert "metrics" in d
        assert "checks" in d
        assert "notes" in d
        assert isinstance(d["metrics"], dict)
        assert isinstance(d["checks"], dict)


class TestConditionalExecutionScoring:
    """Test Feature 1: Conditional execution heuristics."""

    def test_condition_evaluation_detected(self):
        text = "evaluate the condition expression against the context dict, skip if false"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["condition_evaluation"] is True

    def test_condition_skip_detected(self):
        text = "step status is skipped when condition is false"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["condition_skip"] is True

    def test_missing_key_handling_detected(self):
        text = "except KeyError: handle missing key in context.get()"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["condition_missing_key"] is True


class TestDependencyHandlingScoring:
    """Test Feature 2: Dependency handling heuristics."""

    def test_dependency_graph_detected(self):
        text = (
            "check blockedBy dependencies. if dependency completed, proceed. if failed, propagate"
        )
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["dependency_graph"] is True

    def test_failure_propagation_detected(self):
        text = "dependency_failed: step blocked by failed dependency"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["failure_propagation"] is True

    def test_skip_no_propagation_detected(self):
        text = "skip does not propagate failure, skipped dep proceeds normally"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["skip_no_propagation"] is True

    def test_dag_ordering_detected(self):
        text = "topological sort of the dependency graph DAG"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["dag_ordering"] is True


class TestRetryLogicScoring:
    """Test Feature 3: Retry logic heuristics."""

    def test_retry_mechanism_detected(self):
        text = "retry up to max_retries attempts on failure with except handling"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["retry_mechanism"] is True

    def test_exponential_backoff_detected(self):
        text = "exponential backoff delays: 1s, 2s, 4s"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["exponential_backoff"] is True

    def test_retry_exhaustion_detected(self):
        text = "all retries exhausted, attempt_count equals max"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["retry_exhaustion"] is True


class TestTimeoutSemanticsScoring:
    """Test Feature 4: Timeout semantics heuristics."""

    def test_timeout_mechanism_detected(self):
        text = "if timeout_seconds exceeded, terminate the step and mark timed_out"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["timeout_mechanism"] is True

    def test_timeout_no_retry_detected(self):
        text = "timed_out steps are not retried even with max_retries"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["timeout_no_retry"] is True

    def test_timeout_as_failure_detected(self):
        text = "timed_out counts as failure, propagates dependency_failed"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["timeout_as_failure"] is True


class TestOutputCaptureScoring:
    """Test Feature 5: Output capture heuristics."""

    def test_output_capture_detected(self):
        text = "capture stdout output and store in context[step_id] dict"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["output_capture"] is True

    def test_template_resolution_detected(self):
        text = "resolve {{step_id}} template interpolation using re.sub"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["template_resolution"] is True


class TestSubRecipeDelegationScoring:
    """Test Feature 6: Sub-recipe delegation heuristics."""

    def test_sub_recipe_execution_detected(self):
        text = "if sub_recipe is present, run the child recipe in a child context"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["sub_recipe_execution"] is True

    def test_context_isolation_detected(self):
        text = "child context inherits parent context, propagate_outputs controls isolation"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["context_isolation"] is True

    def test_sub_recipe_failure_detected(self):
        text = "sub-recipe failure marks parent as failed, not retried"
        evaluation = evaluate_gherkin_artifact(text)
        assert evaluation.checks["sub_recipe_failure"] is True


# ---------------------------------------------------------------------------
# Integration Tests — manifest loading and CLI
# ---------------------------------------------------------------------------


class TestManifestLoading:
    """Test manifest loading and validation."""

    def test_manifest_path_construction(self):
        path = default_gherkin_v2_manifest_path("/tmp/fake_root")
        assert str(path).endswith("gherkin_v2_recipe_executor/manifest.json")

    def test_load_manifest_from_repo(self):
        """Load the actual manifest and verify structure."""
        manifest = load_gherkin_v2_manifest()
        assert manifest.experiment_id == "gherkin-v2-recipe-executor"
        assert manifest.generation_target.target_id == "recipe_step_executor"
        assert len(manifest.prompt_variants) == 4
        assert len(manifest.models) == 2

    def test_manifest_variant_ids(self):
        manifest = load_gherkin_v2_manifest()
        variant_ids = {v.variant_id for v in manifest.prompt_variants}
        assert variant_ids == {
            "english",
            "gherkin_only",
            "gherkin_plus_english",
            "gherkin_plus_acceptance",
        }

    def test_manifest_model_ids(self):
        manifest = load_gherkin_v2_manifest()
        model_ids = {m.model_id for m in manifest.models}
        assert model_ids == {"claude-opus-4.6", "gpt-5.4"}

    def test_smoke_matrix_expansion(self):
        manifest = load_gherkin_v2_manifest()
        conditions = manifest.expand_matrix(smoke=True)
        # 4 variants x 2 models x 1 repeat = 8
        assert len(conditions) == 8

    def test_full_matrix_expansion(self):
        manifest = load_gherkin_v2_manifest()
        conditions = manifest.expand_matrix(smoke=False)
        # 4 variants x 2 models x 3 repeats = 24
        assert len(conditions) == 24

    def test_prompt_bundles_load(self):
        manifest = load_gherkin_v2_manifest()
        for variant in manifest.prompt_variants:
            bundle = manifest.load_prompt_bundle(variant.variant_id)
            assert len(bundle.prompt_text) > 0
            combined = bundle.combined_text()
            assert len(combined) > 0
            if variant.append_spec:
                assert "Feature:" in combined or "Scenario:" in combined


class TestCLI:
    """Test CLI entry point."""

    def test_cli_matrix_output(self):
        """Test that --smoke produces valid JSON output."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name
        try:
            exit_code = main(["--smoke", "--output", output_path])
            assert exit_code == 0
            data = json.loads(Path(output_path).read_text())
            assert data["experiment_id"] == "gherkin-v2-recipe-executor"
            assert data["matrix_mode"] == "smoke"
            assert len(data["conditions"]) == 8
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_cli_variant_output(self):
        """Test that --variant prints combined prompt text."""
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = main(["--variant", "english"])
        assert exit_code == 0
        output = buf.getvalue()
        assert "RecipeStepExecutor" in output or "recipe" in output.lower()
