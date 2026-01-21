#!/usr/bin/env python3
"""
Integration tests for workflow_invocation enforcement in power_steering_checker

Tests the full integration flow: validator → checker → considerations
"""

import sys
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


def create_mock_transcript(messages: list[tuple[str, str]]) -> list[dict]:
    """Create mock transcript from (role, text) tuples.

    Args:
        messages: List of (role, text) tuples

    Returns:
        Transcript list compatible with PowerSteeringChecker
    """
    transcript = []
    for role, text in messages:
        msg = {
            "type": role,
            "message": {"content": [{"type": "text", "text": text}]},
        }
        transcript.append(msg)
    return transcript


def test_workflow_invocation_with_skill_tool():
    """Test workflow invocation check passes with Skill tool."""
    print("Testing workflow invocation with Skill tool...")

    messages = [
        ("user", "/ultrathink implement authentication"),
        ("assistant", "Detecting task type: Development"),
        ("assistant", 'Skill(skill="default-workflow")'),
        ("assistant", "Workflow loaded, executing steps..."),
    ]

    transcript = create_mock_transcript(messages)
    checker = PowerSteeringChecker(Path("/tmp/test_session"))

    # Call the checker method directly
    result = checker._check_workflow_invocation(transcript, "test_session")

    assert result is True, "Should pass with proper Skill invocation"
    print("✓ Workflow invocation check passes with Skill tool")


def test_workflow_invocation_with_read_fallback():
    """Test workflow invocation check passes with Read tool fallback."""
    print("Testing workflow invocation with Read tool fallback...")

    messages = [
        ("user", "/ultrathink implement authentication"),
        ("assistant", "Skill invocation failed, using fallback"),
        ("assistant", "Read(.claude/workflow/DEFAULT_WORKFLOW.md)"),
        ("assistant", "Workflow loaded, executing steps..."),
    ]

    transcript = create_mock_transcript(messages)
    checker = PowerSteeringChecker(Path("/tmp/test_session"))

    result = checker._check_workflow_invocation(transcript, "test_session")

    assert result is True, "Should pass with Read tool fallback"
    print("✓ Workflow invocation check passes with Read tool fallback")


def test_workflow_invocation_violation():
    """Test workflow invocation check fails without proper invocation."""
    print("Testing workflow invocation violation detection...")

    messages = [
        ("user", "/ultrathink implement authentication"),
        ("assistant", "Starting implementation directly"),
        ("assistant", "Creating authentication module..."),
    ]

    transcript = create_mock_transcript(messages)
    checker = PowerSteeringChecker(Path("/tmp/test_session"))

    result = checker._check_workflow_invocation(transcript, "test_session")

    assert result is False, "Should fail without workflow invocation"
    print("✓ Workflow invocation violation detected correctly")


def test_workflow_invocation_not_required():
    """Test workflow invocation check skips when not required."""
    print("Testing workflow invocation skips when not required...")

    messages = [
        ("user", "How do I run tests?"),
        ("assistant", "Run pytest in the root directory"),
    ]

    transcript = create_mock_transcript(messages)
    checker = PowerSteeringChecker(Path("/tmp/test_session"))

    result = checker._check_workflow_invocation(transcript, "test_session")

    assert result is True, "Should pass when ultrathink not triggered"
    print("✓ Workflow invocation check skips correctly")


def test_investigation_workflow_skill():
    """Test investigation workflow skill detection."""
    print("Testing investigation workflow skill detection...")

    messages = [
        ("user", "/ultrathink investigate authentication system"),
        ("assistant", "Detecting task type: Investigation"),
        ("assistant", 'Skill(skill="investigation-workflow")'),
        ("assistant", "Phase 1: Scope Definition"),
    ]

    transcript = create_mock_transcript(messages)
    checker = PowerSteeringChecker(Path("/tmp/test_session"))

    result = checker._check_workflow_invocation(transcript, "test_session")

    assert result is True, "Should pass with investigation-workflow skill"
    print("✓ Investigation workflow skill detected correctly")


def test_transcript_conversion():
    """Test transcript to text conversion."""
    print("Testing transcript to text conversion...")

    messages = [
        ("user", "/ultrathink implement auth"),
        ("assistant", 'Skill(skill="default-workflow")'),
    ]

    transcript = create_mock_transcript(messages)
    checker = PowerSteeringChecker(Path("/tmp/test_session"))

    text = checker._transcript_to_text(transcript)

    assert "User:" in text, "Should have user role"
    assert "Claude:" in text, "Should have assistant role"
    assert "/ultrathink" in text, "Should preserve command"
    assert "Skill" in text, "Should preserve Skill tool"
    print("✓ Transcript conversion works correctly")


def run_integration_tests():
    """Run all integration tests."""
    print("\nRunning workflow_invocation integration tests...\n")

    tests = [
        test_workflow_invocation_with_skill_tool,
        test_workflow_invocation_with_read_fallback,
        test_workflow_invocation_violation,
        test_workflow_invocation_not_required,
        test_investigation_workflow_skill,
        test_transcript_conversion,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"Integration Tests: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
