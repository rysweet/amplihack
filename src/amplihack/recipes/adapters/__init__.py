"""Recipe execution adapters.

Exports the SDKAdapter protocol and a factory function for selecting
the best available adapter.
"""

from __future__ import annotations

from amplihack.recipes.adapters.base import SDKAdapter
from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter
from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter

__all__ = [
    "SDKAdapter",
    "ClaudeSDKAdapter",
    "CLISubprocessAdapter",
    "get_adapter",
]


def get_adapter(
    preference: str | None = None,
) -> ClaudeSDKAdapter | CLISubprocessAdapter:
    """Return the best available adapter, optionally preferring a specific backend.

    Args:
        preference: Optional backend name (``"claude-sdk"``, ``"cli"``).

    Returns:
        An adapter instance.
    """
    if preference == "cli":
        return CLISubprocessAdapter()
    if preference == "claude-sdk":
        return ClaudeSDKAdapter()

    # Auto-detect: try Claude SDK first, then CLI fallback
    claude = ClaudeSDKAdapter()
    if claude.is_available():
        return claude

    return CLISubprocessAdapter()
