"""Base MCP server infrastructure.

This module provides the core MCP protocol handling following the
Model Context Protocol specification for tool servers.
"""

import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class MCPServerError(Exception):
    """Base exception for MCP server errors."""
    pass


@dataclass
class MCPTool:
    """Definition of an MCP tool.

    Attributes:
        name: Tool name (must be unique within server)
        description: Human-readable description of what the tool does
        input_schema: JSON schema for tool parameters
    """
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})

    def to_dict(self) -> dict[str, Any]:
        """Convert tool to MCP protocol format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


class MCPServer(ABC):
    """Base class for MCP servers.

    MCP servers expose tools via stdio using JSON-RPC-like protocol.
    Each server implements specific tools and handles their execution.

    Philosophy:
    - Single responsibility: Each server focuses on one capability area
    - Standard library only: No external MCP library dependencies
    - Self-contained: Can be regenerated from specification
    """

    def __init__(self, name: str, version: str = "1.0.0"):
        """Initialize MCP server.

        Args:
            name: Server name
            version: Server version
        """
        self.name = name
        self.version = version
        self._tools: dict[str, MCPTool] = {}
        self._register_tools()

    @abstractmethod
    def _register_tools(self) -> None:
        """Register tools provided by this server.

        Implementations should call self.register_tool() for each tool.
        """
        pass

    def register_tool(self, tool: MCPTool) -> None:
        """Register a tool with this server.

        Args:
            tool: Tool to register

        Raises:
            MCPServerError: If tool name already registered
        """
        if tool.name in self._tools:
            raise MCPServerError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool with given arguments.

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPServerError: If tool not found or execution fails
        """
        pass

    def _send_response(self, response: dict[str, Any]) -> None:
        """Send JSON response to stdout.

        Args:
            response: Response dictionary to send
        """
        json_response = json.dumps(response)
        sys.stdout.write(json_response + "\n")
        sys.stdout.flush()

    def _send_error(self, error_code: int, message: str, request_id: Any = None) -> None:
        """Send error response.

        Args:
            error_code: Error code
            message: Error message
            request_id: Request ID if available
        """
        response = {
            "jsonrpc": "2.0",
            "error": {
                "code": error_code,
                "message": message
            }
        }
        if request_id is not None:
            response["id"] = request_id
        self._send_response(response)

    async def _handle_initialize(self, request_id: Any) -> None:
        """Handle initialize request.

        Args:
            request_id: Request ID
        """
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": self.name,
                    "version": self.version
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }
        self._send_response(response)

    async def _handle_list_tools(self, request_id: Any) -> None:
        """Handle tools/list request.

        Args:
            request_id: Request ID
        """
        tools = [tool.to_dict() for tool in self._tools.values()]
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools
            }
        }
        self._send_response(response)

    async def _handle_call_tool(self, request_id: Any, params: dict[str, Any]) -> None:
        """Handle tools/call request.

        Args:
            request_id: Request ID
            params: Request parameters
        """
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            self._send_error(-32602, "Missing tool name", request_id)
            return

        if tool_name not in self._tools:
            self._send_error(-32601, f"Tool not found: {tool_name}", request_id)
            return

        try:
            result = await self.execute_tool(tool_name, arguments)
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result) if not isinstance(result, str) else result
                        }
                    ]
                }
            }
            self._send_response(response)
        except Exception as e:
            self._send_error(-32000, f"Tool execution failed: {str(e)}", request_id)

    async def _handle_request(self, request: dict[str, Any]) -> None:
        """Handle incoming MCP request.

        Args:
            request: Parsed JSON request
        """
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            await self._handle_initialize(request_id)
        elif method == "tools/list":
            await self._handle_list_tools(request_id)
        elif method == "tools/call":
            await self._handle_call_tool(request_id, params)
        else:
            self._send_error(-32601, f"Method not found: {method}", request_id)

    async def run(self) -> None:
        """Run the MCP server (reads from stdin, writes to stdout)."""
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                    await self._handle_request(request)
                except json.JSONDecodeError as e:
                    self._send_error(-32700, f"Parse error: {str(e)}")
                except Exception as e:
                    self._send_error(-32603, f"Internal error: {str(e)}")
        except KeyboardInterrupt:
            pass
