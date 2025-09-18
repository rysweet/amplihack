#!/usr/bin/env python3
"""
Test CI Workflow Tool

Basic tests to verify the CI workflow tool functionality.
"""

import sys

from ci_workflow import analyze_diagnostics, diagnose_ci, poll_status


def test_diagnostics_analysis():
    """Test the diagnostic analysis function."""
    print("Testing diagnostic analysis...")

    # Test case 1: All passing
    diagnostics = {
        "ci_status": {"status": "PASSING", "success": True},
        "lint_check": {"success": True},
        "test_check": {"success": True},
        "build_check": {"success": True},
    }
    result = analyze_diagnostics(diagnostics)
    assert result == "ALL_PASSING", f"Expected ALL_PASSING, got {result}"
    print("  ✓ All passing case works")

    # Test case 2: CI failing
    diagnostics["ci_status"]["status"] = "FAILING"
    result = analyze_diagnostics(diagnostics)
    assert result == "CI_FAILING", f"Expected CI_FAILING, got {result}"
    print("  ✓ CI failing case works")

    # Test case 3: Tests failing
    diagnostics["ci_status"]["status"] = "PASSING"
    diagnostics["test_check"]["success"] = False
    result = analyze_diagnostics(diagnostics)
    assert result == "TESTS_FAILING", f"Expected TESTS_FAILING, got {result}"
    print("  ✓ Tests failing case works")

    # Test case 4: Lint failing
    diagnostics["test_check"]["success"] = True
    diagnostics["lint_check"]["success"] = False
    result = analyze_diagnostics(diagnostics)
    assert result == "LINT_FAILING", f"Expected LINT_FAILING, got {result}"
    print("  ✓ Lint failing case works")

    # Test case 5: Build failing
    diagnostics["lint_check"]["success"] = True
    diagnostics["build_check"]["success"] = False
    result = analyze_diagnostics(diagnostics)
    assert result == "BUILD_FAILING", f"Expected BUILD_FAILING, got {result}"
    print("  ✓ Build failing case works")

    # Test case 6: CI pending
    diagnostics["build_check"]["success"] = True
    diagnostics["ci_status"]["status"] = "PENDING"
    result = analyze_diagnostics(diagnostics)
    assert result == "CI_PENDING", f"Expected CI_PENDING, got {result}"
    print("  ✓ CI pending case works")

    print("✓ All diagnostic analysis tests passed!\n")


def test_poll_status_mock():
    """Test the poll status function with a mock scenario."""
    print("Testing poll status with mock (very quick test)...")

    # Test with very short timeout to avoid waiting
    result = poll_status(
        reference=None,  # Will use current branch
        timeout=2,  # Very short timeout
        interval=1,  # Quick interval
        exponential_backoff=False,
    )

    # Verify structure
    assert "polls" in result, "Result should have polls"
    assert "final_status" in result, "Result should have final_status"
    assert "success" in result, "Result should have success"
    assert "timed_out" in result, "Result should have timed_out"

    print(f"  ✓ Poll status returned with {len(result['polls'])} polls")
    print(f"  ✓ Final status: {result['final_status']}")
    print(f"  ✓ Timed out: {result['timed_out']}")
    print("✓ Poll status structure test passed!\n")


def test_diagnose_structure():
    """Test that diagnose_ci returns the expected structure."""
    print("Testing diagnose structure...")

    # Run diagnose without PR/branch (will use current)
    result = diagnose_ci()

    # Verify structure
    assert "ci_status" in result, "Result should have ci_status"
    assert "lint_check" in result, "Result should have lint_check"
    assert "test_check" in result, "Result should have test_check"
    assert "build_check" in result, "Result should have build_check"
    assert "overall_status" in result, "Result should have overall_status"
    assert "errors" in result, "Result should have errors"

    print("  ✓ Diagnostic structure is correct")
    print(f"  ✓ Overall status: {result['overall_status']}")

    # Print summary
    if result["ci_status"]:
        ci_status = result["ci_status"].get("status", "UNKNOWN")
        print(f"  ✓ CI Status: {ci_status}")

    print("✓ Diagnose structure test passed!\n")


def main():
    """Run all tests."""
    print("=" * 50)
    print("CI Workflow Tool Tests")
    print("=" * 50 + "\n")

    try:
        test_diagnostics_analysis()
        test_poll_status_mock()
        test_diagnose_structure()

        print("=" * 50)
        print("✓ All tests passed successfully!")
        print("=" * 50)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
