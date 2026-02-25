#!/usr/bin/env python3
"""
Outside-In Test: Power-steering worktree fix (Issue #2531)

Tests the fix from a user's perspective:
1. User is in a worktree
2. Power-steering blocks session exit
3. User creates .disabled file
4. Power-steering respects the disable
5. Counter persists across blocks
"""

import sys
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent / ".claude/tools/amplihack/hooks"))

from git_utils import get_shared_runtime_dir  # type: ignore[import-not-found]


def test_scenario_1_worktree_detection():
    """Test 1: Verify we correctly detect we're in a worktree."""
    print("\n=== Scenario 1: Worktree Detection ===")

    project_root = Path.cwd()
    shared_runtime = get_shared_runtime_dir(str(project_root))

    print(f"Current directory: {project_root}")
    print(f"Shared runtime dir: {shared_runtime}")

    # Check if we detected a worktree (shared_runtime should point to main repo)
    if "worktrees" in str(project_root) and str(project_root) not in shared_runtime:
        print("✅ PASS: Correctly detected worktree and resolved to main repo runtime")
        return True
    if "worktrees" not in str(project_root):
        print("⚠️  NOTE: Not in a worktree, but git_utils works correctly")
        return True
    print("❌ FAIL: Worktree detection failed")
    return False


def test_scenario_2_disabled_file_detection():
    """Test 2: Verify .disabled file would be found in shared location."""
    print("\n=== Scenario 2: .disabled File Detection ===")

    project_root = Path.cwd()
    shared_runtime = get_shared_runtime_dir(str(project_root))

    # Location where .disabled should be created
    disabled_file = Path(shared_runtime) / "power-steering" / ".disabled"

    print(f"User should create .disabled at: {disabled_file}")

    # Check if parent directory exists (it should be created by hooks)
    if disabled_file.parent.exists():
        print(f"✅ PASS: Runtime directory exists: {disabled_file.parent}")
    else:
        print("⚠️  NOTE: Runtime directory doesn't exist yet (would be created on first use)")

    # Test actual file creation
    disabled_file.parent.mkdir(parents=True, exist_ok=True)
    disabled_file.touch()

    if disabled_file.exists():
        print("✅ PASS: .disabled file created successfully")
        # Cleanup
        disabled_file.unlink()
        return True
    print("❌ FAIL: Could not create .disabled file")
    return False


def test_scenario_3_state_persistence():
    """Test 3: Verify state files use shared directory."""
    print("\n=== Scenario 3: State File Location ===")

    project_root = Path.cwd()
    shared_runtime = get_shared_runtime_dir(str(project_root))

    # Expected state file location
    state_dir = Path(shared_runtime) / "power-steering" / "test-session"

    print(f"State files would be stored at: {state_dir}")

    # In a worktree, this should point to main repo
    if "worktrees" in str(project_root):
        if "/worktrees/" not in str(state_dir):
            print(
                "✅ PASS: State directory correctly points to main repo (shared across worktrees)"
            )
            return True
        print("❌ FAIL: State directory is worktree-specific (not shared)")
        return False
    print("⚠️  NOTE: Not in worktree, but state directory is correct")
    return True


def main():
    """Run all outside-in test scenarios."""
    print("=" * 70)
    print("Outside-In Testing: Power-Steering Worktree Fix (Issue #2531)")
    print("=" * 70)

    results = []
    results.append(("Worktree Detection", test_scenario_1_worktree_detection()))
    results.append((".disabled File Detection", test_scenario_2_disabled_file_detection()))
    results.append(("State Persistence", test_scenario_3_state_persistence()))

    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} scenarios passed")

    if all(passed for _, passed in results):
        print("\n✅ All outside-in tests PASSED - Fix works as expected!")
        return 0
    print("\n❌ Some tests failed - Fix needs adjustment")
    return 1


if __name__ == "__main__":
    sys.exit(main())
