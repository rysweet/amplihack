#!/usr/bin/env python3
"""
Integration test for workflow classification reminder hook.

Simulates real Claude Code hook invocation to verify:
1. Hook loads correctly
2. System reminder appears on new topics
3. No reminder on follow-ups
4. State persists between invocations
"""

import sys
import unittest.mock
from pathlib import Path

# Add hook directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_classification_reminder import WorkflowClassificationReminder


def simulate_hook_call(user_message: str, turn_count: int) -> dict:
    """Simulate Claude Code calling the hook."""
    # Mock the parent class initialization
    with unittest.mock.patch.object(WorkflowClassificationReminder, "_init_state_dir"):
        hook = WorkflowClassificationReminder()

    # Set up test environment
    hook._state_dir = Path("/tmp/integration_test_classification_state")
    hook._state_dir.mkdir(parents=True, exist_ok=True)
    hook.get_session_id = lambda: "integration_test_session"

    input_data = {"userMessage": user_message, "turnCount": turn_count}

    return hook.process(input_data)


def print_result(scenario: str, result: dict, expected_reminder: bool):
    """Print test result."""
    has_reminder = "NEW TOPIC DETECTED" in result.get("additionalContext", "")

    status = "✓" if has_reminder == expected_reminder else "✗"
    print(f"\n{status} {scenario}")
    print(f"  Expected reminder: {expected_reminder}")
    print(f"  Got reminder: {has_reminder}")

    if result.get("additionalContext"):
        print(f"  Context preview: {result['additionalContext'][:100]}...")
    else:
        print("  No context injected")

    return has_reminder == expected_reminder


def main():
    """Run integration test scenarios."""
    print("=" * 70)
    print("WORKFLOW CLASSIFICATION REMINDER - INTEGRATION TEST")
    print("=" * 70)

    results = []

    # Scenario 1: First turn (new topic)
    print("\n[Scenario 1] First turn of session")
    result = simulate_hook_call("Implement user authentication", turn_count=0)
    results.append(
        print_result("First turn should trigger reminder", result, expected_reminder=True)
    )

    # Scenario 2: Follow-up (same topic)
    print("\n[Scenario 2] Follow-up on same topic")
    result = simulate_hook_call("Also add password reset", turn_count=2)
    results.append(
        print_result("Follow-up should NOT trigger reminder", result, expected_reminder=False)
    )

    # Scenario 3: Explicit transition (new topic)
    print("\n[Scenario 3] Explicit topic transition")
    result = simulate_hook_call("Now let's work on caching", turn_count=5)
    results.append(
        print_result("Explicit transition should trigger reminder", result, expected_reminder=True)
    )

    # Scenario 4: Clarification (same topic)
    print("\n[Scenario 4] Clarification on current work")
    result = simulate_hook_call("What about error handling?", turn_count=6)
    results.append(
        print_result("Clarification should NOT trigger reminder", result, expected_reminder=False)
    )

    # Scenario 5: Different topic after time
    print("\n[Scenario 5] New topic after several turns")
    result = simulate_hook_call("Can you help with testing?", turn_count=15)
    results.append(
        print_result("New topic after gap should trigger reminder", result, expected_reminder=True)
    )

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n✓ All integration tests PASSED")
        print("\nThe hook correctly:")
        print("  - Detects new topics (first turn, explicit transitions)")
        print("  - Ignores follow-ups and clarifications")
        print("  - Injects system reminders at the right times")
        return 0
    print(f"\n✗ {total - passed} integration test(s) FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
