# GitHub Copilot SDK - Complete API Reference

## Architecture

### SDK Client Communication

The SDK communicates with Copilot CLI via JSON-RPC over a local connection:

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Application                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Session   │  │   Session   │  │   Custom Tools      │  │
│  │     #1      │  │     #2      │  │   + MCP Servers     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         └────────────────┼─────────────────────┘             │
│                          │                                   │
│                   ┌──────▼──────┐                           │
│                   │ SDK Client  │                           │
│                   └──────┬──────┘                           │
└──────────────────────────┼───────────────────────────────────┘
                           │ JSON-RPC
                   ┌───────▼───────┐
                   │  Copilot CLI  │
                   │ (server mode) │
                   └───────────────┘
```

### Lifecycle Management

**Automatic Mode (default)**:

- SDK starts CLI process automatically
- Manages process lifecycle
- Cleans up on client stop

**External Server Mode**:

- Connect to pre-running CLI server
- SDK doesn't manage CLI process
- Useful for debugging and resource sharing

---

## CopilotClient API

### Constructor / Initialization

**TypeScript**:

```typescript
import { CopilotClient } from "@github/copilot-sdk";

// Default - auto-manages CLI process
const client = new CopilotClient();

// Connect to external CLI server
const client = new CopilotClient({
  cliUrl: "localhost:4321",
});
```

**Python**:

```python
from copilot import CopilotClient

# Default - auto-manages CLI process
client = CopilotClient()

# Connect to external CLI server
client = CopilotClient({"cli_url": "localhost:4321"})
```

**Go**:

```go
import copilot "github.com/github/copilot-sdk/go"

// Default - auto-manages CLI process
client := copilot.NewClient(nil)

// Connect to external CLI server
client := copilot.NewClient(&copilot.ClientOptions{
    CLIUrl: "localhost:4321",
})
```

**.NET**:

```csharp
using GitHub.Copilot.SDK;

// Default - auto-manages CLI process
await using var client = new CopilotClient();

// Connect to external CLI server
await using var client = new CopilotClient(new CopilotClientOptions {
    CliUrl = "localhost:4321"
});
```

### Client Methods

| Method                  | Description                       | Returns   |
| ----------------------- | --------------------------------- | --------- |
| `start()`               | Initialize connection (Python/Go) | `void`    |
| `stop()`                | Close connection and cleanup      | `void`    |
| `createSession(config)` | Create new conversation session   | `Session` |

### ClientOptions

| Option   | Type     | Description                                      |
| -------- | -------- | ------------------------------------------------ |
| `cliUrl` | `string` | External CLI server URL (e.g., `localhost:4321`) |

---

## Session API

### createSession Configuration

**Complete TypeScript Example**:

```typescript
const session = await client.createSession({
  // Model selection
  model: "gpt-4.1",

  // Enable streaming responses
  streaming: true,

  // Custom tools
  tools: [weatherTool, calculatorTool],

  // MCP server connections
  mcpServers: {
    github: {
      type: "http",
      url: "https://api.githubcopilot.com/mcp/",
    },
    filesystem: {
      type: "stdio",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
    },
  },

  // Custom system message
  systemMessage: {
    content: "You are a helpful assistant focused on code review.",
  },

  // Custom agents
  customAgents: [
    {
      name: "pr-reviewer",
      displayName: "PR Reviewer",
      description: "Reviews pull requests for best practices",
      prompt: "Focus on security, performance, and maintainability.",
    },
  ],
});
```

**Complete Python Example**:

```python
session = await client.create_session({
    "model": "gpt-4.1",
    "streaming": True,
    "tools": [weather_tool, calculator_tool],
    "mcpServers": {
        "github": {
            "type": "http",
            "url": "https://api.githubcopilot.com/mcp/",
        },
    },
    "systemMessage": {
        "content": "You are a helpful assistant.",
    },
    "customAgents": [{
        "name": "code-helper",
        "displayName": "Code Helper",
        "description": "Helps with coding tasks",
        "prompt": "Focus on clean, maintainable code.",
    }],
})
```

### SessionConfig Options

| Option          | Type      | Description                        |
| --------------- | --------- | ---------------------------------- |
| `model`         | `string`  | Model identifier (e.g., `gpt-4.1`) |
| `streaming`     | `boolean` | Enable streaming responses         |
| `tools`         | `Tool[]`  | Custom tools for the session       |
| `mcpServers`    | `object`  | MCP server configurations          |
| `systemMessage` | `object`  | Custom system message              |
| `customAgents`  | `Agent[]` | Custom agent definitions           |

### Session Methods

| Method                 | Description                        | Returns    |
| ---------------------- | ---------------------------------- | ---------- |
| `sendAndWait(options)` | Send message and wait for response | `Response` |
| `on(handler)`          | Register event handler (streaming) | `void`     |

### MessageOptions

| Option   | Type     | Description          |
| -------- | -------- | -------------------- |
| `prompt` | `string` | User message to send |

---

## Tools API

### defineTool Function

**TypeScript**:

```typescript
import { defineTool } from "@github/copilot-sdk";

const myTool = defineTool("tool_name", {
  description: "What this tool does",
  parameters: {
    type: "object",
    properties: {
      param1: { type: "string", description: "Parameter description" },
      param2: { type: "number", description: "Another parameter" },
    },
    required: ["param1"],
  },
  handler: async (args) => {
    // Tool implementation
    return { result: args.param1 };
  },
});
```

**Python**:

```python
from copilot.tools import define_tool
from pydantic import BaseModel, Field

class MyToolParams(BaseModel):
    param1: str = Field(description="Parameter description")
    param2: int = Field(default=0, description="Another parameter")

@define_tool(description="What this tool does")
async def my_tool(params: MyToolParams) -> dict:
    return {"result": params.param1}
```

**Go**:

```go
type MyParams struct {
    Param1 string `json:"param1" jsonschema:"Parameter description"`
    Param2 int    `json:"param2" jsonschema:"Another parameter"`
}

type MyResult struct {
    Result string `json:"result"`
}

myTool := copilot.DefineTool(
    "tool_name",
    "What this tool does",
    func(params MyParams, inv copilot.ToolInvocation) (MyResult, error) {
        return MyResult{Result: params.Param1}, nil
    },
)
```

**.NET**:

```csharp
using Microsoft.Extensions.AI;
using System.ComponentModel;

var myTool = AIFunctionFactory.Create(
    ([Description("Parameter description")] string param1,
     [Description("Another parameter")] int param2 = 0) =>
    {
        return new { result = param1 };
    },
    "tool_name",
    "What this tool does"
);
```

### Tool Definition Schema

| Field         | Type          | Required | Description                     |
| ------------- | ------------- | -------- | ------------------------------- |
| `name`        | `string`      | Yes      | Unique tool identifier          |
| `description` | `string`      | Yes      | Clear description of capability |
| `parameters`  | `JSON Schema` | Yes      | Parameter schema                |
| `handler`     | `function`    | Yes      | Implementation function         |

---

## Events API

### Event Types

| Event Type (TS/Go)        | Python Enum                                | Description           |
| ------------------------- | ------------------------------------------ | --------------------- |
| `assistant.message_delta` | `SessionEventType.ASSISTANT_MESSAGE_DELTA` | Streaming text chunk  |
| `session.idle`            | `SessionEventType.SESSION_IDLE`            | Response complete     |
| `tool.invocation`         | `SessionEventType.TOOL_EXECUTION_START`    | Tool being called     |
| `tool.result`             | `SessionEventType.TOOL_EXECUTION_COMPLETE` | Tool execution result |

> **⚠️ Python Note**: Python uses `SessionEventType` enum from
> `copilot.generated.session_events`. The enum names differ from TypeScript/Go
> string literals (e.g., `TOOL_EXECUTION_START` vs `tool.invocation`).

### Event Handling

**TypeScript**:

```typescript
session.on((event: SessionEvent) => {
  switch (event.type) {
    case "assistant.message_delta":
      process.stdout.write(event.data.deltaContent);
      break;
    case "session.idle":
      console.log("\n[Complete]");
      break;
    case "tool.invocation":
      console.log(`[Tool: ${event.data.toolName}]`);
      break;
  }
});
```

**Python**:

```python
from copilot.generated.session_events import SessionEventType

def handle_event(event):
    if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
        sys.stdout.write(event.data.delta_content)
        sys.stdout.flush()
    elif event.type == SessionEventType.TOOL_EXECUTION_START:
        print(f"[Tool: {event.data.tool_name}]")
    elif event.type == SessionEventType.TOOL_EXECUTION_COMPLETE:
        print(f"[Result: {event.data.result}]")
    elif event.type == SessionEventType.SESSION_IDLE:
        print()

session.on(handle_event)
```

**Go**:

```go
session.On(func(event copilot.SessionEvent) {
    switch event.Type {
    case "assistant.message_delta":
        fmt.Print(*event.Data.DeltaContent)
    case "session.idle":
        fmt.Println()
    }
})
```

**.NET**:

```csharp
session.On(ev =>
{
    if (ev is AssistantMessageDeltaEvent deltaEvent)
    {
        Console.Write(deltaEvent.Data.DeltaContent);
    }
    if (ev is SessionIdleEvent)
    {
        Console.WriteLine();
    }
});
```

---

## MCP Integration

### MCP Server Types

**HTTP Type** (remote servers):

```typescript
mcpServers: {
    github: {
        type: "http",
        url: "https://api.githubcopilot.com/mcp/",
    }
}
```

**stdio Type** (process-based):

```typescript
mcpServers: {
    filesystem: {
        type: "stdio",
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allow"],
        env: { /* optional environment variables */ }
    }
}
```

### Common MCP Servers

| Server     | Package                                   | Description       |
| ---------- | ----------------------------------------- | ----------------- |
| GitHub     | `@github/github-mcp-server`               | Repository access |
| Filesystem | `@modelcontextprotocol/server-filesystem` | File operations   |

---

## External CLI Server

### Running CLI in Server Mode

```bash
# Start CLI server on specific port
copilot --server --port 4321

# Random available port
copilot --server
```

### Connecting SDK to External Server

**Benefits**:

- Debugging: Keep CLI running between SDK restarts
- Resource sharing: Multiple SDK clients share one CLI
- Development: Custom CLI settings

**All Languages**:

TypeScript: `cliUrl: "localhost:4321"`
Python: `cli_url: "localhost:4321"`
Go: `CLIUrl: "localhost:4321"`
.NET: `CliUrl = "localhost:4321"`

---

## Models

### Available Models

The SDK supports all models available via Copilot CLI. Use the SDK's model discovery method to list available models at runtime.

### Specifying Model

```typescript
const session = await client.createSession({
  model: "gpt-4.1", // Default recommended model
});
```

---

## BYOK (Bring Your Own Key)

The SDK supports using your own API keys from LLM providers (OpenAI, Azure, Anthropic). Refer to individual SDK documentation for configuration details.

---

## Error Handling

### Common Errors

| Error                 | Cause             | Solution                      |
| --------------------- | ----------------- | ----------------------------- |
| `ConnectionError`     | CLI not running   | Install and start Copilot CLI |
| `AuthenticationError` | Not authenticated | Run `copilot auth login`      |
| `TimeoutError`        | Response timeout  | Increase timeout or retry     |

### Error Handling Pattern

```typescript
try {
  const response = await session.sendAndWait({ prompt: "..." });
  console.log(response?.data.content);
} catch (error) {
  if (error.code === "CONNECTION_ERROR") {
    console.error("CLI not running");
  } else if (error.code === "TIMEOUT") {
    console.error("Request timed out");
  } else {
    console.error("Unexpected error:", error);
  }
}
```

---

## Billing

SDK usage counts toward your premium request quota, same as Copilot CLI. See [GitHub Copilot billing](https://docs.github.com/en/copilot/concepts/billing/copilot-requests) for details.
