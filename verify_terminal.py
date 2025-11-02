#!/usr/bin/env python3
"""Verification script for terminal enhancements.

Tests core functionality without pytest to verify cross-platform
compatibility and performance.
"""

import os
import sys
import time
from unittest.mock import patch

# Add src to path
sys.path.insert(0, "src")

from amplihack.terminal import (
    create_progress_bar,
    format_error,
    format_info,
    format_success,
    format_warning,
    is_bell_enabled,
    is_rich_enabled,
    is_title_enabled,
    progress_spinner,
    ring_bell,
    update_title,
)


def test_configuration():
    """Test configuration functions."""
    print("Testing configuration...")

    # Test defaults
    with patch.dict(os.environ, {}, clear=True):
        assert is_title_enabled() is True
        assert is_bell_enabled() is True
        assert is_rich_enabled() is True

    # Test disabled
    with patch.dict(
        os.environ,
        {
            "AMPLIHACK_TERMINAL_TITLE": "false",
            "AMPLIHACK_TERMINAL_BELL": "false",
            "AMPLIHACK_TERMINAL_RICH": "false",
        },
    ):
        assert is_title_enabled() is False
        assert is_bell_enabled() is False
        assert is_rich_enabled() is False

    print("✓ Configuration tests passed")


def test_title_update():
    """Test title update functionality."""
    print("Testing title updates...")

    with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_TITLE": "true"}):
        # Should not raise
        update_title("Test Title")
        update_title("Amplihack - Session 20251102")

    print("✓ Title update tests passed")


def test_bell():
    """Test bell notification."""
    print("Testing bell notifications...")

    with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_BELL": "true"}):
        # Should not raise
        ring_bell()

    print("✓ Bell notification tests passed")


def test_rich_formatting():
    """Test Rich formatting utilities."""
    print("Testing Rich formatting...")

    with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
        # Should not raise
        format_success("Success message")
        format_error("Error message")
        format_warning("Warning message")
        format_info("Info message")

    print("✓ Rich formatting tests passed")


def test_progress_spinner():
    """Test progress spinner."""
    print("Testing progress spinner...")

    with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
        with progress_spinner("Testing..."):
            time.sleep(0.01)

    print("✓ Progress spinner tests passed")


def test_progress_bar():
    """Test progress bar."""
    print("Testing progress bar...")

    with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
        with create_progress_bar(10, "Testing") as progress:
            task_id = progress.add_task("Testing", total=10)
            for i in range(10):
                progress.update(task_id, advance=1)
                time.sleep(0.001)

    print("✓ Progress bar tests passed")


def test_performance():
    """Test performance requirements (< 10ms per operation)."""
    print("Testing performance...")

    with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_TITLE": "true"}):
        start = time.time()
        for i in range(10):
            update_title(f"Test {i}")
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < 100, f"Title updates too slow: {elapsed_ms:.2f}ms"

    with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_BELL": "true"}):
        start = time.time()
        for i in range(10):
            ring_bell()
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < 100, f"Bell notifications too slow: {elapsed_ms:.2f}ms"

    print("✓ Performance tests passed (< 10ms per operation)")


def test_e2e_workflow():
    """Test complete E2E workflow."""
    print("Testing E2E workflow...")

    with patch.dict(
        os.environ,
        {
            "AMPLIHACK_TERMINAL_TITLE": "true",
            "AMPLIHACK_TERMINAL_BELL": "true",
            "AMPLIHACK_TERMINAL_RICH": "true",
        },
    ):
        # Session start
        update_title("Amplihack - Session 20251102_143022")
        format_info("Session started")

        # Work phase
        with progress_spinner("Analyzing files..."):
            time.sleep(0.01)
        format_success("Analysis complete")

        # Completion
        ring_bell()

    print("✓ E2E workflow tests passed")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Terminal Enhancement Verification")
    print("=" * 60)
    print()

    tests = [
        test_configuration,
        test_title_update,
        test_bell,
        test_rich_formatting,
        test_progress_spinner,
        test_progress_bar,
        test_performance,
        test_e2e_workflow,
    ]

    failed = []
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed.append((test.__name__, e))
        print()

    print("=" * 60)
    if failed:
        print(f"FAILED: {len(failed)}/{len(tests)} tests failed")
        for name, error in failed:
            print(f"  - {name}: {error}")
        sys.exit(1)
    else:
        print(f"SUCCESS: All {len(tests)} tests passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
