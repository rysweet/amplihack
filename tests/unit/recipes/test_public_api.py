"""Tests for public API convenience functions.

Verifies that the three main public API functions work correctly:
1. parse_recipe() - wrapper for RecipeParser().parse()
2. run_recipe() - parse and execute shortcut
3. run_recipe_by_name() - find, parse, and execute with FileNotFoundError handling
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from amplihack.recipes import parse_recipe, run_recipe, run_recipe_by_name
from amplihack.recipes.models import Recipe, RecipeResult, StepStatus, StepType


class TestParseRecipe:
    """Test parse_recipe() convenience function."""

    def test_parse_recipe_returns_recipe_object(self, simple_recipe_yaml: str) -> None:
        """parse_recipe() returns a fully populated Recipe object."""
        recipe = parse_recipe(simple_recipe_yaml)

        assert isinstance(recipe, Recipe)
        assert recipe.name == "simple-test-recipe"
        assert len(recipe.steps) == 2

    def test_parse_recipe_validates_yaml_structure(self) -> None:
        """parse_recipe() raises ValueError for non-dict YAML structure."""
        invalid_yaml = "- just\n- a\n- list"
        with pytest.raises(ValueError, match="must be a mapping at the top level"):
            parse_recipe(invalid_yaml)

    def test_parse_recipe_missing_name_field(self) -> None:
        """parse_recipe() raises ValueError when 'name' field is missing."""
        yaml_str = """\
description: "Missing name"
steps:
  - id: "step-1"
    command: "echo test"
"""
        with pytest.raises(ValueError, match="must have a 'name' field"):
            parse_recipe(yaml_str)

    def test_parse_recipe_missing_steps_field(self) -> None:
        """parse_recipe() raises ValueError when 'steps' field is missing."""
        yaml_str = """\
name: "no-steps-recipe"
description: "Missing steps"
"""
        with pytest.raises(ValueError, match="must have a 'steps' field"):
            parse_recipe(yaml_str)

    def test_parse_recipe_preserves_metadata(self, simple_recipe_yaml: str) -> None:
        """parse_recipe() preserves description, version, and context fields."""
        recipe = parse_recipe(simple_recipe_yaml)

        assert recipe.description == "A minimal recipe for testing"
        assert recipe.version == "1.0.0"
        assert recipe.context == {"greeting": "hello"}

    def test_parse_recipe_step_ids_and_types(self, simple_recipe_yaml: str) -> None:
        """parse_recipe() correctly parses step IDs and types."""
        recipe = parse_recipe(simple_recipe_yaml)

        assert recipe.steps[0].id == "step-01-echo"
        assert recipe.steps[0].step_type == StepType.BASH
        assert recipe.steps[1].id == "step-02-agent"
        assert recipe.steps[1].step_type == StepType.AGENT

    def test_parse_recipe_duplicate_step_ids(self) -> None:
        """parse_recipe() raises ValueError for duplicate step IDs."""
        yaml_str = """\
name: "duplicate-ids"
steps:
  - id: "step-1"
    command: "echo first"
  - id: "step-1"
    command: "echo second"
"""
        with pytest.raises(ValueError, match="Duplicate step id"):
            parse_recipe(yaml_str)

    def test_parse_recipe_empty_step_id(self) -> None:
        """parse_recipe() raises ValueError for empty step ID."""
        yaml_str = """\
name: "empty-id"
steps:
  - id: ""
    command: "echo test"
"""
        with pytest.raises(ValueError, match="must have a non-empty 'id' field"):
            parse_recipe(yaml_str)


class TestRunRecipe:
    """Test run_recipe() convenience function."""

    def test_run_recipe_parses_and_executes(
        self, simple_recipe_yaml: str, mock_adapter: MagicMock
    ) -> None:
        """run_recipe() parses YAML and executes all steps."""
        result = run_recipe(simple_recipe_yaml, adapter=mock_adapter)

        assert isinstance(result, RecipeResult)
        assert result.recipe_name == "simple-test-recipe"
        assert result.success is True
        assert len(result.step_results) == 2

    def test_run_recipe_passes_user_context(self, mock_adapter: MagicMock) -> None:
        """run_recipe() merges user_context into recipe context."""
        yaml_str = """\
name: "context-test"
context:
  base_value: "default"
steps:
  - id: "step-1"
    command: "echo {{base_value}} {{user_value}}"
    output: "result"
"""
        mock_adapter.execute_bash_step.return_value = "default custom"

        result = run_recipe(yaml_str, adapter=mock_adapter, user_context={"user_value": "custom"})

        assert result.success is True
        assert "result" in result.context
        assert result.context["result"] == "default custom"

    def test_run_recipe_dry_run_mode(
        self, simple_recipe_yaml: str, mock_adapter: MagicMock
    ) -> None:
        """run_recipe() with dry_run=True does not execute steps."""
        result = run_recipe(simple_recipe_yaml, adapter=mock_adapter, dry_run=True)

        assert result.success is True
        assert all(r.status == StepStatus.COMPLETED for r in result.step_results)
        mock_adapter.execute_bash_step.assert_not_called()
        mock_adapter.execute_agent_step.assert_not_called()

    def test_run_recipe_fails_on_step_error(self, mock_adapter: MagicMock) -> None:
        """run_recipe() stops execution on first step failure."""
        yaml_str = """\
name: "failing-recipe"
steps:
  - id: "step-1"
    command: "echo first"
    output: "first_result"
  - id: "step-2"
    command: "echo second"
    output: "second_result"
  - id: "step-3"
    command: "echo third"
    output: "third_result"
"""
        # First step succeeds, second fails
        mock_adapter.execute_bash_step.side_effect = [
            "first success",
            Exception("step 2 failed"),
        ]

        result = run_recipe(yaml_str, adapter=mock_adapter)

        assert result.success is False
        assert len(result.step_results) == 2  # Only 2 steps executed
        assert result.step_results[0].status == StepStatus.COMPLETED
        assert result.step_results[1].status == StepStatus.FAILED
        assert "step 2 failed" in result.step_results[1].error

    def test_run_recipe_accumulates_context(self, mock_adapter: MagicMock) -> None:
        """run_recipe() accumulates step outputs in context."""
        yaml_str = """\
name: "context-accumulation"
steps:
  - id: "step-1"
    command: "echo first"
    output: "first"
  - id: "step-2"
    command: "echo second"
    output: "second"
"""
        mock_adapter.execute_bash_step.side_effect = ["first value", "second value"]

        result = run_recipe(yaml_str, adapter=mock_adapter)

        assert result.context["first"] == "first value"
        assert result.context["second"] == "second value"

    def test_run_recipe_requires_adapter_for_non_dry_run(self, simple_recipe_yaml: str) -> None:
        """run_recipe() raises ValueError if adapter is None and dry_run=False."""
        with pytest.raises(ValueError, match="adapter is required"):
            run_recipe(simple_recipe_yaml, adapter=None, dry_run=False)

    def test_run_recipe_allows_none_adapter_in_dry_run(self, simple_recipe_yaml: str) -> None:
        """run_recipe() allows adapter=None when dry_run=True."""
        result = run_recipe(simple_recipe_yaml, adapter=None, dry_run=True)

        assert result.success is True
        assert len(result.step_results) == 2

    def test_run_recipe_skips_conditional_steps(self, mock_adapter: MagicMock) -> None:
        """run_recipe() skips steps when condition evaluates to false."""
        yaml_str = """\
name: "conditional-skip"
context:
  run_optional: false
steps:
  - id: "step-1"
    command: "echo always"
    output: "always_result"
  - id: "step-2"
    command: "echo conditional"
    condition: "run_optional"
    output: "conditional_result"
  - id: "step-3"
    command: "echo final"
    output: "final_result"
"""
        mock_adapter.execute_bash_step.side_effect = ["always", "final"]

        result = run_recipe(yaml_str, adapter=mock_adapter)

        assert result.success is True
        assert len(result.step_results) == 3
        assert result.step_results[0].status == StepStatus.COMPLETED
        assert result.step_results[1].status == StepStatus.SKIPPED
        assert result.step_results[2].status == StepStatus.COMPLETED
        # Only 2 calls: step-1 and step-3
        assert mock_adapter.execute_bash_step.call_count == 2

    def test_run_recipe_invalid_yaml_raises_error(self, mock_adapter: MagicMock) -> None:
        """run_recipe() raises ValueError for invalid recipe structure."""
        invalid_yaml = "- not\n- a\n- dict"
        with pytest.raises(ValueError, match="must be a mapping"):
            run_recipe(invalid_yaml, adapter=mock_adapter)


class TestRunRecipeByName:
    """Test run_recipe_by_name() convenience function."""

    @patch("amplihack.recipes.find_recipe")
    @patch("amplihack.recipes.RecipeParser.parse_file")
    def test_run_recipe_by_name_finds_and_executes(
        self,
        mock_parse_file: MagicMock,
        mock_find_recipe: MagicMock,
        simple_recipe_yaml: str,
        mock_adapter: MagicMock,
    ) -> None:
        """run_recipe_by_name() finds recipe file, parses, and executes."""
        from pathlib import Path

        from amplihack.recipes.parser import RecipeParser

        recipe_path = Path("/fake/path/test-recipe.yaml")
        mock_find_recipe.return_value = recipe_path

        # Parse the simple recipe and return it
        parser = RecipeParser()
        recipe = parser.parse(simple_recipe_yaml)
        mock_parse_file.return_value = recipe

        result = run_recipe_by_name("test-recipe", adapter=mock_adapter)

        mock_find_recipe.assert_called_once_with("test-recipe")
        mock_parse_file.assert_called_once_with(recipe_path)
        assert result.recipe_name == "simple-test-recipe"
        assert result.success is True

    @patch("amplihack.recipes.find_recipe")
    def test_run_recipe_by_name_raises_file_not_found(
        self, mock_find_recipe: MagicMock, mock_adapter: MagicMock
    ) -> None:
        """run_recipe_by_name() raises FileNotFoundError when recipe not found."""
        mock_find_recipe.return_value = None

        with pytest.raises(FileNotFoundError, match="Recipe 'nonexistent' not found"):
            run_recipe_by_name("nonexistent", adapter=mock_adapter)

    @patch("amplihack.recipes.find_recipe")
    @patch("amplihack.recipes.RecipeParser.parse_file")
    def test_run_recipe_by_name_passes_user_context(
        self,
        mock_parse_file: MagicMock,
        mock_find_recipe: MagicMock,
        mock_adapter: MagicMock,
    ) -> None:
        """run_recipe_by_name() merges user_context into execution."""
        from pathlib import Path

        from amplihack.recipes.parser import RecipeParser

        yaml_str = """\
name: "context-recipe"
context:
  default_value: "default"
steps:
  - id: "step-1"
    command: "echo {{default_value}} {{user_value}}"
    output: "result"
"""
        recipe_path = Path("/fake/path/context-recipe.yaml")
        mock_find_recipe.return_value = recipe_path
        parser = RecipeParser()
        recipe = parser.parse(yaml_str)
        mock_parse_file.return_value = recipe

        mock_adapter.execute_bash_step.return_value = "default custom"

        result = run_recipe_by_name(
            "context-recipe", adapter=mock_adapter, user_context={"user_value": "custom"}
        )

        assert result.success is True
        assert result.context["result"] == "default custom"

    @patch("amplihack.recipes.find_recipe")
    @patch("amplihack.recipes.RecipeParser.parse_file")
    def test_run_recipe_by_name_dry_run_mode(
        self,
        mock_parse_file: MagicMock,
        mock_find_recipe: MagicMock,
        simple_recipe_yaml: str,
        mock_adapter: MagicMock,
    ) -> None:
        """run_recipe_by_name() respects dry_run parameter."""
        from pathlib import Path

        from amplihack.recipes.parser import RecipeParser

        recipe_path = Path("/fake/path/test-recipe.yaml")
        mock_find_recipe.return_value = recipe_path
        parser = RecipeParser()
        recipe = parser.parse(simple_recipe_yaml)
        mock_parse_file.return_value = recipe

        result = run_recipe_by_name("test-recipe", adapter=mock_adapter, dry_run=True)

        assert result.success is True
        mock_adapter.execute_bash_step.assert_not_called()
        mock_adapter.execute_agent_step.assert_not_called()

    @patch("amplihack.recipes.find_recipe")
    def test_run_recipe_by_name_error_message_includes_name(
        self, mock_find_recipe: MagicMock, mock_adapter: MagicMock
    ) -> None:
        """run_recipe_by_name() includes recipe name in FileNotFoundError."""
        mock_find_recipe.return_value = None

        with pytest.raises(
            FileNotFoundError, match="Recipe 'missing-recipe' not found in any search directory"
        ):
            run_recipe_by_name("missing-recipe", adapter=mock_adapter)

    @patch("amplihack.recipes.find_recipe")
    @patch("amplihack.recipes.RecipeParser.parse_file")
    def test_run_recipe_by_name_handles_parse_error(
        self,
        mock_parse_file: MagicMock,
        mock_find_recipe: MagicMock,
        mock_adapter: MagicMock,
    ) -> None:
        """run_recipe_by_name() propagates parser errors."""
        from pathlib import Path

        recipe_path = Path("/fake/path/bad-recipe.yaml")
        mock_find_recipe.return_value = recipe_path
        mock_parse_file.side_effect = ValueError("Invalid recipe format")

        with pytest.raises(ValueError, match="Invalid recipe format"):
            run_recipe_by_name("bad-recipe", adapter=mock_adapter)


class TestPublicAPIIntegration:
    """Integration tests across public API functions."""

    def test_parse_then_run_workflow(
        self, simple_recipe_yaml: str, mock_adapter: MagicMock
    ) -> None:
        """Parse a recipe then execute it manually - ensures consistency."""
        recipe = parse_recipe(simple_recipe_yaml)
        from amplihack.recipes.runner import RecipeRunner

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Should be equivalent to run_recipe()
        direct_result = run_recipe(simple_recipe_yaml, adapter=mock_adapter)

        assert result.recipe_name == direct_result.recipe_name
        assert result.success == direct_result.success
        assert len(result.step_results) == len(direct_result.step_results)

    def test_all_api_functions_share_same_parser(self, simple_recipe_yaml: str) -> None:
        """All public API functions produce the same Recipe object."""
        from pathlib import Path
        from tempfile import NamedTemporaryFile

        from amplihack.recipes.parser import RecipeParser

        # Test parse_recipe
        recipe1 = parse_recipe(simple_recipe_yaml)

        # Test RecipeParser().parse() directly
        parser = RecipeParser()
        recipe2 = parser.parse(simple_recipe_yaml)

        # Test RecipeParser().parse_file()
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(simple_recipe_yaml)
            temp_path = Path(f.name)

        try:
            recipe3 = parser.parse_file(temp_path)

            # All should be equivalent
            assert recipe1.name == recipe2.name == recipe3.name
            assert len(recipe1.steps) == len(recipe2.steps) == len(recipe3.steps)
            assert recipe1.context == recipe2.context == recipe3.context
        finally:
            temp_path.unlink()

    def test_error_handling_consistency(self, mock_adapter: MagicMock) -> None:
        """All API functions raise consistent errors for invalid input."""
        invalid_yaml = "- not\n- a\n- recipe\n- dict"

        # parse_recipe should raise
        with pytest.raises(ValueError, match="must be a mapping"):
            parse_recipe(invalid_yaml)

        # run_recipe should raise
        with pytest.raises(ValueError, match="must be a mapping"):
            run_recipe(invalid_yaml, adapter=mock_adapter)

    def test_dry_run_flag_consistency(
        self, simple_recipe_yaml: str, mock_adapter: MagicMock
    ) -> None:
        """dry_run flag works identically across run_recipe functions."""
        result1 = run_recipe(simple_recipe_yaml, adapter=mock_adapter, dry_run=True)

        # Verify no actual execution
        mock_adapter.execute_bash_step.assert_not_called()
        mock_adapter.execute_agent_step.assert_not_called()

        # run_recipe_by_name with dry_run should also not execute
        with patch("amplihack.recipes.find_recipe") as mock_find:
            from pathlib import Path
            from tempfile import NamedTemporaryFile

            from amplihack.recipes.parser import RecipeParser

            with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write(simple_recipe_yaml)
                temp_path = Path(f.name)

            try:
                mock_find.return_value = temp_path
                parser = RecipeParser()
                recipe = parser.parse(simple_recipe_yaml)

                with patch("amplihack.recipes.RecipeParser.parse_file", return_value=recipe):
                    result2 = run_recipe_by_name("test-recipe", adapter=mock_adapter, dry_run=True)

                assert result1.success == result2.success
                assert len(result1.step_results) == len(result2.step_results)
            finally:
                temp_path.unlink()
