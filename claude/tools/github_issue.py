#!/usr/bin/env python3
"""
GitHub Issue Creation Tool

A simple wrapper around GitHub CLI (gh) for creating issues programmatically.
Provides validation, error handling, and structured output.
"""

import re
import shutil
import subprocess
from typing import Any


class GitHubIssueCreator:
    """Create GitHub issues using the GitHub CLI."""

    def __init__(self):
        """Initialize and validate GitHub CLI is available."""
        self._validate_gh_cli()

    def _validate_gh_cli(self) -> None:
        """Check that gh CLI is installed and authenticated."""
        if not shutil.which("gh"):
            raise RuntimeError(
                "GitHub CLI (gh) is not installed. Install from: https://cli.github.com/"
            )

        # Check authentication status
        try:
            result = subprocess.run(
                ["gh", "auth", "status"], capture_output=True, text=True, check=False
            )
            if result.returncode != 0:
                raise RuntimeError("GitHub CLI is not authenticated. Run: gh auth login")
        except subprocess.SubprocessError as e:
            raise RuntimeError(f"Failed to check GitHub CLI status: {e}")

    def create_issue(
        self,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        milestone: str | None = None,
        project: str | None = None,
        repo: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a GitHub issue.

        Args:
            title: Issue title (required)
            body: Issue body/description
            labels: List of label names to apply
            assignees: List of GitHub usernames to assign
            milestone: Milestone name or number
            project: Project name or number
            repo: Repository in format "owner/repo" (uses current if not specified)

        Returns:
            Dict with keys:
                - success: bool
                - issue_url: str (if successful)
                - issue_number: int (if successful)
                - error: str (if failed)

        Example:
            >>> creator = GitHubIssueCreator()
            >>> result = creator.create_issue(
            ...     title="Fix authentication bug",
            ...     body="Users cannot log in with OAuth",
            ...     labels=["bug", "high-priority"]
            ... )
            >>> print(result['issue_url'])
        """
        # Validate required inputs
        if not title or not title.strip():
            return {"success": False, "error": "Title is required and cannot be empty"}

        # Build command
        cmd = ["gh", "issue", "create"]

        # Add title
        cmd.extend(["--title", title])

        # Add optional parameters
        if body:
            cmd.extend(["--body", body])

        if labels:
            for label in labels:
                cmd.extend(["--label", label])

        if assignees:
            for assignee in assignees:
                cmd.extend(["--assignee", assignee])

        if milestone:
            cmd.extend(["--milestone", milestone])

        if project:
            cmd.extend(["--project", project])

        if repo:
            cmd.extend(["--repo", repo])

        # Execute command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to create issue: {result.stderr.strip()}",
                }

            # Parse output to extract URL and issue number
            output = result.stdout.strip()
            if not output:
                return {"success": False, "error": "No output from gh command"}

            # gh issue create returns the URL directly
            issue_url = output

            # Extract issue number from URL
            # Format: https://github.com/owner/repo/issues/123
            match = re.search(r"/issues/(\d+)$", issue_url)
            if not match:
                return {
                    "success": False,
                    "error": f"Could not parse issue number from URL: {issue_url}",
                }

            issue_number = int(match.group(1))

            return {"success": True, "issue_url": issue_url, "issue_number": issue_number}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out after 30 seconds"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {e!s}"}


def create_issue(
    title: str,
    body: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
    milestone: str | None = None,
    project: str | None = None,
    repo: str | None = None,
) -> dict[str, Any]:
    """
    Convenience function to create a GitHub issue.

    This is the main entry point for using this module.

    Args:
        title: Issue title (required)
        body: Issue body/description
        labels: List of label names to apply
        assignees: List of GitHub usernames to assign
        milestone: Milestone name or number
        project: Project name or number
        repo: Repository in format "owner/repo" (uses current if not specified)

    Returns:
        Dict with success status and issue details or error message

    Example:
        >>> from github_issue import create_issue
        >>> result = create_issue(
        ...     title="Add unit tests for authentication",
        ...     body="We need comprehensive test coverage",
        ...     labels=["testing", "enhancement"]
        ... )
        >>> if result['success']:
        ...     print(f"Created issue #{result['issue_number']}")
    """
    try:
        creator = GitHubIssueCreator()
        return creator.create_issue(
            title=title,
            body=body,
            labels=labels,
            assignees=assignees,
            milestone=milestone,
            project=project,
            repo=repo,
        )
    except RuntimeError as e:
        return {"success": False, "error": str(e)}


def main():
    """Command-line interface for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Create a GitHub issue")
    parser.add_argument("title", help="Issue title")
    parser.add_argument("--body", help="Issue body/description")
    parser.add_argument(
        "--label", action="append", dest="labels", help="Add label (can be used multiple times)"
    )
    parser.add_argument(
        "--assignee",
        action="append",
        dest="assignees",
        help="Assign user (can be used multiple times)",
    )
    parser.add_argument("--milestone", help="Milestone name or number")
    parser.add_argument("--project", help="Project name or number")
    parser.add_argument("--repo", help="Repository (owner/repo format)")

    args = parser.parse_args()

    result = create_issue(
        title=args.title,
        body=args.body,
        labels=args.labels,
        assignees=args.assignees,
        milestone=args.milestone,
        project=args.project,
        repo=args.repo,
    )

    if result["success"]:
        print(f"✓ Created issue #{result['issue_number']}")
        print(f"  URL: {result['issue_url']}")
        return 0
    print(f"✗ Failed to create issue: {result['error']}")
    return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
