#!/usr/bin/env python3
"""Comprehensive test of the amplihack installation system."""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_fresh_install():
    """Test fresh installation (no existing ~/.claude directory)."""
    print("\n=== Testing Fresh Installation ===")

    # Backup existing .claude if it exists
    claude_dir = Path.home() / ".claude"
    backup_dir = None
    if claude_dir.exists():
        backup_dir = claude_dir.parent / f".claude.backup.{os.getpid()}"
        shutil.move(str(claude_dir), str(backup_dir))
        print(f"Backed up existing .claude to {backup_dir}")

    try:
        from amplihack import _local_install

        repo_root = Path(__file__).parent
        _local_install(str(repo_root))

        # Verify all components
        checks = {
            "agents/amplihack": claude_dir / "agents" / "amplihack",
            "commands/amplihack": claude_dir / "commands" / "amplihack",
            "tools/amplihack": claude_dir / "tools" / "amplihack",
            "context": claude_dir / "context",
            "workflow": claude_dir / "workflow",
            "runtime": claude_dir / "runtime",
            "runtime/logs": claude_dir / "runtime" / "logs",
            "runtime/metrics": claude_dir / "runtime" / "metrics",
            "settings.json": claude_dir / "settings.json",
        }

        all_good = True
        for name, path in checks.items():
            if path.exists():
                print(f"  ✅ {name} exists")
            else:
                print(f"  ❌ {name} missing")
                all_good = False

        return all_good

    finally:
        # Restore backup if it exists
        if backup_dir:
            if claude_dir.exists():
                shutil.rmtree(claude_dir)
            shutil.move(str(backup_dir), str(claude_dir))
            print("Restored original .claude from backup")


def test_upgrade_install():
    """Test upgrading an existing installation."""
    print("\n=== Testing Upgrade Installation ===")

    from amplihack import _local_install

    repo_root = Path(__file__).parent
    claude_dir = Path.home() / ".claude"

    # Check if settings.json was backed up
    backups = list(claude_dir.glob("settings.json.backup.*"))
    backup_count_before = len(backups)

    _local_install(str(repo_root))

    backups_after = list(claude_dir.glob("settings.json.backup.*"))
    backup_count_after = len(backups_after)

    if backup_count_after > backup_count_before:
        print("  ✅ Settings backed up before upgrade")
    else:
        print("  ⚠️  No new backup created (settings may not have changed)")

    # Verify hooks are using absolute paths
    settings_path = claude_dir / "settings.json"
    if settings_path.exists():
        with open(settings_path) as f:
            settings = json.load(f)

        abs_path_count = 0
        for hook_type in ["SessionStart", "Stop", "PostToolUse", "PreCompact"]:
            if hook_type in settings.get("hooks", {}):
                for config in settings["hooks"][hook_type]:
                    for hook in config.get("hooks", []):
                        if "command" in hook and hook["command"].startswith("/"):
                            abs_path_count += 1

        if abs_path_count >= 4:
            print(f"  ✅ All {abs_path_count} hooks using absolute paths")
            return True
        else:
            print(f"  ❌ Only {abs_path_count}/4 hooks using absolute paths")
            return False
    else:
        print("  ❌ settings.json not found after upgrade")
        return False


def test_uninstall_reinstall():
    """Test uninstall and reinstall cycle."""
    print("\n=== Testing Uninstall/Reinstall Cycle ===")

    from amplihack import _local_install, uninstall

    repo_root = Path(__file__).parent
    claude_dir = Path.home() / ".claude"

    # First install
    print("Installing...")
    _local_install(str(repo_root))

    # Verify amplihack directories exist
    amplihack_dirs = [
        claude_dir / "agents" / "amplihack",
        claude_dir / "commands" / "amplihack",
        claude_dir / "tools" / "amplihack",
    ]

    for dir_path in amplihack_dirs:
        if not dir_path.exists():
            print(f"  ❌ {dir_path} not created during install")
            return False

    # Uninstall
    print("Uninstalling...")
    uninstall()

    # Verify amplihack directories removed but parent dirs may remain
    for dir_path in amplihack_dirs:
        if dir_path.exists():
            print(f"  ❌ {dir_path} not removed during uninstall")
            return False

    print("  ✅ All amplihack directories removed")

    # Reinstall
    print("Reinstalling...")
    _local_install(str(repo_root))

    # Verify reinstall worked
    for dir_path in amplihack_dirs:
        if dir_path.exists():
            print(f"  ✅ {dir_path} recreated")
        else:
            print(f"  ❌ {dir_path} not recreated")
            return False

    return True


def test_external_directory_install():
    """Test installing from a different directory (simulating uvx/pip)."""
    print("\n=== Testing External Directory Installation ===")

    from amplihack import _local_install

    repo_root = Path(__file__).parent
    claude_dir = Path.home() / ".claude"

    # Change to temp directory
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        print(f"  Working from: {tmpdir}")
        print(f"  Installing from: {repo_root}")

        try:
            _local_install(str(repo_root))

            # Verify installation worked
            checks = [
                claude_dir / "agents" / "amplihack",
                claude_dir / "commands" / "amplihack",
                claude_dir / "tools" / "amplihack" / "hooks" / "session_start.py",
                claude_dir / "context" / "PHILOSOPHY.md",
                claude_dir / "workflow" / "DEFAULT_WORKFLOW.md",
            ]

            all_good = True
            for path in checks:
                if path.exists():
                    print(f"  ✅ {path.name} installed")
                else:
                    print(f"  ❌ {path.name} missing")
                    all_good = False

            return all_good

        finally:
            os.chdir(original_cwd)


def main():
    """Run all tests."""
    print("=" * 60)
    print("AMPLIHACK INSTALLATION TEST SUITE")
    print("=" * 60)

    tests = [
        ("Fresh Install", test_fresh_install),
        ("Upgrade Install", test_upgrade_install),
        ("Uninstall/Reinstall", test_uninstall_reinstall),
        ("External Directory", test_external_directory_install),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{name:.<40} {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
