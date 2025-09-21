#!/usr/bin/env python3
"""
Tests for ReviewerAgent PR comment functionality.
"""

import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import MagicMock, patch

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestReviewerPRComments(TestCase):
    """Tests for ReviewerAgent PR comments."""

    def setUp(self):
        """Set up test environment."""
        self.test_pr_number = 123
        self.test_repo = "owner/repo"

    def test_initialization(self):
        """Test ReviewerAgent initialization."""
        from reviewer_agent import ReviewerAgent

        # Valid initialization
        agent = ReviewerAgent(pr_number=123, repo="owner/repo")
        self.assertEqual(agent.pr_number, 123)
        self.assertEqual(agent.repo, "owner/repo")

        # Invalid PR number
        with self.assertRaises(ValueError):
            ReviewerAgent(pr_number=0, repo="owner/repo")

        # Invalid repo format
        with self.assertRaises(ValueError):
            ReviewerAgent(pr_number=123, repo="invalid")

    @patch("subprocess.run")
    def test_post_review_comment(self, mock_subprocess):
        """Test posting a review comment."""
        from reviewer_agent import ReviewerAgent

        mock_subprocess.return_value = MagicMock(returncode=0)

        agent = ReviewerAgent(pr_number=123, repo="owner/repo")
        result = agent.post_review_comment("Test review")

        # Verify correct command was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]

        self.assertEqual(call_args[:3], ["gh", "pr", "comment"])
        self.assertEqual(call_args[3], "123")
        self.assertIn("--body", call_args)
        self.assertIn("Test review", call_args)
        self.assertTrue(result)

    @patch("subprocess.run")
    def test_command_failure(self, mock_subprocess):
        """Test handling of command failure."""
        from reviewer_agent import ReviewerAgent

        mock_subprocess.return_value = MagicMock(returncode=1, stderr="Error: PR not found")

        agent = ReviewerAgent(pr_number=123, repo="owner/repo")

        with self.assertRaises(Exception) as context:
            agent.post_review_comment("Test")

        self.assertIn("Failed to post review", str(context.exception))

    def test_input_validation(self):
        """Test input validation."""
        from reviewer_agent import ReviewerAgent

        agent = ReviewerAgent(pr_number=123, repo="owner/repo")

        # Empty content
        with self.assertRaises(ValueError):
            agent.post_review_comment("")

        # Non-string content
        with self.assertRaises(TypeError):
            agent.post_review_comment(123)  # type: ignore

        # Null byte rejection
        with self.assertRaises(ValueError):
            agent.post_review_comment("test\x00content")

    @patch("subprocess.run")
    def test_timeout_handling(self, mock_subprocess):
        """Test timeout handling."""
        import subprocess

        from reviewer_agent import ReviewerAgent

        mock_subprocess.side_effect = subprocess.TimeoutExpired("gh", 30)

        agent = ReviewerAgent(pr_number=123, repo="owner/repo")

        with self.assertRaises(Exception) as context:
            agent.post_review_comment("Test")

        self.assertIn("timed out", str(context.exception))


if __name__ == "__main__":
    main()
