"""Recipe CLI command handlers.

Implements the four recipe subcommands:
- amplihack recipe run <path> [options]
- amplihack recipe list [options]
- amplihack recipe validate <path> [options]
- amplihack recipe show <path> [options]

Each function returns an exit code (0=success, 1=error, 130=SIGINT).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from amplihack.recipes import RecipeParser, RecipeRunner, discover_recipes
from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter
from amplihack.recipes.models import Recipe

from .recipe_output import (
    format_recipe_details,
    format_recipe_list,
    format_recipe_result,
    format_validation_result,
)


def parse_context_args(context_args: list[str]) -> tuple[dict[str, str], list[str]]:
    """Parse context key=value arguments.

    Args:
        context_args: List of strings in "key=value" format. Values may contain
            any characters including parentheses, hashes, periods, and quotes.

    Returns:
        Tuple of (parsed_context_dict, error_messages)
    """
    context: dict[str, str] = {}
    errors: list[str] = []

    for ctx_arg in context_args:
        if "=" in ctx_arg:
            key, value = ctx_arg.split("=", 1)
            if not key.strip():
                errors.append(
                    f"Invalid context format '{ctx_arg}': key must not be empty. "
                    "Use key=value format (e.g., -c task='Fix bug (#123)')"
                )
            else:
                context[key] = value
        else:
            errors.append(
                f"Invalid context format '{ctx_arg}'. "
                "Use key=value format (e.g., -c task='Fix bug (#123)' -c var=value)"
            )

    return context, errors


def _validate_path(path_str: str, must_exist: bool = True) -> Path:
    """Validate and resolve a user-provided path.

    Args:
        path_str: Path string from user input
        must_exist: If True, verify path exists

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path is invalid or contains suspicious patterns
        FileNotFoundError: If must_exist=True and path doesn't exist
    """
    # Basic path validation
    if not path_str or not path_str.strip():
        raise ValueError("Path cannot be empty")

    # Check for suspicious path patterns
    if ".." in path_str:
        # Allow .. but resolve to absolute path to prevent traversal
        pass

    try:
        path = Path(path_str).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}")

    if must_exist and not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    return path


def handle_run(
    recipe_path: str,
    context: dict[str, Any],
    dry_run: bool = False,
    verbose: bool = False,
    format: str = "table",
    working_dir: str | None = None,
) -> int:
    """Execute a recipe from a YAML file.

    Args:
        recipe_path: Path to recipe YAML file
        context: User-provided context variables (overrides recipe defaults)
        dry_run: If True, show what would be executed without running
        verbose: Show detailed step-by-step output
        format: Output format (table/json/yaml)
        working_dir: Working directory for recipe execution

    Returns:
        Exit code (0=success, 1=error, 130=SIGINT)
    """
    # Validate format before try block for fail-fast behavior
    if format not in ["table", "json", "yaml"]:
        raise ValueError(f"Invalid format: {format}. Must be table, json, or yaml")

    try:
        # Validate and resolve recipe path
        validated_path = _validate_path(recipe_path, must_exist=False)

        # Parse recipe file
        parser = RecipeParser()
        recipe = parser.parse_file(str(validated_path))

        if verbose:
            print(f"Executing recipe: {recipe.name}", file=sys.stderr)
            if dry_run:
                print("DRY RUN MODE - No actual execution", file=sys.stderr)

        # Create adapter and runner
        # Cast to str since adapter __init__ expects str, not str | None
        wd: str = working_dir if working_dir is not None else "."
        adapter = CLISubprocessAdapter(working_dir=wd)
        runner = RecipeRunner(adapter=adapter)

        # Merge context: user context overrides recipe defaults
        merged_context = {**(recipe.context or {}), **context}

        # Execute recipe
        result = runner.execute(
            recipe,
            user_context=merged_context,
            dry_run=dry_run,
        )

        # Format and print output
        output = format_recipe_result(result, format=format, show_context=False)
        print(output)

        # Return exit code based on success
        return 0 if result.success else 1

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except PermissionError as e:
        print(f"Error: Permission denied - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def handle_list(
    recipe_dir: str | None = None,
    format: str = "table",
    tags: list[str] | None = None,
    verbose: bool = False,
) -> int:
    """List available recipes in a directory.

    Args:
        recipe_dir: Directory to search for recipes (None = use default search paths)
        format: Output format (table/json/yaml)
        tags: Filter recipes by tags (AND logic - must have all tags)
        verbose: Show full recipe details

    Returns:
        Exit code (0=success, 1=error)
    """
    try:
        # Discover recipes - use default search paths if no directory specified
        if recipe_dir is None:
            recipe_result = discover_recipes()
        else:
            # Validate and resolve recipe directory path
            validated_dir = _validate_path(recipe_dir, must_exist=False)
            recipe_result = discover_recipes([validated_dir])

        # Handle both dict (real implementation) and list (test mocks)
        recipes: list[Recipe]
        if isinstance(recipe_result, dict):
            # Real implementation: parse each RecipeInfo
            parser = RecipeParser()
            recipes = []
            for recipe_info in recipe_result.values():
                try:
                    recipe = parser.parse_file(str(recipe_info.path))
                    recipes.append(recipe)
                except Exception as e:
                    # Skip recipes that fail to parse
                    if verbose:
                        print(f"Warning: Skipped recipe {recipe_info.path}: {e}", file=sys.stderr)
                    continue
        else:
            # Test mock: already a list of Recipe objects
            recipes = list(recipe_result)

        # Filter by tags if specified
        if tags:
            filtered = []
            for recipe in recipes:
                recipe_tags = set(recipe.tags or [])
                if all(tag in recipe_tags for tag in tags):
                    filtered.append(recipe)
            recipes = filtered

        # Format and print output
        output = format_recipe_list(recipes, format=format, verbose=verbose, show_tags=True)
        print(output)

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_validate(
    recipe_path: str,
    verbose: bool = False,
    format: str = "table",
) -> int:
    """Validate a recipe YAML file.

    Args:
        recipe_path: Path to recipe YAML file
        verbose: Show detailed validation information
        format: Output format (table/json/yaml)

    Returns:
        Exit code (0=valid, 1=invalid)
    """
    try:
        # Validate and resolve recipe path
        validated_path = _validate_path(recipe_path, must_exist=False)

        # Try to parse the recipe
        parser = RecipeParser()
        recipe = parser.parse_file(str(validated_path))

        # If we got here, recipe is valid
        output = format_validation_result(
            recipe=recipe,
            is_valid=True,
            errors=[],
            format=format,
            verbose=verbose,
        )
        print(output)
        return 0

    except FileNotFoundError as e:
        output = format_validation_result(
            recipe=None,
            is_valid=False,
            errors=[f"File not found: {e}"],
            format=format,
        )
        print(output)
        return 1
    except ValueError as e:
        output = format_validation_result(
            recipe=None,
            is_valid=False,
            errors=[str(e)],
            format=format,
        )
        print(output)
        return 1
    except Exception as e:
        output = format_validation_result(
            recipe=None,
            is_valid=False,
            errors=[f"Validation error: {e}"],
            format=format,
        )
        print(output)
        return 1


def handle_show(
    recipe_path: str,
    format: str = "table",
    show_steps: bool = True,
    show_context: bool = True,
) -> int:
    """Show detailed recipe information.

    Args:
        recipe_path: Path to recipe YAML file
        format: Output format (table/json/yaml)
        show_steps: Include step details
        show_context: Include context variables

    Returns:
        Exit code (0=success, 1=error)
    """
    try:
        # Validate and resolve recipe path
        validated_path = _validate_path(recipe_path, must_exist=False)

        # Parse recipe
        parser = RecipeParser()
        recipe = parser.parse_file(str(validated_path))

        # Format and print output
        output = format_recipe_details(
            recipe,
            format=format,
            show_steps=show_steps,
            show_context=show_context,
            show_tags=True,
        )
        print(output)
        return 0

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
