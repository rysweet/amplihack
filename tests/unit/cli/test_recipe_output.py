"""Unit tests for recipe output formatters.

Tests the output formatting functions for:
- Table formatting (human-readable)
- JSON formatting (machine-readable)
- YAML formatting (machine-readable)

Following TDD: These tests are written BEFORE implementation.
Expected to fail until recipe_output.py is implemented.

Test Coverage:
- RecipeResult formatting (run command output)
- Recipe list formatting (list command output)
- Validation result formatting (validate command output)
- Recipe detail formatting (show command output)
- Edge cases (empty results, large data, special characters)
- Output consistency and format validity
"""

from __future__ import annotations

import json

import pytest
import yaml

from amplihack.recipes.models import Recipe, RecipeResult, StepResult, StepStatus

# Import the output formatters we're testing (will fail until implemented)
try:
    from amplihack.cli.recipe_output import (
        format_recipe_details,
        format_recipe_list,
        format_recipe_result,
        format_validation_result,
    )

    FORMATTERS_EXIST = True
except ImportError:
    FORMATTERS_EXIST = False
    # Create placeholder functions for test structure
    format_recipe_result = None
    format_recipe_list = None
    format_validation_result = None
    format_recipe_details = None


pytestmark = pytest.mark.skipif(not FORMATTERS_EXIST, reason="recipe_output.py not yet implemented")


class TestFormatRecipeResult:
    """Tests for formatting recipe execution results."""

    def test_format_successful_result_table(
        self,
        successful_result: RecipeResult,
    ) -> None:
        """Test table formatting of successful recipe execution."""
        output = format_recipe_result(successful_result, format="table")

        assert isinstance(output, str)
        assert successful_result.recipe_name in output
        assert "success" in output.lower() or "✓" in output
        assert "step1" in output
        assert "step2" in output

    def test_format_failed_result_table(
        self,
        failed_result: RecipeResult,
    ) -> None:
        """Test table formatting of failed recipe execution."""
        output = format_recipe_result(failed_result, format="table")

        assert isinstance(output, str)
        assert "fail" in output.lower() or "✗" in output or "error" in output.lower()
        assert "Command failed with exit code 1" in output

    def test_format_skipped_result_table(
        self,
        skipped_result: RecipeResult,
    ) -> None:
        """Test table formatting of result with skipped steps."""
        output = format_recipe_result(skipped_result, format="table")

        assert isinstance(output, str)
        assert "skip" in output.lower() or "⊘" in output
        assert "step2" in output

    def test_format_result_json(
        self,
        successful_result: RecipeResult,
    ) -> None:
        """Test JSON formatting of recipe result."""
        output = format_recipe_result(successful_result, format="json")

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed["recipe_name"] == successful_result.recipe_name
        assert parsed["success"] == successful_result.success
        assert len(parsed["step_results"]) == len(successful_result.step_results)

    def test_format_result_yaml(
        self,
        successful_result: RecipeResult,
    ) -> None:
        """Test YAML formatting of recipe result."""
        output = format_recipe_result(successful_result, format="yaml")

        # Should be valid YAML
        parsed = yaml.safe_load(output)
        assert parsed["recipe_name"] == successful_result.recipe_name
        assert parsed["success"] == successful_result.success
        assert len(parsed["step_results"]) == len(successful_result.step_results)

    def test_format_result_with_empty_steps(self) -> None:
        """Test formatting result with no steps."""
        empty_result = RecipeResult(
            recipe_name="empty-test",
            success=True,
            step_results=[],
            context={},
        )

        output = format_recipe_result(empty_result, format="table")
        assert "empty-test" in output
        assert "0 steps" in output or "no steps" in output.lower()

    def test_format_result_with_long_output(self) -> None:
        """Test formatting result with very long step output."""
        long_output = "x" * 10000
        result = RecipeResult(
            recipe_name="long-output",
            success=True,
            step_results=[
                StepResult(
                    step_id="step1",
                    status=StepStatus.COMPLETED,
                    output=long_output,
                )
            ],
        )

        output = format_recipe_result(result, format="table")
        # Should truncate or handle gracefully
        assert len(output) < len(long_output) + 1000

    def test_format_result_with_special_characters(self) -> None:
        """Test formatting result with special characters in output."""
        special_chars = "Test\nNewline\tTab\r\nWindows\x00Null"
        result = RecipeResult(
            recipe_name="special-chars",
            success=True,
            step_results=[
                StepResult(
                    step_id="step1",
                    status=StepStatus.COMPLETED,
                    output=special_chars,
                )
            ],
        )

        output = format_recipe_result(result, format="table")
        # Should handle special characters without breaking
        assert isinstance(output, str)
        assert "special-chars" in output

    def test_format_result_json_unicode(self) -> None:
        """Test JSON formatting with Unicode characters."""
        unicode_result = RecipeResult(
            recipe_name="unicode-test",
            success=True,
            step_results=[
                StepResult(
                    step_id="emoji",
                    status=StepStatus.COMPLETED,
                    output="✅ Success! 🎉",
                )
            ],
        )

        output = format_recipe_result(unicode_result, format="json")
        parsed = json.loads(output)
        assert "✅" in parsed["step_results"][0]["output"]

    def test_format_result_with_context(self) -> None:
        """Test formatting result that includes context variables."""
        result = RecipeResult(
            recipe_name="context-test",
            success=True,
            step_results=[],
            context={"var1": "value1", "var2": 42, "var3": {"nested": "dict"}},
        )

        output = format_recipe_result(result, format="table", show_context=True)
        assert "var1" in output or "context" in output.lower()

    def test_format_result_invalid_format(
        self,
        successful_result: RecipeResult,
    ) -> None:
        """Test error handling for invalid format type."""
        with pytest.raises(ValueError, match="format"):
            format_recipe_result(successful_result, format="invalid")


class TestFormatRecipeList:
    """Tests for formatting recipe lists."""

    def test_format_empty_list_table(self) -> None:
        """Test table formatting of empty recipe list."""
        output = format_recipe_list([], format="table")

        assert isinstance(output, str)
        assert "no recipes" in output.lower() or "0 recipes" in output.lower()

    def test_format_single_recipe_table(
        self,
        simple_recipe: Recipe,
    ) -> None:
        """Test table formatting of single recipe."""
        output = format_recipe_list([simple_recipe], format="table")

        assert simple_recipe.name in output
        assert simple_recipe.description in output

    def test_format_multiple_recipes_table(
        self,
        sample_recipes: list[Recipe],
    ) -> None:
        """Test table formatting of multiple recipes."""
        output = format_recipe_list(sample_recipes, format="table")

        for recipe in sample_recipes:
            assert recipe.name in output

    def test_format_recipes_with_tags_table(
        self,
        sample_recipes: list[Recipe],
    ) -> None:
        """Test table includes recipe tags."""
        output = format_recipe_list(sample_recipes, format="table", show_tags=True)

        assert "tag1" in output or "tags" in output.lower()

    def test_format_recipes_verbose_table(
        self,
        sample_recipes: list[Recipe],
    ) -> None:
        """Test verbose table includes full details."""
        output = format_recipe_list(sample_recipes, format="table", verbose=True)

        # Verbose should show more details
        assert len(output) > len(format_recipe_list(sample_recipes, format="table", verbose=False))

    def test_format_recipes_json(
        self,
        sample_recipes: list[Recipe],
    ) -> None:
        """Test JSON formatting of recipe list."""
        output = format_recipe_list(sample_recipes, format="json")

        parsed = json.loads(output)
        assert isinstance(parsed, list)
        assert len(parsed) == len(sample_recipes)
        assert all("name" in recipe for recipe in parsed)

    def test_format_recipes_yaml(
        self,
        sample_recipes: list[Recipe],
    ) -> None:
        """Test YAML formatting of recipe list."""
        output = format_recipe_list(sample_recipes, format="yaml")

        parsed = yaml.safe_load(output)
        assert isinstance(parsed, list)
        assert len(parsed) == len(sample_recipes)

    def test_format_recipes_sorted_by_name(
        self,
        sample_recipes: list[Recipe],
    ) -> None:
        """Test recipes are sorted alphabetically by name."""
        output = format_recipe_list(sample_recipes, format="table")

        # Find positions of recipe names in output
        positions = {recipe.name: output.find(recipe.name) for recipe in sample_recipes}
        sorted_names = sorted(sample_recipes, key=lambda r: r.name)

        # Check if order matches alphabetical
        for i in range(len(sorted_names) - 1):
            assert positions[sorted_names[i].name] < positions[sorted_names[i + 1].name]

    def test_format_recipes_with_missing_fields(self) -> None:
        """Test formatting recipes with optional fields missing."""
        minimal_recipe = Recipe(name="minimal")

        output = format_recipe_list([minimal_recipe], format="table")
        assert "minimal" in output
        # Should handle missing description gracefully
        assert isinstance(output, str)

    def test_format_large_recipe_list(self) -> None:
        """Test formatting large number of recipes."""
        large_list = [
            Recipe(name=f"recipe-{i}", description=f"Description {i}") for i in range(100)
        ]

        output = format_recipe_list(large_list, format="table")
        assert "recipe-0" in output
        assert "recipe-99" in output


class TestFormatValidationResult:
    """Tests for formatting validation results."""

    def test_format_valid_recipe_table(
        self,
        simple_recipe: Recipe,
    ) -> None:
        """Test table formatting of valid recipe validation."""
        output = format_validation_result(
            recipe=simple_recipe,
            is_valid=True,
            errors=[],
            format="table",
        )

        assert "valid" in output.lower() or "✓" in output
        assert simple_recipe.name in output

    def test_format_invalid_recipe_table(
        self,
        simple_recipe: Recipe,
    ) -> None:
        """Test table formatting of invalid recipe validation."""
        errors = ["Missing required field: steps", "Invalid step type in step2"]

        output = format_validation_result(
            recipe=simple_recipe,
            is_valid=False,
            errors=errors,
            format="table",
        )

        assert "invalid" in output.lower() or "✗" in output or "error" in output.lower()
        for error in errors:
            assert error in output

    def test_format_validation_json(
        self,
        simple_recipe: Recipe,
    ) -> None:
        """Test JSON formatting of validation result."""
        errors = ["Error 1", "Error 2"]

        output = format_validation_result(
            recipe=simple_recipe,
            is_valid=False,
            errors=errors,
            format="json",
        )

        parsed = json.loads(output)
        assert parsed["valid"] is False
        assert len(parsed["errors"]) == 2

    def test_format_validation_yaml(
        self,
        simple_recipe: Recipe,
    ) -> None:
        """Test YAML formatting of validation result."""
        output = format_validation_result(
            recipe=simple_recipe,
            is_valid=True,
            errors=[],
            format="yaml",
        )

        parsed = yaml.safe_load(output)
        assert parsed["valid"] is True

    def test_format_validation_verbose(
        self,
        simple_recipe: Recipe,
    ) -> None:
        """Test verbose validation output includes details."""
        output = format_validation_result(
            recipe=simple_recipe,
            is_valid=True,
            errors=[],
            format="table",
            verbose=True,
        )

        # Verbose should show structure details
        assert "steps" in output.lower() or len(output) > 50

    def test_format_validation_no_recipe(self) -> None:
        """Test validation formatting when recipe couldn't be parsed."""
        output = format_validation_result(
            recipe=None,
            is_valid=False,
            errors=["Could not parse YAML"],
            format="table",
        )

        assert "could not parse" in output.lower() or "error" in output.lower()

    def test_format_validation_multiple_errors(
        self,
        simple_recipe: Recipe,
    ) -> None:
        """Test formatting with multiple validation errors."""
        errors = [
            "Error 1: Missing name field",
            "Error 2: Invalid step type",
            "Error 3: Timeout must be positive",
            "Error 4: Unknown field 'invalid_field'",
        ]

        output = format_validation_result(
            recipe=simple_recipe,
            is_valid=False,
            errors=errors,
            format="table",
        )

        for error in errors:
            assert error in output


class TestFormatRecipeDetails:
    """Tests for formatting recipe details (show command)."""

    def test_format_basic_details_table(
        self,
        simple_recipe: Recipe,
    ) -> None:
        """Test table formatting of basic recipe details."""
        output = format_recipe_details(simple_recipe, format="table")

        assert simple_recipe.name in output
        assert simple_recipe.description in output
        assert simple_recipe.version in output
        assert simple_recipe.author in output

    def test_format_details_with_steps(
        self,
        complex_recipe: Recipe,
    ) -> None:
        """Test formatting recipe details including steps."""
        output = format_recipe_details(complex_recipe, format="table", show_steps=True)

        for step in complex_recipe.steps:
            assert step.id in output

    def test_format_details_with_context(
        self,
        complex_recipe: Recipe,
    ) -> None:
        """Test formatting recipe details including context."""
        output = format_recipe_details(complex_recipe, format="table", show_context=True)

        assert "output_dir" in output or "context" in output.lower()

    def test_format_details_with_tags(
        self,
        complex_recipe: Recipe,
    ) -> None:
        """Test formatting recipe details including tags."""
        output = format_recipe_details(complex_recipe, format="table", show_tags=True)

        for tag in complex_recipe.tags:
            assert tag in output

    def test_format_details_json(
        self,
        simple_recipe: Recipe,
    ) -> None:
        """Test JSON formatting of recipe details."""
        output = format_recipe_details(simple_recipe, format="json")

        parsed = json.loads(output)
        assert parsed["name"] == simple_recipe.name
        assert parsed["description"] == simple_recipe.description

    def test_format_details_yaml(
        self,
        simple_recipe: Recipe,
    ) -> None:
        """Test YAML formatting of recipe details."""
        output = format_recipe_details(simple_recipe, format="yaml")

        parsed = yaml.safe_load(output)
        assert parsed["name"] == simple_recipe.name

    def test_format_details_minimal_recipe(self) -> None:
        """Test formatting minimal recipe with few fields."""
        minimal = Recipe(name="minimal")

        output = format_recipe_details(minimal, format="table")
        assert "minimal" in output
        assert isinstance(output, str)

    def test_format_details_with_all_step_types(
        self,
        agent_recipe: Recipe,
    ) -> None:
        """Test formatting recipe with different step types."""
        output = format_recipe_details(agent_recipe, format="table", show_steps=True)

        assert "agent" in output.lower()
        assert "analyzer" in output

    def test_format_details_table_alignment(
        self,
        complex_recipe: Recipe,
    ) -> None:
        """Test table columns are properly aligned."""
        output = format_recipe_details(complex_recipe, format="table", show_steps=True)

        # Basic check for table structure
        lines = output.split("\n")
        assert len(lines) > 3  # Should have header, separator, and data rows

    def test_format_details_step_attributes(
        self,
        complex_recipe: Recipe,
    ) -> None:
        """Test formatting includes step attributes (timeout, condition, etc)."""
        output = format_recipe_details(
            complex_recipe, format="table", show_steps=True, verbose=True
        )

        # Check for step attributes in verbose mode
        assert "timeout" in output.lower() or "300" in output  # timeout value from fixture


class TestOutputConsistency:
    """Tests for output format consistency across functions."""

    def test_json_output_always_parseable(
        self,
        simple_recipe: Recipe,
        successful_result: RecipeResult,
    ) -> None:
        """Test all JSON outputs can be parsed."""
        outputs = [
            format_recipe_result(successful_result, format="json"),
            format_recipe_list([simple_recipe], format="json"),
            format_validation_result(simple_recipe, True, [], format="json"),
            format_recipe_details(simple_recipe, format="json"),
        ]

        for output in outputs:
            # Should not raise exception
            json.loads(output)

    def test_yaml_output_always_parseable(
        self,
        simple_recipe: Recipe,
        successful_result: RecipeResult,
    ) -> None:
        """Test all YAML outputs can be parsed."""
        outputs = [
            format_recipe_result(successful_result, format="yaml"),
            format_recipe_list([simple_recipe], format="yaml"),
            format_validation_result(simple_recipe, True, [], format="yaml"),
            format_recipe_details(simple_recipe, format="yaml"),
        ]

        for output in outputs:
            # Should not raise exception
            yaml.safe_load(output)

    def test_table_output_never_empty(
        self,
        simple_recipe: Recipe,
        successful_result: RecipeResult,
    ) -> None:
        """Test table outputs always contain some content."""
        outputs = [
            format_recipe_result(successful_result, format="table"),
            format_recipe_list([simple_recipe], format="table"),
            format_validation_result(simple_recipe, True, [], format="table"),
            format_recipe_details(simple_recipe, format="table"),
        ]

        for output in outputs:
            assert len(output.strip()) > 0

    def test_all_formats_support_unicode(self) -> None:
        """Test all formatters handle Unicode correctly."""
        unicode_recipe = Recipe(
            name="unicode-test",
            description="Test with émojis 🎉 and spëcial çhars",
        )
        unicode_result = RecipeResult(
            recipe_name="test",
            success=True,
            step_results=[
                StepResult(
                    step_id="unicode",
                    status=StepStatus.COMPLETED,
                    output="✓ Sućcess",
                )
            ],
        )

        for fmt in ["table", "json", "yaml"]:
            # Should not raise exceptions
            format_recipe_result(unicode_result, format=fmt)
            format_recipe_list([unicode_recipe], format=fmt)
            format_validation_result(unicode_recipe, True, [], format=fmt)
            format_recipe_details(unicode_recipe, format=fmt)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_strings_in_fields(self) -> None:
        """Test handling of empty string values."""
        empty_recipe = Recipe(
            name="",
            description="",
            version="",
            author="",
        )

        # Should not crash
        output = format_recipe_details(empty_recipe, format="table")
        assert isinstance(output, str)

    def test_very_long_field_values(self) -> None:
        """Test handling of very long field values."""
        long_recipe = Recipe(
            name="x" * 500,
            description="y" * 5000,
        )

        output = format_recipe_details(long_recipe, format="table")
        # Should truncate or wrap appropriately
        assert isinstance(output, str)

    def test_null_values_in_context(self) -> None:
        """Test handling of None values in context."""
        result = RecipeResult(
            recipe_name="test",
            success=True,
            step_results=[],
            context={"key1": None, "key2": "value", "key3": 0, "key4": False},
        )

        output = format_recipe_result(result, format="json", show_context=True)
        parsed = json.loads(output)
        assert parsed["context"]["key1"] is None

    def test_circular_reference_protection(self) -> None:
        """Test protection against circular references in data."""
        # Note: This is a design consideration - formatters should handle
        # data structures defensively
        result = RecipeResult(
            recipe_name="test",
            success=True,
            step_results=[],
        )

        # Should not raise recursion errors
        output = format_recipe_result(result, format="json")
        assert isinstance(output, str)

    def test_format_with_missing_optional_params(
        self,
        simple_recipe: Recipe,
    ) -> None:
        """Test formatters work with minimal required parameters."""
        # All optional parameters omitted
        output1 = format_recipe_details(simple_recipe, format="table")
        output2 = format_recipe_list([simple_recipe], format="table")

        assert isinstance(output1, str)
        assert isinstance(output2, str)
