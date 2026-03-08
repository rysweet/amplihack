"""Recipe Runner module -- parse, validate, and execute YAML-defined recipes.

Public API:
    - ``parse_recipe(yaml_content)`` -- shortcut to parse a YAML string
    - ``run_recipe(yaml_content, adapter, **kwargs)`` -- parse and execute in one call
    - ``list_recipes()`` -- discover all available recipes
    - ``find_recipe(name)`` -- find a recipe file by name
    - ``RecipeRunner`` -- the core execution engine
    - ``RecipeParser`` -- YAML-to-Recipe parser
    - ``RecipeContext`` -- template-rendering execution context
"""

from __future__ import annotations

from typing import Any

from amplihack.recipes.agent_resolver import AgentNotFoundError, AgentResolver
from amplihack.recipes.context import RecipeContext
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
from amplihack.recipes.runner import RecipeRunner

from amplihack.recipes.rust_runner import (
    RustRunnerNotFoundError,
    find_rust_binary,
    is_rust_runner_available,
    run_recipe_via_rust,
)

__all__ = [
    "AgentNotFoundError",
    "AgentResolver",
    "RecipeContext",
    "RecipeInfo",
    "RecipeParser",
    "RecipeRunner",
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
    "find_recipe",
    "find_rust_binary",
    "is_rust_runner_available",
    "list_recipes",
    "parse_recipe",
    "run_recipe",
    "run_recipe_by_name",
    "run_recipe_via_rust",
    "sync_upstream",
    "update_manifest",
    "verify_global_installation",
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


def run_recipe_by_name(
    name: str,
    adapter: Any,
    user_context: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> RecipeResult:
    """Find a recipe by name, parse it, and execute it.

    Engine selection (no fallbacks — chosen engine must succeed or fail):

    - ``RECIPE_RUNNER_ENGINE=rust`` → Rust binary only (fails if not installed)
    - ``RECIPE_RUNNER_ENGINE=python`` → Python runner only
    - Not set → auto-detect once: Rust if binary exists, Python otherwise.
      Logs which engine was selected.

    Args:
        name: Recipe name (e.g. ``"default-workflow"``).
        adapter: SDK adapter for step execution (used by Python engine).
        user_context: Context variable overrides.
        dry_run: If True, log steps without executing.

    Raises:
        FileNotFoundError: If no recipe with that name is found.
        RustRunnerNotFoundError: If engine is 'rust' but binary is missing.
    """
    import os

    engine = os.environ.get("RECIPE_RUNNER_ENGINE", "").lower()

    if engine == "rust":
        # Explicit Rust — no fallback
        return run_recipe_via_rust(name=name, user_context=user_context, dry_run=dry_run)

    if engine == "python":
        # Explicit Python — no Rust attempted
        return _run_recipe_python(name, adapter, user_context, dry_run)

    # Auto-detect: check once, commit to the result
    if is_rust_runner_available():
        import logging
        logging.getLogger(__name__).info("Auto-detected Rust recipe runner — using it exclusively")
        return run_recipe_via_rust(name=name, user_context=user_context, dry_run=dry_run)

    return _run_recipe_python(name, adapter, user_context, dry_run)


def _run_recipe_python(
    name: str,
    adapter: Any,
    user_context: dict[str, Any] | None,
    dry_run: bool,
) -> RecipeResult:
    """Execute a recipe using the Python runner."""
    path = find_recipe(name)
    if path is None:
        raise FileNotFoundError(f"Recipe '{name}' not found in any search directory")
    recipe = RecipeParser().parse_file(path)
    runner = RecipeRunner(adapter=adapter)
    return runner.execute(recipe, user_context=user_context, dry_run=dry_run)
