#!/usr/bin/env python3
"""Verify test harness setup is correct.

This script checks that all test harness components are properly installed
and importable before runnin' the actual tests.
"""

import sys
from pathlib import Path


def verify_imports():
    """Verify all harness imports work."""
    print("Verifying imports...")

    try:
        from tests.harness import (
            PluginTestHarness,
            HookTestHarness,
            LSPTestHarness,
            SubprocessResult,
        )
        print("✓ All harness classes importable")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def verify_test_files():
    """Verify all test files exist."""
    print("\nVerifying test files...")

    test_files = [
        "tests/harness/__init__.py",
        "tests/harness/subprocess_test_harness.py",
        "tests/harness/README.md",
        "tests/e2e/test_plugin_manager_e2e.py",
        "tests/e2e/test_hook_protocol_e2e.py",
        "tests/e2e/test_lsp_detection_e2e.py",
        "tests/e2e/README.md",
        "tests/conftest.py",
        "tests/PLUGIN_TEST_HARNESS_SUMMARY.md",
    ]

    all_exist = True
    for test_file in test_files:
        file_path = Path(test_file)
        if file_path.exists():
            print(f"✓ {test_file}")
        else:
            print(f"✗ {test_file} - NOT FOUND")
            all_exist = False

    return all_exist


def verify_syntax():
    """Verify Python syntax is correct."""
    print("\nVerifying Python syntax...")

    python_files = [
        "tests/harness/subprocess_test_harness.py",
        "tests/e2e/test_plugin_manager_e2e.py",
        "tests/e2e/test_hook_protocol_e2e.py",
        "tests/e2e/test_lsp_detection_e2e.py",
    ]

    import py_compile

    all_valid = True
    for python_file in python_files:
        try:
            py_compile.compile(python_file, doraise=True)
            print(f"✓ {python_file}")
        except py_compile.PyCompileError as e:
            print(f"✗ {python_file} - SYNTAX ERROR: {e}")
            all_valid = False

    return all_valid


def verify_fixtures():
    """Verify conftest.py has required fixtures."""
    print("\nVerifying fixtures...")

    try:
        import tests.conftest as conftest

        required_fixtures = [
            "sample_plugin",
            "invalid_plugin",
            "multi_language_project",
        ]

        all_present = True
        for fixture_name in required_fixtures:
            if hasattr(conftest, fixture_name):
                print(f"✓ {fixture_name}")
            else:
                print(f"✗ {fixture_name} - NOT FOUND")
                all_present = False

        return all_present
    except Exception as e:
        print(f"✗ Could not verify fixtures: {e}")
        return False


def count_tests():
    """Count total E2E tests."""
    print("\nCounting tests...")

    try:
        import subprocess

        result = subprocess.run(
            ["python3", "-m", "pytest", "tests/e2e/", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            # Look fer line like "39 tests collected"
            for line in result.stdout.split("\n"):
                if "test" in line and "collected" in line:
                    print(f"✓ {line.strip()}")
                    return True

            print("✗ Could not parse test count")
            return False
        else:
            print(f"✗ pytest collection failed: {result.stderr}")
            return False

    except FileNotFoundError:
        print("⚠ pytest not installed (expected if not in development mode)")
        print("  Run: pip install pytest")
        return True  # Not a critical failure
    except Exception as e:
        print(f"✗ Error counting tests: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Test Harness Setup Verification")
    print("=" * 60)

    results = {
        "Imports": verify_imports(),
        "Test Files": verify_test_files(),
        "Syntax": verify_syntax(),
        "Fixtures": verify_fixtures(),
        "Test Count": count_tests(),
    }

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for check, passed in results.items():
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {check}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✅ All checks passed! Test harness is ready.")
        print("\nNext steps:")
        print("  1. Install pytest: pip install pytest")
        print("  2. Run E2E tests: pytest tests/e2e/ -v")
        print("  3. Implement plugin bricks to make tests pass")
        return 0
    else:
        print("\n❌ Some checks failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
