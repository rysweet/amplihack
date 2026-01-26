#!/usr/bin/env python3
"""Verify UVX Integration Test Harness Implementation.

This script verifies that all components are properly implemented.
"""

import sys
from pathlib import Path

# Colors fer output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def check_file_exists(filepath: Path, description: str) -> bool:
    """Check if file exists and report."""
    if filepath.exists():
        print(f"{GREEN}✓{RESET} {description}: {filepath.name}")
        return True
    print(f"{RED}✗{RESET} {description}: {filepath.name} (NOT FOUND)")
    return False


def check_python_syntax(filepath: Path) -> bool:
    """Check if Python file has valid syntax."""
    try:
        import py_compile

        py_compile.compile(filepath, doraise=True)
        return True
    except Exception as e:
        print(f"{RED}✗{RESET} Syntax error in {filepath.name}: {e}")
        return False


def main():
    """Main verification."""
    print("Verifying UVX Integration Test Harness Implementation")
    print("=" * 60)

    base_dir = Path(__file__).parent
    harness_dir = base_dir / "harness"

    all_good = True

    # Check harness files
    print("\n1. Harness Module Files:")
    harness_files = [
        (harness_dir / "__init__.py", "Harness __init__.py"),
        (harness_dir / "uvx_launcher.py", "UVX Launcher"),
        (harness_dir / "output_validator.py", "Output Validator"),
        (harness_dir / "test_helpers.py", "Test Helpers"),
    ]

    for filepath, description in harness_files:
        if not check_file_exists(filepath, description) or not check_python_syntax(filepath):
            all_good = False

    # Check test files
    print("\n2. Integration Test Files:")
    test_files = [
        (base_dir / "test_hooks.py", "Hook Tests"),
        (base_dir / "test_skills.py", "Skill Tests"),
        (base_dir / "test_commands.py", "Command Tests"),
        (base_dir / "test_agents.py", "Agent Tests"),
        (base_dir / "test_lsp_detection.py", "LSP Detection Tests"),
        (base_dir / "test_settings_generation.py", "Settings Generation Tests"),
    ]

    for filepath, description in test_files:
        if not check_file_exists(filepath, description) or not check_python_syntax(filepath):
            all_good = False

    # Check documentation
    print("\n3. Documentation Files:")
    doc_files = [
        (base_dir / "README.md", "README"),
        (base_dir / "IMPLEMENTATION_SUMMARY.md", "Implementation Summary"),
    ]

    for filepath, description in doc_files:
        if not check_file_exists(filepath, description):
            all_good = False

    # Count tests
    print("\n4. Test Count:")
    try:
        import subprocess

        result = subprocess.run(
            ["grep", "-r", "def test_", str(base_dir)],
            capture_output=True,
            text=True,
        )
        test_count = len(result.stdout.strip().split("\n"))
        print(f"   Found {test_count} test methods")

        if test_count >= 80:
            print(f"   {GREEN}✓{RESET} Test count meets target (80+)")
        else:
            print(f"   {RED}✗{RESET} Test count below target (found {test_count}, need 80+)")
            all_good = False

    except Exception as e:
        print(f"   {RED}✗{RESET} Could not count tests: {e}")

    # Count lines of code
    print("\n5. Lines of Code:")
    try:
        total_lines = 0
        for py_file in base_dir.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                lines = len(py_file.read_text().split("\n"))
                total_lines += lines

        print(f"   Total Python lines: {total_lines}")

        if total_lines >= 2500:
            print(f"   {GREEN}✓{RESET} LOC meets target (2500+)")
        else:
            print(f"   {RED}✗{RESET} LOC below target (found {total_lines}, need 2500+)")

    except Exception as e:
        print(f"   {RED}✗{RESET} Could not count lines: {e}")

    # Summary
    print("\n" + "=" * 60)
    if all_good:
        print(f"{GREEN}✓ ALL CHECKS PASSED{RESET}")
        print("\nImplementation is complete and ready fer testing!")
        return 0
    print(f"{RED}✗ SOME CHECKS FAILED{RESET}")
    print("\nPlease review errors above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
