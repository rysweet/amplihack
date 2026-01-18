#!/usr/bin/env python3
"""
Claude Code hook for post tool use events.
Uses unified HookProcessor for common functionality.

Uses extensible tool registry system for multiple tool hooks.
"""

# Import the base processor
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

# Import tool registry for extensible hook system
try:
    from tool_registry import aggregate_hook_results, get_global_registry

    TOOL_REGISTRY_AVAILABLE = True
except ImportError:
    TOOL_REGISTRY_AVAILABLE = False


class PostToolUseHook(HookProcessor):
    """Hook processor for post tool use events."""

    def __init__(self):
        super().__init__("post_tool_use")
        self.strategy = None
        self._setup_tool_hooks()

    def _setup_tool_hooks(self):
        """Setup all tool hooks (context management, etc.)."""
        if not TOOL_REGISTRY_AVAILABLE:
            self.log("Tool registry not available - hooks disabled", "DEBUG")
            return

        # Import and register context management hook
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from context_automation_hook import register_context_hook

            register_context_hook()  # Registers with global registry
            self.log("Context management hook registered", "DEBUG")
        except ImportError as e:
            self.log(f"Context management hook not available: {e}", "DEBUG")

        # Future: Add more tool hooks here
        # from other_tool_hook import register_other_hook
        # register_other_hook()

    def save_tool_metric(self, tool_name: str, duration_ms: int | None = None):
        """Save tool usage metric with structured data.

        Args:
            tool_name: Name of the tool used
            duration_ms: Duration in milliseconds (if available)
        """
        metadata = {}
        if duration_ms is not None:
            metadata["duration_ms"] = duration_ms

        self.save_metric("tool_usage", tool_name, metadata)

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process post tool use event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Empty dict or validation messages
        """
        # Detect launcher and select strategy
        self.strategy = self._select_strategy()
        if self.strategy:
            self.log(f"Using strategy: {self.strategy.__class__.__name__}")
            # Check for strategy-specific post-tool handling
            strategy_result = self.strategy.handle_post_tool_use(input_data)
            if strategy_result:
                self.log("Strategy provided custom post-tool handling")
                return strategy_result

        # Extract tool information
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "unknown")

        # Extract result if available (not currently used but could be useful)
        result = input_data.get("result", {})

        self.log(f"Tool used: {tool_name}")

        # Save metrics - could extract duration from result if available
        duration_ms = None
        if isinstance(result, dict):
            # Some tools might include timing information
            duration_ms = result.get("duration_ms")

        self.save_tool_metric(tool_name, duration_ms)

        # Check for specific tool types that might need validation
        output = {}
        if tool_name in ["Write", "Edit", "MultiEdit"]:
            # Could add validation or checks here
            # For example, check if edits were successful
            if isinstance(result, dict) and result.get("error"):
                self.log(f"Tool {tool_name} reported error: {result.get('error')}", "WARNING")
                # Could return a suggestion or alert
                output["metadata"] = {
                    "warning": f"Tool {tool_name} encountered an error",
                    "tool": tool_name,
                }

        # Track high-level metrics
        if tool_name == "Bash":
            self.save_metric("bash_commands", 1)
        elif tool_name in ["Read", "Write", "Edit", "MultiEdit"]:
            self.save_metric("file_operations", 1)
        elif tool_name in ["Grep", "Glob"]:
            self.save_metric("search_operations", 1)

        # Execute registered tool hooks via registry
        if TOOL_REGISTRY_AVAILABLE:
            try:
                registry = get_global_registry()
                hook_results = registry.execute_hooks(input_data)

                # Aggregate results from all hooks
                aggregated = aggregate_hook_results(hook_results)

                # Add warnings and metadata to output
                if aggregated["warnings"] or aggregated["metadata"]:
                    if "metadata" not in output:
                        output["metadata"] = {}

                    # Add aggregated metadata
                    for key, value in aggregated["metadata"].items():
                        output["metadata"][key] = value

                    # Add warnings list if present
                    if aggregated["warnings"]:
                        output["metadata"]["warnings"] = aggregated["warnings"]

                # Log actions taken by hooks
                for action in aggregated["actions_taken"]:
                    self.log(f"Tool Hook Action: {action}", "INFO")

                # Log warnings
                for warning in aggregated["warnings"]:
                    self.log(f"Tool Hook Warning: {warning}", "INFO")

            except Exception as e:
                # Silently fail - don't interrupt user workflow
                self.log(f"Tool registry error: {e}", "DEBUG")

        return output

    def _select_strategy(self):
        """Detect launcher and select appropriate strategy."""
        try:
            # Import adaptive components
            sys.path.insert(0, str(self.project_root / "src" / "amplihack"))
            from amplihack.context.adaptive.detector import LauncherDetector
            from amplihack.context.adaptive.strategies import ClaudeStrategy, CopilotStrategy

            detector = LauncherDetector(self.project_root)
            launcher_type = detector.detect()

            if launcher_type == "copilot":
                return CopilotStrategy(self.project_root, self.log)
            else:
                return ClaudeStrategy(self.project_root, self.log)

        except ImportError as e:
            self.log(f"Adaptive strategy not available: {e}", "DEBUG")
            return None


def main():
    """Entry point for the post tool use hook."""
    hook = PostToolUseHook()
    hook.run()


if __name__ == "__main__":
    main()
