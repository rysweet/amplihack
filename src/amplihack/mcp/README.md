# Amplihack MCP Servers

This directory contains MCP (Model Context Protocol) server implementations that expose amplihack capabilities as tools for MCP clients like GitHub Copilot CLI.

## Structure

```
mcp/
├── __init__.py           # Package exports
├── base.py              # Base MCP server infrastructure
├── agents_server.py     # Agents MCP server
├── workflows_server.py  # Workflows MCP server
├── hooks_server.py      # Hooks MCP server
└── README.md           # This file
```

## Servers

### Agents Server (`amplihack-mcp-agents`)

Exposes amplihack agents as MCP tools.

**Entry point:** `amplihack.mcp.agents_server:main`

**Tools:**
- `invoke_agent`: Execute an agent with a task
- `list_agents`: Get list of available agents
- `get_agent_info`: Get detailed agent information

### Workflows Server (`amplihack-mcp-workflows`)

Exposes amplihack workflows as MCP tools.

**Entry point:** `amplihack.mcp.workflows_server:main`

**Tools:**
- `start_workflow`: Start workflow execution
- `execute_step`: Execute specific workflow step
- `get_workflow_state`: Get workflow execution state
- `list_workflows`: Get list of available workflows

### Hooks Server (`amplihack-mcp-hooks`)

Exposes amplihack hooks as MCP tools.

**Entry point:** `amplihack.mcp.hooks_server:main`

**Tools:**
- `trigger_hook`: Execute a hook
- `list_hooks`: Get list of available hooks
- `get_hook_status`: Get hook execution status

## Usage

### From Command Line

```bash
# Start agents server
amplihack start-mcp-server agents

# Start workflows server
amplihack start-mcp-server workflows

# Start hooks server
amplihack start-mcp-server hooks
```

### As Executables

The servers are registered as console scripts in pyproject.toml:

```bash
amplihack-mcp-agents
amplihack-mcp-workflows
amplihack-mcp-hooks
```

### From MCP Clients

Configure in your MCP client (e.g., GitHub Copilot CLI):

```json
{
  "mcpServers": {
    "amplihack-agents": {
      "command": "uvx",
      "args": ["--from", "amplihack", "amplihack-mcp-agents"]
    }
  }
}
```

## Implementation

### Philosophy

- **Self-contained**: No external MCP library dependencies
- **Standard library only**: Uses only Python standard library
- **Regeneratable**: Can be rebuilt from specification
- **Simple**: Follows ruthless simplicity principle

### Base Class

All servers inherit from `MCPServer` base class which provides:

- Protocol handling (JSON-RPC-like messages)
- Tool registration and discovery
- Request/response management
- Error handling

### Discovery

Servers discover resources from the `.claude/` directory:

- **Agents**: `.claude/agents/amplihack/{core,specialized}/`
- **Workflows**: `.claude/workflow/`
- **Hooks**: `.claude/tools/`

## Development

### Adding a New Tool

1. Register the tool in `_register_tools()`:

```python
def _register_tools(self):
    self.register_tool(MCPTool(
        name="my_tool",
        description="Description of what it does",
        input_schema={
            "type": "object",
            "properties": {
                "arg1": {"type": "string", "description": "..."}
            },
            "required": ["arg1"]
        }
    ))
```

2. Implement the tool in `execute_tool()`:

```python
async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
    if tool_name == "my_tool":
        return await self._my_tool(arguments["arg1"])
    # ...
```

### Creating a New Server

1. Create new file in `mcp/` directory
2. Inherit from `MCPServer`
3. Implement `_register_tools()` and `execute_tool()`
4. Add `async def main()` entry point
5. Register in pyproject.toml `[project.scripts]`

## Testing

Tests are in `tests/test_mcp_servers.py`:

```bash
pytest tests/test_mcp_servers.py -v
```

## Documentation

Full documentation: `docs/copilot/MCP_SERVERS.md`

## See Also

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Amplihack Documentation](../../../docs/)
- [Base MCP Server](base.py)
