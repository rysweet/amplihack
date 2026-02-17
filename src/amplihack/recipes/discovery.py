"""Recipe discovery — find, list, and sync recipe YAML files.

Searches well-known directories for recipe files and provides metadata
about each discovered recipe. Supports tracking upstream recipe bundles.

Search Path Priority
--------------------
Recipes are discovered in a specific priority order (global → local):

1. User home recipes (~/.amplihack/.claude/recipes/) - Global installation
2. Global bundled recipes (amplifier-bundle/recipes/)
3. Global source recipes (src/amplihack/amplifier-bundle/recipes/)
4. Project local recipes (.claude/recipes/)

This ordering ensures that core global recipes are always available first,
preventing ImportError when user directories don't exist. Project-local
recipes can still override globals by name (last path wins).
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_UPSTREAM_REPO = "https://github.com/microsoft/amplifier-bundle-recipes"
_UPSTREAM_BRANCH = "main"

# Directories searched for recipe files, in priority order.
# Later entries override earlier ones when recipes share the same name.
#
# IMPORTANT: Global recipes come first to ensure core recipes are always
# discoverable even in /tmp clones where local directories don't exist.
# This fixes Issue #2381 where Recipe Runner failed in subprocess isolation.
#
# Priority (global → local):
# 1. ~/.amplihack/.claude/recipes/       - User home (global installation)
# 2. amplifier-bundle/recipes/           - Global bundled recipes
# 3. src/amplihack/amplifier-bundle/     - Global source recipes
# 4. .claude/recipes/                    - Project local recipes
_DEFAULT_SEARCH_DIRS: list[Path] = [
    Path.home() / ".amplihack" / ".claude" / "recipes",  # Global - FIRST
    Path("amplifier-bundle") / "recipes",  # Global bundled
    Path("src") / "amplihack" / "amplifier-bundle" / "recipes",  # Global source
    Path(".claude") / "recipes",  # Local - LAST
]


@dataclass
class RecipeInfo:
    """Metadata about a discovered recipe file."""

    name: str
    path: Path
    description: str = ""
    version: str = ""
    step_count: int = 0
    tags: list[str] = field(default_factory=list)
    sha256: str = ""


def discover_recipes(
    search_dirs: list[Path] | None = None,
) -> dict[str, RecipeInfo]:
    """Find all recipe YAML files in the search directories.

    Returns a dict mapping recipe name to RecipeInfo. When the same recipe
    name appears in multiple directories, the last one wins (user recipes
    override bundled ones).

    Debug Logging
    -------------
    When logger is set to DEBUG level, outputs:
    - Each directory searched and whether it exists
    - Each recipe file found and its source directory
    - Total recipe count by directory

    This helps diagnose discovery issues like missing global recipes or
    incorrect search path ordering.

    Args:
        search_dirs: Override the default search directories.

    Returns:
        Dict of recipe name -> RecipeInfo.
    """
    dirs = search_dirs or _DEFAULT_SEARCH_DIRS
    recipes: dict[str, RecipeInfo] = {}

    logger.debug("Searching for recipes in %d directories", len(dirs))
    for search_dir in dirs:
        if not search_dir.is_dir():
            logger.debug("  Skipping non-existent: %s", search_dir)
            continue
        logger.debug("  Scanning: %s", search_dir)
        dir_recipe_count = 0
        for yaml_path in sorted(search_dir.glob("*.yaml")):
            info = _load_recipe_info(yaml_path)
            if info is not None:
                logger.debug("    Found: %s", info.name)
                recipes[info.name] = info
                dir_recipe_count += 1
        logger.debug("  Discovered %d recipes in %s", dir_recipe_count, search_dir)

    if not recipes:
        logger.warning("No recipes discovered! Searched: %s", ", ".join(str(d) for d in dirs))
    else:
        logger.debug("Total recipes discovered: %d", len(recipes))

    return recipes


def list_recipes(search_dirs: list[Path] | None = None) -> list[RecipeInfo]:
    """Return a sorted list of all discovered recipes.

    Args:
        search_dirs: Override the default search directories.

    Returns:
        List of RecipeInfo sorted by name.
    """
    return sorted(discover_recipes(search_dirs).values(), key=lambda r: r.name)


def verify_global_installation() -> dict[str, Any]:
    """Verify that global recipe directories exist and contain recipes.

    Checks the first two search paths (global bundled and source recipes)
    to ensure the amplihack installation includes core recipes. This is
    diagnostic only - does not modify anything.

    Returns:
        Dict with keys:
        - ``global_dirs_exist``: list[bool] for each global directory
        - ``global_recipe_count``: list[int] for recipe count per directory
        - ``has_global_recipes``: bool, True if ANY global dir has recipes
        - ``global_paths_checked``: list[Path] of directories checked

    Example:
        >>> result = verify_global_installation()
        >>> if not result["has_global_recipes"]:
        ...     print("Warning: No global recipes found in installation")
    """
    # Check first two global directories (user home + bundled)
    global_dirs = [
        Path.home() / ".amplihack" / ".claude" / "recipes",
        Path("amplifier-bundle") / "recipes",
    ]

    result = {
        "global_dirs_exist": [],
        "global_recipe_count": [],
        "has_global_recipes": False,
        "global_paths_checked": global_dirs,
    }

    for global_dir in global_dirs:
        exists = global_dir.is_dir()
        result["global_dirs_exist"].append(exists)

        if exists:
            recipe_count = len(list(global_dir.glob("*.yaml")))
            result["global_recipe_count"].append(recipe_count)
            if recipe_count > 0:
                result["has_global_recipes"] = True
        else:
            result["global_recipe_count"].append(0)

    return result


def find_recipe(name: str, search_dirs: list[Path] | None = None) -> Path | None:
    """Find a recipe by name and return its file path.

    Searches for ``{name}.yaml`` in each search directory. Returns the
    first match, or None if not found.

    Args:
        name: Recipe name (without .yaml extension).
        search_dirs: Override the default search directories.

    Returns:
        Path to the recipe file, or None.
    """
    dirs = search_dirs or _DEFAULT_SEARCH_DIRS
    for search_dir in dirs:
        candidate = search_dir / f"{name}.yaml"
        if candidate.is_file():
            return candidate
    return None


def check_upstream_changes(
    local_dir: Path | None = None,
) -> list[dict[str, str]]:
    """Compare local recipe files against their content hashes.

    Returns a list of changes detected. Each change is a dict with keys:
    ``name``, ``status`` (``modified``, ``new``, ``deleted``), ``local_hash``,
    ``stored_hash``.

    This does NOT fetch from the network — it compares local files against
    a stored manifest (``_recipe_manifest.json``) in the same directory.
    Call ``update_manifest()`` after syncing to refresh the baseline.

    Args:
        local_dir: Directory containing recipe YAML files.

    Returns:
        List of change dicts. Empty list means no changes.
    """
    recipe_dir = local_dir or _find_first_recipe_dir()
    if recipe_dir is None:
        return []

    manifest = _load_manifest(recipe_dir)
    changes: list[dict[str, str]] = []

    # Check existing files
    for yaml_path in sorted(recipe_dir.glob("*.yaml")):
        name = yaml_path.stem
        current_hash = _file_hash(yaml_path)
        stored_hash = manifest.get(name, "")

        if not stored_hash:
            changes.append(
                {"name": name, "status": "new", "local_hash": current_hash, "stored_hash": ""}
            )
        elif current_hash != stored_hash:
            changes.append(
                {
                    "name": name,
                    "status": "modified",
                    "local_hash": current_hash,
                    "stored_hash": stored_hash,
                }
            )

    # Check for deleted files
    for name in manifest:
        if not (recipe_dir / f"{name}.yaml").is_file():
            changes.append(
                {"name": name, "status": "deleted", "local_hash": "", "stored_hash": manifest[name]}
            )

    return changes


def sync_upstream(
    repo_url: str = _UPSTREAM_REPO,
    branch: str = _UPSTREAM_BRANCH,
    remote_name: str = "amplifier-recipes",
) -> dict[str, Any]:
    """Check upstream for recipe changes using git fetch and diff.

    Adds upstream as a git remote, fetches latest, and compares the recipes
    directory. Returns what changed without modifying local files.

    Args:
        repo_url: Upstream git repository URL.
        branch: Branch to fetch from.
        remote_name: Name for the git remote.

    Returns:
        Dict with keys: ``has_changes``, ``files_changed``, ``diff_summary``.
    """
    # Add upstream remote if not already present
    remote_name_internal = f"upstream-{remote_name}"
    result = subprocess.run(
        ["git", "remote", "get-url", remote_name_internal],
        capture_output=True,
        timeout=5,
    )
    if result.returncode != 0:
        subprocess.run(
            ["git", "remote", "add", remote_name_internal, repo_url],
            check=True,
            capture_output=True,
            timeout=10,
        )
        logger.info("Added remote '%s' -> %s", remote_name_internal, repo_url)

    # Fetch latest from upstream
    subprocess.run(
        ["git", "fetch", remote_name_internal, branch],
        check=True,
        capture_output=True,
        timeout=60,
    )

    # Check what changed in recipes directories
    diff_result = subprocess.run(
        [
            "git",
            "diff",
            f"{remote_name_internal}/{branch}",
            "--",
            "amplifier-bundle/recipes/",
            "src/amplihack/amplifier-bundle/recipes/",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    has_changes = bool(diff_result.stdout.strip())

    # Get list of changed files
    files_result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{remote_name_internal}/{branch}",
            "--",
            "amplifier-bundle/recipes/",
            "src/amplihack/amplifier-bundle/recipes/",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    files_changed = [f for f in files_result.stdout.strip().split("\n") if f]

    return {
        "has_changes": has_changes,
        "files_changed": files_changed,
        "diff_summary": diff_result.stdout[:500] if has_changes else "No changes",
        "upstream_ref": f"{remote_name_internal}/{branch}",
    }


def update_manifest(local_dir: Path | None = None) -> Path:
    """Write a manifest file recording the current hash of each recipe.

    The manifest is stored as ``_recipe_manifest.json`` in the recipe
    directory. Used by ``check_upstream_changes()`` to detect modifications.

    Args:
        local_dir: Directory containing recipe YAML files.

    Returns:
        Path to the written manifest file.
    """
    recipe_dir = local_dir or _find_first_recipe_dir()
    if recipe_dir is None:
        raise FileNotFoundError("No recipe directory found")

    manifest: dict[str, str] = {}
    for yaml_path in sorted(recipe_dir.glob("*.yaml")):
        manifest[yaml_path.stem] = _file_hash(yaml_path)

    manifest_path = recipe_dir / "_recipe_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    logger.info("Updated recipe manifest at %s (%d recipes)", manifest_path, len(manifest))
    return manifest_path


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _load_recipe_info(yaml_path: Path) -> RecipeInfo | None:
    """Load minimal metadata from a recipe YAML file without full parsing."""
    try:
        text = yaml_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if not isinstance(data, dict) or "name" not in data:
            return None

        steps = data.get("steps", [])
        return RecipeInfo(
            name=data["name"],
            path=yaml_path.resolve(),
            description=data.get("description", ""),
            version=data.get("version", ""),
            step_count=len(steps) if isinstance(steps, list) else 0,
            tags=data.get("tags", []),
            sha256=_file_hash(yaml_path),
        )
    except Exception:
        logger.debug("Failed to load recipe info from %s", yaml_path)
        return None


def _file_hash(path: Path) -> str:
    """Return SHA-256 hex digest of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _load_manifest(recipe_dir: Path) -> dict[str, str]:
    """Load the recipe manifest from a directory, or return empty dict."""
    manifest_path = recipe_dir / "_recipe_manifest.json"
    if manifest_path.is_file():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _find_first_recipe_dir() -> Path | None:
    """Return the first existing recipe directory from the search list."""
    for d in _DEFAULT_SEARCH_DIRS:
        if d.is_dir():
            return d
    return None
