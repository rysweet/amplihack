"""Recipe discovery — find, list, and sync recipe YAML files.

Searches well-known directories for recipe files and provides metadata
about each discovered recipe. Supports tracking upstream recipe bundles.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_UPSTREAM_REPO = "https://github.com/microsoft/amplifier-bundle-recipes"
_UPSTREAM_BRANCH = "main"

# Directories searched for recipe files, in priority order.
# Later entries override earlier ones when recipes share the same name.
_DEFAULT_SEARCH_DIRS: list[Path] = [
    Path("amplifier-bundle") / "recipes",
    Path("src") / "amplihack" / "amplifier-bundle" / "recipes",
    Path.home() / ".amplihack" / ".claude" / "recipes",
    Path(".claude") / "recipes",
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

    Args:
        search_dirs: Override the default search directories.

    Returns:
        Dict of recipe name -> RecipeInfo.
    """
    dirs = search_dirs or _DEFAULT_SEARCH_DIRS
    recipes: dict[str, RecipeInfo] = {}

    for search_dir in dirs:
        if not search_dir.is_dir():
            continue
        for yaml_path in sorted(search_dir.glob("*.yaml")):
            info = _load_recipe_info(yaml_path)
            if info is not None:
                recipes[info.name] = info

    return recipes


def list_recipes(search_dirs: list[Path] | None = None) -> list[RecipeInfo]:
    """Return a sorted list of all discovered recipes.

    Args:
        search_dirs: Override the default search directories.

    Returns:
        List of RecipeInfo sorted by name.
    """
    return sorted(discover_recipes(search_dirs).values(), key=lambda r: r.name)


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
    target_dir: Path | None = None,
    repo_url: str = _UPSTREAM_REPO,
    branch: str = _UPSTREAM_BRANCH,
) -> dict[str, Any]:
    """Fetch recipes from upstream repository and sync to local directory.

    Clones the upstream repo to a temp directory, copies recipe YAML files,
    and updates the manifest. Returns a summary of changes.

    Args:
        target_dir: Local directory to sync recipes into.
        repo_url: Upstream git repository URL.
        branch: Branch to fetch from.

    Returns:
        Dict with keys: ``added``, ``updated``, ``unchanged`` (counts).
    """
    local_dir = target_dir or _find_first_recipe_dir()
    if local_dir is None:
        raise FileNotFoundError("No local recipe directory found")

    # Clone to temp directory
    with tempfile.TemporaryDirectory(prefix="recipe-sync-") as tmpdir:
        tmp_path = Path(tmpdir)
        logger.info("Cloning %s to %s", repo_url, tmp_path)

        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth=1",
                    f"--branch={branch}",
                    repo_url,
                    str(tmp_path / "repo"),
                ],
                check=True,
                capture_output=True,
                timeout=300,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clone upstream: {e.stderr.decode()}") from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("Upstream clone timed out after 5 minutes") from e

        upstream_dir = tmp_path / "repo" / "recipes"
        if not upstream_dir.is_dir():
            raise FileNotFoundError(f"No 'recipes' directory in upstream repo: {repo_url}")

        # Track changes
        added = 0
        updated = 0
        unchanged = 0

        for yaml_path in sorted(upstream_dir.glob("*.yaml")):
            local_path = local_dir / yaml_path.name
            upstream_content = yaml_path.read_bytes()

            if local_path.exists():
                local_content = local_path.read_bytes()
                if local_content != upstream_content:
                    shutil.copy2(yaml_path, local_path)
                    updated += 1
                    logger.info("Updated: %s", yaml_path.name)
                else:
                    unchanged += 1
            else:
                shutil.copy2(yaml_path, local_path)
                added += 1
                logger.info("Added: %s", yaml_path.name)

        # Update manifest after sync
        update_manifest(local_dir)

        return {"added": added, "updated": updated, "unchanged": unchanged}


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
