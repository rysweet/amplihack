# GitHub Copilot SDK - Practical Examples

## Example 1: Hello World (All Languages)

### TypeScript

```typescript
import { CopilotClient } from "@github/copilot-sdk";

const client = new CopilotClient();
const session = await client.createSession({ model: "gpt-4.1" });

const response = await session.sendAndWait({ prompt: "What is 2 + 2?" });
console.log(response?.data.content);

await client.stop();
process.exit(0);
```

### Python

```python
import asyncio
from copilot import CopilotClient

async def main():
    client = CopilotClient()
    await client.start()

    session = await client.create_session({"model": "gpt-4.1"})
    response = await session.send_and_wait({"prompt": "What is 2 + 2?"})
    print(response.data.content)

    await client.stop()

asyncio.run(main())
```

### Go

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

	response, err := session.SendAndWait(copilot.MessageOptions{Prompt: "What is 2 + 2?"}, 0)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println(*response.Data.Content)
	os.Exit(0)
}
```

### .NET

```csharp
using GitHub.Copilot.SDK;

await using var client = new CopilotClient();
await using var session = await client.CreateSessionAsync(new SessionConfig { Model = "gpt-4.1" });

var response = await session.SendAndWaitAsync(new MessageOptions { Prompt = "What is 2 + 2?" });
Console.WriteLine(response?.Data.Content);
```

---

## Example 2: Streaming Responses

### TypeScript

```typescript
import { CopilotClient, SessionEvent } from "@github/copilot-sdk";

const client = new CopilotClient();
const session = await client.createSession({
  model: "gpt-4.1",
  streaming: true,
});

session.on((event: SessionEvent) => {
  if (event.type === "assistant.message_delta") {
    process.stdout.write(event.data.deltaContent);
  }
  if (event.type === "session.idle") {
    console.log();
  }
});

await session.sendAndWait({ prompt: "Tell me a short joke" });

await client.stop();
process.exit(0);
```

### Python

```python
import asyncio
import sys
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType

async def main():
    client = CopilotClient()
    await client.start()

    session = await client.create_session({
        "model": "gpt-4.1",
        "streaming": True,
    })

    def handle_event(event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            sys.stdout.write(event.data.delta_content)
            sys.stdout.flush()
        if event.type == SessionEventType.SESSION_IDLE:
            print()

    session.on(handle_event)

    await session.send_and_wait({"prompt": "Tell me a short joke"})

    await client.stop()

asyncio.run(main())
```

### Go

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

	session, err := client.CreateSession(&copilot.SessionConfig{
		Model:     "gpt-4.1",
		Streaming: true,
	})
	if err != nil {
		log.Fatal(err)
	}

	session.On(func(event copilot.SessionEvent) {
		if event.Type == "assistant.message_delta" {
			fmt.Print(*event.Data.DeltaContent)
		}
		if event.Type == "session.idle" {
			fmt.Println()
		}
	})

	_, err = session.SendAndWait(copilot.MessageOptions{Prompt: "Tell me a short joke"}, 0)
	if err != nil {
		log.Fatal(err)
	}
	os.Exit(0)
}
```

### .NET

```csharp
using GitHub.Copilot.SDK;

await using var client = new CopilotClient();
await using var session = await client.CreateSessionAsync(new SessionConfig
{
    Model = "gpt-4.1",
    Streaming = true,
});

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

await session.SendAndWaitAsync(new MessageOptions { Prompt = "Tell me a short joke" });
```

---

## Example 3: Custom Tool - Weather

### TypeScript

```typescript
import { CopilotClient, defineTool, SessionEvent } from "@github/copilot-sdk";

const getWeather = defineTool("get_weather", {
  description: "Get the current weather for a city",
  parameters: {
    type: "object",
    properties: {
      city: { type: "string", description: "The city name" },
    },
    required: ["city"],
  },
  handler: async ({ city }: { city: string }) => {
    const conditions = ["sunny", "cloudy", "rainy", "partly cloudy"];
    const temp = Math.floor(Math.random() * 30) + 50;
    const condition = conditions[Math.floor(Math.random() * conditions.length)];
    return { city, temperature: `${temp}°F`, condition };
  },
});

const client = new CopilotClient();
const session = await client.createSession({
  model: "gpt-4.1",
  streaming: true,
  tools: [getWeather],
});

session.on((event: SessionEvent) => {
  if (event.type === "assistant.message_delta") {
    process.stdout.write(event.data.deltaContent);
  }
});

await session.sendAndWait({
  prompt: "What's the weather like in Seattle and Tokyo?",
});

await client.stop();
process.exit(0);
```

### Python

```python
import asyncio
import random
import sys
from copilot import CopilotClient
from copilot.tools import define_tool
from copilot.generated.session_events import SessionEventType
from pydantic import BaseModel, Field

class GetWeatherParams(BaseModel):
    city: str = Field(description="The name of the city to get weather for")

@define_tool(description="Get the current weather for a city")
async def get_weather(params: GetWeatherParams) -> dict:
    conditions = ["sunny", "cloudy", "rainy", "partly cloudy"]
    temp = random.randint(50, 80)
    condition = random.choice(conditions)
    return {"city": params.city, "temperature": f"{temp}°F", "condition": condition}

async def main():
    client = CopilotClient()
    await client.start()

    session = await client.create_session({
        "model": "gpt-4.1",
        "streaming": True,
        "tools": [get_weather],
    })

    def handle_event(event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            sys.stdout.write(event.data.delta_content)
            sys.stdout.flush()

    session.on(handle_event)

    await session.send_and_wait({
        "prompt": "What's the weather like in Seattle and Tokyo?"
    })

    await client.stop()

asyncio.run(main())
```

### Go

```go
package main

import (
	"fmt"
	"log"
	"math/rand"
	"os"

	copilot "github.com/github/copilot-sdk/go"
)

type WeatherParams struct {
	City string `json:"city" jsonschema:"The city name"`
}

type WeatherResult struct {
	City        string `json:"city"`
	Temperature string `json:"temperature"`
	Condition   string `json:"condition"`
}

func main() {
	getWeather := copilot.DefineTool(
		"get_weather",
		"Get the current weather for a city",
		func(params WeatherParams, inv copilot.ToolInvocation) (WeatherResult, error) {
			conditions := []string{"sunny", "cloudy", "rainy", "partly cloudy"}
			temp := rand.Intn(30) + 50
			condition := conditions[rand.Intn(len(conditions))]
			return WeatherResult{
				City:        params.City,
				Temperature: fmt.Sprintf("%d°F", temp),
				Condition:   condition,
			}, nil
		},
	)

	client := copilot.NewClient(nil)
	if err := client.Start(); err != nil {
		log.Fatal(err)
	}
	defer client.Stop()

	session, err := client.CreateSession(&copilot.SessionConfig{
		Model:     "gpt-4.1",
		Streaming: true,
		Tools:     []copilot.Tool{getWeather},
	})
	if err != nil {
		log.Fatal(err)
	}

	session.On(func(event copilot.SessionEvent) {
		if event.Type == "assistant.message_delta" {
			fmt.Print(*event.Data.DeltaContent)
		}
	})

	_, err = session.SendAndWait(copilot.MessageOptions{
		Prompt: "What's the weather like in Seattle and Tokyo?",
	}, 0)
	if err != nil {
		log.Fatal(err)
	}
	os.Exit(0)
}
```

### .NET

```csharp
using GitHub.Copilot.SDK;
using Microsoft.Extensions.AI;
using System.ComponentModel;

await using var client = new CopilotClient();

var getWeather = AIFunctionFactory.Create(
    ([Description("The city name")] string city) =>
    {
        var conditions = new[] { "sunny", "cloudy", "rainy", "partly cloudy" };
        var temp = Random.Shared.Next(50, 80);
        var condition = conditions[Random.Shared.Next(conditions.Length)];
        return new { city, temperature = $"{temp}°F", condition };
    },
    "get_weather",
    "Get the current weather for a city"
);

await using var session = await client.CreateSessionAsync(new SessionConfig
{
    Model = "gpt-4.1",
    Streaming = true,
    Tools = [getWeather],
});

session.On(ev =>
{
    if (ev is AssistantMessageDeltaEvent deltaEvent)
    {
        Console.Write(deltaEvent.Data.DeltaContent);
    }
});

await session.SendAndWaitAsync(new MessageOptions
{
    Prompt = "What's the weather like in Seattle and Tokyo?",
});
```

---

## Example 4: Interactive CLI Assistant

### TypeScript

```typescript
import { CopilotClient, defineTool, SessionEvent } from "@github/copilot-sdk";
import * as readline from "readline";

const getWeather = defineTool("get_weather", {
  description: "Get the current weather for a city",
  parameters: {
    type: "object",
    properties: {
      city: { type: "string", description: "The city name" },
    },
    required: ["city"],
  },
  handler: async ({ city }) => {
    const conditions = ["sunny", "cloudy", "rainy"];
    const temp = Math.floor(Math.random() * 30) + 50;
    return { city, temperature: `${temp}°F`, condition: conditions[0] };
  },
});

const client = new CopilotClient();
const session = await client.createSession({
  model: "gpt-4.1",
  streaming: true,
  tools: [getWeather],
});

session.on((event: SessionEvent) => {
  if (event.type === "assistant.message_delta") {
    process.stdout.write(event.data.deltaContent);
  }
});

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

console.log("🌤️  Weather Assistant (type 'exit' to quit)");

const prompt = () => {
  rl.question("You: ", async (input) => {
    if (input.toLowerCase() === "exit") {
      await client.stop();
      rl.close();
      return;
    }
    process.stdout.write("Assistant: ");
    await session.sendAndWait({ prompt: input });
    console.log("\n");
    prompt();
  });
};

prompt();
```

---

## Example 5: Multiple Sessions

### TypeScript

```typescript
import { CopilotClient } from "@github/copilot-sdk";

const client = new CopilotClient();

// Create two independent sessions
const codeReviewSession = await client.createSession({
  model: "gpt-4.1",
  systemMessage: { content: "You are a code reviewer." },
});

const documentationSession = await client.createSession({
  model: "gpt-4.1",
  systemMessage: { content: "You are a documentation writer." },
});

// Use sessions independently
const review = await codeReviewSession.sendAndWait({
  prompt: "Review: function add(a,b){return a+b}",
});
console.log("Review:", review?.data.content);

const docs = await documentationSession.sendAndWait({
  prompt: "Document: function add(a,b){return a+b}",
});
console.log("Docs:", docs?.data.content);

await client.stop();
```

### Python

```python
import asyncio
from copilot import CopilotClient

async def main():
    client = CopilotClient()
    await client.start()

    # Create two independent sessions
    review_session = await client.create_session({
        "model": "gpt-4.1",
        "systemMessage": {"content": "You are a code reviewer."},
    })

    docs_session = await client.create_session({
        "model": "gpt-4.1",
        "systemMessage": {"content": "You are a documentation writer."},
    })

    # Use sessions independently
    review = await review_session.send_and_wait({
        "prompt": "Review: def add(a,b): return a+b",
    })
    print("Review:", review.data.content)

    docs = await docs_session.send_and_wait({
        "prompt": "Document: def add(a,b): return a+b",
    })
    print("Docs:", docs.data.content)

    await client.stop()

asyncio.run(main())
```

---

## Example 6: Custom System Message

### TypeScript

```typescript
import { CopilotClient } from "@github/copilot-sdk";

const client = new CopilotClient();
const session = await client.createSession({
  model: "gpt-4.1",
  systemMessage: {
    content: `You are a Python expert focused on writing clean, idiomatic code.
Always follow PEP 8 guidelines.
Include type hints and docstrings in all code examples.`,
  },
});

const response = await session.sendAndWait({
  prompt: "Write a function to calculate the nth Fibonacci number",
});
console.log(response?.data.content);

await client.stop();
```

---

## Example 7: Error Handling

### TypeScript

```typescript
import { CopilotClient } from "@github/copilot-sdk";

async function main() {
  const client = new CopilotClient();

  try {
    const session = await client.createSession({ model: "gpt-4.1" });

    const response = await session.sendAndWait({
      prompt: "Explain async/await in JavaScript",
    });

    console.log(response?.data.content);
  } catch (error: any) {
    if (error.code === "CONNECTION_ERROR") {
      console.error("Failed to connect to Copilot CLI. Is it installed?");
    } else if (error.code === "AUTHENTICATION_ERROR") {
      console.error("Not authenticated. Run: copilot auth login");
    } else {
      console.error("Error:", error.message);
    }
  } finally {
    await client.stop();
  }
}

main();
```

### Python

```python
import asyncio
from copilot import CopilotClient
from copilot.errors import ConnectionError, AuthenticationError

async def main():
    client = CopilotClient()

    try:
        await client.start()
        session = await client.create_session({"model": "gpt-4.1"})

        response = await session.send_and_wait({
            "prompt": "Explain async/await in Python"
        })
        print(response.data.content)

    except ConnectionError:
        print("Failed to connect to Copilot CLI. Is it installed?")
    except AuthenticationError:
        print("Not authenticated. Run: copilot auth login")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.stop()

asyncio.run(main())
```

---

## Example 8: MCP GitHub Integration

### TypeScript

```typescript
import { CopilotClient } from "@github/copilot-sdk";

const client = new CopilotClient();
const session = await client.createSession({
  model: "gpt-4.1",
  streaming: true,
  mcpServers: {
    github: {
      type: "http",
      url: "https://api.githubcopilot.com/mcp/",
    },
  },
});

session.on((event) => {
  if (event.type === "assistant.message_delta") {
    process.stdout.write(event.data.deltaContent);
  }
});

await session.sendAndWait({
  prompt: "List the open issues in the microsoft/TypeScript repository",
});

await client.stop();
```

---

## Example 9: Custom Agent Definition

### TypeScript

```typescript
import { CopilotClient } from "@github/copilot-sdk";

const client = new CopilotClient();
const session = await client.createSession({
  model: "gpt-4.1",
  customAgents: [
    {
      name: "security-reviewer",
      displayName: "Security Reviewer",
      description: "Reviews code for security vulnerabilities",
      prompt: `You are a security expert. When reviewing code:
1. Check for SQL injection vulnerabilities
2. Look for XSS possibilities
3. Identify authentication/authorization issues
4. Find hardcoded secrets
5. Rate severity: Critical, High, Medium, Low`,
    },
  ],
});

const response = await session.sendAndWait({
  prompt: `Review this code:
const query = "SELECT * FROM users WHERE id = " + userId;
db.query(query);`,
});

console.log(response?.data.content);
await client.stop();
```

---

## Example 10: External CLI Server Connection

### TypeScript

```typescript
// First, start CLI in server mode:
// $ copilot --server --port 4321

import { CopilotClient } from "@github/copilot-sdk";

// Connect to external server instead of managing CLI
const client = new CopilotClient({
  cliUrl: "localhost:4321",
});

const session = await client.createSession({ model: "gpt-4.1" });

const response = await session.sendAndWait({
  prompt: "What is the capital of France?",
});

console.log(response?.data.content);

await client.stop();
```

### Python

```python
# First, start CLI in server mode:
# $ copilot --server --port 4321

import asyncio
from copilot import CopilotClient

async def main():
    # Connect to external server
    client = CopilotClient({"cli_url": "localhost:4321"})
    await client.start()

    session = await client.create_session({"model": "gpt-4.1"})
    response = await session.send_and_wait({
        "prompt": "What is the capital of France?"
    })
    print(response.data.content)

    await client.stop()

asyncio.run(main())
```

### Go

```go
package main

import (
	"fmt"
	"log"

	copilot "github.com/github/copilot-sdk/go"
)

func main() {
	// Connect to external server
	client := copilot.NewClient(&copilot.ClientOptions{
		CLIUrl: "localhost:4321",
	})

	if err := client.Start(); err != nil {
		log.Fatal(err)
	}
	defer client.Stop()

	session, err := client.CreateSession(&copilot.SessionConfig{Model: "gpt-4.1"})
	if err != nil {
		log.Fatal(err)
	}

	response, err := session.SendAndWait(copilot.MessageOptions{
		Prompt: "What is the capital of France?",
	}, 0)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println(*response.Data.Content)
}
```

### .NET

```csharp
// First, start CLI in server mode:
// $ copilot --server --port 4321

using GitHub.Copilot.SDK;

await using var client = new CopilotClient(new CopilotClientOptions
{
    CliUrl = "localhost:4321"
});

await using var session = await client.CreateSessionAsync(
    new SessionConfig { Model = "gpt-4.1" }
);

var response = await session.SendAndWaitAsync(
    new MessageOptions { Prompt = "What is the capital of France?" }
);

Console.WriteLine(response?.Data.Content);
```

---

## Example Summary

| #   | Example           | Languages  | Key Concepts           |
| --- | ----------------- | ---------- | ---------------------- |
| 1   | Hello World       | All 4      | Basic send/receive     |
| 2   | Streaming         | All 4      | Real-time output       |
| 3   | Custom Tool       | All 4      | Tool definition        |
| 4   | Interactive CLI   | TS         | readline, conversation |
| 5   | Multiple Sessions | TS, Python | Session isolation      |
| 6   | System Message    | TS         | Persona customization  |
| 7   | Error Handling    | TS, Python | Try/catch patterns     |
| 8   | MCP GitHub        | TS         | MCP integration        |
| 9   | Custom Agent      | TS         | Agent definition       |
| 10  | External Server   | All 4      | CLI server mode        |
