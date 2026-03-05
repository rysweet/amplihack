"""Recipe execution adapters.

Exports the SDKAdapter protocol, a factory function for selecting
the best available adapter, and a shared utility for building clean
child-process environments.
"""

from __future__ import annotations

from amplihack.recipes.adapters.base import SDKAdapter
from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter
from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter
from amplihack.recipes.adapters.env import build_child_env
from amplihack.recipes.adapters.nested_session import NestedSessionAdapter

__all__ = [
    "SDKAdapter",
    "ClaudeSDKAdapter",
    "CLISubprocessAdapter",
    "NestedSessionAdapter",
    "build_child_env",
    "get_adapter",
]


def get_adapter(
    preference: str | None = None,
) -> ClaudeSDKAdapter | CLISubprocessAdapter | NestedSessionAdapter:
    """Return the best available adapter, optionally preferring a specific backend.

    Args:
        preference: Optional backend name (``"claude-sdk"``, ``"cli"``, ``"nested"``).

    Returns:
        An adapter instance.
    """
    if preference == "nested":
        return NestedSessionAdapter()
    if preference == "cli":
        return CLISubprocessAdapter()
    if preference == "claude-sdk":
        return ClaudeSDKAdapter()

    # Auto-detect best adapter
    # Priority 1: try Claude SDK first
    claude = ClaudeSDKAdapter()
    if claude.is_available():
        return claude

    # Priority 2: CLI fallback
    return CLISubprocessAdapter()
