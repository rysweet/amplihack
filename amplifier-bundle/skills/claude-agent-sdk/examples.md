# Claude Agent SDK - Practical Examples

## Basic Agent Examples

### Minimal Python Agent

```python
from claude_agents import Agent

# Simplest possible agent
agent = Agent(model="claude-sonnet-4-5-20250929")

# Single task execution
result = agent.run("What is the capital of France?")
print(result.response)
# Output: "The capital of France is Paris."
```

### Minimal TypeScript Agent

```typescript
import { Agent } from "@anthropics/agent-sdk";

// Simplest possible agent
const agent = new Agent({
  model: "claude-sonnet-4-5-20250929",
});

// Single task execution
const result = await agent.run("What is the capital of France?");
console.log(result.response);
// Output: "The capital of France is Paris."
```

### Agent with Custom System Prompt

```python
from claude_agents import Agent

agent = Agent(
    model="claude-sonnet-4-5-20250929",
    system="""You are a Python expert focused on writing clean, idiomatic code.
    Always follow PEP 8 guidelines and suggest best practices.
    When showing code examples, include docstrings and type hints."""
)

result = agent.run("Write a function to calculate fibonacci numbers")
print(result.response)
```

### Agent with Custom Tools

```python
from claude_agents import Agent
from claude_agents.tools import Tool

# Define custom tool
def search_documentation(query: str, library: str) -> str:
    """Search library documentation (mock implementation)."""
    docs = {
        "requests": "The requests library is used for HTTP requests...",
        "pandas": "Pandas is a data manipulation library...",
    }
    return docs.get(library, f"Documentation for {library} not found.")

doc_search_tool = Tool(
    name="search_documentation",
    description="Search Python library documentation",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "library": {"type": "string", "description": "Library name (e.g., 'requests', 'pandas')"}
        },
        "required": ["query", "library"]
    },
    function=search_documentation
)

# Agent with custom tool
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[doc_search_tool],
    system="You are a helpful Python assistant with access to library documentation."
)

result = agent.run("How do I make an HTTP GET request in Python?")
print(result.response)
# Agent will use search_documentation tool to find relevant info
```

### Agent with MCP Integration

```python
from claude_agents import Agent
from claude_agents.mcp import MCPClient

# Connect to filesystem MCP server
fs_mcp = MCPClient(
    "npx",
    ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"]
)

# Connect to GitHub MCP server
github_mcp = MCPClient(
    "npx",
    ["-y", "@modelcontextprotocol/server-github"],
    env={"GITHUB_TOKEN": "ghp_..."}
)

# Agent with multiple MCP servers
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    mcp_clients=[fs_mcp, github_mcp],
    system="You are a development assistant with access to filesystem and GitHub."
)

result = agent.run(
    "List all Python files in the project and create a GitHub issue "
    "for adding type hints to files that don't have them."
)
```

## Tool Implementations

### File Operations Tool

```python
from claude_agents.tools import Tool
import os
from pathlib import Path

def safe_file_operation(operation: str, path: str, content: str = None) -> dict:
    """Perform safe file operations with validation."""
    # Validate path
    file_path = Path(path).resolve()
    allowed_dir = Path("/home/user/workspace").resolve()

    if not str(file_path).startswith(str(allowed_dir)):
        return {"error": "Path outside allowed directory"}

    try:
        if operation == "read":
            if not file_path.exists():
                return {"error": f"File not found: {path}"}
            return {
                "content": file_path.read_text(),
                "size": file_path.stat().st_size,
                "path": str(file_path)
            }

        elif operation == "write":
            if content is None:
                return {"error": "Content required for write operation"}
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            return {
                "success": True,
                "path": str(file_path),
                "size": len(content)
            }

        elif operation == "list":
            if not file_path.is_dir():
                return {"error": "Path is not a directory"}
            files = [str(f.relative_to(file_path)) for f in file_path.rglob("*") if f.is_file()]
            return {
                "files": files,
                "count": len(files),
                "path": str(file_path)
            }

    except Exception as e:
        return {"error": str(e)}

file_tool = Tool(
    name="file_operation",
    description="Perform safe file operations (read, write, list)",
    input_schema={
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "list"],
                "description": "Operation to perform"
            },
            "path": {"type": "string", "description": "File or directory path"},
            "content": {"type": "string", "description": "Content for write operation"}
        },
        "required": ["operation", "path"]
    },
    function=safe_file_operation
)
```

### Code Execution Tool

```python
import subprocess
import tempfile
from pathlib import Path

def execute_code(code: str, language: str, timeout: int = 30) -> dict:
    """Execute code in a sandboxed environment."""
    try:
        if language == "python":
            # Write code to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name

            # Execute with timeout
            result = subprocess.run(
                ["python3", temp_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Cleanup
            Path(temp_path).unlink()

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0
            }

        elif language == "bash":
            result = subprocess.run(
                ["bash", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0
            }

        else:
            return {"error": f"Unsupported language: {language}"}

    except subprocess.TimeoutExpired:
        return {"error": f"Execution timeout after {timeout} seconds"}
    except Exception as e:
        return {"error": str(e)}

code_exec_tool = Tool(
    name="execute_code",
    description="Execute Python or Bash code and return output",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Code to execute"},
            "language": {
                "type": "string",
                "enum": ["python", "bash"],
                "description": "Programming language"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 30
            }
        },
        "required": ["code", "language"]
    },
    function=execute_code
)
```

### Web Search Tool

```python
import aiohttp
from typing import List, Dict

async def web_search(query: str, max_results: int = 5) -> dict:
    """Perform web search using a search API."""
    # This is a mock implementation - use real search API in production
    search_api_url = "https://api.search-provider.com/search"
    api_key = os.getenv("SEARCH_API_KEY")

    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "q": query,
                "count": max_results,
                "apikey": api_key
            }

            async with session.get(search_api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []

                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title"),
                            "url": item.get("url"),
                            "snippet": item.get("snippet")
                        })

                    return {
                        "query": query,
                        "results": results,
                        "count": len(results)
                    }
                else:
                    return {"error": f"Search API returned {response.status}"}

    except Exception as e:
        return {"error": str(e)}

search_tool = Tool(
    name="web_search",
    description="Search the web for information",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return",
                "default": 5,
                "minimum": 1,
                "maximum": 10
            }
        },
        "required": ["query"]
    },
    function=web_search
)
```

### Database Query Tool

```python
import sqlite3
from typing import List, Dict, Any

def query_database(query: str, params: List[Any] = None) -> dict:
    """Execute SQL query on SQLite database."""
    db_path = "/path/to/database.db"

    # Validate query (read-only)
    query_lower = query.lower().strip()
    if not query_lower.startswith("select"):
        return {"error": "Only SELECT queries allowed"}

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        rows = cursor.fetchall()
        results = [dict(row) for row in rows]

        conn.close()

        return {
            "results": results,
            "count": len(results),
            "query": query
        }

    except sqlite3.Error as e:
        return {"error": f"Database error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}

db_tool = Tool(
    name="query_database",
    description="Execute SELECT queries on the database",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "SQL SELECT query to execute"
            },
            "params": {
                "type": "array",
                "items": {"type": ["string", "number"]},
                "description": "Query parameters for prepared statement"
            }
        },
        "required": ["query"]
    },
    function=query_database
)
```

### MCP Tool Wrapper

```python
from claude_agents.mcp import MCPClient
from claude_agents import Agent

# Create MCP client for custom server
custom_mcp = MCPClient(
    command="node",
    args=["./custom-mcp-server.js"],
    env={"API_KEY": "secret-key"}  # pragma: allowlist secret
)

# Agent automatically gets all tools from MCP server
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    mcp_clients=[custom_mcp]
)

# Use MCP tools naturally
result = agent.run("Use the custom_tool to process this data: [data]")
```

## Hook Implementations

### Logging Hook

```python
from claude_agents.hooks import PreToolUseHook, PostToolUseHook
import logging
from datetime import datetime

class ComprehensiveLoggingHook(PreToolUseHook, PostToolUseHook):
    """Log all tool usage with timing and results."""

    def __init__(self, log_file: str = "agent_tools.log"):
        self.logger = logging.getLogger("agent_tools")
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    async def execute(self, context):
        if isinstance(self, PreToolUseHook):
            self.logger.info(
                f"TOOL_START: {context.tool_name} | "
                f"Input: {context.tool_input}"
            )
        else:  # PostToolUseHook
            status = "SUCCESS" if context.success else "FAILED"
            self.logger.info(
                f"TOOL_END: {context.tool_name} | "
                f"Status: {status} | "
                f"Time: {context.execution_time:.2f}s | "
                f"Output: {str(context.tool_output)[:100]}"
            )

        return context

# Usage
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[...],
    hooks=[ComprehensiveLoggingHook("agent_activity.log")]
)
```

### Validation Hook

```python
from claude_agents.hooks import PreToolUseHook
import re

class SecurityValidationHook(PreToolUseHook):
    """Validate tool inputs for security issues."""

    def __init__(self):
        self.dangerous_patterns = [
            r"rm\s+-rf",
            r"mkfs",
            r"dd\s+if=.*of=/dev/",
            r":\(\)\{.*\|.*\};",  # Fork bomb
            r"eval\(",
            r"exec\("
        ]

    async def execute(self, context):
        # Validate bash commands
        if context.tool_name == "bash":
            command = context.tool_input.get("command", "")

            for pattern in self.dangerous_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    raise PermissionError(
                        f"Dangerous command blocked: {command}\n"
                        f"Matched pattern: {pattern}"
                    )

        # Validate file paths
        if context.tool_name in ["read_file", "write_file", "edit_file"]:
            path = context.tool_input.get("path", "")

            # Block directory traversal
            if ".." in path:
                raise ValueError("Directory traversal not allowed")

            # Block absolute paths to sensitive locations
            sensitive = ["/etc", "/sys", "/proc", "/root"]
            if any(path.startswith(s) for s in sensitive):
                raise PermissionError(f"Access to {path} not allowed")

        # Validate SQL queries (if using database tool)
        if context.tool_name == "query_database":
            query = context.tool_input.get("query", "").lower()

            # Only allow SELECT
            if not query.strip().startswith("select"):
                raise PermissionError("Only SELECT queries allowed")

            # Block dangerous SQL patterns
            dangerous_sql = ["drop", "delete", "truncate", "update", "insert"]
            if any(keyword in query for keyword in dangerous_sql):
                raise PermissionError("Potentially dangerous SQL blocked")

        return context

# Usage
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[...],
    hooks=[SecurityValidationHook()]
)
```

### Rate Limiting Hook

```python
from claude_agents.hooks import PreToolUseHook
import time
from collections import defaultdict
from typing import Dict, List

class RateLimitHook(PreToolUseHook):
    """Enforce rate limits on tool usage."""

    def __init__(
        self,
        global_limit: int = 100,  # Total calls per minute
        per_tool_limit: int = 20,  # Per-tool calls per minute
        time_window: int = 60      # Seconds
    ):
        self.global_limit = global_limit
        self.per_tool_limit = per_tool_limit
        self.time_window = time_window

        self.global_calls: List[float] = []
        self.tool_calls: Dict[str, List[float]] = defaultdict(list)

    def _clean_old_calls(self, call_list: List[float], now: float):
        """Remove calls outside time window."""
        return [t for t in call_list if now - t < self.time_window]

    async def execute(self, context):
        now = time.time()
        tool_name = context.tool_name

        # Clean old calls
        self.global_calls = self._clean_old_calls(self.global_calls, now)
        self.tool_calls[tool_name] = self._clean_old_calls(
            self.tool_calls[tool_name], now
        )

        # Check global limit
        if len(self.global_calls) >= self.global_limit:
            raise RuntimeError(
                f"Global rate limit exceeded: {self.global_limit} calls per "
                f"{self.time_window} seconds"
            )

        # Check per-tool limit
        if len(self.tool_calls[tool_name]) >= self.per_tool_limit:
            raise RuntimeError(
                f"Rate limit exceeded for {tool_name}: {self.per_tool_limit} "
                f"calls per {self.time_window} seconds"
            )

        # Record this call
        self.global_calls.append(now)
        self.tool_calls[tool_name].append(now)

        return context

# Usage
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[...],
    hooks=[RateLimitHook(global_limit=100, per_tool_limit=20)]
)
```

### Cost Tracking Hook

```python
from claude_agents.hooks import PostToolUseHook
from collections import defaultdict
from typing import Dict

class CostTrackingHook(PostToolUseHook):
    """Track estimated costs of tool usage."""

    def __init__(self):
        self.total_cost = 0.0
        self.tool_costs: Dict[str, float] = defaultdict(float)
        self.tool_call_counts: Dict[str, int] = defaultdict(int)

        # Cost per tool (adjust based on actual costs)
        self.cost_rates = {
            "bash": 0.001,
            "read_file": 0.0001,
            "write_file": 0.0002,
            "web_search": 0.01,
            "query_database": 0.0005,
            "execute_code": 0.002
        }

    def _estimate_cost(self, tool_name: str, execution_time: float) -> float:
        """Estimate cost based on tool and execution time."""
        base_rate = self.cost_rates.get(tool_name, 0.001)
        return base_rate * (1 + execution_time / 10)  # Time factor

    async def execute(self, context):
        cost = self._estimate_cost(context.tool_name, context.execution_time)

        self.total_cost += cost
        self.tool_costs[context.tool_name] += cost
        self.tool_call_counts[context.tool_name] += 1

        print(f"💰 Tool: {context.tool_name} | Cost: ${cost:.4f} | Total: ${self.total_cost:.4f}")

        return context

    def report(self):
        """Generate cost report."""
        print("\n=== Cost Report ===")
        print(f"Total Cost: ${self.total_cost:.4f}")
        print("\nBy Tool:")
        for tool, cost in sorted(self.tool_costs.items(), key=lambda x: x[1], reverse=True):
            count = self.tool_call_counts[tool]
            avg = cost / count if count > 0 else 0
            print(f"  {tool}: ${cost:.4f} ({count} calls, ${avg:.4f} avg)")

# Usage
cost_tracker = CostTrackingHook()
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[...],
    hooks=[cost_tracker]
)

result = agent.run("Process this data")
cost_tracker.report()
```

## Advanced Patterns

### Subagent Delegation

```python
from claude_agents import Agent
from claude_agents.tools import Tool

# Main coordinator agent
main_agent = Agent(
    model="claude-sonnet-4-5-20250929",
    system="You are a project coordinator. Delegate specialized tasks to subagents."
)

# Example: Code review task
with main_agent.subagent(
    system="You are a security-focused code reviewer. Check for vulnerabilities.",
    tools=[read_file_tool, static_analysis_tool],
    max_turns=10
) as security_reviewer:
    security_report = security_reviewer.run(
        "Review all Python files in ./src for security issues"
    )

# Another subagent for performance review
with main_agent.subagent(
    system="You are a performance expert. Identify bottlenecks.",
    tools=[read_file_tool, profiler_tool],
    max_turns=10
) as performance_reviewer:
    performance_report = performance_reviewer.run(
        "Analyze ./src for performance bottlenecks"
    )

# Main agent synthesizes results
final_report = main_agent.run(
    f"Based on these reviews:\n\n"
    f"Security: {security_report.response}\n\n"
    f"Performance: {performance_report.response}\n\n"
    f"Create a prioritized action plan."
)
```

### Agentic Search Pattern

```python
from claude_agents import Agent

# Agent with search and analysis tools
search_agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[web_search_tool, read_url_tool, summarize_tool],
    system="""You are a research assistant. When given a research topic:
    1. Search for relevant information
    2. Read and analyze sources
    3. Gather multiple perspectives
    4. Synthesize findings
    Continue until you have comprehensive information."""
)

result = search_agent.run(
    "Research the current state of quantum computing: "
    "What are the leading approaches, key challenges, and recent breakthroughs?"
)

# Agent will:
# 1. Search for "quantum computing current state"
# 2. Read top results
# 3. Search for "quantum computing challenges"
# 4. Search for "quantum computing breakthroughs 2024"
# 5. Synthesize all information
# 6. Return comprehensive report
```

### Context Compaction Strategy

```python
from claude_agents import Agent

# Agent with automatic context compaction
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    max_context_tokens=50000,  # Start compaction at 50K tokens
    compaction_strategy="smart_summarize"
)

# Long-running task that accumulates context
for i in range(100):
    result = agent.run(f"Process item {i}")
    # Context automatically compacted when approaching limit
```

### Verification Pattern

```python
from claude_agents import Agent

# Agent with self-verification
verification_agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[calculator_tool, code_exec_tool],
    system="""You are a meticulous assistant. For any calculation or analysis:
    1. Perform the task
    2. Verify your work using a different method
    3. Report both results and confidence level"""
)

result = verification_agent.run(
    "Calculate the ROI for a $100,000 investment over 5 years at 7% annual return. "
    "Verify your calculation."
)

# Agent will:
# 1. Calculate using formula
# 2. Verify by calculating year by year
# 3. Compare results
# 4. Report with confidence
```

### Error Recovery Pattern

```python
from claude_agents import Agent, AgentError

# Agent with retry logic
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[flaky_api_tool],
    max_turns=15
)

max_retries = 3
for attempt in range(max_retries):
    try:
        result = agent.run("Fetch data from API and analyze")
        break  # Success
    except AgentError as e:
        if attempt < max_retries - 1:
            print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
            # Optionally modify agent configuration for retry
        else:
            print(f"All attempts failed: {e}")
            raise
```

## Integration Examples

### Integration with Amplihack Agents

```python
# .claude/agents/amplihack/specialized/data_analyzer.md
"""
You are a data analysis specialist.
Use the Agent SDK to perform multi-step data analysis.
"""

from claude_agents import Agent
from claude_agents.tools import Tool

def create_data_analyzer():
    """Create specialized data analysis agent."""
    return Agent(
        model="claude-sonnet-4-5-20250929",
        system="""You are a data analysis expert. You can:
        - Load and explore datasets
        - Perform statistical analysis
        - Create visualizations
        - Generate insights and recommendations""",
        tools=[
            load_data_tool,
            stats_tool,
            plot_tool,
            query_tool
        ]
    )

# Usage in Amplihack workflow
analyzer = create_data_analyzer()
result = analyzer.run("Analyze sales_data.csv and identify trends")
```

### Integration with auto_mode.py

```python
# In amplihack/auto_mode.py
from claude_agents import Agent
from claude_agents.tools import Tool

def setup_auto_mode_agent():
    """Create agent for auto mode with all Amplihack tools."""
    return Agent(
        model="claude-sonnet-4-5-20250929",
        system=load_amplihack_system_prompt(),
        tools=get_amplihack_tools(),
        hooks=[
            AmplihackLoggingHook(),
            AmplihackSecurityHook()
        ],
        max_turns=50
    )

# Auto mode execution
agent = setup_auto_mode_agent()
result = agent.run(user_task)
```

### Integration with Existing Tools

```python
# Wrap existing Amplihack tools for Agent SDK
from claude_agents.tools import Tool

def wrap_amplihack_tool(amplihack_tool):
    """Convert Amplihack tool to Agent SDK format."""
    return Tool(
        name=amplihack_tool.name,
        description=amplihack_tool.description,
        input_schema=amplihack_tool.schema,
        function=amplihack_tool.execute
    )

# Create agent with wrapped tools
amplihack_tools = [
    wrap_amplihack_tool(tool)
    for tool in load_amplihack_tools()
]

agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=amplihack_tools
)
```
