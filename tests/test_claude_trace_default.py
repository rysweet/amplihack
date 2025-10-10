"""Test claude-trace default behavior - simplified for hard dependency approach."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.utils.claude_trace import get_claude_command, should_use_trace


def test_should_use_trace_default():
    """Test that claude-trace is preferred by default."""
    with patch.dict(os.environ, {}, clear=True):
        assert should_use_trace() is True, "Should default to using claude-trace"


def test_should_use_trace_explicit_disable():
    """Test that claude-trace can be explicitly disabled."""
    test_cases = ["0", "false", "no", "False", "NO", "FALSE"]

    for value in test_cases:
        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": value}):
            assert should_use_trace() is False, (
                f"Should be disabled with AMPLIHACK_USE_TRACE={value}"
            )


def test_should_use_trace_explicit_enable():
    """Test that explicit enable still works (backward compatibility)."""
    test_cases = ["1", "true", "yes", "True", "YES", "TRUE"]

    for value in test_cases:
        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": value}):
            assert should_use_trace() is True, f"Should be enabled with AMPLIHACK_USE_TRACE={value}"


def test_get_claude_command_when_disabled():
    """Test that regular claude is used when explicitly disabled."""
    with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": "0"}):
        cmd = get_claude_command()
        assert cmd == "claude"


def test_get_claude_command_when_enabled():
    """Test that claude-trace is used by default."""
    with patch.dict(os.environ, {}, clear=True):
        cmd = get_claude_command()
        assert cmd == "claude-trace"


def test_get_claude_command_explicit_enable():
    """Test that claude-trace is used when explicitly enabled."""
    with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": "1"}):
        cmd = get_claude_command()
        assert cmd == "claude-trace"


if __name__ == "__main__":
    # Run all tests
    test_functions = [
        test_should_use_trace_default,
        test_should_use_trace_explicit_disable,
        test_should_use_trace_explicit_enable,
        test_get_claude_command_when_disabled,
        test_get_claude_command_when_enabled,
        test_get_claude_command_explicit_enable,
    ]

    print("Running claude-trace simplified tests...")
    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Tests: {passed} passed, {failed} failed")
    if failed == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
        sys.exit(1)
