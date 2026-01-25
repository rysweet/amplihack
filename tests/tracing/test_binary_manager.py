"""
Unit tests for ClaudeBinaryManager module.

Tests binary detection, command building, trace flag injection.
This is TDD - tests written before implementation.

Coverage Focus (60% of test suite):
- Binary detection (rustyclawd, claude-cli)
- Command building with trace flags
- Trace flag injection logic
- Path resolution
- Error handling
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from amplihack.launcher.claude_binary_manager import ClaudeBinaryManager, BinaryInfo


# =============================================================================
# Binary Detection Tests
# =============================================================================


def test_detect_native_binary_finds_rustyclawd():
    """Test detection of rustyclawd binary."""
    manager = ClaudeBinaryManager()

    with patch("amplihack.launcher.claude_binary_manager.shutil.which", return_value="/usr/local/bin/rustyclawd"):
        with patch("amplihack.launcher.claude_binary_manager.Path.exists", return_value=True):
            with patch("amplihack.launcher.claude_binary_manager.os.access", return_value=True):
                binary = manager.detect_native_binary()

                assert binary is not None
                assert binary.name == "rustyclawd"
                assert binary.path == Path("/usr/local/bin/rustyclawd")
                assert binary.supports_trace is True


def test_detect_native_binary_finds_claude_cli():
    """Test detection of claude-cli binary."""
    manager = ClaudeBinaryManager()

    with patch("amplihack.launcher.claude_binary_manager.shutil.which", side_effect=lambda x: "/usr/local/bin/claude" if x == "claude" else None):
        with patch("amplihack.launcher.claude_binary_manager.Path.exists", return_value=True):
            with patch("amplihack.launcher.claude_binary_manager.os.access", return_value=True):
                binary = manager.detect_native_binary()

                assert binary is not None
                assert binary.name == "claude"
                assert binary.path == Path("/usr/local/bin/claude")


def test_detect_native_binary_prefers_rustyclawd():
    """Test that rustyclawd is preferred over claude-cli."""
    manager = ClaudeBinaryManager()

    # Both binaries available
    def which_mock(name):
        if name == "rustyclawd":
            return "/usr/local/bin/rustyclawd"
        elif name == "claude":
            return "/usr/local/bin/claude"
        return None

    with patch("amplihack.launcher.claude_binary_manager.shutil.which", side_effect=which_mock):
        with patch("amplihack.launcher.claude_binary_manager.Path.exists", return_value=True):
            with patch("amplihack.launcher.claude_binary_manager.os.access", return_value=True):
                binary = manager.detect_native_binary()

                assert binary.name == "rustyclawd"


def test_detect_native_binary_returns_none_when_not_found():
    """Test that None is returned when no binary is found."""
    manager = ClaudeBinaryManager()

    with patch("shutil.which", return_value=None):
        binary = manager.detect_native_binary()

        assert binary is None


def test_detect_native_binary_validates_binary_exists():
    """Test that detection validates binary actually exists."""
    manager = ClaudeBinaryManager()

    with patch("shutil.which", return_value="/nonexistent/rustyclawd"):
        with patch("pathlib.Path.exists", return_value=False):
            binary = manager.detect_native_binary()

            assert binary is None


def test_detect_native_binary_validates_binary_executable():
    """Test that detection validates binary is executable."""
    manager = ClaudeBinaryManager()

    with patch("shutil.which", return_value="/tmp/rustyclawd"):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("os.access", return_value=False):
                binary = manager.detect_native_binary()

                assert binary is None


# =============================================================================
# BinaryInfo Tests
# =============================================================================


def test_binary_info_creation():
    """Test BinaryInfo dataclass creation."""
    binary = BinaryInfo(
        name="rustyclawd",
        path=Path("/usr/local/bin/rustyclawd"),
        version="0.1.0",
        supports_trace=True,
    )

    assert binary.name == "rustyclawd"
    assert binary.path == Path("/usr/local/bin/rustyclawd")
    assert binary.version == "0.1.0"
    assert binary.supports_trace is True


def test_binary_info_defaults():
    """Test BinaryInfo default values."""
    binary = BinaryInfo(name="claude", path=Path("/usr/local/bin/claude"))

    assert binary.version is None
    assert binary.supports_trace is False  # Conservative default


# =============================================================================
# Command Building Tests
# =============================================================================


def test_build_command_without_trace():
    """Test building command without trace flags."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(name="rustyclawd", path=Path("/usr/local/bin/rustyclawd"))

    cmd = manager.build_command(binary, enable_trace=False)

    assert cmd == ["/usr/local/bin/rustyclawd"]


def test_build_command_with_trace_enabled():
    """Test building command with trace flags."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(
        name="rustyclawd",
        path=Path("/usr/local/bin/rustyclawd"),
        supports_trace=True,
    )

    cmd = manager.build_command(binary, enable_trace=True, trace_file="/tmp/trace.jsonl")

    assert "/usr/local/bin/rustyclawd" in cmd
    assert "--trace" in cmd or "--log-file" in cmd
    # Exact flag format TBD in implementation
    if "--log-file" in cmd:
        idx = cmd.index("--log-file")
        assert cmd[idx + 1] == "/tmp/trace.jsonl"


def test_build_command_with_trace_unsupported_binary():
    """Test that trace flags are not added for unsupported binaries."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(
        name="claude",
        path=Path("/usr/local/bin/claude"),
        supports_trace=False,
    )

    cmd = manager.build_command(binary, enable_trace=True, trace_file="/tmp/trace.jsonl")

    # Should not include trace flags
    assert "--trace" not in cmd
    assert "--log-file" not in cmd


def test_build_command_preserves_additional_args():
    """Test that additional arguments are preserved."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(name="rustyclawd", path=Path("/usr/local/bin/rustyclawd"))

    additional_args = ["--model", "claude-3-sonnet", "--temperature", "0.7"]
    cmd = manager.build_command(binary, enable_trace=False, additional_args=additional_args)

    assert "/usr/local/bin/rustyclawd" in cmd
    assert "--model" in cmd
    assert "claude-3-sonnet" in cmd
    assert "--temperature" in cmd
    assert "0.7" in cmd


def test_build_command_trace_flags_before_additional_args():
    """Test that trace flags come before additional arguments."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(
        name="rustyclawd",
        path=Path("/usr/local/bin/rustyclawd"),
        supports_trace=True,
    )

    additional_args = ["--model", "claude-3-sonnet"]
    cmd = manager.build_command(
        binary, enable_trace=True, trace_file="/tmp/trace.jsonl", additional_args=additional_args
    )

    # Binary path should be first
    assert cmd[0] == "/usr/local/bin/rustyclawd"

    # Trace flags should come before additional args
    if "--log-file" in cmd:
        trace_idx = cmd.index("--log-file")
        model_idx = cmd.index("--model")
        assert trace_idx < model_idx


def test_build_command_handles_none_trace_file():
    """Test command building with trace enabled but no file specified."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(
        name="rustyclawd",
        path=Path("/usr/local/bin/rustyclawd"),
        supports_trace=True,
    )

    # Should use default trace file location
    cmd = manager.build_command(binary, enable_trace=True, trace_file=None)

    # Should either have default file or disable tracing
    assert "/usr/local/bin/rustyclawd" in cmd


# =============================================================================
# Version Detection Tests
# =============================================================================


def test_detect_binary_version_success():
    """Test successful version detection."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(name="rustyclawd", path=Path("/usr/local/bin/rustyclawd"))

    mock_result = Mock()
    mock_result.stdout = "rustyclawd 0.1.0\n"
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result):
        version = manager.detect_version(binary)

        assert version == "0.1.0"


def test_detect_binary_version_handles_failure():
    """Test version detection when command fails."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(name="rustyclawd", path=Path("/usr/local/bin/rustyclawd"))

    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
        version = manager.detect_version(binary)

        assert version is None


def test_detect_binary_version_handles_timeout():
    """Test version detection with timeout."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(name="rustyclawd", path=Path("/usr/local/bin/rustyclawd"))

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
        version = manager.detect_version(binary)

        assert version is None


def test_detect_binary_version_parses_various_formats():
    """Test version parsing handles various output formats."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(name="rustyclawd", path=Path("/usr/local/bin/rustyclawd"))

    test_cases = [
        ("rustyclawd 0.1.0", "0.1.0"),
        ("version: 1.2.3", "1.2.3"),
        ("v2.0.0-beta", "2.0.0-beta"),
        ("claude-cli version 0.5.0 (build 123)", "0.5.0"),
    ]

    for output, expected_version in test_cases:
        mock_result = Mock(stdout=output, returncode=0)
        with patch("subprocess.run", return_value=mock_result):
            version = manager.detect_version(binary)
            assert version == expected_version, f"Failed to parse: {output}"


# =============================================================================
# Error Handling Tests
# =============================================================================


def test_build_command_with_nonexistent_binary_path():
    """Test command building with nonexistent binary path - should still build command."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(name="invalid", path=Path("/nonexistent/binary"))

    # build_command doesn't validate path - it just builds the command list
    cmd = manager.build_command(binary, enable_trace=False)
    assert cmd == ["/nonexistent/binary"]


def test_build_command_with_invalid_trace_file_path():
    """Test command building with invalid trace file path."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(
        name="rustyclawd",
        path=Path("/usr/local/bin/rustyclawd"),
        supports_trace=True,
    )

    # Should handle gracefully or raise clear error
    with pytest.raises((ValueError, OSError)):
        manager.build_command(binary, enable_trace=True, trace_file="/\0invalid/path")


# =============================================================================
# Environment-Based Configuration Tests
# =============================================================================


def test_manager_respects_binary_path_env_variable(monkeypatch):
    """Test that manager respects CLAUDE_BINARY_PATH environment variable."""
    monkeypatch.setenv("CLAUDE_BINARY_PATH", "/custom/path/to/rustyclawd")

    manager = ClaudeBinaryManager()

    with patch("pathlib.Path.exists", return_value=True):
        with patch("os.access", return_value=True):
            binary = manager.detect_native_binary()

            assert binary.path == Path("/custom/path/to/rustyclawd")


def test_manager_prioritizes_env_over_path():
    """Test that environment variable overrides PATH search."""
    manager = ClaudeBinaryManager()

    with patch.dict(os.environ, {"CLAUDE_BINARY_PATH": "/custom/rustyclawd"}):
        with patch("shutil.which", return_value="/usr/local/bin/rustyclawd"):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("os.access", return_value=True):
                    binary = manager.detect_native_binary()

                    # Should use env variable, not PATH
                    assert str(binary.path) == "/custom/rustyclawd"


# =============================================================================
# Fallback Behavior Tests
# =============================================================================


def test_fallback_to_python_launcher_when_no_binary():
    """Test fallback to Python launcher when native binary not found."""
    manager = ClaudeBinaryManager()

    with patch("shutil.which", return_value=None):
        binary = manager.detect_native_binary()

        assert binary is None

        # Launcher should fall back to Python implementation
        # This is tested in launcher integration tests


def test_graceful_degradation_when_trace_unsupported():
    """Test graceful degradation when trace is requested but unsupported."""
    manager = ClaudeBinaryManager()
    binary = BinaryInfo(
        name="claude",
        path=Path("/usr/local/bin/claude"),
        supports_trace=False,
    )

    # Should not raise error, just omit trace flags
    cmd = manager.build_command(binary, enable_trace=True, trace_file="/tmp/trace.jsonl")

    assert "/usr/local/bin/claude" in cmd
    assert "--trace" not in cmd


# =============================================================================
# Platform-Specific Tests
# =============================================================================


@pytest.mark.skipif(os.name != "posix", reason="Unix-specific test")
def test_detect_binary_on_unix():
    """Test binary detection on Unix-like systems."""
    manager = ClaudeBinaryManager()

    with patch("amplihack.launcher.claude_binary_manager.shutil.which", return_value="/usr/local/bin/rustyclawd"):
        with patch("amplihack.launcher.claude_binary_manager.Path.exists", return_value=True):
            with patch("amplihack.launcher.claude_binary_manager.os.access", return_value=True):
                binary = manager.detect_native_binary()

                assert binary is not None
                assert str(binary.path).startswith("/")


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
def test_detect_binary_on_windows():
    """Test binary detection on Windows."""
    manager = ClaudeBinaryManager()

    with patch("amplihack.launcher.claude_binary_manager.shutil.which", return_value=r"C:\Program Files\Anthropic\rustyclawd.exe"):
        with patch("amplihack.launcher.claude_binary_manager.Path.exists", return_value=True):
            with patch("amplihack.launcher.claude_binary_manager.os.access", return_value=True):
                binary = manager.detect_native_binary()

                assert binary is not None
                assert ".exe" in str(binary.path).lower()


# =============================================================================
# Caching Tests
# =============================================================================


def test_binary_detection_caching():
    """Test that binary detection results are cached."""
    manager = ClaudeBinaryManager()

    with patch("amplihack.launcher.claude_binary_manager.shutil.which", return_value="/usr/local/bin/rustyclawd") as mock_which:
        with patch("amplihack.launcher.claude_binary_manager.Path.exists", return_value=True):
            with patch("amplihack.launcher.claude_binary_manager.os.access", return_value=True):
                # First call
                binary1 = manager.detect_native_binary()
                # Second call
                binary2 = manager.detect_native_binary()

                # Should only call which once due to caching
                assert mock_which.call_count == 1
                assert binary1 == binary2


def test_cache_invalidation():
    """Test cache invalidation when binary changes."""
    manager = ClaudeBinaryManager()

    with patch("amplihack.launcher.claude_binary_manager.shutil.which", return_value="/usr/local/bin/rustyclawd"):
        with patch("amplihack.launcher.claude_binary_manager.Path.exists", return_value=True):
            with patch("amplihack.launcher.claude_binary_manager.os.access", return_value=True):
                binary1 = manager.detect_native_binary()

    # Simulate binary change
    manager.invalidate_cache()

    with patch("amplihack.launcher.claude_binary_manager.shutil.which", return_value="/usr/local/bin/claude"):
        with patch("amplihack.launcher.claude_binary_manager.Path.exists", return_value=True):
            with patch("amplihack.launcher.claude_binary_manager.os.access", return_value=True):
                binary2 = manager.detect_native_binary()

                assert binary1.name != binary2.name
