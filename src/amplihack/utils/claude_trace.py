"""Claude-trace integration - ruthlessly simple implementation."""

import os
import shutil
import subprocess


def should_use_trace() -> bool:
    """Check if claude-trace should be used instead of claude."""
    return os.getenv("AMPLIHACK_USE_TRACE", "").lower() in ("1", "true", "yes")


def get_claude_command() -> str:
    """Get the appropriate claude command (claude or claude-trace).

    Returns:
        Command name to use ('claude' or 'claude-trace')

    Side Effects:
        May attempt to install claude-trace via npm if requested but not found
    """
    if not should_use_trace():
        return "claude"

    # Check if claude-trace is available
    if shutil.which("claude-trace"):
        return "claude-trace"

    # Try to install claude-trace
    if _install_claude_trace():
        return "claude-trace"

    # Fall back to claude
    return "claude"


def _install_claude_trace() -> bool:
    """Attempt to install claude-trace via npm.

    Returns:
        True if installation succeeded, False otherwise
    """
    try:
        # Check if npm is available
        if not shutil.which("npm"):
            return False

        # Install claude-trace globally
        result = subprocess.run(
            ["npm", "install", "-g", "@mariozechner/claude-trace"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        return result.returncode == 0

    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False
