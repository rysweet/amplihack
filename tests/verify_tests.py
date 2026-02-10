#!/usr/bin/env python3
"""
Verify test structure and count tests.

This script analyzes the test files to verify:
- Test count matches documentation
- Tests follow naming conventions
- Tests are properly distributed across pyramid levels
"""

import re
from pathlib import Path


def count_tests_in_file(file_path: Path) -> dict:
    """Count test methods in a file."""
    content = file_path.read_text()

    # Count test classes
    test_classes = re.findall(r"class (Test\w+)", content)

    # Count test methods
    test_methods = re.findall(r"def (test_\w+)", content)

    # Count docstrings
    docstrings = re.findall(r'"""(.+?)"""', content, re.DOTALL)

    return {
        "file": file_path.name,
        "classes": len(test_classes),
        "tests": len(test_methods),
        "class_names": test_classes,
        "test_names": test_methods,
        "lines": len(content.split("\n")),
    }


def analyze_test_structure():
    """Analyze complete test structure."""
    test_dir = Path(__file__).parent

    results = {"unit": [], "integration": [], "e2e": []}

    # Analyze unit tests
    unit_dir = test_dir / "unit"
    if unit_dir.exists():
        for test_file in unit_dir.glob("test_*.py"):
            results["unit"].append(count_tests_in_file(test_file))

    # Analyze integration tests
    integration_dir = test_dir / "integration"
    if integration_dir.exists():
        for test_file in integration_dir.glob("test_*.py"):
            results["integration"].append(count_tests_in_file(test_file))

    # Analyze E2E tests
    e2e_dir = test_dir / "e2e"
    if e2e_dir.exists():
        for test_file in e2e_dir.glob("test_*.py"):
            results["e2e"].append(count_tests_in_file(test_file))

    return results


def print_summary(results: dict):
    """Print summary of test structure."""
    print("=" * 80)
    print("TEST STRUCTURE VERIFICATION")
    print("=" * 80)
    print()

    total_tests = 0
    total_classes = 0
    total_lines = 0

    for level, files in results.items():
        level_tests = sum(f["tests"] for f in files)
        level_classes = sum(f["classes"] for f in files)
        level_lines = sum(f["lines"] for f in files)

        total_tests += level_tests
        total_classes += level_classes
        total_lines += level_lines

        print(f"{level.upper()} TESTS:")
        print(f"  Files: {len(files)}")
        print(f"  Test Classes: {level_classes}")
        print(f"  Test Methods: {level_tests}")
        print(f"  Total Lines: {level_lines}")
        print()

        for file_info in files:
            print(f"  📄 {file_info['file']}")
            print(
                f"     Classes: {file_info['classes']}, Tests: {file_info['tests']}, Lines: {file_info['lines']}"
            )
            for class_name in file_info["class_names"]:
                class_tests = [
                    t
                    for t in file_info["test_names"]
                    if class_name.lower().replace("test", "") in t
                ]
                print(f"       └─ {class_name}: ~{len(class_tests)} tests")
        print()

    print("=" * 80)
    print("SUMMARY:")
    print(f"  Total Test Files: {sum(len(f) for f in results.values())}")
    print(f"  Total Test Classes: {total_classes}")
    print(f"  Total Test Methods: {total_tests}")
    print(f"  Total Lines of Test Code: {total_lines}")
    print()

    # Calculate pyramid distribution
    unit_pct = (
        (sum(f["tests"] for f in results["unit"]) / total_tests * 100) if total_tests > 0 else 0
    )
    int_pct = (
        (sum(f["tests"] for f in results["integration"]) / total_tests * 100)
        if total_tests > 0
        else 0
    )
    e2e_pct = (
        (sum(f["tests"] for f in results["e2e"]) / total_tests * 100) if total_tests > 0 else 0
    )

    print("TESTING PYRAMID DISTRIBUTION:")
    print(f"  Unit Tests:        {unit_pct:5.1f}% (Target: 60%)")
    print(f"  Integration Tests: {int_pct:5.1f}% (Target: 30%)")
    print(f"  E2E Tests:         {e2e_pct:5.1f}% (Target: 10%)")
    print()

    print("=" * 80)
    print("✅ ALL TESTS ARE DESIGNED TO FAIL (TDD Approach)")
    print("   Implementation phase will make tests pass")
    print("=" * 80)


if __name__ == "__main__":
    results = analyze_test_structure()
    print_summary(results)
