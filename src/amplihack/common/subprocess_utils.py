"""Common subprocess utilities for running external commands safely."""

import logging
import subprocess
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class SubprocessError(Exception):
    """Base exception for subprocess operations."""


class CommandNotFoundError(SubprocessError):
    """Raised when command is not found."""


def run_command(
    cmd: List[str],
    timeout: Optional[float] = None,
    check: bool = False,
    capture_output: bool = True,
    text: bool = True,
) -> Tuple[int, str, str]:
    """Run command safely with standard error handling.

    Args:
        cmd: Command as list of strings
        timeout: Timeout in seconds (None = no timeout)
        check: Raise exception if return code != 0
        capture_output: Capture stdout and stderr
        text: Return output as text (not bytes)

    Returns:
        Tuple of (return_code, stdout, stderr)

    Raises:
        SubprocessError: If check=True and command fails
        TimeoutError: If timeout is exceeded
    """
    try:
        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=capture_output,
            text=text,
            check=False,
        )

        if check and result.returncode != 0:
            error_msg = result.stderr or result.stdout or f"Command failed with code {result.returncode}"
            raise SubprocessError(f"Command failed: {' '.join(cmd)}\n{error_msg}")

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired as e:
        raise TimeoutError(f"Command timed out after {timeout}s: {' '.join(cmd)}") from e
    except FileNotFoundError as e:
        raise CommandNotFoundError(f"Command not found: {cmd[0]}") from e
    except Exception as e:
        logger.error(f"Subprocess error running {cmd}: {e}")
        raise SubprocessError(f"Failed to run command {cmd}: {e}") from e


def run_claude_command(
    prompt: str,
    claude_cmd: str = "claude",
    timeout: Optional[float] = None,
    dangerously_skip_permissions: bool = True,
) -> Tuple[int, str, str]:
    """Run Claude command with standard options.

    Args:
        prompt: Prompt text to send to Claude
        claude_cmd: Claude command name (default: "claude")
        timeout: Timeout in seconds
        dangerously_skip_permissions: Skip permission checks

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    cmd = [claude_cmd]

    if dangerously_skip_permissions:
        cmd.append("--dangerously-skip-permissions")

    cmd.extend(["-p", prompt])

    return run_command(cmd, timeout=timeout, check=False, capture_output=True, text=True)


def check_command_exists(command: str) -> bool:
    """Check if command exists in PATH.

    Args:
        command: Command name to check

    Returns:
        True if command exists, False otherwise
    """
    try:
        result = subprocess.run(
            ["which", command],
            capture_output=True,
            timeout=5.0,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False
