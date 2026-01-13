# MCP Server Management

Comprehensive guide for managing Model Context Protocol (MCP) servers in AI-assisted development workflows.

## When to Use

- Setting up new MCP servers for AI tools
- Debugging MCP connection issues
- Registering custom tools and resources
- Optimizing MCP server performance
- Understanding MCP protocol mechanics

## MCP Protocol Overview

### What is MCP?

Model Context Protocol (MCP) is a standard protocol for AI assistants to communicate with external tools and data sources.

```
┌─────────────┐     MCP Protocol     ┌─────────────┐
│   AI Host   │ ◄──────────────────► │ MCP Server  │
│  (Claude)   │   JSON-RPC over      │  (Tools +   │
│             │   stdin/stdout       │  Resources) │
└─────────────┘   or SSE/HTTP        └─────────────┘
```

### Core Concepts

| Concept | Description | Example |
|---------|-------------|---------|
| **Server** | Process providing tools/resources | File system server, database server |
| **Tool** | Callable function with parameters | `read_file`, `execute_query` |
| **Resource** | Data source with URI scheme | `file://`, `db://` |
| **Prompt** | Reusable prompt template | Code review template |

### Protocol Messages

```json
// Tool Call Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "read_file",
    "arguments": {"path": "/src/main.py"}
  }
}

// Tool Call Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {"type": "text", "text": "file contents here..."}
    ]
  }
}
```

## Server Configuration

### Configuration File Structure

```json
{
  "mcpServers": {
    "server-name": {
      "command": "python",
      "args": ["-m", "my_mcp_server"],
      "env": {
        "API_KEY": "${API_KEY}"
      },
      "disabled": false
    }
  }
}
```

### Configuration Locations

| Platform | Location |
|----------|----------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| VS Code | `.vscode/mcp.json` or workspace settings |

### Transport Types

#### stdio (Standard)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
    }
  }
}
```

#### SSE (Server-Sent Events)

```json
{
  "mcpServers": {
    "remote-server": {
      "url": "http://localhost:8080/sse",
      "transport": "sse"
    }
  }
}
```

## Tool Registration

### Python Server with FastMCP

```python
from fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
def search_code(query: str, file_pattern: str = "*.py") -> str:
    """Search for code patterns in the codebase.
    
    Args:
        query: Search pattern (regex supported)
        file_pattern: Glob pattern for files to search
    
    Returns:
        Matching lines with file locations
    """
    # Implementation here
    return results

@mcp.tool()
def run_tests(path: str = ".", verbose: bool = False) -> str:
    """Run test suite for a path.
    
    Args:
        path: Directory or file to test
        verbose: Show detailed output
    
    Returns:
        Test results summary
    """
    # Implementation here
    return output

if __name__ == "__main__":
    mcp.run()
```

### TypeScript Server

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server(
  { name: "my-server", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "analyze_code",
      description: "Analyze code for patterns and issues",
      inputSchema: {
        type: "object",
        properties: {
          file_path: { type: "string", description: "Path to analyze" },
          checks: { type: "array", items: { type: "string" } }
        },
        required: ["file_path"]
      }
    }
  ]
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "analyze_code") {
    const { file_path, checks } = request.params.arguments;
    // Implementation
    return { content: [{ type: "text", text: result }] };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
```

## Resource Management

### Defining Resources

```python
from fastmcp import FastMCP

mcp = FastMCP("resource-server")

@mcp.resource("config://app")
def get_app_config() -> str:
    """Application configuration."""
    return json.dumps(load_config())

@mcp.resource("schema://database/{table}")
def get_table_schema(table: str) -> str:
    """Database table schema."""
    return get_schema(table)
```

### Resource Templates

```python
@mcp.resource("file://{path}")
def read_project_file(path: str) -> str:
    """Read a file from the project directory."""
    full_path = PROJECT_ROOT / path
    if not full_path.is_relative_to(PROJECT_ROOT):
        raise ValueError("Path escapes project root")
    return full_path.read_text()
```

## Debugging MCP Connections

### Common Issues and Solutions

#### Server Won't Start

```bash
# Check if command exists
which npx  # or python, node, etc.

# Test server manually
npx -y @modelcontextprotocol/server-filesystem /tmp

# Check for port conflicts
lsof -i :8080
```

#### Connection Timeouts

```python
# Increase timeout in client configuration
{
  "mcpServers": {
    "slow-server": {
      "command": "python",
      "args": ["server.py"],
      "timeout": 60000  # 60 seconds
    }
  }
}
```

#### Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In FastMCP
mcp = FastMCP("debug-server", debug=True)
```

### MCP Inspector

```bash
# Use MCP Inspector for interactive debugging
npx @modelcontextprotocol/inspector

# Test specific server
npx @modelcontextprotocol/inspector python -m my_server
```

### Health Checks

```python
@mcp.tool()
def health_check() -> str:
    """Check server health and connectivity."""
    checks = {
        "server": "ok",
        "database": check_db_connection(),
        "cache": check_cache_connection(),
        "disk_space": check_disk_space()
    }
    return json.dumps(checks, indent=2)
```

## Common MCP Patterns

### Pattern 1: Stateless Tools

```python
# Preferred: Each call is independent
@mcp.tool()
def format_code(code: str, language: str) -> str:
    """Format code - stateless operation."""
    return formatter.format(code, language)
```

### Pattern 2: Resource-Backed Tools

```python
# Tool that reads from managed resources
@mcp.tool()
def query_logs(
    service: str,
    timerange: str = "1h",
    level: str = "error"
) -> str:
    """Query application logs."""
    # Uses resource: logs://{service}
    logs = get_resource(f"logs://{service}")
    return filter_logs(logs, timerange, level)
```

### Pattern 3: Batch Operations

```python
@mcp.tool()
def batch_analyze(
    files: list[str],
    analysis_type: str = "security"
) -> str:
    """Analyze multiple files efficiently."""
    results = []
    for file in files:
        result = analyze_file(file, analysis_type)
        results.append({"file": file, "result": result})
    return json.dumps(results, indent=2)
```

### Pattern 4: Progress Streaming

```python
@mcp.tool()
async def long_running_task(params: dict) -> str:
    """Task with progress updates via notifications."""
    total_steps = 10
    for i in range(total_steps):
        await process_step(i, params)
        # Send progress notification
        await mcp.notify("progress", {
            "step": i + 1,
            "total": total_steps,
            "message": f"Processing step {i + 1}"
        })
    return "Complete"
```

### Pattern 5: Error Handling

```python
from fastmcp import ToolError

@mcp.tool()
def safe_file_operation(path: str, operation: str) -> str:
    """File operation with proper error handling."""
    try:
        if operation == "read":
            return Path(path).read_text()
        elif operation == "delete":
            Path(path).unlink()
            return f"Deleted {path}"
    except FileNotFoundError:
        raise ToolError(f"File not found: {path}")
    except PermissionError:
        raise ToolError(f"Permission denied: {path}")
    except Exception as e:
        raise ToolError(f"Operation failed: {str(e)}")
```

## Server Security

### Path Sandboxing

```python
from pathlib import Path

ALLOWED_ROOT = Path("/workspace")

def validate_path(path: str) -> Path:
    """Ensure path is within allowed directory."""
    resolved = (ALLOWED_ROOT / path).resolve()
    if not resolved.is_relative_to(ALLOWED_ROOT):
        raise ValueError("Path escapes sandbox")
    return resolved
```

### Input Validation

```python
from pydantic import BaseModel, validator

class QueryParams(BaseModel):
    table: str
    limit: int = 100
    
    @validator('table')
    def validate_table(cls, v):
        allowed = ['users', 'products', 'orders']
        if v not in allowed:
            raise ValueError(f'Table must be one of: {allowed}')
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        if v > 1000:
            raise ValueError('Limit cannot exceed 1000')
        return v
```

### Rate Limiting

```python
from functools import wraps
from time import time

rate_limits = {}

def rate_limit(calls: int, period: int):
    """Decorator for rate limiting tool calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = func.__name__
            now = time()
            
            if key not in rate_limits:
                rate_limits[key] = []
            
            # Clean old entries
            rate_limits[key] = [t for t in rate_limits[key] if now - t < period]
            
            if len(rate_limits[key]) >= calls:
                raise ToolError(f"Rate limit exceeded: {calls} calls per {period}s")
            
            rate_limits[key].append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@mcp.tool()
@rate_limit(calls=10, period=60)
def expensive_operation(params: dict) -> str:
    """Rate-limited operation."""
    return perform_operation(params)
```

## Testing MCP Servers

### Unit Testing Tools

```python
import pytest
from my_server import mcp

@pytest.fixture
def server():
    return mcp

def test_search_code(server):
    result = server.call_tool("search_code", {
        "query": "def main",
        "file_pattern": "*.py"
    })
    assert "main.py" in result

def test_invalid_path(server):
    with pytest.raises(ToolError):
        server.call_tool("read_file", {"path": "../../../etc/passwd"})
```

### Integration Testing

```python
import subprocess
import json

def test_server_startup():
    """Test server starts and responds to initialize."""
    proc = subprocess.Popen(
        ["python", "-m", "my_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )
    
    # Send initialize request
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"capabilities": {}}
    })
    proc.stdin.write(request + "\n")
    proc.stdin.flush()
    
    response = json.loads(proc.stdout.readline())
    assert "result" in response
    assert response["result"]["serverInfo"]["name"] == "my-server"
    
    proc.terminate()
```

## Performance Optimization

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def expensive_lookup(key: str) -> dict:
    """Cached expensive operation."""
    return database.query(key)

@mcp.tool()
def get_data(key: str, bypass_cache: bool = False) -> str:
    """Get data with optional cache bypass."""
    if bypass_cache:
        expensive_lookup.cache_clear()
    return json.dumps(expensive_lookup(key))
```

### Async Operations

```python
import asyncio

@mcp.tool()
async def parallel_analysis(files: list[str]) -> str:
    """Analyze files in parallel."""
    tasks = [analyze_file_async(f) for f in files]
    results = await asyncio.gather(*tasks)
    return json.dumps(dict(zip(files, results)))
```

### Connection Pooling

```python
from contextlib import contextmanager
import queue

class ConnectionPool:
    def __init__(self, size: int = 5):
        self.pool = queue.Queue(maxsize=size)
        for _ in range(size):
            self.pool.put(create_connection())
    
    @contextmanager
    def get_connection(self):
        conn = self.pool.get()
        try:
            yield conn
        finally:
            self.pool.put(conn)

pool = ConnectionPool()

@mcp.tool()
def query_database(sql: str) -> str:
    """Query with connection pooling."""
    with pool.get_connection() as conn:
        return json.dumps(conn.execute(sql).fetchall())
```

## Checklist

### Server Setup
- [ ] Choose appropriate transport (stdio vs SSE)
- [ ] Configure environment variables securely
- [ ] Set appropriate timeouts
- [ ] Enable debug logging for development

### Tool Design
- [ ] Tools are stateless where possible
- [ ] Input validation is comprehensive
- [ ] Error messages are helpful
- [ ] Documentation is complete

### Security
- [ ] Paths are sandboxed
- [ ] Inputs are validated
- [ ] Rate limiting is implemented
- [ ] Sensitive data is not logged

### Testing
- [ ] Unit tests for each tool
- [ ] Integration tests for server lifecycle
- [ ] Error handling is tested
- [ ] Performance is acceptable
