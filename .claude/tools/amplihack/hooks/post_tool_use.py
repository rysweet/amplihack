#!/usr/bin/env python3
"""
Claude Code hook for post tool use events.
Uses unified HookProcessor for common functionality.
"""

# Import the base processor
import sys
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class PostToolUseHook(HookProcessor):
    """Hook processor for post tool use events."""

    def __init__(self):
        super().__init__("post_tool_use")

    def save_tool_metric(self, tool_name: str, duration_ms: Optional[int] = None):
        """Save tool usage metric with structured data.

        Args:
            tool_name: Name of the tool used
            duration_ms: Duration in milliseconds (if available)
        """
        metadata = {}
        if duration_ms is not None:
            metadata["duration_ms"] = duration_ms

        self.save_metric("tool_usage", tool_name, metadata)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process post tool use event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Empty dict or validation messages
        """
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

        return output


def main():
    """Entry point for the post tool use hook."""
    hook = PostToolUseHook()
    hook.run()


if __name__ == "__main__":
    main()
