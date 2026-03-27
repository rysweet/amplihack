#!/usr/bin/env python3
"""Tests for stop hook lock mode safety valve (fixes #2874).

Verifies that the stop hook auto-approves after MAX_LOCK_ITERATIONS
to prevent infinite loops when the agent has nothing left to do.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def stop_hook(tmp_path):
    """Create a StopHook with a temporary project root."""
    with patch.dict(os.environ, {}, clear=False):
        # Remove any env vars that might interfere
        os.environ.pop("AMPLIHACK_SHUTDOWN_IN_PROGRESS", None)
        os.environ.pop("AMPLIHACK_MAX_LOCK_ITERATIONS", None)

        from stop import StopHook

        hook = StopHook()
        hook.project_root = tmp_path
        hook.lock_flag = tmp_path / ".claude" / "runtime" / "locks" / ".lock_active"
        hook.continuation_prompt_file = (
            tmp_path / ".claude" / "runtime" / "locks" / ".continuation_prompt"
        )
        return hook


@pytest.fixture
def locked_hook(stop_hook):
    """Create a StopHook with lock mode active."""
    stop_hook.lock_flag.parent.mkdir(parents=True, exist_ok=True)
    stop_hook.lock_flag.touch()
    return stop_hook


class TestSafetyValve:
    """Tests for the lock mode safety valve."""

    def test_lock_blocks_normally_below_threshold(self, locked_hook):
        """Lock mode should block stop when below threshold."""
        with patch.object(locked_hook, "_select_strategy", return_value=None), \
             patch.object(locked_hook, "_increment_lock_counter", return_value=1), \
             patch.object(locked_hook, "_get_current_session_id", return_value="test-session"), \
             patch.object(locked_hook, "save_metric"):
            result = locked_hook.process({})
            assert result["decision"] == "block"

    def test_safety_valve_triggers_at_threshold(self, locked_hook):
        """Safety valve should approve stop at max iterations."""
        with patch.object(locked_hook, "_select_strategy", return_value=None), \
             patch.object(locked_hook, "_increment_lock_counter", return_value=50), \
             patch.object(locked_hook, "_get_current_session_id", return_value="test-session"), \
             patch.object(locked_hook, "save_metric"):
            result = locked_hook.process({})
            assert result["decision"] == "approve"

    def test_safety_valve_removes_lock_file(self, locked_hook):
        """Safety valve should remove the lock file."""
        assert locked_hook.lock_flag.exists()
        with patch.object(locked_hook, "_select_strategy", return_value=None), \
             patch.object(locked_hook, "_increment_lock_counter", return_value=50), \
             patch.object(locked_hook, "_get_current_session_id", return_value="test-session"), \
             patch.object(locked_hook, "save_metric"):
            locked_hook.process({})
            assert not locked_hook.lock_flag.exists()

    def test_safety_valve_respects_custom_threshold(self, locked_hook):
        """Safety valve should respect AMPLIHACK_MAX_LOCK_ITERATIONS env var."""
        with patch.dict(os.environ, {"AMPLIHACK_MAX_LOCK_ITERATIONS": "5"}), \
             patch.object(locked_hook, "_select_strategy", return_value=None), \
             patch.object(locked_hook, "_increment_lock_counter", return_value=5), \
             patch.object(locked_hook, "_get_current_session_id", return_value="test-session"), \
             patch.object(locked_hook, "save_metric"):
            result = locked_hook.process({})
            assert result["decision"] == "approve"

    def test_lock_blocks_below_custom_threshold(self, locked_hook):
        """Lock should still block below custom threshold."""
        with patch.dict(os.environ, {"AMPLIHACK_MAX_LOCK_ITERATIONS": "5"}), \
             patch.object(locked_hook, "_select_strategy", return_value=None), \
             patch.object(locked_hook, "_increment_lock_counter", return_value=4), \
             patch.object(locked_hook, "_get_current_session_id", return_value="test-session"), \
             patch.object(locked_hook, "save_metric"):
            result = locked_hook.process({})
            assert result["decision"] == "block"

    def test_no_lock_file_approves_normally(self, stop_hook):
        """Without lock file, stop should approve (after other checks)."""
        with patch.object(stop_hook, "_select_strategy", return_value=None), \
             patch.object(stop_hook, "_handle_neo4j_cleanup"), \
             patch.object(stop_hook, "_handle_neo4j_learning"), \
             patch.object(stop_hook, "_should_run_power_steering", return_value=False), \
             patch.object(stop_hook, "_should_run_reflection", return_value=False):
            result = stop_hook.process({})
            assert result["decision"] == "approve"
