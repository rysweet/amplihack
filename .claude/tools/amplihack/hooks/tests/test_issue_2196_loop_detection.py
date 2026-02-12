#!/usr/bin/env python3
"""
Tests for Issue #2196 Phase 2A: Failure Fingerprinting & Loop Detection.

Verifies that:
- Fingerprints are correctly generated (SHA-256 hash of sorted consideration IDs)
- Loop detection triggers at 3+ identical fingerprints
- Order-independent hashing (same IDs in different order = same fingerprint)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_state import PowerSteeringTurnState


def test_fingerprint_generation():
    """Fingerprints should be 16-character hex strings."""
    state = PowerSteeringTurnState(session_id="test")

    failed_ids = ["todos_complete", "ci_status", "local_testing"]
    fingerprint = state.generate_failure_fingerprint(failed_ids)

    assert len(fingerprint) == 16, f"Fingerprint should be 16 chars: {fingerprint}"
    assert fingerprint.isalnum(), f"Fingerprint should be hex: {fingerprint}"
    # All hex digits are alphanumeric, so just check it's valid hex by trying to parse
    try:
        int(fingerprint, 16)
    except ValueError:
        assert False, f"Fingerprint should be valid hex: {fingerprint}"


def test_fingerprint_deterministic():
    """Same inputs should produce same fingerprint."""
    state = PowerSteeringTurnState(session_id="test")

    failed_ids = ["todos_complete", "ci_status"]
    fp1 = state.generate_failure_fingerprint(failed_ids)
    fp2 = state.generate_failure_fingerprint(failed_ids)

    assert fp1 == fp2, "Same inputs should produce same fingerprint"


def test_fingerprint_order_independent():
    """Different order of same IDs should produce same fingerprint."""
    state = PowerSteeringTurnState(session_id="test")

    ids_order1 = ["todos_complete", "ci_status", "local_testing"]
    ids_order2 = ["local_testing", "todos_complete", "ci_status"]
    ids_order3 = ["ci_status", "local_testing", "todos_complete"]

    fp1 = state.generate_failure_fingerprint(ids_order1)
    fp2 = state.generate_failure_fingerprint(ids_order2)
    fp3 = state.generate_failure_fingerprint(ids_order3)

    assert fp1 == fp2 == fp3, "Order should not affect fingerprint"


def test_fingerprint_different_for_different_ids():
    """Different consideration IDs should produce different fingerprints."""
    state = PowerSteeringTurnState(session_id="test")

    ids1 = ["todos_complete", "ci_status"]
    ids2 = ["todos_complete", "local_testing"]

    fp1 = state.generate_failure_fingerprint(ids1)
    fp2 = state.generate_failure_fingerprint(ids2)

    assert fp1 != fp2, "Different IDs should produce different fingerprints"


def test_loop_detection_at_threshold():
    """Loop should be detected when fingerprint appears >= 3 times."""
    state = PowerSteeringTurnState(session_id="test")

    failed_ids = ["todos_complete", "ci_status"]
    fingerprint = state.generate_failure_fingerprint(failed_ids)

    # Add fingerprint 3 times
    state.failure_fingerprints = [fingerprint, fingerprint, fingerprint]

    is_loop = state.detect_loop(fingerprint, threshold=3)
    assert is_loop is True, "Loop should be detected at threshold (3 occurrences)"


def test_loop_not_detected_below_threshold():
    """Loop should NOT be detected with only 2 occurrences."""
    state = PowerSteeringTurnState(session_id="test")

    failed_ids = ["todos_complete", "ci_status"]
    fingerprint = state.generate_failure_fingerprint(failed_ids)

    # Add fingerprint only 2 times
    state.failure_fingerprints = [fingerprint, fingerprint]

    is_loop = state.detect_loop(fingerprint, threshold=3)
    assert is_loop is False, "Loop should NOT be detected below threshold (2 occurrences)"


def test_loop_detection_with_mixed_fingerprints():
    """Loop detection should work correctly with different fingerprints mixed in."""
    state = PowerSteeringTurnState(session_id="test")

    failed_ids1 = ["todos_complete", "ci_status"]
    failed_ids2 = ["local_testing", "philosophy_compliance"]

    fp1 = state.generate_failure_fingerprint(failed_ids1)
    fp2 = state.generate_failure_fingerprint(failed_ids2)

    # Mix fingerprints: fp1, fp2, fp1, fp2, fp1
    state.failure_fingerprints = [fp1, fp2, fp1, fp2, fp1]

    # fp1 appears 3 times - should detect loop
    is_loop1 = state.detect_loop(fp1, threshold=3)
    assert is_loop1 is True, "Should detect loop for fp1 (3 occurrences)"

    # fp2 appears only 2 times - should NOT detect loop
    is_loop2 = state.detect_loop(fp2, threshold=3)
    assert is_loop2 is False, "Should NOT detect loop for fp2 (only 2 occurrences)"


def test_loop_detection_custom_threshold():
    """Loop detection should work with custom threshold."""
    state = PowerSteeringTurnState(session_id="test")

    failed_ids = ["todos_complete"]
    fingerprint = state.generate_failure_fingerprint(failed_ids)

    state.failure_fingerprints = [fingerprint, fingerprint]

    # Threshold of 2 should detect loop
    is_loop = state.detect_loop(fingerprint, threshold=2)
    assert is_loop is True, "Should detect loop with threshold=2"


def test_empty_fingerprints_list():
    """Loop detection should handle empty fingerprints list."""
    state = PowerSteeringTurnState(session_id="test")

    failed_ids = ["todos_complete"]
    fingerprint = state.generate_failure_fingerprint(failed_ids)

    state.failure_fingerprints = []

    is_loop = state.detect_loop(fingerprint, threshold=3)
    assert is_loop is False, "No loop with empty fingerprints list"


def test_single_consideration_fingerprint():
    """Fingerprinting should work with single consideration."""
    state = PowerSteeringTurnState(session_id="test")

    failed_ids = ["todos_complete"]
    fingerprint = state.generate_failure_fingerprint(failed_ids)

    assert len(fingerprint) == 16, "Single consideration should produce valid fingerprint"


def test_many_considerations_fingerprint():
    """Fingerprinting should work with many considerations."""
    state = PowerSteeringTurnState(session_id="test")

    failed_ids = [
        "todos_complete",
        "ci_status",
        "local_testing",
        "philosophy_compliance",
        "dev_workflow_complete",
        "next_steps",
        "docs_organization",
    ]
    fingerprint = state.generate_failure_fingerprint(failed_ids)

    assert len(fingerprint) == 16, "Many considerations should produce valid fingerprint"


def test_fingerprints_reset_on_approval():
    """Fingerprints should be cleared when approval is recorded."""
    from power_steering_state import TurnStateManager

    manager = TurnStateManager(
        project_root=Path("/tmp"),
        session_id="test",
    )

    state = PowerSteeringTurnState(session_id="test")
    state.consecutive_blocks = 5
    state.failure_fingerprints = ["abc123", "def456", "abc123"]

    # Record approval should reset fingerprints
    state = manager.record_approval(state)

    assert state.consecutive_blocks == 0, "Blocks should be reset"
    assert state.failure_fingerprints == [], "Fingerprints should be cleared"


if __name__ == "__main__":
    print("Running Issue #2196 Phase 2A tests (Loop Detection)...")

    test_fingerprint_generation()
    print("✓ test_fingerprint_generation")

    test_fingerprint_deterministic()
    print("✓ test_fingerprint_deterministic")

    test_fingerprint_order_independent()
    print("✓ test_fingerprint_order_independent")

    test_fingerprint_different_for_different_ids()
    print("✓ test_fingerprint_different_for_different_ids")

    test_loop_detection_at_threshold()
    print("✓ test_loop_detection_at_threshold")

    test_loop_not_detected_below_threshold()
    print("✓ test_loop_not_detected_below_threshold")

    test_loop_detection_with_mixed_fingerprints()
    print("✓ test_loop_detection_with_mixed_fingerprints")

    test_loop_detection_custom_threshold()
    print("✓ test_loop_detection_custom_threshold")

    test_empty_fingerprints_list()
    print("✓ test_empty_fingerprints_list")

    test_single_consideration_fingerprint()
    print("✓ test_single_consideration_fingerprint")

    test_many_considerations_fingerprint()
    print("✓ test_many_considerations_fingerprint")

    test_fingerprints_reset_on_approval()
    print("✓ test_fingerprints_reset_on_approval")

    print("\n✅ All Phase 2A tests passed!")
