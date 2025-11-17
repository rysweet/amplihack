# Tools & Functions - Extending Agent Capabilities

## Overview

Tools allow agents to perform actions beyond text generation. They enable agents to:

- Call external APIs
- Query databases
- Perform calculations
- Access file systems
- Execute code
- Interact with user interfaces

## Defining Tools

### Python Function Tools

Use the `@function_tool` decorator to convert Python functions into agent tools:

```python
from agents_framework import function_tool

@function_tool
def get_weather(location: str, units: str = "fahrenheit") -> str:
    """
    Get current weather for a location.

    Args:
        location: City name or zip code
        units: Temperature units (fahrenheit or celsius)

    Returns:
        Weather description string
    """
    # Implementation here
    return f"Weather in {location}: Sunny, 72°{units[0].upper()}"

# Use in agent
agent = Agent(model=model, tools=[get_weather])
```

**Key Requirements**:

- **Type hints**: Required for all parameters and return values
- **Docstring**: Describes the function's purpose (agent uses this to decide when to call)
- **Clear naming**: Function name should describe the action

### C# Function Tools

```csharp
using Microsoft.Agents.AI;

public class WeatherTools
{
    [FunctionTool(Description = "Get current weather for a location")]
    public static string GetWeather(
        [Parameter(Description = "City name or zip code")] string location,
        [Parameter(Description = "Temperature units")] string units = "fahrenheit")
    {
        return $"Weather in {location}: Sunny, 72°{units[0]}";
    }
}

// Use in agent
var agent = new Agent(
    model: model,
    tools: new[] { typeof(WeatherTools).GetMethod("GetWeather") }
);
```

### Async Tools

For I/O-bound operations:

```python
@function_tool
async def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

### Tools with Complex Types

Use Pydantic models for structured inputs/outputs:

```python
from pydantic import BaseModel

class SearchQuery(BaseModel):
    query: str
    max_results: int = 10
    filters: dict = {}

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

@function_tool
def search_documents(query: SearchQuery) -> list[SearchResult]:
    """Search internal documents."""
    results = perform_search(query.query, query.max_results, query.filters)
    return [SearchResult(**r) for r in results]
```

## Tool Usage Patterns

### Automatic Tool Calling

Agent decides when to use tools based on user message:

```python
agent = Agent(
    model=model,
    instructions="You are a helpful assistant with access to tools",
    tools=[get_weather, search_web, calculate]
)

# Agent automatically calls appropriate tool
response = await agent.run(message="What's the weather in Seattle?")
# Internally: agent calls get_weather("Seattle") → generates response
```

### Forced Tool Calling

Require agent to use a specific tool:

```python
response = await agent.run(
    message="Get weather",
    tool_choice={"type": "function", "function": {"name": "get_weather"}}
)
```

### Tool Call Inspection

See which tools were called:

```python
response = await agent.run(message="What's 23 * 45 and the weather in NYC?")

for tool_call in response.tool_calls:
    print(f"Called: {tool_call.function.name}")
    print(f"Arguments: {tool_call.function.arguments}")
    print(f"Result: {tool_call.result}")
```

### Parallel Tool Calls

Execute multiple tools concurrently:

```python
agent = Agent(
    model=model,
    tools=[get_weather, get_news, get_stock_price],
    parallel_tool_calls=True  # Enable parallel execution
)

# Agent can call multiple tools at once
response = await agent.run(
    message="What's the weather, news, and AAPL stock price?"
)
# get_weather(), get_news(), get_stock_price() all run concurrently
```

## Advanced Tool Features

### Tool Authorization

Control which tools can be called:

```python
from agents_framework import ToolAuthorizer

class CustomAuthorizer(ToolAuthorizer):
    def authorize(self, tool_name: str, arguments: dict) -> bool:
        # Only allow weather lookups for specific cities
        if tool_name == "get_weather":
            allowed_cities = ["Seattle", "Portland", "San Francisco"]
            return arguments.get("location") in allowed_cities
        return True

agent = Agent(
    model=model,
    tools=[get_weather],
    tool_authorizer=CustomAuthorizer()
)
```

### Human-in-the-Loop Approval

Require human approval for sensitive operations:

```python
from agents_framework import HumanApproval

@function_tool
def delete_file(path: str) -> str:
    """Delete a file from the filesystem."""
    os.remove(path)
    return f"Deleted {path}"

# Wrap tool with approval workflow
delete_with_approval = HumanApproval(
    tool=delete_file,
    approval_prompt="Approve deletion of {path}?",
    require_reason=True
)

agent = Agent(model=model, tools=[delete_with_approval])

# Agent calls tool → user prompted → approval → execution
response = await agent.run(message="Delete old logs")
```

**C# Example**:

```csharp
var deleteWithApproval = new HumanApproval(
    tool: deleteFile,
    approvalPrompt: "Approve deletion of {path}?",
    requireReason: true
);
```

### Tool Error Handling

Handle tool failures gracefully:

```python
@function_tool
def risky_operation(param: str) -> str:
    """Operation that might fail."""
    try:
        result = perform_operation(param)
        return f"Success: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

# Agent configuration
agent = Agent(
    model=model,
    tools=[risky_operation],
    tool_error_handler=lambda error: f"Tool failed: {error}",
    retry_failed_tools=True,
    max_tool_retries=3
)
```

### Tool Timeouts

Set execution time limits:

```python
from agents_framework import ToolConfig

@function_tool
async def slow_operation(query: str) -> str:
    """Long-running operation."""
    await asyncio.sleep(10)
    return "Result"

agent = Agent(
    model=model,
    tools=[slow_operation],
    tool_config=ToolConfig(
        timeout=5.0,  # 5 second timeout
        on_timeout="return_error"  # or "retry"
    )
)
```

### Tool Rate Limiting

Prevent excessive tool calls:

```python
from agents_framework import RateLimiter

rate_limiter = RateLimiter(
    max_calls_per_minute=10,
    max_calls_per_hour=100
)

@function_tool
def api_call(endpoint: str) -> str:
    """Call external API."""
    rate_limiter.check()  # Raises exception if limit exceeded
    return call_api(endpoint)
```

## Tool Categories

### Data Retrieval Tools

```python
@function_tool
def query_database(sql: str) -> list[dict]:
    """Execute SQL query and return results."""
    conn = get_db_connection()
    cursor = conn.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@function_tool
def fetch_document(doc_id: str) -> str:
    """Retrieve document by ID."""
    return document_store.get(doc_id)

@function_tool
def search_knowledge_base(query: str, top_k: int = 5) -> list[dict]:
    """Semantic search over knowledge base."""
    embeddings = get_embeddings(query)
    results = vector_store.search(embeddings, top_k)
    return results
```

### Computation Tools

```python
@function_tool
def calculate(expression: str) -> float:
    """Evaluate mathematical expression."""
    return eval(expression, {"__builtins__": {}})  # Safe eval

@function_tool
def analyze_data(data: list[float]) -> dict:
    """Compute statistics on numerical data."""
    return {
        "mean": statistics.mean(data),
        "median": statistics.median(data),
        "stdev": statistics.stdev(data)
    }
```

### External Integration Tools

```python
@function_tool
async def send_email(to: str, subject: str, body: str) -> str:
    """Send email via SMTP."""
    # Email sending logic
    return f"Email sent to {to}"

@function_tool
async def create_ticket(title: str, description: str, priority: str) -> str:
    """Create support ticket in Jira."""
    ticket = jira_client.create_issue(
        project="SUPPORT",
        summary=title,
        description=description,
        priority=priority
    )
    return f"Created ticket {ticket.key}"

@function_tool
async def post_to_slack(channel: str, message: str) -> str:
    """Post message to Slack channel."""
    slack_client.chat_postMessage(channel=channel, text=message)
    return "Posted to Slack"
```

### File System Tools

```python
@function_tool
def read_file(path: str) -> str:
    """Read file contents."""
    with open(path, 'r') as f:
        return f.read()

@function_tool
def write_file(path: str, content: str) -> str:
    """Write content to file."""
    with open(path, 'w') as f:
        f.write(content)
    return f"Wrote {len(content)} bytes to {path}"

@function_tool
def list_directory(path: str) -> list[str]:
    """List files in directory."""
    return os.listdir(path)
```

### Code Execution Tools

```python
@function_tool
def run_python_code(code: str) -> str:
    """Execute Python code in sandboxed environment."""
    # Use safe execution environment
    result = exec_sandbox(code)
    return str(result)

@function_tool
def run_shell_command(command: str) -> str:
    """Execute shell command (requires approval)."""
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.stdout
```

## Tool Design Best Practices

### 1. Clear, Descriptive Names

```python
# Good
@function_tool
def get_customer_order_history(customer_id: str) -> list[dict]:
    """Retrieve all orders for a customer."""
    pass

# Bad
@function_tool
def get_data(id: str) -> list:
    """Get data."""
    pass
```

### 2. Comprehensive Docstrings

```python
@function_tool
def search_products(
    query: str,
    category: str = None,
    min_price: float = None,
    max_price: float = None,
    in_stock_only: bool = True
) -> list[dict]:
    """
    Search product catalog with filters.

    This function searches the product database and returns matching items.
    Results are sorted by relevance.

    Args:
        query: Search terms (product name, description, tags)
        category: Filter by category (e.g., "electronics", "clothing")
        min_price: Minimum price filter (inclusive)
        max_price: Maximum price filter (inclusive)
        in_stock_only: Only return products with inventory > 0

    Returns:
        List of product dictionaries with keys:
        - id: Product ID
        - name: Product name
        - price: Current price
        - stock: Inventory count
        - category: Product category
    """
    pass
```

### 3. Type Safety

```python
from typing import Literal

@function_tool
def set_thermostat(
    temperature: float,
    mode: Literal["heat", "cool", "auto"],
    fan: Literal["on", "auto"] = "auto"
) -> str:
    """Control thermostat settings."""
    pass
```

### 4. Error Messages

```python
@function_tool
def get_user_profile(user_id: str) -> dict:
    """Retrieve user profile."""
    if not user_id:
        raise ValueError("user_id cannot be empty")

    user = database.get_user(user_id)

    if not user:
        raise ValueError(f"User {user_id} not found")

    return user
```

### 5. Idempotency

```python
@function_tool
def create_or_update_record(record_id: str, data: dict) -> str:
    """Create new record or update existing one."""
    if record_exists(record_id):
        update_record(record_id, data)
        return f"Updated record {record_id}"
    else:
        create_record(record_id, data)
        return f"Created record {record_id}"
```

## Testing Tools

```python
import pytest

@function_tool
def add_numbers(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b

def test_add_numbers():
    # Test tool directly
    result = add_numbers(2, 3)
    assert result == 5

async def test_tool_in_agent():
    # Test tool via agent
    agent = Agent(model=model, tools=[add_numbers])
    response = await agent.run(message="What's 2 + 3?")
    assert "5" in response.content
```

## Performance Optimization

### Caching Tool Results

```python
from functools import lru_cache

@function_tool
@lru_cache(maxsize=128)
def expensive_lookup(key: str) -> dict:
    """Cached lookup operation."""
    return perform_expensive_operation(key)
```

### Batch Tool Operations

```python
@function_tool
def batch_lookup(keys: list[str]) -> list[dict]:
    """Lookup multiple keys at once (more efficient)."""
    return database.batch_get(keys)
```

### Async for I/O

```python
@function_tool
async def fetch_multiple_urls(urls: list[str]) -> list[str]:
    """Fetch multiple URLs concurrently."""
    async with aiohttp.ClientSession() as session:
        tasks = [session.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [await r.text() for r in responses]
```

## Security Considerations

1. **Input validation**: Always validate tool inputs
2. **Authorization**: Check permissions before executing sensitive operations
3. **Sandboxing**: Execute code in isolated environments
4. **Audit logging**: Log all tool calls for security review
5. **Rate limiting**: Prevent abuse of expensive operations
6. **Secret management**: Never expose API keys or credentials in tool outputs
