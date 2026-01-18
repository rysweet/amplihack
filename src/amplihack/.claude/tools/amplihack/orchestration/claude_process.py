"""Claude subprocess execution with output capture and timeout support.

This module extracts and refines the subprocess mechanics from auto_mode.py,
providing a clean interface for running Claude CLI processes with proper
output streaming, timeout handling, and logging.
"""

import os
import pty
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessResult:
    """Result of a Claude process execution.

    Attributes:
        exit_code: Process exit code (0=success, -1=timeout, other=error)
        output: Combined stdout output
        stderr: Stderr output if any
        duration: Execution duration in seconds
        process_id: Unique identifier for this process
    """

    exit_code: int
    output: str
    stderr: str
    duration: float
    process_id: str


class ClaudeProcess:
    """Manages a single Claude CLI subprocess execution.

    This class handles:
    - Building Claude CLI commands
    - Creating PTY for stdin to prevent blocking
    - Streaming output to console while capturing it
    - Timeout handling and process termination
    - Comprehensive logging

    Example:
        >>> process = ClaudeProcess(
        ...     prompt="Analyze this code",
        ...     process_id="analyze-001",
        ...     working_dir=Path("/project"),
        ...     log_dir=Path("/logs")
        ... )
        >>> result = process.run()
        >>> if result.exit_code == 0:
        ...     print(f"Success: {result.output}")
    """

    def __init__(
        self,
        prompt: str,
        process_id: str,
        working_dir: Path,
        log_dir: Path,
        model: str | None = None,
        stream_output: bool = True,
        timeout: int | None = None,
    ):
        """Initialize Claude process.

        Args:
            prompt: The prompt to send to Claude
            process_id: Unique identifier for this process
            working_dir: Working directory for the subprocess
            log_dir: Directory for process logs
            model: Claude model to use (default: uses CLI default)
            stream_output: Whether to stream output to console (default: True)
            timeout: Timeout in seconds (default: None = no timeout)
        """
        self.prompt = prompt
        self.process_id = process_id
        self.working_dir = working_dir
        self.log_dir = log_dir
        self.model = model
        self.stream_output = stream_output
        self.timeout = timeout

        # Runtime state
        self._process: subprocess.Popen | None = None
        self._master_fd: int | None = None
        self._start_time: float = 0
        self._stdout_lines: list[str] = []
        self._stderr_lines: list[str] = []

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, msg: str, level: str = "INFO"):
        """Log message to both console and file.

        Args:
            msg: Message to log
            level: Log level (INFO, WARNING, ERROR)
        """
        log_msg = f"[{time.strftime('%H:%M:%S')}] [{level}] [{self.process_id}] {msg}"
        print(log_msg)

        log_file = self.log_dir / f"{self.process_id}.log"
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")

    def run(self) -> ProcessResult:
        """Execute the Claude process.

        Main entry point that orchestrates the full execution lifecycle:
        1. Build command
        2. Setup PTY and logging
        3. Spawn subprocess
        4. Start output threads
        5. Feed PTY stdin
        6. Wait for completion
        7. Cleanup and return result

        Returns:
            ProcessResult with exit code, output, stderr, duration, and process_id
        """
        self._start_time = time.time()
        self.log(f"Starting process with timeout={self.timeout}s")

        try:
            # Build and log command
            cmd = self._build_command()
            self.log(f'Command: {" ".join(cmd[:2])} -p "..."')

            # Setup PTY and spawn process
            self._setup_logging()
            self._master_fd, slave_fd = pty.openpty()
            self._process = self._spawn_process(cmd, slave_fd)

            # Close slave in parent (child has copy)
            os.close(slave_fd)

            # Start output capture threads
            threads = self._start_threads()

            # Wait for completion with timeout
            exit_code = self._wait_for_completion()

            # Wait for output threads to finish
            for thread in threads[:2]:  # stdout and stderr threads
                thread.join()
            # stdin thread is daemon, will terminate automatically

            # Combine results
            stdout_output = "".join(self._stdout_lines)
            stderr_output = "".join(self._stderr_lines)
            duration = time.time() - self._start_time

            if stderr_output:
                self.log(f"stderr: {stderr_output[:200]}...", level="WARNING")

            self.log(f"Completed with exit_code={exit_code} in {duration:.1f}s")

            return ProcessResult(
                exit_code=exit_code,
                output=stdout_output,
                stderr=stderr_output,
                duration=duration,
                process_id=self.process_id,
            )

        except Exception as e:
            duration = time.time() - self._start_time
            self.log(f"Fatal error: {e}", level="ERROR")
            return ProcessResult(
                exit_code=-1,
                output="",
                stderr=str(e),
                duration=duration,
                process_id=self.process_id,
            )
        finally:
            self._cleanup()

    def terminate(self):
        """Force terminate the subprocess.

        Called when timeout expires or for emergency shutdown.
        """
        if self._process:
            self.log("Terminating process", level="WARNING")
            try:
                self._process.terminate()
                time.sleep(0.5)
                if self._process.poll() is None:
                    self.log("Process did not terminate, killing", level="WARNING")
                    self._process.kill()
            except Exception as e:
                self.log(f"Error during termination: {e}", level="ERROR")

    def _build_command(self) -> list[str]:
        """Build the Claude CLI command.

        Returns:
            Command as list of strings
        """
        cmd = ["claude", "--dangerously-skip-permissions", "-p", self.prompt]

        if self.model:
            cmd.extend(["--model", self.model])

        return cmd

    def _spawn_process(self, cmd: list[str], slave_fd: int) -> subprocess.Popen:
        """Spawn the subprocess with PTY stdin.

        Args:
            cmd: Command to execute
            slave_fd: Slave side of PTY for stdin

        Returns:
            Popen process object
        """
        return subprocess.Popen(
            cmd,
            stdin=slave_fd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.working_dir,
        )

    def _start_threads(self) -> list[threading.Thread]:
        """Start output capture and stdin feeding threads.

        Returns:
            List of thread objects
        """
        stdout_thread = threading.Thread(
            target=self._read_stream,
            args=(self._process.stdout, self._stdout_lines, sys.stdout),
        )
        stderr_thread = threading.Thread(
            target=self._read_stream,
            args=(self._process.stderr, self._stderr_lines, sys.stderr),
        )
        stdin_thread = threading.Thread(
            target=self._feed_pty_stdin,
            daemon=True,
        )

        stdout_thread.start()
        stderr_thread.start()
        stdin_thread.start()

        return [stdout_thread, stderr_thread, stdin_thread]

    def _read_stream(self, stream, output_list: list[str], mirror_stream):
        """Read from stream and mirror to output.

        Args:
            stream: Input stream to read
            output_list: List to append lines to
            mirror_stream: Output stream to mirror to
        """
        try:
            for line in iter(stream.readline, ""):
                output_list.append(line)
                if self.stream_output:
                    mirror_stream.write(line)
                    mirror_stream.flush()
        except Exception as e:
            self.log(f"Error reading stream: {e}", level="ERROR")

    def _feed_pty_stdin(self):
        """Auto-feed PTY master with newlines to prevent stdin blocking.

        This ensures any subprocess attempts to read stdin don't block.
        Runs in daemon thread until process completes.
        """
        try:
            while self._process.poll() is None:
                time.sleep(0.1)  # Check every 100ms
                try:
                    os.write(self._master_fd, b"\n")
                except (BrokenPipeError, OSError):
                    # Process closed or PTY closed
                    break
        except Exception:
            # Silently handle any other exceptions
            pass

    def _wait_for_completion(self) -> int:
        """Wait for process to complete with optional timeout.

        Returns:
            Exit code (-1 for timeout, actual exit code otherwise)
        """
        try:
            if self.timeout:
                self._process.wait(timeout=self.timeout)
            else:
                self._process.wait()
            return self._process.returncode
        except subprocess.TimeoutExpired:
            self.log(f"Timeout ({self.timeout}s) expired, terminating", level="WARNING")
            self.terminate()
            return -1

    def _setup_logging(self):
        """Setup logging infrastructure.

        Creates process-specific log file.
        """
        log_file = self.log_dir / f"{self.process_id}.log"
        with open(log_file, "w") as f:
            f.write(f"Process: {self.process_id}\n")
            f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Prompt: {self.prompt[:100]}...\n")
            f.write("-" * 80 + "\n")

    def _cleanup(self):
        """Cleanup resources.

        Closes PTY master fd if still open.
        """
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except Exception:
                pass
            self._master_fd = None
