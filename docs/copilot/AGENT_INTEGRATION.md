# Copilot CLI Agent Integration

Complete integration system for invoking Copilot CLI agents from amplihack.

## Overview

This system provides a production-ready way to invoke agents from `.github/agents/` using Copilot CLI, with:

- Agent discovery from REGISTRY.json
- Simple invocation interface
- Comprehensive error handling
- CLI integration with `amplihack copilot-agent`

## Quick Start

### List Available Agents

```bash
# Simple list
amplihack list-copilot-agents

# Detailed view with metadata
amplihack list-copilot-agents --verbose
```

### Invoke an Agent

```bash
# Basic invocation
amplihack copilot-agent architect "Design authentication system"

# With additional context files
amplihack copilot-agent architect "Design API" --files PHILOSOPHY.md PATTERNS.md

# Verbose mode (shows command details)
amplihack copilot-agent builder "Implement login" --verbose
```

## Architecture

### Component Overview

```
src/amplihack/copilot/
├── agent_wrapper.py      # Core agent invocation logic
├── cli_handlers.py       # CLI command handlers
├── errors.py             # Error types
├── formatters.py         # Output formatting
├── workflow_state.py     # State management
└── tests/
    └── test_agent_integration.py  # Comprehensive tests
```

### Agent Discovery

Agents are discovered from `.github/agents/REGISTRY.json`:

```python
from amplihack.copilot import discover_agents, list_agents

# Get agent dictionary
agents = discover_agents()  # Dict[str, AgentInfo]

# Get sorted list
agents_list = list_agents()  # List[AgentInfo]
```

### Agent Invocation

#### Python API

```python
from amplihack.copilot import invoke_copilot_agent

result = invoke_copilot_agent(
    "architect",
    "Design authentication system",
    additional_files=["PHILOSOPHY.md"],
    verbose=True
)

if result.success:
    print(result.output)
else:
    print(f"Failed: {result.error}")
```

#### CLI

```bash
# Basic invocation
amplihack copilot-agent architect "Design authentication system"

# With additional files
amplihack copilot-agent architect "Design API" --files PHILOSOPHY.md PATTERNS.md

# List agents first
amplihack copilot-agent --list
```

## Usage Examples

### Example 1: Architecture Design

```bash
amplihack copilot-agent architect "Design a REST API for user management with authentication"
```

This invokes the architect agent with the task description.

### Example 2: Code Implementation

```bash
amplihack copilot-agent builder "Implement the user registration endpoint" \
  --files docs/api-spec.md
```

This invokes the builder agent with the spec file for context.

### Example 3: Code Review

```bash
amplihack copilot-agent reviewer "Review the authentication module for security issues" \
  --files PHILOSOPHY.md .claude/context/PATTERNS.md
```

This invokes the reviewer agent with philosophy and patterns for context.

## Agent Information

### Available Agents

Run `amplihack list-copilot-agents` to see all available agents. Common agents include:

- **architect**: System design and architecture
- **builder**: Code implementation from specifications
- **reviewer**: Code review and quality assurance
- **tester**: Test generation and validation
- **optimizer**: Performance optimization
- **security**: Security analysis and recommendations

### Agent Metadata

Each agent has:
- **name**: Agent identifier
- **path**: Relative path to agent file
- **description**: What the agent does
- **tags**: Categorization tags
- **invocable_by**: What can invoke this agent

## API Reference

### Functions

#### `discover_agents(registry_path) -> Dict[str, AgentInfo]`

Discover available agents from REGISTRY.json.

**Args:**
- `registry_path`: Path to REGISTRY.json (default: `.github/agents/REGISTRY.json`)

**Returns:**
- Dictionary mapping agent name to AgentInfo

**Raises:**
- `FileNotFoundError`: If REGISTRY.json doesn't exist
- `ValueError`: If REGISTRY.json is invalid

#### `list_agents(registry_path) -> List[AgentInfo]`

List all available agents sorted by name.

**Args:**
- `registry_path`: Path to REGISTRY.json (default: `.github/agents/REGISTRY.json`)

**Returns:**
- List of AgentInfo objects

#### `invoke_copilot_agent(agent_name, task, ...) -> AgentInvocationResult`

Invoke a Copilot agent with a task.

**Args:**
- `agent_name`: Name of agent to invoke
- `task`: Task description for the agent
- `registry_path`: Path to REGISTRY.json
- `additional_files`: Additional files to include with -f flag
- `allow_all_tools`: Allow all tools (default True)
- `verbose`: Show detailed output (default False)

**Returns:**
- `AgentInvocationResult` with:
  - `success`: Whether invocation succeeded
  - `agent_name`: Name of invoked agent
  - `output`: Agent output (stdout)
  - `error`: Error output (stderr)
  - `exit_code`: Command exit code

**Raises:**
- `InstallationError`: If Copilot CLI not installed
- `InvocationError`: If agent not found or invocation fails

### Data Classes

#### `AgentInfo`

Agent metadata from REGISTRY.json.

**Attributes:**
- `name`: Agent name
- `path`: Relative path to agent file
- `description`: Agent description
- `tags`: Agent tags
- `invocable_by`: What can invoke this agent

#### `AgentInvocationResult`

Result from agent invocation.

**Attributes:**
- `success`: Whether invocation succeeded
- `agent_name`: Name of invoked agent
- `output`: Agent output (stdout)
- `error`: Error output (stderr)
- `exit_code`: Command exit code

## Integration with CLI

### Adding Handlers to cli.py

The command handlers are in `copilot/cli_handlers.py`. To integrate with cli.py's main():

```python
elif args.command == "copilot-agent":
    from .copilot.cli_handlers import handle_copilot_agent
    return handle_copilot_agent(args)

elif args.command == "list-copilot-agents":
    from .copilot.cli_handlers import handle_list_copilot_agents
    return handle_list_copilot_agents(args)
```

The command parsers are already added to `create_parser()` in cli.py.

## Error Handling

### Common Errors

#### Copilot CLI Not Installed

```
InstallationError: Copilot CLI not installed. Install with:
  npm install -g @github/copilot
```

**Solution**: Install Copilot CLI using npm.

#### Agent Not Found

```
InvocationError: Agent 'nonexistent' not found.
Available agents: architect, builder, reviewer, ...
```

**Solution**: Check available agents with `amplihack list-copilot-agents`.

#### Registry Not Found

```
FileNotFoundError: Agent registry not found: .github/agents/REGISTRY.json
Run 'amplihack sync-agents' to create it
```

**Solution**: Run `amplihack sync-agents` to create the registry.

#### Agent File Missing

```
InvocationError: Agent file not found: .github/agents/core/architect.md
Run 'amplihack sync-agents' to create it
```

**Solution**: Run `amplihack sync-agents` to sync agent files.

## Testing

### Running Tests

```bash
# Run all agent integration tests
pytest src/amplihack/copilot/tests/test_agent_integration.py

# Run with verbose output
pytest src/amplihack/copilot/tests/test_agent_integration.py -v

# Run specific test class
pytest src/amplihack/copilot/tests/test_agent_integration.py::TestInvokeCopilotAgent
```

### Test Coverage

The test suite follows the testing pyramid (60% unit, 30% integration, 10% E2E):

- **Unit Tests**: Fast, heavily mocked tests for individual functions
- **Integration Tests**: Tests for multiple components working together
- **E2E Tests**: Complete workflow tests from discovery to invocation

## Troubleshooting

### Issue: "No agents found"

**Cause**: REGISTRY.json doesn't exist or is empty.

**Solution**:
```bash
amplihack sync-agents
```

### Issue: Agent invocation hangs

**Cause**: Copilot CLI might be waiting for input or has frozen.

**Solution**:
- Check if Copilot CLI is responsive: `copilot --version`
- Kill the process and try again
- Use `--verbose` flag to see what's happening

### Issue: Permission denied errors

**Cause**: Copilot CLI doesn't have required permissions.

**Solution**:
```bash
# The integration uses --allow-all-tools for VM environments
# If running locally, ensure Copilot CLI has necessary permissions
```

## Best Practices

1. **Always sync agents first**: Run `amplihack sync-agents` to ensure REGISTRY.json is up-to-date

2. **Use descriptive tasks**: Provide clear, detailed task descriptions for better results

3. **Include context files**: Use `--files` to provide additional context like PHILOSOPHY.md

4. **Check agent descriptions**: Use `--verbose` flag to see what each agent does

5. **Handle errors gracefully**: Check `result.success` and handle errors appropriately

## Philosophy Alignment

This integration follows amplihack philosophy:

- **Zero-BS**: All functions work, no stubs or placeholders
- **Ruthless Simplicity**: Simple, direct implementation
- **Self-contained**: Module is fully independent
- **Regeneratable**: Can be rebuilt from specification

## See Also

- [Copilot CLI Documentation](COPILOT_CLI.md)
- [Agent Synchronization](../AGENT_SYNC.md)
- [Workflow Orchestration](WORKFLOW_ORCHESTRATION.md)
