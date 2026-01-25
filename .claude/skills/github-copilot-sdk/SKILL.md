---
name: github-copilot-sdk
description: Build applications with GitHub Copilot SDK across Python, TypeScript, Go, and .NET
version: 1.0.0
activation_keywords:
  - copilot sdk
  - github copilot sdk
  - CopilotClient
  - copilot streaming
  - "@github/copilot-sdk"
  - copilot sessions
  - copilot tools
  - github copilot api
auto_activate: true
token_budget: 2200
source_urls:
  - https://github.com/github/copilot-sdk
  - https://docs.github.com/en/copilot/building-copilot-extensions
---

# GitHub Copilot SDK

Build AI-powered applications using the official GitHub Copilot SDK. Available in Python, TypeScript, Go, and .NET.

**Status**: Technical Preview (as of 2024)

## Overview

The GitHub Copilot SDK provides programmatic access to GitHub Copilot's capabilities through a unified API across multiple languages. The SDK communicates with Copilot via JSON-RPC through the Copilot CLI in server mode.

**Architecture**: Your App → SDK → JSON-RPC → Copilot CLI (server mode) → GitHub Copilot

**Key Capabilities**:
- **Conversational AI** - Multi-turn chat sessions with context
- **Streaming Responses** - Real-time token streaming for better UX
- **Custom Tools** - Extend Copilot with your own functions
- **MCP Integration** - Connect to Model Context Protocol servers
- **BYOK** - Bring Your Own Key for custom deployments

## Installation

```bash
# Python
pip install github-copilot-sdk

# TypeScript
npm install @github/copilot-sdk

# Go
go get github.com/github/copilot-sdk/go

# .NET
dotnet add package GitHub.Copilot.SDK
```

## Quick Start

### Python Example

```python
from github_copilot_sdk import CopilotClient

# Initialize client
client = CopilotClient()

# Create session
session = client.create_session()

# Send message and stream response
for chunk in session.send_message("Explain Python decorators", stream=True):
    print(chunk.text, end="", flush=True)

# Continue conversation
response = session.send_message("Show me an example")
print(response.text)

# Clean up
session.close()
client.close()
```

### TypeScript Example

```typescript
import { CopilotClient } from '@github/copilot-sdk';

// Initialize client
const client = new CopilotClient();

// Create session
const session = await client.createSession();

// Send message and stream response
const stream = await session.sendMessage('Explain TypeScript generics', { stream: true });

for await (const chunk of stream) {
  process.stdout.write(chunk.text);
}

// Continue conversation
const response = await session.sendMessage('Show me an example');
console.log(response.text);

// Clean up
await session.close();
await client.close();
```

### Go Example

```go
package main

import (
    "context"
    "fmt"
    "io"
    
    copilot "github.com/github/copilot-sdk/go"
)

func main() {
    ctx := context.Background()
    
    // Initialize client
    client, err := copilot.NewClient(ctx)
    if err != nil {
        panic(err)
    }
    defer client.Close()
    
    // Create session
    session, err := client.CreateSession(ctx)
    if err != nil {
        panic(err)
    }
    defer session.Close()
    
    // Send message and stream response
    stream, err := session.SendMessage(ctx, "Explain Go interfaces", &copilot.SendOptions{Stream: true})
    if err != nil {
        panic(err)
    }
    
    for {
        chunk, err := stream.Recv()
        if err == io.EOF {
            break
        }
        if err != nil {
            panic(err)
        }
        fmt.Print(chunk.Text)
    }
}
```

### .NET Example

```csharp
using GitHub.Copilot.SDK;

// Initialize client
using var client = new CopilotClient();

// Create session
var session = await client.CreateSessionAsync();

// Send message and stream response
await foreach (var chunk in session.SendMessageAsync("Explain C# LINQ", stream: true))
{
    Console.Write(chunk.Text);
}

// Continue conversation
var response = await session.SendMessageAsync("Show me an example");
Console.WriteLine(response.Text);

// Clean up
await session.CloseAsync();
```

## Core Concepts

| Concept | Description | Usage |
|---------|-------------|-------|
| **CopilotClient** | Main entry point to SDK | Create once, reuse for multiple sessions |
| **Session** | Isolated conversation context | One per user conversation thread |
| **Message** | User or assistant text | `send_message()` / `sendMessage()` |
| **Streaming** | Real-time token delivery | Set `stream=True` for better UX |
| **Tools** | Custom functions Copilot can call | Register with `register_tool()` |
| **Events** | Session lifecycle notifications | `on_message`, `on_error`, `on_complete` |

## Common Patterns

### Basic Conversation Flow

```python
# 1. Initialize (once per application)
client = CopilotClient()

# 2. Create session (once per conversation)
session = client.create_session()

# 3. Send messages (multiple times)
response = session.send_message("Your prompt here")
print(response.text)

# 4. Clean up (when done)
session.close()
client.close()
```

### Streaming for Better UX

```python
# Stream tokens as they arrive
for chunk in session.send_message("Generate a long response", stream=True):
    print(chunk.text, end="", flush=True)
print()  # New line after streaming completes
```

### Adding Custom Tools

```python
# Define a tool
def get_weather(location: str) -> str:
    """Get current weather for a location."""
    # Your implementation here
    return f"Weather in {location}: Sunny, 72°F"

# Register with session
session.register_tool(
    name="get_weather",
    description="Get current weather for any location",
    function=get_weather,
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name"}
        },
        "required": ["location"]
    }
)

# Now Copilot can call your tool
response = session.send_message("What's the weather in Seattle?")
```

### Error Handling

```python
from github_copilot_sdk import CopilotError, SessionError

try:
    session = client.create_session()
    response = session.send_message("Hello")
except SessionError as e:
    print(f"Session error: {e}")
except CopilotError as e:
    print(f"SDK error: {e}")
finally:
    if session:
        session.close()
```

## Event Types Reference

| Event | When Triggered | Use Case |
|-------|---------------|----------|
| `on_message` | Each message sent/received | Logging, analytics |
| `on_stream_chunk` | Each streaming token | Custom rendering |
| `on_tool_call` | Copilot calls your tool | Validation, logging |
| `on_error` | Any error occurs | Error handling |
| `on_complete` | Response fully delivered | Cleanup, metrics |
| `on_session_start` | Session created | Initialization |
| `on_session_end` | Session closed | Cleanup |

## Configuration Options

```python
# Client configuration
client = CopilotClient(
    api_key="sk-...",          # Optional: BYOK mode
    timeout=30,                # Request timeout in seconds
    max_retries=3,             # Retry failed requests
    log_level="INFO"           # Logging verbosity
)

# Session configuration
session = client.create_session(
    model="gpt-4",             # Model selection
    temperature=0.7,           # Creativity (0.0-1.0)
    max_tokens=2000,           # Response length limit
    system_prompt="You are..." # System instructions
)
```

## MCP Integration

Connect to Model Context Protocol servers to extend Copilot's capabilities:

```python
# Connect to MCP server
session.connect_mcp_server(
    url="http://localhost:3000",
    tools=["filesystem", "database", "api"]
)

# Now Copilot can use MCP tools
response = session.send_message("Read the config file")
```

## Navigation to Supporting Files

- **[reference.md](./reference.md)** - Complete API reference for all languages
- **[multi-language.md](./multi-language.md)** - Language selection guide and trade-offs
- **[examples.md](./examples.md)** - Copy-paste production examples
- **[patterns.md](./patterns.md)** - Best practices and anti-patterns
- **[drift-detection.md](./drift-detection.md)** - Version tracking and compatibility

## Common Issues

**"SDK not found" error**
- Ensure Copilot CLI is installed: `gh copilot --version`
- Verify CLI is in PATH
- Check SDK installation: `pip show github-copilot-sdk`

**"Connection refused" error**
- Copilot CLI server mode may not be running
- SDK auto-starts server, but check firewall/permissions
- Try manual start: `gh copilot serve`

**"Authentication failed" error**
- Run `gh auth login` to authenticate
- For BYOK mode, verify API key is valid
- Check GitHub Copilot subscription status

**Streaming not working**
- Ensure `stream=True` parameter is set
- Use async iteration (Python) or `await for` (TypeScript)
- Check network for buffering/proxy issues

## Best Practices

1. **Session Management** - One session per conversation, close when done
2. **Error Handling** - Always wrap SDK calls in try/catch blocks
3. **Streaming** - Use streaming for responses >100 tokens
4. **Tool Design** - Keep tools focused, single-purpose, fast (<1s)
5. **Context Size** - Monitor token usage, prune old messages if needed
6. **Connection Pooling** - Reuse CopilotClient, don't create per request
7. **Async Operations** - Use async/await in Python/TypeScript for better performance

## SDK vs Agent Frameworks

**Use GitHub Copilot SDK when:**
- Building GitHub-integrated tools
- Need official GitHub Copilot access
- Want simplest path to Copilot features
- Single-agent, straightforward workflows

**Consider Agent Frameworks (AutoGen, LangChain, etc.) when:**
- Multi-agent coordination required
- Complex iterative workflows (review loops)
- Need framework-specific tools/integrations
- Building autonomous agents with self-improvement

The Copilot SDK is lower-level and more direct. For complex agent architectures, consider wrapping it in a framework.

## Language Selection Quick Guide

| Language | Best For | Avoid If |
|----------|----------|----------|
| **Python** | Rapid prototyping, data science, scripting | Need max performance |
| **TypeScript** | Web apps, Node.js ecosystem, type safety | Team unfamiliar with JS |
| **Go** | High performance, concurrency, microservices | Need rich library ecosystem |
| **.NET** | Enterprise, Windows, Azure integration | Non-Windows primary target |

See [multi-language.md](./multi-language.md) for detailed comparison.

## Next Steps

1. **First Agent** - Copy Quick Start example above, run it
2. **Add Tools** - Review Custom Tools pattern, register one function
3. **Production Patterns** - Read [patterns.md](./patterns.md) before deploying
4. **API Details** - Bookmark [reference.md](./reference.md) for lookups

## Additional Resources

- **GitHub Repo**: https://github.com/github/copilot-sdk
- **Official Docs**: https://docs.github.com/en/copilot/building-copilot-extensions
- **Issue Tracker**: https://github.com/github/copilot-sdk/issues
- **Changelog**: Check [drift-detection.md](./drift-detection.md) for version updates

---

**Start building**: Copy the Quick Start example for your language and run it now. Most applications only need the patterns shown above.
