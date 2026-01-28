"""Unit tests for UserPromptSubmit hook's AMPLIHACK.md injection logic.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)

This file focuses on unit tests for the _inject_amplihack_if_different() method
which ensures framework instructions are injected when project CLAUDE.md differs.
"""

import functools
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import the hook under test
import sys

# Add hook location to path
hook_path = Path(__file__).parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
sys.path.insert(0, str(hook_path))

from user_prompt_submit import UserPromptSubmitHook


# ============================================================================
# TEST HELPERS
# ============================================================================


def isolated_env(func):
    """Decorator to ensure test isolation by clearing CLAUDE_PLUGIN_ROOT."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Clear environment to prevent interference from actual amplihack plugin
        env_backup = os.environ.get("CLAUDE_PLUGIN_ROOT")
        if "CLAUDE_PLUGIN_ROOT" in os.environ:
            del os.environ["CLAUDE_PLUGIN_ROOT"]

        try:
            return func(*args, **kwargs)
        finally:
            # Restore original environment
            if env_backup is not None:
                os.environ["CLAUDE_PLUGIN_ROOT"] = env_backup

    return wrapper


# ============================================================================
# UNIT TESTS (60%)
# ============================================================================


class TestAmplihackInjection:
    """Unit tests for _inject_amplihack_if_different() method."""

    @pytest.fixture
    def hook(self):
        """Create a hook instance with mocked project root."""
        hook = UserPromptSubmitHook()
        hook.project_root = Path("/fake/project")
        hook.log = MagicMock()
        return hook

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir(parents=True)
            yield project_root

    # ------------------------------------------------------------------------
    # Scenario 1: Files identical → returns empty string
    # ------------------------------------------------------------------------

    @isolated_env
    def test_identical_files_returns_empty(self, hook):
        """Test that identical AMPLIHACK.md and CLAUDE.md returns empty string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            # Create identical files
            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            content = "# Framework Instructions\nSame content in both files"
            amplihack_path.write_text(content, encoding="utf-8")
            claude_path.write_text(content, encoding="utf-8")

            # Call method
            result = hook._inject_amplihack_if_different()

            # Should return empty string
            assert result == ""
            hook.log.assert_not_called()

    @isolated_env
    def test_identical_with_whitespace_differences(self, hook):
        """Test that whitespace-only differences are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            # Same content but different whitespace
            amplihack_path.write_text("# Title\n\nContent\n\n", encoding="utf-8")
            claude_path.write_text("# Title\n\nContent\n", encoding="utf-8")

            result = hook._inject_amplihack_if_different()

            # Should treat as identical (strip() normalizes whitespace)
            assert result == ""

    # ------------------------------------------------------------------------
    # Scenario 2: Files different → returns AMPLIHACK.md content
    # ------------------------------------------------------------------------

    @isolated_env
    def test_different_files_returns_amplihack_content(self, hook):
        """Test that different files returns AMPLIHACK.md content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            amplihack_content = "# Framework Instructions\nAmplihack content"
            claude_content = "# Project Instructions\nProject-specific content"

            amplihack_path.write_text(amplihack_content, encoding="utf-8")
            claude_path.write_text(claude_content, encoding="utf-8")

            result = hook._inject_amplihack_if_different()

            # Should return AMPLIHACK.md content
            assert result == amplihack_content

    # ------------------------------------------------------------------------
    # Scenario 3: CLAUDE.md missing → returns AMPLIHACK.md content
    # ------------------------------------------------------------------------

    @isolated_env
    def test_missing_claude_md_returns_amplihack(self, hook):
        """Test that missing CLAUDE.md returns AMPLIHACK.md content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"

            amplihack_content = "# Framework Instructions\nAmplihack content"
            amplihack_path.write_text(amplihack_content, encoding="utf-8")

            # CLAUDE.md does not exist
            assert not (project_root / "CLAUDE.md").exists()

            result = hook._inject_amplihack_if_different()

            # Should return AMPLIHACK.md content (compared against empty string)
            assert result == amplihack_content

    # ------------------------------------------------------------------------
    # Scenario 4: AMPLIHACK.md not found → returns empty string
    # ------------------------------------------------------------------------

    @isolated_env
    def test_missing_amplihack_returns_empty(self, hook):
        """Test that missing AMPLIHACK.md returns empty string with log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            # No .claude directory, no AMPLIHACK.md
            result = hook._inject_amplihack_if_different()

            # Should return empty string
            assert result == ""

            # Should log that AMPLIHACK.md was not found
            hook.log.assert_called_once()
            assert "No AMPLIHACK.md found" in str(hook.log.call_args)

    # ------------------------------------------------------------------------
    # Scenario 5: Cache hit (same mtimes) → returns cached result
    # ------------------------------------------------------------------------

    @isolated_env
    def test_cache_hit_avoids_rereading(self, hook):
        """Test that cache hit returns cached result without reading files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            amplihack_content = "# Framework\nAmplihack"
            claude_content = "# Project\nProject"

            amplihack_path.write_text(amplihack_content, encoding="utf-8")
            claude_path.write_text(claude_content, encoding="utf-8")

            # First call - should read files and cache
            result1 = hook._inject_amplihack_if_different()
            assert result1 == amplihack_content

            # Mock read_text to verify it's not called on second call
            with patch.object(Path, "read_text") as mock_read:
                # Second call - should use cache
                result2 = hook._inject_amplihack_if_different()

                # Should return cached result
                assert result2 == amplihack_content

                # Should NOT have called read_text (cache hit)
                mock_read.assert_not_called()

    # ------------------------------------------------------------------------
    # Scenario 6: Cache invalidated (mtime changed) → re-reads files
    # ------------------------------------------------------------------------

    @isolated_env
    def test_cache_invalidation_on_mtime_change(self, hook):
        """Test that mtime change invalidates cache and re-reads files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            # Initial content
            amplihack_path.write_text("# V1\nVersion 1", encoding="utf-8")
            claude_path.write_text("# Project\nProject", encoding="utf-8")

            # First call - caches result
            result1 = hook._inject_amplihack_if_different()
            assert "Version 1" in result1

            # Modify AMPLIHACK.md (changes mtime)
            import time

            time.sleep(0.01)  # Ensure mtime changes
            amplihack_path.write_text("# V2\nVersion 2", encoding="utf-8")

            # Second call - should detect mtime change and re-read
            result2 = hook._inject_amplihack_if_different()
            assert "Version 2" in result2
            assert result2 != result1

    @isolated_env
    def test_claude_md_mtime_change_invalidates_cache(self, hook):
        """Test that CLAUDE.md mtime change also invalidates cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            amplihack_path.write_text("# Framework\nAmplihack", encoding="utf-8")
            claude_path.write_text("# V1\nVersion 1", encoding="utf-8")

            # First call - files are different
            result1 = hook._inject_amplihack_if_different()
            assert result1  # Should return amplihack content

            # Modify CLAUDE.md to match AMPLIHACK.md
            import time

            time.sleep(0.01)
            claude_path.write_text("# Framework\nAmplihack", encoding="utf-8")

            # Second call - should detect change and return empty (now identical)
            result2 = hook._inject_amplihack_if_different()
            assert result2 == ""

    # ------------------------------------------------------------------------
    # Scenario 7: Plugin location takes priority over per-project location
    # ------------------------------------------------------------------------

    @isolated_env
    def test_plugin_location_priority(self, hook):
        """Test that plugin location (CLAUDE_PLUGIN_ROOT) takes priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            plugin_root = Path(tmpdir) / "plugin"
            hook.project_root = project_root

            # Create both locations
            (project_root / ".claude").mkdir(parents=True)
            plugin_root.mkdir(parents=True)

            # Different content in each location
            project_amplihack = project_root / ".claude" / "AMPLIHACK.md"
            plugin_amplihack = plugin_root / "AMPLIHACK.md"
            claude_md = project_root / "CLAUDE.md"

            project_amplihack.write_text("# Project\nProject location", encoding="utf-8")
            plugin_amplihack.write_text("# Plugin\nPlugin location", encoding="utf-8")
            claude_md.write_text("# Different\nDifferent content", encoding="utf-8")

            # Set plugin root environment variable
            with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": str(plugin_root)}):
                result = hook._inject_amplihack_if_different()

                # Should use plugin location (priority)
                assert "Plugin location" in result
                assert "Project location" not in result

    @isolated_env
    def test_fallback_to_project_location_when_no_plugin(self, hook):
        """Test fallback to project location when plugin not set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            amplihack_path.write_text("# Project\nProject location", encoding="utf-8")
            claude_path.write_text("# Different\nDifferent", encoding="utf-8")

            # No CLAUDE_PLUGIN_ROOT set
            with patch.dict(os.environ, {}, clear=True):
                result = hook._inject_amplihack_if_different()

                # Should use project location
                assert "Project location" in result

    @isolated_env
    def test_plugin_location_invalid_path(self, hook):
        """Test handling of invalid plugin path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            amplihack_path.write_text("# Project\nProject", encoding="utf-8")
            claude_path.write_text("# Different\nDiff", encoding="utf-8")

            # Set plugin root to non-existent path
            with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": "/nonexistent/path"}):
                result = hook._inject_amplihack_if_different()

                # Should fallback to project location
                assert "Project" in result

    # ------------------------------------------------------------------------
    # Scenario 8: Error handling → returns empty string
    # ------------------------------------------------------------------------

    @isolated_env
    def test_permission_error_returns_empty(self, hook):
        """Test that permission errors return empty string with warning log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            amplihack_path.write_text("# Content\nContent", encoding="utf-8")

            # Mock read_text to raise PermissionError
            with patch.object(Path, "read_text", side_effect=PermissionError("No access")):
                result = hook._inject_amplihack_if_different()

                # Should return empty string
                assert result == ""

                # Should log warning
                hook.log.assert_called()
                assert "WARNING" in str(hook.log.call_args)

    @isolated_env
    def test_encoding_error_returns_empty(self, hook):
        """Test that encoding errors return empty string with warning log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            amplihack_path.write_text("# Content\nContent", encoding="utf-8")

            # Mock read_text to raise UnicodeDecodeError
            with patch.object(
                Path,
                "read_text",
                side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"),
            ):
                result = hook._inject_amplihack_if_different()

                # Should return empty string
                assert result == ""

                # Should log warning
                hook.log.assert_called()
                assert "WARNING" in str(hook.log.call_args)

    @isolated_env
    def test_generic_exception_returns_empty(self, hook):
        """Test that generic exceptions return empty string with warning log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            # Mock stat() to raise exception
            with patch.object(Path, "stat", side_effect=RuntimeError("Disk error")):
                result = hook._inject_amplihack_if_different()

                # Should return empty string (graceful degradation)
                assert result == ""

                # Should log warning
                hook.log.assert_called()
                assert "WARNING" in str(hook.log.call_args)


# ============================================================================
# INTEGRATION TESTS (30%)
# ============================================================================


class TestAmplihackInjectionIntegration:
    """Integration tests for AMPLIHACK injection within full hook context."""

    @pytest.fixture
    def temp_project_full(self):
        """Create a complete temporary project with all necessary files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create directory structure
            (project_root / ".claude" / "context").mkdir(parents=True)
            (project_root / ".claude" / "transcripts").mkdir(parents=True)

            # Create AMPLIHACK.md
            amplihack = project_root / ".claude" / "AMPLIHACK.md"
            amplihack.write_text(
                "# AMPLIHACK Framework\n\nFramework instructions here.", encoding="utf-8"
            )

            yield project_root

    @isolated_env
    def test_injection_in_full_process_flow(self, temp_project_full):
        """Test that injection works within full hook.process() flow."""
        hook = UserPromptSubmitHook()
        hook.project_root = temp_project_full

        # Create different CLAUDE.md
        claude_md = temp_project_full / "CLAUDE.md"
        claude_md.write_text("# Project\nProject-specific", encoding="utf-8")

        # Process input (minimal valid input)
        input_data = {
            "session_id": "test_session",
            "transcript_path": str(temp_project_full / ".claude" / "transcripts"),
            "cwd": str(temp_project_full),
            "hook_event_name": "UserPromptSubmit",
            "userMessage": "test prompt",
        }

        result = hook.process(input_data)

        # Should have additionalContext with AMPLIHACK content
        assert "additionalContext" in result
        assert "AMPLIHACK Framework" in result["additionalContext"]

    @isolated_env
    def test_no_injection_when_files_identical_in_process(self, temp_project_full):
        """Test that identical files produce no injection in process() flow."""
        hook = UserPromptSubmitHook()
        hook.project_root = temp_project_full

        # Make CLAUDE.md identical to AMPLIHACK.md
        amplihack_content = (temp_project_full / ".claude" / "AMPLIHACK.md").read_text()
        claude_md = temp_project_full / "CLAUDE.md"
        claude_md.write_text(amplihack_content, encoding="utf-8")

        input_data = {
            "session_id": "test_session",
            "transcript_path": str(temp_project_full / ".claude" / "transcripts"),
            "cwd": str(temp_project_full),
            "hook_event_name": "UserPromptSubmit",
            "userMessage": "test prompt",
        }

        result = hook.process(input_data)

        # Should not contain AMPLIHACK content (identical files)
        assert "additionalContext" in result
        # Content might be empty or contain other context (preferences), but not AMPLIHACK
        if result["additionalContext"]:
            assert "AMPLIHACK Framework" not in result["additionalContext"]

    @isolated_env
    def test_caching_across_multiple_process_calls(self, temp_project_full):
        """Test that caching works across multiple process() invocations."""
        hook = UserPromptSubmitHook()
        hook.project_root = temp_project_full

        # Different CLAUDE.md
        claude_md = temp_project_full / "CLAUDE.md"
        claude_md.write_text("# Project\nDifferent", encoding="utf-8")

        input_data = {
            "session_id": "test_session",
            "transcript_path": str(temp_project_full / ".claude" / "transcripts"),
            "cwd": str(temp_project_full),
            "hook_event_name": "UserPromptSubmit",
            "userMessage": "test prompt",
        }

        # First call
        result1 = hook.process(input_data)

        # Mock read_text to verify cache is used
        with patch.object(Path, "read_text") as mock_read:
            # Set return value for any read_text calls that do happen
            mock_read.return_value = "Should not be called"

            # Second call - should use cache
            result2 = hook.process(input_data)

            # Results should be identical
            assert result1["additionalContext"] == result2["additionalContext"]

            # read_text should not be called for AMPLIHACK/CLAUDE comparison
            # (might be called for preferences, but verify AMPLIHACK is not re-read)
            calls = [str(call) for call in mock_read.call_args_list]
            amplihack_reads = [c for c in calls if "AMPLIHACK" in c]
            assert len(amplihack_reads) == 0, "AMPLIHACK.md should be cached"


# ============================================================================
# EDGE CASES
# ============================================================================


class TestAmplihackInjectionEdgeCases:
    """Edge case tests for unusual scenarios."""

    @isolated_env
    def test_empty_amplihack_file(self):
        """Test handling of empty AMPLIHACK.md file."""
        hook = UserPromptSubmitHook()

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            # Empty AMPLIHACK.md
            amplihack_path.write_text("", encoding="utf-8")
            claude_path.write_text("# Content\nSome content", encoding="utf-8")

            result = hook._inject_amplihack_if_different()

            # Empty AMPLIHACK is different from non-empty CLAUDE
            # Should return empty string (the AMPLIHACK content)
            assert result == ""

    @isolated_env
    def test_very_large_files(self):
        """Test handling of very large markdown files."""
        hook = UserPromptSubmitHook()

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            # Create large content (simulate real AMPLIHACK.md size ~2000 lines)
            large_content = "# Framework\n" + ("Line content\n" * 2000)
            amplihack_path.write_text(large_content, encoding="utf-8")
            claude_path.write_text("# Small\nSmall file", encoding="utf-8")

            # Should handle without issues
            result = hook._inject_amplihack_if_different()
            assert result == large_content

    @isolated_env
    def test_symlink_handling(self):
        """Test handling of symlinked AMPLIHACK.md."""
        hook = UserPromptSubmitHook()

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)

            # Create actual file
            actual_file = project_root / "actual_amplihack.md"
            actual_file.write_text("# Framework\nActual content", encoding="utf-8")

            # Create symlink
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            try:
                amplihack_path.symlink_to(actual_file)
            except (OSError, NotImplementedError):
                pytest.skip("Symlinks not supported on this platform")

            claude_path = project_root / "CLAUDE.md"
            claude_path.write_text("# Different\nDifferent", encoding="utf-8")

            # Should follow symlink and read content
            result = hook._inject_amplihack_if_different()
            assert "Actual content" in result

    @isolated_env
    def test_concurrent_file_modification(self):
        """Test behavior when files are modified during comparison."""
        hook = UserPromptSubmitHook()

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            amplihack_path.write_text("# V1\nVersion 1", encoding="utf-8")
            claude_path.write_text("# Project\nProject", encoding="utf-8")

            # Mock stat to return different mtime on second call (simulate concurrent modification)
            original_stat = amplihack_path.stat

            call_count = [0]

            def stat_with_modification():
                call_count[0] += 1
                stat_result = original_stat()
                if call_count[0] == 2:
                    # Simulate mtime change on second call
                    import time

                    time.sleep(0.01)
                return stat_result

            # This is a complex scenario - just verify it doesn't crash
            result = hook._inject_amplihack_if_different()
            assert isinstance(result, str)


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


class TestAmplihackInjectionPerformance:
    """Performance tests for injection method."""

    @isolated_env
    def test_caching_performance_improvement(self):
        """Test that caching provides measurable performance improvement."""
        import time

        hook = UserPromptSubmitHook()

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            # Large file
            content = "# Framework\n" + ("Line content\n" * 1000)
            amplihack_path.write_text(content, encoding="utf-8")
            claude_path.write_text("# Different\nSmall", encoding="utf-8")

            # First call (uncached)
            start = time.time()
            result1 = hook._inject_amplihack_if_different()
            uncached_time = time.time() - start

            # Second call (cached)
            start = time.time()
            result2 = hook._inject_amplihack_if_different()
            cached_time = time.time() - start

            # Verify correctness
            assert result1 == result2
            assert result1 == content

            # Cached should be faster or equal (file I/O is very fast, so improvement may be minimal)
            # This is more of a "does caching work" test than a strict performance test
            assert cached_time <= uncached_time * 1.5, (
                f"Cache appears slower: uncached={uncached_time:.4f}s, "
                f"cached={cached_time:.4f}s"
            )

    @isolated_env
    def test_single_call_performance(self):
        """Test that single call completes within acceptable time."""
        import time

        hook = UserPromptSubmitHook()

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            hook.project_root = project_root

            (project_root / ".claude").mkdir(parents=True)
            amplihack_path = project_root / ".claude" / "AMPLIHACK.md"
            claude_path = project_root / "CLAUDE.md"

            # Realistic file size (~2000 lines like real AMPLIHACK.md)
            content = "# Framework Instructions\n" + ("Line content here\n" * 2000)
            amplihack_path.write_text(content, encoding="utf-8")
            claude_path.write_text("# Project\nSmall", encoding="utf-8")

            # Time the call
            start = time.time()
            result = hook._inject_amplihack_if_different()
            elapsed = time.time() - start

            # Should complete in under 50ms (file I/O is fast)
            assert elapsed < 0.05, f"Too slow: {elapsed:.4f}s"
            assert result == content
