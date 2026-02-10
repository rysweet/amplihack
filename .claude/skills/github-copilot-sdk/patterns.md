# GitHub Copilot SDK - Production Patterns

## Pattern 1: Streaming UI Integration

Real-time response display for better user experience.

### Problem

Users experience long wait times before seeing any output when responses are large.

### Solution

Enable streaming and display chunks as they arrive.

```typescript
import { CopilotClient, SessionEvent } from "@github/copilot-sdk";

class StreamingUI {
  private outputBuffer: string = "";

  async run(prompt: string) {
    const client = new CopilotClient();
    const session = await client.createSession({
      model: "gpt-4.1",
      streaming: true,
    });

    // Handle streaming events
    session.on((event: SessionEvent) => {
      if (event.type === "assistant.message_delta") {
        const chunk = event.data.deltaContent;
        this.outputBuffer += chunk;
        this.renderChunk(chunk);
      }
      if (event.type === "session.idle") {
        this.onComplete(this.outputBuffer);
      }
    });

    await session.sendAndWait({ prompt });
    await client.stop();
  }

  private renderChunk(chunk: string) {
    // Append to UI element
    process.stdout.write(chunk);
  }

  private onComplete(fullResponse: string) {
    // Handle complete response
    console.log("\n[Complete]");
  }
}
```

### When to Use

- Interactive CLI applications
- Web chat interfaces
- Real-time documentation generation
- Code explanation tools

---

## Pattern 2: Tool Chaining

Compose multiple tools for complex workflows.

### Problem

Complex tasks require multiple steps with intermediate results.

### Solution

Define tools that work together, letting Copilot orchestrate.

```typescript
import { CopilotClient, defineTool } from "@github/copilot-sdk";

// Tool 1: Search for files
const searchFiles = defineTool("search_files", {
  description: "Search for files matching a pattern",
  parameters: {
    type: "object",
    properties: {
      pattern: { type: "string" },
      directory: { type: "string" },
    },
    required: ["pattern"],
  },
  handler: async ({ pattern, directory = "." }) => {
    // Implementation
    return { files: ["file1.ts", "file2.ts"] };
  },
});

// Tool 2: Read file content
const readFile = defineTool("read_file", {
  description: "Read the content of a file",
  parameters: {
    type: "object",
    properties: {
      path: { type: "string" },
    },
    required: ["path"],
  },
  handler: async ({ path }) => {
    // Implementation
    return { content: "file contents..." };
  },
});

// Tool 3: Analyze code
const analyzeCode = defineTool("analyze_code", {
  description: "Analyze code for patterns or issues",
  parameters: {
    type: "object",
    properties: {
      code: { type: "string" },
      analysisType: { type: "string" },
    },
    required: ["code", "analysisType"],
  },
  handler: async ({ code, analysisType }) => {
    // Implementation
    return { findings: ["finding1", "finding2"] };
  },
});

// Copilot chains tools automatically
const session = await client.createSession({
  model: "gpt-4.1",
  tools: [searchFiles, readFile, analyzeCode],
});

await session.sendAndWait({
  prompt: "Find all TypeScript files and analyze them for security issues",
});
```

### When to Use

- Code analysis workflows
- Data processing pipelines
- Multi-step automation tasks

---

## Pattern 3: Session Isolation

Keep contexts separate for different concerns.

### Problem

Different tasks contaminate each other's context.

### Solution

Use separate sessions for independent workflows.

```typescript
import { CopilotClient } from "@github/copilot-sdk";

class SessionManager {
  private client: CopilotClient;
  private sessions: Map<string, any> = new Map();

  constructor() {
    this.client = new CopilotClient();
  }

  async getSession(purpose: string, config?: any) {
    if (!this.sessions.has(purpose)) {
      const session = await this.client.createSession({
        model: "gpt-4.1",
        ...config,
      });
      this.sessions.set(purpose, session);
    }
    return this.sessions.get(purpose);
  }

  async execute(purpose: string, prompt: string) {
    const session = await this.getSession(purpose);
    return await session.sendAndWait({ prompt });
  }
}

// Usage
const manager = new SessionManager();

// Different sessions for different tasks
await manager.execute("code-review", "Review this function...");
await manager.execute("documentation", "Document this API...");
await manager.execute("testing", "Generate tests for...");
```

### When to Use

- Multi-tenant applications
- Different personas/roles
- Parallel independent tasks
- Context isolation requirements

---

## Pattern 4: Retry with Backoff

Handle transient failures gracefully.

### Problem

Network issues or rate limits cause occasional failures.

### Solution

Implement exponential backoff retry logic.

```typescript
import { CopilotClient } from "@github/copilot-sdk";

async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error;

      // Don't retry on authentication errors
      if (error.code === "AUTHENTICATION_ERROR") {
        throw error;
      }

      // Exponential backoff
      const delay = baseDelay * Math.pow(2, attempt);
      console.log(`Retry ${attempt + 1}/${maxRetries} in ${delay}ms`);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}

// Usage
const response = await withRetry(async () => {
  const session = await client.createSession({ model: "gpt-4.1" });
  return await session.sendAndWait({ prompt: "Hello" });
});
```

### When to Use

- Production applications
- High-availability requirements
- Network-unreliable environments

---

## Pattern 5: Tool Result Validation

Verify tool outputs before returning to model.

### Problem

Tool errors can confuse the model or cause cascading failures.

### Solution

Validate and sanitize tool results.

```typescript
import { defineTool } from "@github/copilot-sdk";

interface ToolResult<T> {
  success: boolean;
  data?: T;
  error?: string;
}

function createValidatedTool<TInput, TOutput>(
  name: string,
  description: string,
  schema: any,
  handler: (input: TInput) => Promise<TOutput>,
  validator: (output: TOutput) => boolean
) {
  return defineTool(name, {
    description,
    parameters: schema,
    handler: async (input: TInput): Promise<ToolResult<TOutput>> => {
      try {
        const result = await handler(input);

        if (!validator(result)) {
          return {
            success: false,
            error: "Output validation failed",
          };
        }

        return {
          success: true,
          data: result,
        };
      } catch (error: any) {
        return {
          success: false,
          error: error.message,
        };
      }
    },
  });
}

// Usage
const apiTool = createValidatedTool(
  "fetch_user",
  "Fetch user data from API",
  {
    type: "object",
    properties: { userId: { type: "string" } },
    required: ["userId"],
  },
  async ({ userId }) => {
    const response = await fetch(`/api/users/${userId}`);
    return response.json();
  },
  (user) => user && typeof user.id === "string"
);
```

### When to Use

- External API integrations
- Database operations
- File system operations
- Any tool with unreliable output

---

## Pattern 6: Conversation History Management

Maintain context across multiple exchanges.

### Problem

Long conversations exceed context limits or lose focus.

### Solution

Manage conversation history with summarization.

```typescript
import { CopilotClient } from "@github/copilot-sdk";

class ConversationManager {
  private history: Array<{ role: string; content: string }> = [];
  private maxHistoryLength = 10;
  private client: CopilotClient;
  private session: any;

  async init() {
    this.client = new CopilotClient();
    this.session = await this.client.createSession({ model: "gpt-4.1" });
  }

  async send(userMessage: string): Promise<string> {
    // Add user message to history
    this.history.push({ role: "user", content: userMessage });

    // Trim history if too long
    if (this.history.length > this.maxHistoryLength) {
      await this.summarizeHistory();
    }

    // Build context from history
    const context = this.history.map((m) => `${m.role}: ${m.content}`).join("\n");

    const response = await this.session.sendAndWait({
      prompt: `Previous conversation:\n${context}\n\nUser: ${userMessage}`,
    });

    const assistantMessage = response?.data.content || "";
    this.history.push({ role: "assistant", content: assistantMessage });

    return assistantMessage;
  }

  private async summarizeHistory() {
    // Keep last 2 messages, summarize the rest
    const toSummarize = this.history.slice(0, -2);
    const toKeep = this.history.slice(-2);

    const summary = await this.session.sendAndWait({
      prompt: `Summarize this conversation in 2-3 sentences:\n${toSummarize
        .map((m) => `${m.role}: ${m.content}`)
        .join("\n")}`,
    });

    this.history = [
      { role: "system", content: `Previous context: ${summary?.data.content}` },
      ...toKeep,
    ];
  }
}
```

### When to Use

- Long-running chat sessions
- Complex multi-step workflows
- Context-limited models

---

## Pattern 7: MCP Server Composition

Combine multiple MCP servers for rich capabilities.

### Problem

Single MCP server has limited capabilities.

### Solution

Connect multiple MCP servers for comprehensive tool access.

```typescript
import { CopilotClient } from "@github/copilot-sdk";

const session = await client.createSession({
  model: "gpt-4.1",
  mcpServers: {
    // GitHub repository access
    github: {
      type: "http",
      url: "https://api.githubcopilot.com/mcp/",
    },
    // Local filesystem access
    filesystem: {
      type: "stdio",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-filesystem", "./workspace"],
    },
    // Database access (example)
    database: {
      type: "stdio",
      command: "npx",
      args: ["-y", "mcp-server-sqlite", "./data.db"],
      env: {
        DB_READ_ONLY: "true",
      },
    },
  },
});

// Copilot can now use tools from all servers
await session.sendAndWait({
  prompt:
    "Find open issues in my repo, check related files, and query the database for linked tickets",
});
```

### When to Use

- Complex automation workflows
- Cross-system integrations
- Development environment tools

---

## Pattern 8: Graceful Degradation

Handle capability failures without breaking the application.

### Problem

Tool failures or missing capabilities shouldn't crash the app.

### Solution

Implement fallback behaviors and error boundaries.

```typescript
import { CopilotClient, defineTool } from "@github/copilot-sdk";

// Primary tool with fallback
const fetchDataTool = defineTool("fetch_data", {
  description: "Fetch data from API with caching fallback",
  parameters: {
    type: "object",
    properties: { id: { type: "string" } },
    required: ["id"],
  },
  handler: async ({ id }) => {
    try {
      // Try primary API
      const response = await fetch(`https://api.example.com/data/${id}`);
      if (!response.ok) throw new Error("API failed");
      return await response.json();
    } catch (primaryError) {
      try {
        // Try cache
        return await getFromCache(id);
      } catch (cacheError) {
        // Return graceful error
        return {
          error: true,
          message: `Data unavailable for ${id}`,
          suggestion: "Try again later or use a different ID",
        };
      }
    }
  },
});

// Session with graceful error handling
async function safeQuery(prompt: string) {
  const client = new CopilotClient();

  try {
    const session = await client.createSession({
      model: "gpt-4.1",
      tools: [fetchDataTool],
    });

    return await session.sendAndWait({ prompt });
  } catch (error: any) {
    // Return useful error instead of crashing
    return {
      success: false,
      error: error.message,
      fallbackResponse: "I'm unable to complete this request. Please try again.",
    };
  } finally {
    await client.stop();
  }
}
```

### When to Use

- Production applications
- User-facing interfaces
- Unreliable external services

---

## Pattern 9: Rate Limiting

Control request frequency to avoid quota exhaustion.

### Problem

High request volume exceeds API limits.

### Solution

Implement token bucket or sliding window rate limiting.

```typescript
class RateLimiter {
  private tokens: number;
  private maxTokens: number;
  private refillRate: number;
  private lastRefill: number;

  constructor(maxTokens: number, refillPerSecond: number) {
    this.tokens = maxTokens;
    this.maxTokens = maxTokens;
    this.refillRate = refillPerSecond;
    this.lastRefill = Date.now();
  }

  async acquire(): Promise<void> {
    this.refill();

    if (this.tokens < 1) {
      const waitTime = ((1 - this.tokens) / this.refillRate) * 1000;
      await new Promise((resolve) => setTimeout(resolve, waitTime));
      this.refill();
    }

    this.tokens -= 1;
  }

  private refill() {
    const now = Date.now();
    const elapsed = (now - this.lastRefill) / 1000;
    this.tokens = Math.min(this.maxTokens, this.tokens + elapsed * this.refillRate);
    this.lastRefill = now;
  }
}

// Usage with Copilot SDK
const limiter = new RateLimiter(10, 1); // 10 requests, 1 per second refill

async function rateLimitedQuery(prompt: string) {
  await limiter.acquire();
  return await session.sendAndWait({ prompt });
}
```

### When to Use

- Shared API quotas
- Multi-user applications
- Cost control

---

## Pattern 10: Structured Output Extraction

Get structured data from model responses.

### Problem

Need structured data but model returns prose.

### Solution

Use tools to enforce output structure.

```typescript
import { defineTool } from "@github/copilot-sdk";

// Tool that enforces structured output
const extractEntities = defineTool("extract_entities", {
  description: "Return the analysis result as structured data",
  parameters: {
    type: "object",
    properties: {
      entities: {
        type: "array",
        items: {
          type: "object",
          properties: {
            name: { type: "string" },
            type: { type: "string" },
            confidence: { type: "number" },
          },
        },
      },
      summary: { type: "string" },
    },
    required: ["entities", "summary"],
  },
  handler: async (data) => data, // Just return the structured data
});

// Force model to use the tool
const session = await client.createSession({
  model: "gpt-4.1",
  tools: [extractEntities],
  systemMessage: {
    content: "Always use the extract_entities tool to return your analysis results.",
  },
});

const response = await session.sendAndWait({
  prompt: "Analyze this text and identify all people, places, and organizations: ...",
});
```

### When to Use

- Data extraction pipelines
- API response generation
- Form filling automation

---

## Anti-Patterns to Avoid

### 1. Ignoring Cleanup

**Bad:**

```typescript
const client = new CopilotClient();
const session = await client.createSession({ model: "gpt-4.1" });
// No cleanup - resource leak!
```

**Good:**

```typescript
const client = new CopilotClient();
try {
  const session = await client.createSession({ model: "gpt-4.1" });
  // Use session
} finally {
  await client.stop();
}
```

### 2. Blocking on Streaming

**Bad:**

```typescript
// Waiting for full response while streaming
const response = await session.sendAndWait({ prompt: "..." });
// No streaming handler - defeats purpose
```

**Good:**

```typescript
session.on((event) => {
  if (event.type === "assistant.message_delta") {
    displayChunk(event.data.deltaContent);
  }
});
await session.sendAndWait({ prompt: "..." });
```

### 3. Unbounded Tool Execution

**Bad:**

```typescript
const dangerousTool = defineTool("execute", {
  handler: async ({ command }) => {
    return execSync(command).toString(); // Dangerous!
  },
});
```

**Good:**

```typescript
const safeTool = defineTool("execute", {
  handler: async ({ command }) => {
    if (!ALLOWED_COMMANDS.includes(command)) {
      throw new Error("Command not allowed");
    }
    return execSync(command).toString();
  },
});
```

---

## Summary

| Pattern              | Use Case           | Key Benefit          |
| -------------------- | ------------------ | -------------------- |
| Streaming UI         | Chat interfaces    | Real-time UX         |
| Tool Chaining        | Complex workflows  | Automation           |
| Session Isolation    | Multi-tenant       | Context safety       |
| Retry with Backoff   | Production         | Reliability          |
| Tool Validation      | External APIs      | Error handling       |
| History Management   | Long conversations | Context control      |
| MCP Composition      | Rich integrations  | Capability expansion |
| Graceful Degradation | User-facing apps   | Resilience           |
| Rate Limiting        | Shared resources   | Cost control         |
| Structured Output    | Data pipelines     | Type safety          |
