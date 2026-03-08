"""Outside-in tests verifying that review and outside-in testing steps
are NOT skipped during multitask/parallel workstream execution (fix #2925).

Root causes fixed:
1. smart-orchestrator.yaml: validate-outside-in-testing had a condition
   that required PR URLs in round_1_result. For parallel/multitask workstreams
   round_1_result is the orchestrator report (no PR URLs) → step was SKIPPED.
   Fix: condition now checks task_type == Development, not PR URL presence.

2. default-workflow.yaml: step-17a-compliance-verification only echoed
   instructions without checking local_testing_gate — it was a no-op.
   Fix: step now reads local_testing_gate and exits 1 if empty.

Usage:
    uv run pytest tests/outside_in/test_multitask_mandatory_review_steps.py -v
"""

import ast
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SMART_ORCH_YAML = REPO_ROOT / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"
DEFAULT_WF_YAML = REPO_ROOT / "amplifier-bundle" / "recipes" / "default-workflow.yaml"
SRC_SMART_ORCH_YAML = (
    REPO_ROOT / "src" / "amplihack" / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_steps(yaml_path: Path) -> dict:
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    return {s["id"]: s for s in data.get("steps", [])}


# ---------------------------------------------------------------------------
# Fix #2925 Part 1: validate-outside-in-testing condition
# ---------------------------------------------------------------------------

class TestValidateOutsideInTestingCondition:
    """The validate-outside-in-testing condition must not require PR URLs.

    For parallel/multitask workstreams, round_1_result is an orchestrator
    report that never contains PR URLs. The old condition caused this step
    to be permanently SKIPPED for all multi-workstream executions.
    """

    def test_condition_does_not_require_pull_url(self):
        """Condition must NOT contain 'pull/' string check."""
        steps = _load_steps(SMART_ORCH_YAML)
        step = steps.get("validate-outside-in-testing")
        assert step is not None, "validate-outside-in-testing step not found"

        condition = step.get("condition", "")
        assert "pull/" not in condition, (
            "validate-outside-in-testing condition must not check for 'pull/' "
            "in round_1_result — that check causes the step to be SKIPPED for "
            "parallel workstreams where round_1_result is an orchestrator report "
            "with no PR URLs. Fix: condition should check task_type instead."
        )

    def test_condition_triggers_for_development_tasks(self):
        """Condition must evaluate True for Development tasks with results."""
        from amplihack.recipes.context import RecipeContext

        steps = _load_steps(SMART_ORCH_YAML)
        step = steps["validate-outside-in-testing"]
        condition = step.get("condition", "")

        ctx = RecipeContext()
        ctx.set("task_type", "Development")
        ctx.set("round_1_result", "Workstream completed. Branch: feat/issue-123-add-auth")
        ctx.set("round_2_result", "")
        ctx.set("round_3_result", "")

        result = ctx.evaluate(condition)
        assert result is True, (
            f"validate-outside-in-testing should trigger for Development tasks "
            f"even without PR URLs in round_1_result. Condition: {condition!r}"
        )

    def test_condition_triggers_for_parallel_workstream_report(self):
        """Condition must evaluate True when round_1_result is an orchestrator report."""
        from amplihack.recipes.context import RecipeContext

        steps = _load_steps(SMART_ORCH_YAML)
        step = steps["validate-outside-in-testing"]
        condition = step.get("condition", "")

        # This simulates the actual orchestrator report output for parallel workstreams
        orchestrator_report = """
        ======================================================================
        PARALLEL WORKSTREAM REPORT
        Mode: recipe
        ======================================================================

        [123] Add user authentication
          Branch:  feat/add-auth
          Status:  OK
          Runtime: 3600s
          Log:     /tmp/amplihack-workstreams/log-123.txt

        [124] Add structured logging
          Branch:  feat/add-logging
          Status:  OK
          Runtime: 2400s
          Log:     /tmp/amplihack-workstreams/log-124.txt

        Total: 2 | Succeeded: 2 | Failed: 0
        """

        ctx = RecipeContext()
        ctx.set("task_type", "Development")
        ctx.set("round_1_result", orchestrator_report)
        ctx.set("round_2_result", "")
        ctx.set("round_3_result", "")

        result = ctx.evaluate(condition)
        assert result is True, (
            "validate-outside-in-testing must trigger even when round_1_result "
            "is an orchestrator report without PR URLs. This is the key fix for "
            f"#2925. Condition evaluated to False. Condition: {condition!r}"
        )

    def test_condition_skips_for_qa_tasks(self):
        """Condition must evaluate False for Q&A tasks (no code changes)."""
        from amplihack.recipes.context import RecipeContext

        steps = _load_steps(SMART_ORCH_YAML)
        step = steps["validate-outside-in-testing"]
        condition = step.get("condition", "")

        ctx = RecipeContext()
        ctx.set("task_type", "Q&A")
        ctx.set("round_1_result", "Here is the answer to your question...")
        ctx.set("round_2_result", "")
        ctx.set("round_3_result", "")

        result = ctx.evaluate(condition)
        assert result is False, (
            "validate-outside-in-testing should NOT trigger for Q&A tasks"
        )

    def test_condition_skips_for_operations_tasks(self):
        """Condition must evaluate False for Operations tasks."""
        from amplihack.recipes.context import RecipeContext

        steps = _load_steps(SMART_ORCH_YAML)
        step = steps["validate-outside-in-testing"]
        condition = step.get("condition", "")

        ctx = RecipeContext()
        ctx.set("task_type", "Operations")
        ctx.set("round_1_result", "Completed disk cleanup. Freed 10GB.")
        ctx.set("round_2_result", "")
        ctx.set("round_3_result", "")

        result = ctx.evaluate(condition)
        assert result is False, (
            "validate-outside-in-testing should NOT trigger for Operations tasks"
        )

    def test_condition_skips_when_no_results(self):
        """Condition must evaluate False when round_1_result is empty."""
        from amplihack.recipes.context import RecipeContext

        steps = _load_steps(SMART_ORCH_YAML)
        step = steps["validate-outside-in-testing"]
        condition = step.get("condition", "")

        ctx = RecipeContext()
        ctx.set("task_type", "Development")
        ctx.set("round_1_result", "")
        ctx.set("round_2_result", "")
        ctx.set("round_3_result", "")

        result = ctx.evaluate(condition)
        assert result is False, (
            "validate-outside-in-testing should NOT trigger when round_1_result is empty"
        )

    def test_condition_uses_safe_ast_nodes(self):
        """Condition must use only safe AST nodes (no function calls)."""
        steps = _load_steps(SMART_ORCH_YAML)
        step = steps["validate-outside-in-testing"]
        condition = step.get("condition", "")

        tree = ast.parse(condition, mode="eval")
        for node in ast.walk(tree):
            assert not isinstance(node, ast.Call), (
                f"validate-outside-in-testing condition contains function call "
                f"(unsafe for evaluator): {condition!r}"
            )


# ---------------------------------------------------------------------------
# Fix #2925 Part 2: step-17a-compliance-verification enforcement
# ---------------------------------------------------------------------------

class TestStep17aComplianceVerification:
    """step-17a must actually check local_testing_gate and fail if empty.

    Previously this step only echoed instructions — it never blocked review
    when step-13 (outside-in testing) was not completed.
    """

    def test_step_17a_exits_nonzero_when_testing_gate_empty(self):
        """step-17a must exit with code 1 when local_testing_gate is empty."""
        steps = _load_steps(DEFAULT_WF_YAML)
        step = steps.get("step-17a-compliance-verification")
        assert step is not None, "step-17a-compliance-verification not found"
        assert step.get("type") == "bash", "step-17a must be a bash step"

        command_template = step.get("command", "")

        # Render with empty local_testing_gate (simulates step-13 not running)
        command = command_template.replace("{{local_testing_gate}}", "''")

        result = subprocess.run(
            ["/bin/bash", "-c", command],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, (
            "step-17a-compliance-verification must exit non-zero when "
            "local_testing_gate is empty (step-13 was not completed). "
            f"Got exit code {result.returncode}. "
            "This is the key enforcement fix for #2925."
        )
        assert "COMPLIANCE FAILURE" in result.stdout or "COMPLIANCE FAILURE" in result.stderr, (
            "step-17a must output 'COMPLIANCE FAILURE' when testing gate is missing"
        )

    def test_step_17a_succeeds_when_testing_gate_populated(self):
        """step-17a must succeed (exit 0) when local_testing_gate has content."""
        steps = _load_steps(DEFAULT_WF_YAML)
        step = steps["step-17a-compliance-verification"]
        command_template = step.get("command", "")

        # Render with non-empty local_testing_gate (simulates step-13 completing)
        testing_output = "'Step 13: Local Testing Results PASS scenario 1 PASS scenario 2'"
        command = command_template.replace("{{local_testing_gate}}", testing_output)

        result = subprocess.run(
            ["/bin/bash", "-c", command],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            "step-17a-compliance-verification must succeed when local_testing_gate "
            f"is populated. Got exit code {result.returncode}. "
            f"stdout: {result.stdout[:300]}"
        )

    def test_step_17a_command_contains_exit_1(self):
        """step-17a command must contain 'exit 1' to hard-fail on missing testing."""
        steps = _load_steps(DEFAULT_WF_YAML)
        step = steps["step-17a-compliance-verification"]
        command = step.get("command", "")

        assert "exit 1" in command, (
            "step-17a-compliance-verification must contain 'exit 1' to hard-fail "
            "when local_testing_gate is empty. This enforces that outside-in "
            "testing (step-13) cannot be bypassed."
        )

    def test_step_17a_checks_local_testing_gate_variable(self):
        """step-17a command must reference local_testing_gate context variable."""
        steps = _load_steps(DEFAULT_WF_YAML)
        step = steps["step-17a-compliance-verification"]
        command = step.get("command", "")

        assert "{{local_testing_gate}}" in command, (
            "step-17a-compliance-verification must reference {{local_testing_gate}} "
            "to check whether step-13 (outside-in testing) was completed."
        )

    def test_step_17a_output_field_is_set(self):
        """step-17a must have an output field for downstream steps."""
        steps = _load_steps(DEFAULT_WF_YAML)
        step = steps["step-17a-compliance-verification"]
        assert step.get("output"), (
            "step-17a must have an 'output' field so its result is captured"
        )


# ---------------------------------------------------------------------------
# Recipe file sync (repo root = src/)
# ---------------------------------------------------------------------------

class TestSmartOrchestratorSync:
    """Both copies of smart-orchestrator.yaml must be identical after the fix."""

    def test_smart_orchestrator_copies_are_in_sync(self):
        """amplifier-bundle/ and src/ copies of smart-orchestrator.yaml must match."""
        if not SMART_ORCH_YAML.exists() or not SRC_SMART_ORCH_YAML.exists():
            pytest.skip("One or both smart-orchestrator.yaml copies not found")

        repo_content = SMART_ORCH_YAML.read_text()
        src_content = SRC_SMART_ORCH_YAML.read_text()

        assert repo_content == src_content, (
            "smart-orchestrator.yaml is out of sync between "
            "amplifier-bundle/recipes/ and src/amplihack/amplifier-bundle/recipes/. "
            "Run: cp amplifier-bundle/recipes/smart-orchestrator.yaml "
            "src/amplihack/amplifier-bundle/recipes/smart-orchestrator.yaml"
        )

    def test_fixed_condition_is_in_both_copies(self):
        """Both copies must contain the fixed condition (without 'pull/' check)."""
        for yaml_path in [SMART_ORCH_YAML, SRC_SMART_ORCH_YAML]:
            if not yaml_path.exists():
                pytest.skip(f"{yaml_path} not found")

            steps = _load_steps(yaml_path)
            step = steps.get("validate-outside-in-testing")
            assert step is not None, f"validate-outside-in-testing not in {yaml_path}"

            condition = step.get("condition", "")
            assert "pull/" not in condition, (
                f"Fixed condition (without 'pull/' check) not found in {yaml_path}. "
                "Both copies must be updated for #2925 fix."
            )


# ---------------------------------------------------------------------------
# Standalone runner (for direct execution without pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    print("=" * 70)
    print("Outside-In Tests: Multitask Review/Testing Step Enforcement (#2925)")
    print("=" * 70)

    failures = 0
    test_classes = [
        TestValidateOutsideInTestingCondition,
        TestStep17aComplianceVerification,
        TestSmartOrchestratorSync,
    ]

    for cls in test_classes:
        instance = cls()
        print(f"\n{cls.__name__}:")
        for name in dir(instance):
            if not name.startswith("test_"):
                continue
            fn = getattr(instance, name)
            try:
                fn()
                print(f"  PASS  {name}")
            except (AssertionError, Exception) as e:
                print(f"  FAIL  {name}: {e}")
                failures += 1

    print(f"\n{'=' * 70}")
    total = sum(
        len([n for n in dir(cls) if n.startswith("test_")])
        for cls in test_classes
    )
    print(f"Results: {total - failures}/{total} passed")
    if failures:
        print(f"FAILED: {failures} test(s)")
        sys.exit(1)
    else:
        print("ALL PASSED")
