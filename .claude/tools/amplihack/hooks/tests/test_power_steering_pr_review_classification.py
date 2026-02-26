#!/usr/bin/env python3
"""
Tests for power-steering classification of PR review/merge sessions.

Verifies that PR review and merge operations are classified as SIMPLE,
not DEVELOPMENT. Fixes issue #2563.
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


class TestPRReviewClassification:
    """Tests for PR review/merge session classification (issue #2563)."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temporary project directory."""
        project = tmp_path / "project"
        project.mkdir()

        claude_dir = project / ".claude"
        claude_dir.mkdir()

        tools_dir = claude_dir / "tools" / "amplihack"
        tools_dir.mkdir(parents=True)

        runtime_dir = claude_dir / "runtime" / "power-steering"
        runtime_dir.mkdir(parents=True)

        return project

    @pytest.fixture
    def checker(self, temp_project):
        """Create PowerSteeringChecker instance."""
        return PowerSteeringChecker(project_root=temp_project)

    def _make_transcript(self, user_message, tool_commands=None):
        """Build a transcript with a user message and optional Bash tool calls."""
        transcript = [
            {
                "type": "user",
                "message": {"content": user_message},
            }
        ]

        if tool_commands:
            content_blocks = []
            for cmd in tool_commands:
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": cmd},
                    }
                )
            transcript.append(
                {
                    "type": "assistant",
                    "message": {"content": content_blocks},
                }
            )

        return transcript

    def test_review_and_merge_pr_is_simple(self, checker):
        """PR review+merge request should be SIMPLE, not DEVELOPMENT."""
        transcript = self._make_transcript("review PR 2533 and merge it if it looks good")
        session_type = checker.detect_session_type(transcript)
        assert session_type == "SIMPLE", f"PR review+merge should be SIMPLE, got {session_type}"

    def test_merge_pr_keyword_is_simple(self, checker):
        """'merge pr' keyword should trigger SIMPLE classification."""
        transcript = self._make_transcript("merge pr 123")
        session_type = checker.detect_session_type(transcript)
        assert session_type == "SIMPLE", f"'merge pr' should be SIMPLE, got {session_type}"

    def test_review_pr_keyword_is_simple(self, checker):
        """'review pr' keyword should trigger SIMPLE classification."""
        transcript = self._make_transcript("review pr 456")
        session_type = checker.detect_session_type(transcript)
        assert session_type == "SIMPLE", f"'review pr' should be SIMPLE, got {session_type}"

    def test_review_and_merge_keyword_is_simple(self, checker):
        """'review and merge' keyword should trigger SIMPLE classification."""
        transcript = self._make_transcript("review and merge the latest PR")
        session_type = checker.detect_session_type(transcript)
        assert session_type == "SIMPLE", f"'review and merge' should be SIMPLE, got {session_type}"

    def test_gh_pr_merge_does_not_trigger_development(self, checker):
        """gh pr merge commands should NOT classify session as DEVELOPMENT."""
        transcript = self._make_transcript(
            "merge that PR",
            tool_commands=[
                "gh pr view 2533 --json title,body,state",
                "gh pr checks 2533",
                "gh pr merge 2533 --squash",
            ],
        )
        session_type = checker.detect_session_type(transcript)
        assert session_type != "DEVELOPMENT", (
            f"gh pr merge/view/checks should NOT be DEVELOPMENT, got {session_type}"
        )

    def test_gh_pr_view_does_not_trigger_development(self, checker):
        """gh pr view commands should NOT classify session as DEVELOPMENT."""
        transcript = self._make_transcript(
            "check the status of PR 100",
            tool_commands=["gh pr view 100 --json state,statusCheckRollup"],
        )
        session_type = checker.detect_session_type(transcript)
        assert session_type != "DEVELOPMENT", (
            f"gh pr view should NOT be DEVELOPMENT, got {session_type}"
        )

    def test_gh_pr_create_still_triggers_development(self, checker):
        """gh pr create commands SHOULD classify session as DEVELOPMENT."""
        transcript = self._make_transcript(
            "create a PR for this feature",
            tool_commands=[
                'gh pr create --title "Add feature" --body "Details"',
            ],
        )
        session_type = checker.detect_session_type(transcript)
        assert session_type == "DEVELOPMENT", (
            f"gh pr create SHOULD be DEVELOPMENT, got {session_type}"
        )

    def test_gh_pr_edit_still_triggers_development(self, checker):
        """gh pr edit commands SHOULD classify session as DEVELOPMENT."""
        transcript = self._make_transcript(
            "update the PR description",
            tool_commands=[
                'gh pr edit 100 --title "Updated title"',
            ],
        )
        session_type = checker.detect_session_type(transcript)
        assert session_type == "DEVELOPMENT", (
            f"gh pr edit SHOULD be DEVELOPMENT, got {session_type}"
        )

    def test_simple_session_skips_all_checks(self, checker):
        """SIMPLE sessions should have zero applicable considerations."""
        applicable = checker.get_applicable_considerations("SIMPLE")
        assert len(applicable) == 0, (
            f"SIMPLE sessions should skip all checks, got {len(applicable)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
