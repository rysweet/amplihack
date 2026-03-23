from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from amplihack.recipe_cli.recipe_command import (
    handle_list,
    handle_run,
    handle_validate,
    parse_context_args,
)
from amplihack.recipes.models import Recipe, RecipeResult


def _make_recipe(
    *,
    context: dict[str, str] | None = None,
    tags: list[str] | None = None,
) -> Recipe:
    return Recipe(
        name="quality-audit-cycle",
        description="test recipe",
        steps=[],
        context=context or {},
        tags=tags or [],
    )


def _make_result() -> RecipeResult:
    return RecipeResult(
        recipe_name="quality-audit-cycle",
        success=True,
        step_results=[],
        context={},
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
    @patch("amplihack.recipe_cli.recipe_command.load_recipe_definition")
    def test_verbose_run_forwards_progress(self, mock_load_recipe, mock_run_recipe, _mock_format):
        mock_load_recipe.return_value = (
            _make_recipe(context={"max_cycles": "6"}),
            Path("/tmp/quality-audit-cycle.yaml"),
        )
        mock_run_recipe.return_value = _make_result()

        exit_code = handle_run(
            "amplifier-bundle/recipes/quality-audit-cycle.yaml",
            context={"max_cycles": "3"},
            verbose=True,
        )

        assert exit_code == 0
        assert mock_run_recipe.call_args.kwargs["progress"] is True
        assert mock_run_recipe.call_args.kwargs["user_context"]["max_cycles"] == "3"


class TestHandleList:
    @patch("amplihack.recipe_cli.recipe_command.format_recipe_list", return_value="recipes")
    @patch("amplihack.recipe_cli.recipe_command.discover_recipe_definitions")
    def test_filters_tags_before_formatting(self, mock_discover, mock_format):
        mock_discover.return_value = [
            _make_recipe(tags=["audit", "python"]),
            _make_recipe(tags=["audit"]),
        ]

        exit_code = handle_list(tags=["python"])

        assert exit_code == 0
        filtered_recipes = mock_format.call_args.args[0]
        assert len(filtered_recipes) == 1
        assert filtered_recipes[0].tags == ["audit", "python"]

    @patch(
        "amplihack.recipe_cli.recipe_command.discover_recipe_definitions",
        side_effect=FileNotFoundError("missing"),
    )
    def test_returns_error_when_recipe_dir_is_missing(self, _mock_discover, capsys):
        exit_code = handle_list(recipe_dir="/missing")

        assert exit_code == 1
        assert "Error: missing" in capsys.readouterr().err


class TestHandleValidate:
    @patch("amplihack.recipe_cli.recipe_command.format_validation_result", return_value="valid")
    @patch("amplihack.recipe_cli.recipe_command.load_recipe_definition")
    def test_formats_successful_validation(self, mock_load_recipe, mock_format):
        mock_load_recipe.return_value = (_make_recipe(), Path("/tmp/recipe.yaml"))

        exit_code = handle_validate("recipe.yaml", verbose=True)

        assert exit_code == 0
        kwargs = mock_format.call_args.kwargs
        assert kwargs["is_valid"] is True
        assert kwargs["errors"] == []
        assert kwargs["verbose"] is True

    @patch("amplihack.recipe_cli.recipe_command.format_validation_result", return_value="invalid")
    @patch(
        "amplihack.recipe_cli.recipe_command.load_recipe_definition",
        side_effect=ValueError("bad recipe"),
    )
    def test_formats_validation_errors(self, _mock_load_recipe, mock_format):
        exit_code = handle_validate("recipe.yaml")

        assert exit_code == 1
        kwargs = mock_format.call_args.kwargs
        assert kwargs["is_valid"] is False
        assert kwargs["errors"] == ["bad recipe"]
