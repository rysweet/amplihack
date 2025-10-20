#!/usr/bin/env python3
"""
Verify beads CLI integration manually.

This script tests the basic functionality of the beads CLI commands
without requiring pytest.
"""

import sys
import subprocess


def run_command(cmd):
    """Run a command and return exit code and output."""
    print(f"\n{'=' * 80}")
    print(f"Running: {' '.join(cmd)}")
    print("=" * 80)

    result = subprocess.run(cmd, capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)

    return result.returncode


def main():
    """Run verification tests."""
    print("\nBeads CLI Integration Verification")
    print("=" * 80)

    tests_passed = 0
    tests_failed = 0

    # Test 1: beads help
    print("\n[TEST 1] beads help")
    code = run_command([sys.executable, "-m", "src.amplihack.cli", "beads", "--help"])
    if code == 0:
        print("✓ PASS: beads help works")
        tests_passed += 1
    else:
        print("✗ FAIL: beads help failed")
        tests_failed += 1

    # Test 2: beads status
    print("\n[TEST 2] beads status")
    code = run_command([sys.executable, "-m", "src.amplihack.cli", "beads", "status"])
    if code == 0:
        print("✓ PASS: beads status works")
        tests_passed += 1
    else:
        print("✗ FAIL: beads status failed")
        tests_failed += 1

    # Test 3: beads create help
    print("\n[TEST 3] beads create help")
    code = run_command([sys.executable, "-m", "src.amplihack.cli", "beads", "create", "--help"])
    if code == 0:
        print("✓ PASS: beads create help works")
        tests_passed += 1
    else:
        print("✗ FAIL: beads create help failed")
        tests_failed += 1

    # Test 4: beads ready help
    print("\n[TEST 4] beads ready help")
    code = run_command([sys.executable, "-m", "src.amplihack.cli", "beads", "ready", "--help"])
    if code == 0:
        print("✓ PASS: beads ready help works")
        tests_passed += 1
    else:
        print("✗ FAIL: beads ready help failed")
        tests_failed += 1

    # Test 5: beads list help
    print("\n[TEST 5] beads list help")
    code = run_command([sys.executable, "-m", "src.amplihack.cli", "beads", "list", "--help"])
    if code == 0:
        print("✓ PASS: beads list help works")
        tests_passed += 1
    else:
        print("✗ FAIL: beads list help failed")
        tests_failed += 1

    # Test 6: beads update help
    print("\n[TEST 6] beads update help")
    code = run_command([sys.executable, "-m", "src.amplihack.cli", "beads", "update", "--help"])
    if code == 0:
        print("✓ PASS: beads update help works")
        tests_passed += 1
    else:
        print("✗ FAIL: beads update help failed")
        tests_failed += 1

    # Test 7: beads close help
    print("\n[TEST 7] beads close help")
    code = run_command([sys.executable, "-m", "src.amplihack.cli", "beads", "close", "--help"])
    if code == 0:
        print("✓ PASS: beads close help works")
        tests_passed += 1
    else:
        print("✗ FAIL: beads close help failed")
        tests_failed += 1

    # Test 8: beads get help
    print("\n[TEST 8] beads get help")
    code = run_command([sys.executable, "-m", "src.amplihack.cli", "beads", "get", "--help"])
    if code == 0:
        print("✓ PASS: beads get help works")
        tests_passed += 1
    else:
        print("✗ FAIL: beads get help failed")
        tests_failed += 1

    # Test 9: beads with no subcommand (should error gracefully)
    print("\n[TEST 9] beads with no subcommand")
    code = run_command([sys.executable, "-m", "src.amplihack.cli", "beads"])
    if code == 1:  # Should fail but gracefully
        print("✓ PASS: beads without subcommand fails gracefully")
        tests_passed += 1
    else:
        print("✗ FAIL: beads without subcommand should return error code")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Tests passed: {tests_passed}")
    print(f"Tests failed: {tests_failed}")

    if tests_failed == 0:
        print("\n✓ All tests passed!")
        return 0
    print(f"\n✗ {tests_failed} test(s) failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
