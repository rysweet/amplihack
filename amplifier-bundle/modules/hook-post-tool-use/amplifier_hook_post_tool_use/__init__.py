"""Post Tool Use Hook - Amplifier wrapper for tool execution tracking.

Handles post-tool-use processing including:
- Tool usage metrics tracking
- Extensible tool registry for multiple tool hooks
- Error detection and warnings for file operations
- Context management hook execution
"""

import logging
import sys
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

# Add Claude Code hooks to path for imports
_CLAUDE_HOOKS = (
    Path(__file__).parent.parent.parent.parent.parent.parent
    / ".claude"
    / "tools"
    / "amplihack"
    / "hooks"
)
if _CLAUDE_HOOKS.exists():
    sys.path.insert(0, str(_CLAUDE_HOOKS))
    sys.path.insert(0, str(_CLAUDE_HOOKS.parent))


class PostToolUseHook(Hook):
    """Tool execution tracking and registry hook."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._tool_registry = None
        self._registry_checked = False

    def _get_tool_registry(self):
        """Lazy load tool registry."""
        if not self._registry_checked:
            self._registry_checked = True
            try:
                from tool_registry import get_global_registry

                self._tool_registry = get_global_registry()

                # Register context management hook if available
                try:
                    from context_automation_hook import register_context_hook

                    register_context_hook()
                    logger.debug("Context management hook registered")
                except ImportError:
                    pass

            except ImportError as e:
                logger.debug(f"Tool registry not available: {e}")
                self._tool_registry = None
        return self._tool_registry

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle tool:post events for tracking and validation."""
        if not self.enabled:
            return None

        if event != "tool:post":
            return None

        try:
            tool_use = data.get("tool_use", data.get("toolUse", {}))
            tool_name = tool_use.get("name", data.get("tool_name", "unknown"))
            result = data.get("result", {})

            metadata = {"tool_name": tool_name}
            warnings = []

            # Track tool categories
            if tool_name == "bash":
                metadata["category"] = "bash_commands"
            elif tool_name in ["read_file", "write_file", "edit_file"]:
                metadata["category"] = "file_operations"
            elif tool_name in ["grep", "glob"]:
                metadata["category"] = "search_operations"

            # Check for errors in file operations
            if tool_name in ["write_file", "edit_file"]:
                if isinstance(result, dict) and result.get("error"):
                    warnings.append(
                        f"Tool {tool_name} encountered an error: {result.get('error')}"
                    )
                    metadata["has_error"] = True

            # Execute registered tool hooks via registry
            registry = self._get_tool_registry()
            if registry:
                try:
                    from tool_registry import aggregate_hook_results

                    hook_results = registry.execute_hooks(data)
                    aggregated = aggregate_hook_results(hook_results)

                    # Add registry results
                    if aggregated.get("warnings"):
                        warnings.extend(aggregated["warnings"])
                    if aggregated.get("metadata"):
                        metadata.update(aggregated["metadata"])
                    if aggregated.get("actions_taken"):
                        for action in aggregated["actions_taken"]:
                            logger.info(f"Tool hook action: {action}")

                except Exception as e:
                    logger.debug(f"Tool registry execution failed: {e}")

            # Log warnings
            for warning in warnings:
                logger.warning(warning)

            if warnings:
                metadata["warnings"] = warnings

            return HookResult(modified_data=data, metadata=metadata)

        except Exception as e:
            # Fail open - don't interrupt tool workflow
            logger.debug(f"Post tool use hook failed (continuing): {e}")

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the post tool use hook."""
    hook = PostToolUseHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["PostToolUseHook", "mount"]
