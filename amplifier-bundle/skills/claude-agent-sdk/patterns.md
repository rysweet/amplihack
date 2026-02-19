# Claude Agent SDK - Production Patterns

## Agent Loop Patterns

### Gather Pattern (Agentic Search)

The Gather pattern enables agents to iteratively collect information from multiple sources before proceeding.

**When to Use:**

- Research tasks requiring multiple data points
- Analysis needing diverse perspectives
- Decision-making requiring comprehensive context

**Implementation:**

```python
from claude_agents import Agent

gather_agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[search_tool, read_tool, api_tool],
    system="""When gathering information:
    1. Identify key information gaps
    2. Search from multiple sources
    3. Cross-reference findings
    4. Continue until comprehensive
    5. Synthesize before concluding"""
)

result = gather_agent.run(
    "Research market trends for electric vehicles in 2024: "
    "Include sales data, major players, technology advances, and regulatory changes."
)
```

**Key Characteristics:**

- Agent makes multiple tool calls across several turns
- Each iteration builds on previous findings
- Natural termination when sufficient information gathered
- Claude determines when gathering is complete

**Optimization:**

```python
# Provide structure to guide gathering
system_prompt = """Gather information systematically:

For market research, collect:
- Market size and growth data
- Top 3-5 competitors
- Recent technological developments
- Regulatory environment
- Expert opinions

Stop when all categories have reliable data."""
```

### Act Pattern (Tool Selection)

The Act pattern focuses on choosing and executing the right tools for a task.

**When to Use:**

- Clear action required with known tools
- Sequential operations on data
- Workflow automation

**Implementation:**

```python
action_agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[file_tools, data_tools, notification_tools],
    system="""You are an automation agent. Given a task:
    1. Identify required actions
    2. Select appropriate tools
    3. Execute in logical sequence
    4. Handle errors gracefully
    5. Confirm completion"""
)

result = action_agent.run(
    "Process all CSV files in ./data: "
    "1. Validate data format "
    "2. Calculate summary statistics "
    "3. Generate report.pdf "
    "4. Send notification when complete"
)
```

**Best Practices:**

- Provide clear action sequence in system prompt
- Use descriptive tool names and descriptions
- Include error handling in tool implementations
- Return structured results for verification

### Verify Pattern (Self-Checking)

The Verify pattern enables agents to check their own work for accuracy.

**When to Use:**

- Critical calculations or decisions
- Data transformations requiring accuracy
- Code generation needing validation

**Implementation:**

```python
verify_agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[calculator_tool, code_exec_tool, test_tool],
    system="""For any important calculation or generation:
    1. Perform the primary task
    2. Use a different method to verify
    3. Compare results
    4. If mismatch, investigate and retry
    5. Report confidence level"""
)

result = verify_agent.run(
    "Calculate compound interest: "
    "$10,000 principal, 5% annual rate, 10 years, quarterly compounding. "
    "Verify your calculation using two different methods."
)
```

**Verification Strategies:**

1. **Dual Calculation**: Compute same result two different ways
2. **Round-Trip**: Convert data forth and back, check consistency
3. **Constraint Checking**: Verify results meet known constraints
4. **Test Generation**: Create and run tests for generated code

### Iterate Pattern (Refinement)

The Iterate pattern enables progressive refinement of outputs.

**When to Use:**

- Creative tasks needing refinement
- Optimization problems
- Quality improvement workflows

**Implementation:**

```python
iterate_agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[generate_tool, analyze_tool, improve_tool],
    max_turns=20,
    system="""Iteratively improve outputs:
    1. Generate initial version
    2. Analyze for quality/correctness
    3. Identify specific improvements
    4. Apply improvements
    5. Repeat until quality threshold met
    6. Return best version"""
)

result = iterate_agent.run(
    "Write a product description for a smart thermostat. "
    "Iteratively improve for clarity, persuasiveness, and SEO. "
    "Stop when score > 90/100."
)
```

**Convergence Control:**

```python
# Set clear stopping criteria
system_prompt = """Iterate until meeting criteria:
- No syntax errors
- All test cases pass
- Performance meets benchmark
- Code coverage > 80%

Maximum 10 iterations."""
```

## Context Management

### When to Use Subagents

**Use subagents for:**

1. **Task Isolation**: Specialized subtasks with different tool requirements

```python
with main_agent.subagent(
    system="Security expert focused on vulnerabilities",
    tools=[security_tools]
) as security_agent:
    security_report = security_agent.run("Audit this codebase")
```

2. **Context Partitioning**: Prevent context pollution from unrelated information

```python
# Main agent context stays clean
with main_agent.subagent(inherit_system=False) as research_agent:
    # Research agent has isolated context
    research = research_agent.run("Deep dive into topic X")
# Main agent only sees final research summary
```

3. **Parallel Workflows**: Multiple independent processes

```python
# Note: Subagents are sequential, but pattern supports parallel conceptually
security_task = main_agent.subagent(system="Security audit")
performance_task = main_agent.subagent(system="Performance analysis")

sec_result = security_task.run(code)
perf_result = performance_task.run(code)
```

4. **Permission Boundaries**: Different security contexts

```python
with main_agent.subagent(
    allowed_tools=["read_file"],  # Restricted permissions
    disallowed_tools=["write_file", "bash"]
) as readonly_agent:
    analysis = readonly_agent.run("Analyze but don't modify")
```

**Don't use subagents for:**

- Simple tool calls (use tools directly)
- When context sharing is important
- Very short tasks (overhead not worth it)

### Compaction Strategies

**Strategy 1: Token Threshold**

```python
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    max_context_tokens=100000  # Start compaction at 100K
)
```

**Strategy 2: Turn-Based Summarization**

```python
# Every N turns, summarize earlier conversation
if agent.current_turn % 10 == 0:
    agent.compact_context(strategy="summarize_old", keep_recent=5)
```

**Strategy 3: Smart Retention**

```python
# Keep important information, summarize rest
agent.compact_context(
    strategy="smart",
    retain_patterns=["error", "result", "decision"],
    summarize_patterns=["reasoning", "exploration"]
)
```

**Strategy 4: External Memory**

```python
# Store context externally, summarize references
context_store = {}

class MemoryHook(PostToolUseHook):
    async def execute(self, context):
        # Store detailed results externally
        result_id = store_result(context.tool_output)
        # Replace in context with reference
        context.tool_output = {"result_id": result_id, "summary": "..."}
        return context
```

### State Management

**Pattern 1: Agent State Dictionary**

```python
agent = Agent(model="claude-sonnet-4-5-20250929")
agent.state = {
    "processed_files": [],
    "errors_encountered": [],
    "current_phase": "initialization"
}

# Tools can access and modify state
def process_file_tool(filename: str) -> dict:
    result = process(filename)
    agent.state["processed_files"].append(filename)
    return result
```

**Pattern 2: Persistent State**

```python
import json
from pathlib import Path

class StatefulAgent:
    def __init__(self, state_file="agent_state.json"):
        self.state_file = Path(state_file)
        self.agent = Agent(model="claude-sonnet-4-5-20250929")
        self.load_state()

    def load_state(self):
        if self.state_file.exists():
            self.agent.state = json.loads(self.state_file.read_text())
        else:
            self.agent.state = {}

    def save_state(self):
        self.state_file.write_text(json.dumps(self.agent.state, indent=2))

    def run(self, task):
        result = self.agent.run(task)
        self.save_state()
        return result
```

### Memory Optimization

**Pattern 1: Lazy Loading**

```python
# Don't load all tools upfront
def get_tool_when_needed(tool_name: str):
    tool_registry = {
        "heavy_analysis": lambda: create_heavy_tool(),
        "large_dataset": lambda: create_data_tool()
    }
    return tool_registry[tool_name]()

# Agent starts lightweight
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[basic_tools]
)

# Add heavy tools only when needed
if "analyze large dataset" in user_task:
    agent.add_tool(get_tool_when_needed("large_dataset"))
```

**Pattern 2: Result Streaming**

```python
# Stream large results instead of holding in memory
def streaming_analysis_tool(data_path: str):
    """Yield results incrementally."""
    for chunk in process_data_chunks(data_path):
        yield analyze_chunk(chunk)

# Process results without holding all in memory
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[streaming_tool]
)
```

## Tool Design

### Single Responsibility Principle

**Good: Focused tools**

```python
def read_file(path: str) -> str:
    """Read file contents. Does one thing well."""
    return Path(path).read_text()

def write_file(path: str, content: str) -> bool:
    """Write file contents. Does one thing well."""
    Path(path).write_text(content)
    return True
```

**Bad: Multi-purpose tools**

```python
def file_operations(
    operation: str,
    path: str,
    content: str = None,
    mode: str = "r",
    encoding: str = "utf-8"
) -> any:
    """Too many responsibilities. Confusing for agent."""
    if operation == "read":
        return Path(path).read_text(encoding=encoding)
    elif operation == "write":
        return Path(path).write_text(content)
    elif operation == "append":
        pass  # Anti-pattern: Too many responsibilities (example truncated)
    # Multiple other operations...
    return None  # Anti-pattern: Unclear return type
```

### Idempotency

**Idempotent tools** can be called multiple times safely:

```python
def create_directory(path: str) -> dict:
    """Create directory. Safe to call multiple times."""
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)  # Idempotent
    return {
        "path": str(path_obj),
        "existed": path_obj.exists(),
        "created": True
    }
```

**Non-idempotent tools need safeguards:**

```python
def send_notification(message: str, recipient: str) -> dict:
    """Send notification. Not idempotent - implement deduplication."""
    notification_id = hashlib.md5(
        f"{message}{recipient}{time.time() // 60}".encode()
    ).hexdigest()

    if notification_id in sent_notifications:
        return {"sent": False, "reason": "duplicate"}

    send_email(recipient, message)
    sent_notifications.add(notification_id)
    return {"sent": True, "notification_id": notification_id}
```

### Error Handling

**Pattern 1: Structured Error Returns**

```python
def api_call(endpoint: str) -> dict:
    """Return structured results with error info."""
    try:
        response = requests.get(endpoint, timeout=10)
        response.raise_for_status()
        return {
            "success": True,
            "data": response.json(),
            "status_code": response.status_code
        }
    except requests.Timeout:
        return {
            "success": False,
            "error": "Request timeout after 10 seconds",
            "error_type": "timeout",
            "retryable": True
        }
    except requests.HTTPError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "http_error",
            "status_code": e.response.status_code,
            "retryable": e.response.status_code >= 500
        }
```

**Pattern 2: Graceful Degradation**

```python
def get_data_with_fallback(source: str) -> dict:
    """Try primary source, fall back to cache."""
    try:
        return fetch_from_api(source)
    except Exception as e:
        logger.warning(f"API failed: {e}. Using cache.")
        cached = get_from_cache(source)
        if cached:
            return {"data": cached, "source": "cache", "stale": True}
        return {"error": "Both API and cache failed", "success": False}
```

### Tool Composition

**Pattern: Composite Tools**

```python
def analyze_codebase(path: str) -> dict:
    """High-level tool that composes lower-level tools."""
    # Uses multiple smaller tools internally
    files = glob_tool(f"{path}/**/*.py")
    results = []

    for file in files:
        content = read_file_tool(file)
        metrics = calculate_metrics_tool(content)
        issues = lint_tool(content)
        results.append({
            "file": file,
            "metrics": metrics,
            "issues": issues
        })

    return {
        "total_files": len(files),
        "results": results,
        "summary": generate_summary(results)
    }
```

**Pattern: Tool Pipelines**

```python
# Define pipeline of tools
pipeline = [
    ("load", load_data_tool),
    ("clean", clean_data_tool),
    ("transform", transform_data_tool),
    ("analyze", analyze_data_tool)
]

def execute_pipeline(data_path: str) -> dict:
    """Execute tool pipeline."""
    result = {"input": data_path}

    for stage_name, tool in pipeline:
        try:
            result[stage_name] = tool(result.get("output", data_path))
            result["output"] = result[stage_name]
        except Exception as e:
            result["error"] = f"Pipeline failed at {stage_name}: {e}"
            break

    return result
```

## Security Patterns

### Hook-Based Validation

**Pattern: Input Sanitization**

```python
from claude_agents.hooks import PreToolUseHook
import re

class InputSanitizationHook(PreToolUseHook):
    async def execute(self, context):
        # Sanitize file paths
        if context.tool_name in ["read_file", "write_file"]:
            path = context.tool_input.get("path", "")
            # Remove dangerous patterns
            sanitized = re.sub(r'[^\w\s\-./]', '', path)
            context.tool_input["path"] = sanitized

        # Sanitize SQL
        if context.tool_name == "query_database":
            query = context.tool_input.get("query", "")
            # Escape dangerous characters
            sanitized = query.replace(";", "").replace("--", "")
            context.tool_input["query"] = sanitized

        return context
```

### Permission Restrictions

**Pattern: Role-Based Access**

```python
class RoleBasedPermissionHook(PreToolUseHook):
    def __init__(self, user_role: str):
        self.user_role = user_role
        self.role_permissions = {
            "admin": ["bash", "read_file", "write_file", "delete_file"],
            "developer": ["read_file", "write_file", "execute_code"],
            "analyst": ["read_file", "query_database", "generate_report"],
            "viewer": ["read_file"]
        }

    async def execute(self, context):
        allowed = self.role_permissions.get(self.user_role, [])

        if context.tool_name not in allowed:
            raise PermissionError(
                f"Role '{self.user_role}' not authorized for tool '{context.tool_name}'"
            )

        return context

# Usage
agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=all_tools,
    hooks=[RoleBasedPermissionHook(user_role="analyst")]
)
```

### Sensitive Data Handling

**Pattern: Data Redaction**

```python
class DataRedactionHook(PostToolUseHook):
    def __init__(self):
        self.patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'
        }

    def redact(self, text: str) -> str:
        """Redact sensitive patterns."""
        for pattern_name, pattern in self.patterns.items():
            text = re.sub(pattern, f"[REDACTED_{pattern_name.upper()}]", text)
        return text

    async def execute(self, context):
        # Redact sensitive data from tool outputs
        if isinstance(context.tool_output, str):
            context.tool_output = self.redact(context.tool_output)
        elif isinstance(context.tool_output, dict):
            for key, value in context.tool_output.items():
                if isinstance(value, str):
                    context.tool_output[key] = self.redact(value)

        return context
```

### Audit Logging

**Pattern: Comprehensive Audit Trail**

```python
class AuditLogHook(PreToolUseHook, PostToolUseHook):
    def __init__(self, audit_db_path: str):
        self.db_path = audit_db_path
        self.init_db()

    def init_db(self):
        """Initialize audit log database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                timestamp TEXT,
                tool_name TEXT,
                user_id TEXT,
                input TEXT,
                output TEXT,
                success BOOLEAN,
                execution_time REAL
            )
        """)
        conn.commit()
        conn.close()

    async def execute(self, context):
        if isinstance(self, PreToolUseHook):
            # Record intent
            self.log_entry = {
                "timestamp": datetime.now().isoformat(),
                "tool_name": context.tool_name,
                "user_id": get_current_user(),
                "input": json.dumps(context.tool_input)
            }
        else:  # PostToolUseHook
            # Record result
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO audit_log VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self.log_entry["timestamp"],
                self.log_entry["tool_name"],
                self.log_entry["user_id"],
                self.log_entry["input"],
                json.dumps(context.tool_output)[:1000],
                context.success,
                context.execution_time
            ))
            conn.commit()
            conn.close()

        return context
```

## Performance

### Token Budget Management

**Pattern: Dynamic Tool Loading**

```python
# Start with minimal tools
essential_tools = ["read_file", "write_file"]
optional_tools = {
    "analysis": [analyze_tool, stats_tool],
    "code": [execute_code_tool, lint_tool],
    "api": [http_tool, graphql_tool]
}

agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[tool_registry[t] for t in essential_tools]
)

# Add tools based on task
if "analyze" in user_task:
    agent.tools.extend(optional_tools["analysis"])
```

### Parallel Execution

**Pattern: Batch Processing**

```python
import asyncio

async def process_batch(items: list, agent: Agent) -> list:
    """Process multiple items in parallel."""
    tasks = []

    for item in items:
        # Create subagent for each item
        task = agent.subagent().run(f"Process {item}")
        tasks.append(task)

    # Wait for all to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return [
        r if not isinstance(r, Exception) else {"error": str(r)}
        for r in results
    ]
```

### Caching

**Pattern: Result Caching**

```python
from functools import lru_cache
import hashlib

class CachingHook(PostToolUseHook):
    def __init__(self):
        self.cache = {}

    def cache_key(self, tool_name: str, tool_input: dict) -> str:
        """Generate cache key from tool call."""
        input_str = json.dumps(tool_input, sort_keys=True)
        return hashlib.md5(f"{tool_name}:{input_str}".encode()).hexdigest()

    async def execute(self, context):
        key = self.cache_key(context.tool_name, context.tool_input)

        # Store successful results
        if context.success:
            self.cache[key] = {
                "output": context.tool_output,
                "timestamp": time.time()
            }

        return context

class CachePreHook(PreToolUseHook):
    def __init__(self, cache_hook: CachingHook, ttl: int = 300):
        self.cache = cache_hook.cache
        self.ttl = ttl

    async def execute(self, context):
        key = CachingHook().cache_key(context.tool_name, context.tool_input)

        if key in self.cache:
            cached = self.cache[key]
            age = time.time() - cached["timestamp"]

            if age < self.ttl:
                # Use cached result, skip tool execution
                context.tool_output = cached["output"]
                context.cached = True
                # Signal to skip execution (implementation-specific)

        return context
```

## Anti-Patterns

### Anti-Pattern 1: God Agent

**Problem:**

```python
# Don't: Single agent trying to do everything
god_agent = Agent(
    model="claude-sonnet-4-5-20250929",
    tools=[all_possible_tools],  # 50+ tools
    system="You can do anything..."  # Vague
)
```

**Solution:**

```python
# Do: Specialized agents with focused capabilities
code_agent = Agent(tools=[code_tools], system="Code specialist")
data_agent = Agent(tools=[data_tools], system="Data specialist")
api_agent = Agent(tools=[api_tools], system="API specialist")
```

### Anti-Pattern 2: Context Pollution

**Problem:**

```python
# Don't: Let irrelevant context accumulate
agent = Agent(model="claude-sonnet-4-5-20250929")
for task in many_unrelated_tasks:
    result = agent.run(task)  # Context keeps growing
```

**Solution:**

```python
# Do: Use fresh context or subagents for unrelated tasks
for task in many_unrelated_tasks:
    with agent.subagent() as task_agent:
        result = task_agent.run(task)  # Isolated context
```

### Anti-Pattern 3: Brittle Verification

**Problem:**

```python
# Don't: Rely on exact string matching
def verify_result(result: str) -> bool:
    return result == "Expected exact output"  # Too brittle
```

**Solution:**

```python
# Do: Semantic or constraint-based verification
def verify_result(result: dict) -> bool:
    return (
        result.get("status") == "success" and
        result.get("value", 0) > 0 and
        "error" not in result
    )
```

### Anti-Pattern 4: Over-Engineering

**Problem:**

```python
# Don't: Complex abstractions when simple suffices
from abc import ABC, abstractmethod

class AbstractToolFactory(ABC):
    @abstractmethod
    def create_tool(self) -> 'AbstractTool':
        pass  # Anti-pattern: Unnecessary abstraction layer

class AbstractTool(ABC):
    pass  # Anti-pattern: Empty abstraction

class ConcreteToolFactoryImpl(AbstractToolFactory):
    def create_tool(self) -> 'AbstractTool':
        pass  # Anti-pattern: 100+ lines of unnecessary complexity
```

**Solution:**

```python
# Do: Simple, direct tool creation
def create_my_tool() -> Tool:
    return Tool(name="my_tool", description="...", function=my_func)
```
