#!/usr/bin/env python3
"""
Outside-in end-to-end test for stop hook safety valve (fixes #2874).

Tests that the lock mode safety valve prevents infinite loops by
auto-approving after max iterations, simulating real stop hook
invocations from both Claude and Copilot launchers.

Usage:
    uv run pytest tests/outside_in/test_stop_hook_safety_valve_e2e.py -v
    # Or standalone:
    python3 tests/outside_in/test_stop_hook_safety_valve_e2e.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add the hooks directory to path
hooks_dir = Path(__file__).parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
sys.path.insert(0, str(hooks_dir))


def _create_lock_environment(tmp_path):
    """Set up a project root with lock mode active."""
    # Create lock file
    lock_dir = tmp_path / ".claude" / "runtime" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / ".lock_active"
    lock_file.touch()
    return lock_file


def _create_counter_file(tmp_path, session_id, count):
    """Pre-seed the lock counter to a specific value."""
    counter_dir = tmp_path / ".claude" / "runtime" / "locks" / session_id
    counter_dir.mkdir(parents=True, exist_ok=True)
    counter_file = counter_dir / "lock_invocations.txt"
    counter_file.write_text(str(count))
    return counter_file


class TestSafetyValveE2EClaude:
    """End-to-end tests simulating Claude sessions with lock mode."""

    def test_lock_blocks_normally_at_low_count(self):
        """Normal lock mode should block stop (simulating Claude session)."""
        from stop import StopHook

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            lock_file = _create_lock_environment(tmp_path)

            hook = StopHook()
            hook.project_root = tmp_path
            hook.lock_flag = lock_file
            hook.continuation_prompt_file = tmp_path / ".claude" / "runtime" / "locks" / ".continuation_prompt"

            with patch.object(hook, "_select_strategy", return_value=None):
                result = hook.process({})

            assert result["decision"] == "block", (
                "Lock mode should block stop at low iteration count"
            )
            assert "reason" in result

    def test_safety_valve_triggers_at_default_threshold(self):
        """Safety valve should approve at 50 iterations (default)."""
        from stop import StopHook

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            lock_file = _create_lock_environment(tmp_path)
            # Pre-seed counter to 49 (next increment will hit 50)
            _create_counter_file(tmp_path, "test-session", 49)

            hook = StopHook()
            hook.project_root = tmp_path
            hook.lock_flag = lock_file
            hook.continuation_prompt_file = tmp_path / ".claude" / "runtime" / "locks" / ".continuation_prompt"

            with patch.object(hook, "_select_strategy", return_value=None), \
                 patch.object(hook, "_get_current_session_id", return_value="test-session"):
                result = hook.process({})

            assert result["decision"] == "approve", (
                f"Safety valve should approve at threshold, got {result['decision']}"
            )
            assert not lock_file.exists(), "Lock file should be removed by safety valve"

    def test_safety_valve_with_custom_threshold(self):
        """Custom threshold via env var should be respected."""
        from stop import StopHook

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            lock_file = _create_lock_environment(tmp_path)
            _create_counter_file(tmp_path, "test-session", 4)

            hook = StopHook()
            hook.project_root = tmp_path
            hook.lock_flag = lock_file
            hook.continuation_prompt_file = tmp_path / ".claude" / "runtime" / "locks" / ".continuation_prompt"

            with patch.dict(os.environ, {"AMPLIHACK_MAX_LOCK_ITERATIONS": "5"}), \
                 patch.object(hook, "_select_strategy", return_value=None), \
                 patch.object(hook, "_get_current_session_id", return_value="test-session"):
                result = hook.process({})

            assert result["decision"] == "approve", (
                "Safety valve should trigger at custom threshold of 5"
            )

    def test_safety_valve_simulated_infinite_loop(self):
        """Simulate the actual infinite loop scenario from #2874."""
        from stop import StopHook

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            lock_file = _create_lock_environment(tmp_path)

            hook = StopHook()
            hook.project_root = tmp_path
            hook.lock_flag = lock_file
            hook.continuation_prompt_file = tmp_path / ".claude" / "runtime" / "locks" / ".continuation_prompt"

            # Simulate 5 rapid stop attempts (with low threshold for test speed)
            with patch.dict(os.environ, {"AMPLIHACK_MAX_LOCK_ITERATIONS": "3"}), \
                 patch.object(hook, "_select_strategy", return_value=None), \
                 patch.object(hook, "_get_current_session_id", return_value="loop-session"):

                results = []
                for i in range(5):
                    # Re-check lock file existence (safety valve removes it)
                    try:
                        hook.lock_flag.stat()
                    except FileNotFoundError:
                        # Lock removed by safety valve — subsequent stops approve
                        break
                    result = hook.process({})
                    results.append(result["decision"])

            # First 2 should block, 3rd should approve (safety valve)
            assert results[0] == "block", "First stop should be blocked"
            assert results[1] == "block", "Second stop should be blocked"
            assert results[2] == "approve", "Third stop should trigger safety valve"
            assert not lock_file.exists(), "Lock file should be removed"


class TestSafetyValveE2ECopilot:
    """End-to-end tests simulating Copilot sessions with lock mode."""

    def test_copilot_lock_mode_blocks_normally(self):
        """Copilot session with lock mode should block stop."""
        from stop import StopHook

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            lock_file = _create_lock_environment(tmp_path)

            hook = StopHook()
            hook.project_root = tmp_path
            hook.lock_flag = lock_file
            hook.continuation_prompt_file = tmp_path / ".claude" / "runtime" / "locks" / ".continuation_prompt"

            # Simulate Copilot environment
            with patch.object(hook, "_select_strategy", return_value=None), \
                 patch.dict(os.environ, {"GITHUB_COPILOT_CLI": "1"}, clear=False):
                result = hook.process({})

            assert result["decision"] == "block"

    def test_copilot_safety_valve_triggers(self):
        """Copilot session safety valve should also trigger at threshold."""
        from stop import StopHook

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            lock_file = _create_lock_environment(tmp_path)
            _create_counter_file(tmp_path, "copilot-session", 49)

            hook = StopHook()
            hook.project_root = tmp_path
            hook.lock_flag = lock_file
            hook.continuation_prompt_file = tmp_path / ".claude" / "runtime" / "locks" / ".continuation_prompt"

            with patch.object(hook, "_select_strategy", return_value=None), \
                 patch.object(hook, "_get_current_session_id", return_value="copilot-session"), \
                 patch.dict(os.environ, {"GITHUB_COPILOT_CLI": "1"}, clear=False):
                result = hook.process({})

            assert result["decision"] == "approve", (
                "Copilot safety valve should trigger at threshold"
            )
            assert not lock_file.exists()


class TestNoLockModeUnaffected:
    """Verify normal (no lock) sessions are not affected."""

    def test_no_lock_approves_normally(self):
        """Without lock mode, stop should approve after other checks."""
        from stop import StopHook

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Do NOT create lock file

            hook = StopHook()
            hook.project_root = tmp_path
            hook.lock_flag = tmp_path / ".claude" / "runtime" / "locks" / ".lock_active"
            hook.continuation_prompt_file = tmp_path / ".claude" / "runtime" / "locks" / ".continuation_prompt"

            with patch.object(hook, "_select_strategy", return_value=None), \
                 patch.object(hook, "_handle_neo4j_cleanup"), \
                 patch.object(hook, "_handle_neo4j_learning"), \
                 patch.object(hook, "_should_run_power_steering", return_value=False), \
                 patch.object(hook, "_should_run_reflection", return_value=False):
                result = hook.process({})

            assert result["decision"] == "approve"


if __name__ == "__main__":
    print("=" * 60)
    print("Outside-In Test: Stop Hook Safety Valve (#2874)")
    print("=" * 60)

    failures = 0
    tests = [
        ("Claude lock blocks normally", TestSafetyValveE2EClaude().test_lock_blocks_normally_at_low_count),
        ("Claude safety valve at default threshold", TestSafetyValveE2EClaude().test_safety_valve_triggers_at_default_threshold),
        ("Claude custom threshold", TestSafetyValveE2EClaude().test_safety_valve_with_custom_threshold),
        ("Claude simulated infinite loop", TestSafetyValveE2EClaude().test_safety_valve_simulated_infinite_loop),
        ("Copilot lock blocks normally", TestSafetyValveE2ECopilot().test_copilot_lock_mode_blocks_normally),
        ("Copilot safety valve triggers", TestSafetyValveE2ECopilot().test_copilot_safety_valve_triggers),
        ("No lock mode unaffected", TestNoLockModeUnaffected().test_no_lock_approves_normally),
    ]

    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  ✅ {name}")
        except AssertionError as e:
            print(f"  ❌ {name}: {e}")
            failures += 1
        except Exception as e:
            print(f"  ❌ {name}: {type(e).__name__}: {e}")
            failures += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {len(tests) - failures}/{len(tests)} passed")
    if failures:
        print(f"FAILED: {failures} test(s)")
        sys.exit(1)
    else:
        print("ALL PASSED")
