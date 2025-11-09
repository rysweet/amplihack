#!/usr/bin/env python3
"""
Simple test script to verify lock and reflection independence.
No external dependencies required.
"""

import json
import os
import sys
import tempfile
from pathlib import Path


def setup_test_environment():
    """Create a temporary project root directory."""
    tmpdir = tempfile.mkdtemp()
    project_root = Path(tmpdir)

    # Create necessary directories
    (project_root / ".claude" / "runtime" / "locks").mkdir(parents=True)
    (project_root / ".claude" / "runtime" / "logs").mkdir(parents=True)
    (project_root / ".claude" / "runtime" / "reflection").mkdir(parents=True)
    (project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True)

    # Create reflection config (enabled by default)
    config = {"enabled": True}
    config_path = project_root / ".claude" / "tools" / "amplihack" / ".reflection_config"
    config_path.write_text(json.dumps(config))

    return project_root


def create_stop_hook(project_root):
    """Create StopHook instance."""
    # Add hooks directory to path
    hooks_dir = Path(__file__).parent.parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
    if str(hooks_dir) not in sys.path:
        sys.path.insert(0, str(hooks_dir))

    from stop import StopHook

    hook = StopHook()
    hook.project_root = project_root
    hook.lock_flag = project_root / ".claude" / "runtime" / "locks" / ".lock_active"
    hook.continuation_prompt_file = project_root / ".claude" / "runtime" / "locks" / ".continuation_prompt"

    return hook


def test_lock_blocks_when_reflection_enabled():
    """Test 1: Lock blocks stop when reflection is enabled."""
    print("\n[TEST 1] Lock blocks when reflection enabled...")

    project_root = setup_test_environment()
    hook = create_stop_hook(project_root)

    # Set up: Lock active, reflection enabled (default)
    hook.lock_flag.touch()

    # Execute
    result = hook.process({})

    # Verify
    assert result["decision"] == "block", "Lock should block stop"
    print("✓ PASS: Lock correctly blocks when reflection enabled")
    return True


def test_lock_blocks_when_reflection_disabled():
    """Test 2: Lock blocks stop when reflection is disabled (THE CRITICAL TEST)."""
    print("\n[TEST 2] Lock blocks when reflection disabled via AMPLIHACK_SKIP_REFLECTION...")

    project_root = setup_test_environment()
    hook = create_stop_hook(project_root)

    # Set up: Lock active, reflection disabled via env var
    hook.lock_flag.touch()
    os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    try:
        # Execute
        result = hook.process({})

        # Verify: This is the critical test - lock MUST work even when reflection disabled
        if result["decision"] != "block":
            print(f"✗ FAIL: Lock did NOT block when reflection disabled!")
            print(f"  Result: {result}")
            return False

        print("✓ PASS: Lock correctly blocks even when reflection disabled")
        return True
    finally:
        # Clean up
        if "AMPLIHACK_SKIP_REFLECTION" in os.environ:
            del os.environ["AMPLIHACK_SKIP_REFLECTION"]


def test_no_lock_allows_stop_when_reflection_disabled():
    """Test 3: Stop is allowed when lock inactive and reflection disabled."""
    print("\n[TEST 3] Stop allowed when no lock and reflection disabled...")

    project_root = setup_test_environment()
    hook = create_stop_hook(project_root)

    # Set up: No lock, reflection disabled
    os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    try:
        # Execute
        result = hook.process({})

        # Verify
        assert result["decision"] == "approve", "Should allow stop when no lock and reflection disabled"
        print("✓ PASS: Stop correctly allowed when no lock and reflection disabled")
        return True
    finally:
        # Clean up
        if "AMPLIHACK_SKIP_REFLECTION" in os.environ:
            del os.environ["AMPLIHACK_SKIP_REFLECTION"]


def test_lock_blocks_when_reflection_disabled_via_config():
    """Test 4: Lock blocks when reflection disabled via config."""
    print("\n[TEST 4] Lock blocks when reflection disabled via config...")

    project_root = setup_test_environment()
    hook = create_stop_hook(project_root)

    # Set up: Lock active, reflection disabled via config
    hook.lock_flag.touch()
    config_path = project_root / ".claude" / "tools" / "amplihack" / ".reflection_config"
    config_path.write_text(json.dumps({"enabled": False}))

    # Execute
    result = hook.process({})

    # Verify
    assert result["decision"] == "block", "Lock should block even when reflection disabled via config"
    print("✓ PASS: Lock correctly blocks when reflection disabled via config")
    return True


def test_custom_prompt_with_reflection_disabled():
    """Test 5: Custom continuation prompt works with reflection disabled."""
    print("\n[TEST 5] Custom continuation prompt with reflection disabled...")

    project_root = setup_test_environment()
    hook = create_stop_hook(project_root)

    # Set up: Lock active with custom prompt, reflection disabled
    hook.lock_flag.touch()
    custom_prompt = "Custom continuation instructions for testing"
    hook.continuation_prompt_file.write_text(custom_prompt)
    os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    try:
        # Execute
        result = hook.process({})

        # Verify
        assert result["decision"] == "block", "Lock should block"
        assert custom_prompt in result["reason"], "Custom prompt should be used"
        print("✓ PASS: Custom prompt works with reflection disabled")
        return True
    finally:
        # Clean up
        if "AMPLIHACK_SKIP_REFLECTION" in os.environ:
            del os.environ["AMPLIHACK_SKIP_REFLECTION"]


def main():
    """Run all tests."""
    print("=" * 70)
    print("TESTING: Lock and Reflection Independence")
    print("=" * 70)
    print("\nThis test suite verifies that lock mode and reflection are")
    print("independently controllable, and that disabling reflection does")
    print("NOT break lock mode.")
    print("=" * 70)

    tests = [
        test_lock_blocks_when_reflection_enabled,
        test_lock_blocks_when_reflection_disabled,  # THE CRITICAL TEST
        test_no_lock_allows_stop_when_reflection_disabled,
        test_lock_blocks_when_reflection_disabled_via_config,
        test_custom_prompt_with_reflection_disabled,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ FAIL: {test_func.__name__} raised exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed > 0:
        print("\n🚨 CRITICAL BUG CONFIRMED: Lock mode is broken when reflection disabled!")
        sys.exit(1)
    else:
        print("\n✅ ALL TESTS PASSED: Lock and reflection are properly independent")
        sys.exit(0)


if __name__ == "__main__":
    main()
