"""Recipe loading helpers for CLI handlers."""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from amplihack.recipes import RecipeParser, discover_recipes
from amplihack.recipes.models import Recipe

from .context import validate_user_path


def load_recipe_definition(recipe_path: str) -> tuple[Recipe, Path]:
    """Load a recipe definition from disk and return it with its resolved path."""
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

    for recipe_info in recipe_infos:
        try:
            recipes.append(parser.parse_file(str(recipe_info.path)))
        except Exception as error:
            if verbose:
                print(f"Warning: Skipped recipe {recipe_info.path}: {error}", file=sys.stderr)

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
