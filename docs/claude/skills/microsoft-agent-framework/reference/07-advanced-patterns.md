# Advanced Patterns & Techniques

## Multi-Agent Collaboration Patterns

### Debate Pattern

Multiple agents debate a topic and converge on a consensus:

```python
async def debate_pattern(topic: str, rounds: int = 3):
    """Multi-agent debate to reach consensus."""
    agents = {
        "optimist": Agent(model=model, instructions="Be optimistic"),
        "pessimist": Agent(model=model, instructions="Be critical"),
        "moderator": Agent(model=model, instructions="Synthesize viewpoints")
    }

    thread = Thread()
    positions = {}

    for round in range(rounds):
        # Each agent presents position
        for name, agent in [("optimist", agents["optimist"]), ("pessimist", agents["pessimist"])]:
            response = await agent.run(
                thread=thread,
                message=f"Round {round+1}: Discuss {topic}"
            )
            positions[name] = response.content

        # Moderator synthesizes
        synthesis = await agents["moderator"].run(
            thread=thread,
            message=f"Synthesize these positions: {positions}"
        )

    return synthesis.content
```

### Reflection Pattern

Agent reviews and improves its own output:

```python
async def reflection_pattern(task: str, iterations: int = 2):
    """Agent iteratively refines output."""
    generator = Agent(model=model, instructions="Generate content")
    critic = Agent(model=model, instructions="Critique and suggest improvements")

    output = await generator.run(message=task)

    for i in range(iterations):
        critique = await critic.run(message=f"Critique this: {output.content}")
        output = await generator.run(message=f"Improve based on: {critique.content}")

    return output.content
```

### Hierarchical Planning

Break down complex tasks into subtasks:

```python
async def hierarchical_planning(goal: str):
    """Decompose goal into plan and execute."""
    planner = Agent(model=model, instructions="Create detailed plans")
    executor = Agent(model=model, instructions="Execute tasks", tools=[...])

    # Plan phase
    plan = await planner.run(message=f"Create step-by-step plan for: {goal}")

    # Extract steps (assume structured output)
    steps = parse_plan(plan.content)

    # Execute phase
    results = []
    for step in steps:
        result = await executor.run(message=f"Execute: {step}")
        results.append(result.content)

    # Synthesize
    synthesis = await planner.run(message=f"Summarize results: {results}")
    return synthesis.content
```

## Streaming Patterns

### Progressive Response

Stream agent response as it's generated:

```python
async def stream_response(agent: Agent, message: str):
    """Display response incrementally."""
    print("Agent: ", end="", flush=True)

    async for chunk in agent.run_stream(message=message):
        print(chunk.delta, end="", flush=True)

    print()  # Newline at end
```

### Streaming Workflow

Stream updates from workflow execution:

```python
async def stream_workflow(workflow: GraphWorkflow, initial_state: dict):
    """Stream workflow progress."""
    async for event in workflow.run_stream(initial_state=initial_state):
        print(f"\n[{event.node_name}]")
        if event.output:
            print(event.output)
        if event.state_update:
            print(f"State: {event.state_update}")
```

### Real-Time Tool Results

Stream tool execution results:

```python
@function_tool
async def search_and_summarize(query: str) -> str:
    """Search and stream results."""
    results = []

    async for result in search_api(query):
        yield f"Found: {result.title}\n"
        results.append(result)

    summary = summarize(results)
    yield f"\nSummary: {summary}"
```

## RAG (Retrieval-Augmented Generation) Patterns

### Basic RAG

```python
from agents_framework import Agent, ContextProvider

class RAGAgent:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.agent = Agent(
            model=model,
            instructions="Answer based on provided context"
        )

    async def query(self, question: str):
        # Retrieve relevant documents
        docs = self.vector_store.search(question, top_k=5)

        # Build context
        context = "\n\n".join([f"Document {i+1}: {doc}" for i, doc in enumerate(docs)])

        # Query with context
        message = f"Context:\n{context}\n\nQuestion: {question}"
        response = await self.agent.run(message=message)

        return response.content
```

### Multi-Hop RAG

```python
async def multi_hop_rag(question: str, max_hops: int = 3):
    """Follow-up retrieval based on partial answers."""
    agent = Agent(model=model)
    all_docs = []

    for hop in range(max_hops):
        # Retrieve docs for current question
        docs = vector_store.search(question, top_k=3)
        all_docs.extend(docs)

        # Generate partial answer
        context = "\n".join(all_docs)
        response = await agent.run(message=f"Context: {context}\nQuestion: {question}")

        # Check if more info needed
        needs_more = await agent.run(message=f"Does this answer need more information? {response.content}")

        if "no" in needs_more.content.lower():
            break

        # Generate follow-up query
        follow_up = await agent.run(message=f"What follow-up question would help? {response.content}")
        question = follow_up.content

    return response.content
```

### Hybrid Search RAG

```python
async def hybrid_search_rag(question: str):
    """Combine keyword and semantic search."""
    # Keyword search
    keyword_results = bm25_search(question, top_k=5)

    # Semantic search
    semantic_results = vector_store.search(question, top_k=5)

    # Merge and deduplicate
    all_results = merge_results(keyword_results, semantic_results)

    # Rerank
    reranked = rerank_results(all_results, question)

    # Generate answer
    context = "\n\n".join([r.content for r in reranked[:5]])
    response = await agent.run(message=f"Context:\n{context}\n\nQuestion: {question}")

    return response.content
```

## Long-Running Operations

### Checkpointing Pattern

```python
from agents_framework import CheckpointManager

async def long_running_workflow(data: list, checkpoint_id: str):
    """Process large dataset with checkpointing."""
    checkpoint_mgr = CheckpointManager(storage_path="./checkpoints")

    # Try to resume
    state = checkpoint_mgr.load(checkpoint_id)
    if state:
        processed_items = state.get("processed_items", [])
        start_index = len(processed_items)
    else:
        processed_items = []
        start_index = 0

    for i, item in enumerate(data[start_index:], start=start_index):
        result = await process_item(item)
        processed_items.append(result)

        # Checkpoint every 10 items
        if i % 10 == 0:
            checkpoint_mgr.save(checkpoint_id, {
                "processed_items": processed_items,
                "current_index": i
            })

    return processed_items
```

### Background Task Pattern

```python
import asyncio
from typing import Dict

class BackgroundTaskManager:
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}

    async def start_task(self, task_id: str, agent: Agent, message: str):
        """Start long-running task in background."""
        task = asyncio.create_task(agent.run(message=message))
        self.tasks[task_id] = task
        return task_id

    async def get_status(self, task_id: str) -> str:
        """Check task status."""
        task = self.tasks.get(task_id)
        if not task:
            return "not_found"
        elif task.done():
            return "completed"
        else:
            return "running"

    async def get_result(self, task_id: str):
        """Get task result (blocks if not complete)."""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        return await task

# Usage
manager = BackgroundTaskManager()
task_id = await manager.start_task("job123", agent, "Long task")
# ... do other work ...
result = await manager.get_result("job123")
```

## Optimization Patterns

### Batching Pattern

```python
async def batch_processing(items: list, batch_size: int = 10):
    """Process items in batches."""
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]

        # Process batch in parallel
        batch_results = await asyncio.gather(*[
            agent.run(message=f"Process {item}")
            for item in batch
        ])

        results.extend(batch_results)

    return results
```

### Caching Pattern

```python
from functools import lru_cache
import hashlib

class CachedAgent:
    def __init__(self, agent: Agent):
        self.agent = agent
        self.cache = {}

    def _cache_key(self, message: str) -> str:
        return hashlib.md5(message.encode()).hexdigest()

    async def run(self, message: str, use_cache: bool = True):
        if use_cache:
            key = self._cache_key(message)
            if key in self.cache:
                return self.cache[key]

        response = await self.agent.run(message=message)

        if use_cache:
            self.cache[key] = response

        return response
```

### Load Balancing Pattern

```python
class LoadBalancedAgents:
    def __init__(self, agents: list[Agent]):
        self.agents = agents
        self.current = 0

    async def run(self, message: str):
        """Round-robin across agents."""
        agent = self.agents[self.current]
        self.current = (self.current + 1) % len(self.agents)
        return await agent.run(message=message)

# Usage
agents = [
    Agent(model=ModelClient(model="gpt-4")),
    Agent(model=ModelClient(model="gpt-4")),
    Agent(model=ModelClient(model="gpt-4"))
]
load_balancer = LoadBalancedAgents(agents)
```

## Error Recovery Patterns

### Retry with Exponential Backoff

```python
import asyncio

async def retry_with_backoff(agent: Agent, message: str, max_retries: int = 3):
    """Retry with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await agent.run(message=message)
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            wait_time = 2 ** attempt  # 1, 2, 4, 8...
            print(f"Attempt {attempt+1} failed, retrying in {wait_time}s")
            await asyncio.sleep(wait_time)
```

### Fallback Pattern

```python
async def fallback_pattern(message: str):
    """Try multiple approaches until one succeeds."""
    strategies = [
        ("gpt-4", "primary"),
        ("gpt-3.5-turbo", "fallback"),
        ("local-model", "local")
    ]

    for model_name, strategy in strategies:
        try:
            agent = Agent(model=ModelClient(model=model_name))
            return await agent.run(message=message)
        except Exception as e:
            print(f"{strategy} strategy failed: {e}")

    raise Exception("All strategies failed")
```

### Circuit Breaker Pattern

```python
from datetime import datetime, timedelta

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, agent: Agent, message: str):
        if self.state == "open":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            response = await agent.run(message=message)
            self.failures = 0
            self.state = "closed"
            return response
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.now()

            if self.failures >= self.failure_threshold:
                self.state = "open"

            raise
```

## Testing Patterns

### Mock Agent Pattern

```python
class MockAgent:
    def __init__(self, canned_responses: dict):
        self.responses = canned_responses

    async def run(self, message: str):
        from unittest.mock import Mock
        response = Mock()
        response.content = self.responses.get(message, "Mock response")
        response.usage = Mock(total_tokens=100)
        return response

# Usage in tests
async def test_workflow():
    mock_agent = MockAgent({
        "Research AI": "AI is advancing rapidly",
        "Summarize": "Summary here"
    })

    result = await workflow.run(agent=mock_agent)
    assert "Summary" in result
```

### Deterministic Testing

```python
# Use temperature=0 for deterministic outputs
test_agent = Agent(
    model=ModelClient(model="gpt-4", temperature=0),
    instructions="Be concise"
)

# Test with fixed inputs
response = await test_agent.run(message="What is 2+2?")
assert "4" in response.content
```

## Best Practices

1. **Use appropriate patterns**: Match pattern to problem (don't over-engineer)
2. **Monitor performance**: Track latency and costs for each pattern
3. **Test edge cases**: Especially for error recovery patterns
4. **Document patterns**: Explain when and why to use each pattern
5. **Combine patterns**: Many patterns work well together (e.g., caching + batching)
6. **Start simple**: Add complexity only when needed
