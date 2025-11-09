"""Standardized subprocess execution with comprehensive error handling.

This module provides a unified interface for all subprocess operations in amplihack,
ensuring consistent error handling, timeout management, logging, and cross-platform
compatibility.

Philosophy:
- Every subprocess call should be safe and predictable
- Failures should provide actionable error messages
- Timeouts prevent hanging operations
- Logging enables debugging and monitoring
- Cross-platform compatibility is built-in

Public API:
    SubprocessRunner: Main class for running subprocesses
    SubprocessResult: Result object with rich error information
    SubprocessError: Exception raised on command failures

Example:
    >>> runner = SubprocessRunner()
    >>> result = runner.run_safe(["git", "status"], timeout=10)
    >>> if result.success:
    ...     print(result.stdout)
    ... else:
    ...     print(f"Error: {result.stderr}")
"""

import logging
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class SubprocessResult:
    """Result of a subprocess execution with rich error information.

    Attributes:
        returncode: Exit code of the process (0 = success)
        stdout: Standard output from the process
        stderr: Standard error from the process
        command: The command that was executed
        success: True if returncode == 0
        error_type: Type of error if command failed (timeout, not_found, etc.)
        duration: Execution time in seconds
    """

    returncode: int
    stdout: str
    stderr: str
    command: List[str]
    success: bool
    error_type: Optional[str] = None
    duration: Optional[float] = None

    def __bool__(self) -> bool:
        """Allow boolean evaluation of result."""
        return self.success


class SubprocessError(Exception):
    """Exception raised when subprocess execution fails.

    Attributes:
        result: The SubprocessResult containing error details
        message: Human-readable error message
    """

    def __init__(self, result: SubprocessResult, message: str):
        self.result = result
        self.message = message
        super().__init__(message)


class SubprocessRunner:
    """Standardized subprocess execution with comprehensive error handling.

    This class provides a single, consistent interface for running subprocess
    commands across the amplihack codebase. It handles:

    - Timeout management (default 30s)
    - Cross-platform compatibility
    - Error classification and helpful messages
    - Optional logging of all commands
    - Process group management for clean termination

    Example:
        >>> runner = SubprocessRunner(default_timeout=60, log_commands=True)
        >>> result = runner.run_safe(["npm", "install"], cwd="/path/to/project")
        >>> if not result:
        ...     logger.error(f"npm install failed: {result.stderr}")
    """

    def __init__(
        self,
        default_timeout: int = 30,
        log_commands: bool = True,
        capture_output: bool = True,
    ):
        """Initialize SubprocessRunner.

        Args:
            default_timeout: Default timeout in seconds for all commands
            log_commands: Whether to log command execution (for debugging)
            capture_output: Whether to capture stdout/stderr by default
        """
        self.default_timeout = default_timeout
        self.log_commands = log_commands
        self.capture_output = capture_output

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows.

        Returns:
            True if Windows, False otherwise
        """
        return sys.platform == "win32" or os.name == "nt"

    def run_safe(
        self,
        cmd: List[str],
        timeout: Optional[int] = None,
        check: bool = False,
        capture: Optional[bool] = None,
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        context: Optional[str] = None,
        shell: bool = False,
    ) -> SubprocessResult:
        """Execute command with comprehensive error handling.

        This is the primary method for running subprocess commands. It provides:
        - Automatic timeout handling
        - Detailed error classification
        - Optional command logging
        - Cross-platform compatibility
        - Rich result objects

        Args:
            cmd: Command and arguments as list (e.g., ["git", "status"])
            timeout: Timeout in seconds (None = use default_timeout)
            check: If True, raise SubprocessError on non-zero exit
            capture: Override capture_output setting for this call
            cwd: Working directory for command execution
            env: Environment variables (merged with current environment)
            context: Human-readable description for error messages
            shell: Whether to run command through shell (avoid if possible)

        Returns:
            SubprocessResult with command output and metadata

        Raises:
            SubprocessError: If check=True and command fails

        Example:
            >>> result = runner.run_safe(
            ...     ["git", "clone", "https://github.com/user/repo"],
            ...     timeout=300,
            ...     context="cloning repository"
            ... )
            >>> if result.success:
            ...     print("Clone successful!")
        """
        import time

        start_time = time.time()
        timeout_val = timeout if timeout is not None else self.default_timeout
        capture_val = capture if capture is not None else self.capture_output

        # Log command if enabled
        if self.log_commands:
            cmd_str = " ".join(cmd)
            logger.debug(f"Running command: {cmd_str}")
            if context:
                logger.debug(f"Context: {context}")

        # Prepare environment
        final_env = os.environ.copy()
        if env:
            final_env.update(env)

        # Convert cwd to string if Path
        cwd_str = str(cwd) if cwd else None

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_val,
                text=True,
                timeout=timeout_val,
                check=False,  # We handle this manually
                cwd=cwd_str,
                env=final_env,
                shell=shell,
            )

            duration = time.time() - start_time

            # Create result object
            subprocess_result = SubprocessResult(
                returncode=result.returncode,
                stdout=result.stdout if capture_val else "",
                stderr=result.stderr if capture_val else "",
                command=cmd,
                success=(result.returncode == 0),
                duration=duration,
            )

            # Log result
            if self.log_commands:
                if subprocess_result.success:
                    logger.debug(f"Command succeeded in {duration:.2f}s")
                else:
                    logger.warning(
                        f"Command failed with exit code {result.returncode} "
                        f"in {duration:.2f}s"
                    )

            # Raise if check=True and command failed
            if check and not subprocess_result.success:
                error_msg = self._build_error_message(subprocess_result, context)
                raise SubprocessError(subprocess_result, error_msg)

            return subprocess_result

        except FileNotFoundError:
            # Command not found - most common error
            duration = time.time() - start_time
            cmd_name = cmd[0] if cmd else "command"
            error_msg = f"Command not found: {cmd_name}"
            if context:
                error_msg += f"\nContext: {context}"
            error_msg += "\nPlease ensure the tool is installed and in your PATH."

            logger.error(error_msg)

            result = SubprocessResult(
                returncode=127,
                stdout="",
                stderr=error_msg,
                command=cmd,
                success=False,
                error_type="not_found",
                duration=duration,
            )

            if check:
                raise SubprocessError(result, error_msg)
            return result

        except PermissionError:
            # Permission denied
            duration = time.time() - start_time
            cmd_name = cmd[0] if cmd else "command"
            error_msg = f"Permission denied: {cmd_name}"
            if context:
                error_msg += f"\nContext: {context}"
            error_msg += "\nPlease check file permissions or run with appropriate privileges."

            logger.error(error_msg)

            result = SubprocessResult(
                returncode=126,
                stdout="",
                stderr=error_msg,
                command=cmd,
                success=False,
                error_type="permission",
                duration=duration,
            )

            if check:
                raise SubprocessError(result, error_msg)
            return result

        except subprocess.TimeoutExpired as e:
            # Command timed out
            duration = time.time() - start_time
            cmd_name = cmd[0] if cmd else "command"
            error_msg = f"Command timed out after {timeout_val}s: {cmd_name}"
            if context:
                error_msg += f"\nContext: {context}"
            error_msg += "\nThe operation took too long to complete."

            logger.error(error_msg)

            # Try to get partial output from timeout exception
            stdout = e.stdout if hasattr(e, "stdout") and e.stdout else ""
            stderr = e.stderr if hasattr(e, "stderr") and e.stderr else ""

            result = SubprocessResult(
                returncode=124,
                stdout=stdout,
                stderr=error_msg + (f"\n{stderr}" if stderr else ""),
                command=cmd,
                success=False,
                error_type="timeout",
                duration=duration,
            )

            if check:
                raise SubprocessError(result, error_msg)
            return result

        except OSError as e:
            # Generic OS error
            duration = time.time() - start_time
            cmd_name = cmd[0] if cmd else "command"
            error_msg = f"OS error running {cmd_name}: {e!s}"
            if context:
                error_msg += f"\nContext: {context}"

            logger.error(error_msg)

            result = SubprocessResult(
                returncode=1,
                stdout="",
                stderr=error_msg,
                command=cmd,
                success=False,
                error_type="os_error",
                duration=duration,
            )

            if check:
                raise SubprocessError(result, error_msg)
            return result

        except Exception as e:
            # Catch-all for unexpected errors
            duration = time.time() - start_time
            cmd_name = cmd[0] if cmd else "command"
            error_msg = f"Unexpected error running {cmd_name}: {e!s}"
            if context:
                error_msg += f"\nContext: {context}"

            logger.exception(error_msg)

            result = SubprocessResult(
                returncode=1,
                stdout="",
                stderr=error_msg,
                command=cmd,
                success=False,
                error_type="unexpected",
                duration=duration,
            )

            if check:
                raise SubprocessError(result, error_msg)
            return result

    def _build_error_message(
        self,
        result: SubprocessResult,
        context: Optional[str] = None,
    ) -> str:
        """Build comprehensive error message from result.

        Args:
            result: SubprocessResult from failed command
            context: Optional context string

        Returns:
            Formatted error message
        """
        cmd_str = " ".join(result.command)
        msg = f"Command failed with exit code {result.returncode}: {cmd_str}"

        if context:
            msg += f"\nContext: {context}"

        if result.stderr:
            msg += f"\nError output:\n{result.stderr}"

        return msg

    def check_command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH.

        Args:
            command: Command name to check (e.g., "git", "npm")

        Returns:
            True if command exists, False otherwise

        Example:
            >>> if runner.check_command_exists("git"):
            ...     print("Git is available")
        """
        try:
            if self.is_windows():
                # Windows: use where command
                result = self.run_safe(
                    ["where", command],
                    timeout=5,
                    capture=True,
                )
            else:
                # Unix: use which command
                result = self.run_safe(
                    ["which", command],
                    timeout=5,
                    capture=True,
                )
            return result.success
        except Exception:
            return False

    def create_process_group_popen(
        self,
        cmd: List[str],
        **kwargs,
    ) -> subprocess.Popen:
        """Create a Popen process in a new process group.

        This is useful for long-running processes that may need to be
        terminated along with their children (e.g., dev servers).

        Args:
            cmd: Command and arguments as list
            **kwargs: Additional arguments passed to Popen

        Returns:
            Popen process object

        Example:
            >>> process = runner.create_process_group_popen(
            ...     ["npm", "run", "dev"],
            ...     cwd="/path/to/project"
            ... )
            >>> # Later...
            >>> runner.terminate_process_group(process)
        """
        if self.is_windows():
            # CREATE_NEW_PROCESS_GROUP is Windows-specific
            if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["preexec_fn"] = os.setsid

        return subprocess.Popen(cmd, **kwargs)

    def terminate_process_group(
        self,
        process: subprocess.Popen,
        timeout: int = 5,
    ) -> None:
        """Terminate a process and its entire process group.

        This ensures all child processes are also terminated, preventing
        orphaned processes.

        Args:
            process: Process to terminate
            timeout: Timeout in seconds for graceful shutdown

        Example:
            >>> process = runner.create_process_group_popen(["npm", "start"])
            >>> # Do work...
            >>> runner.terminate_process_group(process, timeout=10)
        """
        if process.poll() is not None:
            return  # Already terminated

        try:
            if self.is_windows():
                # Windows: terminate the process
                process.terminate()
            else:
                # Unix: terminate the process group
                pgid = os.getpgid(process.pid)
                os.killpg(pgid, signal.SIGTERM)

            # Wait for graceful shutdown
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Force kill if not responding
                if self.is_windows():
                    process.kill()
                else:
                    try:
                        os.killpg(pgid, signal.SIGKILL)  # type: ignore
                    except (NameError, UnboundLocalError):
                        process.kill()  # Fallback if pgid not defined
                process.wait()

        except Exception as e:
            # Try direct kill as fallback
            logger.warning(f"Error terminating process group: {e}")
            try:
                process.kill()
                process.wait()
            except Exception:
                pass  # Best effort


# Convenience functions for common use cases

def run_command(
    cmd: List[str],
    timeout: int = 30,
    check: bool = False,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Dict[str, str]] = None,
    context: Optional[str] = None,
) -> SubprocessResult:
    """Convenience function to run a command with default settings.

    This is a module-level function for one-off command execution without
    creating a SubprocessRunner instance.

    Args:
        cmd: Command and arguments as list
        timeout: Timeout in seconds
        check: If True, raise SubprocessError on failure
        cwd: Working directory
        env: Environment variables
        context: Human-readable context for error messages

    Returns:
        SubprocessResult with command output

    Example:
        >>> from amplihack.utils.subprocess_runner import run_command
        >>> result = run_command(["git", "status"], context="checking git status")
        >>> print(result.stdout)
    """
    runner = SubprocessRunner(default_timeout=timeout, log_commands=False)
    return runner.run_safe(
        cmd,
        timeout=timeout,
        check=check,
        cwd=cwd,
        env=env,
        context=context,
    )


def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH.

    Args:
        command: Command name to check

    Returns:
        True if command exists, False otherwise

    Example:
        >>> if check_command_exists("docker"):
        ...     print("Docker is installed")
    """
    runner = SubprocessRunner(log_commands=False)
    return runner.check_command_exists(command)
