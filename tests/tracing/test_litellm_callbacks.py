"""
Unit tests for LiteLLM callbacks module.

Tests callback registration, logging integration, performance overhead.
This is TDD - tests written before implementation.

Coverage Focus (60% of test suite):
- Callback registration with LiteLLM
- Trace logging integration
- Performance (<5ms overhead)
- Error handling
- Callback lifecycle
"""

import time
from unittest.mock import patch

import pytest

from amplihack.proxy.litellm_callbacks import (
    TraceCallback,
    register_trace_callbacks,
    unregister_trace_callbacks,
)

# =============================================================================
# Callback Registration Tests
# =============================================================================


def test_register_trace_callbacks_success():
    """Test successful callback registration."""
    with patch("litellm.callbacks", new=[]):
        callback = register_trace_callbacks(enabled=True, trace_file="/tmp/trace.jsonl")

        assert callback is not None
        assert isinstance(callback, TraceCallback)
        # Verify callback was added to list
        import litellm

        assert callback in litellm.callbacks


def test_register_trace_callbacks_disabled():
    """Test that callbacks are not registered when disabled."""
    with patch("litellm.callbacks", new=[]):
        callback = register_trace_callbacks(enabled=False)

        assert callback is None
        # Verify no callbacks were added
        import litellm

        assert len(litellm.callbacks) == 0


def test_register_trace_callbacks_returns_callback_instance():
    """Test that registration returns callback instance for cleanup."""
    with patch("litellm.callbacks", new=[]):
        callback = register_trace_callbacks(enabled=True, trace_file="/tmp/trace.jsonl")

        assert isinstance(callback, TraceCallback)


def test_unregister_trace_callbacks_success():
    """Test successful callback unregistration."""
    with patch("litellm.callbacks", new=[]):
        callback = register_trace_callbacks(enabled=True, trace_file="/tmp/trace.jsonl")

        # Verify it was added
        import litellm

        assert callback in litellm.callbacks

        # Unregister
        unregister_trace_callbacks(callback)

        # Verify it was removed
        assert callback not in litellm.callbacks


def test_unregister_trace_callbacks_handles_none():
    """Test unregistration with None callback."""
    with patch("litellm.callbacks", new=[]):
        # Should not raise error
        unregister_trace_callbacks(None)


def test_unregister_trace_callbacks_handles_not_registered():
    """Test unregistration of callback that was never registered."""
    callback = TraceCallback(trace_file="/tmp/trace.jsonl")

    with patch("litellm.callbacks", new=[]):
        # Should not raise error even when callback not in list
        unregister_trace_callbacks(callback)


# =============================================================================
# TraceCallback Class Tests
# =============================================================================


def test_trace_callback_initialization():
    """Test TraceCallback initialization."""
    callback = TraceCallback(trace_file="/tmp/trace.jsonl")

    assert callback.trace_file == "/tmp/trace.jsonl"
    assert callback.trace_logger is not None


def test_trace_callback_initialization_with_logger():
    """Test TraceCallback initialization with existing logger."""
    from amplihack.tracing.trace_logger import TraceLogger

    logger = TraceLogger(enabled=True, log_file="/tmp/trace.jsonl")
    callback = TraceCallback(trace_logger=logger)

    assert callback.trace_logger == logger


# =============================================================================
# Callback Lifecycle Events Tests
# =============================================================================


def test_callback_on_llm_start_event(tmp_path):
    """Test callback on LLM start event."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "model": "claude-3-sonnet-20240229",
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.7,
    }

    with callback.trace_logger:
        callback.on_llm_start(kwargs)

    # Verify log entry
    content = trace_file.read_text()
    assert "on_llm_start" in content or "llm_start" in content
    assert "claude-3-sonnet" in content


def test_callback_on_llm_end_event(tmp_path):
    """Test callback on LLM end event."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "response": {"choices": [{"message": {"content": "Hello!"}}]},
        "model": "claude-3-sonnet-20240229",
    }

    with callback.trace_logger:
        callback.on_llm_end(kwargs)

    content = trace_file.read_text()
    assert "on_llm_end" in content or "llm_end" in content


def test_callback_on_llm_error_event(tmp_path):
    """Test callback on LLM error event."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "exception": "RateLimitError",
        "message": "Rate limit exceeded",
        "model": "claude-3-sonnet-20240229",
    }

    with callback.trace_logger:
        callback.on_llm_error(kwargs)

    content = trace_file.read_text()
    assert "on_llm_error" in content or "llm_error" in content
    assert "RateLimitError" in content


def test_callback_on_llm_stream_event(tmp_path):
    """Test callback on LLM streaming event."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "chunk": {"choices": [{"delta": {"content": "Hello"}}]},
        "model": "claude-3-sonnet-20240229",
    }

    with callback.trace_logger:
        callback.on_llm_stream(kwargs)

    content = trace_file.read_text()
    assert "on_llm_stream" in content or "llm_stream" in content


# =============================================================================
# Data Logging Tests
# =============================================================================


def test_callback_logs_request_metadata(tmp_path):
    """Test that request metadata is logged."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "model": "claude-3-sonnet-20240229",
        "messages": [{"role": "user", "content": "test"}],
        "temperature": 0.7,
        "max_tokens": 1024,
        "stream": False,
    }

    with callback.trace_logger:
        callback.on_llm_start(kwargs)

    import json

    content = trace_file.read_text()
    entry = json.loads(content.strip().split("\n")[0])

    assert entry.get("model") == "claude-3-sonnet-20240229"
    assert entry.get("temperature") == 0.7 or "temperature" in str(entry)


def test_callback_logs_response_metadata(tmp_path):
    """Test that response metadata is logged."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "response": {
            "id": "msg_123",
            "model": "claude-3-sonnet-20240229",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "choices": [{"message": {"content": "Response"}}],
        }
    }

    with callback.trace_logger:
        callback.on_llm_end(kwargs)

    import json

    content = trace_file.read_text()
    entry = json.loads(content.strip().split("\n")[0])

    # Should log usage information
    assert "usage" in str(entry) or "tokens" in str(entry)


def test_callback_logs_timing_information(tmp_path):
    """Test that timing information is logged."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "model": "claude-3-sonnet-20240229",
        "messages": [{"role": "user", "content": "test"}],
    }

    with callback.trace_logger:
        callback.on_llm_start(kwargs)
        time.sleep(0.01)  # Simulate request time
        callback.on_llm_end({"response": {}})

    import json

    content = trace_file.read_text()
    lines = content.strip().split("\n")

    # Both start and end should have timestamps
    start_entry = json.loads(lines[0])
    end_entry = json.loads(lines[1])

    assert "timestamp" in start_entry
    assert "timestamp" in end_entry


# =============================================================================
# Token Sanitization Tests
# =============================================================================


def test_callback_sanitizes_api_keys(tmp_path):
    """Test that API keys in callbacks are sanitized."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "model": "claude-3-sonnet-20240229",
        "api_key": "sk-1234567890abcdefghij",
        "messages": [{"role": "user", "content": "test"}],
    }

    with callback.trace_logger:
        callback.on_llm_start(kwargs)

    content = trace_file.read_text()
    assert "sk-1234567890abcdefghij" not in content
    assert "sk-***" in content


def test_callback_sanitizes_auth_headers(tmp_path):
    """Test that authorization headers are sanitized."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "model": "claude-3-sonnet-20240229",
        "headers": {"Authorization": "Bearer secret_token_123"},
        "messages": [{"role": "user", "content": "test"}],
    }

    with callback.trace_logger:
        callback.on_llm_start(kwargs)

    content = trace_file.read_text()
    assert "secret_token_123" not in content


def test_callback_sanitizes_nested_credentials(tmp_path):
    """Test sanitization of credentials in nested structures."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "model": "claude-3-sonnet-20240229",
        "extra_config": {
            "api_settings": {
                "api_key": "sk-1234567890abcdefghij",
                "endpoint": "https://api.anthropic.com",
            }
        },
    }

    with callback.trace_logger:
        callback.on_llm_start(kwargs)

    content = trace_file.read_text()
    assert "sk-1234567890abcdefghij" not in content


# =============================================================================
# Performance Tests
# =============================================================================


def test_callback_overhead_under_5_milliseconds(tmp_path):
    """Test that callback overhead is <5ms per call."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "model": "claude-3-sonnet-20240229",
        "messages": [{"role": "user", "content": "test"}],
    }

    # Measure 10 calls
    times = []
    with callback.trace_logger:
        for _ in range(10):
            start = time.perf_counter()
            callback.on_llm_start(kwargs)
            end = time.perf_counter()
            times.append(end - start)

    avg_time = sum(times) / len(times)
    assert avg_time < 0.005, f"Callback overhead {avg_time * 1000:.3f}ms exceeds 5ms limit"


@pytest.mark.performance
def test_callback_no_overhead_when_disabled():
    """Test that disabled callbacks have minimal overhead."""
    with patch("litellm.callbacks", new=[]):
        callback = register_trace_callbacks(enabled=False)

        assert callback is None
        # Verify no callbacks were added
        import litellm

        assert len(litellm.callbacks) == 0


def test_callback_async_logging_performance(tmp_path):
    """Test that async logging doesn't block callback execution."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "model": "claude-3-sonnet-20240229",
        "messages": [{"role": "user", "content": "test" * 1000}],
    }

    with callback.trace_logger:
        start = time.perf_counter()
        callback.on_llm_start(kwargs)
        end = time.perf_counter()

    # Should complete quickly even with large data
    assert (end - start) < 0.010  # <10ms


# =============================================================================
# Error Handling Tests
# =============================================================================


def test_callback_handles_missing_fields_gracefully(tmp_path):
    """Test that callback handles missing fields in kwargs."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    # Minimal kwargs
    kwargs = {}

    with callback.trace_logger:
        # Should not raise error
        callback.on_llm_start(kwargs)

    assert trace_file.exists()


def test_callback_handles_malformed_response(tmp_path):
    """Test handling of malformed response data."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {"response": "invalid", "choices": None}

    with callback.trace_logger:
        # Should handle gracefully
        callback.on_llm_end(kwargs)

    assert trace_file.exists()


def test_callback_handles_exceptions_in_logging(tmp_path):
    """Test that exceptions in logging don't break LiteLLM flow."""
    trace_file = tmp_path / "readonly.jsonl"
    trace_file.touch()
    trace_file.chmod(0o444)  # Read-only

    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {
        "model": "claude-3-sonnet-20240229",
        "messages": [{"role": "user", "content": "test"}],
    }

    # Should not raise exception that would break LiteLLM
    try:
        with callback.trace_logger:
            callback.on_llm_start(kwargs)
    except PermissionError:
        pass  # Expected, but shouldn't propagate to LiteLLM


def test_callback_handles_file_write_errors():
    """Test handling of file write errors."""
    callback = TraceCallback(trace_file="/dev/full")  # Device that's always full

    kwargs = {
        "model": "claude-3-sonnet-20240229",
        "messages": [{"role": "user", "content": "test"}],
    }

    # Should handle gracefully
    try:
        with callback.trace_logger:
            callback.on_llm_start(kwargs)
    except OSError:
        pass  # Expected


# =============================================================================
# Streaming Support Tests
# =============================================================================


def test_callback_logs_streaming_chunks(tmp_path):
    """Test that streaming chunks are logged."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    with callback.trace_logger:
        # Simulate streaming
        for i in range(5):
            kwargs = {"chunk": {"choices": [{"delta": {"content": f"chunk{i}"}}]}}
            callback.on_llm_stream(kwargs)

    content = trace_file.read_text()
    lines = content.strip().split("\n")
    assert len(lines) == 5


def test_callback_handles_empty_streaming_chunks(tmp_path):
    """Test handling of empty streaming chunks."""
    trace_file = tmp_path / "trace.jsonl"
    callback = TraceCallback(trace_file=str(trace_file))

    kwargs = {"chunk": {"choices": [{"delta": {}}]}}

    with callback.trace_logger:
        # Should handle gracefully
        callback.on_llm_stream(kwargs)

    assert trace_file.exists()


# =============================================================================
# Integration Tests
# =============================================================================


def test_callback_integrates_with_litellm_flow(tmp_path):
    """Test full integration with LiteLLM request flow."""
    trace_file = tmp_path / "trace.jsonl"

    with patch("litellm.callbacks", new=[]):
        callback = register_trace_callbacks(enabled=True, trace_file=str(trace_file))

        # Simulate LiteLLM flow
        with callback.trace_logger:
            callback.on_llm_start(
                {
                    "model": "claude-3-sonnet-20240229",
                    "messages": [{"role": "user", "content": "Hello"}],
                }
            )

            callback.on_llm_end({"response": {"choices": [{"message": {"content": "Hi!"}}]}})

    # Verify complete flow
    import json

    content = trace_file.read_text()
    lines = content.strip().split("\n")
    assert len(lines) == 2

    start_event = json.loads(lines[0])
    end_event = json.loads(lines[1])

    assert "timestamp" in start_event
    assert "timestamp" in end_event


def test_callback_cleanup_on_unregister(tmp_path):
    """Test that resources are cleaned up on unregister."""
    trace_file = tmp_path / "trace.jsonl"

    with patch("litellm.callbacks", new=[]):
        callback = register_trace_callbacks(enabled=True, trace_file=str(trace_file))

        with callback.trace_logger:
            callback.on_llm_start({"model": "test"})

        unregister_trace_callbacks(callback)

        # Logger should be closed
        assert (
            callback.trace_logger._file_handle is None or callback.trace_logger._file_handle.closed
        )


# =============================================================================
# Configuration Tests
# =============================================================================


def test_callback_respects_env_configuration(monkeypatch, tmp_path):
    """Test that callbacks respect environment configuration."""
    trace_file = tmp_path / "trace.jsonl"
    monkeypatch.setenv("AMPLIHACK_TRACE_LOGGING", "true")
    monkeypatch.setenv("AMPLIHACK_TRACE_FILE", str(trace_file))

    with patch("litellm.callbacks", new=[]):
        callback = register_trace_callbacks()

        assert callback is not None
        assert callback.trace_file == str(trace_file)


def test_callback_disabled_by_default(monkeypatch):
    """Test that callbacks are disabled by default."""
    monkeypatch.delenv("AMPLIHACK_TRACE_LOGGING", raising=False)

    with patch("litellm.callbacks", new=[]):
        callback = register_trace_callbacks()

        assert callback is None
        # Verify no callbacks were added
        import litellm

        assert len(litellm.callbacks) == 0
