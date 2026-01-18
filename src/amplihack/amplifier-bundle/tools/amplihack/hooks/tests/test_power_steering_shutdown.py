#!/usr/bin/env python3
"""
TDD Tests for Power Steering Shutdown Fix

Tests power steering's graceful shutdown behavior when AMPLIHACK_SHUTDOWN_IN_PROGRESS
environment variable is set. These tests follow TDD principles - written BEFORE
implementation to define expected behavior.

Testing Pyramid Distribution:
- 60% Unit Tests: Individual function behavior with shutdown flag
- 30% Integration Tests: Complete shutdown sequence across all functions
- 10% E2E Tests: Exit timing and regression prevention

Philosophy:
- Ruthlessly Simple: Clear, focused tests with single responsibilities
- Zero-BS: All tests work, no stubs or placeholders
- Fail-Open: Shutdown behavior returns safe defaults that never block users
"""

import os

# Import the functions we're testing
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from claude_power_steering import (
    analyze_claims_sync,
    analyze_consideration_sync,
    analyze_if_addressed_sync,
    is_shutting_down,
)

# =============================================================================
# UNIT TESTS (60%)
# =============================================================================


class TestIsShuttingDown:
    """Unit tests for shutdown detection helper function.

    Tests the core helper that checks AMPLIHACK_SHUTDOWN_IN_PROGRESS env var.
    This is the foundational function that all sync wrappers depend on.
    """

    def test_returns_true_when_env_var_set(self):
        """Should return True when AMPLIHACK_SHUTDOWN_IN_PROGRESS=1"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        try:
            # ACT
            result = is_shutting_down()

            # ASSERT
            assert result is True, "Should detect shutdown when env var is '1'"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    def test_returns_false_when_env_var_not_set(self):
        """Should return False when AMPLIHACK_SHUTDOWN_IN_PROGRESS not set"""
        # ARRANGE - ensure env var is not set
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # ACT
        result = is_shutting_down()

        # ASSERT
        assert result is False, "Should not detect shutdown when env var absent"

    def test_returns_false_when_env_var_set_to_zero(self):
        """Should return False when AMPLIHACK_SHUTDOWN_IN_PROGRESS=0"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "0"

        try:
            # ACT
            result = is_shutting_down()

            # ASSERT
            assert result is False, "Should not detect shutdown when env var is '0'"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    def test_returns_false_when_env_var_set_to_empty_string(self):
        """Should return False when AMPLIHACK_SHUTDOWN_IN_PROGRESS=''"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = ""

        try:
            # ACT
            result = is_shutting_down()

            # ASSERT
            assert result is False, "Should not detect shutdown when env var is empty"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


class TestAnalyzeClaimsSyncShutdown:
    """Unit tests for analyze_claims_sync during shutdown.

    Tests that analyze_claims_sync returns empty list immediately during
    shutdown without starting async operations.
    """

    def test_returns_empty_list_during_shutdown(self):
        """Should return [] immediately when shutting down"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        delta_text = "Task complete! All tests passing."
        project_root = Path.cwd()

        try:
            # ACT
            start_time = time.time()
            result = analyze_claims_sync(delta_text, project_root)
            elapsed = time.time() - start_time

            # ASSERT
            assert result == [], "Should return empty list during shutdown"
            assert elapsed < 0.1, f"Should return immediately (<100ms), took {elapsed * 1000:.1f}ms"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    @patch("claude_power_steering.analyze_claims")
    def test_does_not_call_async_during_shutdown(self, mock_analyze_claims):
        """Should not invoke async analyze_claims when shutting down"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        mock_analyze_claims.return_value = AsyncMock(return_value=["claim"])

        try:
            # ACT
            result = analyze_claims_sync("some text", Path.cwd())

            # ASSERT
            assert result == [], "Should return [] without calling async"
            mock_analyze_claims.assert_not_called()
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    @patch("claude_power_steering.analyze_claims")
    @patch("claude_power_steering.asyncio.run")
    def test_calls_async_during_normal_operation(self, mock_asyncio_run, mock_analyze_claims):
        """Should call async analyze_claims during normal operation"""
        # ARRANGE - ensure NOT shutting down
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        mock_asyncio_run.return_value = ["detected claim"]

        # ACT
        result = analyze_claims_sync("Task complete!", Path.cwd())

        # ASSERT
        mock_asyncio_run.assert_called_once()
        assert result == ["detected claim"], "Should return async result during normal operation"


class TestAnalyzeIfAddressedSyncShutdown:
    """Unit tests for analyze_if_addressed_sync during shutdown.

    Tests that analyze_if_addressed_sync returns None immediately during
    shutdown without starting async operations.
    """

    def test_returns_none_during_shutdown(self):
        """Should return None immediately when shutting down"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        failure_id = "todos_complete"
        failure_reason = "3 TODOs remain incomplete"
        delta_text = "Completed all TODOs"
        project_root = Path.cwd()

        try:
            # ACT
            start_time = time.time()
            result = analyze_if_addressed_sync(failure_id, failure_reason, delta_text, project_root)
            elapsed = time.time() - start_time

            # ASSERT
            assert result is None, "Should return None during shutdown"
            assert elapsed < 0.1, f"Should return immediately (<100ms), took {elapsed * 1000:.1f}ms"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    @patch("claude_power_steering.analyze_if_addressed")
    def test_does_not_call_async_during_shutdown(self, mock_analyze_if_addressed):
        """Should not invoke async analyze_if_addressed when shutting down"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        mock_analyze_if_addressed.return_value = AsyncMock(return_value="evidence")

        try:
            # ACT
            result = analyze_if_addressed_sync(
                "todos_complete", "3 TODOs incomplete", "Completed all TODOs", Path.cwd()
            )

            # ASSERT
            assert result is None, "Should return None without calling async"
            mock_analyze_if_addressed.assert_not_called()
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    @patch("claude_power_steering.analyze_if_addressed")
    @patch("claude_power_steering.asyncio.run")
    def test_calls_async_during_normal_operation(self, mock_asyncio_run, mock_analyze_if_addressed):
        """Should call async analyze_if_addressed during normal operation"""
        # ARRANGE - ensure NOT shutting down
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        mock_asyncio_run.return_value = "Completed all TODOs via git commit"

        # ACT
        result = analyze_if_addressed_sync(
            "todos_complete", "3 TODOs incomplete", "Completed all TODOs", Path.cwd()
        )

        # ASSERT
        mock_asyncio_run.assert_called_once()
        assert result == "Completed all TODOs via git commit"


class TestAnalyzeConsiderationSyncShutdown:
    """Unit tests for analyze_consideration_sync during shutdown.

    Tests that analyze_consideration_sync returns (True, None) immediately
    during shutdown without starting async operations.
    """

    def test_returns_satisfied_tuple_during_shutdown(self):
        """Should return (True, None) immediately when shutting down"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        conversation = [{"role": "user", "content": "Hello"}]
        consideration = {
            "id": "tests_passing",
            "question": "Are all tests passing?",
            "description": "Verify test suite passes",
            "category": "Quality",
        }
        project_root = Path.cwd()

        try:
            # ACT
            start_time = time.time()
            satisfied, reason = analyze_consideration_sync(
                conversation, consideration, project_root
            )
            elapsed = time.time() - start_time

            # ASSERT
            assert satisfied is True, "Should return satisfied=True during shutdown"
            assert reason is None, "Should return reason=None during shutdown"
            assert elapsed < 0.1, f"Should return immediately (<100ms), took {elapsed * 1000:.1f}ms"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    @patch("claude_power_steering.analyze_consideration")
    def test_does_not_call_async_during_shutdown(self, mock_analyze_consideration):
        """Should not invoke async analyze_consideration when shutting down"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        mock_analyze_consideration.return_value = AsyncMock(return_value=(False, "reason"))

        try:
            # ACT
            satisfied, reason = analyze_consideration_sync(
                [{"role": "user", "content": "Hello"}],
                {"id": "test", "question": "Test?"},
                Path.cwd(),
            )

            # ASSERT
            assert satisfied is True, "Should return satisfied=True"
            assert reason is None, "Should return reason=None"
            mock_analyze_consideration.assert_not_called()
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    @patch("claude_power_steering.analyze_consideration")
    @patch("claude_power_steering.asyncio.run")
    def test_calls_async_during_normal_operation(
        self, mock_asyncio_run, mock_analyze_consideration
    ):
        """Should call async analyze_consideration during normal operation"""
        # ARRANGE - ensure NOT shutting down
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        mock_asyncio_run.return_value = (False, "Tests are failing")

        # ACT
        satisfied, reason = analyze_consideration_sync(
            [{"role": "user", "content": "Hello"}],
            {"id": "tests_passing", "question": "Tests pass?"},
            Path.cwd(),
        )

        # ASSERT
        mock_asyncio_run.assert_called_once()
        assert satisfied is False
        assert reason == "Tests are failing"


# =============================================================================
# INTEGRATION TESTS (30%)
# =============================================================================


class TestShutdownSequenceIntegration:
    """Integration tests for complete shutdown sequence.

    Tests that all three sync wrapper functions behave correctly during
    shutdown, ensuring fail-open behavior across the entire power steering
    system.
    """

    def test_all_sync_wrappers_return_safe_defaults_during_shutdown(self):
        """All sync wrappers should return safe defaults when shutting down"""
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        project_root = Path.cwd()
        conversation = [{"role": "user", "content": "Test"}]
        consideration = {"id": "test", "question": "Test?"}

        try:
            # ACT
            claims = analyze_claims_sync("Task complete!", project_root)
            evidence = analyze_if_addressed_sync(
                "todos_complete", "3 TODOs", "Completed", project_root
            )
            satisfied, reason = analyze_consideration_sync(
                conversation, consideration, project_root
            )

            # ASSERT
            assert claims == [], "analyze_claims_sync returns []"
            assert evidence is None, "analyze_if_addressed_sync returns None"
            assert satisfied is True, "analyze_consideration_sync returns satisfied=True"
            assert reason is None, "analyze_consideration_sync returns reason=None"
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    def test_fail_open_behavior_prevents_user_blocking(self):
        """Fail-open defaults should never block user from exiting.

        Tests that returned values follow fail-open philosophy:
        - Empty claims list = no completion claims detected
        - None evidence = no evidence of addressing failure
        - (True, None) = consideration assumed satisfied

        All of these allow power steering to proceed without blocking.
        """
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        try:
            # ACT
            claims = analyze_claims_sync("Critical bug found!", Path.cwd())
            evidence = analyze_if_addressed_sync(
                "critical_check", "Must fix", "Ignored it", Path.cwd()
            )
            satisfied, reason = analyze_consideration_sync(
                [{"role": "user", "content": "Bug exists"}],
                {"id": "no_bugs", "question": "Are there bugs?"},
                Path.cwd(),
            )

            # ASSERT - Verify fail-open behavior
            assert claims == [], "No claims detected during shutdown (fail-open)"
            assert evidence is None, "No evidence found during shutdown (fail-open)"
            assert satisfied is True, "Consideration satisfied during shutdown (fail-open)"
            assert reason is None, "No blocking reason during shutdown (fail-open)"

            # PHILOSOPHY CHECK: These values should never trigger a blocking message
            # in power steering's exit prevention logic
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    def test_shutdown_sequence_completes_within_budget(self):
        """Complete shutdown sequence should finish within 1 second.

        Integration test that verifies the complete shutdown sequence
        (all three sync wrappers) completes fast enough to support the
        2-3 second target exit time.
        """
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        project_root = Path.cwd()
        conversation = [{"role": "user", "content": "Test"}]
        consideration = {"id": "test", "question": "Test?"}

        try:
            # ACT
            start_time = time.time()

            # Simulate complete shutdown sequence
            _ = analyze_claims_sync("Done!", project_root)
            _ = analyze_if_addressed_sync("todos", "incomplete", "fixed", project_root)
            _ = analyze_consideration_sync(conversation, consideration, project_root)

            elapsed = time.time() - start_time

            # ASSERT
            assert elapsed < 1.0, (
                f"Shutdown sequence took {elapsed:.2f}s, should be <1.0s "
                f"to support 2-3s exit target"
            )
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    @patch("claude_power_steering.analyze_claims")
    @patch("claude_power_steering.analyze_if_addressed")
    @patch("claude_power_steering.analyze_consideration")
    def test_no_async_operations_started_during_shutdown(
        self, mock_consideration, mock_if_addressed, mock_claims
    ):
        """No async functions should be called when shutting down.

        Integration test verifying that shutdown bypasses ALL async
        operations across all sync wrapper functions.
        """
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        try:
            # ACT - Call all sync wrappers
            analyze_claims_sync("text", Path.cwd())
            analyze_if_addressed_sync("id", "reason", "delta", Path.cwd())
            analyze_consideration_sync(
                [{"role": "user", "content": "test"}],
                {"id": "test", "question": "test?"},
                Path.cwd(),
            )

            # ASSERT - No async functions called
            mock_claims.assert_not_called()
            mock_if_addressed.assert_not_called()
            mock_consideration.assert_not_called()
        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


# =============================================================================
# E2E TESTS (10%)
# =============================================================================


class TestEndToEndExitTiming:
    """End-to-end tests for exit timing and performance.

    Tests that verify the complete user experience:
    - Exit completes within 3 seconds during shutdown
    - No performance regression during normal operation
    """

    @pytest.mark.slow
    def test_exit_completes_within_three_seconds_during_shutdown(self):
        """E2E: Complete exit sequence should finish within 3 seconds.

        This test simulates a realistic exit scenario where power steering
        performs multiple checks before allowing exit. During shutdown,
        all checks should complete within 3 seconds total.

        Target: <3 seconds (user perception threshold for "fast")
        Current: ~10-13 seconds without fix (UNACCEPTABLE)
        Expected: <3 seconds with shutdown checks (GOOD)
        """
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        project_root = Path.cwd()

        # Simulate realistic power steering check sequence
        conversations = [[{"role": "user", "content": f"Conversation {i}"}] for i in range(5)]
        considerations = [{"id": f"check_{i}", "question": f"Check {i}?"} for i in range(10)]
        delta_texts = [f"Delta text {i}" for i in range(5)]

        try:
            # ACT
            start_time = time.time()

            # Simulate complete power steering exit sequence
            for delta in delta_texts:
                _ = analyze_claims_sync(delta, project_root)

                for i, conv in enumerate(conversations):
                    _ = analyze_if_addressed_sync(f"check_{i}", f"reason_{i}", delta, project_root)

            for conv in conversations:
                for consideration in considerations:
                    _ = analyze_consideration_sync(conv, consideration, project_root)

            elapsed = time.time() - start_time

            # ASSERT
            assert elapsed < 3.0, (
                f"Exit sequence took {elapsed:.2f}s, should be <3.0s for good UX. "
                f"Without fix: ~10-13s. Target: <3s."
            )

        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    @pytest.mark.slow
    @patch("claude_power_steering.CLAUDE_SDK_AVAILABLE", True)
    @patch("claude_power_steering.query")
    def test_no_timing_regression_during_normal_operation(self, mock_query):
        """E2E: Normal operation timing should not regress from shutdown checks.

        Verifies that adding is_shutting_down() checks does not slow down
        normal operation. The check is O(1) env var lookup, should add
        negligible overhead (<1ms per call).
        """
        # ARRANGE - ensure NOT shutting down
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # Mock SDK to return quickly (isolate shutdown check overhead)
        async def mock_query_response(*args, **kwargs):
            yield MagicMock(text="SATISFIED: All good")

        mock_query.return_value = mock_query_response()

        # ACT
        start_time = time.time()

        # Run single operation 100 times to measure overhead
        for _ in range(100):
            _ = is_shutting_down()

        elapsed = time.time() - start_time
        avg_per_call = (elapsed / 100) * 1000  # Convert to milliseconds

        # ASSERT
        assert avg_per_call < 1.0, (
            f"is_shutting_down() took {avg_per_call:.2f}ms average, "
            f"should be <1ms (env var lookup is O(1))"
        )

    @pytest.mark.slow
    def test_repeated_shutdown_checks_do_not_accumulate_delay(self):
        """E2E: Multiple shutdown checks should not accumulate delays.

        Tests that calling sync wrappers repeatedly during shutdown
        maintains consistent fast performance without degradation.
        """
        # ARRANGE
        os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        project_root = Path.cwd()

        try:
            # ACT - Call sync wrappers 50 times each
            start_time = time.time()

            for _ in range(50):
                analyze_claims_sync("text", project_root)
                analyze_if_addressed_sync("id", "reason", "delta", project_root)
                analyze_consideration_sync(
                    [{"role": "user", "content": "test"}],
                    {"id": "test", "question": "test?"},
                    project_root,
                )

            elapsed = time.time() - start_time

            # ASSERT - 150 calls (50 * 3 functions) should complete quickly
            assert elapsed < 1.0, (
                f"150 shutdown checks took {elapsed:.2f}s, should be <1.0s. "
                f"Each check should be <7ms average."
            )

        finally:
            # CLEANUP
            del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


# =============================================================================
# TEST CONFIGURATION
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_env_var():
    """Ensure AMPLIHACK_SHUTDOWN_IN_PROGRESS is cleaned up after each test.

    This fixture runs automatically for every test to prevent test pollution
    from env var state leaking between tests.
    """
    yield
    # Cleanup after test
    if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
        del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


# Mark slow tests for optional execution
def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow (run with 'pytest -m slow')")
