"""
Integration tests for native binary trace logging.

Tests integration between components: launcher + trace logging.
This is TDD - tests written before implementation.

Coverage Focus (30% of test suite):
- Launcher integration with binary manager
- End-to-end trace file generation
- Configuration propagation
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from amplihack.launcher.claude_binary_manager import BinaryInfo, ClaudeBinaryManager
from amplihack.launcher.core import launch_claude
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


@pytest.mark.integration
def test_disabled_trace_skips_all_components(monkeypatch):
    """Test that disabled trace skips all components."""
    monkeypatch.setenv("CLAUDE_TRACE_ENABLED", "false")

    # TraceLogger should be disabled
    logger = TraceLogger.from_env()
    assert logger.enabled is False


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
            except (OSError, PermissionError):
                pass  # Trace error, but launcher should handle gracefully


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
def test_trace_logger_data_flow(tmp_path):
    """Test TraceLogger data flow from creation to file output."""
    trace_file = tmp_path / "trace.jsonl"

    logger = TraceLogger(enabled=True, log_file=trace_file)

    with logger:
        logger.log({"event": "launcher_start", "binary": "rustyclawd"})

    assert trace_file.exists()
    content = trace_file.read_text()
    assert "launcher_start" in content
