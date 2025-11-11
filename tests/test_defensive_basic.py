"""Basic tests for defensive utilities to verify functionality."""

import tempfile
from pathlib import Path

import pytest

from amplihack.utils.defensive import (
    isolate_prompt,
    parse_llm_json,
    read_file_with_retry,
    retry_with_feedback,
    validate_json_schema,
    write_file_with_retry,
)


def test_parse_llm_json_basic():
    """Test basic JSON parsing."""
    assert parse_llm_json('{"key": "value"}') == {"key": "value"}
    assert parse_llm_json('```json\n{"key": "value"}\n```') == {"key": "value"}


def test_retry_with_feedback_basic():
    """Test basic retry functionality."""
    call_count = [0]

    def func():
        call_count[0] += 1
        if call_count[0] < 2:
            raise ValueError("fail")
        return "success"

    result = retry_with_feedback(func, max_attempts=3, initial_delay=0.1)
    assert result == "success"
    assert call_count[0] == 2


def test_isolate_prompt_basic():
    """Test basic prompt isolation."""
    result = isolate_prompt("test prompt")
    assert "user" in result
    assert "test prompt" in result["user"]


def test_file_operations_basic():
    """Test basic file I/O with retry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        write_file_with_retry(file_path, "test content", max_attempts=2, initial_delay=0.1)
        content = read_file_with_retry(file_path, max_attempts=2, initial_delay=0.1)
        assert content == "test content"


def test_validate_json_schema_basic():
    """Test basic JSON schema validation."""
    data = {"name": "test", "value": 42}
    result = validate_json_schema(data, required_keys=["name", "value"])
    assert result == data

    with pytest.raises(ValueError, match="Missing required keys"):
        validate_json_schema({}, required_keys=["name"])
