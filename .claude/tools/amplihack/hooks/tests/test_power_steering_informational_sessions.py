#!/usr/bin/env python3
"""
Tests for power-steering handling of INFORMATIONAL (Q&A) sessions.

Verifies that simple Q&A sessions skip power-steering checks appropriately.
Tests for issues #2021 and #2011.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


class TestInformationalSessions:
    """Tests for INFORMATIONAL (Q&A) session handling."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temporary project directory."""
        project = tmp_path / "project"
        project.mkdir()

        # Create .claude directory structure
        claude_dir = project / ".claude"
        claude_dir.mkdir()

        tools_dir = claude_dir / "tools" / "amplihack"
        tools_dir.mkdir(parents=True)

        runtime_dir = claude_dir / "runtime" / "power-steering"
        runtime_dir.mkdir(parents=True)

        return project

    @pytest.fixture
    def qa_transcript_path(self, temp_project):
        """Create a Q&A session transcript (INFORMATIONAL type)."""
        transcript = temp_project / "transcript.jsonl"

        # Create a simple Q&A session with only Read tools
        with open(transcript, "w") as f:
            # User asks a question
            entry = {
                "role": "user",
                "content": [{"type": "text", "text": "What hooks are currently configured?"}],
            }
            f.write(json.dumps(entry) + "\n")

            # Assistant reads config file
            entry = {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me check the hooks configuration"},
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/.claude/tools/amplihack/hooks/"},
                    },
                ],
            }
            f.write(json.dumps(entry) + "\n")

            # Tool result
            entry = {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "123",
                        "content": "stop.py, session_stop.py",
                    }
                ],
            }
            f.write(json.dumps(entry) + "\n")

            # Assistant responds with answer
            entry = {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "The configured hooks are: stop.py and session_stop.py",
                    }
                ],
            }
            f.write(json.dumps(entry) + "\n")

        return transcript

    @pytest.fixture
    def checker(self, temp_project):
        """Create PowerSteeringChecker instance."""
        return PowerSteeringChecker(project_root=temp_project)

    def test_informational_session_detection(self, checker, qa_transcript_path):
        """Test that Q&A sessions are correctly detected as INFORMATIONAL."""
        # Load transcript
        transcript = []
        with open(qa_transcript_path) as f:
            for line in f:
                if line.strip():
                    transcript.append(json.loads(line))

        session_type = checker.detect_session_type(transcript)
        assert session_type == "INFORMATIONAL", f"Expected INFORMATIONAL, got {session_type}"

    def test_informational_session_skips_checks(self, checker, qa_transcript_path):
        """Test that INFORMATIONAL sessions skip most power-steering checks."""
        # Load transcript
        transcript = []
        with open(qa_transcript_path) as f:
            for line in f:
                if line.strip():
                    transcript.append(json.loads(line))

        # Get applicable considerations for INFORMATIONAL session
        applicable = checker.get_applicable_considerations("INFORMATIONAL")

        # INFORMATIONAL sessions should have very few or no applicable checks
        # The objective_completion check should NOT be in the list
        consideration_ids = [c["id"] for c in applicable]
        assert "objective_completion" not in consideration_ids, (
            "objective_completion should not apply to INFORMATIONAL sessions"
        )

        # Most development checks should not apply
        assert "todos_complete" not in consideration_ids
        assert "dev_workflow_complete" not in consideration_ids
        assert "local_testing_complete" not in consideration_ids

    @patch("power_steering_checker.PowerSteeringChecker._is_qa_session", return_value=False)
    def test_informational_session_auto_approves(
        self, mock_qa, checker, qa_transcript_path, temp_project
    ):
        """Test that INFORMATIONAL sessions auto-approve without blocking."""
        result = checker.check(qa_transcript_path, "test-session-qa")

        assert result.decision == "approve", (
            f"INFORMATIONAL session should auto-approve, got {result.decision}"
        )
        assert "no_applicable_checks" in result.reasons or "auto_approve" in result.reasons, (
            f"Expected auto-approval reason, got {result.reasons}"
        )

    def test_simple_question_session(self, temp_project):
        """Test simple question like 'tell me what agents you have'."""
        transcript_path = temp_project / "simple_question.jsonl"

        # Create even simpler Q&A transcript
        with open(transcript_path, "w") as f:
            # User asks a simple question
            entry = {
                "role": "user",
                "content": [{"type": "text", "text": "tell me what agents you have"}],
            }
            f.write(json.dumps(entry) + "\n")

            # Assistant provides answer without any tools
            entry = {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "I have architect, builder, tester, and reviewer agents available.",
                    }
                ],
            }
            f.write(json.dumps(entry) + "\n")

        checker = PowerSteeringChecker(project_root=temp_project)

        # Load transcript
        transcript = []
        with open(transcript_path) as f:
            for line in f:
                if line.strip():
                    transcript.append(json.loads(line))

        session_type = checker.detect_session_type(transcript)
        assert session_type == "INFORMATIONAL", (
            f"Simple question should be INFORMATIONAL, got {session_type}"
        )

        # Should have no applicable checks
        applicable = checker.get_applicable_considerations("INFORMATIONAL")
        assert len(applicable) == 0, (
            f"INFORMATIONAL sessions should have no applicable checks, got {len(applicable)}"
        )


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
