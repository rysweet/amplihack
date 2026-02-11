"""Recipe Runner module -- parse, validate, and execute YAML-defined recipes.

Public API:
    - ``parse_recipe(yaml_content)`` -- shortcut to parse a YAML string
    - ``run_recipe(yaml_content, adapter, **kwargs)`` -- parse and execute in one call
    - ``RecipeRunner`` -- the core execution engine
    - ``RecipeParser`` -- YAML-to-Recipe parser
    - ``RecipeContext`` -- template-rendering execution context
"""

from __future__ import annotations

from typing import Any

from amplihack.recipes.agent_resolver import AgentNotFoundError, AgentResolver
from amplihack.recipes.context import RecipeContext
from amplihack.recipes.models import (
    Recipe,
    RecipeResult,
    RecursionLimits,
    Step,
    StepExecutionError,
    StepResult,
    StepStatus,
    StepType,
)
from amplihack.recipes.parser import RecipeParser
from amplihack.recipes.runner import RecipeRunner

__all__ = [
    "AgentNotFoundError",
    "AgentResolver",
    "RecipeContext",
    "RecipeParser",
    "RecipeRunner",
    "Recipe",
    "RecipeResult",
    "RecursionLimits",
    "Step",
    "StepExecutionError",
    "StepResult",
    "StepStatus",
    "StepType",
    "parse_recipe",
    "run_recipe",
]


def parse_recipe(yaml_content: str) -> Recipe:
    """Shortcut: parse a YAML string into a Recipe."""
    return RecipeParser().parse(yaml_content)


def run_recipe(
    yaml_content: str,
    adapter: Any,
    user_context: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> RecipeResult:
    """Shortcut: parse and execute a recipe in one call."""
    recipe = parse_recipe(yaml_content)
    runner = RecipeRunner(adapter=adapter)
    return runner.execute(recipe, user_context=user_context, dry_run=dry_run)
