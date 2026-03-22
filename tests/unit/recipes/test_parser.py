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


class TestParseStepIdValidation:
    """Test that steps must have non-empty ids."""

    def test_parse_missing_step_id_raises(self) -> None:
        """ValueError when a step has no 'id' field."""
        yaml_str = """\
name: "no-id"
steps:
  - type: "bash"
    command: "echo hi"
"""
        parser = RecipeParser()
        with pytest.raises(ValueError, match="(?i)id"):
            parser.parse(yaml_str)

    def test_parse_prompt_only_step_infers_agent(self) -> None:
        """A step with only 'prompt' (no agent, no command) should infer AGENT type."""
        yaml_str = """\
name: "prompt-only"
steps:
  - id: "step1"
    prompt: "do something"
"""
        parser = RecipeParser()
        recipe = parser.parse(yaml_str)
        assert recipe.steps[0].step_type == StepType.AGENT


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

    def test_validate_warns_on_unrecognized_fields(self) -> None:
        """Unrecognized YAML fields should produce a warning to catch typos."""
        yaml_str = """\
name: "typo-test"
steps:
  - id: "step-01"
    type: "bash"
    comand: "echo hi"
    command: "echo hi"
"""
        parser = RecipeParser()
        recipe = parser.parse(yaml_str)
        warnings = parser.validate(recipe, raw_yaml=yaml_str)

        assert any("comand" in w for w in warnings), (
            f"Expected warning about 'comand' typo, got: {warnings}"
        )


class TestStepFieldTypeCoercion:
    """Test that string values from YAML are coerced to the correct Python types."""

    def _make_yaml(self, **step_overrides: str) -> str:
        fields = {"id": "s1", "type": "bash", "command": "echo hi"}
        fields.update(step_overrides)
        step_lines = "\n".join(f"    {k}: {v}" for k, v in fields.items())
        return f"name: coerce-test\nsteps:\n  - {step_lines.lstrip()}"

    def test_string_true_coerced_to_bool_parse_json(self) -> None:
        recipe = RecipeParser().parse(self._make_yaml(parse_json="'true'"))
        assert recipe.steps[0].parse_json is True

    def test_string_false_coerced_to_bool_parse_json(self) -> None:
        recipe = RecipeParser().parse(self._make_yaml(parse_json="'false'"))
        assert recipe.steps[0].parse_json is False

    def test_string_yes_coerced_to_bool_auto_stage(self) -> None:
        recipe = RecipeParser().parse(self._make_yaml(auto_stage="'yes'"))
        assert recipe.steps[0].auto_stage is True

    def test_string_no_coerced_to_bool_auto_stage(self) -> None:
        recipe = RecipeParser().parse(self._make_yaml(auto_stage="'no'"))
        assert recipe.steps[0].auto_stage is False

    def test_string_int_coerced_to_int_timeout(self) -> None:
        recipe = RecipeParser().parse(self._make_yaml(timeout="'30'"))
        assert recipe.steps[0].timeout == 30
        assert isinstance(recipe.steps[0].timeout, int)

    def test_native_bool_preserved(self) -> None:
        recipe = RecipeParser().parse(self._make_yaml(parse_json="true"))
        assert recipe.steps[0].parse_json is True

    def test_native_int_preserved(self) -> None:
        recipe = RecipeParser().parse(self._make_yaml(timeout="60"))
        assert recipe.steps[0].timeout == 60


class TestStepFieldTypeValidation:
    """Test that invalid types raise clear ValueErrors."""

    def _make_yaml(self, **step_overrides: str) -> str:
        fields = {"id": "s1", "type": "bash", "command": "echo hi"}
        fields.update(step_overrides)
        step_lines = "\n".join(f"    {k}: {v}" for k, v in fields.items())
        return f"name: validate-test\nsteps:\n  - {step_lines.lstrip()}"

    def test_timeout_non_numeric_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must be an integer.*'not_an_int'"):
            RecipeParser().parse(self._make_yaml(timeout="'not_an_int'"))

    def test_parse_json_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a boolean.*'maybe'"):
            RecipeParser().parse(self._make_yaml(parse_json="'maybe'"))

    def test_auto_stage_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a boolean.*'sometimes'"):
            RecipeParser().parse(self._make_yaml(auto_stage="'sometimes'"))

    def test_timeout_bool_raises(self) -> None:
        with pytest.raises(ValueError, match="must be an integer.*bool"):
            RecipeParser().parse(self._make_yaml(timeout="true"))


class TestConflictingFieldWarnings:
    """Test that conflicting step field combinations produce warnings."""

    def test_bash_step_with_agent_field_warns(self) -> None:
        yaml_str = """\
name: conflict-test
steps:
  - id: s1
    type: bash
    command: echo hi
    agent: amplihack:builder
"""
        parser = RecipeParser()
        recipe = parser.parse(yaml_str)
        warnings = parser.validate(recipe)
        assert any("bash step has 'agent' field" in w for w in warnings)

    def test_agent_step_with_agent_field_no_warning(self) -> None:
        yaml_str = """\
name: no-conflict
steps:
  - id: s1
    type: agent
    agent: amplihack:builder
    prompt: do something
"""
        parser = RecipeParser()
        recipe = parser.parse(yaml_str)
        warnings = parser.validate(recipe)
        assert not any("bash step has 'agent' field" in w for w in warnings)
