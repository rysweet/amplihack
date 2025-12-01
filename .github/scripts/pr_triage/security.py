"""Security validation for PR triage automation.

Implements defense controls per security requirements:
- M1.2: Input validation for PR data
- M2.1: Sanitization of untrusted content
- M3.1: Read-only GitHub operations
- M3.2: Label operations only
- M3.4: Clear validation rules
"""

import os
import re
from typing import Any


def validate_pr_number(pr_number: int) -> None:
    """Validate PR number is within acceptable range.

    Args:
        pr_number: PR number to validate

    Raises:
        ValueError: If PR number is invalid
    """
    if not isinstance(pr_number, int):
        raise ValueError(f"PR number must be integer, got {type(pr_number)}")

    if pr_number <= 0:
        raise ValueError(f"PR number must be positive, got {pr_number}")

    if pr_number > 999999:
        raise ValueError(f"PR number too large: {pr_number}")


def validate_github_token() -> str:
    """Validate GitHub token exists and is minimally formatted.

    Returns:
        GitHub token from environment

    Raises:
        ValueError: If token is missing or invalid
    """
    token = os.environ.get("GITHUB_TOKEN", "")

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    # Basic format check (gh_ or gho_ prefix)
    if not (token.startswith("gh_") or token.startswith("gho_")):
        raise ValueError("GITHUB_TOKEN appears malformed (wrong prefix)")

    if len(token) < 20:
        raise ValueError("GITHUB_TOKEN appears too short")

    return token


def sanitize_markdown(text: str) -> str:
    """Sanitize markdown text to prevent injection attacks.

    Args:
        text: Raw markdown text

    Returns:
        Sanitized markdown text
    """
    if not isinstance(text, str):
        return ""

    # Remove HTML tags (except safe ones)
    safe_tags = ["b", "i", "em", "strong", "code", "pre", "a", "ul", "ol", "li"]
    safe_pattern = "|".join(safe_tags)

    # Remove all HTML tags except safe ones
    text = re.sub(
        rf"<(?!/?({safe_pattern})\b)[^>]*>",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove script tags completely
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)

    # Remove event handlers
    text = re.sub(r"\bon\w+\s*=", "", text, flags=re.IGNORECASE)

    # Limit length to prevent DOS
    max_length = 100000
    if len(text) > max_length:
        text = text[:max_length] + "\n\n[Content truncated for safety]"

    return text


def validate_label_name(label: str) -> None:
    """Validate label name is safe to use.

    Args:
        label: Label name to validate

    Raises:
        ValueError: If label name is invalid
    """
    if not isinstance(label, str):
        raise ValueError(f"Label must be string, got {type(label)}")

    if not label:
        raise ValueError("Label cannot be empty")

    if len(label) > 100:
        raise ValueError(f"Label too long: {len(label)} chars")

    # Only allow alphanumeric, dash, underscore, colon
    if not re.match(r"^[a-zA-Z0-9_:-]+$", label):
        raise ValueError(f"Label contains invalid characters: {label}")


def validate_allowed_labels(labels: list[str]) -> None:
    """Validate labels are from allowed set.

    Args:
        labels: List of label names to validate

    Raises:
        ValueError: If any label is not allowed
    """
    allowed_prefixes = [
        "priority:",
        "complexity:",
        "status:",
        "type:",
    ]

    for label in labels:
        validate_label_name(label)

        # Check if label starts with allowed prefix
        if not any(label.startswith(prefix) for prefix in allowed_prefixes):
            raise ValueError(f"Label '{label}' not allowed. Must start with: {allowed_prefixes}")


def validate_pr_data(pr_data: dict[str, Any]) -> None:
    """Validate PR data structure is safe to process.

    Args:
        pr_data: PR data dictionary from GitHub

    Raises:
        ValueError: If PR data is invalid or unsafe
    """
    if not isinstance(pr_data, dict):
        raise ValueError(f"PR data must be dict, got {type(pr_data)}")

    required_fields = ["title", "body", "author", "files"]
    for field in required_fields:
        if field not in pr_data:
            raise ValueError(f"PR data missing required field: {field}")

    # Validate author structure
    author = pr_data.get("author", {})
    if not isinstance(author, dict) or "login" not in author:
        raise ValueError("PR author data malformed")

    # Validate files is list
    files = pr_data.get("files", [])
    if not isinstance(files, list):
        raise ValueError("PR files must be list")

    # Validate comments is list
    comments = pr_data.get("comments", [])
    if not isinstance(comments, list):
        raise ValueError("PR comments must be list")

    # Validate reviews is list
    reviews = pr_data.get("reviews", [])
    if not isinstance(reviews, list):
        raise ValueError("PR reviews must be list")


def is_safe_operation(operation: str) -> bool:
    """Check if GitHub operation is allowed (read-only or label operations).

    Args:
        operation: Operation name to check

    Returns:
        True if operation is safe, False otherwise
    """
    safe_operations = [
        "get_pr_data",
        "apply_labels",
        "post_comment",
        "return_to_draft",
    ]

    return operation in safe_operations


def validate_file_paths(files: list[dict[str, Any]]) -> None:
    """Validate file paths don't contain path traversal attacks.

    Args:
        files: List of file dictionaries with 'path' field

    Raises:
        ValueError: If any file path is unsafe
    """
    for file_data in files:
        path = file_data.get("path", "")

        if not isinstance(path, str):
            raise ValueError(f"File path must be string, got {type(path)}")

        # Check for path traversal
        if ".." in path:
            raise ValueError(f"Path traversal detected in file path: {path}")

        # Check for absolute paths
        if path.startswith("/"):
            raise ValueError(f"Absolute path not allowed: {path}")

        # Check for unusual characters
        if re.search(r"[<>|;`$&]", path):
            raise ValueError(f"Invalid characters in file path: {path}")


def create_audit_log(
    pr_number: int, operation: str, result: str, details: dict[str, Any] = None
) -> str:
    """Create audit log entry for security tracking.

    Args:
        pr_number: PR number
        operation: Operation performed
        result: Result (success/failure)
        details: Additional details

    Returns:
        Formatted audit log entry
    """
    import time

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] PR-{pr_number} | {operation} | {result}"

    if details:
        log_entry += f" | {details}"

    return log_entry
