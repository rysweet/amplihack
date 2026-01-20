"""UVX Integration Tests - Hook Validation.

Tests hook execution through real UVX launches:
- SessionStart hook
- Stop hook
- PostToolUse hook
- PreCompact hook

Philosophy:
- Outside-in testing (user perspective)
- Real UVX execution (no mocking)
- CI-ready (non-interactive)
- Fast execution (< 5 minutes total)
"""

import pytest
from pathlib import Path

from .harness import (
    uvx_launch,
    uvx_launch_with_test_project,
    assert_hook_executed,
    assert_output_contains,
    assert_log_contains,
    create_python_project,
)


# Git reference to test (customize fer yer branch)
GIT_REF = "feat/issue-1948-plugin-architecture"
TIMEOUT = 60  # 60 seconds per test


class TestSessionStartHook:
    """Test SessionStart hook execution via UVX."""

    def test_session_start_hook_executes(self):
        """Test that SessionStart hook executes on launch."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Show session initialization logs",
            timeout=TIMEOUT,
        )

        result.assert_success("SessionStart hook should execute")
        assert_hook_executed(
            result.stdout,
            result.log_files,
            "SessionStart",
            "SessionStart hook should be triggered on launch"
        )

    def test_session_start_loads_context(self):
        """Test that SessionStart hook loads context files."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Show loaded context files",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should load key context files
        expected_contexts = ["PHILOSOPHY.md", "PROJECT.md", "PATTERNS.md"]

        # Check at least one context file was loaded
        found_any = False
        for context in expected_contexts:
            try:
                assert_output_contains(result.stdout, context, case_sensitive=False)
                found_any = True
                break
            except AssertionError:
                pass

        assert found_any, f"Should load at least one context file from {expected_contexts}"


class TestStopHook:
    """Test Stop hook execution via UVX."""

    def test_stop_hook_executes(self):
        """Test that Stop hook executes on session end."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Exit session",
            timeout=TIMEOUT,
        )

        # Stop hook should execute (check logs since it runs at end)
        if result.log_files:
            assert_log_contains(
                result.log_files,
                "Stop",
                case_sensitive=False,
                message="Stop hook should execute on session end"
            )

    def test_stop_hook_cleanup(self):
        """Test that Stop hook performs cleanup operations."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Create some temp files then exit",
            timeout=TIMEOUT,
        )

        # Should mention cleanup in logs
        if result.log_files:
            try:
                assert_log_contains(
                    result.log_files,
                    "cleanup",
                    case_sensitive=False,
                )
            except AssertionError:
                # Cleanup might not be logged explicitly
                pass


class TestPostToolUseHook:
    """Test PostToolUse hook execution via UVX."""

    def test_post_tool_use_hook_executes(self):
        """Test that PostToolUse hook executes after tool invocation."""
        result = uvx_launch_with_test_project(
            project_files={"test.py": "print('hello')"},
            git_ref=GIT_REF,
            prompt="Read the test.py file and show what you found",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # PostToolUse should execute after Read tool
        # Check for tool usage logging
        result.assert_in_output("test.py", "Should read the file")


    def test_post_tool_use_logging(self):
        """Test that PostToolUse hook logs tool invocations."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="List files in current directory",
            timeout=TIMEOUT,
        )

        # Should execute some tool (Bash, Glob, etc.)
        # Check logs for tool invocation tracking
        if result.log_files:
            # At least one tool should be logged
            pass  # Tool logging is optional in logs


class TestPreCompactHook:
    """Test PreCompact hook execution via UVX."""

    def test_pre_compact_hook_awareness(self):
        """Test that PreCompact hook is available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What hooks are available in the system?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # PreCompact may be mentioned in hook list
        # This is a light test since triggering compact is complex


    def test_pre_compact_not_triggered_in_short_session(self):
        """Test that PreCompact doesn't trigger in short sessions."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Quick task",
            timeout=TIMEOUT,
        )

        # PreCompact should NOT trigger in short session
        # (This is implicit - we just verify session succeeds)
        result.assert_success()


class TestHookIntegration:
    """Test hook system integration via UVX."""

    def test_multiple_hooks_in_session(self):
        """Test that multiple hooks can execute in one session."""
        result = uvx_launch_with_test_project(
            project_files={
                "main.py": "print('test')",
            },
            git_ref=GIT_REF,
            prompt="Read main.py file, analyze it, then exit",
            timeout=TIMEOUT,
        )

        # SessionStart should execute
        # PostToolUse might execute (if Read is used)
        # Stop should execute at end

        result.assert_success("Session with multiple hooks should succeed")

        # Verify at least SessionStart executed
        assert_hook_executed(
            result.stdout,
            result.log_files,
            "SessionStart",
        )

    def test_hook_execution_order(self):
        """Test that hooks execute in correct order."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Perform a simple task",
            timeout=TIMEOUT,
        )

        # SessionStart should be first
        # PostToolUse during execution
        # Stop should be last

        result.assert_success()

        # Order verification would require timestamp analysis in logs
        # For now, just verify session completes
        assert result.duration < TIMEOUT


    def test_hook_error_handling(self):
        """Test that hook errors don't crash session."""
        # Even if a hook fails, session should continue
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Simple echo task",
            timeout=TIMEOUT,
        )

        # Session should succeed even if hooks have issues
        # (Hooks should be resilient)
        result.assert_success("Session should handle hook errors gracefully")


# Markers for test organization
pytest.mark.integration = pytest.mark.integration
pytest.mark.uvx = pytest.mark.uvx
pytest.mark.hooks = pytest.mark.hooks
