"""Recipe loading helpers for CLI handlers."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

import yaml

from amplihack.recipes import RecipeParser, discover_recipes, find_recipe
from amplihack.recipes.models import Recipe

from .context import validate_user_path


def _is_bare_recipe_name(recipe_path: str) -> bool:
    """Return True if recipe_path looks like a bare recipe name (not a file path)."""
    return (
        os.sep not in recipe_path
        and (os.altsep is None or os.altsep not in recipe_path)
        and not recipe_path.endswith((".yaml", ".yml"))
    )


def load_recipe_definition(recipe_path: str) -> tuple[Recipe, Path]:
    """Load a recipe definition from disk and return it with its resolved path.

    Supports both file paths (``path/to/recipe.yaml``) and bare recipe names
    (``quality-audit-cycle``).  Bare names are resolved via :func:`find_recipe`
    which searches all known recipe directories.
    """
    if _is_bare_recipe_name(recipe_path):
        resolved = find_recipe(recipe_path)
        if resolved is not None:
            recipe = RecipeParser().parse_file(str(resolved))
            return recipe, resolved

    validated_path = validate_user_path(recipe_path, must_exist=False)
    recipe = RecipeParser().parse_file(str(validated_path))
    return recipe, validated_path


class _RecipeInfoLike(Protocol):
    path: Path


def _parse_discovered_recipes(
    recipe_infos: Iterable[_RecipeInfoLike], *, verbose: bool
) -> list[Recipe]:
    parser = RecipeParser()
    recipes: list[Recipe] = []
    failures: list[str] = []

    for recipe_info in recipe_infos:
        try:
            recipes.append(parser.parse_file(str(recipe_info.path)))
        except (FileNotFoundError, ValueError, yaml.YAMLError) as error:
            failures.append(f"{recipe_info.path}: {error}")

    if failures:
        detail_lines = failures if verbose else failures[:3]
        remaining = len(failures) - len(detail_lines)
        more_suffix = f"\n... and {remaining} more" if remaining > 0 else ""
        print(
            "Warning: Skipped invalid recipe definitions:\n"
            + "\n".join(f"- {detail}" for detail in detail_lines)
            + more_suffix,
            file=sys.stderr,
        )

    return recipes


def discover_recipe_definitions(recipe_dir: str | None, *, verbose: bool = False) -> list[Recipe]:
    """Discover recipe definitions from the default search path or a specific directory."""
    if recipe_dir is None:
        discovered = discover_recipes()
    else:
        validated_dir = validate_user_path(recipe_dir, must_exist=True)
        if not validated_dir.is_dir():
            raise NotADirectoryError(f"Not a directory: {validated_dir}")
        discovered = discover_recipes([validated_dir])

    if isinstance(discovered, dict):
        return _parse_discovered_recipes(discovered.values(), verbose=verbose)

    return list(discovered)


def filter_recipes_by_tags(recipes: list[Recipe], tags: list[str] | None) -> list[Recipe]:
    """Filter recipes using AND semantics for the provided tags."""
    if not tags:
        return recipes

    filtered: list[Recipe] = []
    for recipe in recipes:
        recipe_tags = set(recipe.tags or [])
        if all(tag in recipe_tags for tag in tags):
            filtered.append(recipe)
    return filtered
