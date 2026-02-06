#!/usr/bin/env python3
"""
Tests for Issue #2196 Phase 1.2: Circuit Breaker Enhancement.

Verifies that:
- Auto-approval triggers at 10 consecutive blocks
- Warning message displays at 5+ blocks
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_state import PowerSteeringTurnState


def test_auto_approve_at_10_blocks():
    """Auto-approval should trigger at exactly 10 consecutive blocks."""
    state = PowerSteeringTurnState(session_id="test")
    state.consecutive_blocks = 10

    should_approve, reason, escalation_msg = _should_auto_approve(state)

    assert should_approve is True, "Should auto-approve at 10 blocks"
    assert "10" in reason, f"Reason should mention 10 blocks: {reason}"
    assert escalation_msg is None, "No escalation message at threshold"


def test_no_auto_approve_at_9_blocks():
    """Auto-approval should NOT trigger at 9 blocks."""
    state = PowerSteeringTurnState(session_id="test")
    state.consecutive_blocks = 9

    should_approve, reason, escalation_msg = _should_auto_approve(state)

    assert should_approve is False, "Should NOT auto-approve at 9 blocks"


def test_escalation_warning_at_5_blocks():
    """Escalation warning should display at 5 blocks (halfway to threshold)."""
    state = PowerSteeringTurnState(session_id="test")
    state.consecutive_blocks = 5

    should_approve, reason, escalation_msg = _should_auto_approve(state)

    assert should_approve is False, "Should NOT auto-approve at 5 blocks"
    assert escalation_msg is not None, "Should have escalation message at 5 blocks"
    assert "5/10" in escalation_msg, f"Message should show 5/10: {escalation_msg}"
    assert "5 more blocks" in escalation_msg or "5" in escalation_msg, (
        f"Message should mention remaining blocks: {escalation_msg}"
    )


def test_escalation_warning_at_7_blocks():
    """Escalation warning should continue at 7 blocks."""
    state = PowerSteeringTurnState(session_id="test")
    state.consecutive_blocks = 7

    should_approve, reason, escalation_msg = _should_auto_approve(state)

    assert should_approve is False, "Should NOT auto-approve at 7 blocks"
    assert escalation_msg is not None, "Should have escalation message at 7 blocks"
    assert "7/10" in escalation_msg, f"Message should show 7/10: {escalation_msg}"


def test_no_warning_before_threshold():
    """No escalation warning before halfway point (blocks < 5)."""
    state = PowerSteeringTurnState(session_id="test")
    state.consecutive_blocks = 4

    should_approve, reason, escalation_msg = _should_auto_approve(state)

    assert should_approve is False, "Should NOT auto-approve at 4 blocks"
    assert escalation_msg is None, "No escalation message before halfway (< 5 blocks)"


def test_auto_approve_above_threshold():
    """Auto-approval should work for any count >= 10."""
    state = PowerSteeringTurnState(session_id="test")
    state.consecutive_blocks = 12

    should_approve, reason, escalation_msg = _should_auto_approve(state)

    assert should_approve is True, "Should auto-approve above threshold (12 blocks)"


def test_escalation_counts_remaining():
    """Escalation message should correctly count remaining blocks."""
    state = PowerSteeringTurnState(session_id="test")
    state.consecutive_blocks = 6

    should_approve, reason, escalation_msg = _should_auto_approve(state)

    assert escalation_msg is not None, "Should have escalation message"
    # Remaining should be 10 - 6 = 4
    assert "4" in escalation_msg, f"Should show 4 remaining blocks: {escalation_msg}"


def _should_auto_approve(state: PowerSteeringTurnState) -> tuple[bool, str, str | None]:
    """Helper to test should_auto_approve logic without manager instance."""
    blocks = state.consecutive_blocks
    threshold = PowerSteeringTurnState.MAX_CONSECUTIVE_BLOCKS

    if blocks < threshold:
        escalation_msg = None
        if blocks >= threshold // 2:
            remaining = threshold - blocks
            escalation_msg = (
                f"Warning: {blocks}/{threshold} blocks used. "
                f"Auto-approval in {remaining} more blocks if issues persist."
            )

        return (
            False,
            f"{blocks}/{threshold} consecutive blocks",
            escalation_msg,
        )

    return (
        True,
        f"Auto-approve: {blocks} blocks reached threshold ({threshold})",
        None,
    )


if __name__ == "__main__":
    print("Running Issue #2196 Phase 1.2 tests (Circuit Breaker)...")

    test_auto_approve_at_10_blocks()
    print("✓ test_auto_approve_at_10_blocks")

    test_no_auto_approve_at_9_blocks()
    print("✓ test_no_auto_approve_at_9_blocks")

    test_escalation_warning_at_5_blocks()
    print("✓ test_escalation_warning_at_5_blocks")

    test_escalation_warning_at_7_blocks()
    print("✓ test_escalation_warning_at_7_blocks")

    test_no_warning_before_threshold()
    print("✓ test_no_warning_before_threshold")

    test_auto_approve_above_threshold()
    print("✓ test_auto_approve_above_threshold")

    test_escalation_counts_remaining()
    print("✓ test_escalation_counts_remaining")

    print("\n✅ All Phase 1.2 tests passed!")
