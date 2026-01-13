"""XPIA Defense Hook Module for Amplifier.

Provides cross-prompt injection attack detection for tool calls and user prompts.

Usage in bundle/profile:
    modules:
      hooks:
        - module: hook-xpia-defense
          config:
            mode: standard  # standard, strict, or learning
            block_on_critical: true

Or install via:
    amplifier module add hook-xpia-defense --type hook
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .xpia_hook import HookResult, XPIADefenseHook

if TYPE_CHECKING:
    pass

__amplifier_module_type__ = "hook"
__version__ = "0.1.0"
__all__ = ["mount", "XPIADefenseHook", "HookResult"]

# Events this hook observes
HOOK_EVENTS = [
    "tool:call:before",
    "prompt:submit:before",
]


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> None:
    """Mount the XPIA defense hook into the session.

    This is the Amplifier module entry point. Called during session initialization
    to register the hook with the coordinator.

    Args:
        coordinator: The Amplifier session coordinator
        config: Optional configuration passed from bundle/profile
            - mode: 'standard' (default), 'strict', or 'learning'
            - block_on_critical: Whether to block critical threats (default: True)
            - log_all: Whether to log all checks, not just threats (default: False)
    """
    hook = XPIADefenseHook(config=config)

    # Get or create hooks registry
    hooks = coordinator.get("hooks")
    if hooks is None:
        hooks = {}
        await coordinator.mount("hooks", hooks)

    # Register for each event
    for event in HOOK_EVENTS:
        if event not in hooks:
            hooks[event] = []
        hooks[event].append(hook)
