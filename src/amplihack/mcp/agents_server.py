"""MCP server for amplihack agent invocation.

This server exposes amplihack agents as MCP tools that can be invoked
by MCP clients like GitHub Copilot CLI.

Available tools:
- invoke_agent: Execute an agent with a specific task
- list_agents: Get list of available agents
- get_agent_info: Get detailed information about an agent
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .base import MCPServer, MCPTool, MCPServerError


class AgentsMCPServer(MCPServer):
    """MCP server for agent invocation.

    This server provides tools to invoke amplihack agents programmatically.
    Agents are discovered from the .claude/agents/amplihack/ directory.
    """

    def __init__(self):
        """Initialize agents MCP server."""
        self.agents_dir = self._find_agents_dir()
        super().__init__(name="amplihack-agents", version="1.0.0")

    def _find_agents_dir(self) -> Path:
        """Find the agents directory.

        Returns:
            Path to agents directory

        Raises:
            MCPServerError: If agents directory not found
        """
        # Try multiple locations
        search_paths = [
            Path.cwd() / ".claude" / "agents" / "amplihack",
            Path.home() / ".claude" / "agents" / "amplihack",
            Path(__file__).parent.parent.parent.parent / ".claude" / "agents" / "amplihack"
        ]

        for path in search_paths:
            if path.exists() and path.is_dir():
                return path

        raise MCPServerError("Could not find agents directory")

    def _discover_agents(self) -> list[dict[str, str]]:
        """Discover available agents.

        Returns:
            List of agent info dictionaries
        """
        agents = []

        # Scan core and specialized directories
        for subdir in ["core", "specialized"]:
            agent_dir = self.agents_dir / subdir
            if not agent_dir.exists():
                continue

            for agent_file in agent_dir.glob("*.md"):
                agent_name = agent_file.stem
                agents.append({
                    "name": agent_name,
                    "type": subdir,
                    "path": str(agent_file)
                })

        return agents

    def _read_agent_description(self, agent_path: str) -> str:
        """Read agent description from markdown file.

        Args:
            agent_path: Path to agent markdown file

        Returns:
            Agent description (first paragraph)
        """
        try:
            with open(agent_path, 'r') as f:
                content = f.read()
                # Extract first paragraph after frontmatter
                lines = content.split('\n')
                in_frontmatter = False
                description_lines = []

                for line in lines:
                    if line.strip() == '---':
                        in_frontmatter = not in_frontmatter
                        continue
                    if not in_frontmatter and line.strip():
                        if line.startswith('#'):
                            continue
                        description_lines.append(line.strip())
                        if len(description_lines) >= 3:
                            break

                return ' '.join(description_lines) if description_lines else "No description available"
        except Exception:
            return "No description available"

    def _register_tools(self) -> None:
        """Register agent tools."""
        # Tool: invoke_agent
        self.register_tool(MCPTool(
            name="invoke_agent",
            description="Invoke an amplihack agent to perform a task",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent to invoke (e.g., 'architect', 'builder', 'reviewer')"
                    },
                    "task": {
                        "type": "string",
                        "description": "Task description for the agent to execute"
                    },
                    "context": {
                        "type": "object",
                        "description": "Optional context information for the agent",
                        "additionalProperties": True
                    }
                },
                "required": ["agent_name", "task"]
            }
        ))

        # Tool: list_agents
        self.register_tool(MCPTool(
            name="list_agents",
            description="List all available amplihack agents",
            input_schema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Filter by agent type: 'core' or 'specialized'",
                        "enum": ["core", "specialized"]
                    }
                }
            }
        ))

        # Tool: get_agent_info
        self.register_tool(MCPTool(
            name="get_agent_info",
            description="Get detailed information about a specific agent",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent"
                    }
                },
                "required": ["agent_name"]
            }
        ))

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute an agent tool.

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPServerError: If tool execution fails
        """
        if tool_name == "invoke_agent":
            return await self._invoke_agent(
                arguments["agent_name"],
                arguments["task"],
                arguments.get("context", {})
            )
        elif tool_name == "list_agents":
            return self._list_agents(arguments.get("type"))
        elif tool_name == "get_agent_info":
            return self._get_agent_info(arguments["agent_name"])
        else:
            raise MCPServerError(f"Unknown tool: {tool_name}")

    async def _invoke_agent(self, agent_name: str, task: str, context: dict[str, Any]) -> dict[str, Any]:
        """Invoke an agent.

        Args:
            agent_name: Agent name
            task: Task description
            context: Context information

        Returns:
            Invocation result
        """
        # Find agent file
        agents = self._discover_agents()
        agent_info = next((a for a in agents if a["name"] == agent_name), None)

        if not agent_info:
            raise MCPServerError(f"Agent not found: {agent_name}")

        # For now, return a simulation result
        # In a full implementation, this would invoke Claude Code with the agent
        return {
            "status": "success",
            "agent": agent_name,
            "task": task,
            "message": f"Agent '{agent_name}' would be invoked with task: {task}",
            "note": "Full agent invocation requires Claude Code integration"
        }

    def _list_agents(self, agent_type: str | None = None) -> dict[str, Any]:
        """List available agents.

        Args:
            agent_type: Optional type filter

        Returns:
            List of agents
        """
        agents = self._discover_agents()

        if agent_type:
            agents = [a for a in agents if a["type"] == agent_type]

        # Add descriptions
        for agent in agents:
            agent["description"] = self._read_agent_description(agent["path"])

        return {
            "count": len(agents),
            "agents": agents
        }

    def _get_agent_info(self, agent_name: str) -> dict[str, Any]:
        """Get agent information.

        Args:
            agent_name: Agent name

        Returns:
            Agent information

        Raises:
            MCPServerError: If agent not found
        """
        agents = self._discover_agents()
        agent_info = next((a for a in agents if a["name"] == agent_name), None)

        if not agent_info:
            raise MCPServerError(f"Agent not found: {agent_name}")

        # Add full description
        agent_info["description"] = self._read_agent_description(agent_info["path"])

        # Read full agent content
        try:
            with open(agent_info["path"], 'r') as f:
                agent_info["content"] = f.read()
        except Exception as e:
            agent_info["content"] = f"Error reading agent content: {str(e)}"

        return agent_info


async def main():
    """Main entry point for agents MCP server."""
    try:
        server = AgentsMCPServer()
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
