#!/usr/bin/env python3
"""
Tests for power-steering handling of OPERATIONS (PM/planning) sessions.

Verifies that PM/planning sessions like /pm-architect are correctly classified
as OPERATIONS and do NOT trigger irrelevant development checks.

Covers Issue #2913: Power-steering stop hook incorrectly activates on Q&A/PM sessions.
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


# ---------------------------------------------------------------------------
# Helpers (matching existing test conventions)
# ---------------------------------------------------------------------------

def _user_msg(content: str) -> dict:
    """Create a user message dict for transcripts."""
    return {"type": "user", "message": {"content": content}}


def _assistant_text(text: str) -> dict:
    """Create an assistant text-only message (no tool use)."""
    return {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _assistant_read(file_path: str) -> dict:
    """Create an assistant message with a Read tool call."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Read",
                    "input": {"file_path": file_path},
                }
            ]
        },
    }


def _assistant_grep(pattern: str) -> dict:
    """Create an assistant message with a Grep tool call."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Grep",
                    "input": {"pattern": pattern},
                }
            ]
        },
    }


@pytest.fixture
def checker(tmp_path):
    """Create PowerSteeringChecker instance with temp project."""
    project = tmp_path / "project"
    project.mkdir()
    (project / ".claude" / "tools" / "amplihack").mkdir(parents=True)
    (project / ".claude" / "runtime" / "power-steering").mkdir(parents=True)
    return PowerSteeringChecker(project_root=project)


# ---------------------------------------------------------------------------
# OPERATIONS keyword detection tests
# ---------------------------------------------------------------------------

class TestOperationsSessionDetection:
    """Tests for OPERATIONS session type classification."""

    def test_pm_architect_keyword_detection(self, checker):
        """pm-architect keyword triggers OPERATIONS classification (fixes #2913)."""
        transcript = [
            _user_msg("Run /pm-architect to prioritize our backlog"),
            _assistant_read("/backlog.md"),
            _assistant_grep("open issues"),
            _assistant_text("Here are the top 5 priorities for this sprint..."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "OPERATIONS", (
            f"/pm-architect session should be OPERATIONS, got {session_type}"
        )

    def test_prioritize_keyword_triggers_operations(self, checker):
        """'prioritize' keyword triggers OPERATIONS classification."""
        transcript = [
            _user_msg("Please prioritize the open issues and tell me what to work on"),
            _assistant_read("/issues.md"),
            _assistant_grep("high priority"),
            _assistant_read("/roadmap.md"),
            _assistant_text("Based on the roadmap, I recommend working on issue #42 first."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "OPERATIONS", (
            f"prioritize-keyword session should be OPERATIONS, got {session_type}"
        )

    def test_backlog_keyword_triggers_operations(self, checker):
        """'backlog' keyword triggers OPERATIONS classification."""
        transcript = [
            _user_msg("Review our backlog and identify quick wins"),
            _assistant_read("/backlog.md"),
            _assistant_grep("bug"),
            _assistant_text("The backlog has 3 quick wins: issues #1, #5, #12."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "OPERATIONS", (
            f"backlog-keyword session should be OPERATIONS, got {session_type}"
        )

    def test_roadmap_keyword_triggers_operations(self, checker):
        """'roadmap' keyword triggers OPERATIONS classification."""
        transcript = [
            _user_msg("Analyze the roadmap and suggest what milestone to focus on next"),
            _assistant_read("/roadmap.md"),
            _assistant_text("The next milestone should be v2.0 based on current progress."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "OPERATIONS", (
            f"roadmap-keyword session should be OPERATIONS, got {session_type}"
        )

    def test_sprint_planning_triggers_operations(self, checker):
        """'sprint' keyword triggers OPERATIONS classification."""
        transcript = [
            _user_msg("Help me with sprint planning for next week"),
            _assistant_read("/issues.md"),
            _assistant_grep("milestone"),
            _assistant_text("For next sprint, I recommend including these 5 issues..."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "OPERATIONS", (
            f"sprint-keyword session should be OPERATIONS, got {session_type}"
        )

    def test_triage_keyword_triggers_operations(self, checker):
        """'triage' keyword triggers OPERATIONS classification."""
        transcript = [
            _user_msg("Triage the open GitHub issues and suggest labels"),
            _assistant_read("/issues.md"),
            _assistant_grep("label"),
            _assistant_text("After triage: 3 bugs, 2 features, 1 enhancement."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "OPERATIONS", (
            f"triage-keyword session should be OPERATIONS, got {session_type}"
        )

    def test_what_to_work_on_triggers_operations(self, checker):
        """'what should we work on' triggers OPERATIONS classification."""
        transcript = [
            _user_msg("What should we work on this week?"),
            _assistant_read("/backlog.md"),
            _assistant_grep("priority"),
            _assistant_text("Based on priorities, focus on the auth bug first."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "OPERATIONS", (
            f"'what to work on' session should be OPERATIONS, got {session_type}"
        )


# ---------------------------------------------------------------------------
# No false positive tests: OPERATIONS keyword + code changes = DEVELOPMENT
# ---------------------------------------------------------------------------

class TestOperationsDoesNotOverrideDevelopment:
    """Operations keywords do not override DEVELOPMENT tool signals."""

    def test_backlog_plus_code_edit_is_development(self, checker):
        """'backlog' keyword + code modification = DEVELOPMENT (code wins)."""
        transcript = [
            _user_msg("Review backlog and fix the top bug"),
            _assistant_read("/backlog.md"),
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {
                                "file_path": "/src/auth.py",
                                "old_string": "def login():",
                                "new_string": "def login(username: str):",
                            },
                        }
                    ]
                },
            },
            _assistant_text("Fixed the auth bug from the backlog."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "DEVELOPMENT", (
            f"backlog+code session should be DEVELOPMENT, got {session_type}"
        )

    def test_prioritize_plus_code_write_is_development(self, checker):
        """'prioritize' keyword + code write = DEVELOPMENT."""
        transcript = [
            _user_msg("Prioritize and then implement the top issue"),
            _assistant_read("/issues.md"),
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/src/feature.py"},
                        }
                    ]
                },
            },
            _assistant_text("Implemented the feature."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "DEVELOPMENT", (
            f"prioritize+code session should be DEVELOPMENT, got {session_type}"
        )


# ---------------------------------------------------------------------------
# Investigation keywords are not misidentified as OPERATIONS
# ---------------------------------------------------------------------------

class TestInvestigationNotMistakenForOperations:
    """Verify investigation sessions still get INVESTIGATION type."""

    def test_debug_session_is_investigation(self, checker):
        """'debug' keyword without code changes = INVESTIGATION, not OPERATIONS."""
        transcript = [
            _user_msg("Debug why the login endpoint is failing"),
            _assistant_read("/src/auth.py"),
            _assistant_grep("login"),
            _assistant_text("The issue is in the session handling at line 42."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "INVESTIGATION", (
            f"debug session should be INVESTIGATION, got {session_type}"
        )

    def test_investigate_keyword_is_investigation(self, checker):
        """'investigate' keyword = INVESTIGATION."""
        transcript = [
            _user_msg("Investigate why tests are failing in CI"),
            _assistant_read("/ci.yml"),
            _assistant_grep("pytest"),
            _assistant_text("CI fails because of missing PYTHONPATH env var."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "INVESTIGATION", (
            f"investigate session should be INVESTIGATION, got {session_type}"
        )


# ---------------------------------------------------------------------------
# Applicable considerations tests
# ---------------------------------------------------------------------------

class TestOperationsApplicableConsiderations:
    """OPERATIONS sessions should skip development-specific checks."""

    def test_operations_skips_workflow_invocation(self, checker):
        """OPERATIONS sessions do NOT include workflow_invocation check."""
        applicable = checker.get_applicable_considerations("OPERATIONS")
        ids = [c["id"] for c in applicable]
        assert "workflow_invocation" not in ids, (
            "OPERATIONS sessions should not check workflow_invocation"
        )

    def test_operations_skips_next_steps(self, checker):
        """OPERATIONS sessions do NOT include next_steps check."""
        applicable = checker.get_applicable_considerations("OPERATIONS")
        ids = [c["id"] for c in applicable]
        assert "next_steps" not in ids, (
            "OPERATIONS sessions should not check next_steps"
        )

    def test_operations_skips_documentation_updates(self, checker):
        """OPERATIONS sessions do NOT include documentation_updates check."""
        applicable = checker.get_applicable_considerations("OPERATIONS")
        ids = [c["id"] for c in applicable]
        assert "documentation_updates" not in ids, (
            "OPERATIONS sessions should not check documentation_updates"
        )

    def test_operations_skips_dev_workflow_complete(self, checker):
        """OPERATIONS sessions do NOT include dev_workflow_complete check."""
        applicable = checker.get_applicable_considerations("OPERATIONS")
        ids = [c["id"] for c in applicable]
        assert "dev_workflow_complete" not in ids, (
            "OPERATIONS sessions should not check dev_workflow_complete"
        )

    def test_operations_skips_local_testing(self, checker):
        """OPERATIONS sessions do NOT include local_testing check."""
        applicable = checker.get_applicable_considerations("OPERATIONS")
        ids = [c["id"] for c in applicable]
        assert "local_testing_complete" not in ids, (
            "OPERATIONS sessions should not check local_testing_complete"
        )

    def test_development_sessions_still_get_workflow_invocation(self, checker):
        """DEVELOPMENT sessions still get workflow_invocation check (regression guard)."""
        applicable = checker.get_applicable_considerations("DEVELOPMENT")
        ids = [c["id"] for c in applicable]
        assert "workflow_invocation" in ids, (
            "DEVELOPMENT sessions should still check workflow_invocation"
        )

    def test_investigation_sessions_still_get_workflow_invocation(self, checker):
        """INVESTIGATION sessions still get workflow_invocation check (regression guard)."""
        applicable = checker.get_applicable_considerations("INVESTIGATION")
        ids = [c["id"] for c in applicable]
        assert "workflow_invocation" in ids, (
            "INVESTIGATION sessions should still check workflow_invocation"
        )
