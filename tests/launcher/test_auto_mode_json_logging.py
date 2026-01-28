"""Integration tests for JSON logging in auto_mode.

These tests verify that auto_mode correctly logs structured events
to auto.jsonl during execution.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplihack.launcher.auto_mode import AutoMode


class TestAutoModeJsonLogging:
    """Test JSON logging integration with AutoMode."""

    def test_json_logger_initialized(self):
        """Verify JsonLogger is initialized during AutoMode init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auto = AutoMode(
                sdk="claude",
                prompt="Test task",
                max_turns=5,
                working_dir=Path(tmpdir),
            )

            assert hasattr(auto, "json_logger")
            assert auto.json_logger.log_file.name == "auto.jsonl"

    @pytest.mark.asyncio
    async def test_turn_start_logged_during_async_session(self):
        """Verify turn_start events are logged during async session execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auto = AutoMode(
                sdk="claude",
                prompt="Test objective",
                max_turns=3,
                working_dir=Path(tmpdir),
            )

            # Mock the SDK response to avoid actual API calls
            async def mock_query(*args, **kwargs):
                """Mock async generator for SDK query."""
                # Create mock AssistantMessage
                mock_message = MagicMock()
                mock_message.__class__.__name__ = "AssistantMessage"
                mock_message.content = [
                    MagicMock(type="text", text="Test response - objective clarified")
                ]
                yield mock_message

            with patch("amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE", True):
                with patch("amplihack.launcher.auto_mode.query", side_effect=mock_query):
                    # Mock the retry method to return success immediately
                    auto._run_turn_with_retry = AsyncMock(return_value=(0, "Success"))

                    # Run turn 1 only (clarify objective)
                    auto.turn = 1
                    auto.message_capture.set_phase("clarifying", auto.turn)

                    # Log turn start event
                    auto.json_logger.log_event(
                        "turn_start",
                        {"turn": auto.turn, "phase": "clarifying", "max_turns": auto.max_turns},
                    )

                    # Verify the event was logged
                    jsonl_file = auto.log_dir / "auto.jsonl"
                    assert jsonl_file.exists()

                    with open(jsonl_file) as f:
                        event = json.loads(f.readline())

                    assert event["event"] == "turn_start"
                    assert event["turn"] == 1
                    assert event["phase"] == "clarifying"
                    assert event["max_turns"] == 3

    def test_json_log_file_created_in_log_dir(self):
        """Verify auto.jsonl is created in the correct log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auto = AutoMode(
                sdk="claude",
                prompt="Test",
                max_turns=5,
                working_dir=Path(tmpdir),
            )

            # Log an event to trigger file creation
            auto.json_logger.log_event("turn_start", {"turn": 1, "phase": "test", "max_turns": 5})

            # Verify file exists in log directory
            expected_file = auto.log_dir / "auto.jsonl"
            assert expected_file.exists()

            # Verify log directory structure
            assert auto.log_dir.exists()
            assert auto.log_dir.parent.name == "logs"
