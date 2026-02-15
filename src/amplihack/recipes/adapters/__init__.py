"""Recipe execution adapters.

Exports the SDKAdapter protocol and a factory function for selecting
the best available adapter.
"""

from __future__ import annotations

from amplihack.recipes.adapters.base import SDKAdapter
from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter
from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter
from amplihack.recipes.adapters.nested_session import NestedSessionAdapter

__all__ = [
    "SDKAdapter",
    "ClaudeSDKAdapter",
    "CLISubprocessAdapter",
    "NestedSessionAdapter",
    "get_adapter",
]


def get_adapter(
    preference: str | None = None,
) -> ClaudeSDKAdapter | CLISubprocessAdapter | NestedSessionAdapter:
    """Return the best available adapter, optionally preferring a specific backend.

    Auto-detects nested Claude Code sessions and uses NestedSessionAdapter when needed.

    Args:
        preference: Optional backend name (``"claude-sdk"``, ``"cli"``, ``"nested"``).

    Returns:
        An adapter instance.
    """
    import os

    # Check if we're in a nested Claude Code session
    in_claude_session = "CLAUDECODE" in os.environ

    if preference == "nested":
        return NestedSessionAdapter()
    if preference == "cli":
        return CLISubprocessAdapter()
    if preference == "claude-sdk":
        return ClaudeSDKAdapter()

    # Auto-detect best adapter
    # Priority 1: If nested session, use NestedSessionAdapter
    if in_claude_session:
        return NestedSessionAdapter()

    # Priority 2: try Claude SDK first
    claude = ClaudeSDKAdapter()
    if claude.is_available():
        return claude

    # Priority 3: CLI fallback
    return CLISubprocessAdapter()
