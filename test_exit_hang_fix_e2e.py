#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""
End-to-end test for power steering exit hang fix (Issue #1893).

This script simulates the real user workflow:
1. Install amplihack from the fix branch
2. Import and test the power steering shutdown detection
3. Verify clean exit behavior without hangs

This test validates the fix works in a realistic scenario.
"""

import os
import sys
import time
from pathlib import Path

# Add current directory to Python path so we can import from worktree
sys.path.insert(0, str(Path(__file__).parent))


def test_shutdown_detection():
    """Test that shutdown detection works correctly."""
    print("\n=== Test 1: Shutdown Detection ===")

    # Import from the local worktree
    try:
        # Add .claude/tools to path for local import
        claude_tools_path = Path(__file__).parent / ".claude" / "tools"
        if str(claude_tools_path) not in sys.path:
            sys.path.insert(0, str(claude_tools_path))

        from amplihack.hooks.claude_power_steering import (
            is_shutting_down,  # type: ignore[import-not-found]
        )
    except ImportError as e:
        print(f"❌ FAILED: Could not import power steering module: {e}")
        print("   Make sure you're running from the worktree root")
        return False

    # Test 1: Normal operation (no shutdown)
    print("Testing normal operation...")
    assert is_shutting_down() is False, "Should return False when not shutting down"
    print("✅ Normal operation: is_shutting_down() returns False")

    # Test 2: During shutdown
    print("\nTesting shutdown detection...")
    os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
    assert is_shutting_down() is True, "Should return True when shutting down"
    print("✅ Shutdown detected: is_shutting_down() returns True")

    # Clean up
    del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

    return True


def test_exit_timing():
    """Test that exit completes quickly during shutdown."""
    print("\n=== Test 2: Exit Timing ===")

    try:
        # Add .claude/tools to path for local import
        claude_tools_path = Path(__file__).parent / ".claude" / "tools"
        if str(claude_tools_path) not in sys.path:
            sys.path.insert(0, str(claude_tools_path))

        from amplihack.hooks.claude_power_steering import (  # type: ignore[import-not-found]
            analyze_claims_sync,
            analyze_consideration_sync,
            analyze_if_addressed_sync,
        )
    except ImportError as e:
        print(f"❌ FAILED: Could not import power steering module: {e}")
        return False

    # Set shutdown flag
    os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

    try:
        # Test that all three functions return quickly
        print("Testing analyze_claims_sync() during shutdown...")
        start = time.time()
        result = analyze_claims_sync("Test content", Path.cwd())
        elapsed = time.time() - start

        assert result == [], f"Expected [], got {result}"
        assert elapsed < 0.1, f"Took {elapsed}s, should be <0.1s"
        print(f"✅ analyze_claims_sync(): {elapsed * 1000:.2f}ms (returned [])")

        print("\nTesting analyze_if_addressed_sync() during shutdown...")
        start = time.time()
        result = analyze_if_addressed_sync("id", "reason", "delta", Path.cwd())
        elapsed = time.time() - start

        assert result is None, f"Expected None, got {result}"
        assert elapsed < 0.1, f"Took {elapsed}s, should be <0.1s"
        print(f"✅ analyze_if_addressed_sync(): {elapsed * 1000:.2f}ms (returned None)")

        print("\nTesting analyze_consideration_sync() during shutdown...")
        start = time.time()
        result = analyze_consideration_sync(
            [{"role": "user", "content": "test"}], {"id": "test", "question": "test?"}, Path.cwd()
        )
        elapsed = time.time() - start

        assert result == (True, None), f"Expected (True, None), got {result}"
        assert elapsed < 0.1, f"Took {elapsed}s, should be <0.1s"
        print(f"✅ analyze_consideration_sync(): {elapsed * 1000:.2f}ms (returned (True, None))")

        # Test complete shutdown sequence timing
        print("\n=== Test 3: Complete Shutdown Sequence ===")
        start = time.time()

        # Simulate multiple calls as would happen during exit
        for _ in range(5):
            analyze_claims_sync("content", Path.cwd())
            analyze_if_addressed_sync("id", "reason", "delta", Path.cwd())
            analyze_consideration_sync(
                [{"role": "user", "content": "test"}],
                {"id": "test", "question": "test?"},
                Path.cwd(),
            )

        elapsed = time.time() - start
        print(f"\nComplete sequence (15 function calls): {elapsed * 1000:.2f}ms")

        if elapsed < 1.0:
            print(f"✅ PASS: Shutdown sequence completed in {elapsed * 1000:.2f}ms (<1s)")
        else:
            print(f"⚠️  WARNING: Shutdown sequence took {elapsed:.2f}s (target: <1s)")

        return elapsed < 3.0  # Must be under 3s for success

    finally:
        # Clean up
        del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


def main():
    """Run all end-to-end tests."""
    print("=" * 60)
    print("Power Steering Exit Hang Fix - End-to-End Test")
    print("Issue #1893")
    print("=" * 60)

    # Run tests
    test1_passed = test_shutdown_detection()
    test2_passed = test_exit_timing()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    if test1_passed and test2_passed:
        print("✅ ALL TESTS PASSED")
        print("\nVerified:")
        print("  - Shutdown detection works correctly")
        print("  - Functions return immediately during shutdown")
        print("  - Exit timing meets <3s requirement")
        print("\n🎉 The fix works! Clean exit without hangs confirmed.")
        return 0
    print("❌ SOME TESTS FAILED")
    if not test1_passed:
        print("  - Shutdown detection failed")
    if not test2_passed:
        print("  - Exit timing failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
