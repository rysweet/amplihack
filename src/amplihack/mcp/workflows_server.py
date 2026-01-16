"""MCP server for amplihack workflow orchestration.

This server exposes amplihack workflows as MCP tools that can be orchestrated
by MCP clients like GitHub Copilot CLI.

Available tools:
- start_workflow: Start a workflow execution
- execute_step: Execute a specific workflow step
- get_workflow_state: Get current workflow execution state
- list_workflows: Get list of available workflows
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import MCPServer, MCPTool, MCPServerError


class WorkflowsMCPServer(MCPServer):
    """MCP server for workflow orchestration.

    This server provides tools to orchestrate amplihack workflows.
    Workflows are discovered from the .claude/workflow/ directory.
    """

    def __init__(self):
        """Initialize workflows MCP server."""
        self.workflows_dir = self._find_workflows_dir()
        self.workflow_states: dict[str, dict[str, Any]] = {}
        super().__init__(name="amplihack-workflows", version="1.0.0")

    def _find_workflows_dir(self) -> Path:
        """Find the workflows directory.

        Returns:
            Path to workflows directory

        Raises:
            MCPServerError: If workflows directory not found
        """
        # Try multiple locations
        search_paths = [
            Path.cwd() / ".claude" / "workflow",
            Path.home() / ".claude" / "workflow",
            Path(__file__).parent.parent.parent.parent / ".claude" / "workflow"
        ]

        for path in search_paths:
            if path.exists() and path.is_dir():
                return path

        raise MCPServerError("Could not find workflows directory")

    def _discover_workflows(self) -> list[dict[str, str]]:
        """Discover available workflows.

        Returns:
            List of workflow info dictionaries
        """
        workflows = []

        for workflow_file in self.workflows_dir.glob("*.md"):
            # Skip template and README files
            if workflow_file.name in ["README.md", "WORKFLOW_TEMPLATE.md"]:
                continue

            workflow_name = workflow_file.stem
            workflows.append({
                "name": workflow_name,
                "path": str(workflow_file)
            })

        return workflows

    def _read_workflow_description(self, workflow_path: str) -> str:
        """Read workflow description from markdown file.

        Args:
            workflow_path: Path to workflow markdown file

        Returns:
            Workflow description
        """
        try:
            with open(workflow_path, 'r') as f:
                content = f.read()
                # Extract first paragraph
                lines = content.split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        return line.strip()
                return "No description available"
        except Exception:
            return "No description available"

    def _parse_workflow_steps(self, workflow_path: str) -> list[dict[str, Any]]:
        """Parse workflow steps from markdown file.

        Args:
            workflow_path: Path to workflow markdown file

        Returns:
            List of workflow steps
        """
        steps = []
        try:
            with open(workflow_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')

                for i, line in enumerate(lines):
                    # Look for step headers (## Step N:)
                    if line.startswith('## Step ') or line.startswith('## Phase '):
                        step_name = line.replace('##', '').strip()
                        # Get description (next non-empty line)
                        description = ""
                        for next_line in lines[i+1:i+5]:
                            if next_line.strip() and not next_line.startswith('#'):
                                description = next_line.strip()
                                break

                        steps.append({
                            "name": step_name,
                            "description": description
                        })
        except Exception as e:
            pass

        return steps

    def _register_tools(self) -> None:
        """Register workflow tools."""
        # Tool: start_workflow
        self.register_tool(MCPTool(
            name="start_workflow",
            description="Start a workflow execution",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow_name": {
                        "type": "string",
                        "description": "Name of the workflow to start (e.g., 'DEFAULT_WORKFLOW', 'INVESTIGATION_WORKFLOW')"
                    },
                    "context": {
                        "type": "object",
                        "description": "Context information for the workflow",
                        "additionalProperties": True
                    }
                },
                "required": ["workflow_name"]
            }
        ))

        # Tool: execute_step
        self.register_tool(MCPTool(
            name="execute_step",
            description="Execute a specific workflow step",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "ID of the workflow execution"
                    },
                    "step_number": {
                        "type": "integer",
                        "description": "Step number to execute"
                    }
                },
                "required": ["workflow_id", "step_number"]
            }
        ))

        # Tool: get_workflow_state
        self.register_tool(MCPTool(
            name="get_workflow_state",
            description="Get current workflow execution state",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "ID of the workflow execution"
                    }
                },
                "required": ["workflow_id"]
            }
        ))

        # Tool: list_workflows
        self.register_tool(MCPTool(
            name="list_workflows",
            description="List all available workflows",
            input_schema={
                "type": "object",
                "properties": {}
            }
        ))

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a workflow tool.

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPServerError: If tool execution fails
        """
        if tool_name == "start_workflow":
            return await self._start_workflow(
                arguments["workflow_name"],
                arguments.get("context", {})
            )
        elif tool_name == "execute_step":
            return await self._execute_step(
                arguments["workflow_id"],
                arguments["step_number"]
            )
        elif tool_name == "get_workflow_state":
            return self._get_workflow_state(arguments["workflow_id"])
        elif tool_name == "list_workflows":
            return self._list_workflows()
        else:
            raise MCPServerError(f"Unknown tool: {tool_name}")

    async def _start_workflow(self, workflow_name: str, context: dict[str, Any]) -> dict[str, Any]:
        """Start a workflow execution.

        Args:
            workflow_name: Workflow name
            context: Context information

        Returns:
            Workflow execution info
        """
        # Find workflow file
        workflows = self._discover_workflows()
        workflow_info = next((w for w in workflows if w["name"] == workflow_name), None)

        if not workflow_info:
            raise MCPServerError(f"Workflow not found: {workflow_name}")

        # Parse workflow steps
        steps = self._parse_workflow_steps(workflow_info["path"])

        # Create workflow execution state
        workflow_id = f"{workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.workflow_states[workflow_id] = {
            "id": workflow_id,
            "workflow_name": workflow_name,
            "status": "started",
            "current_step": 0,
            "steps": steps,
            "context": context,
            "started_at": datetime.now().isoformat(),
            "completed_at": None
        }

        return {
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "status": "started",
            "total_steps": len(steps),
            "steps": steps
        }

    async def _execute_step(self, workflow_id: str, step_number: int) -> dict[str, Any]:
        """Execute a workflow step.

        Args:
            workflow_id: Workflow execution ID
            step_number: Step number

        Returns:
            Step execution result
        """
        if workflow_id not in self.workflow_states:
            raise MCPServerError(f"Workflow not found: {workflow_id}")

        state = self.workflow_states[workflow_id]
        steps = state["steps"]

        if step_number < 0 or step_number >= len(steps):
            raise MCPServerError(f"Invalid step number: {step_number}")

        # Update state
        state["current_step"] = step_number
        step = steps[step_number]

        return {
            "workflow_id": workflow_id,
            "step_number": step_number,
            "step": step,
            "status": "executed",
            "message": f"Executed step {step_number}: {step['name']}",
            "note": "Full step execution requires Claude Code integration"
        }

    def _get_workflow_state(self, workflow_id: str) -> dict[str, Any]:
        """Get workflow execution state.

        Args:
            workflow_id: Workflow execution ID

        Returns:
            Workflow state

        Raises:
            MCPServerError: If workflow not found
        """
        if workflow_id not in self.workflow_states:
            raise MCPServerError(f"Workflow not found: {workflow_id}")

        return self.workflow_states[workflow_id]

    def _list_workflows(self) -> dict[str, Any]:
        """List available workflows.

        Returns:
            List of workflows
        """
        workflows = self._discover_workflows()

        # Add descriptions
        for workflow in workflows:
            workflow["description"] = self._read_workflow_description(workflow["path"])

        return {
            "count": len(workflows),
            "workflows": workflows
        }


async def main():
    """Main entry point for workflows MCP server."""
    try:
        server = WorkflowsMCPServer()
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
