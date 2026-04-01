"""Tests for RecipeStepExecutor — covers every Gherkin scenario plus
cross-feature interactions.

Test naming convention: test_f{feature}_{scenario_summary}
Cross-feature tests: test_cross_{summary}
"""

import time

from recipe_step_executor import (
    RecipeStepExecutor,
    StepStatus,
    _effective_max_retries,
    _evaluate_condition,
    _parse_dependencies,
    _resolve_templates,
)

# ── Helpers ──────────────────────────────────────────────────────────


def make_executor():
    """Create executor with no-op sleep, returning (executor, recorded_delays)."""
    delays = []

    def record_sleep(d):
        delays.append(d)

    return RecipeStepExecutor(sleep_func=record_sleep), delays


def run(steps, context=None):
    """Convenience: execute steps, return (results_dict, context)."""
    ctx = context if context is not None else {}
    executor, _ = make_executor()
    out = executor.execute({"steps": steps}, ctx)
    return out["results"], out["context"]


def run_full(steps, context=None):
    """Return full output including execution_events."""
    ctx = context if context is not None else {}
    executor, delays = make_executor()
    executor._sleep_func = lambda d: delays.append(d)
    out = executor.execute({"steps": steps}, ctx)
    return out["results"], out["context"], out["execution_events"], delays


# ======================================================================
# Feature 1: Conditional Step Execution
# ======================================================================


class TestConditionalExecution:
    def test_f1_unconditional_step_always_executes(self):
        results, ctx = run([{"id": "step_a", "command": 'echo "hello"'}])
        assert results["step_a"].status == StepStatus.COMPLETED
        assert ctx["step_a"] == "hello"

    def test_f1_condition_true_executes(self):
        results, _ = run(
            [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}],
            context={"env": "prod"},
        )
        assert results["step_a"].status == StepStatus.COMPLETED

    def test_f1_condition_false_skips(self):
        results, ctx = run(
            [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}],
            context={"env": "staging"},
        )
        assert results["step_a"].status == StepStatus.SKIPPED
        assert "step_a" not in ctx

    def test_f1_missing_key_evaluates_false(self):
        results, _ = run(
            [{"id": "step_a", "command": 'echo "go"', "condition": "feature_flag == True"}]
        )
        assert results["step_a"].status == StepStatus.SKIPPED


# ======================================================================
# Feature 2: Step Dependencies
# ======================================================================


class TestDependencies:
    def test_f2_dependency_ordering(self):
        results, ctx, events, _ = run_full(
            [
                {"id": "step_a", "command": 'echo "first"'},
                {"id": "step_b", "command": 'echo "second"', "blockedBy": "step_a"},
            ]
        )
        assert results["step_b"].status == StepStatus.COMPLETED
        # step_a end must come before step_b start
        a_end = next(i for i, e in enumerate(events) if e == ("step_a", "end"))
        b_start = next(i for i, e in enumerate(events) if e == ("step_b", "start"))
        assert a_end < b_start

    def test_f2_failed_dependency_propagates(self):
        results, _ = run(
            [
                {"id": "step_a", "command": "exit 1"},
                {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
            ]
        )
        assert results["step_a"].status == StepStatus.FAILED
        assert results["step_b"].status == StepStatus.FAILED
        assert results["step_b"].failure_reason == "dependency_failed"

    def test_f2_skipped_dependency_allows_execution(self):
        results, _ = run(
            [
                {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
                {"id": "step_b", "command": 'echo "runs"', "blockedBy": "step_a"},
            ],
            context={"env": "staging"},
        )
        assert results["step_a"].status == StepStatus.SKIPPED
        assert results["step_b"].status == StepStatus.COMPLETED

    def test_f2_diamond_dependency(self):
        results, ctx, events, _ = run_full(
            [
                {"id": "step_a", "command": 'echo "root"'},
                {"id": "step_b", "command": 'echo "left"', "blockedBy": "step_a"},
                {"id": "step_c", "command": 'echo "right"', "blockedBy": "step_a"},
                {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
            ]
        )

        def end_index(sid):
            return next(i for i, e in enumerate(events) if e == (sid, "end"))

        def start_index(sid):
            return next(i for i, e in enumerate(events) if e == (sid, "start"))

        assert end_index("step_a") < start_index("step_b")
        assert end_index("step_a") < start_index("step_c")
        assert end_index("step_b") < start_index("step_d")
        assert end_index("step_c") < start_index("step_d")
        assert results["step_d"].status == StepStatus.COMPLETED


# ======================================================================
# Feature 3: Retry with Exponential Backoff
# ======================================================================


class TestRetry:
    def test_f3_no_retries_fails_immediately(self):
        results, _ = run([{"id": "step_a", "command": "exit 1", "max_retries": 0}])
        assert results["step_a"].status == StepStatus.FAILED
        assert results["step_a"].attempt_count == 1

    def test_f3_succeeds_on_second_attempt(self):
        results, _ = run([{"id": "step_a", "command": "fail_then_succeed(1)", "max_retries": 3}])
        assert results["step_a"].status == StepStatus.COMPLETED
        assert results["step_a"].attempt_count == 2

    def test_f3_exhausts_retries(self):
        results, ctx, events, delays = run_full(
            [{"id": "step_a", "command": "exit 1", "max_retries": 3}]
        )
        assert results["step_a"].status == StepStatus.FAILED
        assert results["step_a"].attempt_count == 4
        assert delays == [1.0, 2.0, 4.0]
        assert results["step_a"].retry_delays == [1.0, 2.0, 4.0]


# ======================================================================
# Feature 4: Timeout Handling
# ======================================================================


class TestTimeout:
    def test_f4_step_exceeds_timeout(self):
        # Use real time.sleep for the timeout mechanism (threading-based)
        executor = RecipeStepExecutor()
        t0 = time.monotonic()
        out = executor.execute(
            {"steps": [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 0.5}]},
            {},
        )
        elapsed = time.monotonic() - t0
        assert out["results"]["step_a"].status == StepStatus.TIMED_OUT
        assert 0.3 < elapsed < 2.0  # roughly 0.5s with tolerance

    def test_f4_timeout_not_retried(self):
        executor = RecipeStepExecutor()
        out = executor.execute(
            {
                "steps": [
                    {
                        "id": "step_a",
                        "command": "sleep 30",
                        "timeout_seconds": 0.3,
                        "max_retries": 3,
                    }
                ]
            },
            {},
        )
        assert out["results"]["step_a"].status == StepStatus.TIMED_OUT
        assert out["results"]["step_a"].attempt_count == 1

    def test_f4_timeout_propagates_as_dependency_failure(self):
        executor = RecipeStepExecutor()
        out = executor.execute(
            {
                "steps": [
                    {"id": "step_a", "command": "sleep 30", "timeout_seconds": 0.3},
                    {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
                ]
            },
            {},
        )
        assert out["results"]["step_a"].status == StepStatus.TIMED_OUT
        assert out["results"]["step_b"].status == StepStatus.FAILED
        assert out["results"]["step_b"].failure_reason == "dependency_failed"


# ======================================================================
# Feature 5: Output Capture
# ======================================================================


class TestOutputCapture:
    def test_f5_output_stored_in_context(self):
        results, ctx = run([{"id": "step_a", "command": 'echo "result_value"'}])
        assert ctx["step_a"] == "result_value"

    def test_f5_template_resolves_prior_output(self):
        results, ctx = run(
            [
                {"id": "step_a", "command": 'echo "data_123"'},
                {
                    "id": "step_b",
                    "command": 'echo "processing {{step_a}}"',
                    "blockedBy": "step_a",
                },
            ]
        )
        assert ctx["step_b"] == "processing data_123"


# ======================================================================
# Feature 6: Sub-recipe Delegation
# ======================================================================


class TestSubRecipe:
    def test_f6_child_inherits_parent_context(self):
        results, ctx = run(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": "echo {{parent_val}}"}],
                }
            ],
            context={"parent_val": "shared"},
        )
        assert results["step_a"].status == StepStatus.COMPLETED
        # child_1 executed with parent_val — verify via sub_results
        child_res = results["step_a"].sub_results["child_1"]
        assert child_res.status == StepStatus.COMPLETED
        assert child_res.output == "shared"

    def test_f6_no_propagation_by_default(self):
        results, ctx = run(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "secret"'}],
                    "propagate_outputs": False,
                },
                {"id": "step_b", "command": 'echo "{{child_1}}"'},
            ]
        )
        assert "child_1" not in ctx
        assert ctx["step_b"] == "{{child_1}}"

    def test_f6_propagation_when_true(self):
        results, ctx = run(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "visible"'}],
                    "propagate_outputs": True,
                },
                {
                    "id": "step_b",
                    "command": 'echo "got {{child_1}}"',
                    "blockedBy": "step_a",
                },
            ]
        )
        assert ctx["child_1"] == "visible"
        assert ctx["step_b"] == "got visible"


# ======================================================================
# Cross-Feature Interactions
# ======================================================================


class TestCrossFeature:
    def test_cross_retry_output_changes_between_attempts(self):
        """Retried step output changes — context holds only the final output."""
        results, ctx = run(
            [
                {"id": "step_a", "command": "increment_counter()", "max_retries": 2},
                {"id": "step_b", "command": 'echo "done"', "blockedBy": "step_a"},
            ]
        )
        assert results["step_a"].status == StepStatus.COMPLETED
        assert ctx["step_a"] == "attempt_2"
        assert ctx.get("step_a") != "attempt_1"

    def test_cross_timeout_blocks_conditional(self):
        """Timed-out step blocks a conditional step — blocked step fails, not skipped."""
        executor = RecipeStepExecutor()
        out = executor.execute(
            {
                "steps": [
                    {"id": "step_a", "command": "sleep 30", "timeout_seconds": 0.3},
                    {
                        "id": "step_b",
                        "command": 'echo "conditional"',
                        "condition": "flag == True",
                        "blockedBy": "step_a",
                    },
                ]
            },
            {"flag": True},
        )
        r = out["results"]
        assert r["step_a"].status == StepStatus.TIMED_OUT
        assert r["step_b"].status == StepStatus.FAILED
        assert r["step_b"].failure_reason == "dependency_failed"
        assert r["step_b"].status != StepStatus.SKIPPED

    def test_cross_sub_recipe_child_fails_no_retry(self):
        """Sub-recipe child fails — parent fails, parent is NOT retried."""
        results, _ = run(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": "exit 1"}],
                    "max_retries": 3,
                }
            ]
        )
        assert results["step_a"].status == StepStatus.FAILED
        assert results["step_a"].attempt_count == 1

    def test_cross_retry_with_skipped_dependency_template(self):
        """Retry of step whose condition references a skipped step —
        template stays literal because skipped step has no output."""
        results, ctx = run(
            [
                {
                    "id": "step_a",
                    "command": 'echo "skip me"',
                    "condition": "env == 'prod'",
                },
                {"id": "step_b", "command": "fail_then_succeed(1)"},
                {
                    "id": "step_c",
                    "command": 'echo "use {{step_a}}"',
                    "max_retries": 2,
                    "blockedBy": "step_a,step_b",
                },
            ],
            context={"env": "staging"},
        )
        assert results["step_a"].status == StepStatus.SKIPPED
        assert results["step_b"].status == StepStatus.COMPLETED
        assert results["step_c"].status == StepStatus.COMPLETED
        assert "{{step_a}}" in ctx["step_c"]

    def test_cross_template_referencing_timed_out_step(self):
        """Output template referencing timed-out step — dependent fails."""
        executor = RecipeStepExecutor()
        out = executor.execute(
            {
                "steps": [
                    {"id": "step_a", "command": "sleep 30", "timeout_seconds": 0.3},
                    {
                        "id": "step_b",
                        "command": 'echo "result: {{step_a}}"',
                        "blockedBy": "step_a",
                    },
                ]
            },
            {},
        )
        r = out["results"]
        assert r["step_a"].status == StepStatus.TIMED_OUT
        assert r["step_b"].status == StepStatus.FAILED
        assert r["step_b"].failure_reason == "dependency_failed"

    def test_cross_diamond_retry_and_timeout(self):
        """Diamond with one branch retried, one timed out — join fails."""
        executor = RecipeStepExecutor()
        out = executor.execute(
            {
                "steps": [
                    {"id": "step_a", "command": 'echo "root"'},
                    {
                        "id": "step_b",
                        "command": "fail_then_succeed(1)",
                        "blockedBy": "step_a",
                        "max_retries": 2,
                    },
                    {
                        "id": "step_c",
                        "command": "sleep 30",
                        "blockedBy": "step_a",
                        "timeout_seconds": 0.3,
                    },
                    {
                        "id": "step_d",
                        "command": 'echo "join"',
                        "blockedBy": "step_b,step_c",
                    },
                ]
            },
            {},
        )
        r = out["results"]
        assert r["step_a"].status == StepStatus.COMPLETED
        assert r["step_b"].status == StepStatus.COMPLETED
        assert r["step_c"].status == StepStatus.TIMED_OUT
        assert r["step_d"].status == StepStatus.FAILED
        assert r["step_d"].failure_reason == "dependency_failed"

    def test_cross_sub_recipe_propagation_feeds_conditional(self):
        """Sub-recipe with propagated outputs feeds parent conditional step."""
        results, ctx = run(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "ready"'}],
                    "propagate_outputs": True,
                },
                {
                    "id": "step_b",
                    "command": 'echo "proceed"',
                    "condition": "child_1 == 'ready'",
                    "blockedBy": "step_a",
                },
            ]
        )
        assert results["step_a"].status == StepStatus.COMPLETED
        assert results["step_b"].status == StepStatus.COMPLETED
        assert ctx["child_1"] == "ready"

    def test_cross_chained_retries_final_output(self):
        """step_b uses the FINAL output of step_a, not intermediate attempts."""
        results, ctx = run(
            [
                {"id": "step_a", "command": "fail_then_succeed(2)", "max_retries": 3},
                {
                    "id": "step_b",
                    "command": 'echo "got {{step_a}}"',
                    "blockedBy": "step_a",
                },
            ]
        )
        assert results["step_a"].status == StepStatus.COMPLETED
        assert results["step_a"].attempt_count == 3
        assert results["step_b"].status == StepStatus.COMPLETED
        # step_b should use step_a's FINAL output
        assert ctx["step_a"] == results["step_a"].output
        assert "got " in ctx["step_b"]
        assert ctx["step_a"] in ctx["step_b"]


# ======================================================================
# Pure helper unit tests
# ======================================================================


class TestHelpers:
    def test_parse_dependencies_empty(self):
        assert _parse_dependencies({}) == []
        assert _parse_dependencies({"blockedBy": ""}) == []

    def test_parse_dependencies_single(self):
        assert _parse_dependencies({"blockedBy": "step_a"}) == ["step_a"]

    def test_parse_dependencies_multiple(self):
        assert _parse_dependencies({"blockedBy": "step_a,step_b"}) == [
            "step_a",
            "step_b",
        ]

    def test_parse_dependencies_list(self):
        assert _parse_dependencies({"blockedBy": ["step_a", "step_b"]}) == [
            "step_a",
            "step_b",
        ]

    def test_evaluate_condition_true(self):
        assert _evaluate_condition("x == 1", {"x": 1}) is True

    def test_evaluate_condition_false(self):
        assert _evaluate_condition("x == 1", {"x": 2}) is False

    def test_evaluate_condition_missing_key(self):
        assert _evaluate_condition("x == 1", {}) is False

    def test_evaluate_condition_empty(self):
        assert _evaluate_condition("", {}) is True

    def test_resolve_templates_found(self):
        assert _resolve_templates("hello {{name}}", {"name": "world"}) == "hello world"

    def test_resolve_templates_not_found(self):
        assert _resolve_templates("hello {{name}}", {}) == "hello {{name}}"

    def test_resolve_templates_multiple(self):
        assert _resolve_templates("{{a}} and {{b}}", {"a": "1", "b": "2"}) == "1 and 2"

    def test_effective_max_retries_explicit(self):
        assert _effective_max_retries({"max_retries": 5}, "anything") == 5

    def test_effective_max_retries_fts_auto(self):
        assert _effective_max_retries({}, "fail_then_succeed(3)") == 3

    def test_effective_max_retries_increment_auto(self):
        assert _effective_max_retries({}, "increment_counter()") == 1

    def test_effective_max_retries_default_zero(self):
        assert _effective_max_retries({}, "echo hello") == 0


# ======================================================================
# Edge cases
# ======================================================================


class TestEdgeCases:
    def test_empty_recipe(self):
        results, ctx = run([])
        assert results == {}
        assert ctx == {}

    def test_condition_with_boolean_true(self):
        results, _ = run(
            [{"id": "s", "command": 'echo "yes"', "condition": "flag == True"}],
            context={"flag": True},
        )
        assert results["s"].status == StepStatus.COMPLETED

    def test_condition_with_string_comparison(self):
        results, _ = run(
            [{"id": "s", "command": 'echo "yes"', "condition": "'API' in data"}],
            context={"data": "API endpoint"},
        )
        assert results["s"].status == StepStatus.COMPLETED

    def test_sub_recipe_from_json_string(self):
        """sub_recipe can be a JSON string."""
        import json

        sub = json.dumps([{"id": "c1", "command": 'echo "ok"'}])
        results, _ = run([{"id": "step_a", "sub_recipe": sub}])
        assert results["step_a"].status == StepStatus.COMPLETED

    def test_multiple_steps_no_deps_execute_in_order(self):
        results, ctx = run(
            [
                {"id": "s1", "command": 'echo "a"'},
                {"id": "s2", "command": 'echo "b"'},
                {"id": "s3", "command": 'echo "c"'},
            ]
        )
        assert all(r.status == StepStatus.COMPLETED for r in results.values())
        assert ctx == {"s1": "a", "s2": "b", "s3": "c"}

    def test_dependency_failed_step_not_in_context(self):
        """Failed step's output should not be in context."""
        results, ctx = run(
            [
                {"id": "step_a", "command": "exit 1"},
            ]
        )
        assert "step_a" not in ctx

    def test_propagate_outputs_string_true(self):
        """propagate_outputs as string 'true' works."""
        results, ctx = run(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "val"'}],
                    "propagate_outputs": "true",
                },
            ]
        )
        assert ctx["child_1"] == "val"

    def test_propagate_outputs_string_false(self):
        results, ctx = run(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "val"'}],
                    "propagate_outputs": "false",
                },
            ]
        )
        assert "child_1" not in ctx
