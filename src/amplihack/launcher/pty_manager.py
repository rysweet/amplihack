"""PTY (pseudo-terminal) management for subprocess stdin handling."""

import os
import sys
import threading
import time
from typing import Any, Callable, Optional, TextIO


class PTYManager:
    """Manages PTY creation and stdin feeding for subprocess communication."""

    @staticmethod
    def create_pty() -> tuple[int, int]:
        """Create a pseudo-terminal pair.

        Returns:
            (master_fd, slave_fd) file descriptor pair
        """
        import pty

        return pty.openpty()

    @staticmethod
    def feed_pty_stdin(
        fd: int,
        process: Any,
        log_func: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """Auto-feed pty master with newlines to prevent stdin blocking.

        Args:
            fd: Master file descriptor
            process: Subprocess instance with poll() method
            log_func: Optional logging function(message, level)
        """
        try:
            while process.poll() is None:
                time.sleep(0.1)  # Check every 100ms
                try:
                    os.write(fd, b"\n")
                except (BrokenPipeError, OSError):
                    # Process closed or pty closed
                    break
        except KeyboardInterrupt:
            # Allow clean shutdown on Ctrl+C
            pass
        except Exception as e:
            # Log unexpected errors for debugging
            if log_func:
                log_func(f"PTY stdin feed error: {e}", "WARNING")
        finally:
            try:
                os.close(fd)
            except (OSError, ValueError):
                # File descriptor already closed or invalid
                pass
            except Exception as e:
                # Log any other unexpected cleanup errors
                if log_func:
                    log_func(f"PTY cleanup error: {e}", "WARNING")

    @staticmethod
    def read_stream(stream: TextIO, output_list: list[str], mirror_stream: TextIO) -> None:
        """Read from stream and mirror to output.

        Args:
            stream: Input stream to read from
            output_list: List to append output lines to
            mirror_stream: Output stream to mirror to (stdout/stderr)
        """
        for line in iter(stream.readline, ""):
            output_list.append(line)
            mirror_stream.write(line)
            mirror_stream.flush()

    @staticmethod
    def start_pty_threads(
        process: Any,
        master_fd: int,
        log_func: Optional[Callable[[str, str], None]] = None,
    ) -> tuple[list[str], list[str], threading.Thread, threading.Thread, threading.Thread]:
        """Start threads for reading stdout/stderr and feeding stdin.

        Args:
            process: Subprocess instance with stdout, stderr attributes
            master_fd: Master file descriptor for stdin feeding
            log_func: Optional logging function(message, level)

        Returns:
            (stdout_lines, stderr_lines, stdout_thread, stderr_thread, stdin_thread)
        """
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        # Create threads to read stdout and stderr concurrently
        stdout_thread = threading.Thread(
            target=PTYManager.read_stream,
            args=(process.stdout, stdout_lines, sys.stdout),
        )
        stderr_thread = threading.Thread(
            target=PTYManager.read_stream,
            args=(process.stderr, stderr_lines, sys.stderr),
        )
        stdin_thread = threading.Thread(
            target=PTYManager.feed_pty_stdin,
            args=(master_fd, process, log_func),
            daemon=True,
        )

        # Start threads
        stdout_thread.start()
        stderr_thread.start()
        stdin_thread.start()

        return stdout_lines, stderr_lines, stdout_thread, stderr_thread, stdin_thread

    @staticmethod
    def wait_for_completion(
        process: Any,
        stdout_thread: threading.Thread,
        stderr_thread: threading.Thread,
    ) -> tuple[int, str, str]:
        """Wait for process and threads to complete.

        Args:
            process: Subprocess instance with wait() method
            stdout_thread: Thread reading stdout
            stderr_thread: Thread reading stderr

        Returns:
            (return_code, stdout_output, stderr_output)
        """
        # Wait for process to complete
        process.wait()

        # Wait for output threads to finish reading
        stdout_thread.join()
        stderr_thread.join()
        # stdin_thread is daemon, will terminate automatically

        return process.returncode
