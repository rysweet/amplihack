"""MCP (Model Context Protocol) servers for amplihack.

This module provides MCP servers that expose amplihack capabilities
as tools that can be consumed by MCP clients like GitHub Copilot CLI.

Available servers:
- agents_server: Exposes agent invocation capabilities
- workflows_server: Exposes workflow orchestration
- hooks_server: Exposes hook execution

Each server runs as a standalone process and communicates via stdio
using the MCP protocol.
"""

from .base import MCPServer, MCPTool, MCPServerError

__all__ = ["MCPServer", "MCPTool", "MCPServerError"]
