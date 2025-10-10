#!/usr/bin/env python3
"""
Tests for Transcript and Codex Builders - Microsoft Amplifier Style
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add the source path for testing
test_dir = Path(__file__).parent
project_root = test_dir.parent
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack"))


class TestClaudeTranscriptBuilder(unittest.TestCase):
    """Test cases for ClaudeTranscriptBuilder."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_session_id = "test_session_20241002_092454"

        # Mock the get_project_root function
        self.mock_project_root = Path(self.temp_dir)

        with patch(
            "builders.claude_transcript_builder.get_project_root",
            return_value=self.mock_project_root,
        ):
            from builders.claude_transcript_builder import ClaudeTranscriptBuilder

            self.builder = ClaudeTranscriptBuilder(self.test_session_id)

    def test_initialization(self):
        """Test builder initialization."""
        self.assertEqual(self.builder.session_id, self.test_session_id)
        self.assertTrue(self.builder.session_dir.exists())

    def test_build_session_transcript(self):
        """Test session transcript building."""
        test_messages = [
            {
                "role": "user",
                "content": "Hello, can you help me with Python?",
                "timestamp": "2024-10-02T09:24:54Z",
            },
            {
                "role": "assistant",
                "content": "I'll help you with Python. What specifically do you need help with?",
                "timestamp": "2024-10-02T09:25:10Z",
            },
        ]

        test_metadata = {"session_type": "coding_assistance", "user_id": "test_user"}

        transcript_path = self.builder.build_session_transcript(test_messages, test_metadata)

        self.assertTrue(Path(transcript_path).exists())

        # Check content
        with open(transcript_path) as f:
            content = f.read()
            self.assertIn(self.test_session_id, content)
            self.assertIn("Hello, can you help me with Python?", content)
            self.assertIn("I'll help you with Python", content)
            self.assertIn("Messages**: 2", content)

    def test_build_session_summary(self):
        """Test session summary building."""
        test_messages = [
            {
                "role": "user",
                "content": 'Test message with some <function_calls><invoke name="Read">content</invoke></function_calls>',
                "timestamp": "2024-10-02T09:24:54Z",
            }
        ]

        summary = self.builder.build_session_summary(test_messages)

        self.assertEqual(summary["session_id"], self.test_session_id)
        self.assertEqual(summary["message_count"], 1)
        self.assertGreater(summary["total_characters"], 0)
        self.assertGreater(summary["total_words"], 0)
        self.assertIn("tools_used", summary)

    def test_export_for_codex(self):
        """Test codex export functionality."""
        test_messages = [
            {
                "role": "user",
                "content": "Can you create a Python function?",
                "timestamp": "2024-10-02T09:24:54Z",
            },
            {
                "role": "assistant",
                "content": "Here's a Python function:\n```python\ndef hello():\n    print('Hello')\n```",
                "timestamp": "2024-10-02T09:25:10Z",
            },
        ]

        codex_path = self.builder.export_for_codex(test_messages)

        self.assertTrue(Path(codex_path).exists())

        # Check content structure
        with open(codex_path) as f:
            codex_data = json.load(f)

            self.assertIn("session_metadata", codex_data)
            self.assertIn("conversation_flow", codex_data)
            self.assertIn("knowledge_artifacts", codex_data)
            self.assertIn("raw_messages", codex_data)

            # Check that code blocks are detected
            artifacts = codex_data["knowledge_artifacts"]
            self.assertTrue(any(artifact["type"] == "code_block" for artifact in artifacts))

    def test_tool_extraction(self):
        """Test tool extraction from messages."""
        test_message = {
            "role": "assistant",
            "content": '<function_calls><invoke name="Read"><parameter name="file_path">test.py</parameter></invoke></function_calls>',
        }

        tools = self.builder._extract_tools_from_message(test_message)
        self.assertIn("Read", tools)

    def test_key_topics_extraction(self):
        """Test key topics extraction."""
        test_messages = [
            {
                "role": "user",
                "content": "I need help with Python programming and database optimization",
            }
        ]

        topics = self.builder._extract_key_topics(test_messages)
        self.assertIsInstance(topics, list)
        # Should extract technical terms
        self.assertTrue(any("python" in topic.lower() for topic in topics))


class TestCodexTranscriptsBuilder(unittest.TestCase):
    """Test cases for CodexTranscriptsBuilder."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_project_root = Path(self.temp_dir)

        # Create mock session structure
        self.logs_dir = self.mock_project_root / ".claude" / "runtime" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Create test session directory
        self.test_session_dir = self.logs_dir / "20241002_092454"
        self.test_session_dir.mkdir(exist_ok=True)

        # Create sample session files
        self._create_sample_session_files()

        with patch(
            "builders.codex_transcripts_builder.get_project_root",
            return_value=self.mock_project_root,
        ):
            from builders.codex_transcripts_builder import CodexTranscriptsBuilder

            self.builder = CodexTranscriptsBuilder()

    def _create_sample_session_files(self):
        """Create sample session files for testing."""
        # Sample transcript
        transcript_data = {
            "session_id": "20241002_092454",
            "created_at": "2024-10-02T09:24:54Z",
            "messages": [
                {"role": "user", "content": "Hello", "timestamp": "2024-10-02T09:24:54Z"},
                {"role": "assistant", "content": "Hi there!", "timestamp": "2024-10-02T09:25:00Z"},
            ],
        }

        transcript_file = self.test_session_dir / "conversation_transcript.json"
        with open(transcript_file, "w") as f:
            json.dump(transcript_data, f)

        # Sample codex export
        codex_data = {
            "session_metadata": {"id": "20241002_092454"},
            "tools_usage": {"total_tool_calls": 5, "unique_tools": ["Read", "Write"]},
            "decisions_made": [{"decision": "Implement feature X", "role": "assistant"}],
            "outcomes_achieved": [{"type": "success", "description": "Feature implemented"}],
        }

        codex_file = self.test_session_dir / "codex_export.json"
        with open(codex_file, "w") as f:
            json.dump(codex_data, f)

        # Sample summary
        summary_data = {
            "session_id": "20241002_092454",
            "message_count": 2,
            "tools_used": ["Read", "Write"],
            "timestamp": "2024-10-02T09:24:54Z",
        }

        summary_file = self.test_session_dir / "session_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary_data, f)

    def test_get_all_session_ids(self):
        """Test getting all session IDs."""
        session_ids = self.builder._get_all_session_ids()
        self.assertIn("20241002_092454", session_ids)

    def test_load_session_data(self):
        """Test loading session data."""
        session_data = self.builder._load_session_data("20241002_092454")

        self.assertIsNotNone(session_data)
        self.assertEqual(session_data["session_id"], "20241002_092454")
        self.assertIsNotNone(session_data["transcript"])
        self.assertIsNotNone(session_data["codex_export"])
        self.assertIsNotNone(session_data["summary"])

    def test_build_comprehensive_codex(self):
        """Test building comprehensive codex."""
        codex_path = self.builder.build_comprehensive_codex()

        self.assertTrue(Path(codex_path).exists())

        # Check content structure
        with open(codex_path) as f:
            codex_data = json.load(f)

            self.assertIn("metadata", codex_data)
            self.assertIn("tool_usage_analytics", codex_data)
            self.assertIn("conversation_insights", codex_data)
            self.assertIn("session_summaries", codex_data)

    def test_extract_learning_corpus(self):
        """Test learning corpus extraction."""
        corpus_path = self.builder.extract_learning_corpus()

        self.assertTrue(Path(corpus_path).exists())

        # Check content structure
        with open(corpus_path) as f:
            corpus_data = json.load(f)

            self.assertIn("metadata", corpus_data)
            self.assertIn("conversation_patterns", corpus_data)
            self.assertIn("problem_solution_pairs", corpus_data)

    def test_generate_insights_report(self):
        """Test insights report generation."""
        report_path = self.builder.generate_insights_report()

        self.assertTrue(Path(report_path).exists())

        # Check content structure
        with open(report_path) as f:
            report_data = json.load(f)

            self.assertIn("executive_summary", report_data)
            self.assertIn("productivity_metrics", report_data)
            self.assertIn("recommendations", report_data)

    def test_build_focused_codex(self):
        """Test building focused codex."""
        # Test tools focus
        tools_codex_path = self.builder.build_focused_codex("tools")
        self.assertTrue(Path(tools_codex_path).exists())

        with open(tools_codex_path) as f:
            tools_data = json.load(f)
            self.assertEqual(tools_data["focus"], "tools")

        # Test errors focus
        errors_codex_path = self.builder.build_focused_codex("errors")
        self.assertTrue(Path(errors_codex_path).exists())

    def test_invalid_focus_area(self):
        """Test handling of invalid focus area."""
        with self.assertRaises(ValueError):
            self.builder.build_focused_codex("invalid_area")


class TestExportOnCompactIntegration(unittest.TestCase):
    """Test cases for ExportOnCompactIntegration."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_project_root = Path(self.temp_dir)

        # Create basic structure
        logs_dir = self.mock_project_root / ".claude" / "runtime" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Add hook processor path to sys.path
        test_dir = Path(__file__).parent
        hook_path = test_dir.parent / ".claude" / "tools" / "amplihack" / "hooks"
        sys.path.insert(0, str(hook_path))

        with patch.object(Path, "mkdir"):
            with patch("builders.claude_transcript_builder.ClaudeTranscriptBuilder"):
                with patch("builders.codex_transcripts_builder.CodexTranscriptsBuilder"):
                    from builders.export_on_compact_integration import ExportOnCompactIntegration

                    # Create instance with real HookProcessor init but mocked dependencies
                    self.integration = ExportOnCompactIntegration()

                    # Override session_id for consistent testing
                    self.integration.session_id = "test_session_20241002"
                    self.integration.session_dir = logs_dir / self.integration.session_id

    def test_initialization(self):
        """Test integration initialization."""
        self.assertEqual(self.integration.session_id, "test_session_20241002")
        self.assertIsNotNone(self.integration.transcript_builder)
        self.assertIsNotNone(self.integration.codex_builder)

    @patch("builders.export_on_compact_integration.ExportOnCompactIntegration.log")
    @patch("builders.export_on_compact_integration.ExportOnCompactIntegration.save_metric")
    def test_process_enhanced_export(self, mock_save_metric, mock_log):
        """Test enhanced export processing."""
        # Create session directory
        self.integration.session_dir.mkdir(parents=True, exist_ok=True)

        test_input = {
            "conversation": [
                {"role": "user", "content": "Test message", "timestamp": "2024-10-02T09:24:54Z"}
            ],
            "metadata": {"test": "data"},
            "trigger": "manual",
        }

        # Mock builder methods
        with patch.object(
            self.integration.transcript_builder,
            "build_session_transcript",
            return_value="transcript_path",
        ), patch.object(
            self.integration.transcript_builder,
            "build_session_summary",
            return_value={"message_count": 1},
        ), patch.object(
            self.integration.transcript_builder,
            "export_for_codex",
            return_value="codex_path",
        ):
            result = self.integration.process(test_input)

            self.assertEqual(result["status"], "success")
            self.assertIn("exports", result)
            self.assertIn("transcript", result["exports"])
            self.assertIn("summary", result["exports"])
            self.assertIn("codex_export", result["exports"])

    def test_list_available_sessions(self):
        """Test listing available sessions."""
        # Create sample session directory
        sample_session = self.integration.log_dir / "20241002_092454"
        sample_session.mkdir(parents=True, exist_ok=True)

        # Create sample files
        (sample_session / "session_summary.json").write_text(
            '{"message_count": 5, "tools_used": ["Read", "Write"], "timestamp": "2024-10-02T09:24:54Z"}'
        )

        sessions = self.integration.list_available_sessions()

        self.assertIsInstance(sessions, list)
        if sessions:  # Only check if sessions were found
            session = sessions[0]
            self.assertIn("session_id", session)
            self.assertIn("has_transcript", session)
            self.assertIn("has_summary", session)


class TestIntegrationFlow(unittest.TestCase):
    """Integration tests for the complete flow."""

    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_project_root = Path(self.temp_dir)

    def test_complete_export_flow(self):
        """Test the complete export flow from messages to codex."""
        # This would test the full pipeline:
        # messages -> transcript -> summary -> codex export -> comprehensive codex

        test_messages = [
            {
                "role": "user",
                "content": "I need help with Python programming",
                "timestamp": "2024-10-02T09:24:54Z",
            },
            {
                "role": "assistant",
                "content": "I'll help you with Python. What specifically do you need?",
                "timestamp": "2024-10-02T09:25:00Z",
            },
        ]

        with patch(
            "builders.claude_transcript_builder.get_project_root",
            return_value=self.mock_project_root,
        ):
            from builders.claude_transcript_builder import ClaudeTranscriptBuilder

            builder = ClaudeTranscriptBuilder("integration_test_session")

            # Build transcript
            transcript_path = builder.build_session_transcript(test_messages)
            self.assertTrue(Path(transcript_path).exists())

            # Build summary
            summary = builder.build_session_summary(test_messages)
            self.assertGreater(summary["message_count"], 0)

            # Export for codex
            codex_path = builder.export_for_codex(test_messages)
            self.assertTrue(Path(codex_path).exists())

            # Verify files exist and have correct structure
            with open(codex_path) as f:
                codex_data = json.load(f)
                self.assertIn("session_metadata", codex_data)
                self.assertIn("raw_messages", codex_data)


def run_tests():
    """Run all tests."""
    print("🧪 Running Transcript and Codex Builders Tests...")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestClaudeTranscriptBuilder))
    suite.addTests(loader.loadTestsFromTestCase(TestCodexTranscriptsBuilder))
    suite.addTests(loader.loadTestsFromTestCase(TestExportOnCompactIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationFlow))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return success status
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
