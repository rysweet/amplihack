# GitHub Copilot SDK - Code Examples

Complete, runnable examples demonstrating GitHub Copilot SDK usage across Python, TypeScript, Go, and .NET.

## Prerequisites

**Install SDKs:**

```bash
# Python
pip install github-copilot-sdk

# TypeScript/JavaScript
npm install @github/copilot-sdk

# Go
go get github.com/github/copilot-sdk-go

# .NET
dotnet add package GitHub.Copilot.SDK
```

**Authentication:**

Set your GitHub token:
```bash
export GITHUB_TOKEN="your_token_here"
```

---

## 1. Hello World - Basic Client Usage

### Python

```python
from github_copilot_sdk import CopilotClient

def hello_world():
    """Basic chat completion request."""
    client = CopilotClient()
    
    response = client.chat.completions.create(
        messages=[
            {"role": "user", "content": "Say hello in 3 languages"}
        ],
        model="gpt-4"
    )
    
    print(response.choices[0].message.content)

if __name__ == "__main__":
    hello_world()
```

### TypeScript

```typescript
import { CopilotClient } from '@github/copilot-sdk';

async function helloWorld() {
  const client = new CopilotClient();
  
  const response = await client.chat.completions.create({
    messages: [
      { role: 'user', content: 'Say hello in 3 languages' }
    ],
    model: 'gpt-4'
  });
  
  console.log(response.choices[0].message.content);
}

helloWorld();
```

### Go

```go
package main

import (
    "context"
    "fmt"
    "log"
    
    copilot "github.com/github/copilot-sdk-go"
)

func main() {
    client := copilot.NewClient()
    
    resp, err := client.Chat.Completions.Create(context.Background(), &copilot.ChatRequest{
        Messages: []copilot.Message{
            {Role: "user", Content: "Say hello in 3 languages"},
        },
        Model: "gpt-4",
    })
    if err != nil {
        log.Fatal(err)
    }
    
    fmt.Println(resp.Choices[0].Message.Content)
}
```

### .NET

```csharp
using GitHub.Copilot.SDK;

class Program
{
    static async Task Main(string[] args)
    {
        var client = new CopilotClient();
        
        var response = await client.Chat.Completions.CreateAsync(new ChatRequest
        {
            Messages = new[]
            {
                new Message { Role = "user", Content = "Say hello in 3 languages" }
            },
            Model = "gpt-4"
        });
        
        Console.WriteLine(response.Choices[0].Message.Content);
    }
}
```

---

## 2. Streaming Responses - Real-time Output

### Python

```python
from github_copilot_sdk import CopilotClient

def streaming_example():
    """Stream response tokens as they arrive."""
    client = CopilotClient()
    
    stream = client.chat.completions.create(
        messages=[
            {"role": "user", "content": "Write a haiku about coding"}
        ],
        model="gpt-4",
        stream=True
    )
    
    print("Response: ", end="", flush=True)
    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()

if __name__ == "__main__":
    streaming_example()
```

### TypeScript

```typescript
import { CopilotClient } from '@github/copilot-sdk';

async function streamingExample() {
  const client = new CopilotClient();
  
  const stream = await client.chat.completions.create({
    messages: [
      { role: 'user', content: 'Write a haiku about coding' }
    ],
    model: 'gpt-4',
    stream: true
  });
  
  process.stdout.write('Response: ');
  
  for await (const chunk of stream) {
    if (chunk.choices[0]?.delta?.content) {
      process.stdout.write(chunk.choices[0].delta.content);
    }
  }
  
  console.log();
}

streamingExample();
```

### Go

```go
package main

import (
    "context"
    "fmt"
    "io"
    "log"
    
    copilot "github.com/github/copilot-sdk-go"
)

func main() {
    client := copilot.NewClient()
    
    stream, err := client.Chat.Completions.CreateStream(context.Background(), &copilot.ChatRequest{
        Messages: []copilot.Message{
            {Role: "user", Content: "Write a haiku about coding"},
        },
        Model:  "gpt-4",
        Stream: true,
    })
    if err != nil {
        log.Fatal(err)
    }
    defer stream.Close()
    
    fmt.Print("Response: ")
    for {
        chunk, err := stream.Recv()
        if err == io.EOF {
            break
        }
        if err != nil {
            log.Fatal(err)
        }
        
        if chunk.Choices[0].Delta.Content != "" {
            fmt.Print(chunk.Choices[0].Delta.Content)
        }
    }
    fmt.Println()
}
```

---

## 3. Multi-turn Conversation - Maintaining Context

### Python

```python
from github_copilot_sdk import CopilotClient

def multi_turn_conversation():
    """Maintain conversation history across turns."""
    client = CopilotClient()
    messages = []
    
    # Turn 1
    messages.append({"role": "user", "content": "My favorite color is blue."})
    response = client.chat.completions.create(messages=messages, model="gpt-4")
    messages.append({"role": "assistant", "content": response.choices[0].message.content})
    print(f"Assistant: {response.choices[0].message.content}")
    
    # Turn 2
    messages.append({"role": "user", "content": "What color did I just mention?"})
    response = client.chat.completions.create(messages=messages, model="gpt-4")
    messages.append({"role": "assistant", "content": response.choices[0].message.content})
    print(f"Assistant: {response.choices[0].message.content}")
    
    # Turn 3
    messages.append({"role": "user", "content": "Suggest 3 things in that color."})
    response = client.chat.completions.create(messages=messages, model="gpt-4")
    print(f"Assistant: {response.choices[0].message.content}")

if __name__ == "__main__":
    multi_turn_conversation()
```

### TypeScript

```typescript
import { CopilotClient, Message } from '@github/copilot-sdk';

async function multiTurnConversation() {
  const client = new CopilotClient();
  const messages: Message[] = [];
  
  // Turn 1
  messages.push({ role: 'user', content: 'My favorite color is blue.' });
  let response = await client.chat.completions.create({ messages, model: 'gpt-4' });
  messages.push({ role: 'assistant', content: response.choices[0].message.content });
  console.log(`Assistant: ${response.choices[0].message.content}`);
  
  // Turn 2
  messages.push({ role: 'user', content: 'What color did I just mention?' });
  response = await client.chat.completions.create({ messages, model: 'gpt-4' });
  messages.push({ role: 'assistant', content: response.choices[0].message.content });
  console.log(`Assistant: ${response.choices[0].message.content}`);
  
  // Turn 3
  messages.push({ role: 'user', content: 'Suggest 3 things in that color.' });
  response = await client.chat.completions.create({ messages, model: 'gpt-4' });
  console.log(`Assistant: ${response.choices[0].message.content}`);
}

multiTurnConversation();
```

---

## 4. Custom Tool Registration - Extending Capabilities

### Python

```python
from github_copilot_sdk import CopilotClient
import json

def get_weather(location: str, unit: str = "celsius") -> dict:
    """Simulated weather API."""
    return {
        "location": location,
        "temperature": 22,
        "unit": unit,
        "condition": "sunny"
    }

def custom_tools_example():
    """Register and use custom tools."""
    client = CopilotClient()
    
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["location"]
            }
        }
    }]
    
    messages = [{"role": "user", "content": "What's the weather in Paris?"}]
    
    response = client.chat.completions.create(
        messages=messages,
        model="gpt-4",
        tools=tools,
        tool_choice="auto"
    )
    
    # Handle tool call
    if response.choices[0].message.tool_calls:
        tool_call = response.choices[0].message.tool_calls[0]
        function_args = json.loads(tool_call.function.arguments)
        
        # Execute function
        result = get_weather(**function_args)
        
        # Send result back
        messages.append(response.choices[0].message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result)
        })
        
        final_response = client.chat.completions.create(
            messages=messages,
            model="gpt-4",
            tools=tools
        )
        
        print(final_response.choices[0].message.content)

if __name__ == "__main__":
    custom_tools_example()
```

### TypeScript

```typescript
import { CopilotClient } from '@github/copilot-sdk';

function getWeather(location: string, unit: string = 'celsius') {
  return {
    location,
    temperature: 22,
    unit,
    condition: 'sunny'
  };
}

async function customToolsExample() {
  const client = new CopilotClient();
  
  const tools = [{
    type: 'function' as const,
    function: {
      name: 'get_weather',
      description: 'Get current weather for a location',
      parameters: {
        type: 'object',
        properties: {
          location: { type: 'string', description: 'City name' },
          unit: { type: 'string', enum: ['celsius', 'fahrenheit'] }
        },
        required: ['location']
      }
    }
  }];
  
  const messages = [
    { role: 'user' as const, content: "What's the weather in Paris?" }
  ];
  
  const response = await client.chat.completions.create({
    messages,
    model: 'gpt-4',
    tools,
    tool_choice: 'auto'
  });
  
  // Handle tool call
  if (response.choices[0].message.tool_calls) {
    const toolCall = response.choices[0].message.tool_calls[0];
    const functionArgs = JSON.parse(toolCall.function.arguments);
    
    // Execute function
    const result = getWeather(functionArgs.location, functionArgs.unit);
    
    // Send result back
    messages.push(response.choices[0].message);
    messages.push({
      role: 'tool' as const,
      tool_call_id: toolCall.id,
      content: JSON.stringify(result)
    });
    
    const finalResponse = await client.chat.completions.create({
      messages,
      model: 'gpt-4',
      tools
    });
    
    console.log(finalResponse.choices[0].message.content);
  }
}

customToolsExample();
```

---

## 5. File Attachment - Sending Code/Files to Analyze

### Python

```python
from github_copilot_sdk import CopilotClient
from pathlib import Path

def analyze_code_file():
    """Analyze code file with Copilot."""
    client = CopilotClient()
    
    # Read file
    code = Path("example.py").read_text()
    
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Review this code for bugs and improvements:"},
                    {"type": "text", "text": f"```python\n{code}\n```"}
                ]
            }
        ],
        model="gpt-4"
    )
    
    print(response.choices[0].message.content)

def analyze_with_context():
    """Send multiple files for context."""
    client = CopilotClient()
    
    files = {
        "main.py": Path("main.py").read_text(),
        "utils.py": Path("utils.py").read_text(),
        "config.py": Path("config.py").read_text()
    }
    
    content_parts = [
        {"type": "text", "text": "Analyze these related files and suggest refactoring:"}
    ]
    
    for filename, code in files.items():
        content_parts.append({
            "type": "text",
            "text": f"\n\n**{filename}:**\n```python\n{code}\n```"
        })
    
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": content_parts}],
        model="gpt-4"
    )
    
    print(response.choices[0].message.content)

if __name__ == "__main__":
    analyze_code_file()
```

### .NET

```csharp
using GitHub.Copilot.SDK;
using System.IO;

class CodeAnalyzer
{
    static async Task Main(string[] args)
    {
        var client = new CopilotClient();
        
        // Read file
        var code = await File.ReadAllTextAsync("Example.cs");
        
        var response = await client.Chat.Completions.CreateAsync(new ChatRequest
        {
            Messages = new[]
            {
                new Message
                {
                    Role = "user",
                    Content = new[]
                    {
                        new ContentPart { Type = "text", Text = "Review this code for bugs:" },
                        new ContentPart { Type = "text", Text = $"```csharp\n{code}\n```" }
                    }
                }
            },
            Model = "gpt-4"
        });
        
        Console.WriteLine(response.Choices[0].Message.Content);
    }
}
```

---

## 6. MCP Server Connection - Using External Tools

### Python

```python
from github_copilot_sdk import CopilotClient
from github_copilot_sdk.mcp import MCPServerConnection

def connect_mcp_server():
    """Connect to MCP server for extended capabilities."""
    client = CopilotClient()
    
    # Connect to MCP server (e.g., filesystem, database, etc.)
    mcp = MCPServerConnection(
        server_url="http://localhost:8080/mcp",
        capabilities=["filesystem", "git"]
    )
    
    # Register MCP tools with client
    client.register_mcp_server(mcp)
    
    # Now Copilot can use MCP tools
    response = client.chat.completions.create(
        messages=[
            {"role": "user", "content": "List all Python files in the current directory"}
        ],
        model="gpt-4",
        mcp_enabled=True
    )
    
    print(response.choices[0].message.content)

if __name__ == "__main__":
    connect_mcp_server()
```

### TypeScript

```typescript
import { CopilotClient, MCPServerConnection } from '@github/copilot-sdk';

async function connectMCPServer() {
  const client = new CopilotClient();
  
  // Connect to MCP server
  const mcp = new MCPServerConnection({
    serverUrl: 'http://localhost:8080/mcp',
    capabilities: ['filesystem', 'git']
  });
  
  await client.registerMCPServer(mcp);
  
  // Use MCP capabilities
  const response = await client.chat.completions.create({
    messages: [
      { role: 'user', content: 'List all TypeScript files in the current directory' }
    ],
    model: 'gpt-4',
    mcpEnabled: true
  });
  
  console.log(response.choices[0].message.content);
}

connectMCPServer();
```

---

## 7. Error Handling with Retry - Robust Patterns

### Python

```python
from github_copilot_sdk import CopilotClient
from github_copilot_sdk.exceptions import RateLimitError, APIError
import time
from functools import wraps

def retry_with_backoff(max_retries=3, initial_delay=1):
    """Decorator for exponential backoff retry."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        print(f"Rate limited. Retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= 2
                except APIError as e:
                    print(f"API error: {e}")
                    raise
            
            raise last_exception
        return wrapper
    return decorator

@retry_with_backoff(max_retries=3, initial_delay=2)
def robust_completion(prompt: str) -> str:
    """Make completion with automatic retry."""
    client = CopilotClient()
    
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4",
        timeout=30.0
    )
    
    return response.choices[0].message.content

def main():
    try:
        result = robust_completion("Explain error handling best practices")
        print(result)
    except Exception as e:
        print(f"Failed after retries: {e}")

if __name__ == "__main__":
    main()
```

### Go

```go
package main

import (
    "context"
    "fmt"
    "log"
    "time"
    
    copilot "github.com/github/copilot-sdk-go"
)

func retryWithBackoff(ctx context.Context, maxRetries int, fn func() error) error {
    delay := 1 * time.Second
    
    for attempt := 0; attempt < maxRetries; attempt++ {
        err := fn()
        if err == nil {
            return nil
        }
        
        if copilot.IsRateLimitError(err) {
            if attempt < maxRetries-1 {
                fmt.Printf("Rate limited. Retrying in %v...\n", delay)
                time.Sleep(delay)
                delay *= 2
                continue
            }
        }
        
        return err
    }
    
    return fmt.Errorf("max retries exceeded")
}

func robustCompletion(ctx context.Context, prompt string) (string, error) {
    client := copilot.NewClient()
    var result string
    
    err := retryWithBackoff(ctx, 3, func() error {
        resp, err := client.Chat.Completions.Create(ctx, &copilot.ChatRequest{
            Messages: []copilot.Message{
                {Role: "user", Content: prompt},
            },
            Model:   "gpt-4",
            Timeout: 30 * time.Second,
        })
        if err != nil {
            return err
        }
        
        result = resp.Choices[0].Message.Content
        return nil
    })
    
    return result, err
}

func main() {
    ctx := context.Background()
    
    result, err := robustCompletion(ctx, "Explain error handling best practices")
    if err != nil {
        log.Fatal(err)
    }
    
    fmt.Println(result)
}
```

---

## 8. BYOK Configuration - Using Custom API Keys

### Python

```python
from github_copilot_sdk import CopilotClient

def byok_configuration():
    """Use custom API keys (OpenAI, Azure, etc.)."""
    
    # Option 1: OpenAI BYOK
    client = CopilotClient(
        api_key="sk-your-openai-key",
        base_url="https://api.openai.com/v1",
        provider="openai"
    )
    
    # Option 2: Azure OpenAI BYOK
    azure_client = CopilotClient(
        api_key="your-azure-key",
        base_url="https://your-resource.openai.azure.com",
        api_version="2024-02-15-preview",
        provider="azure"
    )
    
    # Option 3: From environment
    env_client = CopilotClient()  # Reads OPENAI_API_KEY env var
    
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "Hello from BYOK!"}],
        model="gpt-4"
    )
    
    print(response.choices[0].message.content)

if __name__ == "__main__":
    byok_configuration()
```

### .NET

```csharp
using GitHub.Copilot.SDK;

class BYOKExample
{
    static async Task Main(string[] args)
    {
        // Option 1: OpenAI BYOK
        var client = new CopilotClient(new ClientOptions
        {
            ApiKey = "sk-your-openai-key",
            BaseUrl = "https://api.openai.com/v1",
            Provider = "openai"
        });
        
        // Option 2: Azure OpenAI BYOK
        var azureClient = new CopilotClient(new ClientOptions
        {
            ApiKey = "your-azure-key",
            BaseUrl = "https://your-resource.openai.azure.com",
            ApiVersion = "2024-02-15-preview",
            Provider = "azure"
        });
        
        var response = await client.Chat.Completions.CreateAsync(new ChatRequest
        {
            Messages = new[] { new Message { Role = "user", Content = "Hello from BYOK!" } },
            Model = "gpt-4"
        });
        
        Console.WriteLine(response.Choices[0].Message.Content);
    }
}
```

---

## 9. Session Management - Save/Restore Conversations

### Python

```python
from github_copilot_sdk import CopilotClient
import json
from pathlib import Path

class ConversationSession:
    """Manage conversation sessions with persistence."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.client = CopilotClient()
        self.messages = []
        self.session_file = Path(f"sessions/{session_id}.json")
        self.load()
    
    def load(self):
        """Load session from disk."""
        if self.session_file.exists():
            data = json.loads(self.session_file.read_text())
            self.messages = data.get("messages", [])
            print(f"Loaded session with {len(self.messages)} messages")
    
    def save(self):
        """Save session to disk."""
        self.session_file.parent.mkdir(exist_ok=True)
        self.session_file.write_text(json.dumps({
            "session_id": self.session_id,
            "messages": self.messages
        }, indent=2))
    
    def chat(self, user_message: str) -> str:
        """Send message and get response."""
        self.messages.append({"role": "user", "content": user_message})
        
        response = self.client.chat.completions.create(
            messages=self.messages,
            model="gpt-4"
        )
        
        assistant_message = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": assistant_message})
        
        self.save()
        return assistant_message

def main():
    # Create or resume session
    session = ConversationSession("my-conversation-123")
    
    # Chat
    response1 = session.chat("Remember: my name is Alice")
    print(f"Assistant: {response1}")
    
    response2 = session.chat("What's my name?")
    print(f"Assistant: {response2}")
    
    # Session is automatically saved and can be resumed later

if __name__ == "__main__":
    main()
```

### TypeScript

```typescript
import { CopilotClient, Message } from '@github/copilot-sdk';
import * as fs from 'fs';
import * as path from 'path';

class ConversationSession {
  private sessionId: string;
  private client: CopilotClient;
  private messages: Message[] = [];
  private sessionFile: string;
  
  constructor(sessionId: string) {
    this.sessionId = sessionId;
    this.client = new CopilotClient();
    this.sessionFile = path.join('sessions', `${sessionId}.json`);
    this.load();
  }
  
  private load(): void {
    if (fs.existsSync(this.sessionFile)) {
      const data = JSON.parse(fs.readFileSync(this.sessionFile, 'utf-8'));
      this.messages = data.messages || [];
      console.log(`Loaded session with ${this.messages.length} messages`);
    }
  }
  
  private save(): void {
    const dir = path.dirname(this.sessionFile);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    
    fs.writeFileSync(this.sessionFile, JSON.stringify({
      sessionId: this.sessionId,
      messages: this.messages
    }, null, 2));
  }
  
  async chat(userMessage: string): Promise<string> {
    this.messages.push({ role: 'user', content: userMessage });
    
    const response = await this.client.chat.completions.create({
      messages: this.messages,
      model: 'gpt-4'
    });
    
    const assistantMessage = response.choices[0].message.content;
    this.messages.push({ role: 'assistant', content: assistantMessage });
    
    this.save();
    return assistantMessage;
  }
}

async function main() {
  const session = new ConversationSession('my-conversation-123');
  
  const response1 = await session.chat('Remember: my name is Alice');
  console.log(`Assistant: ${response1}`);
  
  const response2 = await session.chat("What's my name?");
  console.log(`Assistant: ${response2}`);
}

main();
```

---

## 10. Interactive CLI App - Full Working Example

### Python

```python
#!/usr/bin/env python3
"""Interactive CLI chat application with GitHub Copilot SDK."""

from github_copilot_sdk import CopilotClient
from github_copilot_sdk.exceptions import APIError
import sys
from typing import List, Dict

class ChatCLI:
    """Interactive chat CLI with history and commands."""
    
    COMMANDS = {
        "/help": "Show available commands",
        "/clear": "Clear conversation history",
        "/history": "Show conversation history",
        "/save <file>": "Save conversation to file",
        "/quit": "Exit the application"
    }
    
    def __init__(self):
        self.client = CopilotClient()
        self.messages: List[Dict[str, str]] = []
        self.running = True
    
    def show_help(self):
        """Display help information."""
        print("\n📚 Available Commands:")
        for cmd, desc in self.COMMANDS.items():
            print(f"  {cmd:<20} - {desc}")
        print()
    
    def clear_history(self):
        """Clear conversation history."""
        self.messages.clear()
        print("✨ Conversation history cleared.\n")
    
    def show_history(self):
        """Display conversation history."""
        if not self.messages:
            print("📭 No conversation history.\n")
            return
        
        print("\n📜 Conversation History:")
        for i, msg in enumerate(self.messages, 1):
            role = msg['role'].capitalize()
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            print(f"  {i}. [{role}] {content}")
        print()
    
    def save_conversation(self, filename: str):
        """Save conversation to file."""
        if not self.messages:
            print("⚠️  No conversation to save.\n")
            return
        
        try:
            with open(filename, 'w') as f:
                for msg in self.messages:
                    f.write(f"[{msg['role'].upper()}]\n{msg['content']}\n\n")
            print(f"💾 Conversation saved to {filename}\n")
        except IOError as e:
            print(f"❌ Error saving file: {e}\n")
    
    def handle_command(self, user_input: str) -> bool:
        """Handle special commands. Returns True if command was processed."""
        if not user_input.startswith('/'):
            return False
        
        parts = user_input.split(maxsplit=1)
        cmd = parts[0].lower()
        
        if cmd == '/help':
            self.show_help()
        elif cmd == '/clear':
            self.clear_history()
        elif cmd == '/history':
            self.show_history()
        elif cmd == '/save':
            if len(parts) < 2:
                print("⚠️  Usage: /save <filename>\n")
            else:
                self.save_conversation(parts[1])
        elif cmd == '/quit':
            self.running = False
            print("👋 Goodbye!\n")
        else:
            print(f"❌ Unknown command: {cmd}")
            print("💡 Type /help for available commands.\n")
        
        return True
    
    def chat(self, user_message: str) -> str:
        """Send message and get response."""
        self.messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.client.chat.completions.create(
                messages=self.messages,
                model="gpt-4"
            )
            
            assistant_message = response.choices[0].message.content
            self.messages.append({"role": "assistant", "content": assistant_message})
            
            return assistant_message
            
        except APIError as e:
            error_msg = f"API Error: {e}"
            # Remove failed user message
            self.messages.pop()
            return error_msg
    
    def run(self):
        """Run the interactive CLI loop."""
        print("🤖 GitHub Copilot Chat CLI")
        print("Type /help for commands or /quit to exit.\n")
        
        while self.running:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if self.handle_command(user_input):
                    continue
                
                # Regular chat
                print("Assistant: ", end="", flush=True)
                response = self.chat(user_input)
                print(response)
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!\n")
                break
            except EOFError:
                print("\n\n👋 Goodbye!\n")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}\n")

def main():
    cli = ChatCLI()
    cli.run()

if __name__ == "__main__":
    main()
```

**Run it:**

```bash
chmod +x chat_cli.py
./chat_cli.py
```

---

## Additional Resources

- **Official Docs:** https://github.com/github/copilot-sdk
- **API Reference:** https://docs.github.com/copilot/building-copilot-extensions
- **Examples Repo:** https://github.com/github/copilot-sdk-examples
- **Community:** https://github.com/orgs/github/discussions

## Tips

1. **Always handle errors** - Network failures, rate limits, and API errors are inevitable
2. **Stream for UX** - Streaming provides better user experience for long responses
3. **Use tools wisely** - Custom tools extend capabilities but add complexity
4. **Save context** - Persist conversations for better multi-session experiences
5. **Test with BYOK** - Validate your code works with different API providers
6. **Monitor costs** - Track token usage and implement limits for production apps

## License

Examples are provided under MIT License for educational purposes.
