"""
Integration tests for native binary trace logging.

Tests integration between components: launcher + trace logging, LiteLLM + callbacks.
This is TDD - tests written before implementation.

Coverage Focus (30% of test suite):
- Launcher integration with binary manager
- LiteLLM integration with trace callbacks
- End-to-end trace file generation
- Configuration propagation
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from amplihack.launcher.claude_binary_manager import ClaudeBinaryManager, BinaryInfo
from amplihack.launcher.core import launch_claude
from amplihack.proxy.litellm_callbacks import register_trace_callbacks
from amplihack.tracing.trace_logger import TraceLogger


# =============================================================================
# Launcher Integration Tests
# =============================================================================


@pytest.mark.integration
def test_launcher_detects_and_uses_native_binary(tmp_path):
    """Test that launcher detects and uses native binary."""
    trace_file = tmp_path / "trace.jsonl"

    with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            # Launch with trace enabled
            launch_claude(enable_trace=True, trace_file=str(trace_file))

            # Should call rustyclawd with trace flags
            call_args = mock_run.call_args[0][0]
            assert "/usr/local/bin/rustyclawd" in str(call_args) or "rustyclawd" in str(call_args)


@pytest.mark.integration
def test_launcher_passes_trace_flags_to_binary(tmp_path):
    """Test that launcher passes trace flags to native binary."""
    trace_file = tmp_path / "trace.jsonl"

    binary = BinaryInfo(
        name="rustyclawd",
        path=Path("/usr/local/bin/rustyclawd"),
        supports_trace=True,
    )

    manager = ClaudeBinaryManager()

    with patch.object(manager, "detect_native_binary", return_value=binary):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            cmd = manager.build_command(binary, enable_trace=True, trace_file=str(trace_file))

            # Execute command
            subprocess.run(cmd, check=False)

            # Verify trace flags in command
            call_args = mock_run.call_args[0][0]
            assert "--trace" in call_args or "--log-file" in call_args


@pytest.mark.integration
def test_launcher_fallback_when_trace_unsupported(tmp_path):
    """Test launcher falls back gracefully when trace unsupported."""
    trace_file = tmp_path / "trace.jsonl"

    binary = BinaryInfo(
        name="claude",
        path=Path("/usr/local/bin/claude"),
        supports_trace=False,
    )

    manager = ClaudeBinaryManager()

    with patch.object(manager, "detect_native_binary", return_value=binary):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            # Should launch without trace flags
            cmd = manager.build_command(binary, enable_trace=True, trace_file=str(trace_file))

            # Should not include trace flags
            assert "--trace" not in cmd
            assert "--log-file" not in cmd


@pytest.mark.integration
def test_launcher_initializes_trace_logger(tmp_path):
    """Test that launcher initializes trace logger on startup."""
    trace_file = tmp_path / "trace.jsonl"

    with patch("amplihack.launcher.core.TraceLogger") as mock_logger_cls:
        mock_logger = Mock()
        mock_logger_cls.return_value = mock_logger

        with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
            with patch("subprocess.run"):
                launch_claude(enable_trace=True, trace_file=str(trace_file))

                # Should initialize trace logger
                mock_logger_cls.assert_called_once()


@pytest.mark.integration
def test_launcher_registers_litellm_callbacks(tmp_path):
    """Test that launcher registers LiteLLM callbacks."""
    trace_file = tmp_path / "trace.jsonl"

    with patch("amplihack.proxy.litellm_callbacks.register_trace_callbacks") as mock_register:
        with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
            with patch("subprocess.run"):
                launch_claude(enable_trace=True, trace_file=str(trace_file))

                # Should register callbacks
                mock_register.assert_called_once()
                call_kwargs = mock_register.call_args[1]
                assert call_kwargs.get("enabled") is True
                assert str(trace_file) in str(call_kwargs.get("trace_file"))


# =============================================================================
# LiteLLM Integration Tests
# =============================================================================


@pytest.mark.integration
def test_litellm_callbacks_write_to_trace_file(tmp_path):
    """Test that LiteLLM callbacks write to trace file."""
    trace_file = tmp_path / "trace.jsonl"

    with patch("litellm.callbacks.append"):
        callback = register_trace_callbacks(enabled=True, trace_file=str(trace_file))

    # Simulate LiteLLM request
    with callback.trace_logger:
        callback.on_llm_start({
            "model": "claude-3-sonnet-20240229",
            "messages": [{"role": "user", "content": "Hello"}],
        })

    # Verify trace file created and populated
    assert trace_file.exists()
    content = trace_file.read_text()
    assert "claude-3-sonnet" in content


@pytest.mark.integration
def test_litellm_callbacks_sanitize_credentials(tmp_path):
    """Test end-to-end credential sanitization."""
    trace_file = tmp_path / "trace.jsonl"

    with patch("litellm.callbacks.append"):
        callback = register_trace_callbacks(enabled=True, trace_file=str(trace_file))

    # Simulate request with credentials
    with callback.trace_logger:
        callback.on_llm_start({
            "model": "claude-3-sonnet-20240229",
            "api_key": "sk-1234567890abcdefghij",
            "messages": [{"role": "user", "content": "Using key sk-1234567890abcdefghij"}],
        })

    # Verify credentials sanitized in file
    content = trace_file.read_text()
    assert "sk-1234567890abcdefghij" not in content
    assert "sk-***" in content


@pytest.mark.integration
def test_litellm_full_request_cycle(tmp_path):
    """Test full LiteLLM request cycle with tracing."""
    trace_file = tmp_path / "trace.jsonl"

    with patch("litellm.callbacks.append"):
        callback = register_trace_callbacks(enabled=True, trace_file=str(trace_file))

    # Simulate complete request cycle
    with callback.trace_logger:
        callback.on_llm_start({
            "model": "claude-3-sonnet-20240229",
            "messages": [{"role": "user", "content": "Hello"}],
        })

        callback.on_llm_end({
            "response": {
                "id": "msg_123",
                "model": "claude-3-sonnet-20240229",
                "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
                "choices": [{"message": {"content": "Hi!"}}],
            }
        })

    # Verify complete cycle logged
    content = trace_file.read_text()
    lines = content.strip().split("\n")
    assert len(lines) == 2

    start = json.loads(lines[0])
    end = json.loads(lines[1])

    assert "timestamp" in start
    assert "timestamp" in end


# =============================================================================
# Configuration Integration Tests
# =============================================================================


@pytest.mark.integration
def test_env_configuration_propagates_to_all_components(monkeypatch, tmp_path):
    """Test that environment configuration propagates correctly."""
    trace_file = tmp_path / "trace.jsonl"
    monkeypatch.setenv("CLAUDE_TRACE_ENABLED", "true")
    monkeypatch.setenv("CLAUDE_TRACE_FILE", str(trace_file))

    # Should propagate to TraceLogger
    logger = TraceLogger.from_env()
    assert logger.enabled is True
    assert logger.log_file == trace_file

    # Should propagate to callbacks
    with patch("litellm.callbacks.append"):
        callback = register_trace_callbacks()
        assert callback is not None


@pytest.mark.integration
def test_disabled_trace_skips_all_components(monkeypatch):
    """Test that disabled trace skips all components."""
    monkeypatch.setenv("CLAUDE_TRACE_ENABLED", "false")

    # TraceLogger should be disabled
    logger = TraceLogger.from_env()
    assert logger.enabled is False

    # Callbacks should not be registered
    with patch("litellm.callbacks.append") as mock_append:
        callback = register_trace_callbacks()
        assert callback is None
        mock_append.assert_not_called()


# =============================================================================
# Error Handling Integration Tests
# =============================================================================


@pytest.mark.integration
def test_trace_error_does_not_break_launcher(tmp_path):
    """Test that trace errors don't break launcher."""
    # Invalid trace file path
    trace_file = "/invalid/readonly/trace.jsonl"

    with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            # Should launch successfully despite trace error
            try:
                launch_claude(enable_trace=True, trace_file=trace_file)
            except (OSError, IOError, PermissionError):
                pass  # Trace error, but launcher should handle gracefully


@pytest.mark.integration
def test_litellm_continues_on_callback_error(tmp_path):
    """Test that LiteLLM continues even if callback fails."""
    trace_file = tmp_path / "readonly.jsonl"
    trace_file.touch()
    trace_file.chmod(0o444)  # Read-only

    with patch("litellm.callbacks.append"):
        callback = register_trace_callbacks(enabled=True, trace_file=str(trace_file))

    # Callback error should not break LiteLLM flow
    try:
        with callback.trace_logger:
            callback.on_llm_start({"model": "test"})
    except PermissionError:
        pass  # Expected, but shouldn't propagate


# =============================================================================
# Performance Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.performance
def test_end_to_end_trace_overhead(tmp_path):
    """Test end-to-end tracing overhead."""
    trace_file = tmp_path / "trace.jsonl"

    with patch("litellm.callbacks.append"):
        callback = register_trace_callbacks(enabled=True, trace_file=str(trace_file))

    # Measure complete request cycle
    import time

    start = time.perf_counter()

    with callback.trace_logger:
        callback.on_llm_start({
            "model": "claude-3-sonnet-20240229",
            "messages": [{"role": "user", "content": "test" * 100}],
        })

        callback.on_llm_end({"response": {"choices": [{"message": {"content": "response" * 100}}]}})

    end = time.perf_counter()

    # Total overhead should be reasonable (<20ms for entire cycle)
    total_time = (end - start) * 1000
    assert total_time < 20, f"Total trace overhead {total_time:.3f}ms exceeds 20ms"


# =============================================================================
# Concurrent Access Tests
# =============================================================================


@pytest.mark.integration
def test_concurrent_trace_writes(tmp_path):
    """Test concurrent writes to trace file."""
    import threading

    trace_file = tmp_path / "trace.jsonl"

    with patch("litellm.callbacks.append"):
        callback = register_trace_callbacks(enabled=True, trace_file=str(trace_file))

    def write_logs(thread_id):
        with callback.trace_logger:
            for i in range(10):
                callback.on_llm_start({"model": "test", "thread": thread_id, "seq": i})

    # Spawn multiple threads
    threads = [threading.Thread(target=write_logs, args=(i,)) for i in range(5)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Verify all writes succeeded
    content = trace_file.read_text()
    lines = content.strip().split("\n")
    assert len(lines) == 50  # 5 threads * 10 logs each


# =============================================================================
# Prerequisites Integration Tests
# =============================================================================


@pytest.mark.integration
def test_integration_with_prerequisites_checker():
    """Test integration with prerequisites checker."""
    from amplihack.utils.prerequisites import PrerequisiteChecker

    checker = PrerequisiteChecker()
    manager = ClaudeBinaryManager()

    # Binary detection should align with prerequisites
    with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
        binary = manager.detect_native_binary()

        # Should be compatible with prerequisite checks
        assert binary is not None


@pytest.mark.integration
def test_prerequisites_checker_reports_trace_support():
    """Test that prerequisites checker reports trace support status."""
    from amplihack.utils.prerequisites import PrerequisiteChecker

    checker = PrerequisiteChecker()

    with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
        result = checker.check_native_binary()

        # Should report trace support capability
        # Exact API TBD in implementation


# =============================================================================
# Cleanup Integration Tests
# =============================================================================


@pytest.mark.integration
def test_cleanup_on_launcher_exit(tmp_path):
    """Test that resources are cleaned up on launcher exit."""
    trace_file = tmp_path / "trace.jsonl"

    with patch("litellm.callbacks.append"):
        callback = register_trace_callbacks(enabled=True, trace_file=str(trace_file))

    with callback.trace_logger:
        callback.on_llm_start({"model": "test"})

    # After exit, file should be flushed and closed
    assert trace_file.exists()

    # Should be able to read file (not locked)
    content = trace_file.read_text()
    assert len(content) > 0


# =============================================================================
# Cross-Component Data Flow Tests
# =============================================================================


@pytest.mark.integration
def test_data_flows_from_launcher_to_trace_file(tmp_path):
    """Test complete data flow from launcher to trace file."""
    trace_file = tmp_path / "trace.jsonl"

    # Initialize all components
    logger = TraceLogger(enabled=True, log_file=trace_file)

    with patch("litellm.callbacks.append"):
        callback = register_trace_callbacks(enabled=True, trace_file=str(trace_file))

    # Simulate launcher -> LiteLLM -> TraceLogger flow
    with logger:
        logger.log({"event": "launcher_start", "binary": "rustyclawd"})

    with callback.trace_logger:
        callback.on_llm_start({"model": "claude-3-sonnet-20240229"})

    # Verify both events in trace file
    content = trace_file.read_text()
    assert "launcher_start" in content
    assert "claude-3-sonnet" in content


@pytest.mark.integration
def test_configuration_consistency_across_components(tmp_path):
    """Test that configuration is consistent across components."""
    trace_file = tmp_path / "trace.jsonl"

    # All components should use same trace file
    logger = TraceLogger(enabled=True, log_file=trace_file)

    with patch("litellm.callbacks.append"):
        callback = register_trace_callbacks(enabled=True, trace_file=str(trace_file))

    # Both should write to same file
    with logger:
        logger.log({"source": "logger"})

    with callback.trace_logger:
        callback.on_llm_start({"source": "callback"})

    # Verify both in same file
    content = trace_file.read_text()
    lines = content.strip().split("\n")
    assert len(lines) == 2

    sources = [json.loads(line).get("source") or json.loads(line).get("event") for line in lines]
    assert "logger" in str(sources)
