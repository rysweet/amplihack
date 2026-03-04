"""Tests for the RECIPE step type (issue #2821).

Verifies:
- StepType.RECIPE is a valid enum member
- Step dataclass accepts recipe and sub_context fields
- Parser parses ``type: recipe`` YAML steps correctly
- Runner executes sub-recipes with merged context
- Recursion depth guard raises StepExecutionError at depth >= MAX_RECIPE_DEPTH
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from amplihack.recipes.models import Step, StepStatus, StepType
from amplihack.recipes.parser import RecipeParser
from amplihack.recipes.runner import MAX_RECIPE_DEPTH, RecipeRunner


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestStepTypeRecipeEnum:
    """StepType.RECIPE must exist and have the correct value."""

    def test_recipe_enum_member_exists(self) -> None:
        assert hasattr(StepType, "RECIPE")

    def test_recipe_enum_value(self) -> None:
        assert StepType.RECIPE.value == "recipe"

    def test_recipe_round_trip(self) -> None:
        assert StepType("recipe") == StepType.RECIPE


class TestStepDataclassRecipeFields:
    """Step dataclass must have recipe and sub_context fields."""

    def test_recipe_field_default_none(self) -> None:
        step = Step(id="s", step_type=StepType.RECIPE)
        assert step.recipe is None

    def test_sub_context_field_default_none(self) -> None:
        step = Step(id="s", step_type=StepType.RECIPE)
        assert step.sub_context is None

    def test_recipe_and_sub_context_can_be_set(self) -> None:
        step = Step(
            id="s",
            step_type=StepType.RECIPE,
            recipe="quality-audit",
            sub_context={"target": "src/"},
        )
        assert step.recipe == "quality-audit"
        assert step.sub_context == {"target": "src/"}


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


RECIPE_STEP_YAML = """\
name: parent-recipe
steps:
  - id: call-sub
    type: recipe
    recipe: quality-audit-cycle
    context:
      target_path: src/amplihack
    output: quality_audit_results
"""

RECIPE_STEP_INFER_YAML = """\
name: parent-infer
steps:
  - id: call-sub
    recipe: quality-audit-cycle
    output: audit_out
"""


class TestParserRecipeStep:
    """Parser must produce Step with StepType.RECIPE from YAML."""

    def test_explicit_type_recipe_parsed(self) -> None:
        recipe = RecipeParser().parse(RECIPE_STEP_YAML)
        step = recipe.steps[0]
        assert step.step_type == StepType.RECIPE
        assert step.recipe == "quality-audit-cycle"
        assert step.sub_context == {"target_path": "src/amplihack"}
        assert step.output == "quality_audit_results"

    def test_inferred_type_recipe_when_recipe_field_present(self) -> None:
        recipe = RecipeParser().parse(RECIPE_STEP_INFER_YAML)
        step = recipe.steps[0]
        assert step.step_type == StepType.RECIPE
        assert step.recipe == "quality-audit-cycle"

    def test_missing_recipe_field_produces_validation_warning(self) -> None:
        yaml_content = """\
name: bad-recipe
steps:
  - id: no-name
    type: recipe
"""
        recipe = RecipeParser().parse(yaml_content)
        warnings = RecipeParser().validate(recipe)
        assert any("missing a 'recipe' field" in w for w in warnings)

    def test_recipe_and_context_in_known_step_fields(self) -> None:
        """recipe and context must not produce 'unrecognized field' warnings."""
        recipe = RecipeParser().parse(RECIPE_STEP_YAML)
        warnings = RecipeParser().validate(recipe, raw_yaml=RECIPE_STEP_YAML)
        unrecognized = [w for w in warnings if "unrecognized field" in w]
        assert not unrecognized, f"Unexpected unrecognized field warnings: {unrecognized}"


# ---------------------------------------------------------------------------
# Runner tests
# ---------------------------------------------------------------------------


def _make_sub_recipe_yaml(name: str = "sub-recipe") -> str:
    return f"""\
name: {name}
steps:
  - id: inner-step
    type: bash
    command: echo inner
    output: inner_out
"""


class TestRunnerRecipeStep:
    """Runner must execute sub-recipes and merge context."""

    def _make_parent_recipe(self, sub_recipe_name: str = "sub-recipe") -> str:
        return f"""\
name: parent-recipe
context:
  parent_var: "parent_value"
steps:
  - id: call-sub
    type: recipe
    recipe: {sub_recipe_name}
    context:
      extra_var: "extra_value"
    output: sub_result
"""

    def test_happy_path_executes_sub_recipe(self, mock_adapter: MagicMock, tmp_path: Path) -> None:
        """Happy path: sub-recipe executes and result is stored in context."""
        sub_yaml = _make_sub_recipe_yaml("sub-recipe")
        sub_path = tmp_path / "sub-recipe.yaml"
        sub_path.write_text(sub_yaml)

        parent_yaml = self._make_parent_recipe("sub-recipe")
        parent_recipe = RecipeParser().parse(parent_yaml)

        mock_adapter.execute_bash_step.return_value = "inner output"

        with patch(
            "amplihack.recipes.runner.find_recipe", return_value=sub_path
        ):
            runner = RecipeRunner(adapter=mock_adapter)
            result = runner.execute(parent_recipe)

        assert result.success
        # The sub-recipe bash step should have executed
        mock_adapter.execute_bash_step.assert_called_once()
        # Output stored under "sub_result" key
        assert "sub_result" in result.context

    def test_context_merging(self, mock_adapter: MagicMock, tmp_path: Path) -> None:
        """Sub-recipe receives merged context: parent context + step-level context."""
        captured_contexts: list[dict[str, Any]] = []

        # Sub-recipe has a bash step that we intercept
        sub_yaml = _make_sub_recipe_yaml("merge-test")
        sub_path = tmp_path / "merge-test.yaml"
        sub_path.write_text(sub_yaml)

        parent_yaml = """\
name: parent
context:
  parent_var: from_parent
steps:
  - id: call-sub
    type: recipe
    recipe: merge-test
    context:
      step_var: from_step
    output: out
"""
        parent_recipe = RecipeParser().parse(parent_yaml)
        mock_adapter.execute_bash_step.return_value = "done"

        def _capture_and_run(command: str, working_dir: str = ".", **kwargs: Any) -> str:
            return "captured"

        mock_adapter.execute_bash_step.side_effect = _capture_and_run

        with patch(
            "amplihack.recipes.runner.find_recipe", return_value=sub_path
        ) as mock_find:
            # Capture the sub_runner context by inspecting RecipeRunner.execute calls
            original_execute = RecipeRunner.execute

            def patched_execute(
                self: RecipeRunner,
                recipe: Any,
                user_context: dict[str, Any] | None = None,
                dry_run: bool | None = None,
            ) -> Any:
                if user_context:
                    captured_contexts.append(dict(user_context))
                return original_execute(self, recipe, user_context=user_context, dry_run=dry_run)

            with patch.object(RecipeRunner, "execute", patched_execute):
                runner = RecipeRunner(adapter=mock_adapter)
                runner.execute(parent_recipe)

        # The sub-recipe's execute should have received both parent and step context
        assert any("parent_var" in c and "step_var" in c for c in captured_contexts)

    def test_sub_recipe_failure_propagates(self, mock_adapter: MagicMock, tmp_path: Path) -> None:
        """If sub-recipe fails, the parent step is marked FAILED."""
        sub_yaml = """\
name: failing-sub
steps:
  - id: fail-step
    type: bash
    command: exit 1
    output: out
"""
        sub_path = tmp_path / "failing-sub.yaml"
        sub_path.write_text(sub_yaml)

        parent_yaml = """\
name: parent
steps:
  - id: call-sub
    type: recipe
    recipe: failing-sub
    output: out
"""
        parent_recipe = RecipeParser().parse(parent_yaml)
        mock_adapter.execute_bash_step.side_effect = RuntimeError("command failed")

        with patch("amplihack.recipes.runner.find_recipe", return_value=sub_path):
            runner = RecipeRunner(adapter=mock_adapter)
            result = runner.execute(parent_recipe)

        assert not result.success
        assert result.step_results[0].status == StepStatus.FAILED

    def test_missing_recipe_field_fails(self, mock_adapter: MagicMock) -> None:
        """A recipe step missing the 'recipe' field must fail the step."""
        from amplihack.recipes.models import Recipe

        step = Step(id="no-name", step_type=StepType.RECIPE, recipe=None)
        recipe = Recipe(name="test", steps=[step])

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert not result.success
        assert result.step_results[0].status == StepStatus.FAILED

    def test_recipe_not_found_fails(self, mock_adapter: MagicMock) -> None:
        """A recipe step pointing to a non-existent recipe must fail the step."""
        from amplihack.recipes.models import Recipe

        step = Step(id="ghost", step_type=StepType.RECIPE, recipe="does-not-exist")
        recipe = Recipe(name="test", steps=[step])

        with patch("amplihack.recipes.runner.find_recipe", return_value=None):
            runner = RecipeRunner(adapter=mock_adapter)
            result = runner.execute(recipe)

        assert not result.success
        assert result.step_results[0].status == StepStatus.FAILED


class TestRecursionDepthGuard:
    """Runner must enforce max recursion depth of MAX_RECIPE_DEPTH."""

    def test_max_depth_constant_is_3(self) -> None:
        assert MAX_RECIPE_DEPTH == 3

    def test_recursion_blocked_at_max_depth(self, mock_adapter: MagicMock, tmp_path: Path) -> None:
        """A runner at depth == MAX_RECIPE_DEPTH must not execute sub-recipes."""
        from amplihack.recipes.models import Recipe

        step = Step(id="recurse", step_type=StepType.RECIPE, recipe="self-ref")
        recipe = Recipe(name="self-ref", steps=[step])

        with patch("amplihack.recipes.runner.find_recipe", return_value=tmp_path / "x.yaml"):
            runner = RecipeRunner(adapter=mock_adapter, _depth=MAX_RECIPE_DEPTH)
            result = runner.execute(recipe)

        assert not result.success
        assert result.step_results[0].status == StepStatus.FAILED
        assert "depth" in result.step_results[0].error.lower()

    def test_depth_increments_on_each_level(
        self, mock_adapter: MagicMock, tmp_path: Path
    ) -> None:
        """Sub-runner depth must be parent depth + 1."""
        depths_seen: list[int] = []

        original_init = RecipeRunner.__init__

        def patched_init(self: RecipeRunner, *args: Any, **kwargs: Any) -> None:
            original_init(self, *args, **kwargs)
            depths_seen.append(self._depth)

        sub_yaml = _make_sub_recipe_yaml("depth-test")
        sub_path = tmp_path / "depth-test.yaml"
        sub_path.write_text(sub_yaml)

        parent_yaml = """\
name: parent
steps:
  - id: call-sub
    type: recipe
    recipe: depth-test
    output: out
"""
        parent_recipe = RecipeParser().parse(parent_yaml)
        mock_adapter.execute_bash_step.return_value = "ok"

        with patch("amplihack.recipes.runner.find_recipe", return_value=sub_path):
            with patch.object(RecipeRunner, "__init__", patched_init):
                runner = RecipeRunner(adapter=mock_adapter, _depth=0)
                runner.execute(parent_recipe)

        # depth 0 (parent) and depth 1 (sub-runner) should both appear
        assert 0 in depths_seen
        assert 1 in depths_seen

    def test_dry_run_recipe_step_completes(self, mock_adapter: MagicMock) -> None:
        """Dry-run mode must complete recipe steps without executing sub-recipes."""
        from amplihack.recipes.models import Recipe

        step = Step(id="dry-sub", step_type=StepType.RECIPE, recipe="anything")
        recipe = Recipe(name="test", steps=[step])

        runner = RecipeRunner(adapter=mock_adapter, dry_run=True)
        result = runner.execute(recipe, dry_run=True)

        assert result.success
        assert result.step_results[0].status == StepStatus.COMPLETED
        # Sub-recipe should NOT have been invoked in dry-run mode
        mock_adapter.execute_bash_step.assert_not_called()
        mock_adapter.execute_agent_step.assert_not_called()
