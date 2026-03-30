"""Recipe discovery — find, list, and sync recipe YAML files.

Searches well-known directories for recipe files and provides metadata
about each discovered recipe. Supports tracking upstream recipe bundles.

Search Path Priority
--------------------
Recipe discovery uses a canonical first-match-wins search policy. The
important invariant is that editable-checkout repo-root recipes beat stale
``src/amplihack/amplifier-bundle/recipes`` copies.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_UPSTREAM_REPO = "https://github.com/microsoft/amplifier-bundle-recipes"
_UPSTREAM_BRANCH = "main"

# Resolve the installed package's bundled recipes directory.
# ``__file__`` is ``<pkg>/recipes/discovery.py``, so ``.parent.parent``
# gives the ``<pkg>/`` root where ``amplifier-bundle/recipes/`` lives.
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_PACKAGE_BUNDLE_DIR = _PACKAGE_DIR / "amplifier-bundle" / "recipes"

# For editable installs (pip install -e), ``_PACKAGE_DIR`` is
# ``src/amplihack/`` and the full bundle may only exist at the repo root's
# ``amplifier-bundle/recipes/``.  We detect this by walking up to the repo root.
_REPO_ROOT_BUNDLE_DIR = _PACKAGE_DIR.parent.parent / "amplifier-bundle" / "recipes"

# AMPLIHACK_HOME env var provides an explicit amplihack root directory.
# Other asset resolution code (resolve_bundle_asset.py, runtime_assets.py)
# already checks this.  Recipe discovery must too, so recipes are found
# when running from a non-amplihack repo with AMPLIHACK_HOME set (#3237).
#
# Security contract:
# - Path is canonicalized via Path(raw).resolve() before use (follows symlinks)
# - .is_dir() check is required — invalid values emit a WARNING log, not an
#   exception and not silent ignore (#3237)
# - _AMPLIHACK_HOME_BUNDLE_DIR is kept for backwards compat with rust_runner.py
_AMPLIHACK_HOME_DIR: Path | None = None
_AMPLIHACK_HOME_BUNDLE_DIR: Path | None = None
_amplihack_home_raw = os.environ.get("AMPLIHACK_HOME")
if _amplihack_home_raw:
    _amplihack_home_resolved = Path(_amplihack_home_raw).resolve()
    if _amplihack_home_resolved.is_dir():
        _AMPLIHACK_HOME_DIR = _amplihack_home_resolved
        _bundle_candidate = _amplihack_home_resolved / "amplifier-bundle" / "recipes"
        if _bundle_candidate.is_dir():
            _AMPLIHACK_HOME_BUNDLE_DIR = _bundle_candidate
        else:
            logger.warning(
                "AMPLIHACK_HOME=%r is set but amplifier-bundle/recipes/ subdir not found "
                "(resolved: %s) — recipes from AMPLIHACK_HOME will not be discovered. "
                "Ensure amplifier-bundle/recipes/ exists inside AMPLIHACK_HOME.",
                _amplihack_home_raw,
                _bundle_candidate,
            )
    else:
        logger.warning(
            "AMPLIHACK_HOME=%r is not a valid directory (resolved: %s) — ignoring. "
            "Set AMPLIHACK_HOME to an existing directory containing your amplihack installation.",
            _amplihack_home_raw,
            _amplihack_home_resolved,
        )


def _canonicalize_recipe_dir(recipe_dir: Path, *, working_dir: Path) -> Path:
    """Resolve *recipe_dir* against *working_dir* and canonicalize the result."""
    candidate = recipe_dir if recipe_dir.is_absolute() else working_dir / recipe_dir
    return candidate.resolve()


def _default_search_dir_candidates(*, working_dir: Path) -> list[Path]:
    """Return default recipe search directories in first-match-wins order."""
    candidates = [
        _REPO_ROOT_BUNDLE_DIR,
        Path("amplifier-bundle") / "recipes",
    ]
    if _AMPLIHACK_HOME_BUNDLE_DIR is not None:
        candidates.append(_AMPLIHACK_HOME_BUNDLE_DIR)
    candidates.extend(
        [
            Path.home() / ".amplihack" / ".claude" / "recipes",
            _PACKAGE_BUNDLE_DIR,
            Path("src") / "amplihack" / "amplifier-bundle" / "recipes",
            Path(".claude") / "recipes",
        ]
    )
    return [_canonicalize_recipe_dir(candidate, working_dir=working_dir) for candidate in candidates]


def get_recipe_search_dirs(
    search_dirs: list[Path] | None = None,
    *,
    working_dir: str | Path = ".",
) -> list[Path]:
    """Return canonical recipe search directories with stable precedence."""
    base_dir = Path(working_dir).resolve()
    raw_dirs = (
        [_canonicalize_recipe_dir(Path(directory), working_dir=base_dir) for directory in search_dirs]
        if search_dirs is not None
        else _default_search_dir_candidates(working_dir=base_dir)
    )

    seen: set[Path] = set()
    canonical_dirs: list[Path] = []
    for directory in raw_dirs:
        if directory in seen:
            continue
        seen.add(directory)
        canonical_dirs.append(directory)
    return canonical_dirs


_DEFAULT_SEARCH_DIRS: list[Path] = get_recipe_search_dirs()


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


@dataclass
class _RecipeInfoCacheEntry:
    """Cached recipe metadata keyed by stable file metadata."""

    mtime_ns: int
    size: int
    info: RecipeInfo


_RECIPE_INFO_CACHE: dict[Path, _RecipeInfoCacheEntry] = {}


def _clone_recipe_info(info: RecipeInfo) -> RecipeInfo:
    """Return a detached copy so callers cannot mutate cached metadata."""
    return RecipeInfo(
        name=info.name,
        path=info.path,
        description=info.description,
        version=info.version,
        step_count=info.step_count,
        tags=list(info.tags),
        sha256=info.sha256,
    )


def discover_recipes(
    search_dirs: list[Path] | None = None,
) -> dict[str, RecipeInfo]:
    """Find all recipe YAML files in the search directories.

    Returns a dict mapping recipe name to RecipeInfo. When the same recipe
    name appears in multiple directories, the first matching directory wins.

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
    dirs = get_recipe_search_dirs(search_dirs)
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
                if info.name in recipes:
                    logger.debug("    Skipping shadowed recipe: %s", info.name)
                    continue
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
    # Check first two global directories under the user's home — both paths
    # derive from Path.home() so tests can reliably mock the home directory.
    global_dirs = [
        Path.home() / ".amplihack" / ".claude" / "recipes",
        Path.home() / ".amplihack" / "amplifier-bundle" / "recipes",
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

    Searches for ``{name}.yaml`` in each search directory. When multiple
    directories contain the same recipe name, the first matching path wins
    so resolution stays consistent with ``discover_recipes()``.

    Args:
        name: Recipe name (without .yaml extension).
        search_dirs: Override the default search directories.

    Returns:
        Path to the recipe file, or None.
    """
    for search_dir in get_recipe_search_dirs(search_dirs):
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
    resolved_path = yaml_path.resolve()
    try:
        stat = resolved_path.stat()
        cached = _RECIPE_INFO_CACHE.get(resolved_path)
        if cached is not None and cached.mtime_ns == stat.st_mtime_ns and cached.size == stat.st_size:
            return _clone_recipe_info(cached.info)

        content = resolved_path.read_bytes()
        data = yaml.safe_load(content)
        if not isinstance(data, dict) or "name" not in data:
            return None

        steps = data.get("steps", [])
        raw_tags = data.get("tags", [])
        info = RecipeInfo(
            name=data["name"],
            path=resolved_path,
            description=data.get("description", ""),
            version=data.get("version", ""),
            step_count=len(steps) if isinstance(steps, list) else 0,
            tags=list(raw_tags) if isinstance(raw_tags, list) else [],
            sha256=_short_sha256_bytes(content),
        )
        _RECIPE_INFO_CACHE[resolved_path] = _RecipeInfoCacheEntry(
            mtime_ns=stat.st_mtime_ns,
            size=stat.st_size,
            info=_clone_recipe_info(info),
        )
        return info
    except Exception:
        logger.debug("Failed to load recipe info from %s", resolved_path)
        return None


def _short_sha256_bytes(content: bytes) -> str:
    """Return the short SHA-256 digest for in-memory file contents."""
    return hashlib.sha256(content).hexdigest()[:16]


def _file_hash(path: Path) -> str:
    """Return SHA-256 hex digest of a file's contents."""
    return _short_sha256_bytes(path.read_bytes())


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
    for d in get_recipe_search_dirs():
        if d.is_dir():
            return d
    return None
