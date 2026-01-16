# MCP Servers for Amplihack

This document explains how to use amplihack's MCP (Model Context Protocol) servers with GitHub Copilot CLI and other MCP clients.

## Overview

Amplihack provides three MCP servers that expose its capabilities as tools:

1. **amplihack-agents**: Invoke specialized agents (architect, builder, reviewer, etc.)
2. **amplihack-workflows**: Orchestrate multi-step workflows (DEFAULT_WORKFLOW, INVESTIGATION_WORKFLOW, etc.)
3. **amplihack-hooks**: Trigger lifecycle hooks (session_start, pre_tool_use, post_tool_use, etc.)

## Quick Start

### Installation

The MCP servers are included in the amplihack package. Install via uvx (recommended):

```bash
uvx amplihack
```

Or via pip:

```bash
pip install amplihack
```

### Configuration

#### For GitHub Copilot CLI

Copy the MCP server configuration to your Copilot CLI settings:

```bash
# Copy the MCP configuration
cp .github/mcp-servers.json ~/.copilot/mcp-servers.json
```

Or merge with existing configuration:

```bash
# If you already have MCP servers configured
cat .github/mcp-servers.json >> ~/.copilot/mcp-servers.json
```

#### For Claude Code

Add to your Claude Code settings at `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "amplihack-agents": {
      "command": "uvx",
      "args": ["--from", "amplihack", "amplihack-mcp-agents"]
    },
    "amplihack-workflows": {
      "command": "uvx",
      "args": ["--from", "amplihack", "amplihack-mcp-workflows"]
    },
    "amplihack-hooks": {
      "command": "uvx",
      "args": ["--from", "amplihack", "amplihack-mcp-hooks"]
    }
  }
}
```

### Using amplihack CLI

You can also start MCP servers directly using the amplihack CLI:

```bash
# Start agents MCP server
amplihack start-mcp-server agents

# Start workflows MCP server
amplihack start-mcp-server workflows

# Start hooks MCP server
amplihack start-mcp-server hooks
```

## MCP Server Tools

### Agents Server (amplihack-mcp-agents)

Exposes amplihack's specialized agents as MCP tools.

#### Available Tools

##### `invoke_agent`

Invoke an agent to perform a task.

**Parameters:**
- `agent_name` (string, required): Name of the agent (e.g., "architect", "builder", "reviewer")
- `task` (string, required): Task description for the agent
- `context` (object, optional): Additional context information

**Example:**

```bash
copilot mcp amplihack-agents invoke_agent \
  --agent_name architect \
  --task "Design a RESTful API for user authentication"
```

##### `list_agents`

List all available agents.

**Parameters:**
- `type` (string, optional): Filter by agent type ("core" or "specialized")

**Example:**

```bash
copilot mcp amplihack-agents list_agents
copilot mcp amplihack-agents list_agents --type core
```

##### `get_agent_info`

Get detailed information about a specific agent.

**Parameters:**
- `agent_name` (string, required): Name of the agent

**Example:**

```bash
copilot mcp amplihack-agents get_agent_info --agent_name architect
```

#### Available Agents

**Core Agents:**
- `architect`: System design and architecture
- `builder`: Code implementation
- `reviewer`: Code review and quality checks
- `tester`: Test generation and validation
- `api-designer`: API contract design
- `optimizer`: Performance optimization

**Specialized Agents:**
- `database`: Database schema and query optimization
- `security`: Security analysis and vulnerability assessment
- `integration`: External service integration
- `cleanup`: Code simplification and cleanup
- `analyzer`: Deep code analysis
- `knowledge-archaeologist`: Codebase exploration and documentation
- And many more...

### Workflows Server (amplihack-mcp-workflows)

Orchestrates multi-step workflows.

#### Available Tools

##### `start_workflow`

Start a workflow execution.

**Parameters:**
- `workflow_name` (string, required): Name of the workflow (e.g., "DEFAULT_WORKFLOW")
- `context` (object, optional): Context information for the workflow

**Example:**

```bash
copilot mcp amplihack-workflows start_workflow \
  --workflow_name DEFAULT_WORKFLOW \
  --context '{"feature": "authentication"}'
```

##### `execute_step`

Execute a specific workflow step.

**Parameters:**
- `workflow_id` (string, required): ID of the workflow execution
- `step_number` (integer, required): Step number to execute

**Example:**

```bash
copilot mcp amplihack-workflows execute_step \
  --workflow_id DEFAULT_WORKFLOW_20240115_143052 \
  --step_number 3
```

##### `get_workflow_state`

Get current workflow execution state.

**Parameters:**
- `workflow_id` (string, required): ID of the workflow execution

**Example:**

```bash
copilot mcp amplihack-workflows get_workflow_state \
  --workflow_id DEFAULT_WORKFLOW_20240115_143052
```

##### `list_workflows`

List all available workflows.

**Example:**

```bash
copilot mcp amplihack-workflows list_workflows
```

#### Available Workflows

- `DEFAULT_WORKFLOW`: Standard development workflow (features, bugs, refactoring)
- `INVESTIGATION_WORKFLOW`: Deep codebase exploration and understanding
- `Q&A_WORKFLOW`: Simple questions and answers
- `CONSENSUS_WORKFLOW`: High-quality decisions with consensus mechanisms
- `N_VERSION_WORKFLOW`: N-version programming for critical code
- `DEBATE_WORKFLOW`: Multi-perspective decision making
- `CASCADE_WORKFLOW`: Graceful degradation with fallback strategies

### Hooks Server (amplihack-mcp-hooks)

Triggers lifecycle hooks.

#### Available Tools

##### `trigger_hook`

Execute a hook.

**Parameters:**
- `hook_name` (string, required): Name of the hook
- `event` (string, required): Event type (e.g., "session_start", "pre_tool_use")
- `data` (object, optional): Event data to pass to the hook

**Example:**

```bash
copilot mcp amplihack-hooks trigger_hook \
  --hook_name session_start \
  --event session_start \
  --data '{"session_id": "abc123"}'
```

##### `list_hooks`

List all available hooks.

**Parameters:**
- `type` (string, optional): Filter by hook type ("python" or "xpia")

**Example:**

```bash
copilot mcp amplihack-hooks list_hooks
copilot mcp amplihack-hooks list_hooks --type xpia
```

##### `get_hook_status`

Get hook execution status.

**Parameters:**
- `execution_id` (string, required): ID of the hook execution

**Example:**

```bash
copilot mcp amplihack-hooks get_hook_status \
  --execution_id session_start_20240115_143052
```

## Integration with setup-copilot

The `amplihack setup-copilot` command automatically configures MCP servers:

```bash
amplihack setup-copilot
```

This command:
1. Creates `.github/` directory structure
2. Syncs agents to `.github/agents/`
3. Creates sample hooks in `.github/hooks/`
4. Configures MCP servers in `.github/mcp-servers.json`

## Usage Examples

### Example 1: Invoke Architect Agent

```bash
# Using Copilot CLI with MCP
copilot mcp amplihack-agents invoke_agent \
  --agent_name architect \
  --task "Design a microservices architecture for e-commerce platform"

# Or using amplihack CLI directly
amplihack start-mcp-server agents
# (Then interact via stdin/stdout using MCP protocol)
```

### Example 2: Run Complete Workflow

```bash
# Start DEFAULT_WORKFLOW
copilot mcp amplihack-workflows start_workflow \
  --workflow_name DEFAULT_WORKFLOW \
  --context '{"feature": "Add payment processing"}'

# Get workflow ID from response, e.g., DEFAULT_WORKFLOW_20240115_143052

# Execute steps
for step in {0..13}; do
  copilot mcp amplihack-workflows execute_step \
    --workflow_id DEFAULT_WORKFLOW_20240115_143052 \
    --step_number $step
done
```

### Example 3: Trigger Session Start Hook

```bash
copilot mcp amplihack-hooks trigger_hook \
  --hook_name session_start \
  --event session_start \
  --data '{"user": "developer", "project": "amplihack"}'
```

## Troubleshooting

### MCP Server Not Found

If you see "command not found" errors:

1. Ensure amplihack is installed: `uvx amplihack --help`
2. Check your PATH includes the uvx bin directory
3. Try absolute path in configuration: `"command": "/path/to/uvx"`

### Server Fails to Start

If the MCP server fails to start:

1. Check amplihack installation: `amplihack --version`
2. Verify `.claude/` directory exists in your project
3. Check logs for detailed error messages
4. Try running directly: `amplihack start-mcp-server agents`

### Tools Not Available

If tools don't show up in the MCP client:

1. Restart the MCP client after configuration changes
2. Verify MCP server configuration in settings
3. Check server initialization with `initialize` request
4. Use `tools/list` request to see available tools

## Architecture

### Protocol

Amplihack MCP servers follow the Model Context Protocol specification:

- **Transport**: stdio (JSON-RPC-like messages)
- **Protocol Version**: 2024-11-05
- **Message Format**: JSON with `jsonrpc`, `method`, `params`, `id` fields

### Implementation

- **Base Class**: `MCPServer` in `amplihack.mcp.base`
- **Self-Contained**: No external MCP library dependencies
- **Async**: Uses Python's asyncio for non-blocking I/O
- **Modular**: Each server is independent and regeneratable

### Discovery

- **Agents**: Discovered from `.claude/agents/amplihack/` directory
- **Workflows**: Discovered from `.claude/workflow/` directory
- **Hooks**: Discovered from `.claude/tools/` directory

## Advanced Usage

### Custom Environment Variables

You can pass environment variables to MCP servers:

```json
{
  "mcpServers": {
    "amplihack-agents": {
      "command": "uvx",
      "args": ["--from", "amplihack", "amplihack-mcp-agents"],
      "env": {
        "AMPLIHACK_AGENTS_DIR": "/custom/path/.claude/agents",
        "LOG_LEVEL": "debug"
      }
    }
  }
}
```

### Using Local Development Version

For development, use local installation:

```json
{
  "mcpServers": {
    "amplihack-agents": {
      "command": "python",
      "args": ["-m", "amplihack.mcp.agents_server"]
    }
  }
}
```

### Multiple Projects

Configure different MCP servers for different projects:

```json
{
  "mcpServers": {
    "amplihack-project-a-agents": {
      "command": "uvx",
      "args": ["--from", "amplihack", "amplihack-mcp-agents"],
      "env": {
        "PROJECT_ROOT": "/path/to/project-a"
      }
    },
    "amplihack-project-b-agents": {
      "command": "uvx",
      "args": ["--from", "amplihack", "amplihack-mcp-agents"],
      "env": {
        "PROJECT_ROOT": "/path/to/project-b"
      }
    }
  }
}
```

## See Also

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [GitHub Copilot CLI Documentation](https://docs.github.com/en/copilot/github-copilot-in-the-cli)
- [Amplihack Agent Documentation](../agents/README.md)
- [Amplihack Workflow Documentation](../../.claude/workflow/README.md)
- [Copilot CLI Integration Guide](COPILOT_CLI.md)
