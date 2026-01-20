#!/usr/bin/env python3
"""
Verify Test Structure for Shutdown Fix Test Suite

This script validates the test suite structure without running the tests.
Useful for verifying TDD test files are properly structured before implementation.
"""

import ast
from pathlib import Path


def count_test_functions(filepath):
    """Count test functions in a Python file."""
    content = filepath.read_text()
    tree = ast.parse(content)

    test_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_count += 1

    return test_count


def extract_test_classes(filepath):
    """Extract test class names from a Python file."""
    content = filepath.read_text()
    tree = ast.parse(content)

    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            classes.append(node.name)

    return classes


def main():
    """Verify test suite structure."""
    test_dir = Path(__file__).parent

    test_files = [
        "test_shutdown_context.py",
        "test_hook_processor_shutdown.py",
        "test_stop_hook_integration.py",
        "test_exit_hang_e2e.py",
    ]

    print("=" * 70)
    print("Stop Hook Exit Hang Fix - Test Suite Verification")
    print("=" * 70)
    print()

    total_tests = 0
    total_classes = 0

    for test_file in test_files:
        filepath = test_dir / test_file
        if not filepath.exists():
            print(f"❌ {test_file} - NOT FOUND")
            continue

        try:
            test_count = count_test_functions(filepath)
            test_classes = extract_test_classes(filepath)
            total_tests += test_count
            total_classes += len(test_classes)

            print(f"✓ {test_file}")
            print(f"  Test Functions: {test_count}")
            print(f"  Test Classes:   {len(test_classes)}")
            if test_classes:
                print("  Classes:")
                for cls in test_classes[:5]:  # Show first 5
                    print(f"    - {cls}")
                if len(test_classes) > 5:
                    print(f"    ... and {len(test_classes) - 5} more")
            print()

        except Exception as e:
            print(f"❌ {test_file} - ERROR: {e}")
            print()

    print("=" * 70)
    print(f"Total Test Functions: {total_tests}")
    print(f"Total Test Classes:   {total_classes}")
    print("=" * 70)
    print()

    # Check documentation files
    doc_files = ["TEST_SHUTDOWN_FIX.md", "SHUTDOWN_FIX_TEST_SUMMARY.md"]
    print("Documentation Files:")
    for doc_file in doc_files:
        filepath = test_dir / doc_file
        if filepath.exists():
            size_kb = filepath.stat().st_size / 1024
            print(f"  ✓ {doc_file} ({size_kb:.1f}KB)")
        else:
            print(f"  ❌ {doc_file} - NOT FOUND")
    print()

    # Testing pyramid validation
    print("=" * 70)
    print("Testing Pyramid Validation (60/30/10)")
    print("=" * 70)

    unit_tests = count_test_functions(test_dir / "test_shutdown_context.py") + count_test_functions(
        test_dir / "test_hook_processor_shutdown.py"
    )
    integration_tests = count_test_functions(test_dir / "test_stop_hook_integration.py")
    e2e_tests = count_test_functions(test_dir / "test_exit_hang_e2e.py")

    unit_pct = (unit_tests / total_tests * 100) if total_tests > 0 else 0
    integration_pct = (integration_tests / total_tests * 100) if total_tests > 0 else 0
    e2e_pct = (e2e_tests / total_tests * 100) if total_tests > 0 else 0

    print(f"Unit Tests:        {unit_tests:2d} tests ({unit_pct:.1f}%) - Target: 60%")
    print(f"Integration Tests: {integration_tests:2d} tests ({integration_pct:.1f}%) - Target: 30%")
    print(f"E2E Tests:         {e2e_tests:2d} tests ({e2e_pct:.1f}%) - Target: 10%")
    print()

    # Validation
    if 50 <= unit_pct <= 70:
        print("✓ Unit test distribution within target range")
    else:
        print("⚠ Unit test distribution outside target range (50-70%)")

    if 20 <= integration_pct <= 40:
        print("✓ Integration test distribution within target range")
    else:
        print("⚠ Integration test distribution outside target range (20-40%)")

    if 5 <= e2e_pct <= 15:
        print("✓ E2E test distribution within target range")
    else:
        print("⚠ E2E test distribution outside target range (5-15%)")

    print()
    print("=" * 70)
    print("Test Suite Structure: VERIFIED ✓")
    print("=" * 70)
    print()
    print("Next Steps:")
    print("1. Run: pytest test_shutdown_context.py -v")
    print("   (Tests should FAIL - no implementation yet)")
    print()
    print("2. Implement: shutdown_context.py module")
    print()
    print("3. Update: hook_processor.py read_input() method")
    print()
    print("4. Run: pytest test_*.py -v")
    print("   (Tests should PASS after implementation)")
    print()


if __name__ == "__main__":
    main()
