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
import asyncio
from copilot import CopilotClient

async def main():
    async with CopilotClient() as client:
        async with await client.create_session({"model": "gpt-4.1"}) as session:
            # Set up event handler for responses
            done = asyncio.Event()
            
            def handler(event):
                if event.type == "assistant.message":
                    print(event.data.content)
                elif event.type == "session.idle":
                    done.set()
            
            session.on(handler)
            
            # Send message
            await session.send({"prompt": "Explain Python decorators"})
            await done.wait()

asyncio.run(main())
```

### TypeScript Example

```typescript
import { CopilotClient } from "@github/copilot-sdk";

const client = new CopilotClient();
const session = await client.createSession({ model: "gpt-4.1" });

// Set up event handler
session.on((event) => {
  if (event.type === "assistant.message") {
    console.log(event.data.content);
  }
});

// Send message and wait for completion
await session.sendAndWait({ prompt: "Explain TypeScript generics" });

// Cleanup
await session.destroy();
await client.stop();
```

### Go Example

```go
package main

import (
    "fmt"
    "log"
    "os"
    
    copilot "github.com/github/copilot-sdk/go"
)

func main() {
    client := copilot.NewClient(nil)
    if err := client.Start(); err != nil {
        log.Fatal(err)
    }
    defer client.Stop()
    
    session, err := client.CreateSession(&copilot.SessionConfig{Model: "gpt-4.1"})
    if err != nil {
        log.Fatal(err)
    }
    
    // Set up event handler
    session.On(func(event copilot.SessionEvent) {
        if event.Type == "assistant.message" {
            fmt.Println(*event.Data.Content)
        }
    })
    
    // Send and wait
    _, err = session.SendAndWait(copilot.MessageOptions{Prompt: "Explain Go interfaces"}, 0)
    if err != nil {
        log.Fatal(err)
    }
    os.Exit(0)
}
```

### .NET Example

```csharp
using GitHub.Copilot.SDK;

await using var client = new CopilotClient();
await using var session = await client.CreateSessionAsync(new SessionConfig { Model = "gpt-4.1" });

// Set up event handler
session.On(ev =>
{
    if (ev is AssistantMessageEvent msgEvent)
    {
        Console.WriteLine(msgEvent.Data.Content);
    }
});

// Send and wait
await session.SendAndWaitAsync(new MessageOptions { Prompt = "Explain C# LINQ" });
```

## Core Concepts

| Concept | Description | Usage |
|---------|-------------|-------|
| **CopilotClient** | Main entry point to SDK | Create once, reuse for multiple sessions |
| **Session** | Isolated conversation context | One per user conversation thread |
| **send()** | Send message to session | Returns message ID, use with event handlers |
| **sendAndWait()** | Send and wait for response | Simpler for single-turn interactions |
| **Events** | Session lifecycle notifications | `session.on(handler)` for streaming |
| **Tools** | Custom functions Copilot can call | `defineTool()` to register |

## Common Patterns

### Basic Conversation Flow (Python)

```python
import asyncio
from copilot import CopilotClient

async def main():
    async with CopilotClient() as client:
        async with await client.create_session({"model": "gpt-4.1"}) as session:
            # Simple send and wait
            response = await session.send_and_wait({"prompt": "Hello!"})
            if response:
                print(response.data.content)

# 4. Clean up (when done)
session.close()
client.close()
```

### Streaming for Better UX (Python)

```python
import asyncio
import sys
from copilot import CopilotClient

async def main():
    async with CopilotClient() as client:
        session = await client.create_session({"model": "gpt-4.1", "streaming": True})
        
        def handler(event):
            if event.type == "assistant.message.delta":
                sys.stdout.write(event.data.delta_content)
                sys.stdout.flush()
            elif event.type == "session.idle":
                print()  # New line when done
        
        session.on(handler)
        await session.send_and_wait({"prompt": "Generate a long response"})
        await session.destroy()

asyncio.run(main())
```

### Adding Custom Tools (TypeScript)

```typescript
import { defineTool } from "@github/copilot-sdk";

const getWeather = defineTool("get_weather", {
    description: "Get current weather for a city",
    parameters: {
        type: "object",
        properties: {
            city: { type: "string", description: "City name" }
        },
        required: ["city"]
    },
    handler: async ({ city }) => {
        return { city, temperature: "72°F", condition: "sunny" };
    }
});

const session = await client.createSession({
    model: "gpt-4.1",
    tools: [getWeather]
});

await session.sendAndWait({ prompt: "What's the weather in Seattle?" });
```

### Error Handling (Python)

```python
import asyncio
from copilot import CopilotClient

async def main():
    client = CopilotClient()
    session = None
    try:
        await client.start()
        session = await client.create_session({"model": "gpt-4.1"})
        response = await session.send_and_wait({"prompt": "Hello"})
        if response:
            print(response.data.content)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if session:
            await session.destroy()
        await client.stop()

asyncio.run(main())
```

## Event Types Reference

| Event Type | When Triggered | Data Available |
|------------|---------------|----------------|
| `user.message` | User sends message | `content` |
| `assistant.message` | Complete response | `content` |
| `assistant.message.delta` | Streaming chunk | `delta_content` |
| `tool.executionStart` | Tool call begins | `tool_name`, `arguments` |
| `tool.executionComplete` | Tool call ends | `result` |
| `session.start` | Session created | `session_id` |
| `session.idle` | Processing complete | - |
| `session.error` | Error occurred | `message` |

## Configuration Options

```python
# Python: Client configuration
client = CopilotClient({
    "cli_path": "/path/to/copilot",  # Custom CLI path
    "port": 0,                        # 0 = random port
    "auto_start": True,               # Start CLI automatically
    "log_level": "info"
})

# Session configuration  
session = await client.create_session({
    "model": "gpt-4.1",
    "streaming": True,
    "system_message": {
        "mode": "append",
        "content": "You are a helpful assistant."
    }
})
```

```typescript
// TypeScript: Client configuration
const client = new CopilotClient({
    cliPath: "/path/to/copilot",
    autoStart: true,
    logLevel: "debug"
});

// Session configuration
const session = await client.createSession({
    model: "gpt-4.1",
    streaming: true,
    systemMessage: {
        mode: "append",
        content: "You are a helpful assistant."
    }
});
```

## MCP Integration

Connect to Model Context Protocol servers to extend Copilot's capabilities:

```typescript
// TypeScript: MCP server configuration
const session = await client.createSession({
    model: "gpt-4.1",
    mcpServers: {
        github: {
            type: "http",
            url: "https://api.githubcopilot.com/mcp/"
        },
        filesystem: {
            type: "stdio",
            command: "npx",
            args: ["-y", "@modelcontextprotocol/server-filesystem"]
        }
    }
});

// Now Copilot can use MCP tools
await session.sendAndWait({ prompt: "Read the config file" });
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
- Ensure `streaming: true` in session config
- Use event handlers with `session.on()` to receive chunks
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
