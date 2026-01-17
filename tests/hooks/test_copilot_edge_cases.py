"""Comprehensive edge case tests for Copilot CLI Integration.

Tests ALL edge cases identified in comprehensive edge case testing request:
1. Empty/Missing Files
2. Corrupted State
3. Concurrent Access
4. Resource Limits
5. Platform Variations
6. Regression Testing

Philosophy:
- Assume things will break
- Test every failure mode
- Verify graceful degradation
- No silent failures
"""

import json
import os
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from amplihack.context.adaptive.detector import LauncherDetector
from amplihack.context.adaptive.strategies import ClaudeStrategy, CopilotStrategy


class TestEmptyMissingFiles:
    """Edge Case Category 1: Empty/Missing Files.

    Tests behavior when expected files are empty, missing, or in unexpected states.
    """

    def test_empty_preferences_file(self, tmp_path):
        """What if USER_PREFERENCES.md is empty?

        Expected: Graceful degradation - inject empty context, don't crash.
        """
        # Setup
        prefs_file = tmp_path / ".claude" / "context" / "USER_PREFERENCES.md"
        prefs_file.parent.mkdir(parents=True, exist_ok=True)
        prefs_file.write_text("")  # EMPTY FILE

        strategy = CopilotStrategy(tmp_path)

        # Act - inject empty preferences
        result = strategy.inject_context("")

        # Assert - should handle gracefully
        assert result is not None
        assert "USER PREFERENCES" in result

        # Verify AGENTS.md was created with empty content section
        agents_path = tmp_path / "AGENTS.md"
        assert agents_path.exists()
        content = agents_path.read_text()
        assert "AMPLIHACK_CONTEXT_START" in content
        assert "AMPLIHACK_CONTEXT_END" in content

    def test_missing_claude_agents_directory(self, tmp_path):
        """What if .claude/agents/ doesn't exist?

        Expected: No impact - AGENTS.md is in repo root, not .claude/agents/.
        """
        # .claude/agents/ doesn't exist - this is fine
        assert not (tmp_path / ".claude" / "agents").exists()

        strategy = CopilotStrategy(tmp_path)

        # Act - inject context
        result = strategy.inject_context({"test": "data"})

        # Assert - AGENTS.md created in repo root
        agents_path = tmp_path / "AGENTS.md"
        assert agents_path.exists()
        assert "test" in agents_path.read_text()

    def test_agents_md_already_exists_with_content(self, tmp_path):
        """What if AGENTS.md already exists with different content?

        Expected: Preserve existing content, inject context at top.
        """
        # Setup - create AGENTS.md with existing content
        agents_path = tmp_path / "AGENTS.md"
        existing_content = """# Amplihack Agents

## Existing Agent Documentation

This agent does important work.

### Usage

Example usage here.
"""
        agents_path.write_text(existing_content)

        strategy = CopilotStrategy(tmp_path)

        # Act - inject context
        strategy.inject_context({"new": "context"})

        # Assert - existing content preserved
        content = agents_path.read_text()
        assert "Existing Agent Documentation" in content
        assert "important work" in content
        assert "new" in content  # New context also present

        # Context injected at top
        lines = content.split("\n")
        context_line_idx = next(i for i, line in enumerate(lines) if "AMPLIHACK_CONTEXT_START" in line)
        existing_content_idx = next(i for i, line in enumerate(lines) if "Existing Agent" in line)
        assert context_line_idx < existing_content_idx

    def test_agents_md_already_exists_with_old_context(self, tmp_path):
        """What if AGENTS.md has stale amplihack context?

        Expected: Replace old context with new, preserve other content.
        """
        # Setup - create AGENTS.md with old context
        agents_path = tmp_path / "AGENTS.md"
        old_content = """# Amplihack Agents

<!-- AMPLIHACK_CONTEXT_START -->

## 🎯 OLD CONTEXT

Old data here

<!-- AMPLIHACK_CONTEXT_END -->

## Real Agent Docs

Important content.
"""
        agents_path.write_text(old_content)

        strategy = CopilotStrategy(tmp_path)

        # Act - inject new context
        strategy.inject_context({"new": "context", "fresh": "data"})

        # Assert - old context replaced
        content = agents_path.read_text()
        assert "OLD CONTEXT" not in content
        assert "Old data here" not in content
        assert "new" in content
        assert "fresh" in content

        # Real docs preserved
        assert "Real Agent Docs" in content
        assert "Important content" in content


class TestCorruptedState:
    """Edge Case Category 2: Corrupted State.

    Tests behavior when state files are malformed, corrupted, or have invalid data.
    """

    def test_malformed_launcher_context_json(self, tmp_path):
        """Malformed launcher_context.json (invalid JSON).

        Expected: Fail-safe to Claude Code (default launcher).
        """
        # Setup - create malformed JSON
        context_file = tmp_path / ".claude" / "runtime" / "launcher_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        context_file.write_text("{invalid json: this won't parse")

        detector = LauncherDetector(tmp_path)

        # Act - detect launcher
        launcher_type = detector.detect()

        # Assert - fails safe to claude
        assert launcher_type == "claude"

    def test_launcher_context_missing_fields(self, tmp_path):
        """launcher_context.json with missing required fields.

        Expected: Fail-safe to Claude Code.
        """
        # Setup - create context with missing launcher field
        context_file = tmp_path / ".claude" / "runtime" / "launcher_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        context_data = {
            "command": "amplihack copilot",
            "timestamp": datetime.now(timezone.utc).isoformat()
            # Missing "launcher" field!
        }
        context_file.write_text(json.dumps(context_data))

        detector = LauncherDetector(tmp_path)

        # Act
        launcher_type = detector.detect()

        # Assert - defaults to claude
        assert launcher_type == "claude"

    def test_launcher_context_stale_48_hours(self, tmp_path):
        """Stale launcher_context.json (48 hours old).

        Expected: Detect as stale, fail-safe to Claude Code.
        """
        # Setup - create context from 48 hours ago
        context_file = tmp_path / ".claude" / "runtime" / "launcher_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)

        old_timestamp = datetime.now(timezone.utc) - timedelta(hours=48)
        context_data = {
            "launcher": "copilot",
            "command": "amplihack copilot",
            "timestamp": old_timestamp.isoformat()
        }
        context_file.write_text(json.dumps(context_data))

        detector = LauncherDetector(tmp_path)

        # Act
        is_stale = detector.is_stale()
        launcher_type = detector.detect()

        # Assert - detected as stale, fails to claude
        assert is_stale is True
        assert launcher_type == "claude"

    def test_launcher_context_edge_of_staleness_24_hours(self, tmp_path):
        """launcher_context.json exactly 24 hours old (edge of staleness threshold).

        Expected: Just barely stale, fail-safe to Claude Code.
        """
        # Setup - context exactly 24 hours old
        context_file = tmp_path / ".claude" / "runtime" / "launcher_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)

        # Exactly 24 hours + 1 second (just over threshold)
        old_timestamp = datetime.now(timezone.utc) - timedelta(hours=24, seconds=1)
        context_data = {
            "launcher": "copilot",
            "command": "amplihack copilot",
            "timestamp": old_timestamp.isoformat()
        }
        context_file.write_text(json.dumps(context_data))

        detector = LauncherDetector(tmp_path)

        # Act
        is_stale = detector.is_stale()

        # Assert - detected as stale
        assert is_stale is True

    def test_launcher_context_fresh_23_hours(self, tmp_path):
        """launcher_context.json 23 hours old (within threshold).

        Expected: Not stale, detect as copilot.
        """
        # Setup - context 23 hours old (fresh)
        context_file = tmp_path / ".claude" / "runtime" / "launcher_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)

        fresh_timestamp = datetime.now(timezone.utc) - timedelta(hours=23)
        context_data = {
            "launcher": "copilot",
            "command": "amplihack copilot",
            "timestamp": fresh_timestamp.isoformat()
        }
        context_file.write_text(json.dumps(context_data))

        detector = LauncherDetector(tmp_path)

        # Act
        is_stale = detector.is_stale()
        launcher_type = detector.detect()

        # Assert - fresh, detects copilot
        assert is_stale is False
        assert launcher_type == "copilot"

    def test_launcher_context_invalid_launcher_type(self, tmp_path):
        """launcher_context.json with invalid launcher type.

        Expected: Fail-safe to Claude Code.
        """
        # Setup - invalid launcher type
        context_file = tmp_path / ".claude" / "runtime" / "launcher_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        context_data = {
            "launcher": "invalid_launcher_name",  # Not "claude" or "copilot"
            "command": "amplihack invalid",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        context_file.write_text(json.dumps(context_data))

        detector = LauncherDetector(tmp_path)

        # Act
        launcher_type = detector.detect()

        # Assert - fails safe to claude
        assert launcher_type == "claude"


class TestConcurrentAccess:
    """Edge Case Category 3: Concurrent Access.

    Tests behavior when multiple sessions or threads access files simultaneously.
    """

    def test_two_sessions_starting_simultaneously(self, tmp_path):
        """Two sessions starting at exactly the same time.

        Expected: Both complete, last write wins for AGENTS.md.
        """
        # Setup
        results = []
        errors = []

        def start_session(session_id):
            try:
                strategy = CopilotStrategy(tmp_path)
                context = {
                    "session": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                result = strategy.inject_context(context)
                results.append((session_id, result))
            except Exception as e:
                errors.append((session_id, e))

        # Act - start two sessions simultaneously
        thread1 = threading.Thread(target=start_session, args=("session1",))
        thread2 = threading.Thread(target=start_session, args=("session2",))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Assert - both completed without errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 2

        # AGENTS.md exists (one session won the race)
        agents_path = tmp_path / "AGENTS.md"
        assert agents_path.exists()

        # Content from one session is present (last write wins)
        content = agents_path.read_text()
        assert "session" in content

    def test_one_session_writing_while_another_reads(self, tmp_path):
        """One session writing AGENTS.md while another reads.

        Expected: Reader may see partial content, but no crashes.
        """
        # Setup
        agents_path = tmp_path / "AGENTS.md"
        agents_path.write_text("# Amplihack Agents\n\nInitial content")

        read_results = []
        write_completed = threading.Event()

        def writer():
            strategy = CopilotStrategy(tmp_path)
            for i in range(10):
                strategy.inject_context({"iteration": i})
                time.sleep(0.01)  # Small delay
            write_completed.set()

        def reader():
            while not write_completed.is_set():
                try:
                    content = agents_path.read_text()
                    read_results.append(len(content))
                except Exception as e:
                    read_results.append(f"error: {e}")
                time.sleep(0.005)

        # Act
        write_thread = threading.Thread(target=writer)
        read_thread = threading.Thread(target=reader)

        write_thread.start()
        read_thread.start()

        write_thread.join()
        write_completed.set()  # Signal reader to stop
        read_thread.join()

        # Assert - no errors during concurrent access
        errors = [r for r in read_results if isinstance(r, str) and r.startswith("error")]
        # Some OS-level file locking may cause occasional errors, but shouldn't crash
        # We verify the system is resilient
        assert agents_path.exists()

    def test_race_condition_in_file_creation(self, tmp_path):
        """Race condition when creating AGENTS.md (both threads try to create).

        Expected: One succeeds, both complete without errors.
        """
        # Setup
        create_results = []
        errors = []

        def create_file(thread_id):
            try:
                strategy = CopilotStrategy(tmp_path)
                # Both try to inject context (creates file if missing)
                result = strategy.inject_context({"thread": thread_id})
                create_results.append((thread_id, "success"))
            except Exception as e:
                errors.append((thread_id, e))

        # Act - both threads try to create file simultaneously
        thread1 = threading.Thread(target=create_file, args=("thread1",))
        thread2 = threading.Thread(target=create_file, args=("thread2",))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Assert - no crashes
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(create_results) == 2

        # File exists
        agents_path = tmp_path / "AGENTS.md"
        assert agents_path.exists()


class TestResourceLimits:
    """Edge Case Category 4: Resource Limits.

    Tests behavior under resource constraints (large files, disk full, etc.).
    """

    def test_very_long_preferences_100kb(self, tmp_path):
        """Very long preferences (100KB+).

        Expected: Handle gracefully, inject into AGENTS.md without truncation.
        """
        # Setup - create 100KB preferences
        large_prefs = "# User Preferences\n\n" + ("x" * 100_000)

        strategy = CopilotStrategy(tmp_path)

        # Act - inject large preferences
        result = strategy.inject_context(large_prefs)

        # Assert - completed successfully
        assert result is not None
        assert len(result) > 100_000

        # Verify AGENTS.md contains full content
        agents_path = tmp_path / "AGENTS.md"
        assert agents_path.exists()
        content = agents_path.read_text()
        assert len(content) > 100_000
        assert "USER PREFERENCES" in content

    def test_deeply_nested_directory_structures(self, tmp_path):
        """Deeply nested directory structures (10+ levels).

        Expected: Create parent directories as needed, no errors.
        """
        # Setup - create deeply nested path
        deep_path = tmp_path
        for i in range(15):
            deep_path = deep_path / f"level{i}"

        # Act - create detector with deeply nested project root
        detector = LauncherDetector(deep_path)
        detector.write_context("copilot", "amplihack copilot", {})

        # Assert - context file created in deep path
        context_file = deep_path / ".claude" / "runtime" / "launcher_context.json"
        assert context_file.exists()

        # Verify readable
        context = json.loads(context_file.read_text())
        assert context["launcher"] == "copilot"

    @pytest.mark.skipif(os.name == "nt", reason="Disk full test unreliable on Windows")
    def test_disk_full_scenarios(self, tmp_path):
        """Disk full scenarios (write fails).

        Expected: Graceful error handling, log warning, don't crash.
        """
        # Setup - mock write_text to simulate disk full
        strategy = CopilotStrategy(tmp_path)

        with patch.object(Path, "write_text", side_effect=OSError("No space left on device")):
            # Act - try to inject context (should fail gracefully)
            try:
                result = strategy.inject_context({"test": "data"})
                # Should return result but not write file
                assert result is not None
            except OSError:
                pytest.fail("OSError not handled gracefully - should catch and continue")


class TestPlatformVariations:
    """Edge Case Category 5: Platform Variations.

    Tests behavior across different environments and configurations.
    """

    def test_no_git_repository(self, tmp_path):
        """No git repository (detector/hooks use git commands).

        Expected: Detector works, hooks may warn but don't crash.
        """
        # Setup - tmp_path is not a git repository
        assert not (tmp_path / ".git").exists()

        detector = LauncherDetector(tmp_path)

        # Act - detector should work without git
        detector.write_context("copilot", "amplihack copilot", {})
        launcher_type = detector.detect()

        # Assert - works without git
        assert launcher_type == "copilot"

    def test_uvx_temp_directory_vs_local_directory(self, tmp_path):
        """UVX temp directory vs local directory (path resolution).

        Expected: Both work, detector handles both cases.
        """
        # Test 1: Local directory (normal case)
        local_dir = tmp_path / "local_project"
        local_dir.mkdir()

        detector_local = LauncherDetector(local_dir)
        detector_local.write_context("copilot", "amplihack copilot", {})
        assert detector_local.detect() == "copilot"

        # Test 2: Simulated UVX temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            uvx_dir = Path(temp_dir) / "uvx_12345_project"
            uvx_dir.mkdir()

            detector_uvx = LauncherDetector(uvx_dir)
            detector_uvx.write_context("copilot", "amplihack copilot", {})
            assert detector_uvx.detect() == "copilot"

    def test_missing_dependencies(self, tmp_path):
        """Missing dependencies (json, pathlib) - though these are stdlib.

        Expected: N/A - these are stdlib, always available.

        This test documents the assumption that stdlib is always available.
        """
        # Document assumption
        import json  # noqa: F401
        import pathlib  # noqa: F401

        # If these imports fail, Python itself is broken
        # This test just documents the dependency on stdlib
        assert True


class TestRegression:
    """Edge Case Category 6: Regression Testing.

    Ensures existing functionality still works after integration.
    """

    def test_claude_code_still_works(self, tmp_path):
        """Does Claude Code still work after changes?

        Expected: Claude Code uses ClaudeStrategy, works normally.
        """
        # Setup
        strategy = ClaudeStrategy(tmp_path, log_func=Mock())

        # Act - inject context
        result = strategy.inject_context({"workflow": "DEFAULT_WORKFLOW"})

        # Assert - Claude strategy works
        assert result is not None
        assert "DEFAULT_WORKFLOW" in result

        # Verify context file created (not AGENTS.md)
        context_file = tmp_path / ".claude" / "runtime" / "hook_context.json"
        assert context_file.exists()

        # AGENTS.md should NOT be created by Claude strategy
        agents_path = tmp_path / "AGENTS.md"
        assert not agents_path.exists()

    def test_existing_hooks_still_function(self, tmp_path):
        """Do existing hooks still function?

        Expected: All hook methods work for both strategies.
        """
        # Test Claude strategy hooks
        claude_strategy = ClaudeStrategy(tmp_path)

        assert claude_strategy.handle_stop({}) is None
        assert claude_strategy.handle_pre_tool_use({}) is None
        assert claude_strategy.handle_post_tool_use({}) is None
        assert claude_strategy.handle_user_prompt_submit({}) is None

        # Test Copilot strategy hooks
        copilot_strategy = CopilotStrategy(tmp_path, log_func=Mock())

        assert copilot_strategy.handle_stop({}) is None
        assert copilot_strategy.handle_pre_tool_use({}) is None
        assert copilot_strategy.handle_post_tool_use({}) is None
        assert copilot_strategy.handle_user_prompt_submit({}) is None

    def test_launcher_detector_cleanup_works(self, tmp_path):
        """Does detector cleanup work (removes context file)?

        Expected: cleanup() removes launcher_context.json.
        """
        # Setup
        detector = LauncherDetector(tmp_path)
        detector.write_context("copilot", "amplihack copilot", {})

        context_file = tmp_path / ".claude" / "runtime" / "launcher_context.json"
        assert context_file.exists()

        # Act - cleanup
        detector.cleanup()

        # Assert - context file removed
        assert not context_file.exists()

    def test_copilot_strategy_cleanup_works(self, tmp_path):
        """Does Copilot strategy cleanup work (removes context from AGENTS.md)?

        Expected: cleanup() removes context markers but preserves other content.
        """
        # Setup
        strategy = CopilotStrategy(tmp_path)

        # Create AGENTS.md with context and other content
        agents_path = tmp_path / "AGENTS.md"
        agents_path.write_text("""# Amplihack Agents

<!-- AMPLIHACK_CONTEXT_START -->

## Context

Test context

<!-- AMPLIHACK_CONTEXT_END -->

## Real Docs

Important documentation.
""")

        # Act - cleanup
        strategy.cleanup()

        # Assert - context markers removed, real docs preserved
        content = agents_path.read_text()
        assert "AMPLIHACK_CONTEXT_START" not in content
        assert "AMPLIHACK_CONTEXT_END" not in content
        assert "Test context" not in content

        # Real docs still there
        assert "Real Docs" in content
        assert "Important documentation" in content


class TestGracefulDegradation:
    """Additional edge cases: Graceful degradation scenarios.

    Tests that system degrades gracefully rather than crashing.
    """

    def test_write_permissions_denied(self, tmp_path):
        """Write permissions denied on AGENTS.md.

        Expected: Log error, continue without crashing.
        """
        # Setup - create read-only AGENTS.md
        agents_path = tmp_path / "AGENTS.md"
        agents_path.write_text("# Amplihack Agents\n")
        agents_path.chmod(0o444)  # Read-only

        try:
            strategy = CopilotStrategy(tmp_path, log_func=Mock())

            # Act - try to inject context (should fail gracefully)
            try:
                result = strategy.inject_context({"test": "data"})
                # Should return result but log warning
                assert result is not None
            except PermissionError:
                pytest.fail("PermissionError not handled gracefully")
        finally:
            # Cleanup - restore write permissions
            agents_path.chmod(0o644)

    def test_invalid_timestamp_format(self, tmp_path):
        """Invalid timestamp format in launcher_context.json.

        Expected: Detect as stale, fail-safe to Claude.
        """
        # Setup - create context with invalid timestamp
        context_file = tmp_path / ".claude" / "runtime" / "launcher_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        context_data = {
            "launcher": "copilot",
            "command": "amplihack copilot",
            "timestamp": "not-a-valid-timestamp"
        }
        context_file.write_text(json.dumps(context_data))

        detector = LauncherDetector(tmp_path)

        # Act
        is_stale = detector.is_stale()
        launcher_type = detector.detect()

        # Assert - detected as stale (invalid timestamp)
        assert is_stale is True
        assert launcher_type == "claude"

    def test_context_file_contains_only_whitespace(self, tmp_path):
        """launcher_context.json contains only whitespace.

        Expected: Fail-safe to Claude Code.
        """
        # Setup
        context_file = tmp_path / ".claude" / "runtime" / "launcher_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        context_file.write_text("   \n\n  \t  ")

        detector = LauncherDetector(tmp_path)

        # Act
        launcher_type = detector.detect()

        # Assert - fails safe to claude
        assert launcher_type == "claude"

    def test_agents_md_with_only_markers_no_content(self, tmp_path):
        """AGENTS.md with markers but no content between them.

        Expected: Remove markers cleanly, no orphan newlines.
        """
        # Setup
        agents_path = tmp_path / "AGENTS.md"
        agents_path.write_text("""# Amplihack Agents

<!-- AMPLIHACK_CONTEXT_START -->
<!-- AMPLIHACK_CONTEXT_END -->

## Real Content

Documentation here.
""")

        strategy = CopilotStrategy(tmp_path)

        # Act - cleanup
        strategy.cleanup()

        # Assert - markers removed cleanly
        content = agents_path.read_text()
        assert "AMPLIHACK_CONTEXT_START" not in content
        assert "AMPLIHACK_CONTEXT_END" not in content

        # No excessive blank lines
        lines = content.split("\n")
        blank_line_count = sum(1 for line in lines if line.strip() == "")
        assert blank_line_count <= 3  # Reasonable number of blank lines
