"""Recipe output formatters for CLI.

Provides formatting functions for all recipe CLI commands:
- format_recipe_result() - Format recipe execution results
- format_recipe_list() - Format list of available recipes
- format_validation_result() - Format validation results
- format_recipe_details() - Format detailed recipe information

Each formatter supports three output formats: table, json, yaml
"""

from __future__ import annotations

import json
from typing import Any

import yaml

from amplihack.recipes.models import Recipe, RecipeResult, StepStatus

# Truncation constants for output formatting
MAX_OUTPUT_LENGTH = 200  # Maximum characters for step output in table format
MAX_PROMPT_LENGTH = 100  # Maximum characters for prompt display in table format


def format_recipe_result(
    result: RecipeResult,
    format: str = "table",
    show_context: bool = False,
) -> str:
    """Format recipe execution result.

    Args:
        result: Recipe execution result
        format: Output format (table/json/yaml)
        show_context: Include context variables in output

    Returns:
        Formatted string output

    Raises:
        ValueError: If format is invalid
    """
    if format == "json":
        return _format_result_json(result, show_context)
    if format == "yaml":
        return _format_result_yaml(result, show_context)
    if format == "table":
        return _format_result_table(result, show_context)
    raise ValueError(f"Invalid format: {format}. Must be table, json, or yaml")


def format_recipe_list(
    recipes: list[Recipe],
    format: str = "table",
    verbose: bool = False,
    show_tags: bool = False,
) -> str:
    """Format list of recipes.

    Args:
        recipes: List of recipes to format
        format: Output format (table/json/yaml)
        verbose: Include detailed information
        show_tags: Include tags in output

    Returns:
        Formatted string output

    Raises:
        ValueError: If format is invalid
    """
    if format == "json":
        return _format_list_json(recipes, verbose)
    if format == "yaml":
        return _format_list_yaml(recipes, verbose)
    if format == "table":
        return _format_list_table(recipes, verbose, show_tags)
    raise ValueError(f"Invalid format: {format}. Must be table, json, or yaml")


def format_validation_result(
    recipe: Recipe | None,
    is_valid: bool,
    errors: list[str],
    format: str = "table",
    verbose: bool = False,
) -> str:
    """Format recipe validation result.

    Args:
        recipe: Recipe object (None if parsing failed)
        is_valid: Whether recipe is valid
        errors: List of validation errors
        format: Output format (table/json/yaml)
        verbose: Include detailed validation info

    Returns:
        Formatted string output

    Raises:
        ValueError: If format is invalid
    """
    if format == "json":
        return _format_validation_json(recipe, is_valid, errors)
    if format == "yaml":
        return _format_validation_yaml(recipe, is_valid, errors)
    if format == "table":
        return _format_validation_table(recipe, is_valid, errors, verbose)
    raise ValueError(f"Invalid format: {format}. Must be table, json, or yaml")


def format_recipe_details(
    recipe: Recipe,
    format: str = "table",
    show_steps: bool = True,
    show_context: bool = True,
    show_tags: bool = True,
    verbose: bool = False,
) -> str:
    """Format detailed recipe information.

    Args:
        recipe: Recipe to format
        format: Output format (table/json/yaml)
        show_steps: Include step details
        show_context: Include context variables
        show_tags: Include tags
        verbose: Include all details (timeout, conditions, etc.)

    Returns:
        Formatted string output

    Raises:
        ValueError: If format is invalid
    """
    if format == "json":
        return _format_details_json(recipe)
    if format == "yaml":
        return _format_details_yaml(recipe)
    if format == "table":
        return _format_details_table(recipe, show_steps, show_context, show_tags, verbose)
    raise ValueError(f"Invalid format: {format}. Must be table, json, or yaml")


# ============================================================================
# JSON Formatters
# ============================================================================


def _format_result_json(result: RecipeResult, show_context: bool) -> str:
    """Format result as JSON."""
    data = {
        "recipe_name": result.recipe_name,
        "success": result.success,
        "step_results": [
            {
                "step_id": step.step_id,
                "status": step.status.value,
                "output": step.output or "",
                "error": step.error or "",
            }
            for step in result.step_results
        ],
    }
    if show_context and result.context:
        data["context"] = result.context
    return json.dumps(data, indent=2, ensure_ascii=False)


def _format_list_json(recipes: list[Recipe], verbose: bool) -> str:
    """Format recipe list as JSON."""
    data = []
    for recipe in sorted(recipes, key=lambda r: r.name):
        item: dict[str, Any] = {
            "name": recipe.name,
            "description": recipe.description or "",
        }
        if verbose:
            item["version"] = recipe.version or ""
            item["author"] = recipe.author or ""
            item["tags"] = recipe.tags or []
            item["step_count"] = len(recipe.steps or [])
        data.append(item)
    return json.dumps(data, indent=2, ensure_ascii=False)


def _format_validation_json(recipe: Recipe | None, is_valid: bool, errors: list[str]) -> str:
    """Format validation result as JSON."""
    data = {
        "valid": is_valid,
        "errors": errors,
    }
    if recipe:
        data["recipe_name"] = recipe.name
    return json.dumps(data, indent=2, ensure_ascii=False)


def _format_details_json(recipe: Recipe) -> str:
    """Format recipe details as JSON."""
    data = {
        "name": recipe.name,
        "description": recipe.description or "",
        "version": recipe.version or "",
        "author": recipe.author or "",
        "tags": recipe.tags or [],
        "steps": [
            {
                "id": step.id,
                "type": step.step_type.value,
                "command": getattr(step, "command", None),
                "agent": getattr(step, "agent", None),
                "prompt": getattr(step, "prompt", None),
            }
            for step in (recipe.steps or [])
        ],
        "context": recipe.context or {},
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# ============================================================================
# YAML Formatters
# ============================================================================


def _format_result_yaml(result: RecipeResult, show_context: bool) -> str:
    """Format result as YAML."""
    data = {
        "recipe_name": result.recipe_name,
        "success": result.success,
        "step_results": [
            {
                "step_id": step.step_id,
                "status": step.status.value,
                "output": step.output or "",
                "error": step.error or "",
            }
            for step in result.step_results
        ],
    }
    if show_context and result.context:
        data["context"] = result.context
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


def _format_list_yaml(recipes: list[Recipe], verbose: bool) -> str:
    """Format recipe list as YAML."""
    data = []
    for recipe in sorted(recipes, key=lambda r: r.name):
        item: dict[str, Any] = {
            "name": recipe.name,
            "description": recipe.description or "",
        }
        if verbose:
            item["version"] = recipe.version or ""
            item["author"] = recipe.author or ""
            item["tags"] = recipe.tags or []
            item["step_count"] = len(recipe.steps or [])
        data.append(item)
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


def _format_validation_yaml(recipe: Recipe | None, is_valid: bool, errors: list[str]) -> str:
    """Format validation result as YAML."""
    data = {
        "valid": is_valid,
        "errors": errors,
    }
    if recipe:
        data["recipe_name"] = recipe.name
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


def _format_details_yaml(recipe: Recipe) -> str:
    """Format recipe details as YAML."""

    # Return the recipe as YAML (essentially the original file format)
    def serialize_step(step):
        """Convert step to dict with enum values as strings."""
        data = {}
        for k, v in step.__dict__.items():
            if not k.startswith("_"):
                # Convert enums to their string value
                if hasattr(v, "value"):
                    data[k] = v.value
                else:
                    data[k] = v
        return data

    return yaml.dump(
        {
            "name": recipe.name,
            "description": recipe.description or "",
            "version": recipe.version or "",
            "author": recipe.author or "",
            "tags": recipe.tags or [],
            "steps": [serialize_step(step) for step in (recipe.steps or [])],
            "context": recipe.context or {},
        },
        default_flow_style=False,
        allow_unicode=True,
    )


# ============================================================================
# Table Formatters
# ============================================================================


def _format_result_table(result: RecipeResult, show_context: bool) -> str:
    """Format result as human-readable table."""
    lines = []
    lines.append(f"Recipe: {result.recipe_name}")
    lines.append(f"Status: {'✓ Success' if result.success else '✗ Failed'}")
    lines.append("")

    if not result.step_results:
        lines.append("No steps executed (0 steps)")
        return "\n".join(lines)

    lines.append("Steps:")
    for step in result.step_results:
        status_symbol = {
            StepStatus.COMPLETED: "✓",
            StepStatus.FAILED: "✗",
            StepStatus.SKIPPED: "⊘",
        }.get(step.status, "?")

        lines.append(f"  {status_symbol} {step.step_id}: {step.status.value}")

        if step.output:
            # Truncate very long output
            if len(step.output) > MAX_OUTPUT_LENGTH:
                output = step.output[:MAX_OUTPUT_LENGTH] + "... (truncated)"
            else:
                output = step.output
            lines.append(f"    Output: {output}")

        if step.error:
            lines.append(f"    Error: {step.error}")

    if show_context and result.context:
        lines.append("")
        lines.append("Context:")
        for key, value in result.context.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def _format_list_table(recipes: list[Recipe], verbose: bool, show_tags: bool) -> str:
    """Format recipe list as human-readable table."""
    if not recipes:
        return "No recipes found (0 recipes)"

    lines = []
    lines.append(f"Available Recipes ({len(recipes)}):")
    lines.append("")

    for recipe in sorted(recipes, key=lambda r: r.name):
        lines.append(f"• {recipe.name}")
        if recipe.description:
            lines.append(f"  {recipe.description}")

        if verbose:
            if recipe.version:
                lines.append(f"  Version: {recipe.version}")
            if recipe.author:
                lines.append(f"  Author: {recipe.author}")
            step_count = len(recipe.steps or [])
            lines.append(f"  Steps: {step_count}")

        if show_tags and recipe.tags:
            lines.append(f"  Tags: {', '.join(recipe.tags)}")

        lines.append("")

    return "\n".join(lines)


def _format_validation_table(
    recipe: Recipe | None, is_valid: bool, errors: list[str], verbose: bool
) -> str:
    """Format validation result as human-readable table."""
    lines = []

    if is_valid:
        lines.append("✓ Recipe is valid")
        if recipe:
            lines.append(f"  Name: {recipe.name}")
            if verbose:
                lines.append(f"  Description: {recipe.description or '(none)'}")
                lines.append(f"  Steps: {len(recipe.steps or [])}")
    else:
        lines.append("✗ Recipe is invalid")
        if errors:
            lines.append("")
            lines.append("Errors:")
            for error in errors:
                lines.append(f"  • {error}")

    return "\n".join(lines)


def _format_details_table(
    recipe: Recipe,
    show_steps: bool,
    show_context: bool,
    show_tags: bool,
    verbose: bool,
) -> str:
    """Format recipe details as human-readable table."""
    lines = []
    lines.append(f"Recipe: {recipe.name}")
    lines.append(f"Description: {recipe.description or '(none)'}")
    lines.append(f"Version: {recipe.version or '(not specified)'}")
    lines.append(f"Author: {recipe.author or '(not specified)'}")

    if show_tags and recipe.tags:
        lines.append(f"Tags: {', '.join(recipe.tags)}")

    if show_steps and recipe.steps:
        lines.append("")
        lines.append(f"Steps ({len(recipe.steps)}):")
        for i, step in enumerate(recipe.steps, 1):
            lines.append(f"  {i}. {step.id} ({step.step_type.value})")

            if hasattr(step, "command") and step.command:
                lines.append(f"     Command: {step.command}")
            if hasattr(step, "agent") and step.agent:
                lines.append(f"     Agent: {step.agent}")
            if hasattr(step, "prompt") and step.prompt:
                prompt = (
                    step.prompt[:MAX_PROMPT_LENGTH] + "..."
                    if len(step.prompt) > MAX_PROMPT_LENGTH
                    else step.prompt
                )
                lines.append(f"     Prompt: {prompt}")

            if verbose:
                if hasattr(step, "timeout") and step.timeout:
                    lines.append(f"     Timeout: {step.timeout}s")
                if hasattr(step, "condition") and step.condition:
                    lines.append(f"     Condition: {step.condition}")

    if show_context and recipe.context:
        lines.append("")
        lines.append("Context Variables:")
        for key, value in recipe.context.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)
