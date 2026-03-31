"""Tests for RecipeStepExecutor — one test per Gherkin scenario plus
cross-feature interaction tests."""

import time
from unittest.mock import MagicMock

from recipe_step_executor import RecipeStepExecutor

# ======================================================================
# Feature 1: Conditional Step Execution
# ======================================================================


class TestConditionalStepExecution:
    def test_unconditional_step_always_executes(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {"steps": [{"id": "step_a", "command": 'echo "hello"'}]}

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "completed"
        assert context["step_a"] == "hello"

    def test_conditional_step_executes_when_condition_true(self):
        executor = RecipeStepExecutor()
        context = {"env": "prod"}
        recipe = {
            "steps": [
                {
                    "id": "step_a",
                    "command": 'echo "deploying"',
                    "condition": "env == 'prod'",
                }
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "completed"

    def test_conditional_step_skipped_when_condition_false(self):
        executor = RecipeStepExecutor()
        context = {"env": "staging"}
        recipe = {
            "steps": [
                {
                    "id": "step_a",
                    "command": 'echo "deploying"',
                    "condition": "env == 'prod'",
                }
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "skipped"
        assert "step_a" not in context

    def test_condition_referencing_missing_key_evaluates_false(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {
                    "id": "step_a",
                    "command": 'echo "go"',
                    "condition": "feature_flag == True",
                }
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "skipped"


# ======================================================================
# Feature 2: Step Dependencies
# ======================================================================


class TestStepDependencies:
    def test_step_waits_for_dependency_to_complete(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {"id": "step_a", "command": 'echo "first"'},
                {"id": "step_b", "command": 'echo "second"', "blockedBy": "step_a"},
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_b"].status == "completed"
        assert executor.execution_order.index("step_a") < executor.execution_order.index("step_b")

    def test_step_blocked_by_failed_dependency_is_failed(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {"id": "step_a", "command": "exit 1"},
                {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "failed"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"

    def test_step_blocked_by_skipped_dependency_executes(self):
        executor = RecipeStepExecutor()
        context = {"env": "staging"}
        recipe = {
            "steps": [
                {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
                {"id": "step_b", "command": 'echo "runs"', "blockedBy": "step_a"},
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "skipped"
        assert results["step_b"].status == "completed"

    def test_diamond_dependency_graph_order(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {"id": "step_a", "command": 'echo "root"'},
                {"id": "step_b", "command": 'echo "left"', "blockedBy": "step_a"},
                {"id": "step_c", "command": 'echo "right"', "blockedBy": "step_a"},
                {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
            ]
        }

        results = executor.execute(recipe, context)

        order = executor.execution_order
        assert order.index("step_a") < order.index("step_b")
        assert order.index("step_a") < order.index("step_c")
        assert order.index("step_b") < order.index("step_d")
        assert order.index("step_c") < order.index("step_d")
        assert results["step_d"].status == "completed"


# ======================================================================
# Feature 3: Retry with Exponential Backoff
# ======================================================================


class TestRetryWithExponentialBackoff:
    def test_no_retries_fails_immediately(self):
        executor = RecipeStepExecutor(sleep_func=lambda _: None)
        context: dict = {}
        recipe = {"steps": [{"id": "step_a", "command": "exit 1", "max_retries": 0}]}

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "failed"
        assert results["step_a"].attempt_count == 1

    def test_succeeds_on_second_attempt(self):
        mock_sleep = MagicMock()
        executor = RecipeStepExecutor(sleep_func=mock_sleep)
        context: dict = {}
        recipe = {"steps": [{"id": "step_a", "command": "fail_then_succeed(1)", "max_retries": 3}]}

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "completed"
        assert results["step_a"].attempt_count == 2

    def test_exhausts_all_retries_and_fails(self):
        mock_sleep = MagicMock()
        executor = RecipeStepExecutor(sleep_func=mock_sleep)
        context: dict = {}
        recipe = {"steps": [{"id": "step_a", "command": "exit 1", "max_retries": 3}]}

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "failed"
        assert results["step_a"].attempt_count == 4
        assert results["step_a"].retry_delays == [1, 2, 4]


# ======================================================================
# Feature 4: Timeout Handling
# ======================================================================


class TestTimeoutHandling:
    def test_step_exceeding_timeout_is_timed_out(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {"steps": [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2}]}

        start = time.monotonic()
        results = executor.execute(recipe, context)
        elapsed = time.monotonic() - start

        assert results["step_a"].status == "timed_out"
        assert 1.5 <= elapsed <= 4.0, f"Expected ~2s, got {elapsed:.2f}s"

    def test_timed_out_step_not_retried(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {
                    "id": "step_a",
                    "command": "sleep 30",
                    "timeout_seconds": 2,
                    "max_retries": 3,
                }
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "timed_out"
        assert results["step_a"].attempt_count == 1

    def test_timed_out_step_is_failure_for_dependencies(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
                {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "timed_out"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"


# ======================================================================
# Feature 5: Output Capture
# ======================================================================


class TestOutputCapture:
    def test_output_stored_in_context(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {"steps": [{"id": "step_a", "command": 'echo "result_value"'}]}

        executor.execute(recipe, context)

        assert context["step_a"] == "result_value"

    def test_template_references_prior_output(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {"id": "step_a", "command": 'echo "data_123"'},
                {
                    "id": "step_b",
                    "command": 'echo "processing {{step_a}}"',
                    "blockedBy": "step_a",
                },
            ]
        }

        executor.execute(recipe, context)

        assert context["step_b"] == "processing data_123"


# ======================================================================
# Feature 6: Sub-recipe Delegation
# ======================================================================


class TestSubRecipeDelegation:
    def test_sub_recipe_inherits_parent_context(self):
        executor = RecipeStepExecutor()
        context = {"parent_val": "shared"}
        recipe = {
            "steps": [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "{{parent_val}}"'}],
                }
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "completed"
        # child_1 resolved {{parent_val}} -> "shared"
        child_ctx = results["step_a"]._child_context
        assert child_ctx is not None
        assert child_ctx["child_1"] == "shared"

    def test_sub_recipe_outputs_not_propagated_by_default(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "secret"'}],
                    "propagate_outputs": False,
                },
                {"id": "step_b", "command": 'echo "{{child_1}}"'},
            ]
        }

        executor.execute(recipe, context)

        assert "child_1" not in context
        # Template not resolved — left as literal.
        assert context["step_b"] == "{{child_1}}"

    def test_sub_recipe_outputs_propagated_when_true(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
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
        }

        executor.execute(recipe, context)

        assert context["child_1"] == "visible"
        assert context["step_b"] == "got visible"


# ======================================================================
# Cross-Feature Interactions
# ======================================================================


class TestCrossFeatureInteractions:
    def test_retried_step_output_uses_final_attempt_only(self):
        """Retried step output changes between attempts — context holds
        only the final successful output."""
        mock_sleep = MagicMock()
        executor = RecipeStepExecutor(sleep_func=mock_sleep)
        context: dict = {}
        recipe = {
            "steps": [
                {"id": "step_a", "command": "increment_counter()", "max_retries": 2},
                {"id": "step_b", "command": 'echo "done"', "blockedBy": "step_a"},
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "completed"
        assert context["step_a"] == "attempt_2"
        assert context.get("step_a") != "attempt_1"
        assert results["step_b"].status == "completed"

    def test_timed_out_step_blocks_conditional_step_as_failed(self):
        """Timed-out dependency causes dependent step to fail (not skip),
        even if the dependent step's condition is true."""
        executor = RecipeStepExecutor()
        context = {"flag": True}
        recipe = {
            "steps": [
                {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
                {
                    "id": "step_b",
                    "command": 'echo "conditional"',
                    "condition": "flag == True",
                    "blockedBy": "step_a",
                },
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "timed_out"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"
        assert results["step_b"].status != "skipped"

    def test_sub_recipe_child_failure_not_retried(self):
        """Sub-recipe child failure makes parent fail immediately —
        parent is NOT retried even with max_retries set."""
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": "exit 1"}],
                    "max_retries": 3,
                }
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "failed"
        assert results["step_a"].attempt_count == 1

    def test_retry_step_with_skipped_dep_keeps_template_literal(self):
        """step_c references skipped step_a via template — template stays
        literal because skipped steps produce no output."""
        mock_sleep = MagicMock()
        executor = RecipeStepExecutor(sleep_func=mock_sleep)
        context = {"env": "staging"}
        recipe = {
            "steps": [
                {
                    "id": "step_a",
                    "command": 'echo "skip me"',
                    "condition": "env == 'prod'",
                },
                {"id": "step_b", "command": "fail_then_succeed(1)", "max_retries": 2},
                {
                    "id": "step_c",
                    "command": 'echo "use {{step_a}}"',
                    "max_retries": 2,
                    "blockedBy": "step_a,step_b",
                },
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "skipped"
        assert results["step_b"].status == "completed"
        assert results["step_c"].status == "completed"
        assert context["step_c"] == "use {{step_a}}"

    def test_template_referencing_timed_out_step_causes_dep_failure(self):
        """Output template referencing timed-out step — dependent step
        fails with dependency_failed."""
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {"id": "step_a", "command": "sleep 30", "timeout_seconds": 1},
                {
                    "id": "step_b",
                    "command": 'echo "result: {{step_a}}"',
                    "blockedBy": "step_a",
                },
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "timed_out"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"

    def test_diamond_with_retry_branch_and_timeout_branch(self):
        """Diamond graph: left branch retries and succeeds, right branch
        times out — join step fails."""
        mock_sleep = MagicMock()
        executor = RecipeStepExecutor(sleep_func=mock_sleep)
        context: dict = {}
        recipe = {
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
                    "timeout_seconds": 1,
                },
                {
                    "id": "step_d",
                    "command": 'echo "join"',
                    "blockedBy": "step_b,step_c",
                },
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "completed"
        assert results["step_b"].status == "completed"
        assert results["step_c"].status == "timed_out"
        assert results["step_d"].status == "failed"
        assert results["step_d"].failure_reason == "dependency_failed"

    def test_sub_recipe_propagated_outputs_feed_conditional(self):
        """Sub-recipe propagates child_1='ready' to parent context;
        step_b's condition child_1 == 'ready' evaluates true."""
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
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
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "completed"
        assert results["step_b"].status == "completed"
        assert context["child_1"] == "ready"

    def test_chained_retries_use_final_output(self):
        """step_a retries 3 times; step_b uses the FINAL output of
        step_a, not intermediate failed attempts."""
        mock_sleep = MagicMock()
        executor = RecipeStepExecutor(sleep_func=mock_sleep)
        context: dict = {}
        recipe = {
            "steps": [
                {
                    "id": "step_a",
                    "command": "fail_then_succeed(2)",
                    "max_retries": 3,
                },
                {
                    "id": "step_b",
                    "command": 'echo "got {{step_a}}"',
                    "blockedBy": "step_a",
                },
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "completed"
        assert results["step_a"].attempt_count == 3
        assert results["step_b"].status == "completed"
        assert context["step_b"] == "got attempt_3"


# ======================================================================
# Edge cases & additional coverage
# ======================================================================


class TestEdgeCases:
    def test_empty_recipe_returns_no_results(self):
        executor = RecipeStepExecutor()
        results = executor.execute({"steps": []}, {})
        assert results == {}

    def test_sub_recipe_from_json_string(self):
        """sub_recipe can be passed as a JSON string."""
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {
                    "id": "step_a",
                    "sub_recipe": '[{"id": "child_1", "command": "echo \\"hi\\""}]',
                    "propagate_outputs": True,
                }
            ]
        }

        results = executor.execute(recipe, context)

        assert results["step_a"].status == "completed"
        assert context["child_1"] == "hi"

    def test_multiple_templates_in_one_command(self):
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {"id": "step_a", "command": 'echo "foo"'},
                {"id": "step_b", "command": 'echo "bar"'},
                {
                    "id": "step_c",
                    "command": 'echo "{{step_a}}-{{step_b}}"',
                    "blockedBy": "step_a,step_b",
                },
            ]
        }

        executor.execute(recipe, context)

        assert context["step_c"] == "foo-bar"

    def test_condition_with_boolean_context_value(self):
        executor = RecipeStepExecutor()
        context = {"feature_flag": True}
        recipe = {
            "steps": [
                {
                    "id": "step_a",
                    "command": 'echo "enabled"',
                    "condition": "feature_flag == True",
                }
            ]
        }

        results = executor.execute(recipe, context)
        assert results["step_a"].status == "completed"

    def test_retry_delays_passed_to_sleep_func(self):
        """Verify the sleep function is called with correct backoff values."""
        sleep_calls: list[int] = []
        executor = RecipeStepExecutor(sleep_func=lambda d: sleep_calls.append(d))
        context: dict = {}
        recipe = {"steps": [{"id": "step_a", "command": "exit 1", "max_retries": 3}]}

        executor.execute(recipe, context)

        assert sleep_calls == [1, 2, 4]

    def test_propagate_outputs_string_true(self):
        """propagate_outputs accepts string 'true'."""
        executor = RecipeStepExecutor()
        context: dict = {}
        recipe = {
            "steps": [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "val"'}],
                    "propagate_outputs": "true",
                }
            ]
        }

        executor.execute(recipe, context)

        assert context["child_1"] == "val"

    def test_execution_order_tracks_all_steps(self):
        executor = RecipeStepExecutor()
        context = {"env": "staging"}
        recipe = {
            "steps": [
                {"id": "step_a", "command": 'echo "a"', "condition": "env == 'prod'"},
                {"id": "step_b", "command": 'echo "b"'},
            ]
        }

        executor.execute(recipe, context)

        assert "step_a" in executor.execution_order
        assert "step_b" in executor.execution_order
