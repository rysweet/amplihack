#!/usr/bin/env python3
"""
Comprehensive TDD tests for Issue #2155 (File Locking Implementation).

These tests follow TDD methodology - they MUST FAIL before the implementation exists
and PASS after file locking is added.

Test Coverage:
1. Unit Tests (60%): Lock acquisition, timeout, context manager
2. Race Condition Tests (20%): Concurrent increments, counter accuracy
3. Integration Tests (20%): Multiple stop hooks, platform support

Testing Focus:
- fcntl.flock() with 2s timeout
- Context manager pattern
- Windows graceful degradation
- Error handling (permission denied, timeout)
- Race condition prevention

Reference: docs/reference/power-steering-file-locking.md
"""

import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest  # type: ignore

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_state import PowerSteeringTurnState, TurnStateManager

# ============================================================================
# UNIT TESTS (60% of test pyramid)
# ============================================================================


class TestFileLockAcquisition:
    """Unit tests for file lock acquisition with fcntl.flock().

    THESE TESTS WILL FAIL until file locking is implemented.
    """

    def test_lock_acquired_during_save_state(self, tmp_path):
        """MUST FAIL: fcntl.flock() should be called during save_state().

        Expected behavior:
        - save_state() opens file
        - Acquires exclusive lock with fcntl.flock(fd, LOCK_EX | LOCK_NB)
        - Performs read-modify-write
        - Lock released when file closes

        Current behavior (BEFORE FIX):
        - No locking implemented
        - fcntl.flock() never called
        """
        # Patch at module level where it's actually used
        import power_steering_state

        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.LOCK_UN = 8

        # Patch both the module reference and LOCKING_AVAILABLE flag
        with patch.object(power_steering_state, "fcntl", mock_fcntl):
            with patch.object(power_steering_state, "LOCKING_AVAILABLE", True):
                manager = TurnStateManager(tmp_path, "test_session")
                state = PowerSteeringTurnState(session_id="test_session", turn_count=1)
                manager.save_state(state)

                # Verify fcntl.flock() was called
                assert mock_fcntl.flock.called, (
                    "fcntl.flock() MUST be called to acquire exclusive lock during save_state()"
                )

                # Verify correct flags used - check FIRST call (lock), not last (unlock)
                call_args_list = mock_fcntl.flock.call_args_list
                assert len(call_args_list) > 0, "flock should be called at least once"

                # First call should be the lock acquisition
                first_call_args = call_args_list[0][0]
                flags = first_call_args[1]  # Second argument is flags
                expected_flags = mock_fcntl.LOCK_EX | mock_fcntl.LOCK_NB
                assert flags == expected_flags, f"Should use LOCK_EX | LOCK_NB flags, got {flags}"

    def test_lock_uses_exclusive_mode(self, tmp_path):
        """MUST FAIL: Lock should use LOCK_EX for exclusive access.

        Only one process should be able to hold the lock at a time.
        """
        import power_steering_state

        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.LOCK_UN = 8

        with patch.object(power_steering_state, "fcntl", mock_fcntl):
            with patch.object(power_steering_state, "LOCKING_AVAILABLE", True):
                manager = TurnStateManager(tmp_path, "test_session")
                state = PowerSteeringTurnState(session_id="test_session", turn_count=1)
                manager.save_state(state)

                # Verify fcntl.flock() was called
                assert mock_fcntl.flock.called

                # Verify LOCK_EX flag used (not LOCK_SH) - check first call
                call_args_list = mock_fcntl.flock.call_args_list
                assert len(call_args_list) > 0, "flock should be called"

                first_call_args = call_args_list[0][0]
                flags = first_call_args[1]
                assert flags & mock_fcntl.LOCK_EX, "Must use LOCK_EX for exclusive access"

    def test_lock_uses_non_blocking_mode(self, tmp_path):
        """MUST FAIL: Lock should use LOCK_NB for non-blocking.

        Non-blocking mode raises BlockingIOError immediately if lock unavailable,
        allowing timeout logic to work correctly.
        """
        import power_steering_state

        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.LOCK_UN = 8

        with patch.object(power_steering_state, "fcntl", mock_fcntl):
            with patch.object(power_steering_state, "LOCKING_AVAILABLE", True):
                manager = TurnStateManager(tmp_path, "test_session")
                state = PowerSteeringTurnState(session_id="test_session", turn_count=1)
                manager.save_state(state)

                # Verify fcntl.flock() was called
                assert mock_fcntl.flock.called

                # Verify LOCK_NB flag used - check first call
                call_args_list = mock_fcntl.flock.call_args_list
                assert len(call_args_list) > 0, "flock should be called"

                first_call_args = call_args_list[0][0]
                flags = first_call_args[1]
                assert flags & mock_fcntl.LOCK_NB, "Must use LOCK_NB for non-blocking mode"

    def test_lock_released_on_file_close(self, tmp_path):
        """MUST FAIL: Lock should be released when file handle closes.

        Using context manager ensures lock is released automatically.
        """
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        # Track file operations
        files_opened = []
        files_closed = []

        original_open = open

        class TrackedFile:
            def __init__(self, file_obj):
                self.file = file_obj
                files_opened.append(id(self.file))

            def __enter__(self):
                return self.file.__enter__()

            def __exit__(self, *args):
                result = self.file.__exit__(*args)
                files_closed.append(id(self.file))
                return result

            def __getattr__(self, name):
                return getattr(self.file, name)

        def tracked_open(*args, **kwargs):
            return TrackedFile(original_open(*args, **kwargs))

        with patch("builtins.open", tracked_open):
            manager.save_state(state)

            # THIS WILL FAIL if context manager not used
            assert len(files_opened) > 0, "File should be opened"
            assert len(files_closed) > 0, "File should be closed (lock released)"


class TestFileLockTimeout:
    """Unit tests for 2-second timeout mechanism.

    THESE TESTS WILL FAIL until timeout logic is implemented.
    """

    def test_lock_timeout_after_2_seconds(self, tmp_path):
        """MUST FAIL: Lock acquisition should timeout after 2 seconds.

        Expected behavior:
        - Try to acquire lock with non-blocking flock()
        - If BlockingIOError, retry for up to 2 seconds
        - After 2s, log warning and proceed without lock (fail-open)

        Current behavior:
        - No timeout logic implemented
        """
        import power_steering_state

        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.LOCK_UN = 8

        # Simulate lock unavailable (always raises BlockingIOError)
        def raise_blocking_error(*args):
            raise BlockingIOError("Resource temporarily unavailable")

        mock_fcntl.flock.side_effect = raise_blocking_error

        with patch.object(power_steering_state, "fcntl", mock_fcntl):
            with patch.object(power_steering_state, "LOCKING_AVAILABLE", True):
                manager = TurnStateManager(tmp_path, "test_session")
                state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

                start_time = time.time()

                # Should timeout after ~2 seconds and proceed
                manager.save_state(state)

                elapsed = time.time() - start_time

                # Should have tried for approximately 2 seconds
                assert 1.8 <= elapsed <= 2.5, (
                    f"Should timeout after ~2 seconds, took {elapsed:.2f}s"
                )

                # Should have proceeded without lock (fail-open)
                # Verify state was saved despite lock failure
                loaded = manager.load_state()
                assert loaded.turn_count == 1, "Should save state despite lock timeout (fail-open)"

    def test_lock_retry_mechanism(self, tmp_path):
        """MUST FAIL: Should retry lock acquisition until timeout.

        Expected behavior:
        - First flock() attempt raises BlockingIOError
        - Retry with exponential backoff
        - Continue until 2s timeout
        """
        import power_steering_state

        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.LOCK_UN = 8

        # Count retry attempts
        attempt_count = [0]

        def counting_flock(*args):
            attempt_count[0] += 1
            raise BlockingIOError("Lock unavailable")

        mock_fcntl.flock.side_effect = counting_flock

        with patch.object(power_steering_state, "fcntl", mock_fcntl):
            with patch.object(power_steering_state, "LOCKING_AVAILABLE", True):
                manager = TurnStateManager(tmp_path, "test_session")
                state = PowerSteeringTurnState(session_id="test_session", turn_count=1)
                manager.save_state(state)

                # Should retry lock acquisition multiple times
                assert attempt_count[0] > 1, (
                    f"Should retry lock acquisition multiple times, got {attempt_count[0]} attempts"
                )

    def test_fail_open_on_lock_timeout(self, tmp_path):
        """MUST FAIL: Should proceed without lock after timeout (fail-open).

        Fail-open design: Never block user due to locking issues.
        """
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=42)

        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.flock.side_effect = BlockingIOError("Lock unavailable")

        with patch.dict("sys.modules", {"fcntl": mock_fcntl}):
            # Should NOT raise exception
            manager.save_state(state)

            # THIS WILL FAIL if timeout doesn't work
            # Verify state was saved (fail-open worked)
            loaded = manager.load_state()
            assert loaded.turn_count == 42, "Should save despite lock timeout"


class TestFileLockErrorHandling:
    """Unit tests for error handling in file locking.

    THESE TESTS WILL FAIL until error handling is implemented.
    """

    def test_handle_permission_denied_on_lock(self, tmp_path):
        """MUST FAIL: Should handle PermissionError gracefully.

        Expected: Log error, proceed without lock (fail-open)
        """
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.flock.side_effect = PermissionError("Permission denied")

        with patch.dict("sys.modules", {"fcntl": mock_fcntl}):
            # Should NOT raise exception (fail-open)
            manager.save_state(state)

            # THIS WILL FAIL
            # Verify state was saved despite permission error
            loaded = manager.load_state()
            assert loaded.turn_count == 1

    def test_handle_io_error_on_lock(self, tmp_path):
        """MUST FAIL: Should handle IOError gracefully.

        Expected: Log error, proceed without lock (fail-open)
        """
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.flock.side_effect = OSError("I/O error")

        with patch.dict("sys.modules", {"fcntl": mock_fcntl}):
            # Should NOT raise exception
            manager.save_state(state)

            # Verify state was saved
            loaded = manager.load_state()
            assert loaded.turn_count == 1

    def test_handle_os_error_on_lock(self, tmp_path):
        """MUST FAIL: Should handle generic OSError gracefully."""
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.flock.side_effect = OSError("Generic OS error")

        with patch.dict("sys.modules", {"fcntl": mock_fcntl}):
            manager.save_state(state)

            loaded = manager.load_state()
            assert loaded.turn_count == 1


class TestWindowsGracefulDegradation:
    """Unit tests for Windows platform support (graceful degradation).

    THESE TESTS WILL FAIL until Windows support is implemented.
    """

    def test_windows_fcntl_import_fails_gracefully(self, tmp_path):
        """MUST FAIL: Should handle missing fcntl module on Windows.

        Expected behavior:
        - Try to import fcntl
        - If ImportError (Windows), set LOCKING_AVAILABLE = False
        - Proceed without locking (graceful degradation)
        """
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        # Simulate Windows (fcntl not available)
        with patch.dict("sys.modules", {"fcntl": None}):
            # Should NOT raise exception
            # THIS WILL FAIL if Windows support not implemented
            manager.save_state(state)

            # Verify state was saved despite no locking
            loaded = manager.load_state()
            assert loaded.turn_count == 1, "Should work on Windows without locking"

    def test_windows_logs_degraded_mode_warning(self, tmp_path):
        """MUST FAIL: Should log warning when running in degraded mode.

        Windows users should be informed that locking is unavailable.
        """
        import power_steering_state

        log_messages = []

        def mock_log(msg):
            log_messages.append(msg)

        # Simulate Windows by disabling locking
        with patch.object(power_steering_state, "LOCKING_AVAILABLE", False):
            manager = TurnStateManager(tmp_path, "test_session", log=mock_log)
            state = PowerSteeringTurnState(session_id="test_session", turn_count=1)
            manager.save_state(state)

            # Should have logged warning about degraded mode
            degraded_warnings = [
                msg
                for msg in log_messages
                if "windows" in msg.lower()
                or "degraded" in msg.lower()
                or "locking unavailable" in msg.lower()
            ]

            assert len(degraded_warnings) > 0, "Should log warning about Windows degraded mode"

    def test_platform_detection_constant(self, tmp_path):
        """MUST FAIL: Should have LOCKING_AVAILABLE constant for platform detection.

        Implementation should check:
        try:
            import fcntl
            LOCKING_AVAILABLE = True
        except ImportError:
            LOCKING_AVAILABLE = False
        """
        # THIS WILL FAIL
        # Check if power_steering_state module has LOCKING_AVAILABLE
        import power_steering_state

        assert hasattr(power_steering_state, "LOCKING_AVAILABLE"), (
            "Should have LOCKING_AVAILABLE constant for platform detection"
        )


# ============================================================================
# RACE CONDITION TESTS (20% of test pyramid)
# ============================================================================


class TestRaceConditionPrevention:
    """Tests for race condition prevention with file locking.

    THESE TESTS WILL FAIL until file locking prevents race conditions.
    """

    def test_100_concurrent_increments_equal_100(self, tmp_path):
        """MUST FAIL: 100 concurrent increments should result in counter = 100.

        This is the CORE race condition test. Without locking:
        - Multiple threads read same value (e.g., 5)
        - All increment to 6
        - Counter resets or gets stuck

        With locking:
        - Each thread waits for exclusive access
        - Counter increments reliably: 0 → 1 → 2 → ... → 100
        """
        manager = TurnStateManager(tmp_path, "test_session")
        # Increase lock timeout for this stress test
        manager._lock_timeout_seconds = 10.0

        # Initialize state
        state = PowerSteeringTurnState(session_id="test_session", turn_count=0)
        manager.save_state(state)

        # Thread function: atomic increment with locking
        def increment_once():
            mgr = TurnStateManager(tmp_path, "test_session")
            # Increase timeout for this stress test to avoid fail-open timeouts
            mgr._lock_timeout_seconds = 10.0
            mgr.atomic_increment_turn()

        # Launch 100 concurrent threads
        threads = []
        for _ in range(100):
            t = threading.Thread(target=increment_once)
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # THIS WILL FAIL WITHOUT LOCKING
        # Verify final count is exactly 100
        final_state = manager.load_state()

        assert final_state.turn_count == 100, (
            f"100 concurrent increments should result in count=100, got {final_state.turn_count}. "
            f"This indicates a race condition - file locking is needed."
        )

    def test_concurrent_access_serialized(self, tmp_path):
        """MUST FAIL: Concurrent access should be serialized by locking.

        Verifies that operations don't overlap - lock forces sequential access.
        """
        manager = TurnStateManager(tmp_path, "test_session")

        state = PowerSteeringTurnState(session_id="test_session", turn_count=0)
        manager.save_state(state)

        # Track operation start/end times
        operations = []
        lock = threading.Lock()

        def slow_increment(thread_id):
            mgr = TurnStateManager(tmp_path, "test_session")

            with lock:
                operations.append({"thread": thread_id, "event": "start", "time": time.time()})

            # Slow operation - use atomic increment
            time.sleep(0.05)  # 50ms operation
            mgr.atomic_increment_turn()

            with lock:
                operations.append({"thread": thread_id, "event": "end", "time": time.time()})

        # Launch 10 concurrent threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=slow_increment, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # THIS WILL FAIL
        # Analyze operation timeline - should not have overlaps
        final_state = manager.load_state()
        assert final_state.turn_count == 10, (
            f"10 concurrent increments should result in count=10, got {final_state.turn_count}"
        )

    def test_stop_hook_concurrent_invocations(self, tmp_path):
        """MUST FAIL: Multiple stop hook invocations should not conflict.

        Simulates real scenario: Multiple stop hooks running concurrently
        (e.g., from different Claude Code instances or rapid succession).
        """
        manager = TurnStateManager(tmp_path, "test_session")

        state = PowerSteeringTurnState(session_id="test_session", turn_count=0)
        manager.save_state(state)

        # Simulate stop hook behavior: increment counter
        def simulate_stop_hook(hook_id):
            mgr = TurnStateManager(tmp_path, "test_session")

            # Stop hook increments power steering counter atomically
            mgr.atomic_increment_turn()

        # Launch 20 concurrent "stop hooks"
        threads = []
        for i in range(20):
            t = threading.Thread(target=simulate_stop_hook, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # THIS WILL FAIL
        final_state = manager.load_state()
        assert final_state.turn_count == 20, (
            f"20 concurrent stop hooks should increment counter to 20, got {final_state.turn_count}"
        )

    def test_lock_counter_concurrent_increments(self, tmp_path):
        """MUST FAIL: _increment_lock_counter should also be race-safe.

        The stop hook has TWO counters that need protection:
        1. Power steering counter (_increment_power_steering_counter)
        2. Lock mode counter (_increment_lock_counter)

        Both need file locking.
        """
        # Import stop hook module
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from stop import StopHook

        # Create stop hook with test project root
        hook = StopHook.__new__(StopHook)
        hook.project_root = tmp_path
        hook.log = lambda _message, _level="INFO": None

        # Initialize counter file
        counter_file = (
            tmp_path / ".claude" / "runtime" / "locks" / "test_session" / "lock_invocations.txt"
        )
        counter_file.parent.mkdir(parents=True, exist_ok=True)
        counter_file.write_text("0")

        # Concurrent increments
        def increment_once():
            h = StopHook.__new__(StopHook)
            h.project_root = tmp_path
            h.log = lambda message, level=None: None
            h._increment_lock_counter("test_session")

        threads = []
        for _ in range(50):
            t = threading.Thread(target=increment_once)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # THIS WILL FAIL
        final_count = int(counter_file.read_text().strip())
        assert final_count == 50, (
            f"50 concurrent lock counter increments should result in count=50, got {final_count}"
        )

    def test_power_steering_counter_concurrent_increments(self, tmp_path):
        """MUST FAIL: _increment_power_steering_counter should be race-safe."""
        from stop import StopHook

        hook = StopHook.__new__(StopHook)
        hook.project_root = tmp_path
        hook.log = lambda _message, _level="INFO": None

        # Initialize counter file
        counter_file = (
            tmp_path / ".claude" / "runtime" / "power-steering" / "test_session" / "session_count"
        )
        counter_file.parent.mkdir(parents=True, exist_ok=True)
        counter_file.write_text("0")

        def increment_once():
            h = StopHook.__new__(StopHook)
            h.project_root = tmp_path
            h.log = lambda message, level=None: None
            h._increment_power_steering_counter("test_session")

        threads = []
        for _ in range(50):
            t = threading.Thread(target=increment_once)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # THIS WILL FAIL
        final_count = int(counter_file.read_text().strip())
        assert final_count == 50, (
            f"50 concurrent PS counter increments should result in count=50, got {final_count}"
        )


# ============================================================================
# INTEGRATION TESTS (20% of test pyramid)
# ============================================================================


class TestIntegrationFileLocking:
    """Integration tests for file locking in real scenarios.

    THESE TESTS WILL FAIL until file locking is fully integrated.
    """

    def test_multiple_managers_concurrent_access(self, tmp_path):
        """MUST FAIL: Multiple TurnStateManager instances should coordinate via locks.

        Real scenario: Different parts of code creating separate manager instances.
        """
        # Create 5 separate manager instances
        managers = [TurnStateManager(tmp_path, "test_session") for _ in range(5)]

        # Initialize state
        state = PowerSteeringTurnState(session_id="test_session", turn_count=0)
        managers[0].save_state(state)

        # Each manager increments 10 times concurrently
        def increment_10_times(manager):
            for _ in range(10):
                manager.atomic_increment_turn()

        threads = []
        for mgr in managers:
            t = threading.Thread(target=increment_10_times, args=(mgr,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # THIS WILL FAIL
        # 5 managers x 10 increments = 50 total
        final_state = managers[0].load_state()
        assert final_state.turn_count == 50, (
            f"5 managers × 10 increments should result in count=50, got {final_state.turn_count}"
        )

    def test_rapid_succession_increments(self, tmp_path):
        """MUST FAIL: Rapid increments in quick succession should not conflict.

        Tests that lock acquisition/release is fast enough for rapid operations.
        """
        manager = TurnStateManager(tmp_path, "test_session")

        state = PowerSteeringTurnState(session_id="test_session", turn_count=0)
        manager.save_state(state)

        # Rapid increments (no sleep between operations)
        start_time = time.time()

        for _ in range(100):
            s = manager.load_state()
            s = manager.increment_turn(s)
            manager.save_state(s)

        elapsed = time.time() - start_time

        # THIS WILL FAIL
        final_state = manager.load_state()
        assert final_state.turn_count == 100, (
            f"100 rapid increments should result in count=100, got {final_state.turn_count}"
        )

        # Should complete reasonably fast (< 5 seconds)
        assert elapsed < 5.0, (
            f"100 increments took {elapsed:.2f}s - locking overhead may be too high"
        )

    def test_lock_released_after_exception(self, tmp_path):
        """MUST FAIL: Lock should be released even if exception occurs.

        Context manager ensures lock release on exception.
        """
        manager = TurnStateManager(tmp_path, "test_session")

        state = PowerSteeringTurnState(session_id="test_session", turn_count=0)
        manager.save_state(state)

        # Simulate exception during save
        with patch("json.dump", side_effect=ValueError("Simulated error")):
            try:
                manager.save_state(state)
            except ValueError:
                pass  # Expected

        # Lock should be released - next operation should succeed
        # THIS WILL FAIL if lock not released properly
        state2 = PowerSteeringTurnState(session_id="test_session", turn_count=1)
        manager.save_state(state2)  # Should NOT hang or fail

        final_state = manager.load_state()
        assert final_state.turn_count == 1, "Lock should be released after exception"

    def test_lock_timeout_allows_recovery(self, tmp_path):
        """MUST FAIL: After lock timeout, system should recover for next operation.

        Tests that timeout doesn't leave system in broken state.
        """
        manager = TurnStateManager(tmp_path, "test_session")

        state = PowerSteeringTurnState(session_id="test_session", turn_count=0)
        manager.save_state(state)

        # First operation: Simulate lock timeout
        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.flock.side_effect = BlockingIOError("Lock unavailable")

        with patch.dict("sys.modules", {"fcntl": mock_fcntl}):
            # Should timeout and proceed (fail-open)
            state1 = PowerSteeringTurnState(session_id="test_session", turn_count=1)
            manager.save_state(state1)

        # Second operation: Should work normally (no lingering issues)
        # THIS WILL FAIL if timeout leaves system in bad state
        state2 = manager.load_state()
        state2 = manager.increment_turn(state2)
        manager.save_state(state2)

        final_state = manager.load_state()
        assert final_state.turn_count == 2, "System should recover after lock timeout"


# ============================================================================
# LOGGING AND DIAGNOSTICS TESTS
# ============================================================================


class TestFileLockingLogging:
    """Tests for file locking diagnostics and logging.

    THESE TESTS WILL FAIL until logging is implemented.
    """

    def test_log_lock_acquisition_success(self, tmp_path):
        """MUST FAIL: Should log successful lock acquisition.

        Log format (JSONL):
        {"event": "lock_acquired", "timestamp": "...", "duration_ms": 15}
        """
        log_messages = []

        def mock_log(msg):
            log_messages.append(msg)

        manager = TurnStateManager(tmp_path, "test_session", log=mock_log)
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        # THIS WILL FAIL
        manager.save_state(state)

        # Check for lock acquisition log
        lock_acquired_logs = [
            msg
            for msg in log_messages
            if "lock" in msg.lower() and ("acquired" in msg.lower() or "success" in msg.lower())
        ]

        assert len(lock_acquired_logs) > 0, "Should log lock acquisition"

    def test_log_lock_timeout(self, tmp_path):
        """MUST FAIL: Should log lock timeout events.

        Log format:
        {"event": "lock_timeout", "timestamp": "...", "timeout_ms": 2000}
        """
        import power_steering_state

        log_messages = []

        def mock_log(msg):
            log_messages.append(msg)

        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.LOCK_UN = 8
        mock_fcntl.flock.side_effect = BlockingIOError("Lock unavailable")

        with patch.object(power_steering_state, "fcntl", mock_fcntl):
            with patch.object(power_steering_state, "LOCKING_AVAILABLE", True):
                manager = TurnStateManager(tmp_path, "test_session", log=mock_log)
                state = PowerSteeringTurnState(session_id="test_session", turn_count=1)
                manager.save_state(state)

                # Should log lock timeout
                timeout_logs = [
                    msg
                    for msg in log_messages
                    if "lock" in msg.lower() and "timeout" in msg.lower()
                ]

                assert len(timeout_logs) > 0, "Should log lock timeout"

    def test_log_windows_degraded_mode(self, tmp_path):
        """MUST FAIL: Should log Windows degraded mode (no locking)."""
        import power_steering_state

        log_messages = []

        def mock_log(msg):
            log_messages.append(msg)

        # Simulate Windows by disabling locking
        with patch.object(power_steering_state, "LOCKING_AVAILABLE", False):
            manager = TurnStateManager(tmp_path, "test_session", log=mock_log)
            state = PowerSteeringTurnState(session_id="test_session", turn_count=1)
            manager.save_state(state)

            # Should log at least once (not every operation, just info message)
            windows_logs = [
                msg
                for msg in log_messages
                if "windows" in msg.lower() or "locking unavailable" in msg.lower()
            ]

            assert len(windows_logs) > 0, "Should log Windows degraded mode"


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Create temporary directory for test isolation."""
    return tmp_path_factory.mktemp("test_file_locking")
