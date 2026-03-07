#!/usr/bin/env python3
"""Tests for OPERATIONS session type detection (fixes #2913/#2914).

Verifies that PM/planning sessions (e.g. /pm-architect, backlog triage)
are correctly classified as OPERATIONS and skip all power-steering checks.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


@pytest.fixture
def checker(tmp_path):
    """Create a PowerSteeringChecker with a temporary project root."""
    c = PowerSteeringChecker(tmp_path)
    return c


def _make_transcript(user_messages, assistant_messages=None):
    """Build a minimal transcript from user message strings."""
    transcript = []
    for msg in user_messages:
        transcript.append({
            "type": "user",
            "message": {"role": "user", "content": msg},
        })
    if assistant_messages:
        for msg in assistant_messages:
            transcript.append({
                "type": "assistant",
                "message": {"role": "assistant", "content": msg},
            })
    return transcript


class TestOperationsSessionDetection:
    """Tests for OPERATIONS session type classification."""

    def test_pm_architect_classified_as_operations(self, checker):
        """Session starting with /pm-architect should be OPERATIONS."""
        transcript = _make_transcript(["pm-architect please survey the project"])
        assert checker.detect_session_type(transcript) == "OPERATIONS"

    def test_backlog_keyword_classified_as_operations(self, checker):
        """Session mentioning backlog should be OPERATIONS."""
        transcript = _make_transcript(["Let's triage the backlog and prioritize"])
        assert checker.detect_session_type(transcript) == "OPERATIONS"

    def test_roadmap_keyword_classified_as_operations(self, checker):
        """Session mentioning roadmap should be OPERATIONS."""
        transcript = _make_transcript(["Update the roadmap for Q2"])
        assert checker.detect_session_type(transcript) == "OPERATIONS"

    def test_sprint_planning_classified_as_operations(self, checker):
        """Sprint planning session should be OPERATIONS."""
        transcript = _make_transcript(["Let's do sprint planning for this week"])
        assert checker.detect_session_type(transcript) == "OPERATIONS"

    def test_determine_next_steps_classified_as_operations(self, checker):
        """Asking to determine next steps should be OPERATIONS."""
        transcript = _make_transcript(["Help me determine next steps for the project"])
        assert checker.detect_session_type(transcript) == "OPERATIONS"

    def test_prioritization_classified_as_operations(self, checker):
        """Explicit prioritization request should be OPERATIONS."""
        transcript = _make_transcript(["Prioritize the open issues"])
        assert checker.detect_session_type(transcript) == "OPERATIONS"

    def test_operations_skips_all_considerations(self, checker):
        """OPERATIONS sessions should return zero applicable considerations."""
        applicable = checker.get_applicable_considerations("OPERATIONS")
        assert applicable == [], "OPERATIONS sessions should skip all considerations"

    def test_development_still_gets_checks(self, checker):
        """DEVELOPMENT sessions should still have considerations."""
        applicable = checker.get_applicable_considerations("DEVELOPMENT")
        assert len(applicable) > 0, "DEVELOPMENT sessions should have considerations"

    def test_env_override_operations(self, checker):
        """AMPLIHACK_SESSION_TYPE=OPERATIONS should override detection."""
        with patch.dict(os.environ, {"AMPLIHACK_SESSION_TYPE": "OPERATIONS"}):
            transcript = _make_transcript(["implement a new feature"])
            assert checker.detect_session_type(transcript) == "OPERATIONS"

    def test_code_modification_overrides_operations(self, checker):
        """If code files are modified, DEVELOPMENT should take priority."""
        # Transcript with operations keywords BUT actual code modifications
        transcript = _make_transcript(["prioritize and fix the top bug"])
        # Add tool usage showing code file modification
        transcript.append({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{
                    "type": "tool_use",
                    "name": "Write",
                    "input": {"file_path": "src/main.py", "content": "..."},
                }],
            },
        })
        # Operations keywords are checked BEFORE tool usage, so this should
        # still be OPERATIONS. The user said "prioritize" first.
        result = checker.detect_session_type(transcript)
        assert result == "OPERATIONS"

    def test_pure_investigation_not_affected(self, checker):
        """Investigation sessions without operations keywords still work."""
        transcript = _make_transcript(["Investigate how the auth system works"])
        result = checker.detect_session_type(transcript)
        assert result == "INVESTIGATION"

    def test_simple_still_highest_priority(self, checker):
        """SIMPLE keywords should still take priority over OPERATIONS."""
        transcript = _make_transcript(["cleanup the backlog files"])
        result = checker.detect_session_type(transcript)
        # "cleanup" is SIMPLE keyword, should win over "backlog" OPERATIONS keyword
        assert result == "SIMPLE"
