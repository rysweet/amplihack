"""Data formatting utilities for PR analysis."""

from typing import Any


def format_comments(comments: list[dict[str, Any]]) -> str:
    """Format PR comments for analysis.

    Args:
        comments: List of comment dictionaries

    Returns:
        Formatted comments string
    """
    if not comments:
        return "(No comments)"

    lines = []
    for i, comment in enumerate(comments[:10], 1):  # Limit to 10
        author = comment.get("author", {}).get("login", "unknown")
        body = comment.get("body", "")[:200]  # Truncate long comments
        lines.append(f"{i}. @{author}: {body}")

    if len(comments) > 10:
        lines.append(f"... and {len(comments) - 10} more")

    return "\n".join(lines)


def format_reviews(reviews: list[dict[str, Any]]) -> str:
    """Format PR reviews for analysis.

    Args:
        reviews: List of review dictionaries

    Returns:
        Formatted reviews string
    """
    if not reviews:
        return "(No reviews)"

    lines = []
    for i, review in enumerate(reviews, 1):
        author = review.get("author", {}).get("login", "unknown")
        state = review.get("state", "UNKNOWN")
        body = review.get("body", "")[:200]
        lines.append(f"{i}. @{author} ({state}): {body}")

    return "\n".join(lines)


def format_files(files: list[dict[str, Any]]) -> str:
    """Format file list for analysis.

    Args:
        files: List of file dictionaries

    Returns:
        Formatted file list string
    """
    if not files:
        return "(No files)"

    lines = []
    for file_data in files[:50]:  # Limit to 50 files
        path = file_data.get("path", "unknown")
        additions = file_data.get("additions", 0)
        deletions = file_data.get("deletions", 0)
        lines.append(f"- {path} (+{additions}/-{deletions})")

    if len(files) > 50:
        lines.append(f"... and {len(files) - 50} more")

    return "\n".join(lines)
