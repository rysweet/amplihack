"""
Unit tests for TraceLogger module.

Tests JSONL logging, TokenSanitizer integration, performance requirements.
This is TDD - tests written before implementation.

Coverage Focus (60% of test suite):
- JSONL formatting and writing
- Token sanitization integration
- Performance (<0.1ms disabled, <10ms enabled)
- Error handling and edge cases
- Context management (with/async with)
"""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.tracing.trace_logger import TraceLogger

# =============================================================================
# Initialization Tests
# =============================================================================


def test_trace_logger_initialization_enabled(tmp_path):
    """Test TraceLogger initialization when enabled."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    assert logger.enabled is True
    assert logger.log_file == log_file
    assert logger._file_handle is None  # Not opened yet


def test_trace_logger_initialization_disabled():
    """Test TraceLogger initialization when disabled."""
    logger = TraceLogger(enabled=False)

    assert logger.enabled is False
    assert logger.log_file is None
    assert logger._file_handle is None


def test_trace_logger_default_disabled():
    """Test TraceLogger defaults to disabled (opt-in behavior)."""
    logger = TraceLogger()

    assert logger.enabled is False


def test_trace_logger_creates_parent_directories(tmp_path):
    """Test that parent directories are created automatically."""
    log_file = tmp_path / "nested" / "dir" / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        logger.log({"event": "test"})

    assert log_file.parent.exists()
    assert log_file.exists()


# =============================================================================
# JSONL Formatting Tests
# =============================================================================


def test_log_creates_valid_jsonl(tmp_path):
    """Test that log entries are valid JSON Lines format."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        logger.log({"event": "test", "value": 123})
        logger.log({"event": "second", "data": {"nested": "object"}})

    # Read and validate JSONL
    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 2

    # Each line should be valid JSON
    entry1 = json.loads(lines[0])
    entry2 = json.loads(lines[1])

    assert entry1["event"] == "test"
    assert entry1["value"] == 123
    assert entry2["event"] == "second"
    assert entry2["data"]["nested"] == "object"


def test_log_adds_timestamp(tmp_path):
    """Test that timestamp is automatically added to log entries."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        logger.log({"event": "test"})

    lines = log_file.read_text().strip().split("\n")
    entry = json.loads(lines[0])

    assert "timestamp" in entry
    assert "event" in entry
    # Validate ISO 8601 format
    assert "T" in entry["timestamp"]
    assert "Z" in entry["timestamp"] or "+" in entry["timestamp"]


def test_log_preserves_existing_timestamp(tmp_path):
    """Test that existing timestamp is preserved if provided."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    custom_timestamp = "2026-01-22T10:00:00Z"

    with logger:
        logger.log({"event": "test", "timestamp": custom_timestamp})

    lines = log_file.read_text().strip().split("\n")
    entry = json.loads(lines[0])

    assert entry["timestamp"] == custom_timestamp


def test_log_handles_complex_nested_data(tmp_path):
    """Test logging complex nested data structures."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    complex_data = {
        "event": "api_call",
        "request": {
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": {"prompt": "test", "model": "claude-3"},
        },
        "response": {"status": 200, "tokens": [1, 2, 3]},
    }

    with logger:
        logger.log(complex_data)

    lines = log_file.read_text().strip().split("\n")
    entry = json.loads(lines[0])

    assert entry["event"] == "api_call"
    assert entry["request"]["method"] == "POST"
    assert entry["response"]["status"] == 200


# =============================================================================
# Token Sanitization Tests
# =============================================================================


def test_log_sanitizes_api_keys(tmp_path):
    """Test that API keys are sanitized before logging."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        logger.log(
            {
                "event": "api_call",
                "api_key": "sk-1234567890abcdefghij",
                "message": "Using key sk-1234567890abcdefghij",
            }
        )

    lines = log_file.read_text().strip().split("\n")
    entry = json.loads(lines[0])

    # API key should be sanitized
    assert "sk-1234567890abcdefghij" not in json.dumps(entry)
    assert entry["api_key"] == "sk-***"
    assert "sk-***" in entry["message"]


def test_log_sanitizes_bearer_tokens(tmp_path):
    """Test that Bearer tokens are sanitized."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        logger.log(
            {
                "event": "request",
                "headers": {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"},
            }
        )

    lines = log_file.read_text().strip().split("\n")
    entry = json.loads(lines[0])

    # Token should be sanitized
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in json.dumps(entry)
    assert "***" in entry["headers"]["Authorization"]


def test_log_sanitizes_github_tokens(tmp_path):
    """Test that GitHub tokens are sanitized."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        logger.log(
            {
                "event": "git_operation",
                "token": "ghp_FAKE_TOKEN_FOR_TESTING_ONLY_DO_NOT_USE",
            }
        )

    lines = log_file.read_text().strip().split("\n")
    entry = json.loads(lines[0])

    assert "ghp_FAKE_TOKEN_FOR_TESTING_ONLY_DO_NOT_USE" not in json.dumps(entry)
    assert entry["token"] == "ghp_***"


def test_log_sanitizes_nested_credentials(tmp_path):
    """Test that credentials in nested structures are sanitized."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        logger.log(
            {
                "event": "config",
                "settings": {
                    "api": {
                        "key": "sk-1234567890abcdefghij",
                        "endpoint": "https://api.example.com",
                    },
                    "auth": {
                        "password": "secret123",
                        "token": "ghp_FAKE_TOKEN_FOR_TESTING_ONLY_DO_NOT_USE",
                    },
                },
            }
        )

    lines = log_file.read_text().strip().split("\n")
    entry = json.loads(lines[0])

    # All sensitive data should be sanitized
    raw_json = json.dumps(entry)
    assert "sk-1234567890abcdefghij" not in raw_json
    assert "secret123" not in raw_json
    assert "ghp_FAKE_TOKEN_FOR_TESTING_ONLY_DO_NOT_USE" not in raw_json


# =============================================================================
# Performance Tests
# =============================================================================


def test_disabled_overhead_under_100_microseconds():
    """Test that disabled logger has <0.1ms (100μs) overhead."""
    logger = TraceLogger(enabled=False)

    # Measure overhead of 1000 calls
    start = time.perf_counter()
    for _ in range(1000):
        logger.log({"event": "test", "data": "value"})
    end = time.perf_counter()

    # Average per call should be <0.1ms (0.0001 seconds)
    avg_time = (end - start) / 1000
    assert avg_time < 0.0001, f"Disabled overhead {avg_time * 1000:.3f}ms exceeds 0.1ms limit"


def test_enabled_overhead_under_10_milliseconds(tmp_path):
    """Test that enabled logger has <10ms overhead per log."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        # Measure 10 representative logs
        times = []
        for _ in range(10):
            start = time.perf_counter()
            logger.log({"event": "test", "data": {"key": "value" * 100}})
            end = time.perf_counter()
            times.append(end - start)

    avg_time = sum(times) / len(times)
    assert avg_time < 0.010, f"Enabled overhead {avg_time * 1000:.3f}ms exceeds 10ms limit"


@pytest.mark.performance
def test_performance_no_sanitization_overhead_when_disabled():
    """Test that TokenSanitizer is not called when disabled."""
    logger = TraceLogger(enabled=False)

    with patch("amplihack.tracing.trace_logger.TokenSanitizer.sanitize_dict") as mock_sanitize:
        logger.log({"event": "test", "api_key": "sk-1234567890abcdefghij"})

        # Sanitizer should NOT be called when disabled
        mock_sanitize.assert_not_called()


# =============================================================================
# Context Manager Tests
# =============================================================================


def test_context_manager_opens_and_closes_file(tmp_path):
    """Test that context manager properly opens and closes file."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    assert logger._file_handle is None

    with logger:
        assert logger._file_handle is not None
        logger.log({"event": "test"})

    # File should be closed after context
    assert logger._file_handle is None or logger._file_handle.closed


def test_context_manager_flushes_on_exit(tmp_path):
    """Test that data is flushed when exiting context."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        logger.log({"event": "test"})
        # Data should be written even before context exits

    # Read file after context exits
    content = log_file.read_text()
    assert "test" in content


def test_context_manager_handles_errors_gracefully(tmp_path):
    """Test that context manager closes file even on errors."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    try:
        with logger:
            logger.log({"event": "test"})
            raise ValueError("Test error")
    except ValueError:
        pass

    # File should still be closed
    assert logger._file_handle is None or logger._file_handle.closed


@pytest.mark.asyncio
async def test_async_context_manager(tmp_path):
    """Test async context manager support."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    async with logger:
        logger.log({"event": "async_test"})

    # Verify log was written
    content = log_file.read_text()
    assert "async_test" in content


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


def test_log_when_disabled_is_noop():
    """Test that logging when disabled is a no-op."""
    logger = TraceLogger(enabled=False)

    # Should not raise error
    logger.log({"event": "test"})
    logger.log(None)
    logger.log({})


def test_log_handles_none_data(tmp_path):
    """Test logging None data."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        logger.log(None)

    # Should write empty object or handle gracefully
    content = log_file.read_text().strip()
    if content:
        entry = json.loads(content)
        assert "timestamp" in entry


def test_log_handles_empty_dict(tmp_path):
    """Test logging empty dictionary."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        logger.log({})

    lines = log_file.read_text().strip().split("\n")
    entry = json.loads(lines[0])
    assert "timestamp" in entry


def test_log_handles_non_serializable_data(tmp_path):
    """Test logging data that cannot be JSON serialized."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    class NonSerializable:
        pass

    with logger:
        # Should handle gracefully (convert to string or skip)
        logger.log({"event": "test", "obj": NonSerializable()})

    # Should not crash
    assert log_file.exists()


def test_log_handles_large_data(tmp_path):
    """Test logging large data structures."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    large_data = {
        "event": "large_request",
        "data": "x" * 10000,  # 10KB string
        "array": list(range(1000)),
    }

    with logger:
        logger.log(large_data)

    # Should write successfully
    assert log_file.exists()
    content = log_file.read_text()
    entry = json.loads(content)
    assert entry["event"] == "large_request"


def test_log_handles_unicode_and_special_chars(tmp_path):
    """Test logging Unicode and special characters."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        logger.log(
            {
                "event": "unicode_test",
                "message": "Hello 世界 🌍",
                "special": "Line\nBreak\tTab",
            }
        )

    lines = log_file.read_text().strip().split("\n")
    entry = json.loads(lines[0])
    assert "世界" in entry["message"]
    assert "🌍" in entry["message"]


def test_log_without_context_manager_is_noop():
    """Test that logging without context manager is a silent no-op (graceful degradation)."""
    logger = TraceLogger(enabled=True, log_file=Path("/tmp/test.jsonl"))

    # Should not raise - instead silently does nothing
    logger.log({"event": "test"})
    # If we got here without exception, the test passes


def test_multiple_context_manager_entries(tmp_path):
    """Test that logger can be used with multiple context entries."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        logger.log({"event": "first"})

    with logger:
        logger.log({"event": "second"})

    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "first"
    assert json.loads(lines[1])["event"] == "second"


# =============================================================================
# File Handling Tests
# =============================================================================


def test_log_appends_to_existing_file(tmp_path):
    """Test that logging appends to existing file rather than overwriting."""
    log_file = tmp_path / "trace.jsonl"

    # Write first entry
    logger1 = TraceLogger(enabled=True, log_file=log_file)
    with logger1:
        logger1.log({"event": "first"})

    # Write second entry with new logger instance
    logger2 = TraceLogger(enabled=True, log_file=log_file)
    with logger2:
        logger2.log({"event": "second"})

    # Both entries should exist
    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 2


def test_log_handles_permission_errors_gracefully(tmp_path):
    """Test graceful handling of permission errors - logs warning to stderr and disables."""
    log_file = tmp_path / "readonly.jsonl"
    log_file.touch()
    log_file.chmod(0o444)  # Read-only

    logger = TraceLogger(enabled=True, log_file=log_file)

    # Should not raise - gracefully disables and logs warning
    with logger:
        # Logger should be disabled after failing to open
        assert not logger.enabled
        # Logging should be a no-op
        logger.log({"event": "test"})


def test_log_handles_disk_full_errors(tmp_path):
    """Test handling of disk full errors."""
    log_file = tmp_path / "trace.jsonl"
    logger = TraceLogger(enabled=True, log_file=log_file)

    with logger:
        # Simulate disk full by writing huge data
        # This test is aspirational - actual implementation should handle gracefully
        try:
            logger.log({"event": "test", "data": "x" * (10**9)})  # 1GB
        except OSError:
            pass  # Expected


# =============================================================================
# Configuration Tests
# =============================================================================


def test_trace_logger_respects_env_variable(monkeypatch, tmp_path):
    """Test that TraceLogger respects environment variable configuration."""
    log_file = tmp_path / "trace.jsonl"
    monkeypatch.setenv("AMPLIHACK_TRACE_LOGGING", "true")
    monkeypatch.setenv("AMPLIHACK_TRACE_FILE", str(log_file))

    logger = TraceLogger.from_env()

    assert logger.enabled is True
    assert logger.log_file == log_file


def test_trace_logger_env_disabled_by_default(monkeypatch):
    """Test that tracing is disabled by default when env var not set."""
    monkeypatch.delenv("AMPLIHACK_TRACE_LOGGING", raising=False)

    logger = TraceLogger.from_env()

    assert logger.enabled is False


def test_trace_logger_env_handles_invalid_path(monkeypatch):
    """Test handling of invalid log file path from environment."""
    monkeypatch.setenv("AMPLIHACK_TRACE_LOGGING", "true")
    monkeypatch.setenv("AMPLIHACK_TRACE_FILE", "/invalid/path/trace.jsonl")

    logger = TraceLogger.from_env()

    # Should handle gracefully - either disable or raise clear error
    # Exact behavior TBD in implementation
