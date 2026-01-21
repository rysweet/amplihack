"""Integration test for claude-trace fallback functionality (Issue #2042).

This test demonstrates the fix working end-to-end in realistic scenarios.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from amplihack.utils.claude_trace import (
    detect_claude_trace_status,
    get_claude_command,
)


def test_broken_native_binary_fallback():
    """Test fallback when claude-trace is a broken native ELF binary.

    This simulates the real issue from #2042 where claude-trace was a
    broken ELF binary that failed with 'Exec format error'.
    """
    # Create a temporary broken binary (simulated with a script that exits with error 8)
    with tempfile.TemporaryDirectory() as tmpdir:
        broken_binary = Path(tmpdir) / "claude-trace"
        broken_binary.write_text("#!/bin/bash\necho 'Exec format error' >&2\nexit 8\n")
        broken_binary.chmod(0o755)

        # Clear cache
        from amplihack.utils.claude_trace import clear_status_cache

        clear_status_cache()

        # Test detection
        status = detect_claude_trace_status(str(broken_binary))
        assert status == "broken", f"Expected 'broken' but got '{status}'"

        print("✓ Correctly detected broken native binary")


def test_missing_binary_fallback():
    """Test fallback when claude-trace doesn't exist."""
    non_existent = "/this/path/does/not/exist/claude-trace"

    # Clear cache
    from amplihack.utils.claude_trace import clear_status_cache

    clear_status_cache()

    status = detect_claude_trace_status(non_existent)
    assert status == "missing", f"Expected 'missing' but got '{status}'"

    print("✓ Correctly detected missing binary")


def test_working_binary_detection():
    """Test detection of working claude-trace binary (if available)."""
    # This test only runs if claude-trace is actually available
    claude_trace_path = shutil.which("claude-trace")

    if not claude_trace_path:
        print("⊘ Skipped (claude-trace not installed)")
        return

    # Clear cache
    from amplihack.utils.claude_trace import clear_status_cache

    clear_status_cache()

    status = detect_claude_trace_status(claude_trace_path)

    if status == "working":
        print(f"✓ Correctly detected working claude-trace at {claude_trace_path}")
    elif status == "broken":
        print(
            f"⚠ Warning: claude-trace at {claude_trace_path} detected as broken (this is OK if it's a native binary)"
        )
    else:
        print(f"✓ claude-trace status: {status}")


def run_integration_tests():
    """Run all integration tests."""
    print("Running claude-trace fallback integration tests...\n")

    tests = [
        ("Broken native binary fallback", test_broken_native_binary_fallback),
        ("Missing binary fallback", test_missing_binary_fallback),
        ("Working binary detection", test_working_binary_detection),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"Testing: {test_name}")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {test_name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {test_name}")
            print(f"  Unexpected error: {e}")
            failed += 1
        print()

    print("=" * 50)
    print(f"Integration tests: {passed} passed, {failed} failed")

    if failed == 0:
        print("✅ All integration tests passed!")
        return 0

    print("❌ Some integration tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(run_integration_tests())
