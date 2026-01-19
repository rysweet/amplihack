"""Tests for formatting utilities."""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir.parent))

from pr_triage.formatters import format_comments, format_files, format_reviews


def test_format_comments_empty():
    """Test formatting with no comments."""
    result = format_comments([])
    assert result == "(No comments)"


def test_format_comments_single():
    """Test formatting with single comment."""
    comments = [
        {
            "author": {"login": "testuser"},
            "body": "Test comment",
        }
    ]
    result = format_comments(comments)
    assert "1. @testuser: Test comment" in result


def test_format_comments_multiple():
    """Test formatting with multiple comments."""
    comments = [
        {"author": {"login": "user1"}, "body": "Comment 1"},
        {"author": {"login": "user2"}, "body": "Comment 2"},
    ]
    result = format_comments(comments)
    assert "1. @user1: Comment 1" in result
    assert "2. @user2: Comment 2" in result


def test_format_comments_truncates_long():
    """Test that long comments are truncated."""
    long_body = "x" * 300
    comments = [{"author": {"login": "user"}, "body": long_body}]
    result = format_comments(comments)
    # Should truncate to 200 chars
    assert len(result.split(": ", 1)[1]) <= 200


def test_format_comments_limits_count():
    """Test that comment count is limited to 10."""
    comments = [{"author": {"login": f"user{i}"}, "body": f"Comment {i}"} for i in range(15)]
    result = format_comments(comments)
    assert "... and 5 more" in result


def test_format_reviews_empty():
    """Test formatting with no reviews."""
    result = format_reviews([])
    assert result == "(No reviews)"


def test_format_reviews_single():
    """Test formatting with single review."""
    reviews = [
        {
            "author": {"login": "reviewer"},
            "state": "APPROVED",
            "body": "LGTM",
        }
    ]
    result = format_reviews(reviews)
    assert "1. @reviewer (APPROVED): LGTM" in result


def test_format_reviews_multiple_states():
    """Test formatting with different review states."""
    reviews = [
        {"author": {"login": "user1"}, "state": "APPROVED", "body": "Good"},
        {"author": {"login": "user2"}, "state": "CHANGES_REQUESTED", "body": "Fix this"},
    ]
    result = format_reviews(reviews)
    assert "APPROVED" in result
    assert "CHANGES_REQUESTED" in result


def test_format_files_empty():
    """Test formatting with no files."""
    result = format_files([])
    assert result == "(No files)"


def test_format_files_single():
    """Test formatting with single file."""
    files = [
        {
            "path": "test.py",
            "additions": 10,
            "deletions": 5,
        }
    ]
    result = format_files(files)
    assert "- test.py (+10/-5)" in result


def test_format_files_multiple():
    """Test formatting with multiple files."""
    files = [
        {"path": "file1.py", "additions": 10, "deletions": 5},
        {"path": "file2.py", "additions": 20, "deletions": 3},
    ]
    result = format_files(files)
    assert "- file1.py (+10/-5)" in result
    assert "- file2.py (+20/-3)" in result


def test_format_files_limits_count():
    """Test that file count is limited to 50."""
    files = [{"path": f"file{i}.py", "additions": 1, "deletions": 0} for i in range(60)]
    result = format_files(files)
    assert "... and 10 more" in result


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
