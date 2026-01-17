"""Post Tool Use Hook - Amplifier wrapper for tool execution tracking.

Handles post-tool-use processing including:
- Delegating to Claude Code post_tool_use hook
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
# Path: __init__.py -> amplifier_hook_post_tool_use/ -> hook-post-tool-use/ -> modules/ -> amplifier-bundle/ -> amplifier-amplihack/
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
_CLAUDE_HOOKS = _PROJECT_ROOT / ".claude" / "tools" / "amplihack" / "hooks"

_DELEGATION_AVAILABLE = False
_IMPORT_ERROR: str | None = None

if _CLAUDE_HOOKS.exists():
    if str(_CLAUDE_HOOKS) not in sys.path:
        sys.path.insert(0, str(_CLAUDE_HOOKS))
    if str(_CLAUDE_HOOKS.parent) not in sys.path:
        sys.path.insert(0, str(_CLAUDE_HOOKS.parent))

    # Verify the import works
    try:
        import post_tool_use  # noqa: F401

        _DELEGATION_AVAILABLE = True
        logger.info(f"PostToolUseHook: Delegation available from {_CLAUDE_HOOKS}")
    except ImportError as e:
        _IMPORT_ERROR = str(e)
        logger.warning(f"PostToolUseHook: Import failed - {e}")
else:
    _IMPORT_ERROR = f"Claude hooks directory not found: {_CLAUDE_HOOKS}"
    logger.warning(_IMPORT_ERROR)


class PostToolUseHook(Hook):
    """Tool execution tracking and registry hook."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._claude_hook = None
        self._delegation_attempted = False
        self._tool_registry = None
        self._registry_checked = False

    def _get_claude_hook(self):
        """Lazy load post tool use hook from Claude Code."""
        if not self._delegation_attempted:
            self._delegation_attempted = True
            if _DELEGATION_AVAILABLE:
                try:
                    from post_tool_use import PostToolUseHook as ClaudePostToolUseHook

                    self._claude_hook = ClaudePostToolUseHook()
                    logger.info("PostToolUseHook: Delegating to Claude Code hook")
                except ImportError as e:
                    logger.warning(f"PostToolUseHook: Claude Code delegation failed: {e}")
                    self._claude_hook = None
            else:
                logger.info(f"PostToolUseHook: Using fallback ({_IMPORT_ERROR})")
        return self._claude_hook

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
                    logger.debug("context_automation_hook not available")

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

            # Try to delegate to Claude Code hook first
            claude_hook = self._get_claude_hook()
            if claude_hook:
                try:
                    hook_result = claude_hook.process(data)
                    if hook_result:
                        metadata["delegation"] = "success"
                        if hook_result.get("metadata"):
                            metadata.update(hook_result["metadata"])
                        logger.debug(f"PostToolUseHook: Delegated for {tool_name}")
                except Exception as e:
                    logger.warning(f"Claude Code post tool use hook failed: {e}")
                    metadata["delegation"] = "execution_failed"
            else:
                metadata["delegation"] = "fallback"

            # Track tool categories (fallback behavior)
            if tool_name == "bash":
                metadata["category"] = "bash_commands"
            elif tool_name in ["read_file", "write_file", "edit_file"]:
                metadata["category"] = "file_operations"
            elif tool_name in ["grep", "glob"]:
                metadata["category"] = "search_operations"

            # Check for errors in file operations
            if tool_name in ["write_file", "edit_file"]:
                if isinstance(result, dict) and result.get("error"):
                    warnings.append(f"Tool {tool_name} encountered an error: {result.get('error')}")
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
