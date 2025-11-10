"""Base class for Claude command-line interactions."""

import subprocess
from typing import Tuple


class ClaudeCaller:
    """Base class providing common Claude CLI subprocess operations."""

    def __init__(self, claude_cmd: str = "claude"):
        """Initialize Claude caller.

        Args:
            claude_cmd: Claude command to use (default: "claude")
        """
        self.claude_cmd = claude_cmd

    def _call_claude(self, prompt: str) -> Tuple[bool, str, str]:
        """Call Claude CLI with a prompt.

        Args:
            prompt: Prompt to send to Claude

        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        result = subprocess.run(
            [self.claude_cmd, "--dangerously-skip-permissions", "-p", prompt],
            capture_output=True,
            text=True,
            check=False,
        )

        success = result.returncode == 0
        return success, result.stdout, result.stderr
