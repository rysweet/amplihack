#!/usr/bin/env python3
"""State machine tests for stop.py.

Covers: lock_mode state machine, safety valve, continuation prompt,
power_steering decision flow, reflection semaphore, _should_run_reflection,
_should_run_power_steering, _get_current_session_id, _increment_lock_counter.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_stop_hook(tmp_path=None):
    """Create a StopHook with mocked HookProcessor init."""
    root = tmp_path or Path(tempfile.mkdtemp())

    # Create required directories BEFORE StopHook.__init__ runs
    lock_dir = root / ".claude" / "runtime" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    log_dir = root / ".claude" / "runtime" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir = root / ".claude" / "runtime" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir = root / ".claude" / "runtime" / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    def fake_init(self, hook_name):
        self.hook_name = hook_name
        self.project_root = root
        self.log_dir = log_dir
        self.metrics_dir = metrics_dir
        self.analysis_dir = analysis_dir
        self.log_file = log_dir / f"{hook_name}.log"

    with patch("hook_processor.HookProcessor.__init__", fake_init):
        from stop import StopHook

        hook = StopHook()

    hook.log = MagicMock()
    hook.save_metric = MagicMock()
    return hook


# ============================================================================
# Shutdown fast-exit
# ============================================================================


class TestShutdownDetection:
    """Shutdown-in-progress should immediately approve."""

    def test_shutdown_approves_immediately(self):
        hook = _make_stop_hook()
        with patch("shutdown_context.is_shutdown_in_progress", return_value=True):
            result = hook.process({})
        assert result == {"decision": "approve"}


# ============================================================================
# Lock mode state machine
# ============================================================================


class TestLockModeStateMachine:
    """Lock flag controls whether stop is blocked or approved."""

    def test_no_lock_file_approves(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook._select_strategy = MagicMock(return_value=None)
        hook._should_run_power_steering = MagicMock(return_value=False)
        hook._should_run_reflection = MagicMock(return_value=False)
        with patch("shutdown_context.is_shutdown_in_progress", return_value=False):
            result = hook.process({})
        assert result["decision"] == "approve"

    def test_lock_file_exists_blocks(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook.lock_flag.touch()  # Create lock file
        hook._select_strategy = MagicMock(return_value=None)
        hook._increment_lock_counter = MagicMock(return_value=1)
        hook.read_continuation_prompt = MagicMock(return_value="keep working")
        with patch("shutdown_context.is_shutdown_in_progress", return_value=False):
            result = hook.process({})
        assert result["decision"] == "block"
        assert result["reason"] == "keep working"

    def test_lock_file_permission_error_approves(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook._select_strategy = MagicMock(return_value=None)
        # Override lock_flag to a path that raises PermissionError on stat
        mock_path = MagicMock()
        mock_path.stat.side_effect = PermissionError("denied")
        hook.lock_flag = mock_path
        with patch("shutdown_context.is_shutdown_in_progress", return_value=False):
            result = hook.process({})
        assert result["decision"] == "approve"


# ============================================================================
# Safety valve
# ============================================================================


class TestSafetyValve:
    """Safety valve prevents infinite lock mode loops."""

    def test_safety_valve_triggers_at_max_iterations(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook.lock_flag.touch()
        hook._select_strategy = MagicMock(return_value=None)
        hook._increment_lock_counter = MagicMock(return_value=50)
        hook._get_current_session_id = MagicMock(return_value="test-session")
        with patch("shutdown_context.is_shutdown_in_progress", return_value=False):
            with patch.dict(os.environ, {"AMPLIHACK_MAX_LOCK_ITERATIONS": "50"}):
                result = hook.process({})
        assert result["decision"] == "approve"
        # Lock file should have been removed
        assert not hook.lock_flag.exists()

    def test_safety_valve_not_triggered_below_max(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook.lock_flag.touch()
        hook._select_strategy = MagicMock(return_value=None)
        hook._increment_lock_counter = MagicMock(return_value=10)
        hook._get_current_session_id = MagicMock(return_value="test-session")
        hook.read_continuation_prompt = MagicMock(return_value="keep going")
        with patch("shutdown_context.is_shutdown_in_progress", return_value=False):
            with patch.dict(os.environ, {"AMPLIHACK_MAX_LOCK_ITERATIONS": "50"}):
                result = hook.process({})
        assert result["decision"] == "block"

    def test_safety_valve_custom_max_iterations(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook.lock_flag.touch()
        hook._select_strategy = MagicMock(return_value=None)
        hook._increment_lock_counter = MagicMock(return_value=5)
        hook._get_current_session_id = MagicMock(return_value="test-session")
        with patch("shutdown_context.is_shutdown_in_progress", return_value=False):
            with patch.dict(os.environ, {"AMPLIHACK_MAX_LOCK_ITERATIONS": "5"}):
                result = hook.process({})
        assert result["decision"] == "approve"

    def test_safety_valve_lock_unlink_fails(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook.lock_flag.touch()
        hook._select_strategy = MagicMock(return_value=None)
        hook._increment_lock_counter = MagicMock(return_value=50)
        hook._get_current_session_id = MagicMock(return_value="test-session")
        # Replace lock_flag with a mock that has stat() succeed but unlink() fail
        real_lock = hook.lock_flag
        mock_lock = MagicMock()
        mock_lock.stat.return_value = real_lock.stat()
        mock_lock.unlink.side_effect = OSError("cannot remove")
        hook.lock_flag = mock_lock
        with patch("shutdown_context.is_shutdown_in_progress", return_value=False):
            result = hook.process({})
        assert result["decision"] == "approve"


# ============================================================================
# Continuation prompt
# ============================================================================


class TestContinuationPrompt:
    """Test custom and default continuation prompt reading."""

    def test_no_file_returns_default(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        from stop import DEFAULT_CONTINUATION_PROMPT

        result = hook.read_continuation_prompt()
        assert result == DEFAULT_CONTINUATION_PROMPT

    def test_custom_prompt_returned(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook.continuation_prompt_file.write_text("Custom prompt here", encoding="utf-8")
        result = hook.read_continuation_prompt()
        assert result == "Custom prompt here"

    def test_empty_file_returns_default(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook.continuation_prompt_file.write_text("", encoding="utf-8")
        from stop import DEFAULT_CONTINUATION_PROMPT

        result = hook.read_continuation_prompt()
        assert result == DEFAULT_CONTINUATION_PROMPT

    def test_too_long_prompt_returns_default(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook.continuation_prompt_file.write_text("x" * 1001, encoding="utf-8")
        from stop import DEFAULT_CONTINUATION_PROMPT

        result = hook.read_continuation_prompt()
        assert result == DEFAULT_CONTINUATION_PROMPT

    def test_medium_length_prompt_with_warning(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        prompt = "x" * 700
        hook.continuation_prompt_file.write_text(prompt, encoding="utf-8")
        result = hook.read_continuation_prompt()
        assert result == prompt
        # Should have logged a warning about length
        hook.log.assert_any_call(
            "Custom prompt is long (700 chars) - consider shortening for clarity",
            "WARNING",
        )

    def test_permission_error_returns_default(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        # Replace continuation_prompt_file with mock that raises PermissionError
        mock_file = MagicMock()
        mock_file.read_text.side_effect = PermissionError("denied")
        hook.continuation_prompt_file = mock_file
        from stop import DEFAULT_CONTINUATION_PROMPT

        result = hook.read_continuation_prompt()
        assert result == DEFAULT_CONTINUATION_PROMPT


# ============================================================================
# _should_run_reflection
# ============================================================================


class TestShouldRunReflection:
    """Reflection gate checks."""

    def test_skip_env_var_disables(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        with patch.dict(os.environ, {"AMPLIHACK_SKIP_REFLECTION": "1"}):
            assert hook._should_run_reflection() is False

    def test_missing_config_returns_false(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        with patch.dict(os.environ, {}, clear=True):
            assert hook._should_run_reflection() is False

    def test_config_disabled_returns_false(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        config_path = tmp_path / ".claude" / "tools" / "amplihack" / ".reflection_config"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"enabled": False}))
        with patch.dict(os.environ, {}, clear=True):
            assert hook._should_run_reflection() is False

    def test_config_enabled_returns_true(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        config_path = tmp_path / ".claude" / "tools" / "amplihack" / ".reflection_config"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"enabled": True}))
        with patch.dict(os.environ, {}, clear=True):
            assert hook._should_run_reflection() is True

    def test_config_invalid_json_returns_false(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        config_path = tmp_path / ".claude" / "tools" / "amplihack" / ".reflection_config"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("{invalid json")
        with patch.dict(os.environ, {}, clear=True):
            assert hook._should_run_reflection() is False

    def test_concurrent_lock_prevents_reflection(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        # Config enabled
        config_path = tmp_path / ".claude" / "tools" / "amplihack" / ".reflection_config"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"enabled": True}))
        # Create concurrent lock
        reflection_dir = tmp_path / ".claude" / "runtime" / "reflection"
        reflection_dir.mkdir(parents=True, exist_ok=True)
        (reflection_dir / ".reflection_lock").touch()
        with patch.dict(os.environ, {}, clear=True):
            assert hook._should_run_reflection() is False


# ============================================================================
# _should_run_power_steering
# ============================================================================


class TestShouldRunPowerSteering:
    """Power-steering gate checks."""

    def test_disabled_returns_false(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        mock_checker = MagicMock()
        mock_checker._is_disabled.return_value = True
        with patch("power_steering_checker.PowerSteeringChecker", return_value=mock_checker):
            assert hook._should_run_power_steering() is False

    def test_concurrent_lock_returns_false(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        mock_checker = MagicMock()
        mock_checker._is_disabled.return_value = False
        # Create concurrent lock
        ps_dir = tmp_path / ".claude" / "runtime" / "power-steering"
        ps_dir.mkdir(parents=True, exist_ok=True)
        (ps_dir / ".power_steering_lock").touch()
        with patch("power_steering_checker.PowerSteeringChecker", return_value=mock_checker):
            assert hook._should_run_power_steering() is False

    def test_enabled_no_lock_returns_true(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        mock_checker = MagicMock()
        mock_checker._is_disabled.return_value = False
        with patch("power_steering_checker.PowerSteeringChecker", return_value=mock_checker):
            assert hook._should_run_power_steering() is True

    def test_import_error_returns_false(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        with patch.dict("sys.modules", {"power_steering_checker": None}):
            # Should fail-open (return False, not crash)
            result = hook._should_run_power_steering()
            assert result is False


# ============================================================================
# _get_current_session_id
# ============================================================================


class TestGetCurrentSessionId:
    """Session ID detection priority."""

    def test_env_var_takes_priority(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        with patch.dict(os.environ, {"CLAUDE_SESSION_ID": "env-session-123"}):
            assert hook._get_current_session_id() == "env-session-123"

    def test_amplihack_env_var_precedes_claude_env_var(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        with patch.dict(
            os.environ,
            {"AMPLIHACK_SESSION_ID": "amplihack-session", "CLAUDE_SESSION_ID": "claude-session"},
        ):
            assert hook._get_current_session_id() == "amplihack-session"

    def test_falls_back_to_logs_dir(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        # Create session directories
        (hook.log_dir / "session_abc").mkdir()
        with patch.dict(os.environ, {}, clear=True):
            result = hook._get_current_session_id()
            assert result == "session_abc"

    def test_generates_timestamp_when_no_sessions(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        with patch.dict(os.environ, {}, clear=True):
            result = hook._get_current_session_id()
            # Should be a timestamp-style string like 20250101_120000
            assert len(result) >= 10

    def test_handles_logs_dir_error(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        with patch.dict(os.environ, {}, clear=True):
            # Remove the env var but make logs dir listing fail
            with patch("pathlib.Path.iterdir", side_effect=OSError("denied")):
                result = hook._get_current_session_id()
                # Should fall through to timestamp generation
                assert len(result) >= 10


# ============================================================================
# _increment_lock_counter
# ============================================================================


class TestIncrementLockCounter:
    """Lock counter file operations."""

    def test_first_increment_returns_one(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        result = hook._increment_lock_counter("test-session")
        assert result == 1

    def test_second_increment_returns_two(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook._increment_lock_counter("test-session")
        result = hook._increment_lock_counter("test-session")
        assert result == 2

    def test_malformed_counter_forces_safety_valve_recovery(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        counter_file = (
            tmp_path / ".claude" / "runtime" / "locks" / "test-session" / "lock_invocations.txt"
        )
        counter_file.parent.mkdir(parents=True, exist_ok=True)
        counter_file.write_text("not_a_number")
        result = hook._increment_lock_counter("test-session")
        assert result == 50
        assert counter_file.read_text() == "50"

    def test_counter_write_failure_forces_safety_valve_recovery(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        with patch("builtins.open", side_effect=OSError("disk full")):
            result = hook._increment_lock_counter("test-session")
            assert result == 50

    def test_stale_lock_auto_unlocks(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook.lock_flag.parent.mkdir(parents=True, exist_ok=True)
        hook.lock_flag.write_text("locked_at: 2000-01-01T00:00:00\n", encoding="utf-8")
        hook._select_strategy = MagicMock(return_value=None)
        hook._get_current_session_id = MagicMock(return_value="current-session")

        with patch("shutdown_context.is_shutdown_in_progress", return_value=False):
            result = hook.process({})

        assert result["decision"] == "approve"
        assert not hook.lock_flag.exists()

    def test_foreign_session_lock_auto_unlocks(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook.lock_flag.parent.mkdir(parents=True, exist_ok=True)
        hook.lock_flag.write_text(
            "locked_at: 2099-01-01T00:00:00\nsession_id: previous-session\n",
            encoding="utf-8",
        )
        hook._select_strategy = MagicMock(return_value=None)
        hook._get_current_session_id = MagicMock(return_value="current-session")

        with patch("shutdown_context.is_shutdown_in_progress", return_value=False):
            result = hook.process({})

        assert result["decision"] == "approve"
        assert not hook.lock_flag.exists()


# ============================================================================
# _increment_power_steering_counter
# ============================================================================


class TestIncrementPowerSteeringCounter:
    """Power-steering counter file operations."""

    def test_first_increment_returns_one(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        result = hook._increment_power_steering_counter("ps-session")
        assert result == 1

    def test_failure_returns_zero(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        with patch("builtins.open", side_effect=OSError("disk full")):
            result = hook._increment_power_steering_counter("ps-session")
            assert result == 0


# ============================================================================
# Neo4j no-ops
# ============================================================================


class TestNeo4jNoOps:
    """Deprecated Neo4j methods should be no-ops."""

    def test_is_neo4j_in_use_always_false(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        assert hook._is_neo4j_in_use() is False

    def test_handle_neo4j_cleanup_no_crash(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook._handle_neo4j_cleanup()  # Should not raise

    def test_handle_neo4j_learning_no_crash(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook._handle_neo4j_learning()  # Should not raise


# ============================================================================
# Strategy delegation in process()
# ============================================================================


class TestStopStrategyDelegation:
    """Strategy can short-circuit stop processing."""

    def test_strategy_result_returned(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.handle_stop.return_value = {"decision": "approve", "custom": True}
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        with patch("shutdown_context.is_shutdown_in_progress", return_value=False):
            result = hook.process({})
        assert result.get("custom") is True

    def test_strategy_returns_none_continues(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.handle_stop.return_value = None
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        hook._should_run_power_steering = MagicMock(return_value=False)
        hook._should_run_reflection = MagicMock(return_value=False)
        with patch("shutdown_context.is_shutdown_in_progress", return_value=False):
            result = hook.process({})
        assert result["decision"] == "approve"


# ============================================================================
# Reflection semaphore
# ============================================================================


class TestReflectionSemaphore:
    """Reflection semaphore prevents re-showing."""

    def test_semaphore_exists_approves(self, tmp_path):
        hook = _make_stop_hook(tmp_path)
        hook._select_strategy = MagicMock(return_value=None)
        hook._should_run_power_steering = MagicMock(return_value=False)
        hook._should_run_reflection = MagicMock(return_value=True)
        hook._get_current_session_id = MagicMock(return_value="test-session")

        # Create semaphore
        reflection_dir = tmp_path / ".claude" / "runtime" / "reflection"
        reflection_dir.mkdir(parents=True, exist_ok=True)
        semaphore = reflection_dir / ".reflection_presented_test-session"
        semaphore.touch()

        with patch("shutdown_context.is_shutdown_in_progress", return_value=False):
            result = hook.process({})
        assert result["decision"] == "approve"
        # Semaphore should have been cleaned up
        assert not semaphore.exists()
