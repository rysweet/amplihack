#!/usr/bin/env python3
"""
Tests for completion_evidence.py - Concrete completion verification.

Tests evidence-based checking for PR status, user confirmation, TODO completion,
CI status, and git commit status.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from completion_evidence import (
    CompletionEvidenceChecker,
    Evidence,
    EvidenceType,
)


class TestCompletionEvidenceChecker:
    """Tests for CompletionEvidenceChecker class."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temporary project directory."""
        return tmp_path

    @pytest.fixture
    def checker(self, temp_project):
        """Create checker instance."""
        return CompletionEvidenceChecker(temp_project)

    def test_initialization(self, temp_project):
        """Test checker initialization."""
        checker = CompletionEvidenceChecker(temp_project)
        assert checker.project_root == temp_project

    @patch("subprocess.run")
    def test_check_pr_status_merged(self, mock_run, checker):
        """Test PR status check when PR is merged."""
        # Mock gh CLI response for merged PR
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"state": "MERGED", "mergedAt": "2025-01-01T00:00:00Z"}',
        )

        evidence = checker.check_pr_status()

        assert evidence is not None
        assert evidence.evidence_type == EvidenceType.PR_MERGED
        assert evidence.verified is True
        assert evidence.confidence == 1.0
        assert "2025-01-01T00:00:00Z" in evidence.details

    @patch("subprocess.run")
    def test_check_pr_status_open(self, mock_run, checker):
        """Test PR status check when PR is still open."""
        # Mock gh CLI response for open PR
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"state": "OPEN", "mergedAt": null}',
        )

        evidence = checker.check_pr_status()

        assert evidence is not None
        assert evidence.evidence_type == EvidenceType.PR_MERGED
        assert evidence.verified is False
        assert evidence.confidence == 0.0

    @patch("subprocess.run")
    def test_check_pr_status_no_pr(self, mock_run, checker):
        """Test PR status check when no PR exists."""
        # Mock gh CLI error (no PR found)
        mock_run.return_value = MagicMock(returncode=1)

        evidence = checker.check_pr_status()

        assert evidence is None

    @patch("subprocess.run")
    def test_check_pr_status_gh_unavailable(self, mock_run, checker):
        """Test PR status check when gh CLI is unavailable."""
        # Mock FileNotFoundError (gh CLI not installed)
        mock_run.side_effect = FileNotFoundError()

        evidence = checker.check_pr_status()

        assert evidence is None

    def test_check_user_confirmation_exists(self, temp_project, checker):
        """Test user confirmation check when confirmation file exists."""
        session_dir = temp_project / "session"
        session_dir.mkdir()
        confirmation_file = session_dir / "user_confirmed_complete"
        confirmation_file.write_text("Work is complete")

        evidence = checker.check_user_confirmation(session_dir)

        assert evidence is not None
        assert evidence.evidence_type == EvidenceType.USER_CONFIRMATION
        assert evidence.verified is True
        assert evidence.confidence == 1.0
        assert "Work is complete" in evidence.details

    def test_check_user_confirmation_missing(self, temp_project, checker):
        """Test user confirmation check when no confirmation exists."""
        session_dir = temp_project / "session"
        session_dir.mkdir()

        evidence = checker.check_user_confirmation(session_dir)

        assert evidence is None

    def test_check_todo_completion_all_complete(self, temp_project, checker):
        """Test TODO completion check when all TODOs are complete."""
        transcript_path = temp_project / "transcript.jsonl"

        # Create transcript with completed TODOs
        with open(transcript_path, "w") as f:
            entry = {
                "role": "assistant",
                "content": [{"type": "text", "text": "- [x] Task 1\n- [x] Task 2"}],
            }
            f.write(json.dumps(entry) + "\n")

        evidence = checker.check_todo_completion(transcript_path)

        assert evidence.evidence_type == EvidenceType.TODO_COMPLETE
        assert evidence.verified is True
        assert evidence.confidence == 0.8
        assert "2 TODO items complete" in evidence.details

    def test_check_todo_completion_incomplete(self, temp_project, checker):
        """Test TODO completion check when some TODOs are incomplete."""
        transcript_path = temp_project / "transcript.jsonl"

        # Create transcript with incomplete TODOs
        with open(transcript_path, "w") as f:
            entry = {
                "role": "assistant",
                "content": [{"type": "text", "text": "- [x] Task 1\n- [ ] Task 2"}],
            }
            f.write(json.dumps(entry) + "\n")

        evidence = checker.check_todo_completion(transcript_path)

        assert evidence.evidence_type == EvidenceType.TODO_COMPLETE
        assert evidence.verified is False
        assert evidence.confidence == 0.0
        assert "1/2 TODO items complete" in evidence.details

    def test_check_todo_completion_no_todos(self, temp_project, checker):
        """Test TODO completion check when no TODOs exist."""
        transcript_path = temp_project / "transcript.jsonl"

        # Create transcript without TODOs
        with open(transcript_path, "w") as f:
            entry = {
                "role": "assistant",
                "content": [{"type": "text", "text": "Some text without TODOs"}],
            }
            f.write(json.dumps(entry) + "\n")

        evidence = checker.check_todo_completion(transcript_path)

        assert evidence.evidence_type == EvidenceType.TODO_COMPLETE
        assert evidence.verified is False
        assert evidence.confidence == 0.0
        assert "No TODO items found" in evidence.details

    @patch("subprocess.run")
    def test_check_ci_status_all_passing(self, mock_run, checker):
        """Test CI status check when all checks pass."""
        # Mock gh CLI response with passing checks
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"statusCheckRollup": [{"conclusion": "SUCCESS"}, {"conclusion": "SUCCESS"}]}',
        )

        evidence = checker.check_ci_status()

        assert evidence is not None
        assert evidence.evidence_type == EvidenceType.CI_PASSING
        assert evidence.verified is True
        assert evidence.confidence == 0.9
        assert "2 CI checks passed" in evidence.details

    @patch("subprocess.run")
    def test_check_ci_status_some_failing(self, mock_run, checker):
        """Test CI status check when some checks fail."""
        # Mock gh CLI response with mixed checks
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"statusCheckRollup": [{"conclusion": "SUCCESS"}, {"conclusion": "FAILURE"}]}',
        )

        evidence = checker.check_ci_status()

        assert evidence is not None
        assert evidence.evidence_type == EvidenceType.CI_PASSING
        assert evidence.verified is False
        assert evidence.confidence == 0.0
        assert "1/2 CI checks passed" in evidence.details

    @patch("subprocess.run")
    def test_check_ci_status_no_checks(self, mock_run, checker):
        """Test CI status check when no checks exist."""
        # Mock gh CLI response with no checks
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"statusCheckRollup": []}',
        )

        evidence = checker.check_ci_status()

        assert evidence is None

    @patch("subprocess.run")
    def test_check_files_committed_clean(self, mock_run, checker):
        """Test files committed check when working directory is clean."""
        # Mock git status with clean working directory
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        evidence = checker.check_files_committed()

        assert evidence is not None
        assert evidence.evidence_type == EvidenceType.FILES_COMMITTED
        assert evidence.verified is True
        assert evidence.confidence == 0.7

    @patch("subprocess.run")
    def test_check_files_committed_uncommitted(self, mock_run, checker):
        """Test files committed check when files are uncommitted."""
        # Mock git status with uncommitted files
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=" M file1.py\n M file2.py\n",
        )

        evidence = checker.check_files_committed()

        assert evidence is not None
        assert evidence.evidence_type == EvidenceType.FILES_COMMITTED
        assert evidence.verified is False
        assert evidence.confidence == 0.0
        assert "2 files" in evidence.details

    @patch("subprocess.run")
    def test_check_files_committed_git_unavailable(self, mock_run, checker):
        """Test files committed check when git is unavailable."""
        # Mock FileNotFoundError (git not installed)
        mock_run.side_effect = FileNotFoundError()

        evidence = checker.check_files_committed()

        assert evidence is None


class TestEvidenceType:
    """Tests for EvidenceType enum."""

    def test_evidence_types_exist(self):
        """Test that all evidence types are defined."""
        assert EvidenceType.PR_MERGED
        assert EvidenceType.USER_CONFIRMATION
        assert EvidenceType.CI_PASSING
        assert EvidenceType.TODO_COMPLETE
        assert EvidenceType.FILES_COMMITTED


class TestEvidence:
    """Tests for Evidence dataclass."""

    def test_evidence_creation(self):
        """Test creating Evidence object."""
        evidence = Evidence(
            evidence_type=EvidenceType.PR_MERGED,
            verified=True,
            details="PR merged",
            confidence=1.0,
        )

        assert evidence.evidence_type == EvidenceType.PR_MERGED
        assert evidence.verified is True
        assert evidence.details == "PR merged"
        assert evidence.confidence == 1.0
