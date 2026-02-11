"""Tests for RecipeParser.

These tests verify that the RecipeParser can:
- Parse valid YAML recipe strings into Recipe model objects
- Correctly identify step types (BASH vs AGENT)
- Infer step types from the presence of 'agent' or 'command' fields
- Reject invalid recipes with clear error messages
- Validate recipes and produce warnings for questionable patterns
- Parse real recipe files from the amplifier-bundle
"""

from __future__ import annotations

import pytest

from amplihack.recipes.models import StepType
from amplihack.recipes.parser import RecipeParser


class TestParseSimpleRecipe:
    """Test basic recipe parsing from YAML strings."""

    def test_parse_simple_recipe(self, simple_recipe_yaml: str) -> None:
        """Parse a simple 2-step recipe YAML and verify name and step count."""
        parser = RecipeParser()
        recipe = parser.parse(simple_recipe_yaml)

        assert recipe.name == "simple-test-recipe"
        assert len(recipe.steps) == 2

    def test_parse_step_types(self, simple_recipe_yaml: str) -> None:
        """Bash step gets StepType.BASH, agent step gets StepType.AGENT."""
        parser = RecipeParser()
        recipe = parser.parse(simple_recipe_yaml)

        assert recipe.steps[0].step_type == StepType.BASH
        assert recipe.steps[1].step_type == StepType.AGENT


class TestStepTypeInference:
    """Test that step types are inferred from field presence when not explicit."""

    def test_parse_infer_step_type_from_agent(self) -> None:
        """A step with an 'agent' field but no explicit type defaults to StepType.AGENT."""
        yaml_str = """\
name: "infer-agent"
description: "test"
version: "1.0.0"
steps:
  - id: "step-01"
    agent: "amplihack:builder"
    prompt: "Do something"
    output: "result"
"""
        parser = RecipeParser()
        recipe = parser.parse(yaml_str)

        assert recipe.steps[0].step_type == StepType.AGENT

    def test_parse_infer_step_type_from_command(self) -> None:
        """A step with a 'command' field but no explicit type defaults to StepType.BASH."""
        yaml_str = """\
name: "infer-bash"
description: "test"
version: "1.0.0"
steps:
  - id: "step-01"
    command: "echo hello"
    output: "result"
"""
        parser = RecipeParser()
        recipe = parser.parse(yaml_str)

        assert recipe.steps[0].step_type == StepType.BASH


class TestParseValidation:
    """Test that invalid recipes are rejected with clear errors."""

    def test_parse_missing_name_raises(self) -> None:
        """ValueError if recipe YAML has no 'name' field."""
        yaml_str = """\
description: "no name"
version: "1.0.0"
steps:
  - id: "step-01"
    type: "bash"
    command: "echo hello"
"""
        parser = RecipeParser()
        with pytest.raises(ValueError, match="(?i)name"):
            parser.parse(yaml_str)

    def test_parse_missing_steps_raises(self) -> None:
        """ValueError if recipe YAML has no 'steps' field."""
        yaml_str = """\
name: "no-steps"
description: "missing steps"
version: "1.0.0"
"""
        parser = RecipeParser()
        with pytest.raises(ValueError, match="(?i)steps"):
            parser.parse(yaml_str)

    def test_parse_duplicate_step_ids_raises(self) -> None:
        """ValueError when two steps share the same id."""
        yaml_str = """\
name: "duplicate-ids"
description: "test"
version: "1.0.0"
steps:
  - id: "step-01"
    type: "bash"
    command: "echo first"
  - id: "step-01"
    type: "bash"
    command: "echo second"
"""
        parser = RecipeParser()
        with pytest.raises(ValueError, match="(?i)duplicate"):
            parser.parse(yaml_str)


class TestParseRealRecipe:
    """Test parsing of actual recipe files from the amplifier-bundle."""

    def test_parse_existing_recipe_file(self, sample_recipe_path) -> None:
        """Parse the actual verification-workflow.yaml and verify structure."""
        assert sample_recipe_path.exists(), f"Recipe file not found at {sample_recipe_path}"

        parser = RecipeParser()
        recipe = parser.parse(sample_recipe_path.read_text())

        assert recipe.name == "verification-workflow"
        assert len(recipe.steps) >= 5
        # First step should be an agent step (builder)
        assert recipe.steps[0].agent == "amplihack:builder"


class TestRecipeValidation:
    """Test the validate method for producing warnings."""

    def test_validate_returns_no_warnings_for_valid_recipe(self, simple_recipe_yaml: str) -> None:
        """A well-formed recipe with all required fields produces no warnings."""
        parser = RecipeParser()
        recipe = parser.parse(simple_recipe_yaml)
        warnings = parser.validate(recipe)

        assert warnings == []

    def test_validate_warns_on_missing_agent_prompt(self) -> None:
        """An agent step without a 'prompt' field should produce a warning."""
        yaml_str = """\
name: "missing-prompt"
description: "test"
version: "1.0.0"
steps:
  - id: "step-01"
    agent: "amplihack:builder"
    output: "result"
"""
        parser = RecipeParser()
        recipe = parser.parse(yaml_str)
        warnings = parser.validate(recipe)

        assert len(warnings) > 0
        assert any("prompt" in w.lower() for w in warnings)
