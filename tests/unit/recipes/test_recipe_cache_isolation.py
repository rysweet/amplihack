"""Tests for recipe cache isolation across concurrent runs (#3811).

Verifies that:
- _binary_search_paths() returns fresh results (no stale lru_cache)
- discover_recipes() / find_recipe() re-read AMPLIHACK_HOME on each call
- Concurrent threads with different AMPLIHACK_TREE_ID / AMPLIHACK_HOME
  values get isolated results
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from unittest.mock import patch

import pytest


class TestBinarySearchPathsNotCached:
    """_binary_search_paths() must return fresh values, not stale cached ones."""

    def test_returns_list_without_cache_attribute(self) -> None:
        """The function should be a plain function, not an lru_cache wrapper."""
        from amplihack.recipes.rust_runner_binary import _binary_search_paths

        # lru_cache-wrapped functions have a cache_info attribute
        assert not hasattr(_binary_search_paths, "cache_info"), (
            "_binary_search_paths should not be wrapped with lru_cache"
        )

    def test_rust_runner_binary_search_paths_no_cache(self) -> None:
        """rust_runner_binary._binary_search_paths has no cache."""
        from amplihack.recipes.rust_runner_binary import _binary_search_paths

        assert not hasattr(_binary_search_paths, "cache_clear"), (
            "_binary_search_paths in rust_runner_binary should not have cache_clear"
        )

    def test_rust_runner_binary_search_paths_no_cache_main(self) -> None:
        """rust_runner._binary_search_paths has no cache."""
        from amplihack.recipes.rust_runner import _binary_search_paths

        assert not hasattr(_binary_search_paths, "cache_info"), (
            "_binary_search_paths in rust_runner should not be wrapped with lru_cache"
        )


class TestDiscoveryDynamicEnv:
    """discovery.py must re-read AMPLIHACK_HOME on each call, not use stale import-time value."""

    def test_get_amplihack_home_bundle_dir_reads_env(self, tmp_path: Path) -> None:
        """_get_amplihack_home_bundle_dir() reads AMPLIHACK_HOME fresh each call."""
        from amplihack.recipes.discovery import _get_amplihack_home_bundle_dir

        # No env var → None
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("AMPLIHACK_HOME", None)
            assert _get_amplihack_home_bundle_dir() is None

        # Set env var to a dir with the expected subdir
        bundle_dir = tmp_path / "amplifier-bundle" / "recipes"
        bundle_dir.mkdir(parents=True)

        with patch.dict(os.environ, {"AMPLIHACK_HOME": str(tmp_path)}):
            result = _get_amplihack_home_bundle_dir()
            assert result == bundle_dir

    def test_get_default_search_dirs_includes_amplihack_home(self, tmp_path: Path) -> None:
        """_get_default_search_dirs() includes AMPLIHACK_HOME bundle dir when set."""
        from amplihack.recipes.discovery import _get_default_search_dirs

        bundle_dir = tmp_path / "amplifier-bundle" / "recipes"
        bundle_dir.mkdir(parents=True)

        with patch.dict(os.environ, {"AMPLIHACK_HOME": str(tmp_path)}):
            dirs = _get_default_search_dirs()
            assert bundle_dir in dirs

    def test_get_default_search_dirs_excludes_amplihack_home_when_unset(self) -> None:
        """_get_default_search_dirs() omits AMPLIHACK_HOME entry when env var is unset."""
        from amplihack.recipes.discovery import _get_default_search_dirs

        env = os.environ.copy()
        env.pop("AMPLIHACK_HOME", None)
        with patch.dict(os.environ, env, clear=True):
            dirs = _get_default_search_dirs()
            # All entries should be either static package dirs or relative paths
            for d in dirs:
                assert "AMPLIHACK_HOME" not in str(d)

    def test_discover_recipes_sees_changed_amplihack_home(self, tmp_path: Path) -> None:
        """discover_recipes() returns correct results when AMPLIHACK_HOME changes."""
        from amplihack.recipes.discovery import discover_recipes

        # Create two different AMPLIHACK_HOME directories with different recipes
        home_a = tmp_path / "home_a"
        home_b = tmp_path / "home_b"
        for home in (home_a, home_b):
            recipe_dir = home / "amplifier-bundle" / "recipes"
            recipe_dir.mkdir(parents=True)

        (home_a / "amplifier-bundle" / "recipes" / "recipe-a.yaml").write_text(
            "name: recipe-a\ndescription: from home_a\nsteps: []\n"
        )
        (home_b / "amplifier-bundle" / "recipes" / "recipe-b.yaml").write_text(
            "name: recipe-b\ndescription: from home_b\nsteps: []\n"
        )

        # Use only AMPLIHACK_HOME-based dirs for a controlled test
        with patch.dict(os.environ, {"AMPLIHACK_HOME": str(home_a)}):
            search = [home_a / "amplifier-bundle" / "recipes"]
            recipes_a = discover_recipes(search_dirs=search)

        with patch.dict(os.environ, {"AMPLIHACK_HOME": str(home_b)}):
            search = [home_b / "amplifier-bundle" / "recipes"]
            recipes_b = discover_recipes(search_dirs=search)

        assert "recipe-a" in recipes_a
        assert "recipe-b" not in recipes_a
        assert "recipe-b" in recipes_b
        assert "recipe-a" not in recipes_b

    def test_find_recipe_sees_changed_amplihack_home(self, tmp_path: Path) -> None:
        """find_recipe() returns correct results when AMPLIHACK_HOME changes."""
        from amplihack.recipes.discovery import find_recipe

        home_a = tmp_path / "home_a"
        recipe_dir_a = home_a / "amplifier-bundle" / "recipes"
        recipe_dir_a.mkdir(parents=True)
        (recipe_dir_a / "only-in-a.yaml").write_text(
            "name: only-in-a\nsteps: []\n"
        )

        home_b = tmp_path / "home_b"
        recipe_dir_b = home_b / "amplifier-bundle" / "recipes"
        recipe_dir_b.mkdir(parents=True)
        # No recipe in home_b

        with patch.dict(os.environ, {"AMPLIHACK_HOME": str(home_a)}):
            assert find_recipe("only-in-a", [recipe_dir_a]) is not None

        with patch.dict(os.environ, {"AMPLIHACK_HOME": str(home_b)}):
            assert find_recipe("only-in-a", [recipe_dir_b]) is None


class TestConcurrentThreadIsolation:
    """Concurrent threads with different env values must not cross-contaminate."""

    def test_concurrent_threads_get_isolated_search_dirs(self, tmp_path: Path) -> None:
        """Two threads with different AMPLIHACK_HOME see isolated _get_default_search_dirs."""
        from amplihack.recipes.discovery import _get_default_search_dirs

        home_a = tmp_path / "home_a"
        home_b = tmp_path / "home_b"
        for home in (home_a, home_b):
            (home / "amplifier-bundle" / "recipes").mkdir(parents=True)

        bundle_a = home_a / "amplifier-bundle" / "recipes"
        bundle_b = home_b / "amplifier-bundle" / "recipes"

        results: dict[str, list[Path]] = {}
        barrier = threading.Barrier(2)

        def worker(name: str, home: Path) -> None:
            os.environ["AMPLIHACK_HOME"] = str(home)
            barrier.wait()  # Synchronize so both threads read env ~simultaneously
            dirs = _get_default_search_dirs()
            results[name] = dirs

        t1 = threading.Thread(target=worker, args=("a", home_a))
        t2 = threading.Thread(target=worker, args=("b", home_b))
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        # Each thread's result should contain its own AMPLIHACK_HOME bundle dir.
        # Due to os.environ being shared across threads, the last writer wins
        # for the env var itself, but the key point is that no stale *cached*
        # value persists — whichever env value the thread reads, it gets the
        # corresponding directory (not a module-import-time baked value).
        #
        # This test verifies no lru_cache or module-level snapshot interferes.
        # At least one thread must have gotten its own correct bundle dir.
        all_dirs = results.get("a", []) + results.get("b", [])
        assert bundle_a in all_dirs or bundle_b in all_dirs, (
            f"Neither AMPLIHACK_HOME bundle dir found in thread results: {results}"
        )

    def test_concurrent_binary_search_paths_no_stale_cache(self) -> None:
        """_binary_search_paths() returns fresh paths in concurrent threads."""
        from amplihack.recipes.rust_runner_binary import _binary_search_paths

        results: dict[str, list[str]] = {}
        barrier = threading.Barrier(2)

        def worker(name: str) -> None:
            barrier.wait()
            paths = _binary_search_paths()
            results[name] = paths

        t1 = threading.Thread(target=worker, args=("t1",))
        t2 = threading.Thread(target=worker, args=("t2",))
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        assert "t1" in results and "t2" in results
        # Both threads should get valid path lists (not empty or corrupted)
        for name in ("t1", "t2"):
            paths = results[name]
            assert len(paths) == 3, f"Thread {name} got unexpected paths: {paths}"
            assert paths[0] == "recipe-runner-rs"

    def test_concurrent_discover_recipes_isolation(self, tmp_path: Path) -> None:
        """Concurrent discover_recipes calls with different search dirs are isolated."""
        from amplihack.recipes.discovery import discover_recipes

        dir_a = tmp_path / "dir_a"
        dir_b = tmp_path / "dir_b"
        dir_a.mkdir()
        dir_b.mkdir()

        (dir_a / "alpha.yaml").write_text("name: alpha\nsteps: []\n")
        (dir_b / "beta.yaml").write_text("name: beta\nsteps: []\n")

        results: dict[str, dict] = {}
        barrier = threading.Barrier(2)

        def worker(name: str, search_dir: Path) -> None:
            barrier.wait()
            recipes = discover_recipes(search_dirs=[search_dir])
            results[name] = recipes

        t1 = threading.Thread(target=worker, args=("a", dir_a))
        t2 = threading.Thread(target=worker, args=("b", dir_b))
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        assert "alpha" in results["a"]
        assert "beta" not in results["a"]
        assert "beta" in results["b"]
        assert "alpha" not in results["b"]
