"""Recipe directory normalization and target resolution helpers for the Rust runner."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _default_package_recipe_dirs(*, working_dir: str = ".") -> list[str]:
    """Return bundled recipe directories visible to Python discovery."""
    try:
        from amplihack.recipes.discovery import get_recipe_search_dirs

        dirs = [
            str(candidate)
            for candidate in get_recipe_search_dirs(working_dir=working_dir)
            if candidate.is_dir()
        ]
        if dirs:
            return dirs
    except Exception as error:
        logger.debug("Could not resolve default recipe dirs: %s", error)
    return []


def _normalize_recipe_dirs(recipe_dirs: list[str] | None, *, working_dir: str) -> list[str] | None:
    """Return absolute recipe directories rooted at ``working_dir`` when needed."""
    if recipe_dirs is None:
        return None

    from amplihack.recipes.discovery import get_recipe_search_dirs

    return [str(candidate) for candidate in get_recipe_search_dirs([Path(d) for d in recipe_dirs], working_dir=working_dir)]


def _resolve_recipe_target(
    name: str,
    *,
    recipe_dirs: list[str] | None,
    working_dir: str,
) -> str:
    """Resolve a recipe name to a concrete YAML path when Python discovery can find it."""
    working_path = Path(working_dir).resolve()
    candidate = Path(name)

    if candidate.is_absolute():
        return str(candidate.resolve())

    if candidate.suffix in {".yaml", ".yml"} or os.sep in name or (os.altsep and os.altsep in name):
        return str((working_path / candidate).resolve())

    try:
        from amplihack.recipes.discovery import find_recipe, get_recipe_search_dirs

        search_dirs = (
            get_recipe_search_dirs([Path(directory) for directory in recipe_dirs], working_dir=working_dir)
            if recipe_dirs
            else None
        )
        resolved = find_recipe(name, search_dirs=search_dirs)
        if resolved is not None:
            return str(resolved.resolve())
    except Exception as error:
        logger.debug("Could not resolve recipe path for %s: %s", name, error)

    return name
