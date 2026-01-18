# Claude Agent SDK - Complete API Reference

## Architecture

### Agent Loop Internals

The Agent SDK implements a sophisticated agent loop that handles the complete lifecycle of agentic interactions:

```
┌─────────────────────────────────────────────────────┐
│ 1. INPUT PHASE                                      │
│    - User message                                   │
│    - System prompt                                  │
│    - Tool definitions                               │
│    - Conversation history                           │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 2. MODEL INVOCATION                                 │
│    - Call Claude Messages API                       │
│    - Include tools in request                       │
│    - Streaming or non-streaming                     │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 3. RESPONSE PROCESSING                              │
│    - Text response → Return to user                 │
│    - Tool use request → Execute tools               │
│    - Multiple tool calls → Parallel execution       │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 4. TOOL EXECUTION (if tool_use)                     │
│    - PreToolUseHook invocation                      │
│    - Tool function execution                        │
│    - Error handling and retry                       │
│    - PostToolUseHook invocation                     │
│    - Result formatting                              │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 5. ITERATION                                        │
│    - Append tool results to conversation            │
│    - Return to Model Invocation (step 2)            │
│    - Continue until text response or max_turns      │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 6. OUTPUT                                           │
│    - Final text response                            │
│    - Full conversation history                      │
│    - Metadata (turn count, token usage)             │
└─────────────────────────────────────────────────────┘
```

**Key Characteristics:**

- **Automatic Iteration**: Continues until Claude returns text (not tool calls) or max_turns reached
- **Parallel Tool Execution**: Multiple tool calls in single turn executed concurrently
- **Error Recovery**: Failed tools return error messages to Claude for recovery
- **Context Preservation**: Full conversation history maintained across turns
- **Token Management**: Automatic tracking, optional compaction when approaching limits

### Context Management

**Context Components:**

1. **System Prompt** (persistent across turns)
   - Agent role and capabilities
   - Task instructions and constraints
   - Output format requirements
   - Examples and few-shot demonstrations

2. **Conversation History** (grows with each turn)
   - User messages
   - Assistant responses (text + tool calls)
   - Tool results
   - Thinking/reasoning steps (if using extended thinking)

3. **Tool Definitions** (available capabilities)
   - Tool names and descriptions
   - Input schemas (JSON Schema format)
   - Execution metadata

**Context Growth Management:**

```python
# Default: No automatic compaction
agent = Agent(model="claude-sonnet-4-5-20250929")

# With context compaction threshold
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    max_context_tokens=100000,  # Start compaction at 100K tokens
    compaction_strategy="summarize"  # or "truncate"
)
```

**Subagent Context Isolation:**

Subagents create isolated context bubbles:

- Inherit parent's system prompt (optional override)
- Empty conversation history (fresh start)
- Subset of parent's tools (optional additional tools)
- Results summarized back to parent

```python
# Parent context: Full conversation with user
parent = Agent(model="claude-sonnet-4-5-20250929")

# Subagent: Isolated context for specialized task
with parent.subagent(
    system="You are a data analyzer. Focus only on statistical analysis.",
    tools=[stats_tool],
    inherit_system=False  # Don't inherit parent system prompt
) as analyzer:
    # Analyzer sees ONLY its system prompt and this task
    result = analyzer.run("Analyze this dataset: [data]")

# Parent continues with original context + analyzer result
```

### Tool Orchestration

**Tool Execution Pipeline:**

1. **Tool Selection**: Claude chooses which tools to call based on task requirements
2. **Schema Validation**: SDK validates arguments against tool's input_schema
3. **Hook Invocation**: PreToolUseHook called for each tool
4. **Parallel Execution**: Multiple tools executed concurrently when possible
5. **Result Collection**: Tool outputs gathered and formatted
6. **Hook Invocation**: PostToolUseHook called with results
7. **Context Update**: Results added to conversation history

**Tool Execution Modes:**

```python
# Sequential tool execution (default for single tools)
result = tool_function(**validated_args)

# Parallel tool execution (automatic for multiple tools in one turn)
import asyncio
results = await asyncio.gather(*[
    execute_tool(tool1, args1),
    execute_tool(tool2, args2),
    execute_tool(tool3, args3)
])
```

**Error Handling:**

When a tool fails, the SDK returns an error result to Claude:

```python
{
    "tool_use_id": "toolu_123",
    "type": "tool_result",
    "content": "Error: FileNotFoundError: file.txt not found",
    "is_error": True
}
```

Claude can then:

- Retry with corrected arguments
- Try an alternative approach
- Ask user for clarification
- Report the error in natural language

### MCP Integration

**Model Context Protocol (MCP)** is a standardized protocol for exposing tools to language models.

**MCP Architecture:**

```
Agent SDK ←→ MCP Client ←→ MCP Server ←→ External Service
             (SDK)         (stdio/SSE)   (Filesystem, GitHub, etc.)
```

**Connection Types:**

1. **stdio**: Process-based communication (npm packages)

```python
from claude_agents.mcp import MCPClient

mcp = MCPClient("npx", ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allow"])
```

2. **SSE**: HTTP Server-Sent Events (remote servers)

```python
mcp = MCPClient.from_sse("http://localhost:3000/mcp")
```

**Tool Discovery:**

MCP servers expose their tools via the protocol. The SDK automatically:

1. Queries server for available tools
2. Converts MCP tool schemas to SDK Tool format
3. Routes tool calls to appropriate server
4. Translates results back to SDK format

**Multiple MCP Servers:**

```python
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    mcp_clients=[
        MCPClient("npx", ["-y", "@modelcontextprotocol/server-filesystem"]),
        MCPClient("npx", ["-y", "@modelcontextprotocol/server-github"]),
        MCPClient.from_sse("http://localhost:3000/custom-mcp")
    ]
)
# Agent can use tools from all three servers
```

## Setup & Configuration

### Python Setup

**Installation:**

```bash
pip install claude-agents

# With optional dependencies
pip install claude-agents[all]  # Includes MCP clients, dev tools
```

**Basic Configuration:**

```python
from claude_agents import Agent

agent = Agent(
    # Required
    model="claude-sonnet-4-5-20250929",

    # Authentication (optional if env var set)
    api_key="sk-ant-...",

    # System prompt
    system="You are a helpful assistant.",

    # Tools
    tools=[],
    allowed_tools=None,
    disallowed_tools=None,

    # Hooks
    hooks=[],

    # MCP
    mcp_clients=[],

    # Context management
    max_turns=25,
    max_context_tokens=None,

    # Streaming
    stream=False
)
```

**Advanced Options:**

```python
agent = Agent(
    model="claude-sonnet-4-5-20250929",

    # Model parameters
    temperature=1.0,
    top_p=0.9,
    top_k=40,
    max_tokens=4096,

    # Thinking configuration (extended thinking models)
    thinking={
        "type": "enabled",
        "budget_tokens": 10000
    },

    # Tool configuration
    tool_choice="auto",  # or "any", "none", {"type": "tool", "name": "tool_name"}
    parallel_tool_calls=True,

    # Error handling
    retry_failed_tools=True,
    max_retries=3
)
```

### TypeScript Setup

**Installation:**

```bash
npm install @anthropics/agent-sdk
```

**Basic Configuration:**

```typescript
import { Agent } from "@anthropics/agent-sdk";

const agent = new Agent({
  // Required
  model: "claude-sonnet-4-5-20250929",

  // Authentication (optional if env var set)
  apiKey: process.env.ANTHROPIC_API_KEY,

  // System prompt
  system: "You are a helpful assistant.",

  // Tools
  tools: [],
  allowedTools: undefined,
  disallowedTools: undefined,

  // Hooks
  hooks: [],

  // Context management
  maxTurns: 25,
  maxContextTokens: undefined,
});
```

**Async Execution:**

```typescript
const result = await agent.run("Your task here");
console.log(result.response);
```

### Authentication

**Environment Variable (Recommended):**

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Explicit in Code:**

```python
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    api_key="sk-ant-..."
)
```

**From File:**

```python
import os
from pathlib import Path

api_key = Path("~/.anthropic/api_key").expanduser().read_text().strip()
agent = Agent(model="claude-sonnet-4-5-20250929", api_key=api_key)
```

### Environment Configuration

**Common Environment Variables:**

```bash
# Authentication
ANTHROPIC_API_KEY=sk-ant-...

# API endpoint (for proxies, testing)
ANTHROPIC_BASE_URL=https://api.anthropic.com

# Logging
ANTHROPIC_LOG_LEVEL=info  # debug, info, warning, error

# MCP configuration
MCP_SERVER_TIMEOUT=30  # seconds
MCP_MAX_RETRIES=3
```

## Tools System

### Tool Schema

Tools are defined using JSON Schema for input validation:

```python
from claude_agents.tools import Tool

tool = Tool(
    # Required fields
    name="tool_name",  # Unique identifier, snake_case recommended
    description="Clear description of what this tool does and when to use it.",

    # JSON Schema for input parameters
    input_schema={
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "What this parameter does"
            },
            "param2": {
                "type": "integer",
                "description": "Another parameter",
                "minimum": 0,
                "maximum": 100
            }
        },
        "required": ["param1"]  # Required parameters
    },

    # Implementation
    function=my_tool_function  # Callable or async callable
)
```

**Supported Parameter Types:**

- `string`: Text values
- `integer`: Whole numbers
- `number`: Integers or floats
- `boolean`: True/false
- `array`: Lists of values
- `object`: Nested structures
- `null`: Explicit null values

**Advanced Schema Features:**

```python
input_schema={
    "type": "object",
    "properties": {
        "enum_param": {
            "type": "string",
            "enum": ["option1", "option2", "option3"],
            "description": "Choose one option"
        },
        "array_param": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of strings"
        },
        "nested_param": {
            "type": "object",
            "properties": {
                "nested_field": {"type": "string"}
            }
        }
    },
    "required": ["enum_param"],
    "additionalProperties": False  # Reject unknown parameters
}
```

### Built-in Tools Catalog

The SDK includes production-ready built-in tools:

**1. bash** - Execute shell commands

```python
{
    "name": "bash",
    "description": "Execute shell commands. Returns stdout, stderr, and exit code.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30}
        },
        "required": ["command"]
    }
}
```

**2. read_file** - Read file contents

```python
{
    "name": "read_file",
    "description": "Read the contents of a file.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to file to read"}
        },
        "required": ["path"]
    }
}
```

**3. write_file** - Write or create files

```python
{
    "name": "write_file",
    "description": "Write content to a file, creating it if it doesn't exist.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to file"},
            "content": {"type": "string", "description": "Content to write"}
        },
        "required": ["path", "content"]
    }
}
```

**4. edit_file** - Modify existing files

```python
{
    "name": "edit_file",
    "description": "Edit a file by replacing old text with new text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string", "description": "Text to replace"},
            "new_text": {"type": "string", "description": "Replacement text"}
        },
        "required": ["path", "old_text", "new_text"]
    }
}
```

**5. glob** - File pattern matching

```python
{
    "name": "glob",
    "description": "Find files matching a pattern.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern (e.g., '**/*.py')"},
            "base_path": {"type": "string", "description": "Base directory", "default": "."}
        },
        "required": ["pattern"]
    }
}
```

**6. grep** - Content search

```python
{
    "name": "grep",
    "description": "Search for text in files.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Search pattern (regex)"},
            "path": {"type": "string", "description": "File or directory to search"},
            "recursive": {"type": "boolean", "default": True}
        },
        "required": ["pattern", "path"]
    }
}
```

**Using Built-in Tools:**

```python
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    allowed_tools=["read_file", "write_file", "glob"]
)
```

### Custom Tool Creation

**Simple Function Tool:**

```python
def get_current_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return datetime.now().isoformat()

time_tool = Tool(
    name="get_current_time",
    description="Returns the current time in ISO format.",
    input_schema={"type": "object", "properties": {}, "required": []},
    function=get_current_time
)
```

**Tool with Parameters:**

```python
def calculate_compound_interest(
    principal: float,
    rate: float,
    years: int,
    compounds_per_year: int = 1
) -> dict:
    """Calculate compound interest."""
    amount = principal * (1 + rate / compounds_per_year) ** (compounds_per_year * years)
    interest = amount - principal
    return {
        "principal": principal,
        "final_amount": round(amount, 2),
        "interest_earned": round(interest, 2)
    }

interest_tool = Tool(
    name="calculate_compound_interest",
    description="Calculate compound interest over time.",
    input_schema={
        "type": "object",
        "properties": {
            "principal": {"type": "number", "description": "Starting amount"},
            "rate": {"type": "number", "description": "Annual interest rate (decimal, e.g., 0.05 for 5%)"},
            "years": {"type": "integer", "description": "Number of years"},
            "compounds_per_year": {"type": "integer", "description": "Compounding frequency", "default": 1}
        },
        "required": ["principal", "rate", "years"]
    },
    function=calculate_compound_interest
)
```

**Async Tool:**

```python
import asyncio
import aiohttp

async def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

fetch_tool = Tool(
    name="fetch_url",
    description="Fetch content from a URL.",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"}
        },
        "required": ["url"]
    },
    function=fetch_url  # SDK detects async and handles appropriately
)
```

### Permissions & Security

**Allowed Tools (Whitelist Approach):**

```python
# Only specific tools can be used
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[tool1, tool2, tool3, tool4, tool5],
    allowed_tools=["tool1", "tool2"]  # Only these two
)
```

**Disallowed Tools (Blacklist Approach):**

```python
# All tools except specified ones
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[tool1, tool2, tool3],
    disallowed_tools=["tool3"]  # All except tool3
)
```

**Dynamic Permissions (via Hooks):**

```python
from claude_agents.hooks import PreToolUseHook

class DynamicPermissionHook(PreToolUseHook):
    async def execute(self, context):
        # Check permission based on runtime conditions
        if context.tool_name == "bash":
            command = context.tool_input.get("command", "")
            if any(danger in command for danger in ["rm", "delete", "format"]):
                raise PermissionError(f"Dangerous command blocked: {command}")
        return context

agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=all_tools,
    hooks=[DynamicPermissionHook()]
)
```

**Permission Modes:**

```python
# Permissive mode (default): Agent can use allowed tools freely
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    permission_mode="permissive"
)

# Strict mode: Agent must request permission for each tool use
# Requires PreToolUseHook to approve/deny
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    permission_mode="strict",
    hooks=[PermissionRequestHook()]
)
```

### MCP Tool Integration

**Connecting MCP Servers:**

```python
from claude_agents import Agent
from claude_agents.mcp import MCPClient

# Filesystem MCP server
fs_mcp = MCPClient("npx", ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"])

# GitHub MCP server
github_mcp = MCPClient("npx", ["-y", "@modelcontextprotocol/server-github"])

agent = Agent(
    model="claude-sonnet-4-5-20250929",
    mcp_clients=[fs_mcp, github_mcp]
)

# Agent now has access to all tools from both MCP servers
```

**MCP Tool Naming:**
MCP tools are prefixed with server name to avoid conflicts:

```python
# Filesystem tools: fs_read_file, fs_write_file, fs_list_directory
# GitHub tools: github_create_issue, github_list_prs, github_create_pr
```

**Filtering MCP Tools:**

```python
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    mcp_clients=[fs_mcp, github_mcp],
    allowed_tools=[
        "fs_read_file",
        "fs_write_file",
        "github_create_issue"
    ]  # Only these MCP tools allowed
)
```

## Hooks Reference

### Hook Types

**1. PreToolUseHook** - Before tool execution

```python
from claude_agents.hooks import PreToolUseHook

class MyPreHook(PreToolUseHook):
    async def execute(self, context):
        # Access:
        # - context.tool_name: str
        # - context.tool_input: dict
        # - context.conversation_history: list
        # - context.agent_state: dict

        # Options:
        # 1. Allow execution: return context
        # 2. Block execution: raise Exception
        # 3. Modify input: context.tool_input = {...}; return context

        return context
```

**2. PostToolUseHook** - After tool execution

```python
from claude_agents.hooks import PostToolUseHook

class MyPostHook(PostToolUseHook):
    async def execute(self, context):
        # Access:
        # - context.tool_name: str
        # - context.tool_input: dict
        # - context.tool_output: any
        # - context.execution_time: float
        # - context.success: bool

        # Options:
        # 1. Return result as-is: return context
        # 2. Modify result: context.tool_output = {...}; return context
        # 3. Log/record: side effects, then return context

        return context
```

**3. PreSubagentStartHook** - Before subagent creation

```python
from claude_agents.hooks import PreSubagentStartHook

class MyPreSubagentHook(PreSubagentStartHook):
    async def execute(self, context):
        # Access:
        # - context.subagent_config: dict (system, tools, etc.)
        # - context.parent_agent: Agent
        # - context.delegation_reason: str

        # Modify subagent configuration before it starts
        context.subagent_config["max_turns"] = 10
        return context
```

**4. PostSubagentStopHook** - After subagent completes

```python
from claude_agents.hooks import PostSubagentStopHook

class MyPostSubagentHook(PostSubagentStopHook):
    async def execute(self, context):
        # Access:
        # - context.subagent_result: any
        # - context.subagent_metrics: dict (turns, tokens, etc.)
        # - context.parent_agent: Agent

        # Process or modify subagent result
        return context
```

### Hook Patterns

**Logging Hook:**

```python
import logging

class LoggingHook(PreToolUseHook, PostToolUseHook):
    def __init__(self):
        self.logger = logging.getLogger("agent_tools")

    async def execute(self, context):
        if isinstance(self, PreToolUseHook):
            self.logger.info(f"Tool: {context.tool_name}, Input: {context.tool_input}")
        else:  # PostToolUseHook
            self.logger.info(f"Tool: {context.tool_name}, Output: {context.tool_output}, Time: {context.execution_time}s")
        return context
```

**Validation Hook:**

```python
class ValidationHook(PreToolUseHook):
    async def execute(self, context):
        # Validate file paths
        if context.tool_name in ["read_file", "write_file", "edit_file"]:
            path = context.tool_input.get("path", "")
            if ".." in path or path.startswith("/"):
                raise ValueError(f"Invalid path: {path}")

        # Validate bash commands
        if context.tool_name == "bash":
            command = context.tool_input.get("command", "")
            dangerous = ["rm -rf", "format", "mkfs", "> /dev/"]
            if any(d in command for d in dangerous):
                raise PermissionError(f"Dangerous command blocked: {command}")

        return context
```

**Rate Limiting Hook:**

```python
import time
from collections import defaultdict

class RateLimitHook(PreToolUseHook):
    def __init__(self, max_calls_per_minute=60):
        self.max_calls = max_calls_per_minute
        self.calls = defaultdict(list)

    async def execute(self, context):
        now = time.time()
        tool_name = context.tool_name

        # Clean old calls
        self.calls[tool_name] = [t for t in self.calls[tool_name] if now - t < 60]

        # Check limit
        if len(self.calls[tool_name]) >= self.max_calls:
            raise RuntimeError(f"Rate limit exceeded for {tool_name}")

        self.calls[tool_name].append(now)
        return context
```

**Cost Tracking Hook:**

```python
class CostTrackingHook(PostToolUseHook):
    def __init__(self):
        self.total_cost = 0.0
        self.tool_costs = defaultdict(float)

    async def execute(self, context):
        # Estimate cost based on execution time and tool type
        cost = self._estimate_cost(context.tool_name, context.execution_time)
        self.total_cost += cost
        self.tool_costs[context.tool_name] += cost

        print(f"Cost: ${cost:.4f} (Total: ${self.total_cost:.4f})")
        return context

    def _estimate_cost(self, tool_name, execution_time):
        # Simplified cost estimation
        base_costs = {
            "bash": 0.001,
            "read_file": 0.0001,
            "write_file": 0.0002,
            "web_search": 0.01
        }
        return base_costs.get(tool_name, 0.001) * execution_time
```

## Skills System

### Skills Overview

Skills are modular knowledge packages that enhance Claude's capabilities in specific domains. They're automatically discovered from the filesystem and injected into the system prompt when relevant.

**Key Characteristics:**

- Filesystem-based (`.claude/skills/` directory)
- YAML frontmatter with metadata
- Markdown content with domain knowledge
- Automatic activation based on keywords or manual invocation
- Token budget management

### Skill File Format

**Structure:**

```markdown
---
name: skill-name
description: Brief description of skill capabilities
version: 1.0.0
activation_keywords:
  - keyword1
  - keyword2
auto_activate: true
token_budget: 2000
---

# Skill Content

Domain-specific knowledge, patterns, and examples...
```

**YAML Frontmatter Fields:**

- `name` (required): Unique skill identifier (kebab-case)
- `description` (required): Clear description of skill domain
- `version` (required): Semantic version (major.minor.patch)
- `activation_keywords` (required): List of keywords that trigger activation
- `auto_activate` (optional): Boolean, default true
- `token_budget` (optional): Max tokens for skill content
- `dependencies` (optional): List of other skill names this depends on
- `author` (optional): Skill creator
- `last_updated` (optional): ISO date of last update

### Filesystem Discovery

**Default Skills Directory:**

```
.claude/skills/
├── python-expert/
│   └── SKILL.md
├── typescript-expert/
│   └── SKILL.md
├── agent-sdk/
│   ├── SKILL.md
│   ├── reference.md
│   └── examples.md
└── custom-domain/
    └── SKILL.md
```

**Discovery Process:**

1. SDK scans `.claude/skills/` recursively
2. Finds all `SKILL.md` files (case-insensitive)
3. Parses YAML frontmatter
4. Validates required fields
5. Registers skill with keyword index

### Activation Logic

**Automatic Activation:**

```python
# User message contains activation keyword
result = agent.run("How do I use agent sdk tools?")
# → agent-sdk skill automatically included in system prompt
```

**Manual Activation:**

```python
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    skills=["agent-sdk", "python-expert"]  # Explicitly activate skills
)
```

**Conditional Activation:**

```python
# Skills can check context and conditionally activate
from claude_agents.skills import Skill

class ConditionalSkill(Skill):
    def should_activate(self, context):
        # Custom logic
        return "database" in context.user_message.lower()
```

### Setting Sources

Skills can reference external sources that are automatically fetched and embedded:

```yaml
---
name: api-integration
setting_sources:
  - url: https://api.example.com/docs
    type: markdown
    max_tokens: 5000
  - url: https://github.com/org/repo/blob/main/README.md
    type: github
---
```

**Supported Source Types:**

- `markdown`: Fetch and parse markdown content
- `github`: Fetch from GitHub (respects auth)
- `url`: Generic URL fetch
- `file`: Local file reference

**Token Budget Management:**
If total content exceeds `token_budget`, SDK:

1. Prioritizes core skill content
2. Truncates or summarizes setting_sources
3. Warns in logs about truncation

### Multi-File Skills

Skills can span multiple files for organization:

```
.claude/skills/agent-sdk/
├── SKILL.md          # Main entry point (always loaded)
├── reference.md      # API reference (loaded on demand)
├── examples.md       # Code examples (loaded on demand)
├── patterns.md       # Best practices (loaded on demand)
└── .metadata/
    └── index.json    # Internal navigation metadata
```

**Main Skill File (SKILL.md):**

```markdown
---
name: agent-sdk
description: Claude Agent SDK knowledge
token_budget: 4500
---

# Agent SDK Skill

Core content and overview...

For detailed API reference, see [reference.md](./reference.md).
For examples, see [examples.md](./examples.md).
```

**Navigation:**
Claude can reference supplementary files:

- "Read reference.md for complete API details"
- "See examples.md for working code"
- "Check patterns.md for production best practices"

SDK loads supplementary files on-demand when Claude requests them.
