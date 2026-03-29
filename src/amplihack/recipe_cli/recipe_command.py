"""Recipe CLI command handlers.

Implements the four recipe subcommands:
- amplihack recipe run <path> [options]
- amplihack recipe list [options]
- amplihack recipe validate <path> [options]
- amplihack recipe show <path> [options]

Each function returns an exit code (0=success, 1=error, 130=SIGINT).
"""

from __future__ import annotations

__all__ = [
    "handle_run",
    "handle_list",
    "handle_validate",
    "handle_show",
    "parse_context_args",
    "_infer_missing_context",
]

import sys
import traceback
from pathlib import Path
from typing import Any

from amplihack.recipes import run_recipe_via_rust
from amplihack.recipes.models import Recipe, RecipeResult

from .context import (
    infer_missing_context as _infer_missing_context,
)
from .context import merge_recipe_context, parse_context_args
from .loader import discover_recipe_definitions, filter_recipes_by_tags, load_recipe_definition
from .recipe_output import (
    format_recipe_details,
    format_recipe_list,
    format_recipe_result,
    format_validation_result,
)

_VALID_FORMATS = {"table", "json", "yaml"}


def _validate_output_format(format_name: str) -> None:
    if format_name not in _VALID_FORMATS:
        raise ValueError(f"Invalid format: {format_name}. Must be table, json, or yaml")


def _print_error(error: Exception, *, verbose: bool = False, prefix: str = "") -> int:
    print(f"Error: {prefix}{error}", file=sys.stderr)
    if verbose and not isinstance(error, (FileNotFoundError, ValueError, PermissionError)):
        traceback.print_exc()
    return 1


def _print_run_preamble(recipe_name: str, *, dry_run: bool, verbose: bool) -> None:
    if not verbose:
        return
    print(f"Executing recipe: {recipe_name}", file=sys.stderr)
    if dry_run:
        print("DRY RUN MODE - No actual execution", file=sys.stderr)


def _execute_recipe(
    validated_path: Path,
    merged_context: dict[str, Any],
    *,
    dry_run: bool,
    progress: bool,
    verbose: bool,
    working_dir: str | None,
) -> RecipeResult:
    return run_recipe_via_rust(
        name=str(validated_path),
        user_context=merged_context,
        dry_run=dry_run,
        working_dir=working_dir or ".",
        progress=progress or verbose,
        emit_startup_banner=False,
    )


def _render_validation(
    recipe: Recipe | None, *, is_valid: bool, errors: list[str], format: str, verbose: bool = False
) -> int:
    print(
        format_validation_result(
            recipe=recipe,
            is_valid=is_valid,
            errors=errors,
            format=format,
            verbose=verbose,
        )
    )
    return 0 if is_valid else 1


def handle_run(
    recipe_path: str,
    context: dict[str, Any],
    dry_run: bool = False,
    progress: bool = False,
    verbose: bool = False,
    format: str = "table",
    working_dir: str | None = None,
) -> int:
    """Execute a recipe from a YAML file."""
    _validate_output_format(format)

    try:
        recipe, validated_path = load_recipe_definition(recipe_path)
        _print_run_preamble(recipe.name, dry_run=dry_run, verbose=verbose)
        merged_context = merge_recipe_context(recipe.context or {}, context, verbose=verbose)
        result = _execute_recipe(
            validated_path,
            merged_context,
            dry_run=dry_run,
            progress=progress,
            verbose=verbose,
            working_dir=working_dir,
        )
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except PermissionError as error:
        return _print_error(error, prefix="Permission denied - ")
    except (FileNotFoundError, ValueError) as error:
        return _print_error(error)
    except Exception as error:
        return _print_error(error, verbose=verbose)

    print(format_recipe_result(result, format=format, show_context=False))
    return 0 if result.success else 1


def handle_list(
    recipe_dir: str | None = None,
    format: str = "table",
    tags: list[str] | None = None,
    verbose: bool = False,
) -> int:
    """List available recipes in a directory."""
    try:
        recipes = discover_recipe_definitions(recipe_dir, verbose=verbose)
        recipes = filter_recipes_by_tags(recipes, tags)
    except FileNotFoundError as error:
        return _print_error(error)
    except Exception as error:
        return _print_error(error)

    print(format_recipe_list(recipes, format=format, verbose=verbose, show_tags=True))
    return 0


def handle_validate(
    recipe_path: str,
    verbose: bool = False,
    format: str = "table",
) -> int:
    """Validate a recipe YAML file."""
    try:
        recipe, _ = load_recipe_definition(recipe_path)
    except FileNotFoundError as error:
        return _render_validation(
            None, is_valid=False, errors=[f"File not found: {error}"], format=format
        )
    except ValueError as error:
        return _render_validation(None, is_valid=False, errors=[str(error)], format=format)
    except Exception as error:
        return _render_validation(
            None,
            is_valid=False,
            errors=[f"Validation error: {error}"],
            format=format,
        )

    return _render_validation(recipe, is_valid=True, errors=[], format=format, verbose=verbose)


def handle_show(
    recipe_path: str,
    format: str = "table",
    show_steps: bool = True,
    show_context: bool = True,
) -> int:
    """Show detailed recipe information."""
    try:
        recipe, _ = load_recipe_definition(recipe_path)
    except FileNotFoundError as error:
        print(f"Error: File not found - {error}", file=sys.stderr)
        return 1
    except Exception as error:
        return _print_error(error)

    print(
        format_recipe_details(
            recipe,
            format=format,
            show_steps=show_steps,
            show_context=show_context,
            show_tags=True,
        )
    )
    return 0
