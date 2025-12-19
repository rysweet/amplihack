"""GitHub API client for PR data fetching."""

import json
import subprocess
from typing import Any


def get_pr_data(pr_number: int) -> dict[str, Any]:
    """Fetch PR data using gh CLI.

    Args:
        pr_number: GitHub PR number

    Returns:
        PR data dictionary with title, body, files, comments, etc.
    """
    # Fetch PR details
    pr_json = subprocess.check_output(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "title,body,headRefName,baseRefName,author,files,comments,reviews",
        ],
        text=True,
    )
    pr_data = json.loads(pr_json)

    # Fetch diff
    diff = subprocess.check_output(["gh", "pr", "diff", str(pr_number)], text=True)
    pr_data["diff"] = diff

    return pr_data


def apply_labels(pr_number: int, label_names: list[str]) -> None:
    """Apply labels to PR.

    Args:
        pr_number: GitHub PR number
        label_names: List of label names to apply
    """
    for label in label_names:
        try:
            subprocess.run(
                ["gh", "pr", "edit", str(pr_number), "--add-label", label],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            # Label might already exist or other non-critical error
            pass


def return_to_draft(pr_number: int) -> None:
    """Convert PR back to draft status.

    Args:
        pr_number: GitHub PR number
    """
    subprocess.run(
        ["gh", "pr", "ready", str(pr_number), "--undo"],
        check=True,
        capture_output=True,
    )


def post_comment(pr_number: int, comment_file: str) -> None:
    """Post comment to PR from file.

    Args:
        pr_number: GitHub PR number
        comment_file: Path to file containing comment markdown
    """
    subprocess.run(
        [
            "gh",
            "pr",
            "comment",
            str(pr_number),
            "--body-file",
            comment_file,
        ],
        check=True,
        capture_output=True,
    )
