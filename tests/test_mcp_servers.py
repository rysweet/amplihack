"""Tests for MCP servers.

This module tests the MCP server implementations for agents, workflows, and hooks.
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from amplihack.mcp.base import MCPServer, MCPTool, MCPServerError
from amplihack.mcp.agents_server import AgentsMCPServer
from amplihack.mcp.workflows_server import WorkflowsMCPServer
from amplihack.mcp.hooks_server import HooksMCPServer


class TestMCPTool:
    """Test MCPTool dataclass."""

    def test_tool_creation(self):
        """Test creating an MCP tool."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {"arg": {"type": "string"}}}
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.input_schema["type"] == "object"

    def test_tool_to_dict(self):
        """Test converting tool to dictionary."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool"
        )

        tool_dict = tool.to_dict()
        assert tool_dict["name"] == "test_tool"
        assert tool_dict["description"] == "A test tool"
        assert "inputSchema" in tool_dict


class TestMCPServer:
    """Test MCPServer base class."""

    class ConcreteServer(MCPServer):
        """Concrete implementation for testing."""

        def _register_tools(self):
            self.register_tool(MCPTool(
                name="test_tool",
                description="Test tool"
            ))

        async def execute_tool(self, tool_name: str, arguments: dict):
            if tool_name == "test_tool":
                return {"result": "success"}
            raise MCPServerError(f"Unknown tool: {tool_name}")

    def test_server_creation(self):
        """Test creating an MCP server."""
        server = self.ConcreteServer(name="test-server", version="1.0.0")
        assert server.name == "test-server"
        assert server.version == "1.0.0"
        assert "test_tool" in server._tools

    def test_register_tool(self):
        """Test registering a tool."""
        server = self.ConcreteServer(name="test-server")

        tool = MCPTool(name="another_tool", description="Another tool")
        server.register_tool(tool)

        assert "another_tool" in server._tools

    def test_register_duplicate_tool(self):
        """Test registering a duplicate tool raises error."""
        server = self.ConcreteServer(name="test-server")

        tool = MCPTool(name="test_tool", description="Duplicate")
        with pytest.raises(MCPServerError, match="already registered"):
            server.register_tool(tool)

    @pytest.mark.asyncio
    async def test_handle_initialize(self):
        """Test handling initialize request."""
        server = self.ConcreteServer(name="test-server")

        with patch.object(server, '_send_response') as mock_send:
            await server._handle_initialize(request_id=1)

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert call_args["id"] == 1
            assert call_args["result"]["serverInfo"]["name"] == "test-server"

    @pytest.mark.asyncio
    async def test_handle_list_tools(self):
        """Test handling tools/list request."""
        server = self.ConcreteServer(name="test-server")

        with patch.object(server, '_send_response') as mock_send:
            await server._handle_list_tools(request_id=2)

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert call_args["id"] == 2
            assert len(call_args["result"]["tools"]) == 1
            assert call_args["result"]["tools"][0]["name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_handle_call_tool(self):
        """Test handling tools/call request."""
        server = self.ConcreteServer(name="test-server")

        with patch.object(server, '_send_response') as mock_send:
            params = {"name": "test_tool", "arguments": {}}
            await server._handle_call_tool(request_id=3, params=params)

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert call_args["id"] == 3
            assert "result" in call_args


class TestAgentsMCPServer:
    """Test AgentsMCPServer."""

    @pytest.fixture
    def mock_agents_dir(self, tmp_path):
        """Create a mock agents directory."""
        agents_dir = tmp_path / ".claude" / "agents" / "amplihack"
        core_dir = agents_dir / "core"
        core_dir.mkdir(parents=True)

        # Create sample agent files
        (core_dir / "architect.md").write_text("""---
name: architect
---

# Architect Agent

This agent designs system architecture.
""")

        (core_dir / "builder.md").write_text("""---
name: builder
---

# Builder Agent

This agent implements code.
""")

        return agents_dir

    def test_agents_server_creation(self, mock_agents_dir, monkeypatch):
        """Test creating agents MCP server."""
        monkeypatch.setattr(Path, 'cwd', lambda: mock_agents_dir.parent.parent.parent)

        server = AgentsMCPServer()
        assert server.name == "amplihack-agents"
        assert len(server._tools) == 3  # invoke_agent, list_agents, get_agent_info

    def test_discover_agents(self, mock_agents_dir, monkeypatch):
        """Test discovering agents."""
        monkeypatch.setattr(Path, 'cwd', lambda: mock_agents_dir.parent.parent.parent)

        server = AgentsMCPServer()
        agents = server._discover_agents()

        assert len(agents) >= 2
        agent_names = [a["name"] for a in agents]
        assert "architect" in agent_names
        assert "builder" in agent_names

    @pytest.mark.asyncio
    async def test_list_agents(self, mock_agents_dir, monkeypatch):
        """Test listing agents."""
        monkeypatch.setattr(Path, 'cwd', lambda: mock_agents_dir.parent.parent.parent)

        server = AgentsMCPServer()
        result = server._list_agents()

        assert "count" in result
        assert "agents" in result
        assert result["count"] >= 2


class TestWorkflowsMCPServer:
    """Test WorkflowsMCPServer."""

    @pytest.fixture
    def mock_workflows_dir(self, tmp_path):
        """Create a mock workflows directory."""
        workflows_dir = tmp_path / ".claude" / "workflow"
        workflows_dir.mkdir(parents=True)

        # Create sample workflow files
        (workflows_dir / "DEFAULT_WORKFLOW.md").write_text("""# Default Workflow

Standard workflow for development tasks.

## Step 1: Plan

Plan the implementation.

## Step 2: Execute

Execute the plan.
""")

        (workflows_dir / "INVESTIGATION_WORKFLOW.md").write_text("""# Investigation Workflow

Workflow for investigating codebases.

## Phase 1: Discovery

Discover the codebase structure.
""")

        return workflows_dir

    def test_workflows_server_creation(self, mock_workflows_dir, monkeypatch):
        """Test creating workflows MCP server."""
        monkeypatch.setattr(Path, 'cwd', lambda: mock_workflows_dir.parent.parent)

        server = WorkflowsMCPServer()
        assert server.name == "amplihack-workflows"
        assert len(server._tools) == 4

    def test_discover_workflows(self, mock_workflows_dir, monkeypatch):
        """Test discovering workflows."""
        monkeypatch.setattr(Path, 'cwd', lambda: mock_workflows_dir.parent.parent)

        server = WorkflowsMCPServer()
        workflows = server._discover_workflows()

        assert len(workflows) >= 2
        workflow_names = [w["name"] for w in workflows]
        assert "DEFAULT_WORKFLOW" in workflow_names
        assert "INVESTIGATION_WORKFLOW" in workflow_names

    @pytest.mark.asyncio
    async def test_start_workflow(self, mock_workflows_dir, monkeypatch):
        """Test starting a workflow."""
        monkeypatch.setattr(Path, 'cwd', lambda: mock_workflows_dir.parent.parent)

        server = WorkflowsMCPServer()
        result = await server._start_workflow("DEFAULT_WORKFLOW", {})

        assert "workflow_id" in result
        assert result["workflow_name"] == "DEFAULT_WORKFLOW"
        assert result["status"] == "started"

    @pytest.mark.asyncio
    async def test_list_workflows(self, mock_workflows_dir, monkeypatch):
        """Test listing workflows."""
        monkeypatch.setattr(Path, 'cwd', lambda: mock_workflows_dir.parent.parent)

        server = WorkflowsMCPServer()
        result = server._list_workflows()

        assert "count" in result
        assert "workflows" in result
        assert result["count"] >= 2


class TestHooksMCPServer:
    """Test HooksMCPServer."""

    @pytest.fixture
    def mock_hooks_dir(self, tmp_path):
        """Create a mock hooks directory."""
        hooks_dir = tmp_path / ".claude" / "tools"
        hooks_dir.mkdir(parents=True)

        # Create sample hook files
        (hooks_dir / "session_start.py").write_text("""\"\"\"Session start hook.

This hook runs when a session starts.
\"\"\"

def handle_session_start():
    pass
""")

        (hooks_dir / "ci_workflow.py").write_text("""\"\"\"CI workflow hook.

This hook handles CI workflow events.
\"\"\"

def handle_ci():
    pass
""")

        return hooks_dir

    def test_hooks_server_creation(self, mock_hooks_dir, monkeypatch):
        """Test creating hooks MCP server."""
        monkeypatch.setattr(Path, 'cwd', lambda: mock_hooks_dir.parent.parent)

        server = HooksMCPServer()
        assert server.name == "amplihack-hooks"
        assert len(server._tools) == 3

    def test_discover_hooks(self, mock_hooks_dir, monkeypatch):
        """Test discovering hooks."""
        monkeypatch.setattr(Path, 'cwd', lambda: mock_hooks_dir.parent.parent)

        server = HooksMCPServer()
        hooks = server._discover_hooks()

        assert len(hooks) >= 2
        hook_names = [h["name"] for h in hooks]
        assert "session_start" in hook_names
        assert "ci_workflow" in hook_names

    @pytest.mark.asyncio
    async def test_trigger_hook(self, mock_hooks_dir, monkeypatch):
        """Test triggering a hook."""
        monkeypatch.setattr(Path, 'cwd', lambda: mock_hooks_dir.parent.parent)

        server = HooksMCPServer()
        result = await server._trigger_hook("session_start", "session_start", {})

        assert "execution_id" in result
        assert result["hook_name"] == "session_start"
        assert result["event"] == "session_start"

    @pytest.mark.asyncio
    async def test_list_hooks(self, mock_hooks_dir, monkeypatch):
        """Test listing hooks."""
        monkeypatch.setattr(Path, 'cwd', lambda: mock_hooks_dir.parent.parent)

        server = HooksMCPServer()
        result = server._list_hooks()

        assert "count" in result
        assert "hooks" in result
        assert result["count"] >= 2
