# Agents - Deep Dive

## Agent Anatomy

An agent in Microsoft Agent Framework is a stateful conversational entity that combines:

- **Model client**: Connection to an LLM
- **Instructions**: System prompt defining behavior
- **Tools**: Functions the agent can call
- **Context**: Conversation history and state
- **Middleware**: Request/response interceptors

## Creating Agents

### Basic Agent

```python
from agents_framework import Agent, ModelClient

agent = Agent(
    name="assistant",                    # Agent identifier
    model=ModelClient(model="gpt-4"),    # LLM connection
    instructions="You are helpful"       # System prompt
)
```

### Agent with Configuration

```python
agent = Agent(
    name="code_reviewer",
    model=ModelClient(
        model="gpt-4-turbo",
        temperature=0.7,
        max_tokens=2000,
        timeout=60.0
    ),
    instructions="""You are a code reviewer. Focus on:
    - Code correctness and bugs
    - Performance issues
    - Security vulnerabilities
    - Best practices
    Provide actionable feedback.""",
    tools=[analyze_code, suggest_fix],
    parallel_tool_calls=True,            # Call multiple tools concurrently
    response_format=ReviewReport         # Structured output
)
```

### C# Agent

```csharp
using Microsoft.Agents.AI;

var agent = new Agent(
    name: "assistant",
    model: new ModelClient(
        model: "gpt-4",
        temperature: 0.7,
        maxTokens: 2000
    ),
    instructions: "You are a helpful assistant",
    tools: new[] { analyzeTool, suggestTool },
    parallelToolCalls: true
);
```

## Agent Lifecycle

### 1. Initialization

```python
# Agent created with configuration
agent = Agent(name="agent", model=model, instructions="...")

# Initialization happens once
# Tools are registered, middleware is set up
```

### 2. Message Processing

```python
# Single-turn conversation
response = await agent.run(message="Hello")

# Multi-turn with thread
thread = Thread()
response1 = await agent.run(thread=thread, message="First message")
response2 = await agent.run(thread=thread, message="Follow-up")
```

**Processing Flow**:

1. Message arrives → middleware preprocessing
2. Thread retrieves conversation history
3. Context providers inject additional context
4. Model processes message + history + context
5. If tool calls needed → execute tools → back to step 4
6. Generate response → middleware postprocessing
7. Update thread with new messages

### 3. Tool Execution

```python
@function_tool
def get_data(query: str) -> dict:
    return {"result": "data"}

agent = Agent(model=model, tools=[get_data])

# Agent automatically decides when to call tools
response = await agent.run(message="Get data for X")
# Internally: agent calls get_data("X") → processes result → responds
```

### 4. State Management

```python
from agents_framework import Thread

thread = Thread()

# Each run updates thread state
await agent.run(thread=thread, message="My name is Alice")
await agent.run(thread=thread, message="What's my name?")
# Agent remembers: "Your name is Alice"

# Access thread history
for message in thread.messages:
    print(f"{message.role}: {message.content}")
```

## Advanced Agent Features

### Structured Outputs

Force agent to return data in a specific format:

```python
from pydantic import BaseModel

class TaskBreakdown(BaseModel):
    tasks: list[str]
    priority: str
    estimated_hours: float

agent = Agent(
    model=model,
    instructions="Break down projects into tasks",
    response_format=TaskBreakdown
)

response = await agent.run(message="Plan website redesign")
breakdown: TaskBreakdown = response.parsed

print(breakdown.tasks)
print(f"Priority: {breakdown.priority}")
print(f"Est. hours: {breakdown.estimated_hours}")
```

**C# Example**:

```csharp
public class TaskBreakdown
{
    public List<string> Tasks { get; set; }
    public string Priority { get; set; }
    public double EstimatedHours { get; set; }
}

var agent = new Agent(
    model: model,
    instructions: "Break down projects into tasks",
    responseFormat: typeof(TaskBreakdown)
);

var response = await agent.RunAsync("Plan website redesign");
var breakdown = response.Parsed<TaskBreakdown>();
```

### Parallel Tool Calls

Allow agent to call multiple tools simultaneously:

```python
@function_tool
def get_weather(location: str) -> str:
    return f"Weather in {location}: Sunny"

@function_tool
def get_time(timezone: str) -> str:
    return f"Time in {timezone}: 3:00 PM"

agent = Agent(
    model=model,
    tools=[get_weather, get_time],
    parallel_tool_calls=True  # Enable parallel execution
)

# Agent can call both tools at once
response = await agent.run(message="What's the weather and time in Seattle?")
# Internally: get_weather("Seattle") and get_time("America/Los_Angeles") run concurrently
```

### Streaming Responses

Stream agent responses as they're generated:

```python
thread = Thread()

async for chunk in agent.run_stream(thread=thread, message="Explain quantum computing"):
    print(chunk.delta, end="", flush=True)
    # Prints response incrementally
```

**C# Example**:

```csharp
await foreach (var chunk in agent.RunStreamAsync(thread, "Explain quantum computing"))
{
    Console.Write(chunk.Delta);
}
```

### Token Usage Tracking

Monitor token consumption:

```python
response = await agent.run(message="Hello")

print(f"Prompt tokens: {response.usage.prompt_tokens}")
print(f"Completion tokens: {response.usage.completion_tokens}")
print(f"Total tokens: {response.usage.total_tokens}")
```

### Temperature & Sampling Control

```python
# Low temperature for deterministic outputs
code_agent = Agent(
    model=ModelClient(model="gpt-4", temperature=0.1),
    instructions="Generate code"
)

# Higher temperature for creative outputs
creative_agent = Agent(
    model=ModelClient(model="gpt-4", temperature=0.9),
    instructions="Write stories"
)
```

### Max Tokens & Truncation

```python
agent = Agent(
    model=ModelClient(
        model="gpt-4",
        max_tokens=500  # Limit response length
    ),
    instructions="Be concise"
)
```

### Stop Sequences

```python
agent = Agent(
    model=ModelClient(
        model="gpt-4",
        stop=["END", "DONE"]  # Stop generation at these sequences
    ),
    instructions="Generate text until END"
)
```

## Agent Patterns

### Chain-of-Thought Agents

```python
agent = Agent(
    model=model,
    instructions="""Think step-by-step:
    1. Understand the problem
    2. Break down into sub-problems
    3. Solve each sub-problem
    4. Synthesize solution

    Show your reasoning at each step."""
)
```

### Specialized Agents

```python
# Research agent
researcher = Agent(
    model=model,
    instructions="Research topics thoroughly. Cite sources.",
    tools=[search_web, fetch_article]
)

# Writing agent
writer = Agent(
    model=model,
    instructions="Write clear, engaging content based on research.",
    tools=[check_grammar, suggest_synonyms]
)

# Review agent
reviewer = Agent(
    model=model,
    instructions="Review content for accuracy and clarity.",
    tools=[fact_check, readability_score]
)
```

### Persona-Based Agents

```python
expert_agent = Agent(
    model=model,
    instructions="""You are Dr. Smith, a senior software architect with 20 years experience.
    You provide detailed technical advice, reference design patterns, and consider scalability."""
)

beginner_agent = Agent(
    model=model,
    instructions="""You are a friendly tutor. Use simple language, provide examples,
    and encourage learning. Avoid jargon."""
)
```

### Error-Handling Agents

```python
from agents_framework import RetryPolicy, ErrorHandler

agent = Agent(
    model=model,
    retry_policy=RetryPolicy(
        max_retries=3,
        backoff_factor=2.0,
        exceptions=[TimeoutError, ConnectionError]
    ),
    error_handler=ErrorHandler(
        fallback_response="I'm having trouble right now. Please try again.",
        log_errors=True
    )
)
```

## Agent Communication

### Agent-to-Agent Messages

```python
# Agent 1 generates message for Agent 2
response1 = await agent1.run(message="Research AI trends")

# Pass to Agent 2
response2 = await agent2.run(message=f"Summarize this: {response1.content}")
```

### Shared Thread

```python
thread = Thread()

# Multiple agents share conversation history
await agent1.run(thread=thread, message="Hello")
await agent2.run(thread=thread, message="Continue the conversation")
# agent2 sees agent1's message in history
```

### Agent Handoff

```python
async def handoff_flow():
    thread = Thread()

    # Start with classifier agent
    classification = await classifier.run(
        thread=thread,
        message="User query here"
    )

    # Route to appropriate specialist
    if "technical" in classification.content.lower():
        return await technical_agent.run(thread=thread, message="Handle this")
    else:
        return await general_agent.run(thread=thread, message="Handle this")
```

## Best Practices

1. **Clear Instructions**: Write specific, actionable system prompts
2. **Tool Naming**: Use descriptive function names and docstrings
3. **Thread Management**: Reuse threads for related conversations, create new threads for new topics
4. **Error Handling**: Always implement retry policies for production agents
5. **Token Limits**: Monitor usage and set max_tokens to prevent runaway costs
6. **Streaming**: Use streaming for long-form responses to improve UX
7. **Structured Outputs**: Use Pydantic models for consistent data parsing
8. **Testing**: Test agents with diverse inputs to ensure reliability

## Debugging Agents

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Run agent
response = await agent.run(message="Test")

# Inspect response
print(f"Model: {response.model}")
print(f"Role: {response.role}")
print(f"Content: {response.content}")
print(f"Tool calls: {response.tool_calls}")
print(f"Usage: {response.usage}")
```

## Performance Optimization

1. **Parallel Tool Calls**: Enable for independent operations
2. **Caching**: Cache tool results for repeated queries
3. **Model Selection**: Use smaller models for simple tasks
4. **Token Efficiency**: Prune conversation history to reduce context
5. **Batch Processing**: Process multiple messages concurrently

```python
# Batch process
messages = ["Query 1", "Query 2", "Query 3"]

responses = await asyncio.gather(*[
    agent.run(message=msg) for msg in messages
])
```
