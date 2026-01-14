"""Lock tool module for Amplifier.

Provides the 'lock' tool for managing continuous work mode.

Usage in bundle/profile:
    modules:
      tools:
        - module: tool-lock

Or install via:
    amplifier module add tool-lock --type tool
"""

from __future__ import annotations

from typing import Any

from .lock_tool import LockTool, ToolResult

__amplifier_module_type__ = "tool"
__version__ = "0.1.0"
__all__ = ["mount", "LockTool", "ToolResult"]


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> None:
    """Mount the lock tool into the session.

    This is the Amplifier module entry point. Called during session initialization
    to register the tool with the coordinator.

    Args:
        coordinator: The Amplifier session coordinator
        config: Optional configuration passed from bundle/profile
    """
    tool = LockTool(config=config)

    # Get or create tools registry
    tools = coordinator.get("tools")
    if tools is None:
        tools = {}
        await coordinator.mount("tools", tools)

    # Register the tool by name
    tools[tool.name] = tool
