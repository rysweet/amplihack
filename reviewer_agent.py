#!/usr/bin/env python3
"""
ReviewerAgent - Posts code reviews as PR comments using gh CLI.
"""

import subprocess


class ReviewerAgent:
    """Posts code reviews to pull requests as comments."""

    def __init__(self, pr_number: int, repo: str):
        """Initialize with PR number and repository."""
        if not isinstance(pr_number, int) or pr_number <= 0:
            raise ValueError("PR number must be a positive integer")

        if not repo or "/" not in repo:
            raise ValueError("Repository must be in 'owner/repo' format")

        self.pr_number = pr_number
        self.repo = repo

    def post_review_comment(self, review_content: str) -> bool:
        """Post a review comment to the PR using gh CLI."""
        if not isinstance(review_content, str):
            raise TypeError("Review content must be a string")

        if not review_content.strip():
            raise ValueError("Review content cannot be empty")

        # Reject null bytes for security
        if "\x00" in review_content:
            raise ValueError("Invalid character in review content")

        # Build command
        cmd = [
            "gh",
            "pr",
            "comment",
            str(self.pr_number),
            "--body",
            review_content,
            "--repo",
            self.repo,
        ]

        # Execute with timeout
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                raise Exception(f"Failed to post review: {result.stderr}")

            return True

        except subprocess.TimeoutExpired:
            raise Exception("Command timed out after 30 seconds")
