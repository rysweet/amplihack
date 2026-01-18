# Migration Guide

## Overview

This guide covers migration scenarios between amplihack and Microsoft Agent Framework in both directions.

## Migration Scenarios

### 1. amplihack → Agent Framework (Scale Up)

### 2. Agent Framework → amplihack (Simplify)

### 3. Gradual Integration (Hybrid Approach)

---

## Scenario 1: amplihack → Agent Framework

**When to migrate**: Your amplihack prototype needs to become a production system with stateful conversations, enterprise features, or complex orchestration.

### Step 1: Assess Current Implementation

**Inventory your amplihack agents**:

```bash
ls .claude/agents/amplihack/
# Example output:
# - reviewer.md
# - analyzer.md
# - tester.md
```

**Identify components**:

- Which agents are stateless? (Keep in amplihack)
- Which need conversation context? (Migrate to Agent Framework)
- Which need orchestration? (Convert to workflows)

### Step 2: Set Up Agent Framework

```bash
# Install Agent Framework
pip install agent-framework --pre

# Create Agent Framework structure
mkdir -p src/agents
mkdir -p src/workflows
mkdir -p src/tools
```

### Step 3: Convert Agents

**amplihack agent** (`.claude/agents/amplihack/reviewer.md`):

```markdown
# Code Reviewer Agent

You are a code reviewer. Analyze code for:

- Bugs and correctness
- Performance issues
- Security vulnerabilities
- Best practices

Return structured feedback.
```

**Convert to Agent Framework**:

```python
# src/agents/reviewer.py
from agents_framework import Agent, ModelClient
from pydantic import BaseModel

class CodeReview(BaseModel):
    bugs: list[str]
    performance: list[str]
    security: list[str]
    best_practices: list[str]

reviewer_agent = Agent(
    name="code_reviewer",
    model=ModelClient(model="gpt-4"),
    instructions="""You are a code reviewer. Analyze code for:
    - Bugs and correctness
    - Performance issues
    - Security vulnerabilities
    - Best practices

    Return structured feedback.""",
    response_format=CodeReview
)
```

### Step 4: Add Statefulness

**amplihack** (stateless):

```python
# Each call is independent
result1 = reviewer.process({"file": "module1.py"})
result2 = reviewer.process({"file": "module2.py"})
# No connection between calls
```

**Agent Framework** (stateful):

```python
from agents_framework import Thread

thread = Thread()

# Calls share context
result1 = await reviewer_agent.run(
    thread=thread,
    message="Review module1.py: [code]"
)

result2 = await reviewer_agent.run(
    thread=thread,
    message="Now review module2.py: [code]"
)
# Agent remembers previous review
```

### Step 5: Convert to Workflow

**amplihack orchestration** (manual):

```python
# Manual sequential execution
analysis = analyzer.process({"code": code})
review = reviewer.process({"code": code})
tests = tester.process({"code": code})

# Manual synthesis
report = synthesize(analysis, review, tests)
```

**Agent Framework workflow**:

```python
from agents_framework import GraphWorkflow

workflow = GraphWorkflow()

# Add agents as nodes
workflow.add_node("analyze", analyzer_agent)
workflow.add_node("review", reviewer_agent)
workflow.add_node("test", tester_agent)
workflow.add_node("synthesize", synthesizer_agent)

# Define parallel execution
workflow.add_edge("START", ["analyze", "review", "test"])
workflow.add_edge(["analyze", "review", "test"], "synthesize")

# Execute
result = await workflow.run(initial_state={"code": code})
```

### Step 6: Add Enterprise Features

```python
# Telemetry
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("code-review-workflow"):
    result = await workflow.run(initial_state={"code": code})

# Middleware
from agents_framework import Middleware

class LoggingMiddleware(Middleware):
    async def process_request(self, message, context):
        logger.info(f"Request: {message}")
        return message, context

    async def process_response(self, response, context):
        logger.info(f"Response: {response}")
        return response

reviewer_agent.middleware = [LoggingMiddleware()]
```

### Step 7: Maintain Backwards Compatibility

Keep amplihack agents for file operations:

```python
# Agent Framework for orchestration
workflow = GraphWorkflow()

# amplihack for file operations
@function_tool
def analyze_files(path: str) -> str:
    """Use amplihack for file analysis."""
    import subprocess
    result = subprocess.run(
        ["claude", "--agent", ".claude/agents/amplihack/analyzer.md", path],
        capture_output=True,
        text=True
    )
    return result.stdout

file_agent = Agent(
    model=model,
    tools=[analyze_files]
)

workflow.add_node("files", file_agent)
```

### Step 8: Gradual Migration Checklist

- [ ] Set up Agent Framework infrastructure
- [ ] Convert stateless agents to Agent Framework agents
- [ ] Add thread management for stateful conversations
- [ ] Build workflows for complex orchestration
- [ ] Add telemetry and monitoring
- [ ] Implement error handling and retries
- [ ] Test thoroughly (unit + integration)
- [ ] Keep amplihack for file operations
- [ ] Document migration decisions
- [ ] Train team on Agent Framework

---

## Scenario 2: Agent Framework → amplihack

**When to migrate**: Over-engineered solution, cost optimization needed, or moving to local-only operation.

### Step 1: Identify Simplification Opportunities

**Audit Agent Framework usage**:

- Are conversations truly multi-turn? (Or single-shot?)
- Is workflow complexity justified? (Or simple sequential?)
- Are enterprise features used? (Or just overhead?)
- Can state be eliminated? (Or is it essential?)

### Step 2: Extract Stateless Components

**Agent Framework** (stateful):

```python
# Over-engineered for one-shot review
reviewer = Agent(model=model, instructions="Review code")
thread = Thread()  # Unnecessary for single use
response = await reviewer.run(thread=thread, message="Review: [code]")
```

**amplihack** (stateless):

```markdown
# .claude/agents/amplihack/reviewer.md

You are a code reviewer. Analyze the provided code and return feedback.
```

```python
# Simple invocation
from claude import Agent
reviewer = Agent(".claude/agents/amplihack/reviewer.md")
result = reviewer.process({"code": code})
```

### Step 3: Simplify Workflows

**Agent Framework** (complex):

```python
workflow = GraphWorkflow()
workflow.add_node("step1", agent1)
workflow.add_node("step2", agent2)
workflow.add_edge("step1", "step2")
result = await workflow.run(initial_state=state)
```

**amplihack** (simple):

```python
# Direct sequential execution
result1 = agent1.process({"input": data})
result2 = agent2.process({"input": result1})
```

### Step 4: Remove Infrastructure Overhead

**Remove**:

- OpenTelemetry setup (if not needed)
- Middleware chains (if unused)
- Context providers (if unnecessary)
- Checkpointing (if not used)

**Keep**:

- Basic logging
- Error handling
- Core functionality

### Step 5: Convert to File-Based Operations

**Agent Framework** (API-centric):

```python
@function_tool
def read_file(path: str) -> str:
    with open(path) as f:
        return f.read()

agent = Agent(tools=[read_file])
```

**amplihack** (native file ops):

```python
# Direct file operations in agent context
reviewer = Agent(".claude/agents/amplihack/reviewer.md")
result = reviewer.process({"files": ["src/module.py"]})
# Agent uses Read tool directly
```

### Step 6: Migration Checklist

- [ ] Identify stateless components
- [ ] Remove unnecessary state management
- [ ] Simplify workflows to sequential operations
- [ ] Convert agents to markdown definitions
- [ ] Remove infrastructure (telemetry, middleware)
- [ ] Switch to file-based operations
- [ ] Test simplified implementation
- [ ] Measure cost savings
- [ ] Document simplification decisions
- [ ] Update team documentation

---

## Scenario 3: Gradual Integration (Hybrid)

**Goal**: Use both systems optimally without full migration.

### Hybrid Architecture Pattern

```
amplihack (Orchestrator)
    ├─> Local file operations
    ├─> Simple task delegation
    └─> Delegates to Agent Framework
            ├─> Stateful conversations
            ├─> Complex workflows
            └─> Enterprise features
```

### Implementation Steps

#### 1. Define Boundaries

**amplihack responsibilities**:

- Orchestration layer
- File operations
- CI/CD integration
- Development workflows

**Agent Framework responsibilities**:

- User-facing conversations
- Multi-step research
- Tool-heavy operations
- Production features

#### 2. Create Integration Layer

```python
# src/integration/bridge.py
from agents_framework import Agent, Thread
from claude import Agent as ClaudeAgent

class HybridOrchestrator:
    def __init__(self):
        self.amplihack_agents = {
            "reviewer": ClaudeAgent(".claude/agents/amplihack/reviewer.md"),
            "analyzer": ClaudeAgent(".claude/agents/amplihack/analyzer.md")
        }

        self.af_agents = {
            "conversational": Agent(model=model, instructions="Chat"),
            "workflow": create_workflow()
        }

    async def process(self, task: dict):
        """Route to appropriate system."""
        if task["type"] == "file_operation":
            return self.amplihack_agents[task["agent"]].process(task)

        elif task["type"] == "conversation":
            thread = Thread()
            return await self.af_agents["conversational"].run(
                thread=thread,
                message=task["message"]
            )

        elif task["type"] == "workflow":
            return await self.af_agents["workflow"].run(
                initial_state=task["state"]
            )
```

#### 3. Use Context Sharing

```python
# Share context between systems
class SharedContext:
    def __init__(self):
        self.amplihack_results = {}
        self.af_threads = {}

    def store_amplihack_result(self, key, result):
        self.amplihack_results[key] = result

    def get_for_af(self, key):
        return self.amplihack_results.get(key)

# Usage
context = SharedContext()

# amplihack analysis
result = amplihack_agent.process({"files": ["src/"]})
context.store_amplihack_result("analysis", result)

# Agent Framework uses results
analysis = context.get_for_af("analysis")
response = await af_agent.run(
    message=f"Discuss analysis: {analysis}"
)
```

#### 4. Gradual Feature Addition

**Phase 1**: Keep amplihack, add Agent Framework for conversations

```python
# amplihack handles core logic
result = amplihack_agent.process(task)

# Agent Framework for user interaction
thread = Thread()
await af_agent.run(thread=thread, message=f"Result: {result}")
```

**Phase 2**: Migrate complex workflows to Agent Framework

```python
# Agent Framework workflow
workflow = GraphWorkflow()
# ... workflow definition ...

# amplihack for file operations (as tools)
@function_tool
def file_op(path):
    return amplihack_agent.process({"path": path})

agent = Agent(tools=[file_op])
workflow.add_node("files", agent)
```

**Phase 3**: Full hybrid with clear boundaries

```python
# Clear separation of concerns
orchestrator = HybridOrchestrator()
result = await orchestrator.process(task)
```

---

## Testing Migration

### Test Checklist

- [ ] Functional equivalence (same outputs)
- [ ] Performance comparison (latency, throughput)
- [ ] Cost analysis (token usage)
- [ ] Error handling (edge cases)
- [ ] Integration points (handoffs work)
- [ ] Monitoring (telemetry functional)
- [ ] Documentation (up to date)

### Test Examples

**Test functional equivalence**:

```python
# Test both implementations produce same result
amplihack_result = amplihack_agent.process({"input": test_input})
af_result = await af_agent.run(message=test_input)
assert normalize(amplihack_result) == normalize(af_result.content)
```

**Test performance**:

```python
import time

# amplihack
start = time.time()
result1 = amplihack_agent.process({"input": data})
amplihack_time = time.time() - start

# Agent Framework
start = time.time()
result2 = await af_agent.run(message=data)
af_time = time.time() - start

print(f"amplihack: {amplihack_time:.2f}s")
print(f"Agent Framework: {af_time:.2f}s")
```

---

## Rollback Plan

If migration fails:

1. **Keep both systems running** (hybrid mode)
2. **Rollback incrementally** (feature by feature)
3. **Document lessons learned**
4. **Adjust decision criteria**

**Rollback steps**:

- [ ] Stop new features in target system
- [ ] Route traffic back to original system
- [ ] Analyze what went wrong
- [ ] Fix issues
- [ ] Retry migration with updated plan

---

## Success Metrics

Track these metrics during migration:

- **Functionality**: All features working
- **Performance**: Latency within acceptable range
- **Cost**: Token usage optimized
- **Reliability**: Error rates low
- **Maintainability**: Code quality high
- **Team adoption**: Developers comfortable with new system

## Conclusion

Migration between amplihack and Agent Framework should be:

1. **Gradual** (not big bang)
2. **Reversible** (with rollback plan)
3. **Tested** (thoroughly)
4. **Documented** (for team)

When in doubt, use the hybrid approach to get benefits of both systems.
