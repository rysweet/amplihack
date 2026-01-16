"""MCP server for amplihack hook execution.

This server exposes amplihack hooks as MCP tools that can be triggered
by MCP clients like GitHub Copilot CLI.

Available tools:
- trigger_hook: Execute a hook
- list_hooks: Get list of available hooks
- get_hook_status: Get hook execution status
"""

import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import MCPServer, MCPTool, MCPServerError


class HooksMCPServer(MCPServer):
    """MCP server for hook execution.

    This server provides tools to trigger amplihack hooks.
    Hooks are discovered from the .claude/tools/ directory.
    """

    def __init__(self):
        """Initialize hooks MCP server."""
        self.hooks_dir = self._find_hooks_dir()
        self.hook_executions: dict[str, dict[str, Any]] = {}
        super().__init__(name="amplihack-hooks", version="1.0.0")

    def _find_hooks_dir(self) -> Path:
        """Find the hooks directory.

        Returns:
            Path to hooks directory

        Raises:
            MCPServerError: If hooks directory not found
        """
        # Try multiple locations
        search_paths = [
            Path.cwd() / ".claude" / "tools",
            Path.home() / ".claude" / "tools",
            Path(__file__).parent.parent.parent.parent / ".claude" / "tools"
        ]

        for path in search_paths:
            if path.exists() and path.is_dir():
                return path

        raise MCPServerError("Could not find hooks directory")

    def _discover_hooks(self) -> list[dict[str, str]]:
        """Discover available hooks.

        Returns:
            List of hook info dictionaries
        """
        hooks = []

        # Look for Python hook files
        for hook_file in self.hooks_dir.glob("*.py"):
            # Skip test files and __init__.py
            if hook_file.name.startswith("test_") or hook_file.name == "__init__.py":
                continue

            hook_name = hook_file.stem
            hooks.append({
                "name": hook_name,
                "path": str(hook_file),
                "type": "python"
            })

        # Also check xpia/hooks subdirectory
        xpia_hooks_dir = self.hooks_dir / "xpia" / "hooks"
        if xpia_hooks_dir.exists():
            for hook_file in xpia_hooks_dir.glob("*.py"):
                if hook_file.name.startswith("test_") or hook_file.name == "__init__.py":
                    continue

                hook_name = f"xpia_{hook_file.stem}"
                hooks.append({
                    "name": hook_name,
                    "path": str(hook_file),
                    "type": "xpia"
                })

        return hooks

    def _read_hook_description(self, hook_path: str) -> str:
        """Read hook description from Python file docstring.

        Args:
            hook_path: Path to hook Python file

        Returns:
            Hook description
        """
        try:
            with open(hook_path, 'r') as f:
                content = f.read()
                # Extract docstring
                if '"""' in content:
                    parts = content.split('"""')
                    if len(parts) >= 2:
                        docstring = parts[1].strip()
                        # Get first line
                        first_line = docstring.split('\n')[0].strip()
                        return first_line if first_line else "No description available"
                return "No description available"
        except Exception:
            return "No description available"

    def _register_tools(self) -> None:
        """Register hook tools."""
        # Tool: trigger_hook
        self.register_tool(MCPTool(
            name="trigger_hook",
            description="Execute a hook",
            input_schema={
                "type": "object",
                "properties": {
                    "hook_name": {
                        "type": "string",
                        "description": "Name of the hook to trigger"
                    },
                    "event": {
                        "type": "string",
                        "description": "Event type (e.g., 'session_start', 'pre_tool_use', 'post_tool_use')"
                    },
                    "data": {
                        "type": "object",
                        "description": "Event data to pass to the hook",
                        "additionalProperties": True
                    }
                },
                "required": ["hook_name", "event"]
            }
        ))

        # Tool: list_hooks
        self.register_tool(MCPTool(
            name="list_hooks",
            description="List all available hooks",
            input_schema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Filter by hook type: 'python' or 'xpia'",
                        "enum": ["python", "xpia"]
                    }
                }
            }
        ))

        # Tool: get_hook_status
        self.register_tool(MCPTool(
            name="get_hook_status",
            description="Get hook execution status",
            input_schema={
                "type": "object",
                "properties": {
                    "execution_id": {
                        "type": "string",
                        "description": "ID of the hook execution"
                    }
                },
                "required": ["execution_id"]
            }
        ))

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a hook tool.

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPServerError: If tool execution fails
        """
        if tool_name == "trigger_hook":
            return await self._trigger_hook(
                arguments["hook_name"],
                arguments["event"],
                arguments.get("data", {})
            )
        elif tool_name == "list_hooks":
            return self._list_hooks(arguments.get("type"))
        elif tool_name == "get_hook_status":
            return self._get_hook_status(arguments["execution_id"])
        else:
            raise MCPServerError(f"Unknown tool: {tool_name}")

    async def _trigger_hook(self, hook_name: str, event: str, data: dict[str, Any]) -> dict[str, Any]:
        """Trigger a hook execution.

        Args:
            hook_name: Hook name
            event: Event type
            data: Event data

        Returns:
            Hook execution result
        """
        # Find hook file
        hooks = self._discover_hooks()
        hook_info = next((h for h in hooks if h["name"] == hook_name), None)

        if not hook_info:
            raise MCPServerError(f"Hook not found: {hook_name}")

        # Create execution ID
        execution_id = f"{hook_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Store execution info
        self.hook_executions[execution_id] = {
            "id": execution_id,
            "hook_name": hook_name,
            "event": event,
            "status": "triggered",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "result": None
        }

        # For now, return a simulation result
        # In a full implementation, this would actually execute the hook
        result = {
            "execution_id": execution_id,
            "hook_name": hook_name,
            "event": event,
            "status": "simulated",
            "message": f"Hook '{hook_name}' triggered for event '{event}'",
            "note": "Full hook execution requires Claude Code integration"
        }

        # Update execution record
        self.hook_executions[execution_id]["status"] = "completed"
        self.hook_executions[execution_id]["completed_at"] = datetime.now().isoformat()
        self.hook_executions[execution_id]["result"] = result

        return result

    def _list_hooks(self, hook_type: str | None = None) -> dict[str, Any]:
        """List available hooks.

        Args:
            hook_type: Optional type filter

        Returns:
            List of hooks
        """
        hooks = self._discover_hooks()

        if hook_type:
            hooks = [h for h in hooks if h["type"] == hook_type]

        # Add descriptions
        for hook in hooks:
            hook["description"] = self._read_hook_description(hook["path"])

        return {
            "count": len(hooks),
            "hooks": hooks
        }

    def _get_hook_status(self, execution_id: str) -> dict[str, Any]:
        """Get hook execution status.

        Args:
            execution_id: Execution ID

        Returns:
            Hook execution status

        Raises:
            MCPServerError: If execution not found
        """
        if execution_id not in self.hook_executions:
            raise MCPServerError(f"Hook execution not found: {execution_id}")

        return self.hook_executions[execution_id]


async def main():
    """Main entry point for hooks MCP server."""
    try:
        server = HooksMCPServer()
        await server.run()
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32000,
                "message": f"Server initialization failed: {str(e)}"
            }
        }
        print(json.dumps(error_response))


if __name__ == "__main__":
    asyncio.run(main())
