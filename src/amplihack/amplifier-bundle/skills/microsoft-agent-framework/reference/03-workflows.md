# Workflows - Graph-Based Orchestration

## What are Workflows?

Workflows in Microsoft Agent Framework are graph-based orchestration systems that coordinate multiple agents and operations. They provide structured control flow with:

- **Nodes**: Agents, functions, or operations
- **Edges**: Directed connections defining execution order
- **Conditional routing**: Dynamic paths based on state
- **Parallel execution**: Concurrent node processing
- **Checkpointing**: Save/resume long-running processes

## Basic Workflow

```python
from agents_framework import GraphWorkflow, Agent, ModelClient

# Create workflow
workflow = GraphWorkflow()

# Add agents as nodes
agent1 = Agent(model=ModelClient(model="gpt-4"), instructions="Research")
agent2 = Agent(model=ModelClient(model="gpt-4"), instructions="Summarize")

workflow.add_node("researcher", agent1)
workflow.add_node("summarizer", agent2)

# Define sequential execution
workflow.add_edge("researcher", "summarizer")

# Set entry point
workflow.set_entry_point("researcher")

# Run workflow
result = await workflow.run(initial_message="Research AI trends")
print(result.final_output)
```

## Workflow Components

### Nodes

Nodes are execution units in the workflow graph.

**Types of Nodes**:

1. **Agent nodes**: Execute agents
2. **Function nodes**: Run Python/C# functions
3. **Decision nodes**: Route based on conditions
4. **Parallel nodes**: Execute multiple operations concurrently

```python
# Agent node
workflow.add_node("agent1", my_agent)

# Function node
def process_data(state):
    return {"result": state["data"] * 2}

workflow.add_node("processor", process_data)

# Lambda node
workflow.add_node("filter", lambda state: {"filtered": [x for x in state["items"] if x > 0]})
```

### Edges

Edges define execution flow between nodes.

**Types of Edges**:

1. **Sequential**: Node A → Node B
2. **Conditional**: Node A → (condition) → Node B or C
3. **Parallel**: Node A → [Node B, Node C] (both execute)
4. **Join**: [Node A, Node B] → Node C (wait for both)

```python
# Sequential
workflow.add_edge("node1", "node2")

# Parallel - fork
workflow.add_edge("START", ["worker1", "worker2", "worker3"])

# Parallel - join
workflow.add_edge(["worker1", "worker2", "worker3"], "aggregator")
```

### Conditional Edges

Route based on state or output:

```python
def should_approve(state):
    """Return True to approve, False to reject"""
    return state.get("confidence", 0) > 0.8

workflow.add_conditional_edge(
    "reviewer",
    should_approve,
    {
        True: "approve_node",
        False: "reject_node"
    }
)
```

**String-based routing**:

```python
def route_by_category(state):
    """Return string matching edge key"""
    return state.get("category", "default")

workflow.add_conditional_edge(
    "classifier",
    route_by_category,
    {
        "urgent": "urgent_handler",
        "normal": "normal_handler",
        "low": "low_priority_handler",
        "default": "general_handler"
    }
)
```

### State Management

Workflow state is a dictionary passed between nodes:

```python
def node_function(state: dict) -> dict:
    """
    Receive state, process, return updated state.
    Updates are merged into existing state.
    """
    result = process(state["input"])
    return {
        "output": result,
        "processed_count": state.get("processed_count", 0) + 1
    }

workflow.add_node("processor", node_function)

# Initial state
initial_state = {
    "input": "data to process",
    "processed_count": 0
}

result = await workflow.run(initial_state=initial_state)
print(result.state)  # Final state after all nodes
```

## Workflow Patterns

### Sequential Pipeline

```python
workflow = GraphWorkflow()

# Add stages
workflow.add_node("gather", gather_agent)
workflow.add_node("analyze", analyze_agent)
workflow.add_node("report", report_agent)

# Chain them
workflow.add_edge("gather", "analyze")
workflow.add_edge("analyze", "report")

workflow.set_entry_point("gather")

result = await workflow.run(initial_message="Research topic")
```

### Parallel Execution

```python
workflow = GraphWorkflow()

# Multiple workers
workflow.add_node("worker1", worker_agent1)
workflow.add_node("worker2", worker_agent2)
workflow.add_node("worker3", worker_agent3)
workflow.add_node("aggregator", aggregate_agent)

# Fork: run workers in parallel
workflow.add_edge("START", ["worker1", "worker2", "worker3"])

# Join: aggregate results
workflow.add_edge(["worker1", "worker2", "worker3"], "aggregator")

result = await workflow.run(initial_state={"task": "analyze data"})
```

### Conditional Branching

```python
workflow = GraphWorkflow()

workflow.add_node("classifier", classifier_agent)
workflow.add_node("simple_handler", simple_agent)
workflow.add_node("complex_handler", complex_agent)

def classify_complexity(state):
    return state.get("complexity", "simple")

workflow.add_conditional_edge(
    "classifier",
    classify_complexity,
    {
        "simple": "simple_handler",
        "complex": "complex_handler"
    }
)

workflow.set_entry_point("classifier")
```

### Iterative Refinement

```python
workflow = GraphWorkflow()

workflow.add_node("generate", generator_agent)
workflow.add_node("review", reviewer_agent)
workflow.add_node("finalize", finalizer_agent)

def needs_revision(state):
    return state.get("approved", False)

workflow.add_edge("generate", "review")
workflow.add_conditional_edge(
    "review",
    needs_revision,
    {
        True: "finalize",      # Approved
        False: "generate"      # Revise (loop back)
    }
)

# Add iteration limit to prevent infinite loops
MAX_ITERATIONS = 3

def safe_needs_revision(state):
    iterations = state.get("iterations", 0)
    if iterations >= MAX_ITERATIONS:
        return True  # Force approval after max iterations
    return state.get("approved", False)
```

### Human-in-the-Loop

```python
from agents_framework import HumanApproval

workflow = GraphWorkflow()

workflow.add_node("prepare", prepare_agent)
workflow.add_node("human_approval", HumanApproval(
    prompt="Approve this action?",
    options=["approve", "reject", "modify"]
))
workflow.add_node("execute", execute_agent)
workflow.add_node("cancel", cancel_agent)

workflow.add_edge("prepare", "human_approval")

def handle_approval(state):
    return state.get("approval_decision", "reject")

workflow.add_conditional_edge(
    "human_approval",
    handle_approval,
    {
        "approve": "execute",
        "reject": "cancel",
        "modify": "prepare"  # Loop back to modify
    }
)
```

### Error Handling & Retry

```python
workflow = GraphWorkflow()

workflow.add_node("try_operation", operation_agent)
workflow.add_node("handle_error", error_handler_agent)
workflow.add_node("success", success_agent)

def check_success(state):
    if state.get("error"):
        return "error"
    return "success"

workflow.add_conditional_edge(
    "try_operation",
    check_success,
    {
        "success": "success",
        "error": "handle_error"
    }
)

# Retry logic
def should_retry(state):
    retries = state.get("retry_count", 0)
    return retries < 3

workflow.add_conditional_edge(
    "handle_error",
    should_retry,
    {
        True: "try_operation",  # Retry
        False: "END"            # Give up
    }
)
```

## Advanced Workflow Features

### Checkpointing

Save workflow state and resume later:

```python
from agents_framework import CheckpointManager

checkpoint_manager = CheckpointManager(storage_path="./checkpoints")

workflow = GraphWorkflow(checkpoint_manager=checkpoint_manager)

# Run workflow with checkpointing
result = await workflow.run(
    initial_state={"task": "long running task"},
    checkpoint_id="workflow-123"
)

# Resume from checkpoint
result = await workflow.resume(checkpoint_id="workflow-123")
```

### Workflow Composition

Embed workflows within workflows:

```python
# Sub-workflow
sub_workflow = GraphWorkflow()
sub_workflow.add_node("step1", agent1)
sub_workflow.add_node("step2", agent2)
sub_workflow.add_edge("step1", "step2")

# Main workflow
main_workflow = GraphWorkflow()
main_workflow.add_node("prepare", prepare_agent)
main_workflow.add_node("sub_process", sub_workflow)  # Embedded workflow
main_workflow.add_node("finalize", finalize_agent)

main_workflow.add_edge("prepare", "sub_process")
main_workflow.add_edge("sub_process", "finalize")
```

### Streaming Workflow Results

Stream outputs as workflow executes:

```python
async for event in workflow.run_stream(initial_state={"task": "process"}):
    print(f"Node: {event.node_name}")
    print(f"Output: {event.output}")
    print(f"State: {event.state}")
```

### Time-Travel Debugging

Inspect workflow execution history:

```python
result = await workflow.run(initial_state={"task": "debug me"})

# Access execution history
for step in result.history:
    print(f"Node: {step.node_name}")
    print(f"Input: {step.input_state}")
    print(f"Output: {step.output_state}")
    print(f"Duration: {step.duration}s")
```

## Multi-Agent Patterns

### Sequential Handoff

```python
# Research → Write → Review → Publish
workflow = GraphWorkflow()

workflow.add_node("research", research_agent)
workflow.add_node("write", writing_agent)
workflow.add_node("review", review_agent)
workflow.add_node("publish", publish_agent)

workflow.add_edge("research", "write")
workflow.add_edge("write", "review")
workflow.add_edge("review", "publish")
```

### Concurrent Specialization

```python
# Multiple specialists work in parallel, then synthesize
workflow = GraphWorkflow()

workflow.add_node("security_expert", security_agent)
workflow.add_node("performance_expert", performance_agent)
workflow.add_node("ux_expert", ux_agent)
workflow.add_node("synthesizer", synthesis_agent)

# All experts run concurrently
workflow.add_edge("START", ["security_expert", "performance_expert", "ux_expert"])

# Wait for all, then synthesize
workflow.add_edge(["security_expert", "performance_expert", "ux_expert"], "synthesizer")
```

### Hierarchical Delegation

```python
# Manager delegates to workers, aggregates results
workflow = GraphWorkflow()

workflow.add_node("manager", manager_agent)
workflow.add_node("worker1", worker_agent)
workflow.add_node("worker2", worker_agent)
workflow.add_node("worker3", worker_agent)
workflow.add_node("report", reporting_agent)

# Manager assigns tasks
workflow.add_edge("manager", ["worker1", "worker2", "worker3"])

# Workers complete, manager aggregates
workflow.add_edge(["worker1", "worker2", "worker3"], "report")
```

### Magentic Pattern (Dynamic Routing)

```python
# Route to appropriate specialist based on query
workflow = GraphWorkflow()

workflow.add_node("router", router_agent)
workflow.add_node("tech_specialist", tech_agent)
workflow.add_node("business_specialist", business_agent)
workflow.add_node("creative_specialist", creative_agent)

def route_query(state):
    category = state.get("category")
    return {
        "technical": "tech_specialist",
        "business": "business_specialist",
        "creative": "creative_specialist"
    }.get(category, "tech_specialist")  # Default

workflow.add_edge("router", route_query)
```

## C# Workflow Example

```csharp
using Microsoft.Agents.AI.Workflows;

var workflow = new GraphWorkflow();

// Add nodes
workflow.AddNode("researcher", researchAgent);
workflow.AddNode("writer", writerAgent);
workflow.AddNode("reviewer", reviewerAgent);

// Define edges
workflow.AddEdge("researcher", "writer");
workflow.AddEdge("writer", "reviewer");

// Conditional edge
workflow.AddConditionalEdge(
    "reviewer",
    state => state.GetValueOrDefault("approved", false),
    new Dictionary<bool, string>
    {
        { true, "END" },
        { false, "writer" }  // Revise
    }
);

workflow.SetEntryPoint("researcher");

// Execute
var result = await workflow.RunAsync(new Dictionary<string, object>
{
    { "topic", "AI trends" }
});
```

## Best Practices

1. **Keep nodes focused**: Each node should have one clear responsibility
2. **Manage state carefully**: Only include necessary data in state
3. **Set iteration limits**: Prevent infinite loops in conditional edges
4. **Use checkpointing**: For long-running workflows, enable checkpoints
5. **Error handling**: Add error recovery paths in workflows
6. **Monitor performance**: Use telemetry to track workflow execution times
7. **Test thoroughly**: Test all conditional paths and edge cases
8. **Document flow**: Add comments explaining complex routing logic

## Performance Optimization

```python
# Use parallel execution where possible
workflow.add_edge("START", ["worker1", "worker2", "worker3"])

# Batch operations
def batch_processor(state):
    items = state["items"]
    batch_size = 100
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        results.extend(process_batch(batch))
    return {"results": results}

# Cache intermediate results
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_operation(key):
    return compute_result(key)
```
