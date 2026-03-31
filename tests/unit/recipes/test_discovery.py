"""Tests for recipe discovery, listing, and upstream tracking."""

from __future__ import annotations

from pathlib import Path

from amplihack.recipes.discovery import (
    RecipeCache,
    _PACKAGE_BUNDLE_DIR,
    _qualified_key,
    check_upstream_changes,
    discover_recipes,
    find_recipe,
    list_recipes,
    update_manifest,
)
from amplihack.recipes.parser import RecipeParser


class TestDiscoverRecipes:
    """Test recipe auto-discovery from search directories."""

    def test_discovers_bundled_recipes(self) -> None:
        """Finds all 10 recipes from amplifier-bundle/recipes/."""
        recipes = discover_recipes()
        assert len(recipes) >= 10, f"Expected >=10 recipes, got {len(recipes)}"
        assert "default-workflow" in recipes
        assert "verification-workflow" in recipes

    def test_recipe_info_has_metadata(self) -> None:
        """Discovered recipes include name, path, description, step count."""
        recipes = discover_recipes()
        info = recipes["default-workflow"]
        assert info.name == "default-workflow"
        assert info.path.exists()
        assert info.step_count > 0
        assert info.sha256  # non-empty hash

    def test_discovers_from_installed_package_path(self, tmp_path: Path) -> None:
        """Discovers bundled recipes even when CWD has no recipe dirs (fix #2812)."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            recipes = discover_recipes()
            assert len(recipes) >= 10, (
                f"Expected >=10 recipes from installed package, got {len(recipes)}. "
                "Recipe discovery must include the installed package bundle path."
            )
            assert "smart-orchestrator" in recipes
            assert "default-workflow" in recipes
        finally:
            os.chdir(original_cwd)

    def test_package_bundle_dir_is_absolute(self) -> None:
        """_PACKAGE_BUNDLE_DIR is an absolute path to the installed package."""
        assert _PACKAGE_BUNDLE_DIR.is_absolute(), (
            f"Expected absolute path, got: {_PACKAGE_BUNDLE_DIR}"
        )


class TestListRecipes:
    """Test the list_recipes convenience function."""

    def test_returns_sorted_list(self) -> None:
        """list_recipes returns a sorted list of RecipeInfo objects."""
        recipes = list_recipes()
        assert len(recipes) >= 10
        names = [r.name for r in recipes]
        assert names == sorted(names), "list should be sorted by name"

    def test_all_recipes_are_parseable(self) -> None:
        """Every discovered recipe can be parsed by RecipeParser."""
        parser = RecipeParser()
        for info in list_recipes():
            recipe = parser.parse_file(info.path)
            assert recipe.name == info.name


class TestFindRecipe:
    """Test finding a specific recipe by name."""

    def test_finds_existing_recipe(self) -> None:
        """find_recipe returns a path for a known recipe."""
        path = find_recipe("verification-workflow")
        assert path is not None
        assert path.is_file()
        assert path.name == "verification-workflow.yaml"

    def test_returns_none_for_missing(self) -> None:
        """find_recipe returns None for a non-existent recipe."""
        assert find_recipe("this-recipe-does-not-exist-12345") is None

    def test_later_search_dir_overrides_earlier_match(self, tmp_path: Path) -> None:
        """find_recipe should mirror discover_recipes() last-path-wins precedence."""
        early = tmp_path / "early"
        late = tmp_path / "late"
        early.mkdir()
        late.mkdir()

        (early / "shadowed.yaml").write_text("name: shadowed\ndescription: early\nsteps: []\n")
        (late / "shadowed.yaml").write_text("name: shadowed\ndescription: late\nsteps: []\n")

        path = find_recipe("shadowed", [early, late])

        assert path == late / "shadowed.yaml"


class TestParseFile:
    """Test RecipeParser.parse_file method."""

    def test_parse_file_works(self) -> None:
        """parse_file loads and parses a recipe from disk."""
        path = find_recipe("verification-workflow")
        assert path is not None
        parser = RecipeParser()
        recipe = parser.parse_file(path)
        assert recipe.name == "verification-workflow"
        assert len(recipe.steps) >= 5

    def test_parse_file_missing_raises(self, tmp_path: Path) -> None:
        """parse_file raises FileNotFoundError for missing files."""
        parser = RecipeParser()
        import pytest

        with pytest.raises(FileNotFoundError):
            parser.parse_file(tmp_path / "nonexistent.yaml")


class TestUpstreamTracking:
    """Test manifest-based upstream change detection."""

    def test_update_and_check_manifest(self) -> None:
        """update_manifest creates a manifest; check finds no changes."""
        path = find_recipe("verification-workflow")
        assert path is not None
        recipe_dir = path.parent

        # Create baseline manifest
        manifest_path = update_manifest(recipe_dir)
        assert manifest_path.exists()
        assert manifest_path.name == "_recipe_manifest.json"

        # No changes expected immediately after manifest creation
        changes = check_upstream_changes(recipe_dir)
        assert changes == [], f"Expected no changes, got: {changes}"

    def test_detects_modification(self, tmp_path: Path) -> None:
        """Detects when a recipe file changes after manifest was created."""
        # Create a test recipe
        recipe_file = tmp_path / "test-recipe.yaml"
        recipe_file.write_text(
            "name: test-recipe\nsteps:\n  - id: s1\n    type: bash\n    command: echo hi\n"
        )

        # Create manifest
        update_manifest(tmp_path)

        # Modify the recipe
        recipe_file.write_text(
            "name: test-recipe\nsteps:\n  - id: s1\n    type: bash\n    command: echo modified\n"
        )

        # Should detect the change
        changes = check_upstream_changes(tmp_path)
        assert len(changes) == 1
        assert changes[0]["name"] == "test-recipe"
        assert changes[0]["status"] == "modified"


class TestRecipeCacheAliasing:
    """Tests for #3808: same-name recipes from different dirs must not alias."""

    _RECIPE_YAML = "name: {name}\ndescription: from {origin}\nsteps: []\n"

    def _make_recipe(self, directory: Path, name: str, origin: str) -> Path:
        """Create a minimal recipe YAML in *directory*."""
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{name}.yaml"
        path.write_text(self._RECIPE_YAML.format(name=name, origin=origin))
        return path

    def test_same_name_recipes_coexist(self, tmp_path: Path) -> None:
        """Two recipes with the same name in different dirs are both discoverable."""
        dir_a = tmp_path / "dir_a"
        dir_b = tmp_path / "dir_b"
        self._make_recipe(dir_a, "shared", "dir_a")
        self._make_recipe(dir_b, "shared", "dir_b")

        recipes = discover_recipes([dir_a, dir_b])

        # Both qualified keys must exist
        qkey_a = _qualified_key(dir_a.resolve(), "shared")
        qkey_b = _qualified_key(dir_b.resolve(), "shared")
        assert qkey_a in recipes, f"Missing qualified key for dir_a: {qkey_a}"
        assert qkey_b in recipes, f"Missing qualified key for dir_b: {qkey_b}"

        # They must be different RecipeInfo objects (different paths)
        assert recipes[qkey_a].path != recipes[qkey_b].path

        # Descriptions confirm they came from the right directories
        assert recipes[qkey_a].description == "from dir_a"
        assert recipes[qkey_b].description == "from dir_b"

    def test_bare_name_returns_last_wins(self, tmp_path: Path) -> None:
        """Bare-name lookup returns the recipe from the last search directory."""
        dir_a = tmp_path / "dir_a"
        dir_b = tmp_path / "dir_b"
        self._make_recipe(dir_a, "shared", "dir_a")
        self._make_recipe(dir_b, "shared", "dir_b")

        recipes = discover_recipes([dir_a, dir_b])

        # Bare-name lookup must resolve to dir_b (last wins)
        assert "shared" in recipes
        assert recipes["shared"].description == "from dir_b"
        assert recipes["shared"].path == (dir_b / "shared.yaml").resolve()

    def test_qualified_key_returns_specific_recipe(self, tmp_path: Path) -> None:
        """Qualified key returns the exact recipe from a specific directory."""
        dir_a = tmp_path / "dir_a"
        dir_b = tmp_path / "dir_b"
        self._make_recipe(dir_a, "shared", "dir_a")
        self._make_recipe(dir_b, "shared", "dir_b")

        recipes = discover_recipes([dir_a, dir_b])

        qkey_a = _qualified_key(dir_a.resolve(), "shared")
        info_a = recipes[qkey_a]
        assert info_a.description == "from dir_a"
        assert info_a.path == (dir_a / "shared.yaml").resolve()

    def test_values_not_duplicated(self, tmp_path: Path) -> None:
        """values() returns each unique recipe exactly once (no bare-name dupes)."""
        dir_a = tmp_path / "dir_a"
        dir_b = tmp_path / "dir_b"
        self._make_recipe(dir_a, "shared", "dir_a")
        self._make_recipe(dir_b, "shared", "dir_b")
        self._make_recipe(dir_a, "unique_a", "dir_a")

        recipes = discover_recipes([dir_a, dir_b])
        paths = [info.path for info in recipes.values()]

        # No duplicate paths in values()
        assert len(paths) == len(set(paths)), f"Duplicate values: {paths}"
        # Must contain all 3 recipes
        assert len(paths) == 3

    def test_list_recipes_deduplicates(self, tmp_path: Path) -> None:
        """list_recipes returns each recipe once even with overlapping dirs."""
        dir_a = tmp_path / "dir_a"
        dir_b = tmp_path / "dir_b"
        self._make_recipe(dir_a, "shared", "dir_a")
        self._make_recipe(dir_b, "shared", "dir_b")
        self._make_recipe(dir_a, "unique_a", "dir_a")

        result = list_recipes([dir_a, dir_b])
        names = [r.name for r in result]

        # "shared" appears twice (two distinct paths) + "unique_a"
        assert len(result) == 3
        assert names.count("shared") == 2
        assert "unique_a" in names

    def test_find_recipe_qualified_lookup(self, tmp_path: Path) -> None:
        """find_recipe with qualified name returns the specific directory's recipe."""
        dir_a = tmp_path / "dir_a"
        dir_b = tmp_path / "dir_b"
        self._make_recipe(dir_a, "shared", "dir_a")
        self._make_recipe(dir_b, "shared", "dir_b")

        qname = f"{dir_a.resolve()}:shared"
        path = find_recipe(qname)
        assert path is not None
        assert path == dir_a / "shared.yaml"

    def test_find_recipe_bare_name_last_wins(self, tmp_path: Path) -> None:
        """find_recipe with bare name returns the last-wins match."""
        dir_a = tmp_path / "dir_a"
        dir_b = tmp_path / "dir_b"
        self._make_recipe(dir_a, "shared", "dir_a")
        self._make_recipe(dir_b, "shared", "dir_b")

        path = find_recipe("shared", [dir_a, dir_b])
        assert path == dir_b / "shared.yaml"

    def test_recipe_cache_is_dict_subclass(self) -> None:
        """RecipeCache is a dict subclass for backward compatibility."""
        cache = RecipeCache()
        assert isinstance(cache, dict)

    def test_existing_bare_name_lookups_still_work(self) -> None:
        """Existing bare-name lookups on bundled recipes still work (backward compat)."""
        recipes = discover_recipes()
        assert len(recipes) >= 10
        assert "default-workflow" in recipes
        assert "verification-workflow" in recipes
        assert recipes["default-workflow"].name == "default-workflow"
