#!/usr/bin/env python3
"""
Unit tests for workflow_invocation checker method

Tests _check_workflow_invocation method in isolation without full
PowerSteeringChecker initialization.
"""

import sys
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_checker_method_exists():
    """Test that _check_workflow_invocation method exists."""
    print("Testing _check_workflow_invocation method exists...")

    from power_steering_checker import PowerSteeringChecker

    # Check method exists
    assert hasattr(PowerSteeringChecker, "_check_workflow_invocation"), "Method should exist"
    print("✓ _check_workflow_invocation method exists")


def test_transcript_to_text_method():
    """Test _transcript_to_text helper method."""
    print("Testing _transcript_to_text helper method...")

    from power_steering_checker import PowerSteeringChecker

    # Create minimal checker instance for testing helper methods
    class MinimalChecker:
        def __init__(self):
            self.session_logs_dir = "/tmp/test"

        # Copy the helper methods
        _transcript_to_text = PowerSteeringChecker._transcript_to_text
        _extract_message_text = PowerSteeringChecker._extract_message_text

    checker = MinimalChecker()

    # Test transcript conversion
    transcript = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "Hello"}]}},
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Hi there"}]},
        },
    ]

    text = checker._transcript_to_text(transcript)

    assert "User: Hello" in text, "Should convert user message"
    assert "Claude: Hi there" in text, "Should convert assistant message"
    print("✓ _transcript_to_text works correctly")


def test_validator_import():
    """Test that workflow_invocation_validator can be imported."""
    print("Testing workflow_invocation_validator import...")

    try:
        from workflow_invocation_validator import validate_workflow_invocation

        assert callable(validate_workflow_invocation), "Should be callable"
        print("✓ workflow_invocation_validator imports successfully")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        raise


def test_considerations_yaml_has_workflow_invocation():
    """Test that considerations.yaml includes workflow_invocation."""
    print("Testing considerations.yaml has workflow_invocation...")

    import yaml

    considerations_file = Path(__file__).parent.parent.parent / "considerations.yaml"

    with open(considerations_file) as f:
        considerations = yaml.safe_load(f)

    # Find workflow_invocation consideration
    found = False
    for consideration in considerations:
        if consideration.get("id") == "workflow_invocation":
            found = True
            assert consideration.get("severity") == "blocker", "Should be blocker severity"
            assert consideration.get("checker") == "_check_workflow_invocation", (
                "Should use correct checker"
            )
            assert consideration.get("enabled") is True, "Should be enabled"
            break

    assert found, "workflow_invocation consideration should exist in YAML"
    print("✓ considerations.yaml has workflow_invocation")


def test_power_steering_checker_has_method():
    """Test that PowerSteeringChecker class has the new method."""
    print("Testing PowerSteeringChecker has _check_workflow_invocation...")

    import inspect

    from power_steering_checker import PowerSteeringChecker

    # Get method
    method = getattr(PowerSteeringChecker, "_check_workflow_invocation", None)
    assert method is not None, "Method should exist"

    # Check signature
    sig = inspect.signature(method)
    params = list(sig.parameters.keys())

    assert "self" in params, "Should be instance method"
    assert "transcript" in params, "Should accept transcript"
    assert "session_id" in params, "Should accept session_id"

    print("✓ PowerSteeringChecker has correctly defined _check_workflow_invocation")


def run_unit_tests():
    """Run all unit tests."""
    print("\nRunning workflow_invocation checker unit tests...\n")

    tests = [
        test_checker_method_exists,
        test_transcript_to_text_method,
        test_validator_import,
        test_considerations_yaml_has_workflow_invocation,
        test_power_steering_checker_has_method,
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

    print(f"\n{'=' * 60}")
    print(f"Unit Tests: {passed} passed, {failed} failed")
    print(f"{'=' * 60}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_unit_tests()
    sys.exit(0 if success else 1)
