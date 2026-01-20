#!/usr/bin/env python3
"""
Local test to verify Issue #2012 fix works correctly.

Tests that INFORMATIONAL Q&A sessions do not trigger the
"agent_unnecessary_questions" consideration.
"""
import sys
from pathlib import Path

# Add hooks to path
sys.path.insert(0, str(Path(__file__).parent / ".claude" / "tools" / "amplihack" / "hooks"))

from power_steering_checker import PowerSteeringChecker


def test_informational_session_filtering():
    """Test that INFORMATIONAL sessions skip agent_unnecessary_questions check."""

    # Create checker instance
    project_root = Path(__file__).parent
    checker = PowerSteeringChecker(project_root)

    # Get applicable considerations for INFORMATIONAL session
    applicable = checker.get_applicable_considerations("INFORMATIONAL")
    consideration_ids = {c["id"] for c in applicable}

    print("=" * 70)
    print("INFORMATIONAL Session - Applicable Considerations:")
    print("=" * 70)
    for c_id in sorted(consideration_ids):
        print(f"  ✓ {c_id}")

    print("\n" + "=" * 70)
    print("Verification Results:")
    print("=" * 70)

    # TEST 1: agent_unnecessary_questions should NOT be in the list
    if "agent_unnecessary_questions" in consideration_ids:
        print("❌ FAILED: agent_unnecessary_questions IS in INFORMATIONAL considerations")
        print("   This means the fix did NOT work!")
        return False
    else:
        print("✅ PASSED: agent_unnecessary_questions NOT in INFORMATIONAL considerations")
        print("   This is correct - Q&A sessions can have follow-up questions")

    # TEST 2: objective_completion SHOULD still be checked
    if "objective_completion" in consideration_ids:
        print("✅ PASSED: objective_completion IS in INFORMATIONAL considerations")
        print("   This is correct - we still check if the question was answered")
    else:
        print("❌ FAILED: objective_completion NOT in INFORMATIONAL considerations")
        return False

    print("\n" + "=" * 70)
    print("DEVELOPMENT Session - Applicable Considerations (for comparison):")
    print("=" * 70)

    # Get applicable considerations for DEVELOPMENT session
    dev_applicable = checker.get_applicable_considerations("DEVELOPMENT")
    dev_consideration_ids = {c["id"] for c in dev_applicable}

    # TEST 3: agent_unnecessary_questions SHOULD be in DEVELOPMENT
    if "agent_unnecessary_questions" in dev_consideration_ids:
        print("✅ PASSED: agent_unnecessary_questions IS in DEVELOPMENT considerations")
        print("   This is correct - dev sessions should avoid unnecessary questions")
    else:
        print("❌ FAILED: agent_unnecessary_questions NOT in DEVELOPMENT considerations")
        return False

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED - Fix working correctly!")
    print("=" * 70)

    return True


if __name__ == "__main__":
    success = test_informational_session_filtering()
    sys.exit(0 if success else 1)
