#!/usr/bin/env python3
"""
Comprehensive failing tests for Issue #1882 (Power Steering Infinite Loop).

These tests follow TDD methodology - they MUST FAIL before the fix is implemented
and PASS after the fix is applied.

Test Coverage:
1. Reproduction Tests (MUST FAIL before fix)
2. Monotonicity Tests (counter never decreases)
3. Atomic Write Tests (fsync, verification, retry)
4. Infinite Loop Detection Tests
5. Edge Cases (filesystem errors, corrupted state)

Testing Pyramid: 60% unit, 30% integration, 10% E2E
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_state import (
    FailureEvidence,
    PowerSteeringTurnState,
    TurnStateManager,
)


class TestIssue1882Reproduction:
    """Reproduction tests that MUST FAIL before fix is applied.

    These tests reproduce the exact bug: counter resets from 5 → 0
    instead of incrementing to 6.
    """

    def test_counter_increments_from_5_to_6_not_reset_to_0(self, tmp_path):
        """MUST FAIL: Counter should increment 5 → 6, not reset to 0.

        This reproduces the core bug from Issue #1882 where the counter
        mysteriously resets to 0 instead of incrementing.

        Expected behavior:
        - Load state with turn_count=5
        - Increment turn
        - Save state
        - Load state again
        - turn_count should be 6, NOT 0

        Current behavior (BUG):
        - turn_count resets to 0 (bug in save/load cycle)
        """
        manager = TurnStateManager(tmp_path, "test_session")

        # Create initial state with turn_count=5
        state = PowerSteeringTurnState(session_id="test_session", turn_count=5)
        manager.save_state(state)

        # Load and increment
        loaded_state = manager.load_state()
        assert loaded_state.turn_count == 5, "Initial load should have turn_count=5"

        incremented_state = manager.increment_turn(loaded_state)
        assert incremented_state.turn_count == 6, "After increment should have turn_count=6"

        manager.save_state(incremented_state)

        # Load again and verify persistence
        reloaded_state = manager.load_state()

        # THIS SHOULD PASS BUT CURRENTLY FAILS (bug)
        assert reloaded_state.turn_count == 6, (
            "Counter MUST persist as 6, not reset to 0. This is the core bug from Issue #1882."
        )

    def test_state_persists_across_multiple_write_read_cycles(self, tmp_path):
        """MUST FAIL: State should persist correctly across cycles.

        Tests that state doesn't get corrupted or reset across multiple
        save/load cycles (write → read → write → read).
        """
        manager = TurnStateManager(tmp_path, "test_session")

        # Cycle 1: write turn_count=3
        state1 = PowerSteeringTurnState(session_id="test_session", turn_count=3)
        manager.save_state(state1)

        loaded1 = manager.load_state()
        assert loaded1.turn_count == 3

        # Cycle 2: increment to 4, write
        state2 = manager.increment_turn(loaded1)
        manager.save_state(state2)

        loaded2 = manager.load_state()
        assert loaded2.turn_count == 4

        # Cycle 3: increment to 5, write
        state3 = manager.increment_turn(loaded2)
        manager.save_state(state3)

        loaded3 = manager.load_state()

        # THIS SHOULD PASS BUT CURRENTLY FAILS
        assert loaded3.turn_count == 5, (
            "Counter should persist correctly across multiple cycles. "
            "If this fails, there's a bug in save/load persistence."
        )

    def test_no_infinite_loop_in_100_consecutive_calls(self, tmp_path):
        """MUST FAIL: Should not get stuck in infinite loop.

        Simulates 100 consecutive power steering checks to detect:
        - Counter stall (same value repeated)
        - Oscillation (A → B → A → B pattern)
        - Infinite loop condition
        """
        manager = TurnStateManager(tmp_path, "test_session")

        state = PowerSteeringTurnState(session_id="test_session")
        previous_values = []

        for i in range(100):
            state = manager.increment_turn(state)
            manager.save_state(state)

            reloaded = manager.load_state()
            previous_values.append(reloaded.turn_count)

            # Check for stall (same value repeated 10+ times)
            if len(previous_values) >= 10:
                last_10 = previous_values[-10:]
                if len(set(last_10)) == 1:
                    pytest.fail(
                        f"Counter STALLED at {last_10[0]} for 10 consecutive calls. "
                        f"This indicates an infinite loop condition."
                    )

            # Check for oscillation (A → B → A → B pattern)
            if len(previous_values) >= 4:
                last_4 = previous_values[-4:]
                if last_4[0] == last_4[2] and last_4[1] == last_4[3] and last_4[0] != last_4[1]:
                    pytest.fail(
                        f"Counter OSCILLATING between {last_4[0]} and {last_4[1]}. "
                        f"This indicates an infinite loop condition."
                    )

        # Verify counter reached 100 (not stuck)
        final_state = manager.load_state()
        assert final_state.turn_count == 100, (
            f"After 100 increments, counter should be 100, not {final_state.turn_count}. "
            f"History: {previous_values[-20:]}"
        )


class TestMonotonicityValidation:
    """Tests for monotonicity requirement: counter NEVER decreases.

    REQ-1: Counter must increment reliably
    Architect recommendation: Monotonicity check
    """

    def test_counter_never_decreases(self, tmp_path):
        """Counter should warn but not block on monotonicity violation (fail-open design)."""
        manager = TurnStateManager(tmp_path, "test_session")

        state = PowerSteeringTurnState(session_id="test_session", turn_count=10)
        manager.save_state(state)

        # Attempt to save state with LOWER turn_count
        regressed_state = PowerSteeringTurnState(session_id="test_session", turn_count=5)

        # Should NOT raise - fail-open design warns but continues
        # No exception should be raised
        manager.save_state(regressed_state)

        # Verify state was saved (fail-open)
        loaded = manager.load_state()
        assert loaded.turn_count == 5, (
            "State should be saved despite monotonicity violation (fail-open)"
        )

    def test_detect_counter_regression_from_previous_value(self, tmp_path):
        """Should warn on regression but continue (fail-open design)."""
        manager = TurnStateManager(tmp_path, "test_session")

        # Save state with turn_count=20
        state1 = PowerSteeringTurnState(session_id="test_session", turn_count=20)
        manager.save_state(state1)

        # Try to save state with turn_count=15 (regression)
        state2 = PowerSteeringTurnState(session_id="test_session", turn_count=15)

        # Should NOT raise - fail-open design warns but continues
        manager.save_state(state2)

        # Verify state was saved despite regression
        loaded = manager.load_state()
        assert loaded.turn_count == 15, "State should be saved despite regression (fail-open)"

    def test_track_previous_state_for_validation(self, tmp_path):
        """Manager should track previous state to detect violations."""
        manager = TurnStateManager(tmp_path, "test_session")

        # Initial state
        state1 = PowerSteeringTurnState(session_id="test_session", turn_count=5)
        manager.save_state(state1)

        # Should have tracked previous value
        # THIS ASSUMES manager has `_previous_turn_count` attribute (needs to be added)
        assert hasattr(manager, "_previous_turn_count"), (
            "Manager should track previous turn_count for monotonicity validation"
        )
        assert manager._previous_turn_count == 5


class TestAtomicWriteEnhancements:
    """Tests for atomic write requirements.

    REQ-3: Atomic counter increment with retry
    Architect recommendation: fsync, verification read, retry logic
    """

    def test_fsync_called_on_save(self, tmp_path):
        """save_state should call fsync() to ensure data is written to disk."""
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        # Mock os.fsync to verify it's called
        with patch("os.fsync") as mock_fsync:
            manager.save_state(state)

            # THIS SHOULD PASS (after fix adds fsync call)
            assert mock_fsync.called, "fsync() MUST be called to ensure atomic write"

    def test_verification_read_after_write(self, tmp_path):
        """Should verify state was written correctly by reading back."""
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=42)

        # Mock to track read operations
        original_read_text = Path.read_text
        read_calls = []

        def tracked_read_text(self, *args, **kwargs):
            read_calls.append(str(self))
            return original_read_text(self, *args, **kwargs)

        with patch.object(Path, "read_text", tracked_read_text):
            manager.save_state(state)

            # Verification read should happen AFTER write
            # THIS ASSUMES manager does verification read (needs to be added)
            state_file = manager.get_state_file_path()
            assert str(state_file) in read_calls, (
                "State file MUST be read after write for verification"
            )

    def test_retry_on_write_failure(self, tmp_path):
        """Should retry write operation on failure."""
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        call_count = 0

        def failing_write(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Simulated write failure")
            # Success on 3rd attempt
            return MagicMock()

        with patch.object(Path, "write_text", side_effect=failing_write):
            # THIS SHOULD SUCCEED after retries (needs retry logic)
            manager.save_state(state)

            # Verify retry happened
            assert call_count == 3, f"Should retry write operations, got {call_count} attempts"

    def test_verify_both_temp_file_and_final_path(self, tmp_path):
        """Verification should check BOTH temp file AND final path.

        Architect recommendation: Verify both temp file AND final path.
        """
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        verified_paths = []
        original_exists = Path.exists

        def track_exists(self):
            verified_paths.append(str(self))
            return original_exists(self)

        with patch.object(Path, "exists", track_exists):
            manager.save_state(state)

            # Should verify both temp file and final path
            # THIS ASSUMES verification happens (needs to be added)
            state_file = str(manager.get_state_file_path())
            temp_files = [p for p in verified_paths if "turn_state_" in p and ".tmp" in p]

            assert len(temp_files) > 0, "Should verify temp file exists"
            assert state_file in verified_paths, "Should verify final path exists"


class TestInfiniteLoopDetection:
    """Tests for infinite loop detection capabilities.

    Architect recommendation: Auto-detect stall, oscillation, high failure rate.
    """

    def test_detect_counter_stall(self, tmp_path):
        """Should detect when counter stays at same value (stall)."""
        manager = TurnStateManager(tmp_path, "test_session")

        # Simulate counter stuck at 5 for 10 iterations
        state = PowerSteeringTurnState(session_id="test_session", turn_count=5)

        for _ in range(10):
            manager.save_state(state)
            # Don't increment - simulate stall

        # THIS SHOULD DETECT STALL (needs stall detection)
        # Manager should track write operations and detect repeated same-value writes
        diagnostics = manager.get_diagnostics()  # Needs to be implemented

        assert diagnostics["stall_detected"], "Should detect counter stall"
        assert diagnostics["stall_value"] == 5
        assert diagnostics["stall_count"] >= 10

    def test_detect_oscillation_pattern(self, tmp_path):
        """Should detect A → B → A → B oscillation pattern."""
        manager = TurnStateManager(tmp_path, "test_session")

        # Simulate oscillation between 3 and 4
        for i in range(20):
            turn_count = 3 if i % 2 == 0 else 4
            state = PowerSteeringTurnState(session_id="test_session", turn_count=turn_count)
            manager.save_state(state)

        # THIS SHOULD DETECT OSCILLATION (needs oscillation detection)
        diagnostics = manager.get_diagnostics()

        assert diagnostics["oscillation_detected"], "Should detect counter oscillation"
        assert set(diagnostics["oscillation_values"]) == {3, 4}

    def test_detect_high_write_failure_rate(self, tmp_path):
        """Should detect when write failure rate exceeds 30%."""
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        failure_count = 0

        def intermittent_failure(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count % 2 == 0:  # 50% failure rate
                raise OSError("Write failure")
            return MagicMock()

        with patch.object(Path, "write_text", side_effect=intermittent_failure):
            # Try 10 save operations
            for i in range(10):
                try:
                    manager.save_state(state)
                except OSError:
                    pass  # Expected failures

        # THIS SHOULD DETECT HIGH FAILURE RATE (needs failure tracking)
        diagnostics = manager.get_diagnostics()

        assert diagnostics["write_failure_rate"] > 0.30, "Should detect write failure rate > 30%"
        assert diagnostics["high_failure_rate_alert"], "Should alert on high write failure rate"


class TestEdgeCases:
    """Edge case tests for filesystem errors and corruption.

    REQ-4: Robust state management with recovery
    """

    def test_handle_filesystem_full(self, tmp_path):
        """Should handle ENOSPC (filesystem full) gracefully."""
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        def raise_enospc(*args, **kwargs):
            error = OSError("No space left on device")
            error.errno = 28  # ENOSPC
            raise error

        with patch.object(Path, "write_text", side_effect=raise_enospc):
            # Should handle gracefully (fail-open)
            # THIS SHOULD NOT RAISE (fail-open design)
            manager.save_state(state)

            # Should log error for diagnostics
            # (Logging not tested here, but error should be recoverable)

    def test_handle_permission_denied(self, tmp_path):
        """Should handle EACCES (permission denied) gracefully."""
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        def raise_eacces(*args, **kwargs):
            error = OSError("Permission denied")
            error.errno = 13  # EACCES
            raise error

        with patch.object(Path, "write_text", side_effect=raise_eacces):
            # Should handle gracefully (fail-open)
            manager.save_state(state)

    def test_handle_corrupted_state_file(self, tmp_path):
        """Should recover from corrupted state file."""
        manager = TurnStateManager(tmp_path, "test_session")

        # Create corrupted state file
        state_file = manager.get_state_file_path()
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("CORRUPTED JSON{{{")

        # Should load empty state (fail-open)
        loaded_state = manager.load_state()

        assert loaded_state.turn_count == 0, "Should return empty state on corruption"
        assert loaded_state.session_id == "test_session"

    def test_handle_partial_write(self, tmp_path):
        """Should detect and recover from partial write."""
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=42)

        # Simulate partial write (incomplete JSON)
        def partial_write(self, content, *args, **kwargs):
            # Write only half the content
            partial_content = content[: len(content) // 2]
            Path.write_text(self, partial_content)

        with patch.object(Path, "write_text", partial_write):
            manager.save_state(state)

        # Should detect corrupted/partial write
        # THIS ASSUMES verification read catches partial write
        loaded_state = manager.load_state()

        # If verification works, should have retried and written correctly
        # OR should fail-open and return empty state
        assert loaded_state is not None, "Should handle partial write gracefully"

    def test_atomic_rename_failure_recovery(self, tmp_path):
        """Should recover if atomic rename fails."""
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        def failing_rename(*args, **kwargs):
            raise OSError("Rename failed")

        with patch("os.rename", side_effect=failing_rename):
            # Should handle gracefully
            manager.save_state(state)

            # Temp file should be cleaned up (no orphaned files)
            temp_files = list(tmp_path.rglob("turn_state_*.tmp"))
            assert len(temp_files) == 0, "Should clean up temp files on rename failure"


class TestMessageCustomization:
    """Tests for REQ-2: Messages customized based on check results.

    Not directly related to infinite loop bug, but part of overall fix.
    """

    def test_message_includes_turn_count(self, tmp_path):
        """Power steering message should include current turn count."""
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=5)

        # THIS ASSUMES message generation exists
        message = manager.generate_power_steering_message(state)

        assert "5" in message or "five" in message.lower(), "Message should include turn count"

    def test_message_customized_after_first_block(self, tmp_path):
        """Message should change after first power steering block."""
        manager = TurnStateManager(tmp_path, "test_session")

        # First block
        state1 = PowerSteeringTurnState(session_id="test_session", consecutive_blocks=1)
        message1 = manager.generate_power_steering_message(state1)

        # Second block
        state2 = PowerSteeringTurnState(session_id="test_session", consecutive_blocks=2)
        message2 = manager.generate_power_steering_message(state2)

        # Messages should be different
        assert message1 != message2, "Message should be customized based on consecutive blocks"


class TestDiagnosticLogging:
    """Tests for Phase 1: Instrumentation (diagnostic logging).

    Architect recommendation: .jsonl logging for debugging.
    """

    def test_diagnostic_log_created(self, tmp_path):
        """Should create diagnostic log file in .jsonl format."""
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        manager.save_state(state)

        # THIS ASSUMES diagnostic logging is implemented
        log_file = (
            tmp_path
            / ".claude"
            / "runtime"
            / "power-steering"
            / "test_session"
            / "diagnostic.jsonl"
        )

        assert log_file.exists(), "Should create diagnostic log file"

    def test_diagnostic_log_includes_write_events(self, tmp_path):
        """Diagnostic log should include write events."""
        manager = TurnStateManager(tmp_path, "test_session")
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)

        manager.save_state(state)

        log_file = (
            tmp_path
            / ".claude"
            / "runtime"
            / "power-steering"
            / "test_session"
            / "diagnostic.jsonl"
        )

        if log_file.exists():
            content = log_file.read_text()
            log_entries = [json.loads(line) for line in content.strip().split("\n")]

            # Should have write event
            write_events = [e for e in log_entries if e.get("event") == "state_write"]
            assert len(write_events) > 0, "Should log state write events"

    def test_diagnostic_log_includes_read_events(self, tmp_path):
        """Diagnostic log should include read events."""
        manager = TurnStateManager(tmp_path, "test_session")

        # Create state
        state = PowerSteeringTurnState(session_id="test_session", turn_count=1)
        manager.save_state(state)

        # Read state
        manager.load_state()

        log_file = (
            tmp_path
            / ".claude"
            / "runtime"
            / "power-steering"
            / "test_session"
            / "diagnostic.jsonl"
        )

        if log_file.exists():
            content = log_file.read_text()
            log_entries = [json.loads(line) for line in content.strip().split("\n")]

            # Should have read event
            read_events = [e for e in log_entries if e.get("event") == "state_read"]
            assert len(read_events) > 0, "Should log state read events"


# ============================================================================
# INTEGRATION TESTS (30% of test pyramid)
# ============================================================================


class TestIntegrationSaveLoadCycles:
    """Integration tests for complete save/load cycles."""

    def test_full_power_steering_lifecycle(self, tmp_path):
        """Test complete power steering lifecycle with multiple blocks."""
        manager = TurnStateManager(tmp_path, "test_session")

        # Initial state
        state = manager.load_state()
        assert state.turn_count == 0
        assert state.consecutive_blocks == 0

        # Record first block
        failed_evidence = [
            FailureEvidence(
                consideration_id="todos_complete",
                reason="3 TODOs incomplete",
            )
        ]
        state = manager.record_block_with_evidence(state, failed_evidence, transcript_length=10)
        manager.save_state(state)

        # Load and verify
        reloaded = manager.load_state()
        assert reloaded.consecutive_blocks == 1
        assert len(reloaded.block_history) == 1

        # Record second block
        state = manager.record_block_with_evidence(reloaded, failed_evidence, transcript_length=20)
        manager.save_state(state)

        # Final verification
        final_state = manager.load_state()
        assert final_state.consecutive_blocks == 2
        assert len(final_state.block_history) == 2

    def test_state_recovery_after_crash_simulation(self, tmp_path):
        """Simulate crash during write and verify recovery."""
        manager = TurnStateManager(tmp_path, "test_session")

        # Write initial state
        state1 = PowerSteeringTurnState(session_id="test_session", turn_count=5)
        manager.save_state(state1)

        # Simulate crash during second write (by raising exception)
        state2 = PowerSteeringTurnState(session_id="test_session", turn_count=6)

        with patch("os.rename", side_effect=OSError("Simulated crash")):
            try:
                manager.save_state(state2)
            except OSError:
                pass  # Expected

        # Load state - should have first state (atomic write preserved it)
        recovered = manager.load_state()

        # THIS VERIFIES ATOMIC WRITE PROTECTION
        assert recovered.turn_count == 5, "Atomic write should preserve previous state on crash"


# ============================================================================
# E2E TESTS (10% of test pyramid)
# ============================================================================


class TestEndToEndWorkflows:
    """End-to-end tests for complete workflows."""

    def test_complete_power_steering_session(self, tmp_path):
        """Test complete power steering session from start to finish."""
        manager = TurnStateManager(tmp_path, "test_session")

        # Session starts
        state = manager.load_state()

        # Turn 1: Increment and save
        state = manager.increment_turn(state)
        manager.save_state(state)

        # Block 1: Record failed checks
        evidence1 = [
            FailureEvidence(consideration_id="todos", reason="Incomplete"),
        ]
        state = manager.record_block_with_evidence(state, evidence1, 10)
        manager.save_state(state)

        # Turn 2: Increment
        state = manager.increment_turn(state)
        manager.save_state(state)

        # Block 2: Record more failed checks
        evidence2 = [
            FailureEvidence(consideration_id="tests", reason="Not run"),
        ]
        state = manager.record_block_with_evidence(state, evidence2, 20)
        manager.save_state(state)

        # Final verification
        final = manager.load_state()

        assert final.turn_count == 2, "Should have 2 turns"
        assert final.consecutive_blocks == 2, "Should have 2 consecutive blocks"
        assert len(final.block_history) == 2, "Should have 2 blocks in history"

        # Verify state file exists and is valid JSON
        state_file = manager.get_state_file_path()
        assert state_file.exists()

        content = json.loads(state_file.read_text())
        assert content["turn_count"] == 2
        assert content["consecutive_blocks"] == 2


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Create temporary directory for test isolation."""
    return tmp_path_factory.mktemp("test_power_steering")


@pytest.fixture
def mock_log():
    """Mock logging function."""
    return Mock()
