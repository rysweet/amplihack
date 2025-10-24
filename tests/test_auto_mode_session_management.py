#!/usr/bin/env python3
"""
TDD Tests for Auto Mode Session Management - All tests should FAIL until implementation

Tests define success criteria for:
1. Message tracking during auto mode execution
2. Duration tracking and formatting
3. Fork detection at 60-minute threshold
4. Export integration with transcript builder
5. Backward compatibility

These tests follow TDD principles:
- Write failing tests FIRST
- Tests define the interface
- Implementation comes AFTER tests pass
"""

import asyncio
import json
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

# Add project paths
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src" / "amplihack" / "launcher"))

from auto_mode import AutoMode


class TestMessageTracking(unittest.TestCase):
    """Test message tracking during auto mode execution.

    SUCCESS CRITERIA:
    - Messages captured at each phase (clarify, plan, execute, evaluate)
    - Message format matches transcript builder expectations
    - Messages include role, content, timestamp, phase metadata
    """

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=self.temp_dir
        )

    def test_auto_mode_has_messages_list(self):
        """FAIL: AutoMode should have a messages list attribute.

        Expected: self.messages = []
        Actual: Attribute doesn't exist yet
        """
        self.assertTrue(
            hasattr(self.auto_mode, "messages"),
            "AutoMode must have 'messages' attribute for session tracking",
        )
        self.assertIsInstance(self.auto_mode.messages, list, "messages must be a list")
        self.assertEqual(len(self.auto_mode.messages), 0, "messages should start empty")

    def test_messages_captured_during_clarify_phase(self):
        """FAIL: Messages should be captured during clarify phase.

        Expected: After turn 1, messages list contains clarify phase interaction
        Actual: No message tracking implemented
        """
        with patch.object(self.auto_mode, "_run_turn_with_sdk", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (0, "Clarified objective")

            # Run async session
            asyncio.run(self.auto_mode._run_async_session())

            # Check messages captured
            self.assertGreater(len(self.auto_mode.messages), 0, "Should capture messages")

            # Find clarify phase messages
            clarify_messages = [
                msg for msg in self.auto_mode.messages if msg.get("phase") == "clarifying"
            ]
            self.assertGreater(
                len(clarify_messages), 0, "Should have messages from clarify phase"
            )

    def test_messages_captured_during_planning_phase(self):
        """FAIL: Messages should be captured during planning phase.

        Expected: After turn 2, messages list contains planning phase interaction
        Actual: No message tracking implemented
        """
        with patch.object(self.auto_mode, "_run_turn_with_sdk", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                (0, "Clarified objective"),
                (0, "Created plan"),
            ]

            asyncio.run(self.auto_mode._run_async_session())

            planning_messages = [
                msg for msg in self.auto_mode.messages if msg.get("phase") == "planning"
            ]
            self.assertGreater(
                len(planning_messages), 0, "Should have messages from planning phase"
            )

    def test_messages_captured_during_execution_phase(self):
        """FAIL: Messages should be captured during execution phase.

        Expected: During execute turns, messages captured with phase='executing'
        Actual: No message tracking implemented
        """
        with patch.object(self.auto_mode, "_run_turn_with_sdk", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                (0, "Clarified"),
                (0, "Planned"),
                (0, "Executed"),
                (0, "auto-mode evaluation: complete"),
            ]

            asyncio.run(self.auto_mode._run_async_session())

            executing_messages = [
                msg for msg in self.auto_mode.messages if msg.get("phase") == "executing"
            ]
            self.assertGreater(
                len(executing_messages), 0, "Should have messages from executing phase"
            )

    def test_messages_captured_during_evaluation_phase(self):
        """FAIL: Messages should be captured during evaluation phase.

        Expected: After each execution, evaluation messages captured
        Actual: No message tracking implemented
        """
        with patch.object(self.auto_mode, "_run_turn_with_sdk", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                (0, "Clarified"),
                (0, "Planned"),
                (0, "Executed"),
                (0, "auto-mode evaluation: complete"),
            ]

            asyncio.run(self.auto_mode._run_async_session())

            evaluating_messages = [
                msg for msg in self.auto_mode.messages if msg.get("phase") == "evaluating"
            ]
            self.assertGreater(
                len(evaluating_messages), 0, "Should have messages from evaluating phase"
            )

    def test_message_format_includes_required_fields(self):
        """FAIL: Each message should have required fields for transcript builder.

        Expected format:
        {
            'role': 'user' or 'assistant',
            'content': 'message content',
            'timestamp': 'ISO format timestamp',
            'phase': 'clarifying'|'planning'|'executing'|'evaluating'|'summarizing',
            'turn': 1-N
        }

        Actual: No message format defined yet
        """
        with patch.object(self.auto_mode, "_run_turn_with_sdk", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (0, "Test response")

            asyncio.run(self.auto_mode._run_async_session())

            self.assertGreater(len(self.auto_mode.messages), 0)

            # Check first message has required fields
            msg = self.auto_mode.messages[0]
            self.assertIn("role", msg, "Message must have 'role' field")
            self.assertIn(msg["role"], ["user", "assistant"], "Role must be user or assistant")
            self.assertIn("content", msg, "Message must have 'content' field")
            self.assertIn("timestamp", msg, "Message must have 'timestamp' field")
            self.assertIn("phase", msg, "Message must have 'phase' field")
            self.assertIn("turn", msg, "Message must have 'turn' field")

    def test_all_phases_captured_in_complete_session(self):
        """FAIL: Complete session should have messages from all phases.

        Expected: Messages from clarifying, planning, executing, evaluating, summarizing
        Actual: No message tracking implemented
        """
        with patch.object(self.auto_mode, "_run_turn_with_sdk", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                (0, "Clarified"),
                (0, "Planned"),
                (0, "Executed"),
                (0, "auto-mode evaluation: complete"),
                (0, "Summary"),
            ]

            asyncio.run(self.auto_mode._run_async_session())

            phases = {msg.get("phase") for msg in self.auto_mode.messages}

            expected_phases = {"clarifying", "planning", "executing", "evaluating", "summarizing"}
            self.assertTrue(
                expected_phases.issubset(phases),
                f"Should have all phases. Got: {phases}, Expected: {expected_phases}",
            )


class TestDurationTracking(unittest.TestCase):
    """Test duration tracking and formatting.

    SUCCESS CRITERIA:
    - Duration calculated from session start to current time
    - Duration formatted as human-readable (Xm Ys or Xh Ym)
    - Duration visible in log messages
    - Duration cumulative across the session
    """

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=self.temp_dir
        )

    def test_session_duration_calculated_correctly(self):
        """FAIL: Session should track total elapsed time.

        Expected: Duration = current_time - start_time
        Actual: Duration tracking not fully integrated with session
        """
        # Start time is set in run()
        start_time = time.time()
        self.auto_mode.start_time = start_time

        # Simulate some elapsed time
        time.sleep(0.1)

        # Get duration
        elapsed = time.time() - self.auto_mode.start_time
        self.assertGreater(elapsed, 0.09, "Duration should be > 0.09 seconds")
        self.assertLess(elapsed, 1.0, "Duration should be < 1 second in this test")

    def test_duration_formatted_as_seconds_for_short_sessions(self):
        """FAIL: Duration under 60 seconds should format as 'Xs'.

        Expected: 45 seconds -> "45s"
        Actual: Method exists but not used for session duration
        """
        result = self.auto_mode._format_elapsed(45.7)
        self.assertEqual(result, "45s", "Should format as seconds only")

    def test_duration_formatted_as_minutes_and_seconds(self):
        """FAIL: Duration over 60 seconds should format as 'Xm Ys'.

        Expected: 125 seconds -> "2m 5s"
        Actual: Method exists but not used for session duration
        """
        result = self.auto_mode._format_elapsed(125)
        self.assertEqual(result, "2m 5s", "Should format as minutes and seconds")

    def test_duration_appears_in_progress_string(self):
        """FAIL: Progress string should include current duration.

        Expected: "[Turn 2/10 | Planning | 1m 23s]"
        Actual: Method exists but not tracked in session context
        """
        self.auto_mode.start_time = time.time() - 83  # 83 seconds ago
        self.auto_mode.turn = 2

        progress = self.auto_mode._progress_str("Planning")

        self.assertIn("1m 23s", progress, "Should show duration in progress")
        self.assertIn("Turn 2/10", progress, "Should show turn progress")
        self.assertIn("Planning", progress, "Should show current phase")

    def test_session_duration_tracked_in_metadata(self):
        """FAIL: Session should store total duration in metadata.

        Expected: After session completes, duration available for export
        Actual: No session metadata structure yet
        """
        with patch.object(self.auto_mode, "_run_turn_with_sdk", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                (0, "Clarified"),
                (0, "Planned"),
                (0, "Executed"),
                (0, "auto-mode evaluation: complete"),
                (0, "Summary"),
            ]

            # Simulate some time passing
            self.auto_mode.start_time = time.time() - 10

            asyncio.run(self.auto_mode._run_async_session())

            # Check metadata exists
            self.assertTrue(
                hasattr(self.auto_mode, "session_metadata"),
                "Should have session_metadata attribute",
            )
            self.assertIn("duration_seconds", self.auto_mode.session_metadata)
            self.assertGreater(self.auto_mode.session_metadata["duration_seconds"], 9)

    def test_duration_formatted_for_export(self):
        """FAIL: Session metadata should include human-readable duration.

        Expected: metadata includes both duration_seconds and duration_formatted
        Actual: No metadata export structure yet
        """
        self.auto_mode.start_time = time.time() - 150  # 2m 30s ago

        with patch.object(self.auto_mode, "_run_turn_with_sdk", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (0, "auto-mode evaluation: complete")

            asyncio.run(self.auto_mode._run_async_session())

            self.assertTrue(hasattr(self.auto_mode, "session_metadata"))
            self.assertIn("duration_formatted", self.auto_mode.session_metadata)
            self.assertIn("2m", self.auto_mode.session_metadata["duration_formatted"])


class TestForkDetection(unittest.TestCase):
    """Test fork detection at 60-minute threshold.

    SUCCESS CRITERIA:
    - Fork triggered when session duration >= 60 minutes
    - Fork NOT triggered before 60 minutes
    - Fork carries context forward to new session
    - Original session completes with fork marker
    """

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=30, working_dir=self.temp_dir
        )

    def test_fork_not_triggered_before_60_minutes(self):
        """FAIL: Fork should NOT trigger for sessions under 60 minutes.

        Expected: No fork for 59 minute session
        Actual: Fork detection not implemented
        """
        self.auto_mode.start_time = time.time() - (59 * 60)  # 59 minutes ago

        should_fork = self.auto_mode._should_fork_session()
        self.assertFalse(should_fork, "Should not fork before 60 minutes")

    def test_fork_triggered_at_60_minutes(self):
        """FAIL: Fork should trigger when session reaches 60 minutes.

        Expected: Fork triggered at exactly 60 minutes
        Actual: Fork detection method doesn't exist
        """
        self.auto_mode.start_time = time.time() - (60 * 60)  # Exactly 60 minutes

        should_fork = self.auto_mode._should_fork_session()
        self.assertTrue(should_fork, "Should fork at 60 minutes")

    def test_fork_triggered_after_60_minutes(self):
        """FAIL: Fork should trigger for sessions over 60 minutes.

        Expected: Fork triggered at 65 minutes
        Actual: Fork detection method doesn't exist
        """
        self.auto_mode.start_time = time.time() - (65 * 60)  # 65 minutes ago

        should_fork = self.auto_mode._should_fork_session()
        self.assertTrue(should_fork, "Should fork after 60 minutes")

    def test_fork_creates_new_session_with_context(self):
        """FAIL: Fork should create new session with carried context.

        Expected: New AutoMode instance with summary of previous session
        Actual: Fork method doesn't exist
        """
        self.auto_mode.start_time = time.time() - (61 * 60)
        self.auto_mode.messages = [
            {"role": "user", "content": "Original prompt"},
            {"role": "assistant", "content": "Working on it"},
        ]

        new_session = self.auto_mode._fork_session()

        self.assertIsInstance(new_session, AutoMode, "Should create new AutoMode instance")
        self.assertNotEqual(
            new_session.session_id, self.auto_mode.session_id, "Should have different session ID"
        )
        self.assertIn("continuation", new_session.prompt.lower(), "Should indicate continuation")

    def test_fork_exports_current_session_before_forking(self):
        """FAIL: Before forking, current session should be exported.

        Expected: Transcript exported before fork
        Actual: Export integration not implemented
        """
        self.auto_mode.start_time = time.time() - (61 * 60)
        self.auto_mode.messages = [{"role": "user", "content": "Test"}]

        with patch.object(self.auto_mode, "_export_session_transcript") as mock_export:
            self.auto_mode._fork_session()

            mock_export.assert_called_once()

    def test_fork_logs_continuation_marker(self):
        """FAIL: Fork should log that session is being forked.

        Expected: Log message indicating fork and new session ID
        Actual: Fork logging not implemented
        """
        self.auto_mode.start_time = time.time() - (61 * 60)

        with patch.object(self.auto_mode, "log") as mock_log:
            self.auto_mode._fork_session()

            # Check that fork was logged
            fork_logged = any("fork" in str(call).lower() for call in mock_log.call_args_list)
            self.assertTrue(fork_logged, "Should log fork event")


class TestExportIntegration(unittest.TestCase):
    """Test export integration with transcript builder.

    SUCCESS CRITERIA:
    - Export triggered at stop hook
    - Export creates valid transcript file
    - Transcript includes all messages
    - Transcript includes duration metadata
    - Export triggered before fork
    """

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=self.temp_dir
        )

    def test_export_method_exists(self):
        """FAIL: AutoMode should have export method.

        Expected: _export_session_transcript() method exists
        Actual: Method doesn't exist yet
        """
        self.assertTrue(
            hasattr(self.auto_mode, "_export_session_transcript"),
            "Should have _export_session_transcript method",
        )
        self.assertTrue(
            callable(self.auto_mode._export_session_transcript),
            "Method should be callable",
        )

    def test_export_creates_transcript_file(self):
        """FAIL: Export should create transcript file in session directory.

        Expected: CONVERSATION_TRANSCRIPT.md created in log_dir/session_id/
        Actual: Export not implemented
        """
        self.auto_mode.messages = [
            {"role": "user", "content": "Test message", "timestamp": "2024-01-01T00:00:00"},
            {"role": "assistant", "content": "Response", "timestamp": "2024-01-01T00:00:10"},
        ]

        transcript_path = self.auto_mode._export_session_transcript()

        self.assertTrue(Path(transcript_path).exists(), "Transcript file should exist")
        self.assertEqual(
            Path(transcript_path).name,
            "CONVERSATION_TRANSCRIPT.md",
            "Should be named CONVERSATION_TRANSCRIPT.md",
        )

    def test_export_includes_all_messages(self):
        """FAIL: Exported transcript should include all captured messages.

        Expected: All messages from self.messages in transcript
        Actual: Export not implemented
        """
        test_messages = [
            {"role": "user", "content": "Message 1", "phase": "clarifying", "turn": 1},
            {"role": "assistant", "content": "Response 1", "phase": "clarifying", "turn": 1},
            {"role": "user", "content": "Message 2", "phase": "planning", "turn": 2},
            {"role": "assistant", "content": "Response 2", "phase": "planning", "turn": 2},
        ]
        self.auto_mode.messages = test_messages

        transcript_path = self.auto_mode._export_session_transcript()

        with open(transcript_path) as f:
            content = f.read()
            self.assertIn("Message 1", content)
            self.assertIn("Response 1", content)
            self.assertIn("Message 2", content)
            self.assertIn("Response 2", content)

    def test_export_includes_duration_metadata(self):
        """FAIL: Transcript should include session duration in metadata.

        Expected: Transcript header includes duration
        Actual: Export not implemented
        """
        self.auto_mode.start_time = time.time() - 150  # 2m 30s ago
        self.auto_mode.messages = [{"role": "user", "content": "Test"}]
        self.auto_mode.session_metadata = {
            "duration_seconds": 150,
            "duration_formatted": "2m 30s",
        }

        transcript_path = self.auto_mode._export_session_transcript()

        with open(transcript_path) as f:
            content = f.read()
            self.assertIn("2m 30s", content, "Should include formatted duration")
            self.assertIn("150", content, "Should include seconds")

    def test_export_called_in_stop_hook(self):
        """FAIL: Export should be triggered when session ends.

        Expected: _export_session_transcript called in finally block
        Actual: Not integrated into session lifecycle
        """
        with patch.object(self.auto_mode, "_run_turn_with_sdk", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (0, "auto-mode evaluation: complete")

            with patch.object(self.auto_mode, "_export_session_transcript") as mock_export:
                asyncio.run(self.auto_mode._run_async_session())

                mock_export.assert_called_once()

    def test_export_creates_json_for_programmatic_access(self):
        """FAIL: Export should create JSON version for programmatic access.

        Expected: conversation_transcript.json created alongside markdown
        Actual: JSON export not implemented
        """
        self.auto_mode.messages = [
            {"role": "user", "content": "Test", "timestamp": "2024-01-01T00:00:00"}
        ]

        self.auto_mode._export_session_transcript()

        json_file = self.auto_mode.session_dir / "conversation_transcript.json"
        self.assertTrue(json_file.exists(), "JSON transcript should exist")

        # Verify JSON structure
        with open(json_file) as f:
            data = json.load(f)
            self.assertIn("session_id", data)
            self.assertIn("messages", data)
            self.assertEqual(len(data["messages"]), 1)


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with existing auto_mode usage.

    SUCCESS CRITERIA:
    - Existing auto_mode calls work without changes
    - Optional session management (can be disabled)
    - No breaking changes to public API
    - Performance impact minimal (<5% overhead)
    """

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_auto_mode_works_without_session_tracking(self):
        """FAIL: AutoMode should work even if session tracking disabled.

        Expected: Session tracking can be disabled via flag
        Actual: No disable mechanism yet
        """
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test",
            max_turns=3,
            working_dir=self.temp_dir,
            enable_session_management=False,  # New optional parameter
        )

        # Should still work
        self.assertEqual(auto_mode.prompt, "Test")
        self.assertEqual(auto_mode.max_turns, 3)

    def test_existing_public_api_unchanged(self):
        """FAIL: Public API should remain unchanged.

        Expected: run(), run_sdk(), log() methods unchanged
        Actual: API should be backward compatible
        """
        auto_mode = AutoMode(sdk="claude", prompt="Test", working_dir=self.temp_dir)

        # Check public methods exist
        self.assertTrue(hasattr(auto_mode, "run"))
        self.assertTrue(hasattr(auto_mode, "run_sdk"))
        self.assertTrue(hasattr(auto_mode, "log"))
        self.assertTrue(hasattr(auto_mode, "run_hook"))

        # Check signatures haven't changed (no required new parameters)
        import inspect

        run_sig = inspect.signature(auto_mode.run)
        self.assertEqual(len(run_sig.parameters), 0, "run() should have no required parameters")

    def test_session_management_minimal_overhead(self):
        """FAIL: Session management should add minimal overhead.

        Expected: < 5% performance overhead
        Actual: Performance not measured yet
        """
        # Test with session management disabled
        auto_mode_no_tracking = AutoMode(
            sdk="claude",
            prompt="Test",
            max_turns=1,
            working_dir=self.temp_dir,
            enable_session_management=False,
        )

        with patch.object(
            auto_mode_no_tracking, "_run_turn_with_sdk", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = (0, "auto-mode evaluation: complete")

            start = time.time()
            asyncio.run(auto_mode_no_tracking._run_async_session())
            time_no_tracking = time.time() - start

        # Test with session management enabled
        auto_mode_with_tracking = AutoMode(
            sdk="claude",
            prompt="Test",
            max_turns=1,
            working_dir=self.temp_dir,
            enable_session_management=True,
        )

        with patch.object(
            auto_mode_with_tracking, "_run_turn_with_sdk", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = (0, "auto-mode evaluation: complete")

            start = time.time()
            asyncio.run(auto_mode_with_tracking._run_async_session())
            time_with_tracking = time.time() - start

        # Overhead should be less than 5%
        overhead_ratio = (time_with_tracking - time_no_tracking) / time_no_tracking
        self.assertLess(
            overhead_ratio, 0.05, f"Overhead {overhead_ratio:.2%} should be < 5%"
        )

    def test_session_dir_structure_compatible(self):
        """FAIL: Session directory structure should be compatible with existing tools.

        Expected: Files created in .claude/runtime/logs/<session_id>/
        Actual: Structure should match existing conventions
        """
        auto_mode = AutoMode(sdk="claude", prompt="Test", working_dir=self.temp_dir)

        expected_log_dir = self.temp_dir / ".claude" / "runtime" / "logs"
        self.assertTrue(
            str(auto_mode.log_dir).startswith(str(expected_log_dir)),
            f"Log dir should be under {expected_log_dir}",
        )

    def test_existing_hooks_still_called(self):
        """FAIL: Existing session_start and stop hooks should still be called.

        Expected: Hooks called as before, plus new export functionality
        Actual: Hook integration should be backward compatible
        """
        auto_mode = AutoMode(sdk="copilot", prompt="Test", working_dir=self.temp_dir)

        with patch.object(auto_mode, "run_hook") as mock_hook:
            with patch.object(auto_mode, "run_sdk") as mock_sdk:
                mock_sdk.return_value = (0, "auto-mode evaluation: complete")

                auto_mode._run_sync_session()

                # Check hooks were called
                hook_calls = [call[0][0] for call in mock_hook.call_args_list]
                self.assertIn("session_start", hook_calls, "session_start hook should be called")
                self.assertIn("stop", hook_calls, "stop hook should be called")


class TestSessionMetadata(unittest.TestCase):
    """Test session metadata collection and structure.

    SUCCESS CRITERIA:
    - Metadata includes session_id, start_time, end_time, duration
    - Metadata includes turn count, phase breakdown
    - Metadata compatible with transcript builder
    - Metadata available for export
    """

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=self.temp_dir
        )

    def test_session_metadata_structure(self):
        """FAIL: Session metadata should have required fields.

        Expected: session_metadata with id, timestamps, duration, turns, phases
        Actual: Metadata structure not defined yet
        """
        with patch.object(self.auto_mode, "_run_turn_with_sdk", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (0, "auto-mode evaluation: complete")

            asyncio.run(self.auto_mode._run_async_session())

            metadata = self.auto_mode.session_metadata

            # Required fields
            self.assertIn("session_id", metadata)
            self.assertIn("start_time", metadata)
            self.assertIn("end_time", metadata)
            self.assertIn("duration_seconds", metadata)
            self.assertIn("duration_formatted", metadata)
            self.assertIn("total_turns", metadata)
            self.assertIn("max_turns", metadata)
            self.assertIn("prompt", metadata)
            self.assertIn("sdk", metadata)

    def test_session_metadata_phase_breakdown(self):
        """FAIL: Metadata should include breakdown of time spent in each phase.

        Expected: phase_durations with clarifying, planning, executing, evaluating, summarizing
        Actual: Phase tracking not implemented
        """
        with patch.object(self.auto_mode, "_run_turn_with_sdk", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (0, "auto-mode evaluation: complete")

            asyncio.run(self.auto_mode._run_async_session())

            metadata = self.auto_mode.session_metadata
            self.assertIn("phase_breakdown", metadata)

            phase_breakdown = metadata["phase_breakdown"]
            self.assertIn("clarifying", phase_breakdown)
            self.assertIn("planning", phase_breakdown)
            self.assertIn("executing", phase_breakdown)
            self.assertIn("evaluating", phase_breakdown)

    def test_session_metadata_compatible_with_transcript_builder(self):
        """FAIL: Metadata format should match transcript builder expectations.

        Expected: Metadata can be passed directly to ClaudeTranscriptBuilder
        Actual: Format not validated yet
        """
        with patch.object(self.auto_mode, "_run_turn_with_sdk", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (0, "auto-mode evaluation: complete")

            asyncio.run(self.auto_mode._run_async_session())

            metadata = self.auto_mode.session_metadata

            # Should be JSON-serializable
            json_str = json.dumps(metadata)
            self.assertIsInstance(json_str, str)

            # Should have expected structure
            parsed = json.loads(json_str)
            self.assertEqual(parsed["session_id"], metadata["session_id"])


if __name__ == "__main__":
    # Run tests and expect failures (TDD approach)
    unittest.main(verbosity=2)
