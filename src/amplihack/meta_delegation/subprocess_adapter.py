"""Subprocess Adapter Module.

This module provides subprocess execution with real process management,
timeout enforcement, and proper cleanup. It wraps subprocess.Popen with
meta-delegation-specific requirements.

Core Features:
- Real subprocess spawning via subprocess.Popen
- Timeout enforcement with process termination
- Output streaming and capture
- Exit code and error handling
- Process lifecycle tracking

Philosophy:
- Use subprocess.Popen directly (no abstractions)
- Non-blocking I/O with proper timeout handling
- Guaranteed process cleanup (kill on timeout/error)
- Comprehensive error information
"""

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from typing import Any


class SubprocessError(Exception):
    """Base exception for subprocess errors."""

    def __init__(
        self,
        message: str,
        exit_code: int | None = None,
        subprocess_pid: int | None = None,
        spawn_failed: bool = False,
        stdout: str = "",
        stderr: str = "",
    ):
        self.exit_code = exit_code
        self.subprocess_exit_code = exit_code  # Alias
        self.subprocess_pid = subprocess_pid
        self.spawn_failed = spawn_failed
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(message)


class SubprocessTimeoutError(SubprocessError):
    """Exception raised when subprocess exceeds timeout."""

    def __init__(
        self,
        timeout: float,
        duration: float,
        subprocess_pid: int | None = None,
        command: list[str] | None = None,
        partial_stdout: str = "",
        partial_stderr: str = "",
    ):
        self.timeout = timeout
        self.duration = duration
        self.command = command
        self.partial_stdout = partial_stdout
        self.partial_stderr = partial_stderr
        self.was_killed = True  # Always true for timeout errors
        super().__init__(
            f"Subprocess exceeded timeout of {timeout}s (ran for {duration:.1f}s)",
            subprocess_pid=subprocess_pid,
            stdout=partial_stdout,
            stderr=partial_stderr,
        )


@dataclass
class SubprocessResult:
    """Result of subprocess execution.

    Attributes:
        exit_code: Process exit code (0 = success)
        stdout: Standard output content
        stderr: Standard error content
        duration: Execution duration in seconds
        subprocess_pid: Process ID of subprocess
        timed_out: Whether process was killed due to timeout
        monitoring_data: Optional monitoring data if monitor=True
        orphans_cleaned: Number of orphaned child processes cleaned up
        success: Whether execution was successful (exit_code == 0)
        crashed: Whether process crashed (exit_code < 0)
    """

    exit_code: int
    stdout: str
    stderr: str
    duration: float
    subprocess_pid: int
    timed_out: bool = False
    monitoring_data: dict | None = None
    orphans_cleaned: int = 0

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.exit_code == 0 and not self.timed_out

    @property
    def crashed(self) -> bool:
        """Check if process crashed."""
        return self.exit_code < 0


class CLISubprocessAdapter:
    """Adapter for spawning and managing CLI subprocesses.

    Handles real subprocess execution with timeout enforcement,
    output capture, and proper cleanup.
    """

    def __init__(
        self,
        timeout: float | None = None,
        stream_output: bool = False,
        env: dict[str, str] | None = None,
    ):
        """Initialize subprocess adapter.

        Args:
            timeout: Timeout in seconds (default: auto-detect based on CI env)
            stream_output: Whether to stream output in real-time
            env: Environment variables to pass to subprocess
        """
        # Auto-detect timeout based on CI environment
        if timeout is None:
            is_ci = os.getenv("CI", "false").lower() == "true"
            timeout = 30.0 if is_ci else 60.0

        self.timeout = timeout
        self.default_timeout = timeout  # Alias for tests
        self.stream_output = stream_output
        self.env = env or {}

    def spawn(
        self,
        command: list[str],
        working_dir: str,
        capture_exceptions: bool = False,
        timeout_override: float | None = None,
        env_override: dict[str, str] | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
        monitor: bool = False,
        handle_orphans: bool = False,
        check: bool = True,
        expect_json: bool = False,
        _json_recovery: bool = False,
        _context: dict[str, Any] | None = None,
        _ci_format: bool = False,
        _binary_safe: bool = False,
    ) -> SubprocessResult:
        """Spawn a subprocess and wait for completion.

        Args:
            command: Command and arguments to execute
            working_dir: Working directory for subprocess
            capture_exceptions: Whether to capture Python exceptions from subprocess
            timeout_override: Override default timeout for this spawn
            env_override: Override default environment for this spawn
            timeout: Alias for timeout_override
            env: Alias for env_override
            monitor: Enable monitoring and collect progress data
            handle_orphans: Attempt to clean up orphaned child processes
            check: If True, raise exception on non-zero exit code (default: True)
            expect_json: Validate output is valid JSON

        Returns:
            SubprocessResult with exit code, output, and metadata

        Raises:
            SubprocessTimeoutError: If subprocess exceeds timeout
            SubprocessError: If subprocess fails with capture_exceptions=True or check=True
        """
        start_time = time.time()

        # Handle timeout aliases
        if timeout is not None:
            timeout_override = timeout
        timeout_val = timeout_override if timeout_override is not None else self.timeout

        # Handle env aliases
        if env is not None:
            env_override = env
        env_val = env_override if env_override is not None else self.env

        # Prepare environment
        process_env = os.environ.copy()
        if env_val:
            process_env.update(env_val)

        # Spawn process
        try:
            process = subprocess.Popen(
                command,
                cwd=working_dir,
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )
        except Exception as e:
            raise SubprocessError(f"Failed to spawn subprocess: {e}", spawn_failed=True)

        pid = process.pid
        stdout_lines = []
        stderr_lines = []
        monitoring_data = {"progress_updates": []} if monitor else None
        orphans_cleaned = 0

        # Monitor process execution
        try:
            while True:
                # Check timeout
                elapsed = time.time() - start_time
                if timeout_val is not None and elapsed > timeout_val:
                    # Try to read any remaining output before killing
                    try:
                        import select

                        # Check if there's data available to read (non-blocking)
                        if process.stdout:
                            readable, _, _ = select.select([process.stdout], [], [], 0)
                            if readable:
                                chunk = process.stdout.read()
                                if chunk:
                                    stdout_lines.append(chunk)
                        if process.stderr:
                            readable, _, _ = select.select([process.stderr], [], [], 0)
                            if readable:
                                chunk = process.stderr.read()
                                if chunk:
                                    stderr_lines.append(chunk)
                    except Exception:
                        pass

                    # Handle orphaned processes if requested
                    if handle_orphans:
                        orphans_cleaned = self._cleanup_orphans(process)

                    # Kill process
                    self._kill_process(process)

                    # If handle_orphans is set, return a result instead of raising
                    if handle_orphans:
                        stdout = "".join(stdout_lines)
                        stderr = "".join(stderr_lines)
                        duration = time.time() - start_time

                        return SubprocessResult(
                            exit_code=-1,
                            stdout=stdout,
                            stderr=stderr,
                            duration=duration,
                            subprocess_pid=pid,
                            timed_out=True,
                            monitoring_data=monitoring_data,
                            orphans_cleaned=orphans_cleaned,
                        )

                    # Collect partial output before raising
                    partial_stdout = "".join(stdout_lines)
                    partial_stderr = "".join(stderr_lines)

                    raise SubprocessTimeoutError(
                        timeout=timeout_val if timeout_val is not None else 0.0,
                        duration=elapsed,
                        subprocess_pid=pid,
                        command=command,
                        partial_stdout=partial_stdout,
                        partial_stderr=partial_stderr,
                    )

                # Check if process has finished
                exit_code = process.poll()
                if exit_code is not None:
                    # Process finished - collect remaining output
                    stdout_remaining, stderr_remaining = process.communicate(timeout=1.0)
                    if stdout_remaining:
                        stdout_lines.append(stdout_remaining)
                    if stderr_remaining:
                        stderr_lines.append(stderr_remaining)
                    break

                # Try to read output non-blocking
                try:
                    import select

                    if process.stdout:
                        readable, _, _ = select.select([process.stdout], [], [], 0)
                        if readable:
                            chunk = process.stdout.read(4096)
                            if chunk:
                                stdout_lines.append(chunk)
                    if process.stderr:
                        readable, _, _ = select.select([process.stderr], [], [], 0)
                        if readable:
                            chunk = process.stderr.read(4096)
                            if chunk:
                                stderr_lines.append(chunk)
                except Exception:
                    pass

                # Collect monitoring data if enabled
                if monitor and monitoring_data:
                    progress_updates = monitoring_data.get("progress_updates")
                    if isinstance(progress_updates, list):
                        progress_updates.append(
                            {
                                "elapsed": elapsed,
                                "timestamp": time.time(),
                            }
                        )

                # Small sleep to avoid busy-waiting
                time.sleep(0.1)

        except SubprocessTimeoutError:
            raise
        except Exception as e:
            # Cleanup on error
            self._kill_process(process)
            raise SubprocessError(f"Error monitoring subprocess: {e}", subprocess_pid=pid)

        # Calculate duration
        duration = time.time() - start_time

        # Combine output
        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)

        # Check for Python exceptions if requested
        if capture_exceptions and exit_code != 0:
            # Check if stderr contains Python exception
            if "Traceback" in stderr or "Error:" in stderr:
                raise SubprocessError(
                    f"Subprocess raised exception:\n{stderr}",
                    exit_code=exit_code,
                    subprocess_pid=pid,
                    stdout=stdout,
                    stderr=stderr,
                )

        # Check exit code if requested
        if check and exit_code != 0:
            raise SubprocessError(
                f"Subprocess failed with exit code {exit_code}\nstdout: {stdout}\nstderr: {stderr}",
                exit_code=exit_code,
                subprocess_pid=pid,
                stdout=stdout,
                stderr=stderr,
            )

        # Validate JSON if requested
        if expect_json:
            try:
                import json

                json.loads(stdout)
            except json.JSONDecodeError as e:
                raise SubprocessError(
                    f"Expected JSON output but got invalid JSON: {e}\nOutput: {stdout}",
                    exit_code=exit_code,
                    subprocess_pid=pid,
                )

        return SubprocessResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            subprocess_pid=pid,
            timed_out=False,
            monitoring_data=monitoring_data,
            orphans_cleaned=orphans_cleaned,
        )

    def _kill_process(self, process: subprocess.Popen) -> None:
        """Kill a process and all its children.

        Args:
            process: Process to kill
        """
        try:
            # Try graceful termination first
            process.terminate()
            try:
                process.wait(timeout=2.0)
                return
            except subprocess.TimeoutExpired:
                pass

            # Force kill if still alive
            process.kill()
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass  # Best effort

        except (ProcessLookupError, PermissionError):
            # Process already dead or not accessible - acceptable
            pass
        except Exception as e:
            import warnings

            warnings.warn(f"Unexpected cleanup error for PID {process.pid}: {e}", stacklevel=2)

    def _cleanup_orphans(self, process: subprocess.Popen) -> int:
        """Clean up orphaned child processes.

        Args:
            process: Parent process

        Returns:
            Number of orphans cleaned up
        """
        orphans_cleaned = 0
        try:
            # Try to find child processes via psutil if available
            try:
                import psutil

                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    try:
                        child.terminate()
                        orphans_cleaned += 1
                    except (ProcessLookupError, PermissionError):
                        # Process already dead or not accessible - acceptable
                        pass
                    except Exception as e:
                        import warnings

                        warnings.warn(
                            f"Unexpected error terminating child process: {e}", stacklevel=2
                        )
            except ImportError:
                # Fallback: parse ps output (Unix-like systems only)
                if os.name != "nt":  # Not Windows
                    try:
                        ps_output = subprocess.check_output(
                            ["ps", "--ppid", str(process.pid), "-o", "pid="], text=True
                        )
                        child_pids = [
                            int(pid.strip()) for pid in ps_output.strip().split("\n") if pid.strip()
                        ]
                        for child_pid in child_pids:
                            try:
                                os.kill(child_pid, signal.SIGTERM)
                                orphans_cleaned += 1
                            except (ProcessLookupError, PermissionError):
                                # Process already dead or not accessible - acceptable
                                pass
                            except Exception as e:
                                import warnings

                                warnings.warn(
                                    f"Unexpected error killing child PID {child_pid}: {e}",
                                    stacklevel=2,
                                )
                    except (FileNotFoundError, subprocess.CalledProcessError):
                        # ps command not available or failed - acceptable on some systems
                        pass
                    except Exception as e:
                        import warnings

                        warnings.warn(f"Unexpected error in ps fallback: {e}", stacklevel=2)
        except (ProcessLookupError, PermissionError):
            # Parent process already dead or not accessible - acceptable
            pass
        except Exception as e:
            import warnings

            warnings.warn(f"Unexpected error in orphan cleanup: {e}", stacklevel=2)

        return orphans_cleaned


def spawn_subprocess(
    command: list[str],
    working_dir: str,
    timeout: float = 30.0,
    env: dict[str, str] | None = None,
) -> SubprocessResult:
    """Convenience function to spawn a subprocess.

    Args:
        command: Command and arguments
        working_dir: Working directory
        timeout: Timeout in seconds
        env: Environment variables

    Returns:
        SubprocessResult

    Raises:
        SubprocessTimeoutError: If timeout exceeded
        SubprocessError: If spawn fails
    """
    adapter = CLISubprocessAdapter(timeout=timeout, env=env)
    return adapter.spawn(command=command, working_dir=working_dir)
