"""Tests for security utilities."""

from pathlib import Path

import pytest
from generator.security import (
    SecurityError,
    read_json_safe,
    sanitize_path,
    validate_project_root,
)


def test_validate_project_root_allows_valid_paths():
    """Valid paths within project should pass."""
    cwd = Path.cwd()
    valid_path = cwd / "test.txt"
    assert validate_project_root(valid_path) == valid_path.resolve()


def test_validate_project_root_rejects_traversal():
    """Path traversal should be rejected."""
    with pytest.raises(SecurityError, match="outside"):
        validate_project_root(Path("/etc/passwd"))


def test_sanitize_path_allows_safe_paths():
    """Safe paths should pass unchanged."""
    assert sanitize_path("test/file.ts") == "test/file.ts"


def test_sanitize_path_rejects_injection():
    """Shell metacharacters should be rejected."""
    with pytest.raises(SecurityError, match="forbidden"):
        sanitize_path("test; rm -rf /")


def test_sanitize_path_rejects_all_dangerous_chars():
    """All dangerous characters should be rejected."""
    dangerous_chars = [";", "|", "&", "`", "$", "(", ")", "<", ">"]
    for char in dangerous_chars:
        with pytest.raises(SecurityError, match="forbidden"):
            sanitize_path(f"test{char}file")


def test_read_json_safe_reads_valid_json(tmp_path):
    """Valid JSON files should be read successfully."""
    test_file = tmp_path / "test.json"
    test_file.write_text('{"key": "value"}')

    result = read_json_safe(test_file)
    assert result == {"key": "value"}


def test_read_json_safe_limits_size(tmp_path):
    """Large JSON files should be rejected."""
    large_file = tmp_path / "large.json"
    # Create 11MB file
    large_content = '{"x": "' + "a" * (11 * 1024 * 1024) + '"}'
    large_file.write_text(large_content)

    with pytest.raises(SecurityError, match="too large"):
        read_json_safe(large_file, max_size_mb=10)


def test_read_json_safe_rejects_invalid_json(tmp_path):
    """Invalid JSON should raise ValueError."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{invalid json")

    with pytest.raises(ValueError, match="Invalid JSON"):
        read_json_safe(invalid_file)
