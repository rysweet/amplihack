from __future__ import annotations

from unittest.mock import patch

from amplihack.recipe_cli.recipe_command import handle_run, parse_context_args
from amplihack.recipes.models import Recipe, RecipeResult


def _make_recipe(*, context: dict[str, str] | None = None) -> Recipe:
    return Recipe(
        name="quality-audit-cycle",
        description="test recipe",
        steps=[],
        context=context or {},
    )


def _make_result() -> RecipeResult:
    return RecipeResult(
        recipe_name="quality-audit-cycle", success=True, step_results=[], context={}
    )


class TestParseContextArgs:
    def test_single_flag_with_multiple_key_value_pairs(self):
        context, errors = parse_context_args(
            [
                [
                    "target_path=src/amplihack/recipe_cli/recipe_command.py",
                    "min_cycles=3",
                    "max_cycles=3",
                    "validation_threshold=2",
                ]
            ]
        )

        assert errors == []
        assert context == {
            "target_path": "src/amplihack/recipe_cli/recipe_command.py",
            "min_cycles": "3",
            "max_cycles": "3",
            "validation_threshold": "2",
        }

    def test_preserves_spaces_inside_single_value(self):
        context, errors = parse_context_args([["task=Fix", "bug", "(#2453)"]])

        assert errors == []
        assert context == {"task": "Fix bug (#2453)"}


class TestHandleRun:
    @patch("amplihack.recipe_cli.recipe_command.format_recipe_result", return_value="ok")
    @patch("amplihack.recipe_cli.recipe_command.run_recipe_via_rust")
    @patch("amplihack.recipe_cli.recipe_command.RecipeParser")
    def test_verbose_run_forwards_progress(self, mock_parser_cls, mock_run_recipe, _mock_format):
        mock_parser = mock_parser_cls.return_value
        mock_parser.parse_file.return_value = _make_recipe(context={"max_cycles": "6"})
        mock_run_recipe.return_value = _make_result()

        exit_code = handle_run(
            "amplifier-bundle/recipes/quality-audit-cycle.yaml",
            context={"max_cycles": "3"},
            verbose=True,
        )

        assert exit_code == 0
        assert mock_run_recipe.call_args.kwargs["progress"] is True
        assert mock_run_recipe.call_args.kwargs["user_context"]["max_cycles"] == "3"
