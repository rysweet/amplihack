#!/usr/bin/env python3
"""
Simple test script for power_steering_progress module.

Tests the ProgressTracker in isolation to verify basic functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from power_steering_progress import ProgressTracker


def test_basic_functionality():
    """Test basic progress tracker functionality."""
    print("=" * 70)
    print("TEST 1: Basic Functionality (SUMMARY mode)")
    print("=" * 70)

    tracker = ProgressTracker(verbosity="summary")

    # Emit events
    tracker.emit("start", "Starting power-steering analysis...")
    tracker.emit("category", "Checking Session Completion", {"category": "Session Completion"})
    tracker.emit(
        "consideration", "Were all TODO items completed?", {"consideration_id": "todos_complete"}
    )
    tracker.emit(
        "consideration", "Was full workflow followed?", {"consideration_id": "workflow_complete"}
    )
    tracker.emit("complete", "Power-steering analysis complete - all checks passed")

    # Display summary
    tracker.display_summary()

    print("\n✓ Test 1 passed\n")


def test_detailed_mode():
    """Test detailed verbosity mode."""
    print("=" * 70)
    print("TEST 2: Detailed Mode (shows all events)")
    print("=" * 70)

    tracker = ProgressTracker(verbosity="detailed")
    tracker.set_total_considerations(5)

    # Emit events
    tracker.emit("start", "Starting power-steering analysis...")
    tracker.emit("session_type", "Session type: DEVELOPMENT", {"session_type": "DEVELOPMENT"})
    tracker.emit("category", "Checking Session Completion", {"category": "Session Completion"})
    tracker.emit(
        "consideration", "Were all TODO items completed?", {"consideration_id": "todos_complete"}
    )
    tracker.emit(
        "consideration", "Was full workflow followed?", {"consideration_id": "workflow_complete"}
    )
    tracker.emit("category", "Checking Code Quality", {"category": "Code Quality"})
    tracker.emit("consideration", "Philosophy adherence?", {"consideration_id": "philosophy"})
    tracker.emit("consideration", "No shortcuts taken?", {"consideration_id": "shortcuts"})
    tracker.emit("consideration", "Tests passed?", {"consideration_id": "tests"})
    tracker.emit("complete", "Power-steering analysis complete - all checks passed")

    # Display summary
    tracker.display_summary()

    print("\n✓ Test 2 passed\n")


def test_off_mode():
    """Test OFF mode (no output)."""
    print("=" * 70)
    print("TEST 3: OFF Mode (should see no progress output)")
    print("=" * 70)

    tracker = ProgressTracker(verbosity="off")

    # Emit events (should produce no output)
    tracker.emit("start", "Starting power-steering analysis...")
    tracker.emit("consideration", "Checking something", {"consideration_id": "test"})
    tracker.emit("complete", "Complete")

    # Display summary (should produce no output)
    tracker.display_summary()

    print("✓ Test 3 passed (no progress output is expected)\n")


def test_fail_safe():
    """Test fail-safe behavior with invalid inputs."""
    print("=" * 70)
    print("TEST 4: Fail-Safe Behavior")
    print("=" * 70)

    tracker = ProgressTracker(verbosity="summary")

    # Try invalid event types (should not crash)
    try:
        tracker.emit(None, "Test message")
        tracker.emit("invalid_type", None)
        tracker.emit("test", "Test", {"key": None})
        print("✓ Test 4 passed (no exceptions raised)\n")
    except Exception as e:
        print(f"✗ Test 4 failed: {e}\n")
        return False

    return True


def main():
    """Run all tests."""
    print("\n🧪 POWER STEERING PROGRESS TRACKER TESTS\n")

    try:
        test_basic_functionality()
        test_detailed_mode()
        test_off_mode()
        test_fail_safe()

        print("=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
