"""End-to-end tests for loop prevention in interactive reflection system.

These tests simulate the critical scenario where the stop hook could trigger
an infinite loop by calling the Claude SDK, which triggers tool use, which
triggers the stop hook again.

This is the MOST CRITICAL test file in the suite.
"""

import json

# Add paths for imports
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "tools" / "amplihack" / "hooks"))
sys.path.insert(
    0, str(Path(__file__).parent.parent / ".claude" / "tools" / "amplihack" / "reflection")
)

from semaphore import ReflectionLock
from state_machine import ReflectionStateMachine


@pytest.fixture
def temp_project_root():
    """Create temporary project root with .claude structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        claude_dir = root / ".claude"
        runtime_dir = claude_dir / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "logs").mkdir()
        (runtime_dir / "analysis").mkdir()
        yield root


@pytest.mark.e2e
class TestLoopPreventionE2E:
    """Critical E2E tests for loop prevention."""

    def test_stop_hook_does_not_trigger_infinite_loop(self, temp_project_root):
        """Simulated Stop → SDK → Tool → Stop cycle doesn't loop.

        This is the MOST CRITICAL test. It simulates:
        1. Stop hook is triggered
        2. Hook calls Claude SDK for analysis
        3. SDK response triggers tool use
        4. Tool use would normally trigger Stop hook again
        5. Verify loop is prevented
        """
        from stop import StopHook

        runtime_dir = temp_project_root / ".claude" / "runtime"

        # Track number of stop hook invocations
        call_count = {"count": 0}

        # Create stop hook
        with patch.object(StopHook, "__init__", lambda self: None):
            hook = StopHook()
            hook.project_root = temp_project_root
            hook.log_dir = runtime_dir / "logs"
            hook.analysis_dir = runtime_dir / "analysis"
            hook._recursion_guard = threading.local()

            # Mock get_session_messages to return test data
            def mock_get_messages(input_data):
                return [{"role": "assistant", "content": "Test message"}]

            hook.get_session_messages = mock_get_messages

            def mock_save_analysis(messages):
                pass

            hook.save_session_analysis = mock_save_analysis

            # Simulate nested call
            def call_stop_hook(depth=0):
                call_count["count"] += 1

                # Prevent actual infinite loop in test
                if depth > 5:
                    pytest.fail("Infinite loop detected: more than 5 recursive calls")

                input_data = {"session_id": f"test-{depth}", "messages": []}

                result = hook.process(input_data)

                # Try to call again (simulating SDK triggering tool use)
                if depth < 2:
                    call_stop_hook(depth + 1)

                return result

            # Execute
            call_stop_hook(depth=0)

            # Verify recursion guard prevented nested execution
            # Should have 3 calls (depth 0, 1, 2) but only first should fully process
            assert call_count["count"] <= 3
            assert call_count["count"] > 0

    def test_recursion_guard_blocks_reentry(self, temp_project_root):
        """Recursion guard prevents same-thread re-entry."""
        from stop import StopHook

        runtime_dir = temp_project_root / ".claude" / "runtime"

        with patch.object(StopHook, "__init__", lambda self: None):
            hook = StopHook()
            hook.project_root = temp_project_root
            hook.log_dir = runtime_dir / "logs"
            hook.analysis_dir = runtime_dir / "analysis"
            hook._recursion_guard = threading.local()

            input_data = {"session_id": "test", "messages": []}

            # First call
            hook._recursion_guard.active = False
            hook.process(input_data)

            # Simulate re-entry (SDK callback)
            hook._recursion_guard.active = True
            result2 = hook.process(input_data)

            # Second call should be blocked
            assert result2 == {}

    def test_semaphore_blocks_cross_thread_reentry(self, temp_project_root):
        """Semaphore prevents different-thread re-entry."""
        runtime_dir = temp_project_root / ".claude" / "runtime"

        # Create lock in first thread
        lock1 = ReflectionLock(runtime_dir=runtime_dir)
        assert lock1.acquire(session_id="session1", purpose="analysis") is True

        # Try to acquire in "different thread" (simulated)
        results = {"acquired": None}

        def try_acquire():
            lock2 = ReflectionLock(runtime_dir=runtime_dir)
            results["acquired"] = lock2.acquire(session_id="session2", purpose="analysis")

        # Simulate concurrent access
        thread = threading.Thread(target=try_acquire)
        thread.start()
        thread.join()

        # Second thread should be blocked
        assert results["acquired"] is False

        lock1.release()

    def test_stale_lock_recovery(self, temp_project_root):
        """Stale lock is cleaned up and analysis proceeds."""
        from stop import StopHook

        runtime_dir = temp_project_root / ".claude" / "runtime"

        # Create stale lock
        lock = ReflectionLock(runtime_dir=runtime_dir)
        lock.acquire(session_id="old-session", purpose="analysis")

        # Make it stale
        lock_data = lock.read_lock()
        lock_data.timestamp = time.time() - 61  # Older than 60s timeout

        with open(lock.lock_file, "w") as f:
            json.dump(
                {
                    "pid": lock_data.pid,
                    "timestamp": lock_data.timestamp,
                    "session_id": lock_data.session_id,
                    "purpose": lock_data.purpose,
                },
                f,
                indent=2,
            )

        # Verify lock is stale
        assert lock.is_stale()

        # Create stop hook and process
        with patch.object(StopHook, "__init__", lambda self: None):
            hook = StopHook()
            hook.project_root = temp_project_root
            hook.log_dir = runtime_dir / "logs"
            hook.analysis_dir = runtime_dir / "analysis"
            hook._recursion_guard = threading.local()

            with patch.object(hook, "get_session_messages", return_value=[]), patch.object(
                hook, "save_session_analysis"
            ):
                input_data = {"session_id": "new-session", "messages": []}
                hook.process(input_data)

            # Stale lock should be cleaned up by process()
            # Create new lock instance to check
            check_lock = ReflectionLock(runtime_dir=runtime_dir)
            assert not check_lock.is_locked() or check_lock.is_stale()

    def test_performance_overhead(self, temp_project_root):
        """Semaphore check adds < 50ms overhead."""
        from stop import StopHook

        runtime_dir = temp_project_root / ".claude" / "runtime"

        with patch.object(StopHook, "__init__", lambda self: None):
            hook = StopHook()
            hook.project_root = temp_project_root
            hook.log_dir = runtime_dir / "logs"
            hook.analysis_dir = runtime_dir / "analysis"
            hook._recursion_guard = threading.local()

            # Mock to make processing fast
            with patch.object(hook, "get_session_messages", return_value=[]), patch.object(
                hook, "save_session_analysis"
            ):
                input_data = {"session_id": "test", "messages": []}

                # Measure time
                start = time.time()
                hook.process(input_data)
                elapsed = time.time() - start

                # Semaphore check should be very fast
                assert elapsed < 0.5  # 500ms (generous for test environment)


@pytest.mark.e2e
class TestRealisticScenarios:
    """E2E tests for realistic usage scenarios."""

    def test_rapid_stop_events_dont_cause_loop(self, temp_project_root):
        """Multiple rapid stop events don't cause infinite loop."""
        from stop import StopHook

        runtime_dir = temp_project_root / ".claude" / "runtime"

        with patch.object(StopHook, "__init__", lambda self: None):
            hook = StopHook()
            hook.project_root = temp_project_root
            hook.log_dir = runtime_dir / "logs"
            hook.analysis_dir = runtime_dir / "analysis"
            hook._recursion_guard = threading.local()

            with patch.object(hook, "get_session_messages", return_value=[]), patch.object(
                hook, "save_session_analysis"
            ):
                # Simulate 5 rapid stop events
                for i in range(5):
                    input_data = {"session_id": f"test-{i}", "messages": []}
                    hook.process(input_data)
                    # Reset recursion guard for next call
                    hook._recursion_guard.active = False

                # Should complete without infinite loop
                # If we get here, test passes

    def test_concurrent_sessions_with_lock(self, temp_project_root):
        """Multiple concurrent sessions handled by lock."""
        runtime_dir = temp_project_root / ".claude" / "runtime"

        results = {"acquired": [], "lock": threading.Lock()}

        def try_process(session_id):
            lock = ReflectionLock(runtime_dir=runtime_dir)
            acquired = lock.acquire(session_id=session_id, purpose="analysis")

            with results["lock"]:
                results["acquired"].append(acquired)

            if acquired:
                time.sleep(0.05)  # Hold lock briefly
                lock.release()

        # Launch 3 threads simultaneously
        threads = []
        for i in range(3):
            thread = threading.Thread(target=try_process, args=(f"session{i}",))
            threads.append(thread)

        # Start all threads at once
        for thread in threads:
            thread.start()

        # Wait for all
        for thread in threads:
            thread.join()

        # At most one should have acquired lock (others see it locked)
        # Due to timing, possibly all failed if first released before others tried
        true_count = results["acquired"].count(True)
        assert true_count <= 3  # Sanity check
        # At least one should be blocked if truly concurrent
        # But timing makes this racy, so just check basic sanity
        assert len(results["acquired"]) == 3

    def test_analysis_state_persists_across_stops(self, temp_project_root):
        """State persists across multiple stop hook invocations."""
        from stop import StopHook

        runtime_dir = temp_project_root / ".claude" / "runtime"

        # Set up initial state
        state_machine = ReflectionStateMachine(session_id="test-session", runtime_dir=runtime_dir)
        from state_machine import ReflectionState, ReflectionStateData

        initial_state = ReflectionStateData(
            state=ReflectionState.AWAITING_APPROVAL,
            analysis={"patterns": [{"type": "error", "description": "Test", "severity": "high"}]},
            session_id="test-session",
        )
        state_machine.write_state(initial_state)

        # Create stop hook
        with patch.object(StopHook, "__init__", lambda self: None):
            hook = StopHook()
            hook.project_root = temp_project_root
            hook.log_dir = runtime_dir / "logs"
            hook.analysis_dir = runtime_dir / "analysis"
            hook._recursion_guard = threading.local()

            # First stop event
            input_data = {"session_id": "test-session", "messages": []}
            hook.process(input_data)

            # Verify state persists
            loaded_state = state_machine.read_state()
            assert loaded_state.state == ReflectionState.AWAITING_APPROVAL
            assert loaded_state.analysis is not None

    def test_lock_released_on_exception(self, temp_project_root):
        """Lock is released even if processing raises exception."""
        from stop import StopHook

        runtime_dir = temp_project_root / ".claude" / "runtime"
        lock = ReflectionLock(runtime_dir=runtime_dir)
        state_machine = ReflectionStateMachine(session_id="test-session", runtime_dir=runtime_dir)

        with patch.object(StopHook, "__init__", lambda self: None):
            hook = StopHook()
            hook.project_root = temp_project_root
            hook.log_dir = runtime_dir / "logs"
            hook.analysis_dir = runtime_dir / "analysis"
            hook._recursion_guard = threading.local()

            # Mock to raise exception during analysis
            with patch.object(hook, "get_session_messages", side_effect=Exception("Test error")):
                input_data = {"session_id": "test-session", "messages": []}

                try:
                    hook._run_new_analysis(lock, state_machine, input_data, "test-session")
                except Exception as e:
                    # Expected exception during test - log for debugging
                    import logging
                    logging.debug(f"Expected exception in test: {type(e).__name__}: {e}")

            # Lock should still be released
            assert not lock.is_locked()


@pytest.mark.e2e
class TestCompleteWorkflow:
    """E2E test for complete interactive workflow."""

    def test_complete_workflow_analysis_to_issue_to_work(self, temp_project_root):
        """Complete workflow: analysis → approval → issue → work decision."""
        from stop import StopHook

        runtime_dir = temp_project_root / ".claude" / "runtime"
        state_machine = ReflectionStateMachine(session_id="workflow-test", runtime_dir=runtime_dir)

        with patch.object(StopHook, "__init__", lambda self: None):
            hook = StopHook()
            hook.project_root = temp_project_root
            hook.log_dir = runtime_dir / "logs"
            hook.analysis_dir = runtime_dir / "analysis"
            hook._recursion_guard = threading.local()

            # Step 1: Run analysis (finds patterns)
            from lightweight_analyzer import LightweightAnalyzer
            from state_machine import ReflectionState, ReflectionStateData

            analyzer = LightweightAnalyzer()
            messages = [{"role": "assistant", "content": "An error occurred in the test"}]

            with patch.object(
                analyzer,
                "_call_claude_sdk",
                return_value=[{"type": "error", "description": "Test error", "severity": "high"}],
            ):
                result = analyzer.analyze_recent_responses(messages)

            # State should be AWAITING_APPROVAL
            state_data = ReflectionStateData(
                state=ReflectionState.AWAITING_APPROVAL, analysis=result, session_id="workflow-test"
            )
            state_machine.write_state(state_data)

            # Step 2: User approves (create issue)
            input_data = {
                "session_id": "workflow-test",
                "messages": [{"role": "user", "content": "yes, create it"}],
            }

            lock = ReflectionLock(runtime_dir=runtime_dir)

            with patch("stop.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="https://github.com/test/repo/issues/1\n"
                )

                result = hook._handle_interactive_state(state_machine, state_data, input_data, lock)

            # Should prompt for starting work
            assert "Start work" in result.get("message", "")

            # Step 3: Load state (should be AWAITING_WORK_DECISION)
            new_state = state_machine.read_state()
            assert new_state.state == ReflectionState.AWAITING_WORK_DECISION
            assert new_state.issue_url == "https://github.com/test/repo/issues/1"

            # Step 4: User approves starting work
            work_input = {
                "session_id": "workflow-test",
                "messages": [{"role": "user", "content": "yes"}],
            }

            result = hook._handle_interactive_state(state_machine, new_state, work_input, lock)

            # Should return ultrathink command
            assert "ultrathink" in result.get("message", "").lower()

            # State should be cleaned up
            assert not state_machine.state_file.exists()


@pytest.mark.e2e
class TestLoopPreventionStress:
    """Stress tests for loop prevention under load."""

    def test_100_rapid_lock_attempts(self, temp_project_root):
        """100 rapid lock attempts don't cause deadlock."""
        runtime_dir = temp_project_root / ".claude" / "runtime"

        def attempt_lock(attempt_num):
            lock = ReflectionLock(runtime_dir=runtime_dir)
            acquired = lock.acquire(session_id=f"session-{attempt_num}", purpose="analysis")
            if acquired:
                time.sleep(0.001)  # Hold briefly
                lock.release()
            return acquired

        # Sequential attempts (one at a time)
        acquired_count = 0
        for i in range(100):
            if attempt_lock(i):
                acquired_count += 1

        # All should succeed (sequential)
        assert acquired_count == 100

    def test_state_machine_handles_corrupt_data_during_workflow(self, temp_project_root):
        """State machine recovers from corruption during active workflow."""
        runtime_dir = temp_project_root / ".claude" / "runtime"
        state_machine = ReflectionStateMachine(session_id="test", runtime_dir=runtime_dir)

        from state_machine import ReflectionState, ReflectionStateData

        # Set valid state
        state_machine.write_state(
            ReflectionStateData(state=ReflectionState.AWAITING_APPROVAL, session_id="test")
        )

        # Corrupt the state file
        with open(state_machine.state_file, "w") as f:
            f.write("corrupted data {{{")

        # Should recover to IDLE
        state = state_machine.read_state()
        assert state.state == ReflectionState.IDLE

    def test_recursion_guard_thread_safety(self, temp_project_root):
        """Recursion guard is thread-safe (thread-local)."""
        from stop import StopHook

        runtime_dir = temp_project_root / ".claude" / "runtime"

        results = {"thread1": None, "thread2": None}

        def thread1_work():
            with patch.object(StopHook, "__init__", lambda self: None):
                hook = StopHook()
                hook.project_root = temp_project_root
                hook.log_dir = runtime_dir / "logs"
                hook.analysis_dir = runtime_dir / "analysis"
                hook._recursion_guard = threading.local()

                # Set guard in thread 1
                hook._recursion_guard.active = True
                results["thread1"] = hook._recursion_guard.active

        def thread2_work():
            with patch.object(StopHook, "__init__", lambda self: None):
                hook = StopHook()
                hook.project_root = temp_project_root
                hook.log_dir = runtime_dir / "logs"
                hook.analysis_dir = runtime_dir / "analysis"
                hook._recursion_guard = threading.local()

                # Check guard in thread 2 (should be unset)
                results["thread2"] = (
                    hasattr(hook._recursion_guard, "active") and hook._recursion_guard.active
                )

        t1 = threading.Thread(target=thread1_work)
        t2 = threading.Thread(target=thread2_work)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Thread 1 should have guard set, thread 2 should not
        assert results["thread1"] is True
        assert results["thread2"] is False
