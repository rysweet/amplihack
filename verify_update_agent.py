#!/usr/bin/env python3
"""
Verification script for update-agent implementation.

Verifies all components are in place and working.
"""

import sys
from pathlib import Path


def verify_files_exist():
    """Verify all required files exist."""
    required_files = [
        "src/amplihack/goal_agent_generator/models.py",
        "src/amplihack/goal_agent_generator/update_agent/__init__.py",
        "src/amplihack/goal_agent_generator/update_agent/version_detector.py",
        "src/amplihack/goal_agent_generator/update_agent/changeset_generator.py",
        "src/amplihack/goal_agent_generator/update_agent/backup_manager.py",
        "src/amplihack/goal_agent_generator/update_agent/selective_updater.py",
        "src/amplihack/goal_agent_generator/update_agent_cli.py",
        "src/amplihack/goal_agent_generator/tests/test_update_agent.py",
        "src/amplihack/cli.py",
    ]

    print("Checking required files...")
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} - MISSING")
            all_exist = False

    return all_exist


def verify_imports():
    """Verify all modules can be imported."""
    print("\nChecking imports...")
    try:
        from src.amplihack.goal_agent_generator.models import (
            AgentVersionInfo,
            FileChange,
            SkillUpdate,
            UpdateChangeset,
        )
        print("  ✓ Data models import successfully")

        from src.amplihack.goal_agent_generator.update_agent import (
            BackupManager,
            ChangesetGenerator,
            SelectiveUpdater,
            VersionDetector,
        )
        print("  ✓ Update agent modules import successfully")

        from src.amplihack.goal_agent_generator.update_agent_cli import update_agent
        print("  ✓ CLI command imports successfully")

        return True
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return False


def verify_tests():
    """Verify tests exist and are structured correctly."""
    print("\nChecking test structure...")
    test_file = Path("src/amplihack/goal_agent_generator/tests/test_update_agent.py")

    if not test_file.exists():
        print("  ✗ Test file missing")
        return False

    content = test_file.read_text()

    # Check for test classes
    test_classes = [
        "TestVersionDetector",
        "TestChangesetGenerator",
        "TestBackupManager",
        "TestSelectiveUpdater",
        "TestModels",
    ]

    all_found = True
    for test_class in test_classes:
        if f"class {test_class}" in content:
            print(f"  ✓ {test_class} found")
        else:
            print(f"  ✗ {test_class} missing")
            all_found = False

    return all_found


def verify_cli_integration():
    """Verify CLI integration."""
    print("\nChecking CLI integration...")
    cli_file = Path("src/amplihack/cli.py")

    if not cli_file.exists():
        print("  ✗ CLI file missing")
        return False

    content = cli_file.read_text()

    checks = [
        ('update-agent parser', 'update_parser = subparsers.add_parser'),
        ('update-agent command handler', 'elif args.command == "update-agent"'),
        ('update_agent import', 'from .goal_agent_generator.update_agent_cli import update_agent'),
    ]

    all_found = True
    for check_name, check_string in checks:
        if check_string in content:
            print(f"  ✓ {check_name} found")
        else:
            print(f"  ✗ {check_name} missing")
            all_found = False

    return all_found


def count_implementation_lines():
    """Count lines of implementation."""
    print("\nCounting implementation lines...")

    files = [
        "src/amplihack/goal_agent_generator/update_agent/version_detector.py",
        "src/amplihack/goal_agent_generator/update_agent/changeset_generator.py",
        "src/amplihack/goal_agent_generator/update_agent/backup_manager.py",
        "src/amplihack/goal_agent_generator/update_agent/selective_updater.py",
        "src/amplihack/goal_agent_generator/update_agent_cli.py",
    ]

    total_lines = 0
    for file_path in files:
        path = Path(file_path)
        if path.exists():
            lines = len(path.read_text().splitlines())
            total_lines += lines
            print(f"  {path.name}: {lines} lines")

    print(f"\nTotal implementation: {total_lines} lines")
    return total_lines


def main():
    """Run all verifications."""
    print("=" * 70)
    print("UPDATE-AGENT IMPLEMENTATION VERIFICATION")
    print("=" * 70)

    results = []

    # Run verifications
    results.append(("Files exist", verify_files_exist()))
    results.append(("Imports work", verify_imports()))
    results.append(("Tests structured", verify_tests()))
    results.append(("CLI integrated", verify_cli_integration()))

    # Count lines
    line_count = count_implementation_lines()

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    all_passed = True
    for check_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{check_name:20} {status}")
        if not passed:
            all_passed = False

    print(f"\nImplementation size: {line_count} lines")

    if all_passed:
        print("\n🎉 All verifications passed! Implementation is complete.")
        return 0
    else:
        print("\n❌ Some verifications failed. Review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
