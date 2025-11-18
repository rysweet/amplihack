#!/usr/bin/env python3
"""Simple verification script for containerized mode functionality."""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, "src")

from amplihack.launcher.core import ClaudeLauncher


def test_container_detection():
    """Test container detection logic."""
    print("Testing container detection...")

    # Test 1: IS_SANDBOX=1 detection
    print("\n1. Testing IS_SANDBOX=1 detection...")
    os.environ["IS_SANDBOX"] = "1"
    launcher = ClaudeLauncher()
    assert launcher.containerized is True, "Failed: IS_SANDBOX=1 not detected"
    print("   ✓ Detected container via IS_SANDBOX=1")
    del os.environ["IS_SANDBOX"]

    # Test 2: Root user detection (uid=0)
    print("\n2. Testing root user detection...")
    with patch("os.getuid", return_value=0):
        launcher = ClaudeLauncher()
        assert launcher.containerized is True, "Failed: root user not detected"
        print("   ✓ Detected container via uid=0")

    # Test 3: Normal environment (no container)
    print("\n3. Testing normal environment...")
    with patch("os.getuid", return_value=1000):
        launcher = ClaudeLauncher()
        assert launcher.containerized is False, "Failed: false positive detection"
        print("   ✓ No container detected in normal environment")

    # Test 4: Explicit containerized flag
    print("\n4. Testing explicit containerized flag...")
    with patch("os.getuid", return_value=1000):
        launcher = ClaudeLauncher(containerized=True)
        assert launcher.containerized is True, "Failed: explicit flag not respected"
        print("   ✓ Explicit containerized=True works")

    print("\n✅ All container detection tests passed!")


def test_command_building():
    """Test command building with and without containerized mode."""
    print("\nTesting command building...")

    # Test 5: Command without dangerous flag in container
    print("\n5. Testing command without --dangerously-skip-permissions in container...")
    with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
        launcher = ClaudeLauncher(containerized=True)
        cmd = launcher.build_claude_command()
        assert "--dangerously-skip-permissions" not in cmd, (
            "Failed: dangerous flag present in container mode"
        )
        print("   ✓ Command omits --dangerously-skip-permissions in container mode")

    # Test 6: Command with dangerous flag in non-container
    print("\n6. Testing command with --dangerously-skip-permissions in non-container...")
    with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
        launcher = ClaudeLauncher(containerized=False)
        cmd = launcher.build_claude_command()
        assert "--dangerously-skip-permissions" in cmd, (
            "Failed: dangerous flag missing in non-container mode"
        )
        print("   ✓ Command includes --dangerously-skip-permissions in non-container mode")

    # Test 7: claude-trace mode in container
    print("\n7. Testing claude-trace mode in container...")
    with patch("amplihack.launcher.core.get_claude_command", return_value="claude-trace"):
        with patch("amplihack.launcher.core.get_claude_cli_path", return_value="/usr/bin/claude"):
            launcher = ClaudeLauncher(containerized=True)
            cmd = launcher.build_claude_command()
            cmd_str = " ".join(cmd)
            assert "--dangerously-skip-permissions" not in cmd_str, (
                "Failed: dangerous flag in claude-trace container mode"
            )
            print("   ✓ claude-trace mode omits flag in container")

    # Test 8: claude-trace mode in non-container
    print("\n8. Testing claude-trace mode in non-container...")
    with patch("amplihack.launcher.core.get_claude_command", return_value="claude-trace"):
        with patch("amplihack.launcher.core.get_claude_cli_path", return_value="/usr/bin/claude"):
            launcher = ClaudeLauncher(containerized=False)
            cmd = launcher.build_claude_command()
            cmd_str = " ".join(cmd)
            assert "--dangerously-skip-permissions" in cmd_str, (
                "Failed: dangerous flag missing in claude-trace non-container mode"
            )
            print("   ✓ claude-trace mode includes flag in non-container")

    print("\n✅ All command building tests passed!")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Containerized Mode Verification")
    print("=" * 60)

    try:
        test_container_detection()
        test_command_building()

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
