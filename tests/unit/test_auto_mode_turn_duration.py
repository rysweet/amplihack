"""Tests for turn duration tracking in auto-mode.

Tests that each turn's duration is tracked and reported:
- Turn start time recorded at beginning of turn
- Turn duration calculated at end of turn
- Duration logged with turn completion
- Session metrics aggregated and logged
"""

from unittest.mock import patch

from amplihack.launcher.auto_mode import AutoMode


class TestTurnDurationTracking:
    """Test turn duration tracking functionality."""

    def test_turn_durations_initialized_empty(self):
        """turn_durations list should be initialized empty."""
        auto_mode = AutoMode(sdk="claude", prompt="Test prompt", max_turns=3)
        assert hasattr(auto_mode, "turn_durations")
        assert auto_mode.turn_durations == []

    @patch("amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE", False)
    @patch("amplihack.launcher.auto_mode.AutoMode.run_sdk")
    @patch("time.time")
    def test_turn_duration_recorded(self, mock_time, mock_run_sdk):
        """Turn duration should be recorded for each turn."""
        # Mock time to simulate turn execution
        mock_time.side_effect = [
            1000.0,  # session start
            1000.0,  # turn 1 start (clarify)
            1001.0,  # turn 1 end
            1001.0,  # turn 2 start (plan)
            1003.0,  # turn 2 end
            1003.0,  # turn 3 start (execute)
            1008.0,  # turn 3 end
            1008.0,  # session metrics calculation
        ]

        # Mock run_sdk to return success
        mock_run_sdk.return_value = (0, "Test output")

        auto_mode = AutoMode(sdk="claude", prompt="Test prompt", max_turns=3)

        # Mock run_hook to avoid actual hook execution
        with patch.object(auto_mode, "run_hook"):
            auto_mode._run_sync_session()

        # Should have 1 duration recorded for turn 3 (execute + evaluate)
        assert len(auto_mode.turn_durations) == 1
        assert auto_mode.turn_durations[0] == 5.0  # 1008.0 - 1003.0

    @patch("amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE", False)
    @patch("amplihack.launcher.auto_mode.AutoMode.run_sdk")
    @patch("time.time")
    def test_session_metrics_logged(self, mock_time, mock_run_sdk):
        """Session metrics should be logged after all turns complete."""
        # Mock time to simulate multiple turns
        mock_time.side_effect = [
            1000.0,  # session start
            1000.0,  # turn 1 start
            1001.0,  # turn 1 end
            1001.0,  # turn 2 start
            1003.0,  # turn 2 end
            1003.0,  # turn 3 start
            1008.0,  # turn 3 end
            1008.0,  # session metrics
        ]

        # Mock run_sdk to return success
        mock_run_sdk.return_value = (0, "Test output")

        auto_mode = AutoMode(sdk="claude", prompt="Test prompt", max_turns=3)

        # Capture log calls
        log_calls = []
        original_log = auto_mode.log

        def capture_log(msg, level="INFO"):
            log_calls.append({"msg": msg, "level": level})
            original_log(msg, level)

        with patch.object(auto_mode, "log", side_effect=capture_log):
            with patch.object(auto_mode, "run_hook"):
                auto_mode._run_sync_session()

        # Check that session metrics were logged
        session_metrics_logs = [log for log in log_calls if "Session metrics:" in log["msg"]]
        assert len(session_metrics_logs) > 0

        # Verify metrics content
        metrics_msg = session_metrics_logs[0]["msg"]
        assert "turns" in metrics_msg
        assert "avg" in metrics_msg
        assert "max" in metrics_msg
        assert "total" in metrics_msg

    def test_turn_duration_format(self):
        """Turn duration should be formatted to 1 decimal place."""
        auto_mode = AutoMode(sdk="claude", prompt="Test prompt", max_turns=3)

        # Manually set turn durations
        auto_mode.turn_durations = [10.123456, 20.987654, 5.5]

        # Calculate metrics
        avg_duration = sum(auto_mode.turn_durations) / len(auto_mode.turn_durations)
        max_duration = max(auto_mode.turn_durations)
        total_duration = sum(auto_mode.turn_durations)

        # Verify formatting (1 decimal place)
        assert f"{avg_duration:.1f}" == "12.2"
        assert f"{max_duration:.1f}" == "21.0"
        assert f"{total_duration:.1f}" == "36.6"
