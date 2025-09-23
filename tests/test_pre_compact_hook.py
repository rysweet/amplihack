#!/usr/bin/env python3
"""
Unit tests for the pre-compact hook.
Tests automatic transcript export before context compaction.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project paths before imports
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack" / "hooks"))
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack"))

from pre_compact import PreCompactHook  # noqa: E402


class TestPreCompactHook(unittest.TestCase):
    """Tests for the PreCompactHook class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

        # Create required directory structure
        logs_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs"
        logs_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_hook_with_mocked_paths(self):
        """Helper to create a hook instance with mocked paths."""
        hook = PreCompactHook()
        # Override the paths after instantiation
        hook.project_root = Path(self.temp_dir)
        hook.log_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs"
        hook.metrics_dir = Path(self.temp_dir) / ".claude" / "runtime" / "metrics"
        hook.analysis_dir = Path(self.temp_dir) / ".claude" / "runtime" / "analysis"
        # Ensure directories exist
        hook.log_dir.mkdir(parents=True, exist_ok=True)
        hook.metrics_dir.mkdir(parents=True, exist_ok=True)
        hook.analysis_dir.mkdir(parents=True, exist_ok=True)
        # Re-initialize session directory with new paths
        hook.session_id = hook.get_session_id()
        hook.session_dir = hook.log_dir / hook.session_id
        hook.session_dir.mkdir(parents=True, exist_ok=True)
        return hook

    @patch("pre_compact.datetime")
    def test_process_conversation_export(self, mock_datetime):
        """Test successful conversation export."""
        # Mock datetime
        mock_datetime.now.return_value.isoformat.return_value = "2025-09-23T12:00:00"
        mock_datetime.now.return_value.strftime.return_value = "20250923_120000"

        # Create hook with mocked paths
        hook = self._create_hook_with_mocked_paths()

        # Prepare input data
        input_data = {
            "conversation": [
                {
                    "role": "user",
                    "content": "Implement feature X with ALL requirements",
                    "timestamp": "2025-09-23T11:00:00",
                },
                {
                    "role": "assistant",
                    "content": "I'll implement feature X",
                    "timestamp": "2025-09-23T11:01:00",
                },
                {
                    "role": "user",
                    "content": "Make sure to handle edge cases",
                    "timestamp": "2025-09-23T11:02:00",
                },
            ],
            "trigger": "token_limit",
        }

        # Process the event
        result = hook.process(input_data)

        # Verify success
        self.assertEqual(result["status"], "success")
        self.assertIn("3 messages preserved", result["message"])
        self.assertIn("transcript_path", result)

        # Verify files were created
        session_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs" / hook.session_id
        transcript_file = session_dir / "CONVERSATION_TRANSCRIPT.md"
        self.assertTrue(transcript_file.exists())

        # Verify transcript content
        with open(transcript_file, "r") as f:
            content = f.read()
        self.assertIn("Conversation Transcript", content)
        self.assertIn("Messages: 3", content)
        self.assertIn("ALL requirements", content)

    def test_process_with_original_request_extraction(self):
        """Test that original request is extracted from conversation."""
        hook = self._create_hook_with_mocked_paths()

        input_data = {
            "messages": [
                {
                    "role": "user",
                    "content": """Implement conversation transcript and original request preservation similar to Microsoft Amplifier.
**Target**: Context preservation system for original user requirements
**Constraints**: Simple implementation based on Amplifier's proven approach""",
                    "timestamp": "2025-09-23T10:00:00",
                }
            ],
            "trigger": "manual",
        }

        result = hook.process(input_data)

        self.assertEqual(result["status"], "success")

        # Verify original request was saved
        session_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs" / hook.session_id
        original_request_file = session_dir / "ORIGINAL_REQUEST.md"
        self.assertTrue(original_request_file.exists())

        # Verify content
        with open(original_request_file, "r") as f:
            content = f.read()
        self.assertIn("Context preservation system", content)

    def test_compaction_event_tracking(self):
        """Test that compaction events are tracked."""
        hook = self._create_hook_with_mocked_paths()

        input_data = {
            "conversation": [
                {"role": "user", "content": "Test", "timestamp": "2025-09-23T10:00:00"}
            ],
            "trigger": "token_limit",
        }

        # Process multiple compaction events
        hook.process(input_data)
        hook.process(input_data)

        # Check metadata file
        metadata_file = hook.session_dir / "compaction_events.json"
        self.assertTrue(metadata_file.exists())

        with open(metadata_file, "r") as f:
            events = json.load(f)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["compaction_trigger"], "token_limit")
        self.assertEqual(events[0]["messages_exported"], 1)

    def test_transcript_copy_creation(self):
        """Test that transcript copies are created in subdirectory."""
        hook = self._create_hook_with_mocked_paths()

        input_data = {
            "conversation": [
                {"role": "user", "content": "Test message", "timestamp": "2025-09-23T10:00:00"}
            ]
        }

        hook.process(input_data)

        # Check that transcript copy was created
        transcripts_dir = hook.session_dir / "transcripts"
        self.assertTrue(transcripts_dir.exists())

        transcript_copies = list(transcripts_dir.glob("conversation_*.md"))
        self.assertEqual(len(transcript_copies), 1)

    def test_empty_conversation_handling(self):
        """Test handling of empty conversation data."""
        hook = self._create_hook_with_mocked_paths()

        input_data = {"conversation": [], "trigger": "manual"}

        result = hook.process(input_data)

        self.assertEqual(result["status"], "success")
        self.assertIn("0 messages preserved", result["message"])

    def test_error_handling(self):
        """Test error handling during export."""
        hook = self._create_hook_with_mocked_paths()

        # Provide invalid data that will cause an error
        input_data = None

        result = hook.process(input_data)

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to export conversation", result["message"])

    def test_restore_conversation_from_latest(self):
        """Test restoring conversation from latest transcript."""
        # Create a session with transcript
        session_id = "20250923_100000"
        session_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs" / session_id
        session_dir.mkdir(parents=True)

        transcript_file = session_dir / "CONVERSATION_TRANSCRIPT.md"
        transcript_file.write_text("# Test Transcript\nTest content")

        hook = self._create_hook_with_mocked_paths()
        result = hook.restore_conversation_from_latest()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "transcript")
        self.assertEqual(result[0]["session"], session_id)
        self.assertIn("CONVERSATION_TRANSCRIPT.md", result[0]["path"])

    def test_metrics_saving(self):
        """Test that metrics are saved correctly."""
        hook = self._create_hook_with_mocked_paths()

        input_data = {
            "conversation": [
                {"role": "user", "content": "Test 1"},
                {"role": "assistant", "content": "Response 1"},
                {"role": "user", "content": "Test 2"},
            ]
        }

        hook.process(input_data)

        # Check metrics file (metrics are saved as JSONL in metrics_dir, not session_dir)
        metrics_file = hook.metrics_dir / "pre_compact_metrics.jsonl"
        self.assertTrue(metrics_file.exists())

        # Read all metrics from JSONL file and verify content
        saved_metrics = {}
        with open(metrics_file, "r") as f:
            for line in f:
                metric = json.loads(line.strip())
                saved_metrics[metric["metric"]] = metric["value"]

        # Verify the metrics that should be saved
        self.assertEqual(saved_metrics.get("messages_exported"), 3)
        self.assertEqual(saved_metrics.get("transcript_exported"), True)
        self.assertEqual(saved_metrics.get("compaction_events"), 1)

    @patch("pre_compact.ContextPreserver")
    def test_context_preserver_integration(self, mock_preserver_class):
        """Test integration with ContextPreserver."""
        # Setup mock
        mock_preserver = MagicMock()
        mock_preserver_class.return_value = mock_preserver
        mock_preserver.extract_original_request.return_value = {
            "target": "Test target",
            "requirements": ["req1", "req2"],
            "session_id": "test_session",
        }
        mock_preserver.export_conversation_transcript.return_value = "/path/to/transcript.md"

        hook = self._create_hook_with_mocked_paths()

        input_data = {
            "conversation": [
                {
                    "role": "user",
                    "content": "This is a long user request that should trigger extraction" * 10,
                }
            ]
        }

        result = hook.process(input_data)

        # Verify ContextPreserver was used
        mock_preserver_class.assert_called_once_with(hook.session_id)
        mock_preserver.extract_original_request.assert_called_once()
        mock_preserver.export_conversation_transcript.assert_called_once()

        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
