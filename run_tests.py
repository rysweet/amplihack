#!/usr/bin/env python3
"""Test runner script for REST API Client.

Runs tests with coverage reporting and different test suites.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        print(f"❌ {description} failed with exit code {result.returncode}")
        return False

    print(f"✅ {description} completed successfully")
    return True


def main():
    """Run all test suites with coverage."""

    # Change to project root
    project_root = Path(__file__).parent

    all_passed = True

    # 1. Run unit tests (60% coverage target)
    if not run_command(
        [
            "pytest",
            "-v",
            "-m",
            "unit",
            "tests/",
            "--cov=rest_api_client",
            "--cov-report=term-missing",
        ],
        "Unit Tests (60% coverage)",
    ):
        all_passed = False

    # 2. Run integration tests (30% coverage target)
    if not run_command(
        ["pytest", "-v", "-m", "integration", "tests/", "--cov=rest_api_client", "--cov-append"],
        "Integration Tests (30% coverage)",
    ):
        all_passed = False

    # 3. Run E2E tests (10% coverage target)
    if not run_command(
        ["pytest", "-v", "-m", "e2e", "tests/", "--cov=rest_api_client", "--cov-append"],
        "End-to-End Tests (10% coverage)",
    ):
        all_passed = False

    # 4. Run all tests with full coverage report
    print("\n" + "=" * 60)
    print("Running Full Test Suite with Coverage Report")
    print("=" * 60)

    full_test_cmd = [
        "pytest",
        "-v",
        "tests/",
        "--cov=rest_api_client",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=80",  # Minimum 80% coverage
    ]

    if not run_command(full_test_cmd, "Full Test Suite"):
        all_passed = False

    # 5. Type checking with mypy
    if not run_command(
        ["mypy", "rest_api_client/", "--ignore-missing-imports"], "Type Checking (mypy)"
    ):
        all_passed = False

    # 6. Linting with flake8
    if not run_command(["flake8", "rest_api_client/", "--max-line-length=100"], "Linting (flake8)"):
        # Linting failures are warnings, don't fail the entire suite
        print("⚠️  Linting issues found (non-blocking)")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    if all_passed:
        print("✅ All tests passed successfully!")
        print("📊 Coverage report available in htmlcov/index.html")
        return 0
    print("❌ Some tests failed. Please review the output above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
