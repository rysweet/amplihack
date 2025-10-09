"""Claude-trace integration - ruthlessly simple implementation.

Claude-trace is a required dependency installed via:
    npm install -g @mariozechner/claude-trace

Set AMPLIHACK_USE_TRACE=0 to explicitly disable and use plain 'claude'.
"""

import os


def should_use_trace() -> bool:
    """Check if claude-trace should be used instead of claude.

    Default: Always use claude-trace (assumes it's installed as dependency).
    Set AMPLIHACK_USE_TRACE=0 to disable.
    """
    use_trace_env = os.getenv("AMPLIHACK_USE_TRACE", "1").lower()
    return use_trace_env not in ("0", "false", "no")


def get_claude_command() -> str:
    """Get the appropriate claude command.

    Returns:
        'claude-trace' (default) or 'claude' (if explicitly disabled)
    """
    return "claude-trace" if should_use_trace() else "claude"
