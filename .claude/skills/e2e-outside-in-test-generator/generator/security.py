"""Security utilities for safe file and path operations."""

import json
from pathlib import Path
from typing import Any


class SecurityError(Exception):
    """Base exception for security violations."""


def validate_project_root(path: Path, allowed_root: Path | None = None) -> Path:
    """Validate path is within project boundaries.

    Prevents path traversal attacks.

    Args:
        path: Path to validate
        allowed_root: Root directory (default: current working directory)

    Returns:
        Resolved path if valid

    Raises:
        SecurityError: If path is outside allowed root
    """
    if allowed_root is None:
        allowed_root = Path.cwd()

    resolved = path.resolve()
    allowed_resolved = allowed_root.resolve()

    # Check if path is within allowed root
    try:
        resolved.relative_to(allowed_resolved)
    except ValueError:
        raise SecurityError(f"Path traversal detected: {path} is outside {allowed_root}")

    return resolved


def sanitize_path(path: str) -> str:
    """Remove shell metacharacters from path strings.

    Prevents command injection via malicious paths.

    Args:
        path: Path string to sanitize

    Returns:
        Sanitized path string

    Raises:
        SecurityError: If path contains forbidden characters
    """
    forbidden_chars = [";", "|", "&", "`", "$", "(", ")", "<", ">", "\n", "\r"]

    for char in forbidden_chars:
        if char in path:
            raise SecurityError(f"Path contains forbidden character '{char}': {path}")

    return path


def read_json_safe(path: Path, max_size_mb: int = 10) -> dict[str, Any]:
    """Read JSON file with DoS protection.

    Prevents JSON bomb attacks via size limits.

    Args:
        path: Path to JSON file
        max_size_mb: Maximum file size in megabytes (default: 10MB)

    Returns:
        Parsed JSON data

    Raises:
        SecurityError: If file is too large
        ValueError: If JSON is invalid
    """
    # Check file size before reading
    file_size = path.stat().st_size
    max_bytes = max_size_mb * 1024 * 1024

    if file_size > max_bytes:
        raise SecurityError(
            f"JSON file too large: {file_size / 1024 / 1024:.1f}MB (max: {max_size_mb}MB)"
        )

    # Read and parse
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}")
