"""Unit tests for AutoMode timeout and session-limit behavior.

Tests for:
1. Default timeout is 30.0 minutes
2. None timeout is accepted (disables per-query timeout)
3. Explicit timeout values are respected
4. Session-level API-call and duration limits are env-var-configurable
5. Edge cases: zero/negative/very-long timeouts
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from amplihack.launcher.auto_mode import AutoMode


@pytest.fixture(autouse=True)
def disable_agent_memory():
    """Keep timeout-focused tests out of the Kuzu-backed memory path."""
    with patch("amplihack.launcher.agent_memory.AgentMemory.create", return_value=None):
        yield


class TestDefaultTimeout:
    """Test that default timeout is 30.0 minutes (not 5.0)."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_default_timeout_is_30_minutes(self, temp_working_dir):
        """Test that AutoMode uses 30.0 minute default timeout.

        Expected behavior:
        - Default query_timeout_minutes should be 30.0
        - query_timeout_seconds should be 1800.0 (30 * 60)

        This is a change from the previous default of 5.0 minutes.
        Rationale: 5 minutes is too short for complex agentic tasks.
        """
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test prompt",
            max_turns=5,
            working_dir=temp_working_dir,
            # NOTE: Not passing query_timeout_minutes - should use default
        )

        # Default should be 30.0 minutes = 1800 seconds
        assert auto_mode.query_timeout_seconds == 1800.0, (
            f"Default timeout should be 30 minutes (1800s), "
            f"got {auto_mode.query_timeout_seconds / 60} minutes"
        )


class TestNoTimeoutFlag:
    """Test --no-timeout flag disables timeout (sets to None)."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_none_timeout_accepted(self, temp_working_dir):
        """Test that AutoMode accepts None timeout without error.

        Expected behavior:
        - AutoMode should accept query_timeout_minutes=None
        - query_timeout_seconds should be None
        - No validation error should be raised

        This enables --no-timeout flag to disable timeout completely.
        """
        # This test should fail until AutoMode is updated to accept None
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test prompt",
            max_turns=5,
            working_dir=temp_working_dir,
            query_timeout_minutes=None,  # type: ignore  # Testing new feature
        )

        assert auto_mode.query_timeout_seconds is None, (
            "When query_timeout_minutes is None, query_timeout_seconds should be None (no timeout)"
        )

    def test_none_timeout_disables_validation(self, temp_working_dir):
        """Test that None timeout bypasses positive value validation.

        Expected behavior:
        - None should not trigger 'must be positive' validation error
        - None is a valid sentinel value meaning 'no timeout'
        """
        # Should not raise ValueError for None
        try:
            AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=temp_working_dir,
                query_timeout_minutes=None,  # type: ignore
            )
        except ValueError as e:
            pytest.fail(f"None should be accepted without validation error: {e}")


class TestExplicitTimeout:
    """Test explicit --query-timeout-minutes value is respected."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_explicit_timeout_15_minutes(self, temp_working_dir):
        """Test that explicit timeout value is used.

        Expected behavior:
        - query_timeout_minutes=15.0 should set query_timeout_seconds=900.0
        """
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test prompt",
            max_turns=5,
            working_dir=temp_working_dir,
            query_timeout_minutes=15.0,
        )

        assert auto_mode.query_timeout_seconds == 900.0, (
            f"Explicit 15 minute timeout should be 900s, got {auto_mode.query_timeout_seconds}"
        )

    def test_explicit_timeout_45_minutes(self, temp_working_dir):
        """Test that explicit 45 minute timeout is used.

        Expected behavior:
        - query_timeout_minutes=45.0 should set query_timeout_seconds=2700.0
        """
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test prompt",
            max_turns=5,
            working_dir=temp_working_dir,
            query_timeout_minutes=45.0,
        )

        assert auto_mode.query_timeout_seconds == 2700.0, (
            f"Explicit 45 minute timeout should be 2700s, got {auto_mode.query_timeout_seconds}"
        )


class TestSessionLimitOverrides:
    """Test environment overrides for auto-mode session safety limits."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_session_limit_env_overrides_are_applied(self, temp_working_dir):
        """Configured env vars should override default session caps."""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_AUTO_MODE_MAX_TOTAL_API_CALLS": "99",
                "AMPLIHACK_AUTO_MODE_MAX_SESSION_DURATION_SECONDS": "7200",
            },
            clear=False,
        ):
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=temp_working_dir,
            )

        assert auto_mode.max_total_api_calls == 99
        assert auto_mode.max_session_duration == 7200

    def test_invalid_session_limit_env_values_warn_and_fall_back(self, temp_working_dir):
        """Invalid env values should warn explicitly and use safe defaults."""
        with (
            patch.object(AutoMode, "log") as mock_log,
            patch.dict(
                os.environ,
                {
                    "AMPLIHACK_AUTO_MODE_MAX_TOTAL_API_CALLS": "bad",
                    "AMPLIHACK_AUTO_MODE_MAX_SESSION_DURATION_SECONDS": "0",
                },
                clear=False,
            ),
        ):
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=temp_working_dir,
            )

        assert auto_mode.max_total_api_calls == 50
        assert auto_mode.max_session_duration == 3600
        assert any(
            "AMPLIHACK_AUTO_MODE_MAX_TOTAL_API_CALLS" in call.args[0]
            and call.kwargs.get("level") == "WARNING"
            for call in mock_log.call_args_list
        )
        assert any(
            "AMPLIHACK_AUTO_MODE_MAX_SESSION_DURATION_SECONDS" in call.args[0]
            and call.kwargs.get("level") == "WARNING"
            for call in mock_log.call_args_list
        )


class TestEdgeCases:
    """Test edge cases for timeout handling."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_zero_timeout_still_rejected(self, temp_working_dir):
        """Test that zero timeout is still rejected.

        Expected behavior:
        - query_timeout_minutes=0 should raise ValueError
        - Only None (no timeout) and positive values are valid
        """
        with pytest.raises(ValueError, match="must be positive"):
            AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=temp_working_dir,
                query_timeout_minutes=0.0,
            )

    def test_negative_timeout_still_rejected(self, temp_working_dir):
        """Test that negative timeout is still rejected.

        Expected behavior:
        - query_timeout_minutes=-5.0 should raise ValueError
        """
        with pytest.raises(ValueError, match="must be positive"):
            AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=temp_working_dir,
                query_timeout_minutes=-5.0,
            )

    def test_very_long_timeout_warning_threshold_unchanged(self, temp_working_dir, capsys):
        """Test warning for very long timeouts still works.

        Expected behavior:
        - timeout > 120 minutes should print warning
        - This behavior should be unchanged
        """
        AutoMode(
            sdk="claude",
            prompt="Test prompt",
            max_turns=5,
            working_dir=temp_working_dir,
            query_timeout_minutes=130.0,
        )

        captured = capsys.readouterr()
        assert "Warning" in captured.err, "Very long timeout (>120 min) should print warning"
