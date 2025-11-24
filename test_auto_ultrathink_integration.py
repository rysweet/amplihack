#!/usr/bin/env python3
"""
Manual integration test for auto-ultrathink feature.

This script tests the complete integration of auto-ultrathink
in realistic scenarios.
"""

import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parent / ".claude" / "tools" / "amplihack" / "hooks" / "auto_ultrathink"))

from hook_integration import auto_ultrathink_hook


def test_scenario(name: str, prompt: str, expected_action: str):
    """Test a specific scenario."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"Input: {prompt}")

    result = auto_ultrathink_hook(
        prompt=prompt,
        context={"session_id": "test123"}
    )

    print(f"\nResult: {result[:200]}..." if len(result) > 200 else f"\nResult: {result}")
    print(f"Expected: {expected_action}")

    # Check if result matches expected behavior
    if expected_action == "INVOKE":
        success = result.startswith("/ultrathink")
        print(f"✅ PASS" if success else f"❌ FAIL")
    elif expected_action == "ASK":
        success = "💡 ULTRATHINK RECOMMENDATION" in result or "recommend" in result.lower()
        print(f"✅ PASS" if success else f"❌ FAIL")
    elif expected_action == "SKIP":
        success = result == prompt
        print(f"✅ PASS" if success else f"❌ FAIL")

    return success


def main():
    """Run all test scenarios."""
    print("="*60)
    print("AUTO-ULTRATHINK INTEGRATION TEST")
    print("="*60)

    results = []

    # Test 1: Feature implementation (should trigger)
    results.append(test_scenario(
        "Feature Implementation",
        "Add JWT authentication to the API",
        "INVOKE"
    ))

    # Test 2: Bug fix (should trigger)
    results.append(test_scenario(
        "Bug Fix",
        "Fix the memory leak in the user session handler",
        "INVOKE"
    ))

    # Test 3: Refactoring (should trigger)
    results.append(test_scenario(
        "Refactoring",
        "Refactor the authentication module to use dependency injection",
        "INVOKE"
    ))

    # Test 4: Question (should NOT trigger)
    results.append(test_scenario(
        "Question (Should Skip)",
        "How does the authentication system work?",
        "SKIP"
    ))

    # Test 5: Explanation request (should NOT trigger)
    results.append(test_scenario(
        "Explanation Request (Should Skip)",
        "Explain the purpose of the user_prompt_submit hook",
        "SKIP"
    ))

    # Test 6: Already has /ultrathink (should NOT trigger)
    results.append(test_scenario(
        "Already Has Ultrathink (Should Skip)",
        "/ultrathink implement authentication",
        "SKIP"
    ))

    # Test 7: Quick fix (should NOT trigger)
    results.append(test_scenario(
        "Quick Fix (Should Skip)",
        "Quick fix typo in readme.md",
        "SKIP"
    ))

    # Test 8: Simple edit (should NOT trigger)
    results.append(test_scenario(
        "Simple Edit (Should Skip)",
        "Update the version number in package.json to 1.2.3",
        "SKIP"
    ))

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"❌ {total - passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
