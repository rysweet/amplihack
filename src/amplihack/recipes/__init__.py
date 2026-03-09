"""Recipe Runner module -- parse, validate, and execute YAML-defined recipes.

All recipe execution uses the Rust recipe runner (recipe-runner-rs).
The Python recipe runner has been removed.

Public API:
    - ``parse_recipe(yaml_content)`` -- shortcut to parse a YAML string
    - ``run_recipe_by_name(name, **kwargs)`` -- find and execute via Rust runner
    - ``list_recipes()`` -- discover all available recipes
    - ``find_recipe(name)`` -- find a recipe file by name
    - ``RecipeParser`` -- YAML-to-Recipe parser
"""

from __future__ import annotations

from typing import Any

from amplihack.recipes.agent_resolver import AgentNotFoundError, AgentResolver
from amplihack.recipes.discovery import (
    RecipeInfo,
    check_upstream_changes,
    discover_recipes,
    find_recipe,
    list_recipes,
    sync_upstream,
    update_manifest,
    verify_global_installation,
)
from amplihack.recipes.models import (
    Recipe,
    RecipeResult,
    Step,
    StepExecutionError,
    StepResult,
    StepStatus,
    StepType,
)
from amplihack.recipes.parser import RecipeParser
from amplihack.recipes.rust_runner import (
    RustRunnerNotFoundError,
    ensure_rust_recipe_runner,
    find_rust_binary,
    is_rust_runner_available,
    run_recipe_via_rust,
)

__all__ = [
    "AgentNotFoundError",
    "AgentResolver",
    "RecipeInfo",
    "RecipeParser",
    "Recipe",
    "RecipeResult",
    "RustRunnerNotFoundError",
    "Step",
    "StepExecutionError",
    "StepResult",
    "StepStatus",
    "StepType",
    "check_upstream_changes",
    "discover_recipes",
    "ensure_rust_recipe_runner",
    "find_recipe",
    "find_rust_binary",
    "is_rust_runner_available",
    "list_recipes",
    "parse_recipe",
    "run_recipe_by_name",
    "run_recipe_via_rust",
    "sync_upstream",
    "update_manifest",
    "verify_global_installation",
]


def parse_recipe(yaml_content: str) -> Recipe:
    """Shortcut: parse a YAML string into a Recipe."""
    return RecipeParser().parse(yaml_content)


def run_recipe_by_name(
    name: str,
    user_context: dict[str, Any] | None = None,
    dry_run: bool = False,
    **_kwargs: Any,
) -> RecipeResult:
    """Find a recipe by name and execute it via the Rust recipe runner.

    The ``adapter`` keyword argument is accepted for backward compatibility
    but ignored — all execution goes through the Rust binary.

    Args:
        name: Recipe name (e.g. ``"default-workflow"``).
        user_context: Context variable overrides.
        dry_run: If True, log steps without executing.

    Raises:
        RustRunnerNotFoundError: If the Rust binary is not installed.
    """
    return run_recipe_via_rust(name=name, user_context=user_context, dry_run=dry_run)
