"""
Integration tests for native binary trace logging.

Tests integration between components: launcher + trace logging.

Coverage Focus (30% of test suite):
- Binary manager command building with trace flags
- TraceLogger configuration from environment
- End-to-end trace file generation
- Configuration propagation
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.launcher.claude_binary_manager import BinaryInfo, ClaudeBinaryManager
from amplihack.tracing.trace_logger import TraceLogger

# =============================================================================
# Binary Manager Integration Tests
# =============================================================================


@pytest.mark.integration
def test_binary_manager_detects_native_binary(tmp_path):
    """Test that binary manager detects native binary via shutil.which."""
    # Create a real executable file so path.exists() and os.access() pass
    fake_binary = tmp_path / "rustyclawd"
    fake_binary.write_text("#!/bin/sh\necho 'mock'")
    fake_binary.chmod(0o755)

    manager = ClaudeBinaryManager()

    with patch("shutil.which", return_value=str(fake_binary)):
        binary = manager.detect_native_binary()

        assert binary is not None
        assert "rustyclawd" in binary.name or "rustyclawd" in str(binary.path)


@pytest.mark.integration
def test_binary_manager_passes_trace_flags(tmp_path):
    """Test that binary manager adds trace flags to command."""
    trace_file = tmp_path / "trace.jsonl"

    binary = BinaryInfo(
        name="rustyclawd",
        path=Path("/usr/local/bin/rustyclawd"),
        supports_trace=True,
    )

    manager = ClaudeBinaryManager()
    cmd = manager.build_command(binary, enable_trace=True, trace_file=str(trace_file))

    # Should include the binary path and trace-related flags
    assert str(binary.path) in cmd[0]
    assert "--trace" in cmd or "--log-file" in cmd


@pytest.mark.integration
def test_binary_manager_no_trace_flags_when_unsupported(tmp_path):
    """Test binary manager omits trace flags when binary doesn't support them."""
    trace_file = tmp_path / "trace.jsonl"

    binary = BinaryInfo(
        name="claude",
        path=Path("/usr/local/bin/claude"),
        supports_trace=False,
    )

    manager = ClaudeBinaryManager()
    cmd = manager.build_command(binary, enable_trace=True, trace_file=str(trace_file))

    # Should not include trace flags for unsupported binaries
    assert "--trace" not in cmd
    assert "--log-file" not in cmd


# =============================================================================
# Configuration Integration Tests
# =============================================================================


@pytest.mark.integration
def test_env_configuration_propagates_to_trace_logger(monkeypatch, tmp_path):
    """Test that environment configuration propagates correctly."""
    trace_file = tmp_path / "trace.jsonl"
    monkeypatch.setenv("AMPLIHACK_TRACE_LOGGING", "true")
    monkeypatch.setenv("AMPLIHACK_TRACE_FILE", str(trace_file))

    logger = TraceLogger.from_env()
    assert logger.enabled is True
    assert logger.log_file == trace_file


@pytest.mark.integration
def test_disabled_trace_skips_all_components(monkeypatch):
    """Test that disabled trace skips all components."""
    monkeypatch.setenv("AMPLIHACK_TRACE_LOGGING", "false")

    logger = TraceLogger.from_env()
    assert logger.enabled is False


@pytest.mark.integration
def test_default_trace_is_disabled(monkeypatch):
    """Test that trace logging is disabled by default."""
    monkeypatch.delenv("AMPLIHACK_TRACE_LOGGING", raising=False)

    logger = TraceLogger.from_env()
    assert logger.enabled is False


# =============================================================================
# Prerequisites Integration Tests
# =============================================================================


@pytest.mark.integration
def test_integration_with_prerequisites_checker(tmp_path):
    """Test binary manager works alongside prerequisites checker."""
    from amplihack.utils.prerequisites import PrerequisiteChecker

    fake_binary = tmp_path / "rustyclawd"
    fake_binary.write_text("#!/bin/sh\necho 'mock'")
    fake_binary.chmod(0o755)

    PrerequisiteChecker()
    manager = ClaudeBinaryManager()

    with patch("shutil.which", return_value=str(fake_binary)):
        binary = manager.detect_native_binary()
        assert binary is not None


# =============================================================================
# TraceLogger Data Flow Tests
# =============================================================================


@pytest.mark.integration
def test_trace_logger_data_flow(tmp_path):
    """Test TraceLogger data flow from creation to file output."""
    trace_file = tmp_path / "trace.jsonl"

    logger = TraceLogger(enabled=True, log_file=trace_file)

    with logger:
        logger.log({"event": "launcher_start", "binary": "rustyclawd"})

    assert trace_file.exists()
    content = trace_file.read_text()
    assert "launcher_start" in content
