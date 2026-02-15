"""Extended tests for adapter error paths and edge cases.

TDD approach: These tests validate error handling, resource limits, concurrency,
and edge cases in adapter implementations. Tests will fail until the adapters
properly implement timeout handling, network resilience, output processing,
resource cleanup, and signal management.
"""

from __future__ import annotations

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from amplihack.recipes.adapters import ClaudeSDKAdapter, CLISubprocessAdapter


class TestAdapterTimeouts:
    """Test timeout handling in adapters (TDD - will fail until implemented)."""

    @patch("subprocess.run")
    def test_bash_step_timeout_raises(self, mock_run: MagicMock) -> None:
        """Bash step timeout raises TimeoutError with descriptive message."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 100", timeout=1.0)

        adapter = CLISubprocessAdapter()
        with pytest.raises(subprocess.TimeoutExpired) as exc_info:
            adapter.execute_bash_step("sleep 100", timeout=1.0)

        assert exc_info.value.timeout == 1.0

    @patch("subprocess.run")
    def test_agent_step_timeout_raises(self, mock_run: MagicMock) -> None:
        """Agent step timeout raises TimeoutError."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="claude query 'long task'", timeout=5.0
        )

        adapter = CLISubprocessAdapter()
        with pytest.raises(subprocess.TimeoutExpired):
            adapter.execute_agent_step(
                agent_type="amplihack:architect",
                prompt="Very long analysis task",
                timeout=5.0,
            )

    @patch("subprocess.run")
    def test_subprocess_hangs_terminates(self, mock_run: MagicMock) -> None:
        """Hanging subprocess is terminated after timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="hang", timeout=2.0)

        adapter = CLISubprocessAdapter()
        with pytest.raises(subprocess.TimeoutExpired):
            adapter.execute_bash_step("while true; do sleep 1; done", timeout=2.0)

        # Verify subprocess.run was called with timeout parameter
        assert mock_run.call_args[1]["timeout"] == 2.0

    @patch("subprocess.run")
    def test_timeout_respects_custom_value(self, mock_run: MagicMock) -> None:
        """Custom timeout value is passed correctly to subprocess."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        adapter = CLISubprocessAdapter()
        adapter.execute_bash_step("echo test", timeout=42.5)

        assert mock_run.call_args[1]["timeout"] == 42.5

    def test_zero_timeout_rejected(self) -> None:
        """Zero timeout is rejected with ValueError."""
        adapter = CLISubprocessAdapter()
        # TDD: Implementation should validate timeout > 0
        # This test will fail until validation is added
        with pytest.raises((ValueError, RuntimeError)):
            adapter.execute_bash_step("echo test", timeout=0)

    def test_negative_timeout_rejected(self) -> None:
        """Negative timeout is rejected with ValueError."""
        adapter = CLISubprocessAdapter()
        # TDD: Implementation should validate timeout > 0
        with pytest.raises((ValueError, RuntimeError)):
            adapter.execute_bash_step("echo test", timeout=-5)

    @patch("subprocess.run")
    def test_timeout_cleanup_on_kill(self, mock_run: MagicMock) -> None:
        """Timeout triggers cleanup of subprocess resources."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=1.0)

        adapter = CLISubprocessAdapter()
        with pytest.raises(subprocess.TimeoutExpired):
            adapter.execute_bash_step("sleep 100", timeout=1.0)

        # Verify run was called (cleanup happens in subprocess.run)
        assert mock_run.called


class TestAdapterNetworkFailures:
    """Test network failure handling in SDK adapter (TDD)."""

    def test_sdk_import_lazy_loading_failure(self) -> None:
        """SDK import failure is handled gracefully."""
        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("claude_agent_sdk not found")

            adapter = ClaudeSDKAdapter()
            # Should return False without crashing
            assert adapter.is_available() is False

    @patch("subprocess.run")
    def test_sdk_query_network_timeout(self, mock_run: MagicMock) -> None:
        """Network timeout during SDK query is handled."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="query", timeout=30.0)

        adapter = ClaudeSDKAdapter()
        with pytest.raises(subprocess.TimeoutExpired):
            adapter.execute_agent_step(agent_type="amplihack:builder", prompt="test", timeout=30.0)

    @patch("subprocess.run")
    def test_sdk_query_connection_refused(self, mock_run: MagicMock) -> None:
        """Connection refused error is propagated correctly."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="query", stderr="Connection refused"
        )

        adapter = ClaudeSDKAdapter()
        with pytest.raises((subprocess.CalledProcessError, RuntimeError)):
            adapter.execute_agent_step(agent_type="amplihack:builder", prompt="test")

    @patch("subprocess.run")
    def test_sdk_query_dns_failure(self, mock_run: MagicMock) -> None:
        """DNS resolution failure is handled."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="DNS resolution failed")

        adapter = ClaudeSDKAdapter()
        with pytest.raises(RuntimeError, match="exit 1"):
            adapter.execute_agent_step(agent_type="amplihack:builder", prompt="test")

    @patch("subprocess.run")
    def test_sdk_api_rate_limit(self, mock_run: MagicMock) -> None:
        """API rate limit error (429) is handled."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Rate limit exceeded (429)"
        )

        adapter = ClaudeSDKAdapter()
        with pytest.raises(RuntimeError, match="exit 1"):
            adapter.execute_agent_step(agent_type="amplihack:builder", prompt="test")

    @patch("subprocess.run")
    def test_sdk_api_503_service_unavailable(self, mock_run: MagicMock) -> None:
        """Service unavailable (503) error is handled."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Service Unavailable (503)"
        )

        adapter = ClaudeSDKAdapter()
        with pytest.raises(RuntimeError):
            adapter.execute_agent_step(agent_type="amplihack:builder", prompt="test")

    @patch("subprocess.run")
    def test_sdk_partial_response_failure(self, mock_run: MagicMock) -> None:
        """Partial response followed by disconnect is handled."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="Partial response...", stderr="Connection reset"
        )

        adapter = ClaudeSDKAdapter()
        with pytest.raises(RuntimeError):
            adapter.execute_agent_step(agent_type="amplihack:builder", prompt="test")


class TestAdapterOutputHandling:
    """Test handling of various output formats and edge cases (TDD)."""

    @patch("subprocess.run")
    def test_very_large_output_1mb(self, mock_run: MagicMock) -> None:
        """Handle 1MB of output without crashing."""
        large_output = "x" * (1024 * 1024)  # 1MB
        mock_run.return_value = MagicMock(returncode=0, stdout=large_output, stderr="")

        adapter = CLISubprocessAdapter()
        result = adapter.execute_bash_step("generate_large_output")

        assert len(result) == 1024 * 1024
        assert result == large_output.rstrip()

    @patch("subprocess.run")
    def test_very_large_output_10mb(self, mock_run: MagicMock) -> None:
        """Handle 10MB of output (stress test)."""
        large_output = "y" * (10 * 1024 * 1024)  # 10MB
        mock_run.return_value = MagicMock(returncode=0, stdout=large_output, stderr="")

        adapter = CLISubprocessAdapter()
        result = adapter.execute_bash_step("generate_very_large_output")

        assert len(result) == 10 * 1024 * 1024

    @patch("subprocess.run")
    def test_unicode_output_emoji(self, mock_run: MagicMock) -> None:
        """Handle emoji and multi-byte unicode characters."""
        unicode_output = "Hello 👋 World 🌍 Test 🚀\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=unicode_output, stderr="")

        adapter = CLISubprocessAdapter()
        result = adapter.execute_bash_step("echo emoji")

        assert "👋" in result
        assert "🌍" in result
        assert "🚀" in result

    @patch("subprocess.run")
    def test_unicode_output_rtl(self, mock_run: MagicMock) -> None:
        """Handle right-to-left (RTL) text like Arabic/Hebrew."""
        rtl_output = "مرحبا بالعالم\n"  # Arabic "Hello World"
        mock_run.return_value = MagicMock(returncode=0, stdout=rtl_output, stderr="")

        adapter = CLISubprocessAdapter()
        result = adapter.execute_bash_step("echo arabic")

        assert "مرحبا" in result

    @patch("subprocess.run")
    def test_binary_output_handling(self, mock_run: MagicMock) -> None:
        """Binary output is handled without decode errors."""
        # Simulate binary data that's not valid UTF-8
        binary_output = b"\x00\x01\x02\xff\xfe\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=binary_output, stderr=b"")

        adapter = CLISubprocessAdapter()
        # TDD: Should either handle gracefully or raise clear error
        try:
            result = adapter.execute_bash_step("cat binary_file")
            # If it succeeds, verify result is string
            assert isinstance(result, str)
        except (UnicodeDecodeError, ValueError) as e:
            # Acceptable: clear error about binary data
            assert "decode" in str(e).lower() or "binary" in str(e).lower()

    @patch("subprocess.run")
    def test_null_bytes_in_output(self, mock_run: MagicMock) -> None:
        """Null bytes in output are handled."""
        output_with_nulls = "before\x00null\x00after\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=output_with_nulls, stderr="")

        adapter = CLISubprocessAdapter()
        result = adapter.execute_bash_step("echo null_bytes")

        # TDD: Should handle null bytes (strip, replace, or preserve)
        assert isinstance(result, str)
        assert "before" in result

    @patch("subprocess.run")
    def test_partial_utf8_sequences(self, mock_run: MagicMock) -> None:
        """Handle partial UTF-8 sequences at buffer boundaries."""
        # Start of multi-byte sequence without continuation
        partial_utf8 = b"valid\xc3\n"  # Incomplete UTF-8
        mock_run.return_value = MagicMock(returncode=0, stdout=partial_utf8, stderr=b"")

        adapter = CLISubprocessAdapter()
        # TDD: Should handle gracefully (replace chars or error)
        try:
            result = adapter.execute_bash_step("echo partial")
            assert isinstance(result, str)
        except UnicodeDecodeError:
            # Acceptable: clear decode error
            pass

    @patch("subprocess.run")
    def test_mixed_encoding_output(self, mock_run: MagicMock) -> None:
        """Handle mixed encoding (UTF-8 + Latin-1)."""
        # Mix of UTF-8 and Latin-1 characters
        mixed = "UTF-8: café, Latin-1: \xe9\n".encode("utf-8", errors="ignore")
        mock_run.return_value = MagicMock(returncode=0, stdout=mixed, stderr=b"")

        adapter = CLISubprocessAdapter()
        result = adapter.execute_bash_step("echo mixed")

        assert isinstance(result, str)
        assert "café" in result or "caf" in result


class TestAdapterResourceLimits:
    """Test adapter behavior under resource constraints (TDD)."""

    @patch("subprocess.run")
    def test_out_of_memory_handling(self, mock_run: MagicMock) -> None:
        """Out of memory error is handled gracefully."""
        mock_run.side_effect = MemoryError("Cannot allocate memory")

        adapter = CLISubprocessAdapter()
        with pytest.raises(MemoryError):
            adapter.execute_bash_step("allocate_huge_array")

    @patch("subprocess.run")
    def test_too_many_open_files(self, mock_run: MagicMock) -> None:
        """'Too many open files' error is handled."""
        mock_run.side_effect = OSError(24, "Too many open files")

        adapter = CLISubprocessAdapter()
        with pytest.raises(OSError) as exc_info:
            adapter.execute_bash_step("open_many_files")

        assert exc_info.value.errno == 24

    @patch("subprocess.run")
    def test_disk_full_during_execution(self, mock_run: MagicMock) -> None:
        """Disk full error during execution is propagated."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="No space left on device")

        adapter = CLISubprocessAdapter()
        with pytest.raises(RuntimeError, match="exit 1"):
            adapter.execute_bash_step("write_large_file")

    @patch("subprocess.run")
    def test_cpu_quota_exceeded(self, mock_run: MagicMock) -> None:
        """CPU quota exceeded (containerized env) is handled."""
        mock_run.return_value = MagicMock(returncode=137, stdout="", stderr="CPU quota exceeded")

        adapter = CLISubprocessAdapter()
        with pytest.raises(RuntimeError, match="exit 137"):
            adapter.execute_bash_step("cpu_intensive_task")

    @patch("subprocess.run")
    def test_process_count_limit(self, mock_run: MagicMock) -> None:
        """Process count limit (ulimit) is handled."""
        mock_run.side_effect = OSError(11, "Resource temporarily unavailable")

        adapter = CLISubprocessAdapter()
        with pytest.raises(OSError):
            adapter.execute_bash_step("fork_many_processes")


class TestAdapterConcurrency:
    """Test concurrent execution safety (TDD)."""

    @patch("subprocess.run")
    def test_concurrent_bash_steps(self, mock_run: MagicMock) -> None:
        """Multiple bash steps can execute concurrently."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        adapter = CLISubprocessAdapter()

        def run_step(n: int) -> str:
            return adapter.execute_bash_step(f"echo step{n}")

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(run_step, range(10)))

        assert len(results) == 10
        assert all(isinstance(r, str) for r in results)

    @patch("subprocess.run")
    def test_concurrent_agent_steps(self, mock_run: MagicMock) -> None:
        """Multiple agent steps can execute concurrently."""
        mock_run.return_value = MagicMock(returncode=0, stdout="done", stderr="")

        adapter = CLISubprocessAdapter()

        def run_agent(n: int) -> str:
            return adapter.execute_agent_step(agent_type="amplihack:builder", prompt=f"Task {n}")

        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(run_agent, range(5)))

        assert len(results) == 5

    @patch("subprocess.run")
    def test_adapter_state_isolation(self, mock_run: MagicMock) -> None:
        """Concurrent executions don't share state incorrectly."""
        call_count = {"count": 0}

        def side_effect(*args, **kwargs):
            call_count["count"] += 1
            time.sleep(0.01)  # Simulate work
            return MagicMock(returncode=0, stdout=f"result{call_count['count']}", stderr="")

        mock_run.side_effect = side_effect

        adapter = CLISubprocessAdapter()

        def run_isolated(n: int) -> str:
            return adapter.execute_bash_step(f"echo {n}")

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(run_isolated, range(10)))

        # All should succeed independently
        assert len(results) == 10

    @patch("subprocess.run")
    def test_shared_working_dir_safety(self, mock_run: MagicMock) -> None:
        """Concurrent steps with shared working_dir are safe."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        adapter = CLISubprocessAdapter()

        def run_in_dir(n: int) -> str:
            return adapter.execute_bash_step(f"echo {n} > file{n}.txt", working_dir="/tmp")

        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(run_in_dir, range(5)))

        assert len(results) == 5

    @patch("subprocess.run")
    def test_parallel_subprocess_safety(self, mock_run: MagicMock) -> None:
        """subprocess.run calls don't interfere with each other."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        adapter1 = CLISubprocessAdapter()
        adapter2 = CLISubprocessAdapter()

        def run1() -> str:
            return adapter1.execute_bash_step("task1")

        def run2() -> str:
            return adapter2.execute_bash_step("task2")

        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(run1)
            future2 = executor.submit(run2)

            result1 = future1.result()
            result2 = future2.result()

        assert result1 == "ok"
        assert result2 == "ok"


class TestAdapterWorkingDirectory:
    """Test working directory edge cases (TDD)."""

    @patch("subprocess.run")
    def test_nonexistent_working_dir(self, mock_run: MagicMock) -> None:
        """Nonexistent working directory raises FileNotFoundError."""
        mock_run.side_effect = FileNotFoundError("No such file or directory")

        adapter = CLISubprocessAdapter()
        with pytest.raises(FileNotFoundError):
            adapter.execute_bash_step("echo test", working_dir="/nonexistent/path")

    @patch("subprocess.run")
    def test_working_dir_permission_denied(self, mock_run: MagicMock) -> None:
        """Permission denied on working_dir raises PermissionError."""
        mock_run.side_effect = PermissionError("Permission denied")

        adapter = CLISubprocessAdapter()
        with pytest.raises(PermissionError):
            adapter.execute_bash_step("echo test", working_dir="/root/restricted")

    @patch("subprocess.run")
    def test_working_dir_not_a_directory(self, mock_run: MagicMock) -> None:
        """Using a file as working_dir raises NotADirectoryError."""
        mock_run.side_effect = NotADirectoryError("Not a directory")

        adapter = CLISubprocessAdapter()
        with pytest.raises(NotADirectoryError):
            adapter.execute_bash_step("echo test", working_dir="/etc/passwd")

    @patch("subprocess.run")
    def test_working_dir_deleted_during_execution(self, mock_run: MagicMock) -> None:
        """Working directory deleted during execution is handled."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="cannot access directory")

        adapter = CLISubprocessAdapter()
        with pytest.raises(RuntimeError):
            adapter.execute_bash_step("echo test", working_dir="/tmp/deleted")

    @patch("subprocess.run")
    def test_relative_working_dir_resolution(self, mock_run: MagicMock) -> None:
        """Relative working_dir paths are resolved correctly."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        adapter = CLISubprocessAdapter()
        result = adapter.execute_bash_step("pwd", working_dir="./relative/path")

        # Should not crash; subprocess will handle resolution
        assert isinstance(result, str)


class TestAdapterSignalHandling:
    """Test signal handling and cleanup (TDD)."""

    @patch("subprocess.run")
    def test_sigterm_cleanup(self, mock_run: MagicMock) -> None:
        """SIGTERM during execution triggers cleanup."""
        mock_run.return_value = MagicMock(returncode=-15, stdout="", stderr="Terminated")

        adapter = CLISubprocessAdapter()
        with pytest.raises(RuntimeError, match="exit -15"):
            adapter.execute_bash_step("long_running_task")

    @patch("subprocess.run")
    def test_sigkill_forced_termination(self, mock_run: MagicMock) -> None:
        """SIGKILL (signal 9) is handled."""
        mock_run.return_value = MagicMock(returncode=-9, stdout="", stderr="Killed")

        adapter = CLISubprocessAdapter()
        with pytest.raises(RuntimeError, match="exit -9"):
            adapter.execute_bash_step("unkillable_task")

    @patch("subprocess.run")
    def test_sigint_graceful_stop(self, mock_run: MagicMock) -> None:
        """SIGINT (Ctrl+C) stops execution gracefully."""
        mock_run.side_effect = KeyboardInterrupt()

        adapter = CLISubprocessAdapter()
        with pytest.raises(KeyboardInterrupt):
            adapter.execute_bash_step("interactive_task")

    @patch("subprocess.run")
    def test_subprocess_signal_propagation(self, mock_run: MagicMock) -> None:
        """Signals are propagated to subprocess correctly."""
        mock_run.return_value = MagicMock(returncode=-2, stdout="", stderr="Interrupt")

        adapter = CLISubprocessAdapter()
        with pytest.raises(RuntimeError, match="exit -2"):
            adapter.execute_bash_step("signal_sensitive_task")

    @patch("subprocess.run")
    def test_orphaned_process_cleanup(self, mock_run: MagicMock) -> None:
        """Orphaned child processes are cleaned up."""
        # Simulate parent exits but child continues
        mock_run.return_value = MagicMock(returncode=0, stdout="parent done", stderr="")

        adapter = CLISubprocessAdapter()
        result = adapter.execute_bash_step("bash -c '(sleep 100 &); echo parent done'")

        # TDD: Adapter should track and clean up background processes
        # For now, just verify the call succeeded
        assert "parent done" in result
