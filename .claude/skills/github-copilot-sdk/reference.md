# GitHub Copilot SDK API Reference

Complete API reference for GitHub Copilot SDK across all supported languages.

## CopilotClient API

### Initialization

**Python:**
```python
from github_copilot_sdk import CopilotClient

# Default initialization (uses GitHub token from environment)
client = CopilotClient()

# With custom token
client = CopilotClient(token="ghp_...")

# With BYOK configuration
client = CopilotClient(
    azure_endpoint="https://your-instance.openai.azure.com",
    azure_key="your-api-key",
    azure_deployment="gpt-4"
)
```

**TypeScript:**
```typescript
import { CopilotClient } from '@github/copilot-sdk';

// Default initialization
const client = new CopilotClient();

// With custom token
const client = new CopilotClient({ token: 'ghp_...' });

// With BYOK configuration
const client = new CopilotClient({
  azureEndpoint: 'https://your-instance.openai.azure.com',
  azureKey: 'your-api-key',
  azureDeployment: 'gpt-4'
});
```

**Go:**
```go
import "github.com/github/copilot-sdk-go"

// Default initialization
client := copilot.NewClient()

// With custom token
client := copilot.NewClient(copilot.WithToken("ghp_..."))

// With BYOK configuration
client := copilot.NewClient(
    copilot.WithAzureEndpoint("https://your-instance.openai.azure.com"),
    copilot.WithAzureKey("your-api-key"),
    copilot.WithAzureDeployment("gpt-4"),
)
```

**.NET:**
```csharp
using GitHub.Copilot;

// Default initialization
var client = new CopilotClient();

// With custom token
var client = new CopilotClient(token: "ghp_...");

// With BYOK configuration
var client = new CopilotClient(new CopilotOptions
{
    AzureEndpoint = "https://your-instance.openai.azure.com",
    AzureKey = "your-api-key",
    AzureDeployment = "gpt-4"
});
```

### Configuration Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `token` | string | GitHub authentication token | From `GITHUB_TOKEN` env |
| `azure_endpoint` | string | Azure OpenAI endpoint URL | `null` |
| `azure_key` | string | Azure OpenAI API key | `null` |
| `azure_deployment` | string | Azure OpenAI deployment name | `null` |
| `timeout` | int | Request timeout in seconds | `30` |
| `max_retries` | int | Maximum retry attempts | `3` |
| `model` | string | Model to use (non-BYOK) | `gpt-4` |

## Session API

### Create Session

**Python:**
```python
session = client.create_session(
    session_id="unique-session-id",  # Optional, auto-generated if omitted
    context={"repository": "owner/repo"}  # Optional metadata
)
```

**TypeScript:**
```typescript
const session = await client.createSession({
  sessionId: 'unique-session-id',  // Optional
  context: { repository: 'owner/repo' }  // Optional
});
```

**Go:**
```go
session, err := client.CreateSession(ctx, &copilot.SessionOptions{
    SessionID: "unique-session-id",  // Optional
    Context: map[string]string{"repository": "owner/repo"},
})
```

**.NET:**
```csharp
var session = await client.CreateSessionAsync(new SessionOptions
{
    SessionId = "unique-session-id",  // Optional
    Context = new Dictionary<string, string> { ["repository"] = "owner/repo" }
});
```

### Send Message (Non-Streaming)

**Python:**
```python
response = session.send_message(
    prompt="Explain this code",
    attachments=[
        {"type": "code", "content": "def hello(): pass", "language": "python"}
    ],
    mode="agent"  # "agent" or "chat"
)

print(response.content)
print(response.metadata)
```

**TypeScript:**
```typescript
const response = await session.sendMessage({
  prompt: 'Explain this code',
  attachments: [
    { type: 'code', content: 'def hello(): pass', language: 'python' }
  ],
  mode: 'agent'
});

console.log(response.content);
console.log(response.metadata);
```

**Go:**
```go
response, err := session.SendMessage(ctx, &copilot.MessageRequest{
    Prompt: "Explain this code",
    Attachments: []copilot.Attachment{
        {Type: "code", Content: "def hello(): pass", Language: "python"},
    },
    Mode: copilot.ModeAgent,
})
```

**.NET:**
```csharp
var response = await session.SendMessageAsync(new MessageRequest
{
    Prompt = "Explain this code",
    Attachments = new[]
    {
        new Attachment { Type = "code", Content = "def hello(): pass", Language = "python" }
    },
    Mode = MessageMode.Agent
});
```

### Stream Message

**Python:**
```python
for event in session.stream_message(
    prompt="Generate a function",
    mode="agent"
):
    if event.type == "content":
        print(event.data.content, end="", flush=True)
    elif event.type == "tool_call":
        print(f"\n[Tool: {event.data.tool_name}]")
    elif event.type == "done":
        print("\n[Complete]")
```

**TypeScript:**
```typescript
for await (const event of session.streamMessage({
  prompt: 'Generate a function',
  mode: 'agent'
})) {
  switch (event.type) {
    case 'content':
      process.stdout.write(event.data.content);
      break;
    case 'tool_call':
      console.log(`\n[Tool: ${event.data.toolName}]`);
      break;
    case 'done':
      console.log('\n[Complete]');
      break;
  }
}
```

**Go:**
```go
stream, err := session.StreamMessage(ctx, &copilot.MessageRequest{
    Prompt: "Generate a function",
    Mode: copilot.ModeAgent,
})

for stream.Next() {
    event := stream.Event()
    switch event.Type {
    case copilot.EventTypeContent:
        fmt.Print(event.Data.Content)
    case copilot.EventTypeToolCall:
        fmt.Printf("\n[Tool: %s]\n", event.Data.ToolName)
    case copilot.EventTypeDone:
        fmt.Println("\n[Complete]")
    }
}
```

**.NET:**
```csharp
await foreach (var evt in session.StreamMessageAsync(new MessageRequest
{
    Prompt = "Generate a function",
    Mode = MessageMode.Agent
}))
{
    switch (evt.Type)
    {
        case EventType.Content:
            Console.Write(evt.Data.Content);
            break;
        case EventType.ToolCall:
            Console.WriteLine($"\n[Tool: {evt.Data.ToolName}]");
            break;
        case EventType.Done:
            Console.WriteLine("\n[Complete]");
            break;
    }
}
```

### Close Session

**Python:**
```python
session.close()
```

**TypeScript:**
```typescript
await session.close();
```

**Go:**
```go
err := session.Close(ctx)
```

**.NET:**
```csharp
await session.CloseAsync();
```

## Message Options

### Prompt Formats

**Simple String:**
```python
prompt = "Explain this code"
```

**Multi-Turn Conversation:**
```python
messages = [
    {"role": "user", "content": "What's a binary tree?"},
    {"role": "assistant", "content": "A binary tree is..."},
    {"role": "user", "content": "Show me an implementation"}
]
```

### Attachment Types

**Code Attachment:**
```python
{
    "type": "code",
    "content": "def hello(): print('hi')",
    "language": "python",
    "path": "src/main.py"  # Optional
}
```

**File Attachment:**
```python
{
    "type": "file",
    "path": "/path/to/file.txt",
    "content": "File contents...",
    "mime_type": "text/plain"
}
```

**Image Attachment:**
```python
{
    "type": "image",
    "url": "https://example.com/image.png",
    # OR
    "data": "base64-encoded-image-data",
    "mime_type": "image/png"
}
```

**Reference Attachment:**
```python
{
    "type": "reference",
    "title": "Related Documentation",
    "url": "https://docs.example.com/api",
    "snippet": "Relevant excerpt..."  # Optional
}
```

### Message Modes

- **`agent`**: Full agentic capabilities with tool use, reasoning, multi-step planning
- **`chat`**: Conversational mode without tool calling, faster responses

## Tool Definition API

### Define Custom Tool

**Python:**
```python
from github_copilot_sdk import Tool

def search_files(query: str, file_type: str = "py") -> list[str]:
    """Search for files matching query.
    
    Args:
        query: Search query string
        file_type: File extension to filter (default: py)
    
    Returns:
        List of matching file paths
    """
    # Implementation
    return ["file1.py", "file2.py"]

# Register tool
tool = Tool.from_function(
    search_files,
    name="search_files",  # Optional, uses function name if omitted
    description="Search codebase for files matching query"
)

client.register_tool(tool)
```

**TypeScript:**
```typescript
import { Tool } from '@github/copilot-sdk';

const searchFilesTool = new Tool({
  name: 'search_files',
  description: 'Search codebase for files matching query',
  parameters: {
    type: 'object',
    properties: {
      query: { type: 'string', description: 'Search query string' },
      fileType: { type: 'string', description: 'File extension to filter', default: 'py' }
    },
    required: ['query']
  },
  handler: async ({ query, fileType = 'py' }) => {
    // Implementation
    return ['file1.py', 'file2.py'];
  }
});

client.registerTool(searchFilesTool);
```

**Go:**
```go
tool := &copilot.Tool{
    Name: "search_files",
    Description: "Search codebase for files matching query",
    Parameters: copilot.Parameters{
        Type: "object",
        Properties: map[string]copilot.Property{
            "query": {Type: "string", Description: "Search query string"},
            "file_type": {Type: "string", Description: "File extension", Default: "py"},
        },
        Required: []string{"query"},
    },
    Handler: func(ctx context.Context, args map[string]interface{}) (interface{}, error) {
        query := args["query"].(string)
        fileType := args["file_type"].(string)
        // Implementation
        return []string{"file1.py", "file2.py"}, nil
    },
}

client.RegisterTool(tool)
```

**.NET:**
```csharp
var searchFilesTool = new Tool
{
    Name = "search_files",
    Description = "Search codebase for files matching query",
    Parameters = new ToolParameters
    {
        Type = "object",
        Properties = new Dictionary<string, ParameterProperty>
        {
            ["query"] = new() { Type = "string", Description = "Search query string" },
            ["fileType"] = new() { Type = "string", Description = "File extension", Default = "py" }
        },
        Required = new[] { "query" }
    },
    Handler = async (args) =>
    {
        var query = args["query"].ToString();
        var fileType = args.GetValueOrDefault("fileType", "py").ToString();
        // Implementation
        return new[] { "file1.py", "file2.py" };
    }
};

client.RegisterTool(searchFilesTool);
```

### Tool Parameter Schema

Tool parameters follow JSON Schema specification:

```json
{
  "type": "object",
  "properties": {
    "param_name": {
      "type": "string|number|boolean|array|object",
      "description": "Parameter description",
      "enum": ["option1", "option2"],  // Optional
      "default": "default_value",       // Optional
      "items": { "type": "string" }     // For arrays
    }
  },
  "required": ["param_name"]
}
```

**Supported Types:**
- `string`, `number`, `integer`, `boolean`
- `array` (with `items` schema)
- `object` (with nested `properties`)

## Event Types

### Content Event

Emitted when new content is generated.

```python
{
    "type": "content",
    "data": {
        "content": "Generated text chunk",
        "delta": true  # True for streaming chunks, False for complete content
    }
}
```

### Tool Call Event

Emitted when a tool is being called.

```python
{
    "type": "tool_call",
    "data": {
        "tool_name": "search_files",
        "tool_id": "call_abc123",
        "arguments": {"query": "main.py", "file_type": "py"}
    }
}
```

### Tool Result Event

Emitted when a tool call completes.

```python
{
    "type": "tool_result",
    "data": {
        "tool_id": "call_abc123",
        "result": ["src/main.py", "tests/main.py"],
        "error": None  # Set if tool execution failed
    }
}
```

### Confirmation Request Event

Emitted when agent requests user confirmation (e.g., for dangerous operations).

```python
{
    "type": "confirmation_request",
    "data": {
        "message": "About to delete 5 files. Proceed?",
        "confirmation_id": "conf_xyz789",
        "default": False  # Default choice if timeout
    }
}
```

**Responding to Confirmation:**
```python
session.send_confirmation(
    confirmation_id="conf_xyz789",
    approved=True
)
```

### Error Event

Emitted when an error occurs during processing.

```python
{
    "type": "error",
    "data": {
        "error": "Rate limit exceeded",
        "error_code": "rate_limit",
        "retry_after": 60  # Seconds until retry allowed
    }
}
```

### Done Event

Emitted when message processing completes.

```python
{
    "type": "done",
    "data": {
        "finish_reason": "completed",  # completed | length | tool_calls | error
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 85,
            "total_tokens": 205
        }
    }
}
```

### Progress Event

Emitted during long-running operations.

```python
{
    "type": "progress",
    "data": {
        "step": "Analyzing codebase",
        "current": 5,
        "total": 10,
        "percent": 50.0
    }
}
```

## MCP Integration

### Connect to MCP Server

**Python:**
```python
from github_copilot_sdk import MCPConnection

# Connect to local MCP server
mcp = MCPConnection.connect_local(
    command=["python", "server.py"],
    env={"API_KEY": "secret"}
)

# Connect to remote MCP server via SSE
mcp = MCPConnection.connect_sse(
    url="https://mcp-server.example.com/events"
)

# Connect via stdio
mcp = MCPConnection.connect_stdio(
    command=["mcp-server", "--config", "config.json"]
)

# Register MCP tools with client
client.register_mcp_connection(mcp)
```

**TypeScript:**
```typescript
import { MCPConnection } from '@github/copilot-sdk';

// Connect to local MCP server
const mcp = await MCPConnection.connectLocal({
  command: ['python', 'server.py'],
  env: { API_KEY: 'secret' }
});

// Connect to remote MCP server
const mcp = await MCPConnection.connectSSE({
  url: 'https://mcp-server.example.com/events'
});

// Register with client
client.registerMCPConnection(mcp);
```

**Go:**
```go
import "github.com/github/copilot-sdk-go/mcp"

// Connect to local MCP server
conn, err := mcp.ConnectLocal(ctx, &mcp.LocalConfig{
    Command: []string{"python", "server.py"},
    Env: map[string]string{"API_KEY": "secret"},
})

// Register with client
client.RegisterMCPConnection(conn)
```

**.NET:**
```csharp
using GitHub.Copilot.MCP;

// Connect to local MCP server
var mcp = await MCPConnection.ConnectLocalAsync(new LocalMCPConfig
{
    Command = new[] { "python", "server.py" },
    Environment = new Dictionary<string, string> { ["API_KEY"] = "secret" }
});

// Register with client
client.RegisterMCPConnection(mcp);
```

### List Available MCP Tools

**Python:**
```python
tools = mcp.list_tools()
for tool in tools:
    print(f"{tool.name}: {tool.description}")
```

**TypeScript:**
```typescript
const tools = await mcp.listTools();
tools.forEach(tool => {
  console.log(`${tool.name}: ${tool.description}`);
});
```

### MCP Resource Access

**Python:**
```python
# Read resource
resource = mcp.read_resource("file:///path/to/file.txt")
print(resource.content)

# List resources
resources = mcp.list_resources()
for res in resources:
    print(f"{res.uri}: {res.name}")
```

## BYOK Configuration

### Azure OpenAI

**Python:**
```python
client = CopilotClient(
    azure_endpoint="https://your-instance.openai.azure.com",
    azure_key="your-api-key",
    azure_deployment="gpt-4",
    api_version="2024-02-01"  # Optional
)
```

### OpenAI Direct

**Python:**
```python
client = CopilotClient(
    openai_api_key="sk-...",
    model="gpt-4-turbo"
)
```

### Custom Endpoint

**Python:**
```python
client = CopilotClient(
    endpoint="https://custom-llm-provider.com/v1",
    api_key="custom-key",
    model="custom-model"
)
```

### Environment Variables

All BYOK options can be configured via environment variables:

```bash
# Azure OpenAI
export AZURE_OPENAI_ENDPOINT="https://your-instance.openai.azure.com"
export AZURE_OPENAI_KEY="your-api-key"
export AZURE_OPENAI_DEPLOYMENT="gpt-4"

# OpenAI Direct
export OPENAI_API_KEY="sk-..."

# Custom
export COPILOT_ENDPOINT="https://custom-llm-provider.com/v1"
export COPILOT_API_KEY="custom-key"
export COPILOT_MODEL="custom-model"
```

## Error Handling

### Exception Types

**Python:**
```python
from github_copilot_sdk.exceptions import (
    CopilotException,        # Base exception
    AuthenticationError,      # Invalid token/credentials
    RateLimitError,          # Rate limit exceeded
    TimeoutError,            # Request timeout
    InvalidRequestError,     # Malformed request
    ServerError,             # Server-side error
    ConnectionError,         # Network issues
    SessionClosedError       # Session already closed
)
```

**TypeScript:**
```typescript
import {
  CopilotException,
  AuthenticationError,
  RateLimitError,
  TimeoutError,
  InvalidRequestError,
  ServerError
} from '@github/copilot-sdk';
```

### Error Handling Patterns

**Python:**
```python
from github_copilot_sdk.exceptions import RateLimitError, AuthenticationError

try:
    response = session.send_message(prompt="Hello")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
    time.sleep(e.retry_after)
    response = session.send_message(prompt="Hello")
except AuthenticationError:
    print("Invalid credentials. Please check your token.")
except CopilotException as e:
    print(f"Copilot error: {e}")
```

**TypeScript:**
```typescript
try {
  const response = await session.sendMessage({ prompt: 'Hello' });
} catch (error) {
  if (error instanceof RateLimitError) {
    console.log(`Rate limited. Retry after ${error.retryAfter} seconds`);
    await new Promise(resolve => setTimeout(resolve, error.retryAfter * 1000));
    const response = await session.sendMessage({ prompt: 'Hello' });
  } else if (error instanceof AuthenticationError) {
    console.log('Invalid credentials. Please check your token.');
  } else {
    console.error('Copilot error:', error);
  }
}
```

### Retry Strategies

**Python with Built-in Retry:**
```python
client = CopilotClient(
    max_retries=3,
    retry_delay=1.0,
    exponential_backoff=True
)
```

**Manual Retry Logic:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def send_with_retry():
    return session.send_message(prompt="Hello")
```

### Error Metadata

All exceptions include additional context:

```python
try:
    session.send_message(prompt="Hello")
except CopilotException as e:
    print(e.message)        # Human-readable error message
    print(e.error_code)     # Machine-readable code
    print(e.status_code)    # HTTP status code (if applicable)
    print(e.request_id)     # Request ID for debugging
    print(e.details)        # Additional error details
```

## Rate Limiting

### Rate Limit Headers

After each request, check rate limit status:

**Python:**
```python
response = session.send_message(prompt="Hello")
print(f"Remaining: {response.rate_limit.remaining}")
print(f"Reset at: {response.rate_limit.reset_at}")
print(f"Limit: {response.rate_limit.limit}")
```

### Proactive Rate Limit Check

**Python:**
```python
if client.rate_limit.remaining < 10:
    wait_time = (client.rate_limit.reset_at - datetime.now()).total_seconds()
    print(f"Low on quota. Waiting {wait_time}s")
    time.sleep(wait_time)
```

## Advanced Features

### Context Management

**Python:**
```python
# Set global context for all sessions
client.set_context({
    "repository": "owner/repo",
    "branch": "main",
    "user": "username"
})

# Override per session
session = client.create_session(
    context={"branch": "feature-branch"}  # Merges with global context
)
```

### Response Callbacks

**Python:**
```python
def on_content(content: str):
    print(f"Generated: {content}")

def on_tool_call(tool_name: str, args: dict):
    print(f"Calling {tool_name} with {args}")

session.stream_message(
    prompt="Generate code",
    on_content=on_content,
    on_tool_call=on_tool_call
)
```

### Session History

**Python:**
```python
# Get conversation history
history = session.get_history()
for msg in history:
    print(f"{msg.role}: {msg.content}")

# Clear history
session.clear_history()

# Export history
session.export_history("conversation.json")
```

### Model Selection Per Message

**Python:**
```python
# Override model for specific message
response = session.send_message(
    prompt="Complex reasoning task",
    model="gpt-4-turbo"  # Use different model
)
```

---

**See Also:**
- [Quick Start Guide](quickstart.md)
- [Tutorial](tutorial.md)
- [Examples Repository](https://github.com/github/copilot-sdk-examples)
