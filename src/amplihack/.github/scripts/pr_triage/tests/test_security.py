"""Tests for security validation module."""

import pytest

from pr_triage import security


def test_validate_pr_number_valid():
    """Test valid PR numbers pass."""
    security.validate_pr_number(1)
    security.validate_pr_number(123)
    security.validate_pr_number(999999)


def test_validate_pr_number_invalid():
    """Test invalid PR numbers raise ValueError."""
    with pytest.raises(ValueError, match="must be integer"):
        security.validate_pr_number("123")

    with pytest.raises(ValueError, match="must be positive"):
        security.validate_pr_number(0)

    with pytest.raises(ValueError, match="must be positive"):
        security.validate_pr_number(-1)

    with pytest.raises(ValueError, match="too large"):
        security.validate_pr_number(1000000)


def test_sanitize_markdown_removes_scripts():
    """Test script tags are removed."""
    text = "Hello <script>alert('xss')</script> world"
    result = security.sanitize_markdown(text)
    assert "<script>" not in result
    assert "</script>" not in result


def test_sanitize_markdown_removes_event_handlers():
    """Test event handlers are removed."""
    text = '<div onclick="alert(1)">Click me</div>'
    result = security.sanitize_markdown(text)
    assert "onclick" not in result


def test_sanitize_markdown_limits_length():
    """Test long text is truncated."""
    long_text = "x" * 200000
    result = security.sanitize_markdown(long_text)
    assert len(result) <= 110000  # 100k + truncation message


def test_validate_label_name_valid():
    """Test valid label names pass."""
    security.validate_label_name("priority:high")
    security.validate_label_name("complexity:moderate")
    security.validate_label_name("status:in-progress")


def test_validate_label_name_invalid():
    """Test invalid label names raise ValueError."""
    with pytest.raises(ValueError, match="must be string"):
        security.validate_label_name(123)

    with pytest.raises(ValueError, match="cannot be empty"):
        security.validate_label_name("")

    with pytest.raises(ValueError, match="too long"):
        security.validate_label_name("x" * 101)

    with pytest.raises(ValueError, match="invalid characters"):
        security.validate_label_name("label with spaces")

    with pytest.raises(ValueError, match="invalid characters"):
        security.validate_label_name("label;drop table")


def test_validate_allowed_labels_valid():
    """Test allowed labels pass."""
    labels = ["priority:high", "complexity:moderate"]
    security.validate_allowed_labels(labels)


def test_validate_allowed_labels_invalid():
    """Test disallowed labels raise ValueError."""
    with pytest.raises(ValueError, match="not allowed"):
        security.validate_allowed_labels(["random:label"])

    with pytest.raises(ValueError, match="not allowed"):
        security.validate_allowed_labels(["malicious-label"])


def test_validate_pr_data_valid():
    """Test valid PR data passes."""
    pr_data = {
        "title": "Test PR",
        "body": "Description",
        "author": {"login": "testuser"},
        "files": [],
        "comments": [],
        "reviews": [],
    }
    security.validate_pr_data(pr_data)


def test_validate_pr_data_invalid():
    """Test invalid PR data raises ValueError."""
    with pytest.raises(ValueError, match="must be dict"):
        security.validate_pr_data("not a dict")

    with pytest.raises(ValueError, match="missing required field"):
        security.validate_pr_data({})

    with pytest.raises(ValueError, match="author data malformed"):
        security.validate_pr_data(
            {
                "title": "Test",
                "body": "Body",
                "author": "notadict",
                "files": [],
            }
        )


def test_validate_file_paths_valid():
    """Test valid file paths pass."""
    files = [
        {"path": "src/main.py"},
        {"path": "tests/test_main.py"},
        {"path": ".github/workflows/ci.yml"},
    ]
    security.validate_file_paths(files)


def test_validate_file_paths_invalid():
    """Test invalid file paths raise ValueError."""
    with pytest.raises(ValueError, match="Path traversal"):
        security.validate_file_paths([{"path": "../etc/passwd"}])

    with pytest.raises(ValueError, match="Absolute path"):
        security.validate_file_paths([{"path": "/etc/passwd"}])

    with pytest.raises(ValueError, match="Invalid characters"):
        security.validate_file_paths([{"path": "file;rm -rf /"}])


def test_is_safe_operation():
    """Test safe operation checking."""
    assert security.is_safe_operation("get_pr_data")
    assert security.is_safe_operation("apply_labels")
    assert security.is_safe_operation("post_comment")
    assert security.is_safe_operation("return_to_draft")

    assert not security.is_safe_operation("delete_repo")
    assert not security.is_safe_operation("force_merge")


def test_create_audit_log():
    """Test audit log creation."""
    log = security.create_audit_log(123, "test_op", "success", {"key": "value"})

    assert "PR-123" in log
    assert "test_op" in log
    assert "success" in log
    assert "{'key': 'value'}" in log
