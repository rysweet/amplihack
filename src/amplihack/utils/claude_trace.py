"""Claude-trace integration - ruthlessly simple implementation."""

import os
import shutil
import subprocess


def should_use_trace() -> bool:
    """Check if claude-trace should be used instead of claude.

    Default behavior: Always prefer claude-trace unless explicitly disabled.
    """
    # Check if explicitly disabled
    use_trace_env = os.getenv("AMPLIHACK_USE_TRACE", "").lower()
    if use_trace_env in ("0", "false", "no"):
        return False

    # Default to using claude-trace
    return True


def get_claude_command() -> str:
    """Get the appropriate claude command (claude or claude-trace).

    Returns:
        Command name to use ('claude' or 'claude-trace')

    Side Effects:
        May attempt to install claude-trace via npm if not found
    """
    if not should_use_trace():
        print("Claude-trace explicitly disabled via AMPLIHACK_USE_TRACE=0")
        return "claude"

    # Check if claude-trace is available
    if shutil.which("claude-trace"):
        print("Using claude-trace for enhanced debugging")
        return "claude-trace"

    # Try to install claude-trace
    print("Claude-trace not found, attempting to install...")
    if _install_claude_trace():
        print("Claude-trace installed successfully")
        return "claude-trace"

    # Fall back to claude
    print("Could not install claude-trace, falling back to standard claude")
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
