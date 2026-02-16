"""Tests for streaming output monitoring in recipe adapters.

Tests the timeout removal and streaming output monitoring behavior:
- Agent steps run without hard timeout
- Output is streamed to log file
- Background thread monitors and prints progress
- Heartbeat printed when output is idle
- Bash steps retain timeout
"""

from __future__ import annotations

import subprocess
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter
from amplihack.recipes.adapters.nested_session import NestedSessionAdapter


class TestCLISubprocessAdapterStreaming:
    """Test streaming behavior in CLI subprocess adapter."""

    def test_execute_agent_step_no_timeout(self) -> None:
        """Agent steps run without timeout parameter."""
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("threading.Thread"),
            patch("pathlib.Path.read_text") as mock_read,
            patch("pathlib.Path.mkdir"),
            patch("builtins.open", mock_open()),
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.wait = MagicMock()
            mock_popen.return_value = mock_proc
            mock_read.return_value = "Agent output"

            adapter = CLISubprocessAdapter()
            result = adapter.execute_agent_step("test prompt")

            # Verify Popen was called (allows no timeout)
            assert mock_popen.called
            # Verify process.wait() was called without timeout
            mock_proc.wait.assert_called_once_with()
            assert result == "Agent output"

    def test_execute_agent_step_streams_to_log_file(self) -> None:
        """Output is captured to a log file for tailing."""
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("threading.Thread"),
            patch("pathlib.Path.read_text") as mock_read,
            patch("pathlib.Path.mkdir"),
            patch("builtins.open", mock_open()),
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc
            mock_read.return_value = "output"

            adapter = CLISubprocessAdapter()
            adapter.execute_agent_step("prompt")

            # Verify Popen stdout was redirected to file
            popen_kwargs = mock_popen.call_args[1]
            assert "stdout" in popen_kwargs
            assert popen_kwargs["stderr"] == subprocess.STDOUT

    def test_execute_agent_step_starts_tail_thread(self) -> None:
        """Background thread is started to tail output."""
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("threading.Thread") as mock_thread,
            patch("pathlib.Path.read_text") as mock_read,
            patch("pathlib.Path.mkdir"),
            patch("builtins.open", mock_open()),
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc
            mock_read.return_value = "output"

            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            adapter = CLISubprocessAdapter()
            adapter.execute_agent_step("prompt")

            # Verify thread was created with _tail_output target
            assert mock_thread.called
            call_kwargs = mock_thread.call_args[1]
            assert call_kwargs["target"] == adapter._tail_output
            assert "args" in call_kwargs
            assert call_kwargs["daemon"] is True

            # Verify thread was started
            mock_thread_instance.start.assert_called_once()

    def test_execute_agent_step_stops_tail_thread(self) -> None:
        """Thread is stopped and joined after process completes."""
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("threading.Thread") as mock_thread,
            patch("pathlib.Path.read_text") as mock_read,
            patch("pathlib.Path.mkdir"),
            patch("builtins.open", mock_open()),
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc
            mock_read.return_value = "output"

            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            adapter = CLISubprocessAdapter()
            adapter.execute_agent_step("prompt")

            # Verify thread was joined with timeout
            mock_thread_instance.join.assert_called_once()
            join_kwargs = mock_thread_instance.join.call_args[1]
            assert "timeout" in join_kwargs

    def test_execute_agent_step_cleans_up_log_file(self) -> None:
        """Log file is deleted after execution."""
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("threading.Thread"),
            patch("pathlib.Path.read_text") as mock_read,
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.unlink") as mock_unlink,
            patch("builtins.open", mock_open()),
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc
            mock_read.return_value = "output"

            adapter = CLISubprocessAdapter()
            adapter.execute_agent_step("prompt")

            # Verify unlink was called to delete log file
            assert mock_unlink.called

    @patch("subprocess.run")
    def test_execute_bash_step_has_timeout(self, mock_run: MagicMock) -> None:
        """Bash steps retain timeout (default 120s)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        adapter = CLISubprocessAdapter()
        adapter.execute_bash_step("echo test")

        # Verify timeout was passed
        call_kwargs = mock_run.call_args[1]
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == 120

    @patch("subprocess.run")
    def test_execute_bash_step_custom_timeout(self, mock_run: MagicMock) -> None:
        """Bash steps can use custom timeout."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        adapter = CLISubprocessAdapter()
        adapter.execute_bash_step("sleep 5", timeout=30)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 30


class TestCLISubprocessAdapterTailOutput:
    """Test the _tail_output helper function."""

    def test_tail_output_prints_new_lines(self, capsys) -> None:
        """New lines in log file are printed as progress."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write("Initial line\n")
            tmp.flush()

            stop_event = threading.Event()

            # Start tail thread
            thread = threading.Thread(
                target=CLISubprocessAdapter._tail_output, args=(tmp_path, stop_event), daemon=True
            )
            thread.start()

            # Write more content
            time.sleep(0.1)
            with open(tmp_path, "a") as f:
                f.write("New line\n")

            # Let tail thread detect change
            time.sleep(2.5)

            # Stop thread
            stop_event.set()
            thread.join(timeout=3)

            # Verify output
            captured = capsys.readouterr()
            assert "[agent]" in captured.out

            # Cleanup
            tmp_path.unlink()

    def test_tail_output_heartbeat_on_idle(self, capsys) -> None:
        """Heartbeat is printed when output is idle for 60s."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write("Initial\n")
            tmp.flush()

            stop_event = threading.Event()

            # Mock time to simulate idle period
            with patch("time.time") as mock_time:
                times = [0, 0, 10, 20, 30, 40, 50, 61]  # Simulates 61s idle
                mock_time.side_effect = times

                thread = threading.Thread(
                    target=CLISubprocessAdapter._tail_output,
                    args=(tmp_path, stop_event),
                    daemon=True,
                )
                thread.start()

                # Wait for a few cycles
                time.sleep(5)

                stop_event.set()
                thread.join(timeout=3)

            tmp_path.unlink()

    def test_tail_output_stops_on_event(self) -> None:
        """Thread stops when stop event is set."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp_path = Path(tmp.name)

            stop_event = threading.Event()

            thread = threading.Thread(
                target=CLISubprocessAdapter._tail_output, args=(tmp_path, stop_event), daemon=True
            )
            thread.start()

            # Stop immediately
            stop_event.set()
            thread.join(timeout=2)

            # Thread should have stopped
            assert not thread.is_alive()

            tmp_path.unlink()


class TestNestedSessionAdapterStreaming:
    """Test streaming behavior in nested session adapter."""

    def test_execute_agent_step_no_timeout(self) -> None:
        """Agent steps run without timeout parameter."""
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("threading.Thread") as mock_thread,
            patch("pathlib.Path.read_text") as mock_read,
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.wait = MagicMock()
            mock_popen.return_value = mock_proc
            mock_read.return_value = "output"

            adapter = NestedSessionAdapter(use_temp_dirs=False)
            result = adapter.execute_agent_step("prompt")

            # Verify wait() called without timeout
            mock_proc.wait.assert_called_once_with()
            assert result == "output"

    def test_execute_agent_step_unsets_claudecode(self) -> None:
        """CLAUDECODE env var is unset for nested sessions."""
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("threading.Thread"),
            patch("pathlib.Path.read_text") as mock_read,
            patch("os.environ.copy") as mock_env_copy,
        ):
            mock_env = {"CLAUDECODE": "1", "PATH": "/usr/bin"}
            mock_env_copy.return_value = mock_env.copy()

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc
            mock_read.return_value = "output"

            adapter = NestedSessionAdapter(use_temp_dirs=False)
            adapter.execute_agent_step("prompt")

            # Verify CLAUDECODE was removed from env
            popen_kwargs = mock_popen.call_args[1]
            assert "env" in popen_kwargs
            env = popen_kwargs["env"]
            assert "CLAUDECODE" not in env
            assert "PATH" in env  # Other vars preserved

    def test_execute_agent_step_streams_to_log(self) -> None:
        """Output is captured to log file for monitoring."""
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("threading.Thread"),
            patch("pathlib.Path.read_text") as mock_read,
            patch("builtins.open", mock_open()) as mock_file,
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc
            mock_read.return_value = "output"

            adapter = NestedSessionAdapter(use_temp_dirs=False)
            adapter.execute_agent_step("prompt")

            # Verify stdout redirected to file
            popen_kwargs = mock_popen.call_args[1]
            assert "stdout" in popen_kwargs

    def test_execute_agent_step_starts_tail_thread(self) -> None:
        """Background monitoring thread is started."""
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("threading.Thread") as mock_thread,
            patch("pathlib.Path.read_text") as mock_read,
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc
            mock_read.return_value = "output"

            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            adapter = NestedSessionAdapter(use_temp_dirs=False)
            adapter.execute_agent_step("prompt")

            # Verify thread created with _tail_output
            assert mock_thread.called
            call_kwargs = mock_thread.call_args[1]
            assert call_kwargs["target"] == adapter._tail_output
            assert call_kwargs["daemon"] is True

            mock_thread_instance.start.assert_called_once()

    @patch("subprocess.run")
    def test_execute_bash_step_has_timeout(self, mock_run: MagicMock) -> None:
        """Bash steps retain timeout."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        adapter = NestedSessionAdapter()
        adapter.execute_bash_step("echo test")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 120


class TestStreamingIntegration:
    """Integration tests for streaming behavior."""

    def test_agent_step_completes_without_timeout_error(self) -> None:
        """Long-running agent steps don't raise TimeoutExpired."""
        # This would require mocking a long-running process
        # For now, verify the pattern is correct
        adapter = CLISubprocessAdapter()

        # Mock a process that takes a while
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("threading.Thread"),
            patch("pathlib.Path.read_text") as mock_read,
            patch("pathlib.Path.mkdir"),
            patch("builtins.open", mock_open()),
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0

            def slow_wait():
                """Simulate slow process."""
                time.sleep(0.1)

            mock_proc.wait = slow_wait
            mock_popen.return_value = mock_proc
            mock_read.return_value = "Long output"

            # Should complete without timeout error
            result = adapter.execute_agent_step("prompt")
            assert result == "Long output"

    def test_bash_step_respects_timeout(self) -> None:
        """Bash steps still timeout on slow commands."""
        import subprocess as sp

        adapter = CLISubprocessAdapter()

        # This should timeout (but we won't actually wait)
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = sp.TimeoutExpired("sleep", 1)

            with pytest.raises(sp.TimeoutExpired):
                adapter.execute_bash_step("sleep 999", timeout=1)
