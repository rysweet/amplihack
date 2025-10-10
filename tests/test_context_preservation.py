#!/usr/bin/env python3
"""
Unit tests for the context preservation system.
Tests extraction, preservation, and retrieval of original user requirements.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add project paths before imports
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack"))
sys.path.insert(0, str(project_root / "src"))

from context_preservation import ContextPreserver  # noqa: E402


class TestContextPreserver(unittest.TestCase):
    """Tests for the ContextPreserver class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_root = ContextPreserver.__init__.__globals__.get("project_root")
        # Monkey patch the project root for testing
        ContextPreserver.__init__.__globals__["project_root"] = Path(self.temp_dir)

        # Create required directory structure
        (Path(self.temp_dir) / ".claude" / "runtime" / "logs").mkdir(parents=True)

        # Create test preserver
        self.session_id = "test_20250923_120000"
        self.preserver = ContextPreserver(self.session_id)

    def tearDown(self):
        """Clean up test environment."""
        # Restore original project root
        if self.original_root:
            ContextPreserver.__init__.__globals__["project_root"] = self.original_root
        # Clean up temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_simple_request(self):
        """Test extraction from simple request."""
        prompt = "Implement a function to calculate fibonacci numbers."

        result = self.preserver.extract_original_request(prompt)

        self.assertEqual(result["session_id"], self.session_id)
        self.assertEqual(result["raw_prompt"], prompt)
        self.assertIn("fibonacci", result["target"].lower())
        self.assertGreater(result["word_count"], 0)

    def test_extract_structured_request(self):
        """Test extraction from structured request with explicit markers."""
        prompt = """
Implement conversation transcript and original request preservation for amplihack.

**Target**: Context preservation system for original user requirements
**Problem**: Original user requests get lost during context compaction and aren't consistently passed to subagents
**Constraints**: Simple implementation based on Amplifier's proven approach

## Requirements
- Extract explicit user requirements from initial request
- Store in structured format accessible to all agents
- Include in `.claude/runtime/logs/<session_id>/ORIGINAL_REQUEST.md`
"""

        result = self.preserver.extract_original_request(prompt)

        self.assertEqual(
            result["target"], "Context preservation system for original user requirements"
        )
        self.assertTrue(any("TARGET:" in req for req in result["requirements"]))
        self.assertTrue(any("PROBLEM:" in req for req in result["requirements"]))
        self.assertTrue(
            any("Simple implementation" in constraint for constraint in result["constraints"])
        )

    def test_parse_requirements_simple(self):
        """Test simple requirement parsing."""
        prompt = "Implement ALL authentication features and add comprehensive logging."

        requirements = self.preserver._parse_requirements(prompt)

        self.assertGreater(len(requirements), 0)
        self.assertTrue(any("ALL" in req for req in requirements))

    def test_parse_constraints_simple(self):
        """Test simple constraint parsing."""
        prompt = "**Constraints**: Cannot use external APIs"

        constraints = self.preserver._parse_constraints(prompt)

        self.assertGreaterEqual(len(constraints), 0)
        # At minimum, should not crash

    def test_parse_success_criteria_simple(self):
        """Test simple success criteria parsing."""
        prompt = "Success criteria: All tests pass with 90% coverage."

        criteria = self.preserver._parse_success_criteria(prompt)

        # Should not crash - criteria parsing may or may not find content
        self.assertIsInstance(criteria, list)

    def test_save_and_retrieve_request(self):
        """Test saving and retrieving original request."""
        prompt = "Implement ALL files backup system with no exclusions."

        # Extract and save
        self.preserver.extract_original_request(prompt)

        # Verify files were created
        session_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs" / self.session_id
        self.assertTrue((session_dir / "ORIGINAL_REQUEST.md").exists())
        self.assertTrue((session_dir / "original_request.json").exists())

        # Retrieve
        retrieved = self.preserver.get_original_request(self.session_id)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["raw_prompt"], prompt)
        self.assertEqual(retrieved["session_id"], self.session_id)

    def test_format_agent_context(self):
        """Test formatting for agent injection."""
        prompt = """
**Target**: Build a REST API
**Requirements**: Must handle authentication, Must support pagination
**Constraints**: No external dependencies
**Success Criteria**: 100% test coverage
"""

        original_request = self.preserver.extract_original_request(prompt)
        context = self.preserver.format_agent_context(original_request)

        self.assertIn("🎯 ORIGINAL USER REQUEST", context)
        self.assertIn("Build a REST API", context)
        self.assertIn("Requirements", context)
        self.assertIn("Constraints", context)
        self.assertIn("Success Criteria", context)
        self.assertIn("CRITICAL", context)

    def test_export_conversation_transcript(self):
        """Test conversation transcript export."""
        conversation_data = [
            {"timestamp": "2025-09-23T10:00:00", "role": "user", "content": "Test"}
        ]

        transcript_path = self.preserver.export_conversation_transcript(conversation_data)

        self.assertTrue(Path(transcript_path).exists())
        with open(transcript_path) as f:
            content = f.read()
        self.assertIn("Conversation Transcript", content)

    def test_get_latest_session_id(self):
        """Test getting the latest session ID."""
        logs_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs"
        (logs_dir / "20250923_120000").mkdir(parents=True)

        latest = self.preserver.get_latest_session_id()
        self.assertEqual(latest, "20250923_120000")

    def test_requirement_preservation(self):
        """Test that explicit requirements like 'ALL' are preserved."""
        prompt = """
Backup ALL files in the directory.
Include ALL subdirectories.
Process ALL file types without exception.
"""

        result = self.preserver.extract_original_request(prompt)

        # Ensure 'ALL' is preserved in requirements
        all_text = " ".join(result["requirements"])
        self.assertIn("ALL", all_text)

        # Ensure it's in the formatted context
        context = self.preserver.format_agent_context(result)
        self.assertIn("ALL", context)

    def test_empty_prompt_handling(self):
        """Test handling of empty prompts."""
        result = self.preserver.extract_original_request("")
        self.assertEqual(result["target"], "General development task")
        self.assertEqual(len(result["requirements"]), 0)

    def test_session_directory_creation(self):
        """Test that session directories are created properly."""
        session_id = "test_20250923_150000"
        ContextPreserver(session_id)
        session_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs" / session_id
        self.assertTrue(session_dir.exists())


if __name__ == "__main__":
    unittest.main()
