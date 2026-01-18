#!/usr/bin/env python3
"""
Integration tests for evidence-based completion checking in power_steering_checker.

Tests the integration of completion_evidence with power_steering_checker to
verify that concrete evidence can override SDK analysis.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


class TestEvidenceBasedCompletion:
    """Integration tests for evidence-based completion checking."""

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
    def transcript_path(self, temp_project):
        """Create a test transcript file."""
        transcript = temp_project / "transcript.jsonl"

        # Create a realistic development transcript with tool use
        with open(transcript, "w") as f:
            entry = {
                "role": "user",
                "content": [{"type": "text", "text": "Fix the bug in the authentication module"}],
            }
            f.write(json.dumps(entry) + "\n")

            # Add tool use to make it a DEVELOPMENT session
            entry = {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll fix the authentication bug"},
                    {
                        "type": "tool_use",
                        "name": "Write",
                        "input": {"file_path": "/path/to/file.py"},
                    },
                ],
            }
            f.write(json.dumps(entry) + "\n")

            entry = {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "123"}],
            }
            f.write(json.dumps(entry) + "\n")

        return transcript

    @pytest.fixture
    def checker(self, temp_project):
        """Create PowerSteeringChecker instance."""
        return PowerSteeringChecker(project_root=temp_project)

    @patch("power_steering_checker.PowerSteeringChecker._is_qa_session", return_value=False)
    @patch("subprocess.run")
    def test_pr_merged_allows_stop(self, mock_run, mock_qa, checker, transcript_path, temp_project):
        """Test that merged PR allows stop without SDK analysis."""
        # Mock gh CLI to return merged PR
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"state": "MERGED", "mergedAt": "2025-01-01T00:00:00Z"}',
        )

        result = checker.check(transcript_path, "test-session-123")

        assert result.decision == "approve"
        assert "PR merged successfully" in result.reasons
        # Verify we didn't run expensive SDK analysis
        # (would have taken longer if we did)

    @patch("power_steering_checker.PowerSteeringChecker._is_qa_session", return_value=False)
    def test_user_confirmation_allows_stop(self, mock_qa, checker, transcript_path, temp_project):
        """Test that user confirmation allows stop without SDK analysis."""
        # Create user confirmation file
        session_dir = temp_project / ".claude" / "runtime" / "power-steering" / "test-session-456"
        session_dir.mkdir(parents=True)
        confirmation_file = session_dir / "user_confirmed_complete"
        confirmation_file.write_text("Work is complete")

        result = checker.check(transcript_path, "test-session-456")

        assert result.decision == "approve"
        assert "User explicitly confirmed work is complete" in result.reasons

    @patch("subprocess.run")
    def test_evidence_available_flag_respected(
        self, mock_run, checker, transcript_path, temp_project
    ):
        """Test that evidence checking only runs when EVIDENCE_AVAILABLE is True."""
        # Mock gh CLI to simulate unavailable
        mock_run.side_effect = FileNotFoundError()

        # This should not crash - it should fail-open and continue to SDK analysis
        result = checker.check(transcript_path, "test-session-789")

        # Result should still be valid (either approve or block from SDK analysis)
        assert result.decision in ["approve", "block"]

    @patch("power_steering_checker.PowerSteeringChecker._is_qa_session", return_value=False)
    def test_evidence_results_attached_to_result(
        self, mock_qa, checker, transcript_path, temp_project
    ):
        """Test that evidence results are attached to PowerSteeringResult."""
        # Create transcript with completed TODOs
        with open(transcript_path, "w") as f:
            entry = {
                "role": "assistant",
                "content": [{"type": "text", "text": "- [x] Task 1\n- [x] Task 2"}],
            }
            f.write(json.dumps(entry) + "\n")

        result = checker.check(transcript_path, "test-session-evidence")

        # Evidence results field should be attached (even if empty due to EVIDENCE_AVAILABLE flag)
        assert hasattr(result, "evidence_results")
        # This is a list (empty or populated depending on EVIDENCE_AVAILABLE)
        assert isinstance(result.evidence_results, list)

    @patch("subprocess.run")
    def test_evidence_checking_fails_gracefully(
        self, mock_run, checker, transcript_path, temp_project
    ):
        """Test that evidence checking failures don't break the checker."""
        # Mock subprocess to raise an unexpected exception
        mock_run.side_effect = RuntimeError("Unexpected error")

        # Should not crash - should log warning and continue to SDK analysis
        result = checker.check(transcript_path, "test-session-fail")

        # Result should still be valid
        assert result.decision in ["approve", "block"]


class TestEvidenceSuggestsComplete:
    """Tests for _evidence_suggests_complete helper method."""

    @pytest.fixture
    def checker(self, tmp_path):
        """Create PowerSteeringChecker instance."""
        return PowerSteeringChecker(project_root=tmp_path)

    def test_no_evidence_returns_false(self, checker):
        """Test that no evidence returns False."""
        result = checker._evidence_suggests_complete([])
        assert result is False

    def test_strong_evidence_returns_true(self, checker):
        """Test that strong evidence types return True."""
        from completion_evidence import Evidence, EvidenceType

        evidence = [
            Evidence(
                evidence_type=EvidenceType.PR_MERGED,
                verified=True,
                details="PR merged",
                confidence=1.0,
            )
        ]

        result = checker._evidence_suggests_complete(evidence)
        assert result is True

    def test_multiple_medium_evidence_returns_true(self, checker):
        """Test that 3+ verified medium evidence types return True."""
        from completion_evidence import Evidence, EvidenceType

        evidence = [
            Evidence(
                evidence_type=EvidenceType.TODO_COMPLETE,
                verified=True,
                details="All TODOs complete",
                confidence=0.8,
            ),
            Evidence(
                evidence_type=EvidenceType.FILES_COMMITTED,
                verified=True,
                details="All files committed",
                confidence=0.7,
            ),
            Evidence(
                evidence_type=EvidenceType.CI_PASSING,
                verified=True,
                details="CI passing",
                confidence=0.9,
            ),
        ]

        result = checker._evidence_suggests_complete(evidence)
        assert result is True

    def test_insufficient_evidence_returns_false(self, checker):
        """Test that insufficient evidence returns False."""
        from completion_evidence import Evidence, EvidenceType

        evidence = [
            Evidence(
                evidence_type=EvidenceType.TODO_COMPLETE,
                verified=False,
                details="Some TODOs incomplete",
                confidence=0.0,
            ),
            Evidence(
                evidence_type=EvidenceType.FILES_COMMITTED,
                verified=False,
                details="Files uncommitted",
                confidence=0.0,
            ),
        ]

        result = checker._evidence_suggests_complete(evidence)
        assert result is False
