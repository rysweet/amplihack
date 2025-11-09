#!/usr/bin/env python3
"""
Test that lock and reflection are independently controllable in stop hook.

This test verifies the critical requirement that:
1. Lock mode works when reflection is enabled
2. Lock mode works when reflection is disabled
3. Reflection can be disabled without affecting lock mode
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_project_root():
    """Create a temporary project root directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
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

        yield project_root


@pytest.fixture
def stop_hook(temp_project_root):
    """Create StopHook instance with mocked project root."""
    # Add parent directory to path for import
    import sys
    hooks_dir = Path(__file__).parent.parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
    sys.path.insert(0, str(hooks_dir))

    from stop import StopHook

    with patch.object(StopHook, 'project_root', temp_project_root):
        hook = StopHook()
        hook.project_root = temp_project_root
        hook.lock_flag = temp_project_root / ".claude" / "runtime" / "locks" / ".lock_active"
        hook.continuation_prompt_file = temp_project_root / ".claude" / "runtime" / "locks" / ".continuation_prompt"
        yield hook


class TestLockAndReflectionIndependence:
    """Test that lock and reflection are independently controllable."""

    def test_lock_blocks_when_reflection_enabled(self, stop_hook):
        """Test that lock blocks stop when reflection is enabled."""
        # Set up: Lock active, reflection enabled (default)
        stop_hook.lock_flag.touch()

        # Execute
        result = stop_hook.process({})

        # Verify: Lock should block
        assert result["decision"] == "block"
        assert "lock" in result["reason"].lower() or "continue" in result["reason"].lower()

    def test_lock_blocks_when_reflection_disabled_via_env(self, stop_hook):
        """Test that lock blocks stop when reflection is disabled via AMPLIHACK_SKIP_REFLECTION."""
        # Set up: Lock active, reflection disabled via env var
        stop_hook.lock_flag.touch()
        os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

        try:
            # Execute
            result = stop_hook.process({})

            # Verify: Lock should STILL block (lock is checked BEFORE reflection)
            assert result["decision"] == "block", "Lock must block even when reflection disabled"
            assert "lock" in result["reason"].lower() or "continue" in result["reason"].lower()
        finally:
            # Clean up
            if "AMPLIHACK_SKIP_REFLECTION" in os.environ:
                del os.environ["AMPLIHACK_SKIP_REFLECTION"]

    def test_lock_blocks_when_reflection_disabled_via_config(self, stop_hook):
        """Test that lock blocks stop when reflection is disabled via config."""
        # Set up: Lock active, reflection disabled via config
        stop_hook.lock_flag.touch()
        config_path = stop_hook.project_root / ".claude" / "tools" / "amplihack" / ".reflection_config"
        config_path.write_text(json.dumps({"enabled": False}))

        # Execute
        result = stop_hook.process({})

        # Verify: Lock should STILL block
        assert result["decision"] == "block", "Lock must block even when reflection disabled"
        assert "lock" in result["reason"].lower() or "continue" in result["reason"].lower()

    def test_no_lock_no_reflection_allows_stop(self, stop_hook):
        """Test that stop is allowed when lock is inactive and reflection is disabled."""
        # Set up: No lock, reflection disabled
        os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

        try:
            # Execute
            result = stop_hook.process({})

            # Verify: Should allow stop
            assert result["decision"] == "approve"
        finally:
            # Clean up
            if "AMPLIHACK_SKIP_REFLECTION" in os.environ:
                del os.environ["AMPLIHACK_SKIP_REFLECTION"]

    def test_lock_priority_over_reflection(self, stop_hook):
        """Test that lock is checked BEFORE reflection (priority test)."""
        # Set up: Both lock and reflection active
        stop_hook.lock_flag.touch()

        # Mock reflection to verify it's NOT called when lock is active
        with patch.object(stop_hook, '_should_run_reflection', return_value=True) as mock_reflection_check:
            with patch.object(stop_hook, '_run_reflection_sync') as mock_reflection_run:
                # Execute
                result = stop_hook.process({})

                # Verify: Lock blocks immediately
                assert result["decision"] == "block"

                # Verify: Reflection check was called (to determine flow)
                # but reflection execution should NOT happen
                mock_reflection_run.assert_not_called()

    def test_reflection_disabled_env_var_only_affects_reflection(self, stop_hook):
        """Test that AMPLIHACK_SKIP_REFLECTION only affects reflection, not lock."""
        # Set up: Lock active, env var set
        stop_hook.lock_flag.touch()
        os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

        try:
            # Execute
            result = stop_hook.process({})

            # Verify: Lock still works
            assert result["decision"] == "block"

            # Now remove lock
            stop_hook.lock_flag.unlink()

            # Execute again
            result = stop_hook.process({})

            # Verify: Now it should approve (no lock, reflection skipped)
            assert result["decision"] == "approve"
        finally:
            # Clean up
            if "AMPLIHACK_SKIP_REFLECTION" in os.environ:
                del os.environ["AMPLIHACK_SKIP_REFLECTION"]

    def test_custom_continuation_prompt_with_reflection_disabled(self, stop_hook):
        """Test that custom continuation prompt works when reflection is disabled."""
        # Set up: Lock active with custom prompt, reflection disabled
        stop_hook.lock_flag.touch()
        custom_prompt = "Custom continuation instructions"
        stop_hook.continuation_prompt_file.write_text(custom_prompt)
        os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

        try:
            # Execute
            result = stop_hook.process({})

            # Verify: Lock blocks with custom prompt
            assert result["decision"] == "block"
            assert custom_prompt in result["reason"]
        finally:
            # Clean up
            if "AMPLIHACK_SKIP_REFLECTION" in os.environ:
                del os.environ["AMPLIHACK_SKIP_REFLECTION"]


class TestExecutionFlow:
    """Test the execution flow to ensure lock is always checked first."""

    def test_execution_order_lock_before_reflection(self, stop_hook):
        """Test that lock is evaluated before reflection in execution order."""
        # Set up: Lock active
        stop_hook.lock_flag.touch()

        # Mock both lock and reflection checks to track execution order
        call_order = []

        original_exists = stop_hook.lock_flag.exists

        def mock_lock_exists():
            call_order.append("lock_check")
            return original_exists()

        def mock_reflection_check():
            call_order.append("reflection_check")
            return True

        with patch.object(Path, 'exists', side_effect=mock_lock_exists):
            with patch.object(stop_hook, '_should_run_reflection', side_effect=mock_reflection_check):
                # Execute
                result = stop_hook.process({})

                # Verify: Lock blocks
                assert result["decision"] == "block"

                # Verify: Lock was checked first
                assert call_order[0] == "lock_check"


def test_integration_scenario_cli_flag(temp_project_root):
    """Integration test: Simulate CLI with --no-reflection flag."""
    # Simulate what happens when user runs: amplihack --no-reflection
    # This sets AMPLIHACK_SKIP_REFLECTION=1

    # Set up environment as CLI would
    os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    try:
        # Create lock file (simulating lock mode)
        lock_file = temp_project_root / ".claude" / "runtime" / "locks" / ".lock_active"
        lock_file.touch()

        # Import and create hook
        import sys
        hooks_dir = Path(__file__).parent.parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
        sys.path.insert(0, str(hooks_dir))

        from stop import StopHook

        with patch.object(StopHook, 'project_root', temp_project_root):
            hook = StopHook()
            hook.project_root = temp_project_root
            hook.lock_flag = lock_file
            hook.continuation_prompt_file = temp_project_root / ".claude" / "runtime" / "locks" / ".continuation_prompt"

            # Execute
            result = hook.process({})

            # Verify: Lock MUST still work
            assert result["decision"] == "block", \
                "CRITICAL BUG: Lock mode broken when --no-reflection flag used!"
    finally:
        # Clean up
        if "AMPLIHACK_SKIP_REFLECTION" in os.environ:
            del os.environ["AMPLIHACK_SKIP_REFLECTION"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
