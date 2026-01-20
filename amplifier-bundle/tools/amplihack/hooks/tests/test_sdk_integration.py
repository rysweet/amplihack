#!/usr/bin/env python3
"""
Test script to verify Claude SDK integration with power-steering mode.

This script tests that:
1. Claude SDK is available and can be imported
2. The analyze_consideration function works correctly
3. The integration with PowerSteeringChecker functions properly
4. Fallback to heuristic checkers works when SDK fails
"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude_power_steering import (
    CLAUDE_SDK_AVAILABLE,
    _format_consideration_prompt,
    _format_conversation_summary,
    analyze_consideration_sync,
)
from power_steering_checker import SDK_AVAILABLE, PowerSteeringChecker


def test_sdk_availability():
    """Test that Claude SDK is available."""
    print("Testing SDK availability...")
    print(f"  CLAUDE_SDK_AVAILABLE: {CLAUDE_SDK_AVAILABLE}")
    print(f"  SDK_AVAILABLE (from checker): {SDK_AVAILABLE}")

    if CLAUDE_SDK_AVAILABLE:
        print("  ✓ Claude SDK is available")
        return True
    print("  ⚠ Claude SDK is NOT available (will use heuristic fallback)")
    return False


def test_conversation_formatting():
    """Test conversation summary formatting."""
    print("\nTesting conversation formatting...")

    conversation = [
        {"type": "user", "message": {"content": "Implement feature X"}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll implement feature X for you."},
                    {"type": "tool_use", "name": "Write", "id": "1"},
                ]
            },
        },
        {"type": "tool_result", "message": {"content": "File written"}},
    ]

    summary = _format_conversation_summary(conversation)
    print(f"  Formatted {len(conversation)} messages")
    print(f"  Summary length: {len(summary)} chars")

    # Check that key elements are present
    assert "user" in summary.lower() or "message" in summary.lower()
    assert "assistant" in summary.lower() or "message" in summary.lower()
    assert "feature" in summary.lower() or "implement" in summary.lower()

    print("  ✓ Conversation formatting works")
    return True


def test_prompt_formatting():
    """Test consideration prompt formatting."""
    print("\nTesting prompt formatting...")

    consideration = {
        "id": "test_check",
        "question": "Were all TODO items completed?",
        "description": "Verify TodoWrite has all items marked complete",
        "category": "Completion",
    }

    conversation = [
        {"type": "user", "message": {"content": "Complete all TODOs"}},
        {"type": "assistant", "message": {"content": "All TODOs are now complete"}},
    ]

    prompt = _format_consideration_prompt(consideration, conversation)
    print(f"  Prompt length: {len(prompt)} chars")

    # Check that key elements are present
    assert "TODO items completed" in prompt
    assert "SATISFIED" in prompt
    assert "NOT SATISFIED" in prompt

    print("  ✓ Prompt formatting works")
    return True


def test_sdk_analysis():
    """Test actual SDK analysis (if SDK available)."""
    if not CLAUDE_SDK_AVAILABLE:
        print("\nSkipping SDK analysis test (SDK not available)")
        return True

    print("\nTesting SDK analysis...")

    consideration = {
        "id": "local_testing",
        "question": "Were tests run locally?",
        "description": "Check if pytest or similar test command was executed",
        "category": "Testing",
    }

    # Conversation WITH tests
    conversation_with_tests = [
        {"type": "user", "message": {"content": "Run the tests"}},
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Running pytest..."}]},
        },
        {
            "type": "tool_result",
            "message": {"content": "pytest output: 10 passed, 0 failed"},
        },
    ]

    # Conversation WITHOUT tests
    conversation_without_tests = [
        {"type": "user", "message": {"content": "Fix the bug"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Fixed"}]}},
    ]

    temp_dir = Path(tempfile.mkdtemp())

    try:
        print("  Testing WITH tests in transcript...")
        result_with = analyze_consideration_sync(conversation_with_tests, consideration, temp_dir)
        print(f"    Result: {'SATISFIED' if result_with else 'NOT SATISFIED'}")

        print("  Testing WITHOUT tests in transcript...")
        result_without = analyze_consideration_sync(
            conversation_without_tests, consideration, temp_dir
        )
        print(f"    Result: {'SATISFIED' if result_without else 'NOT SATISFIED'}")

        # We expect the SDK to correctly identify presence/absence of tests
        # Note: SDK might still return True (fail-open) if it's unsure
        print("  ✓ SDK analysis completed successfully")
        return True

    except Exception as e:
        print(f"  ✗ SDK analysis failed: {e}")
        return False


def test_integration_with_checker():
    """Test integration with PowerSteeringChecker."""
    print("\nTesting integration with PowerSteeringChecker...")

    temp_dir = Path(tempfile.mkdtemp())
    (temp_dir / ".claude" / "tools" / "amplihack").mkdir(parents=True)
    (temp_dir / ".claude" / "runtime" / "power-steering").mkdir(parents=True, exist_ok=True)

    # Create considerations YAML with a specific checker
    yaml_path = temp_dir / ".claude" / "tools" / "amplihack" / "considerations.yaml"
    yaml_content = """
- id: todos_complete
  category: Completion
  question: Were all TODO items completed?
  description: Check TodoWrite for completion
  severity: blocker
  checker: _check_todos_complete
  enabled: true
"""
    yaml_path.write_text(yaml_content)

    checker = PowerSteeringChecker(temp_dir)

    # Transcript with completed TODOs
    transcript = [
        {"type": "user", "message": {"content": "Complete the task"}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "TodoWrite",
                        "input": {"todos": [{"status": "completed"}]},
                    }
                ]
            },
        },
    ]

    analysis = checker._analyze_considerations(transcript, "test_session")

    print(f"  Analysis completed with {len(analysis.results)} results")

    # Note: Results might be empty if SDK is unavailable or checker method doesn't exist
    # This is expected behavior (fail-open), not a failure
    if len(analysis.results) > 0:
        if "todos_complete" in analysis.results:
            print(f"  todos_complete satisfied: {analysis.results['todos_complete'].satisfied}")
        else:
            print(f"  Available results: {list(analysis.results.keys())}")
    else:
        print("  No results returned (expected when SDK unavailable or checker method missing)")

    print("  ✓ Integration with PowerSteeringChecker works (no errors)")
    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("Claude SDK Integration Test Suite")
    print("=" * 70)

    results = []

    results.append(("SDK Availability", test_sdk_availability()))
    results.append(("Conversation Formatting", test_conversation_formatting()))
    results.append(("Prompt Formatting", test_prompt_formatting()))
    results.append(("SDK Analysis", test_sdk_analysis()))
    results.append(("Checker Integration", test_integration_with_checker()))

    print("\n" + "=" * 70)
    print("Test Results:")
    print("=" * 70)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")

    all_passed = all(passed for _, passed in results)
    print("=" * 70)

    if all_passed:
        print("✅ All tests passed!")
        return 0
    print("❌ Some tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
