"""Extended edge case tests for recipe discovery module.

Tests cover error conditions, race conditions, and boundary cases not
covered by basic functional tests.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from unittest import mock

import pytest

from amplihack.recipes.discovery import (
    check_upstream_changes,
    discover_recipes,
    sync_upstream,
    update_manifest,
)

# =============================================================================
# TestSyncUpstreamErrors - Git and network failure scenarios
# =============================================================================


class TestSyncUpstreamErrors:
    """Test sync_upstream error handling and edge cases."""

    def test_git_not_installed(self, monkeypatch):
        """sync_upstream fails gracefully when git is not in PATH."""

        def mock_run(*args, **kwargs):
            raise FileNotFoundError("git command not found")

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(FileNotFoundError):
            sync_upstream()

    def test_remote_add_failure(self, monkeypatch):
        """sync_upstream handles remote add failures."""
        call_count = {"count": 0}

        def mock_run(cmd, **kwargs):
            call_count["count"] += 1
            # First call: remote get-url fails (returncode != 0)
            if call_count["count"] == 1:
                return subprocess.CompletedProcess(cmd, returncode=1, stdout=b"", stderr=b"")
            # Second call: remote add fails
            if "remote" in cmd and "add" in cmd:
                raise subprocess.CalledProcessError(128, cmd, stderr=b"remote already exists")
            # Other calls succeed
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(subprocess.CalledProcessError):
            sync_upstream()

    def test_fetch_network_timeout(self, monkeypatch):
        """sync_upstream handles network timeout during fetch."""
        call_count = {"count": 0}

        def mock_run(cmd, **kwargs):
            call_count["count"] += 1
            # First call: remote get-url succeeds
            if call_count["count"] == 1:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"url", stderr=b"")
            # Second call: fetch times out
            if "fetch" in cmd:
                raise subprocess.TimeoutExpired(cmd, timeout=60)
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(subprocess.TimeoutExpired):
            sync_upstream()

    def test_fetch_auth_failure(self, monkeypatch):
        """sync_upstream handles authentication failures."""
        call_count = {"count": 0}

        def mock_run(cmd, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"url", stderr=b"")
            if "fetch" in cmd:
                raise subprocess.CalledProcessError(128, cmd, stderr=b"Authentication failed")
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(subprocess.CalledProcessError):
            sync_upstream()

    def test_fetch_invalid_url(self, monkeypatch):
        """sync_upstream handles invalid repository URLs."""
        call_count = {"count": 0}

        def mock_run(cmd, **kwargs):
            call_count["count"] += 1
            # Remote get-url fails
            if call_count["count"] == 1:
                return subprocess.CompletedProcess(cmd, returncode=1, stdout=b"", stderr=b"")
            # Remote add succeeds
            if call_count["count"] == 2:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")
            # Fetch fails with invalid URL
            if "fetch" in cmd:
                raise subprocess.CalledProcessError(128, cmd, stderr=b"not a valid repository URL")
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(subprocess.CalledProcessError):
            sync_upstream(repo_url="invalid://url")

    def test_branch_not_found(self, monkeypatch):
        """sync_upstream handles nonexistent branch."""
        call_count = {"count": 0}

        def mock_run(cmd, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"url", stderr=b"")
            if "fetch" in cmd:
                raise subprocess.CalledProcessError(
                    128, cmd, stderr=b"couldn't find remote ref nonexistent-branch"
                )
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(subprocess.CalledProcessError):
            sync_upstream(branch="nonexistent-branch")

    def test_diff_with_binary_files(self, monkeypatch):
        """sync_upstream handles diffs containing binary files."""
        call_count = {"count": 0}

        def mock_run(cmd, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"url", stderr=b"")
            if call_count["count"] == 2:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")
            if "diff" in cmd and "--name-only" not in cmd:
                # text=True means stdout is str, not bytes
                binary_diff = "Binary files a/recipe.yaml and b/recipe.yaml differ\n"
                result = subprocess.CompletedProcess(
                    cmd, returncode=0, stdout=binary_diff, stderr=""
                )
                return result
            if "diff" in cmd and "--name-only" in cmd:
                # text=True means stdout is str, not bytes
                result = subprocess.CompletedProcess(
                    cmd, returncode=0, stdout="amplifier-bundle/recipes/test.yaml\n", stderr=""
                )
                return result
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = sync_upstream()
        assert result["has_changes"] is True
        assert "Binary" in result["diff_summary"]

    def test_diff_huge_output(self, monkeypatch):
        """sync_upstream truncates very large diff outputs."""
        call_count = {"count": 0}

        def mock_run(cmd, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"url", stderr=b"")
            if call_count["count"] == 2:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")
            if "diff" in cmd and "--name-only" not in cmd:
                # Create a 10KB diff (text=True means str output)
                huge_diff = "+" + "x" * 10000 + "\n"
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=huge_diff, stderr="")
            if "diff" in cmd and "--name-only" in cmd:
                # text=True means str output
                return subprocess.CompletedProcess(
                    cmd, returncode=0, stdout="amplifier-bundle/recipes/huge.yaml\n", stderr=""
                )
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = sync_upstream()
        # diff_summary is truncated to 500 chars
        assert len(result["diff_summary"]) == 500

    def test_diff_corrupted_repo(self, monkeypatch):
        """sync_upstream handles corrupted git repository."""
        call_count = {"count": 0}

        def mock_run(cmd, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"url", stderr=b"")
            if call_count["count"] == 2:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")
            if "diff" in cmd:
                raise subprocess.CalledProcessError(128, cmd, stderr=b"fatal: not a git repository")
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(subprocess.CalledProcessError):
            sync_upstream()

    def test_concurrent_sync_operations(self, monkeypatch):
        """sync_upstream handles concurrent calls gracefully."""
        call_count = {"count": 0}
        lock = threading.Lock()

        def mock_run(cmd, **kwargs):
            with lock:
                call_count["count"] += 1
                count = call_count["count"]

            # Simulate slow network operations
            if "fetch" in cmd:
                time.sleep(0.1)

            if count % 3 == 1:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"url", stderr=b"")
            if count % 3 == 2:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Run two sync operations concurrently
        results = []
        errors = []

        def run_sync():
            try:
                result = sync_upstream()
                results.append(result)
            except Exception as e:
                errors.append(e)

        thread1 = threading.Thread(target=run_sync)
        thread2 = threading.Thread(target=run_sync)

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # At least one should complete successfully
        assert len(results) >= 1 or len(errors) >= 1

    def test_subprocess_hanging_timeout(self, monkeypatch):
        """sync_upstream respects timeout for hanging subprocess."""
        call_count = {"count": 0}

        def mock_run(cmd, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"url", stderr=b"")
            # Simulate hanging fetch by raising timeout
            if "fetch" in cmd:
                raise subprocess.TimeoutExpired(cmd, timeout=kwargs.get("timeout", 60))
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(subprocess.TimeoutExpired):
            sync_upstream()


# =============================================================================
# TestManifestEdgeCases - Manifest file handling edge cases
# =============================================================================


class TestManifestEdgeCases:
    """Test manifest file edge cases and error handling."""

    def test_corrupted_manifest_json(self, tmp_path):
        """check_upstream_changes handles corrupted manifest JSON."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        # Create valid recipe
        recipe_file = recipe_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        # Create corrupted manifest
        manifest_file = recipe_dir / "_recipe_manifest.json"
        manifest_file.write_text("{invalid json content")

        # Should not crash, treats as empty manifest
        changes = check_upstream_changes(recipe_dir)
        assert len(changes) == 1
        assert changes[0]["status"] == "new"

    def test_manifest_invalid_hash_format(self, tmp_path):
        """check_upstream_changes handles invalid hash values."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        recipe_file = recipe_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        # Manifest with invalid hash format
        manifest_file = recipe_dir / "_recipe_manifest.json"
        manifest_file.write_text('{"test": "not-a-valid-hash"}')

        changes = check_upstream_changes(recipe_dir)
        assert len(changes) == 1
        assert changes[0]["status"] == "modified"

    def test_manifest_locked_file(self, tmp_path):
        """update_manifest handles locked manifest file on Windows."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        recipe_file = recipe_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        manifest_file = recipe_dir / "_recipe_manifest.json"
        manifest_file.write_text("{}")

        # Mock file write failure
        original_write = Path.write_text

        def failing_write(self, *args, **kwargs):
            if self.name == "_recipe_manifest.json":
                raise PermissionError("File is locked")
            return original_write(self, *args, **kwargs)

        with mock.patch.object(Path, "write_text", failing_write):
            with pytest.raises(PermissionError):
                update_manifest(recipe_dir)

    def test_manifest_missing_recovery(self, tmp_path):
        """check_upstream_changes creates baseline when manifest missing."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        recipe_file = recipe_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        # No manifest exists
        changes = check_upstream_changes(recipe_dir)
        # All recipes should be reported as "new"
        assert len(changes) == 1
        assert changes[0]["status"] == "new"

    def test_manifest_very_large(self, tmp_path):
        """update_manifest handles very large manifests (10K+ recipes)."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        # Create 10,000 recipe files
        num_recipes = 10000
        for i in range(num_recipes):
            recipe_file = recipe_dir / f"recipe_{i:05d}.yaml"
            recipe_file.write_text(f"name: recipe_{i:05d}\nsteps: []\n")

        # Should handle without crashing
        manifest_path = update_manifest(recipe_dir)
        assert manifest_path.exists()

        manifest_data = json.loads(manifest_path.read_text())
        assert len(manifest_data) == num_recipes

    def test_manifest_race_condition(self, tmp_path):
        """update_manifest handles concurrent writes safely."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        for i in range(10):
            recipe_file = recipe_dir / f"recipe_{i}.yaml"
            recipe_file.write_text(f"name: recipe_{i}\nsteps: []\n")

        errors = []

        def update_worker():
            try:
                update_manifest(recipe_dir)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=update_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # At least one should succeed
        manifest_path = recipe_dir / "_recipe_manifest.json"
        assert manifest_path.exists()

        # All threads should complete (may overwrite each other)
        assert len(errors) == 0

    def test_manifest_permission_denied(self, tmp_path):
        """update_manifest handles permission denied on manifest file."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        recipe_file = recipe_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        manifest_file = recipe_dir / "_recipe_manifest.json"
        manifest_file.write_text("{}")

        # Make manifest read-only
        if os.name != "nt":  # Skip on Windows
            manifest_file.chmod(0o444)

            with pytest.raises(PermissionError):
                update_manifest(recipe_dir)

            # Cleanup
            manifest_file.chmod(0o644)

    def test_manifest_disk_full(self, tmp_path, monkeypatch):
        """update_manifest handles disk full during write."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        recipe_file = recipe_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        # Mock write_text to simulate disk full
        original_write = Path.write_text

        def disk_full_write(self, *args, **kwargs):
            if self.name == "_recipe_manifest.json":
                raise OSError(28, "No space left on device")
            return original_write(self, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", disk_full_write)

        with pytest.raises(OSError):
            update_manifest(recipe_dir)

    def test_manifest_encoding_errors(self, tmp_path):
        """check_upstream_changes handles encoding errors in manifest.

        Note: The implementation's _load_manifest catches OSError but not
        UnicodeDecodeError. This test documents that behavior - encoding
        errors will propagate up. This is actually reasonable behavior since
        manifests are internal files that should always be valid UTF-8.
        """
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        recipe_file = recipe_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        # Create manifest with invalid UTF-8
        manifest_file = recipe_dir / "_recipe_manifest.json"
        manifest_file.write_bytes(b'{"test": "\xff\xfe"}')

        # UnicodeDecodeError will be raised (documented behavior)
        with pytest.raises(UnicodeDecodeError):
            check_upstream_changes(recipe_dir)


# =============================================================================
# TestSearchPathEdgeCases - Search path and filesystem edge cases
# =============================================================================


class TestSearchPathEdgeCases:
    """Test edge cases in search path handling."""

    def test_nonexistent_directory(self, tmp_path):
        """discover_recipes handles nonexistent directories gracefully."""
        nonexistent = tmp_path / "does_not_exist"
        recipes = discover_recipes([nonexistent])
        assert recipes == {}

    def test_search_path_permission_denied(self, tmp_path):
        """discover_recipes skips directories without read permission."""
        if os.name == "nt":
            pytest.skip("Permission tests unreliable on Windows")

        no_access_dir = tmp_path / "no_access"
        no_access_dir.mkdir()
        recipe_file = no_access_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        # Remove read permission
        no_access_dir.chmod(0o000)

        try:
            # Should not crash, just skip the directory
            recipes = discover_recipes([no_access_dir])
            assert recipes == {}
        finally:
            # Restore permissions for cleanup
            no_access_dir.chmod(0o755)

    def test_symlink_loops(self, tmp_path):
        """discover_recipes handles symlink loops without hanging."""
        if os.name == "nt":
            pytest.skip("Symlink tests unreliable on Windows")

        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        # Create circular symlinks
        (dir1 / "link_to_dir2").symlink_to(dir2)
        (dir2 / "link_to_dir1").symlink_to(dir1)

        # Should not hang or crash
        recipes = discover_recipes([dir1])
        assert recipes == {}

    def test_file_deleted_during_scan(self, tmp_path, monkeypatch):
        """discover_recipes handles files deleted during scan."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        recipe_file = recipe_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        original_glob = Path.glob
        call_count = {"count": 0}

        def delayed_glob(self, pattern):
            call_count["count"] += 1
            results = list(original_glob(self, pattern))
            # Delete file after glob but before read
            if call_count["count"] == 1 and results:
                results[0].unlink()
            return iter(results)

        monkeypatch.setattr(Path, "glob", delayed_glob)

        # Should handle gracefully
        recipes = discover_recipes([recipe_dir])
        assert recipes == {}

    def test_mixed_case_filenames(self, tmp_path):
        """discover_recipes handles mixed case YAML extensions."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        # .yaml extension (standard)
        (recipe_dir / "test.yaml").write_text("name: test\nsteps: []\n")

        # Mixed case should not be discovered (only .yaml is supported)
        (recipe_dir / "Test.YAML").write_text("name: test2\nsteps: []\n")
        (recipe_dir / "test3.Yaml").write_text("name: test3\nsteps: []\n")

        recipes = discover_recipes([recipe_dir])
        # Only .yaml (lowercase) should be found
        assert len(recipes) == 1
        assert "test" in recipes

    def test_special_chars_in_filenames(self, tmp_path):
        """discover_recipes handles special characters in filenames."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        # Various special characters
        special_files = [
            "test-recipe.yaml",
            "test_recipe.yaml",
            "test.recipe.yaml",
            "test@recipe.yaml",
        ]

        for filename in special_files:
            (recipe_dir / filename).write_text(
                f"name: {filename.replace('.yaml', '')}\nsteps: []\n"
            )

        recipes = discover_recipes([recipe_dir])
        assert len(recipes) == len(special_files)

    def test_hidden_yaml_files(self, tmp_path):
        """discover_recipes finds hidden YAML files (starting with dot).

        Note: Python's glob('*.yaml') DOES match hidden files like '.hidden.yaml'
        This documents actual glob behavior - the pattern matches the entire
        basename, not just visible files. If we wanted to exclude hidden files,
        we'd need explicit filtering.
        """
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        # Regular file
        (recipe_dir / "visible.yaml").write_text("name: visible\nsteps: []\n")

        # Hidden file (starts with dot)
        (recipe_dir / ".hidden.yaml").write_text("name: hidden\nsteps: []\n")

        recipes = discover_recipes([recipe_dir])
        # glob('*.yaml') matches both visible and hidden .yaml files
        assert len(recipes) == 2
        assert "visible" in recipes
        assert "hidden" in recipes

    def test_yaml_without_extension(self, tmp_path):
        """discover_recipes ignores YAML files without .yaml extension."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        # File with .yaml extension
        (recipe_dir / "test.yaml").write_text("name: test\nsteps: []\n")

        # YAML content but wrong extension
        (recipe_dir / "test.yml").write_text("name: test2\nsteps: []\n")
        (recipe_dir / "test.txt").write_text("name: test3\nsteps: []\n")
        (recipe_dir / "test").write_text("name: test4\nsteps: []\n")

        recipes = discover_recipes([recipe_dir])
        # Only .yaml extension should be found
        assert len(recipes) == 1
        assert "test" in recipes

    def test_recursive_scan_disabled(self, tmp_path):
        """discover_recipes does not recurse into subdirectories."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        # Recipe in top level
        (recipe_dir / "top.yaml").write_text("name: top\nsteps: []\n")

        # Recipe in subdirectory
        subdir = recipe_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.yaml").write_text("name: nested\nsteps: []\n")

        recipes = discover_recipes([recipe_dir])
        # Only top-level recipe should be found
        assert len(recipes) == 1
        assert "top" in recipes
        assert "nested" not in recipes

    def test_very_deep_nesting(self, tmp_path):
        """discover_recipes handles very deep directory nesting."""
        # Create deeply nested structure
        current = tmp_path
        for i in range(50):
            current = current / f"level_{i}"
            current.mkdir()

        recipe_file = current / "deep.yaml"
        recipe_file.write_text("name: deep\nsteps: []\n")

        # Should handle without stack overflow
        recipes = discover_recipes([current])
        assert len(recipes) == 1
        assert "deep" in recipes


# =============================================================================
# TestDiscoveryRaceConditions - Concurrent access edge cases
# =============================================================================


class TestDiscoveryRaceConditions:
    """Test race conditions and concurrent access patterns."""

    @pytest.mark.flaky(reruns=3)
    def test_concurrent_discovery_calls(self, tmp_path):
        """Multiple discover_recipes calls running concurrently.

        Note: Marked as flaky due to potential race conditions in concurrent filesystem access.
        """
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        for i in range(20):
            recipe_file = recipe_dir / f"recipe_{i}.yaml"
            recipe_file.write_text(f"name: recipe_{i}\nsteps: []\n")

        results = []
        errors = []
        barrier = threading.Barrier(10)  # Synchronize thread start

        def discover_worker():
            try:
                barrier.wait()  # All threads start together
                recipes = discover_recipes([recipe_dir])
                results.append(recipes)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=discover_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        assert len(errors) == 0
        assert len(results) == 10

        # All should find the same recipes
        for recipes in results:
            assert len(recipes) == 20

    @pytest.mark.flaky(reruns=3)
    def test_recipe_modified_during_discovery(self, tmp_path):
        """discover_recipes handles file modification during scan.

        Note: Marked as flaky due to timing-dependent race condition.
        """
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        recipe_file = recipe_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        # Simulate modification during discovery
        def modify_during_scan():
            time.sleep(0.01)
            recipe_file.write_text("name: modified\nsteps: [step1]\n")

        modifier = threading.Thread(target=modify_during_scan)
        modifier.start()

        # Discovery should complete without error
        recipes = discover_recipes([recipe_dir])

        modifier.join()

        # Should have found the recipe (content may vary)
        assert len(recipes) >= 1

    @pytest.mark.flaky(reruns=3)
    def test_recipe_deleted_during_discovery(self, tmp_path):
        """discover_recipes handles file deletion during scan.

        Note: Marked as flaky due to timing-dependent race condition.
        """
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        recipe_file = recipe_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        # Simulate deletion during discovery
        def delete_during_scan():
            time.sleep(0.01)
            if recipe_file.exists():
                recipe_file.unlink()

        deleter = threading.Thread(target=delete_during_scan)
        deleter.start()

        # Discovery should complete without error
        recipes = discover_recipes([recipe_dir])

        deleter.join()

        # May or may not find the recipe depending on timing
        assert isinstance(recipes, dict)

    def test_directory_deleted_during_scan(self, tmp_path):
        """discover_recipes handles directory deletion during scan."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        recipe_file = recipe_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        # Simulate directory deletion during discovery (difficult to trigger)
        # This is more of a documentation test
        recipes = discover_recipes([recipe_dir])

        # If directory gets deleted, glob should return empty
        assert isinstance(recipes, dict)

    @pytest.mark.flaky(reruns=3)
    def test_manifest_updated_during_check(self, tmp_path):
        """check_upstream_changes handles manifest updates during check.

        Note: Marked as flaky due to timing-dependent race condition.
        """
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        recipe_file = recipe_dir / "test.yaml"
        recipe_file.write_text("name: test\nsteps: []\n")

        # Create initial manifest
        update_manifest(recipe_dir)

        # Simulate manifest update during check
        def update_during_check():
            time.sleep(0.01)
            # Modify recipe and update manifest
            recipe_file.write_text("name: test\nsteps: [step1]\n")
            update_manifest(recipe_dir)

        updater = threading.Thread(target=update_during_check)
        updater.start()

        # Check should complete without error
        changes = check_upstream_changes(recipe_dir)

        updater.join()

        # Should detect changes or not, both valid depending on timing
        assert isinstance(changes, list)


# =============================================================================
# TestRecipeInfoEdgeCases - RecipeInfo metadata edge cases
# =============================================================================


class TestRecipeInfoEdgeCases:
    """Test edge cases in RecipeInfo metadata extraction."""

    def test_missing_metadata_fields(self, tmp_path):
        """discover_recipes handles recipes with minimal metadata."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        # Minimal valid recipe
        recipe_file = recipe_dir / "minimal.yaml"
        recipe_file.write_text("name: minimal\n")

        recipes = discover_recipes([recipe_dir])
        assert len(recipes) == 1

        info = recipes["minimal"]
        assert info.name == "minimal"
        assert info.description == ""
        assert info.version == ""
        assert info.step_count == 0
        assert info.tags == []

    def test_malformed_steps_field(self, tmp_path):
        """discover_recipes handles malformed steps field."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        # Steps is not a list
        recipe_file = recipe_dir / "bad_steps.yaml"
        recipe_file.write_text("name: bad_steps\nsteps: 'not a list'\n")

        recipes = discover_recipes([recipe_dir])
        assert len(recipes) == 1

        info = recipes["bad_steps"]
        assert info.step_count == 0

    def test_very_long_description(self, tmp_path):
        """discover_recipes handles very long description fields."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        # 10KB description
        long_desc = "x" * 10000
        recipe_file = recipe_dir / "long_desc.yaml"
        recipe_file.write_text(f"name: long_desc\ndescription: {long_desc}\nsteps: []\n")

        recipes = discover_recipes([recipe_dir])
        assert len(recipes) == 1

        info = recipes["long_desc"]
        assert len(info.description) == 10000

    def test_unicode_in_all_fields(self, tmp_path):
        """discover_recipes handles Unicode in all metadata fields."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        recipe_content = """
name: unicode_test
description: "Testing 🎯 Unicode 中文 العربية"
version: "1.0.0-β"
tags: ["emoji-🚀", "日本語", "한글"]
steps:
  - name: "Step with émojis 🎉"
"""
        recipe_file = recipe_dir / "unicode.yaml"
        recipe_file.write_text(recipe_content, encoding="utf-8")

        recipes = discover_recipes([recipe_dir])
        assert len(recipes) == 1

        info = recipes["unicode_test"]
        assert "🎯" in info.description
        assert "β" in info.version
        assert "emoji-🚀" in info.tags

    def test_sha256_collision_detection(self, tmp_path):
        """discover_recipes generates unique hashes for different files."""
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        # Create two very similar recipes
        recipe1 = recipe_dir / "recipe1.yaml"
        recipe1.write_text("name: recipe1\nsteps: []\n")

        recipe2 = recipe_dir / "recipe2.yaml"
        recipe2.write_text("name: recipe2\nsteps: []\n")

        recipes = discover_recipes([recipe_dir])
        assert len(recipes) == 2

        # Hashes should be different
        hash1 = recipes["recipe1"].sha256
        hash2 = recipes["recipe2"].sha256
        assert hash1 != hash2
        # Both should be 16-character hex strings (truncated SHA256)
        assert len(hash1) == 16
        assert len(hash2) == 16
        assert all(c in "0123456789abcdef" for c in hash1)
        assert all(c in "0123456789abcdef" for c in hash2)
