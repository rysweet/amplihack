#!/usr/bin/env python3
"""WS1: Subordinate Session Log Visibility — Failing Tests.

Tests that subordinate session logs are streamed to the parent terminal
in real-time with per-workstream prefixes. These tests define the contract
for the WS1 implementation and FAIL until the implementation is complete.

Coverage:
  - _stdout_lock: threading.Lock on ParallelOrchestrator
  - _tail_threads: dict tracking per-workstream daemon threads
  - _stdout_write(): thread-safe stdout helper
  - _tail_output(): daemon thread that tees pipe → log file + prefixed stdout
  - launch(): uses subprocess.PIPE (not log file handle) for stdout
  - launch(): starts a daemon tailing thread per workstream
  - monitor(): uses _stdout_write() for all stdout writes (lock coverage)
  - MAX_LOG_BYTES: log size cap to prevent /tmp exhaustion
"""

import io
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator import ParallelOrchestrator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_orchestrator(tmp_path: Path) -> ParallelOrchestrator:
    """Create an orchestrator with a known temp directory."""
    return ParallelOrchestrator(
        repo_url="https://github.com/test/repo",
        tmp_base=str(tmp_path),
    )


# ---------------------------------------------------------------------------
# 1. _stdout_lock: class-level threading.Lock
# ---------------------------------------------------------------------------


class TestStdoutLock:
    """ParallelOrchestrator must have a threading.Lock for atomic stdout writes."""

    def test_stdout_lock_exists(self, tmp_path):
        """_stdout_lock attribute must exist on orchestrator instance."""
        orc = make_orchestrator(tmp_path)
        assert hasattr(orc, "_stdout_lock"), (
            "ParallelOrchestrator is missing '_stdout_lock' attribute. "
            "Add '_stdout_lock = threading.Lock()' to __init__."
        )

    def test_stdout_lock_is_threading_lock(self, tmp_path):
        """_stdout_lock must be a real threading.Lock (or RLock)."""
        orc = make_orchestrator(tmp_path)
        lock = orc._stdout_lock
        # A Lock has acquire() and release() methods
        assert hasattr(lock, "acquire"), "_stdout_lock must have acquire() method"
        assert hasattr(lock, "release"), "_stdout_lock must have release() method"
        assert callable(lock.acquire), "_stdout_lock.acquire must be callable"

    def test_stdout_lock_is_acquirable(self, tmp_path):
        """_stdout_lock must be acquirable and releasable."""
        orc = make_orchestrator(tmp_path)
        # Should not raise
        acquired = orc._stdout_lock.acquire(blocking=False)
        assert acquired, "_stdout_lock should be acquirable (not already held)"
        orc._stdout_lock.release()

    def test_multiple_instances_have_independent_locks(self, tmp_path):
        """Each orchestrator instance must have its own lock (not a class-level shared lock)."""
        orc1 = make_orchestrator(tmp_path / "a")
        orc2 = make_orchestrator(tmp_path / "b")
        # Acquire lock on orc1 — orc2's lock should remain free
        orc1._stdout_lock.acquire()
        try:
            orc2_acquired = orc2._stdout_lock.acquire(blocking=False)
            assert orc2_acquired, "orc2._stdout_lock should be independent of orc1._stdout_lock"
            orc2._stdout_lock.release()
        finally:
            orc1._stdout_lock.release()


# ---------------------------------------------------------------------------
# 2. _tail_threads: per-workstream thread tracking dict
# ---------------------------------------------------------------------------


class TestTailThreads:
    """ParallelOrchestrator must track tailing daemon threads per workstream."""

    def test_tail_threads_exists(self, tmp_path):
        """_tail_threads attribute must exist on orchestrator instance."""
        orc = make_orchestrator(tmp_path)
        assert hasattr(orc, "_tail_threads"), (
            "ParallelOrchestrator is missing '_tail_threads' attribute. "
            "Add '_tail_threads: dict[int, threading.Thread] = {}' to __init__."
        )

    def test_tail_threads_is_dict(self, tmp_path):
        """_tail_threads must be a dict (mapping issue_id → thread)."""
        orc = make_orchestrator(tmp_path)
        assert isinstance(orc._tail_threads, dict), (
            f"_tail_threads must be a dict, got {type(orc._tail_threads).__name__}"
        )

    def test_tail_threads_starts_empty(self, tmp_path):
        """_tail_threads must start empty before any workstream is launched."""
        orc = make_orchestrator(tmp_path)
        assert len(orc._tail_threads) == 0, (
            f"_tail_threads should be empty on init, got {orc._tail_threads}"
        )


# ---------------------------------------------------------------------------
# 3. _stdout_write(): thread-safe stdout helper
# ---------------------------------------------------------------------------


class TestStdoutWrite:
    """_stdout_write() must acquire the lock and write atomically."""

    def test_stdout_write_method_exists(self, tmp_path):
        """_stdout_write() must exist on ParallelOrchestrator."""
        orc = make_orchestrator(tmp_path)
        assert hasattr(orc, "_stdout_write"), (
            "ParallelOrchestrator is missing '_stdout_write()' method. "
            "Add a thread-safe stdout write helper that acquires _stdout_lock."
        )
        assert callable(orc._stdout_write), "_stdout_write must be callable"

    def test_stdout_write_outputs_to_stdout(self, tmp_path, capsys):
        """_stdout_write() must write its argument to stdout."""
        orc = make_orchestrator(tmp_path)
        orc._stdout_write("[ws:42] test line\n")
        captured = capsys.readouterr()
        assert "[ws:42] test line" in captured.out, (
            f"_stdout_write should write to stdout, but got: {captured.out!r}"
        )

    def test_stdout_write_acquires_lock(self, tmp_path):
        """_stdout_write() must hold _stdout_lock while writing."""
        orc = make_orchestrator(tmp_path)
        lock_acquired_during_write = []

        original_write = sys.stdout.write

        def capturing_write(text):
            # Check if the lock is held during write
            is_locked = not orc._stdout_lock.acquire(blocking=False)
            lock_acquired_during_write.append(is_locked)
            if not is_locked:
                orc._stdout_lock.release()
            return original_write(text)

        with patch.object(sys.stdout, "write", capturing_write):
            orc._stdout_write("test message\n")

        assert any(lock_acquired_during_write), (
            "_stdout_write() must hold _stdout_lock while writing to stdout. "
            "The lock was not held during sys.stdout.write()."
        )

    def test_stdout_write_is_thread_safe_under_contention(self, tmp_path, capsys):
        """Concurrent _stdout_write() calls must not interleave mid-line."""
        orc = make_orchestrator(tmp_path)
        num_threads = 10
        errors = []

        def writer(i):
            try:
                # Write a clearly delimited line
                orc._stdout_write(f"THREAD-{i:02d}-LINE\n")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Errors during concurrent writes: {errors}"

        captured = capsys.readouterr()
        lines = [ln for ln in captured.out.splitlines() if ln.startswith("THREAD-")]
        assert len(lines) == num_threads, (
            f"Expected {num_threads} complete lines, got {len(lines)}: {captured.out!r}"
        )


# ---------------------------------------------------------------------------
# 4. _tail_output(): daemon thread that tees pipe → log + prefixed stdout
# ---------------------------------------------------------------------------


class TestTailOutput:
    """_tail_output() must read from pipe, write to log file, and prefix stdout."""

    def test_tail_output_method_exists(self, tmp_path):
        """_tail_output() must exist on ParallelOrchestrator."""
        orc = make_orchestrator(tmp_path)
        assert hasattr(orc, "_tail_output"), (
            "ParallelOrchestrator is missing '_tail_output()' method. "
            "This daemon thread reads from proc.stdout pipe and tees output."
        )

    def test_tail_output_writes_prefixed_lines_to_stdout(self, tmp_path, capsys):
        """_tail_output() must prefix each line with [ws:{issue_id}]."""
        orc = make_orchestrator(tmp_path)
        log_file = tmp_path / "log-42.txt"
        log_file.touch()

        # Simulate pipe with a StringIO
        pipe_content = "line one\nline two\n"
        fake_pipe = io.StringIO(pipe_content)

        # Run _tail_output in a thread (it blocks until EOF)
        t = threading.Thread(
            target=orc._tail_output,
            args=(fake_pipe, log_file, 42),
            daemon=True,
        )
        t.start()
        t.join(timeout=5)

        captured = capsys.readouterr()
        assert "[ws:42]" in captured.out, (
            f"_tail_output must prefix lines with '[ws:42]', got: {captured.out!r}"
        )
        assert "line one" in captured.out, f"Output missing 'line one': {captured.out!r}"
        assert "line two" in captured.out, f"Output missing 'line two': {captured.out!r}"

    def test_tail_output_writes_raw_lines_to_log_file(self, tmp_path):
        """_tail_output() must write raw (unprefixed) lines to the log file."""
        orc = make_orchestrator(tmp_path)
        log_file = tmp_path / "log-99.txt"

        pipe_content = "raw line alpha\nraw line beta\n"
        fake_pipe = io.StringIO(pipe_content)

        t = threading.Thread(
            target=orc._tail_output,
            args=(fake_pipe, log_file, 99),
            daemon=True,
        )
        t.start()
        t.join(timeout=5)

        assert log_file.exists(), "_tail_output must create the log file"
        log_contents = log_file.read_text()
        assert "raw line alpha" in log_contents, (
            f"Log file missing 'raw line alpha': {log_contents!r}"
        )
        assert "raw line beta" in log_contents, (
            f"Log file missing 'raw line beta': {log_contents!r}"
        )
        assert "[ws:99]" not in log_contents, (
            f"Log file must contain raw lines, not prefixed lines. Got: {log_contents!r}"
        )

    def test_tail_output_prefix_format(self, tmp_path, capsys):
        """Prefix format must be '[ws:{issue_id}] ' (with trailing space)."""
        orc = make_orchestrator(tmp_path)
        log_file = tmp_path / "log-7.txt"
        log_file.touch()

        fake_pipe = io.StringIO("hello world\n")

        t = threading.Thread(
            target=orc._tail_output,
            args=(fake_pipe, log_file, 7),
            daemon=True,
        )
        t.start()
        t.join(timeout=5)

        captured = capsys.readouterr()
        # The line must start with [ws:7] prefix
        output_lines = captured.out.splitlines()
        prefixed = [ln for ln in output_lines if "hello world" in ln]
        assert prefixed, f"No line containing 'hello world' in output: {captured.out!r}"
        assert any(ln.startswith("[ws:7]") for ln in prefixed), (
            f"Line with 'hello world' must start with '[ws:7]', got: {prefixed}"
        )

    def test_tail_output_handles_empty_pipe(self, tmp_path, capsys):
        """_tail_output() must handle EOF immediately (empty pipe) without hanging."""
        orc = make_orchestrator(tmp_path)
        log_file = tmp_path / "log-0.txt"
        log_file.touch()

        fake_pipe = io.StringIO("")  # Immediate EOF

        t = threading.Thread(
            target=orc._tail_output,
            args=(fake_pipe, log_file, 0),
            daemon=True,
        )
        t.start()
        t.join(timeout=2)  # Must complete quickly
        assert not t.is_alive(), "_tail_output must exit when pipe reaches EOF"

    def test_tail_output_enforces_max_log_bytes(self, tmp_path, capsys):
        """_tail_output() must stop writing to log file after MAX_LOG_BYTES exceeded."""
        orc = make_orchestrator(tmp_path)
        log_file = tmp_path / "log-55.txt"
        log_file.touch()

        # Generate data exceeding a small cap (we'll patch MAX_LOG_BYTES)
        large_content = ("X" * 100 + "\n") * 200  # 20,200 bytes
        fake_pipe = io.StringIO(large_content)

        # Patch MAX_LOG_BYTES to something small for testing
        with patch.object(orc, "_max_log_bytes", 1000, create=True):
            t = threading.Thread(
                target=orc._tail_output,
                args=(fake_pipe, log_file, 55),
                daemon=True,
            )
            t.start()
            t.join(timeout=5)

        # Log file must exist but must not exceed cap by more than one line
        assert log_file.exists(), "Log file must be created"
        log_size = log_file.stat().st_size
        # Allow some slack (one extra line) but should be close to cap
        assert log_size < 2000, (
            f"Log file should be capped around 1000 bytes, but got {log_size} bytes. "
            "MAX_LOG_BYTES cap is not being enforced."
        )


# ---------------------------------------------------------------------------
# 5. launch(): uses subprocess.PIPE not a log file handle
# ---------------------------------------------------------------------------


class TestLaunchUsesPipe:
    """launch() must use stdout=subprocess.PIPE (not a file handle)."""

    def test_launch_uses_pipe_not_file_handle(self, tmp_path):
        """launch() must open subprocess with stdout=subprocess.PIPE."""
        import subprocess

        orc = make_orchestrator(tmp_path)

        # Create a fake workstream
        from orchestrator import Workstream

        ws = Workstream(issue=101, branch="test", description="test", task="do it")
        ws.work_dir = tmp_path / "ws-101"
        ws.work_dir.mkdir(parents=True)
        ws.log_file = tmp_path / "log-101.txt"

        # Create a minimal run.sh that exits immediately
        run_sh = ws.work_dir / "run.sh"
        run_sh.write_text("#!/bin/bash\necho 'hello from ws'\nexit 0\n")
        run_sh.chmod(0o755)

        popen_calls = []
        original_popen = subprocess.Popen

        def mock_popen(*args, **kwargs):
            popen_calls.append(kwargs)
            # Return a real minimal process so cleanup doesn't fail
            return original_popen(
                ["echo", "done"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

        with patch("subprocess.Popen", side_effect=mock_popen):
            try:
                orc.launch(ws)
            except Exception:
                pass  # May fail after Popen — that's ok, we only check the call

        assert popen_calls, "subprocess.Popen was never called in launch()"
        call_kwargs = popen_calls[0]
        assert call_kwargs.get("stdout") == subprocess.PIPE, (
            f"launch() must pass stdout=subprocess.PIPE to Popen, "
            f"but got stdout={call_kwargs.get('stdout')!r}. "
            "The old implementation used stdout=log_file_handle which prevents streaming."
        )

    def test_launch_sets_text_mode(self, tmp_path):
        """launch() must use text=True so readline() returns str not bytes."""
        import subprocess

        orc = make_orchestrator(tmp_path)
        from orchestrator import Workstream

        ws = Workstream(issue=102, branch="test", description="test", task="do it")
        ws.work_dir = tmp_path / "ws-102"
        ws.work_dir.mkdir(parents=True)
        ws.log_file = tmp_path / "log-102.txt"
        run_sh = ws.work_dir / "run.sh"
        run_sh.write_text("#!/bin/bash\nexit 0\n")
        run_sh.chmod(0o755)

        popen_calls = []
        original_popen = subprocess.Popen

        def mock_popen(*args, **kwargs):
            popen_calls.append(kwargs)
            return original_popen(
                ["echo", "done"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

        with patch("subprocess.Popen", side_effect=mock_popen):
            try:
                orc.launch(ws)
            except Exception:
                pass

        assert popen_calls, "subprocess.Popen was never called"
        call_kwargs = popen_calls[0]
        assert call_kwargs.get("text") is True, (
            "launch() must pass text=True to Popen so that readline() returns str. "
            "Without text=True, the iter(pipe.readline, '') sentinel never matches bytes."
        )


# ---------------------------------------------------------------------------
# 6. launch(): starts a daemon thread per workstream
# ---------------------------------------------------------------------------


class TestLaunchStartsTailThread:
    """launch() must register a daemon thread in _tail_threads[ws.issue]."""

    def test_launch_registers_tail_thread(self, tmp_path):
        """After launch(), _tail_threads must contain a thread for the workstream."""
        import subprocess

        orc = make_orchestrator(tmp_path)
        from orchestrator import Workstream

        ws = Workstream(issue=200, branch="test", description="test", task="do it")
        ws.work_dir = tmp_path / "ws-200"
        ws.work_dir.mkdir(parents=True)
        ws.log_file = tmp_path / "log-200.txt"
        run_sh = ws.work_dir / "run.sh"
        run_sh.write_text("#!/bin/bash\necho hi\n")
        run_sh.chmod(0o755)

        # Create a process that stays alive briefly
        fake_proc = subprocess.Popen(
            ["cat"],  # cat waits for stdin
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        with patch("subprocess.Popen", return_value=fake_proc):
            try:
                orc.launch(ws)
            except Exception:
                pass

        # Cleanup the fake process
        fake_proc.stdin.close()
        fake_proc.wait(timeout=2)

        assert ws.issue in orc._tail_threads, (
            f"After launch(), _tail_threads must contain an entry for ws.issue={ws.issue}. "
            f"Got: {orc._tail_threads}"
        )

    def test_launched_tail_thread_is_daemon(self, tmp_path):
        """The tailing thread registered by launch() must be a daemon thread."""
        import subprocess

        orc = make_orchestrator(tmp_path)
        from orchestrator import Workstream

        ws = Workstream(issue=201, branch="test", description="test", task="do it")
        ws.work_dir = tmp_path / "ws-201"
        ws.work_dir.mkdir(parents=True)
        ws.log_file = tmp_path / "log-201.txt"
        run_sh = ws.work_dir / "run.sh"
        run_sh.write_text("#!/bin/bash\necho hi\n")
        run_sh.chmod(0o755)

        fake_proc = subprocess.Popen(
            ["cat"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        with patch("subprocess.Popen", return_value=fake_proc):
            try:
                orc.launch(ws)
            except Exception:
                pass

        fake_proc.stdin.close()
        fake_proc.wait(timeout=2)

        if ws.issue in orc._tail_threads:
            thread = orc._tail_threads[ws.issue]
            assert thread.daemon is True, (
                "The tailing thread must be a daemon thread so it terminates automatically "
                "when the subprocess exits. Got daemon=False."
            )


# ---------------------------------------------------------------------------
# 7. monitor(): uses _stdout_write() not raw print()
# ---------------------------------------------------------------------------


class TestMonitorUsesLock:
    """monitor() must use _stdout_write() for all stdout output (lock coverage)."""

    def test_monitor_calls_stdout_write_not_raw_print(self, tmp_path):
        """monitor() must route all status output through _stdout_write()."""
        orc = make_orchestrator(tmp_path)

        stdout_write_calls = []
        raw_print_calls = []

        # Check that _stdout_write method exists first
        assert hasattr(orc, "_stdout_write"), (
            "Cannot test monitor() lock usage without _stdout_write() existing. "
            "Add _stdout_write() to ParallelOrchestrator first."
        )

        with patch.object(
            orc, "_stdout_write", side_effect=lambda msg: stdout_write_calls.append(msg)
        ):
            with patch(
                "builtins.print", side_effect=lambda *args, **kwargs: raw_print_calls.append(args)
            ):
                # Run monitor with no workstreams (exits immediately)
                orc.monitor(check_interval=0, max_runtime=0)

        # All status output must go through _stdout_write, not raw print
        # (Some print() may be acceptable for report-style output outside the lock,
        #  but status lines about running/completed/failed MUST use the lock)
        status_prints = [
            call
            for call in raw_print_calls
            if any(
                keyword in str(call)
                for keyword in ["Running:", "Completed:", "Failed:", "Status (elapsed"]
            )
        ]
        assert not status_prints, (
            f"monitor() wrote status lines via raw print() instead of _stdout_write(). "
            f"These {len(status_prints)} calls bypass the stdout lock: {status_prints[:3]}"
        )


# ---------------------------------------------------------------------------
# 8. MAX_LOG_BYTES: module-level or class-level constant
# ---------------------------------------------------------------------------


class TestMaxLogBytes:
    """A MAX_LOG_BYTES constant must exist to cap log file sizes."""

    def test_max_log_bytes_constant_exists(self, tmp_path):
        """MAX_LOG_BYTES must be defined in orchestrator module or on the class."""
        import orchestrator as orc_module

        has_module_level = hasattr(orc_module, "MAX_LOG_BYTES")
        orc = make_orchestrator(tmp_path)
        has_instance_level = hasattr(orc, "_max_log_bytes") or hasattr(orc, "MAX_LOG_BYTES")

        assert has_module_level or has_instance_level, (
            "MAX_LOG_BYTES (or _max_log_bytes) constant must be defined in orchestrator.py "
            "to cap log file sizes and prevent /tmp exhaustion. "
            "Default value should be 100MB (100 * 1024 * 1024 bytes). "
            "It can be overridden via AMPLIHACK_MAX_LOG_BYTES env var."
        )

    def test_max_log_bytes_default_is_reasonable(self, tmp_path):
        """MAX_LOG_BYTES default must be positive and ≤ 1GB."""
        import orchestrator as orc_module

        cap = getattr(orc_module, "MAX_LOG_BYTES", None)
        orc = make_orchestrator(tmp_path)
        if cap is None:
            cap = getattr(orc, "_max_log_bytes", None)

        assert cap is not None, "MAX_LOG_BYTES must be defined"
        assert isinstance(cap, int), f"MAX_LOG_BYTES must be an int, got {type(cap).__name__}"
        assert cap > 0, f"MAX_LOG_BYTES must be positive, got {cap}"
        assert cap <= 1024**3, (
            f"MAX_LOG_BYTES default should be ≤ 1GB to protect /tmp. Got {cap} bytes."
        )


# ---------------------------------------------------------------------------
# Entry point for direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
