# 5-Type Memory System - API Design

Clean, minimal API contracts for intelligent agent memory following the brick & studs philosophy.

## Overview

The 5-Type Memory System provides intelligent memory storage and retrieval for AI agents based on psychological memory models:

1. **EPISODIC** - What happened when (events, conversations)
2. **SEMANTIC** - Important learnings (patterns, facts, best practices)
3. **PROSPECTIVE** - Future intentions (TODOs, reminders, follow-ups)
4. **PROCEDURAL** - How to do something (workflows, procedures)
5. **WORKING** - Active task details (temporary context)

## Design Philosophy

**Ruthlessly Simple**:

- Single responsibility per interface
- Minimal method signatures
- Standard library types only
- No unnecessary abstractions

**Performance Contracts**:

- Storage: <500ms (includes agent review)
- Retrieval: <50ms (without agent review)
- Smart Retrieval: <300ms (with relevance scoring)

**Brick & Studs**:

- Each interface is a stable "stud" (connection point)
- Implementation can be regenerated from specification
- Clear boundaries between components

## Architecture

```
MemoryCoordinator (Main Interface)
    │
    ├── StoragePipeline
    │   └── AgentReview (3 parallel agents)
    │       ├── analyzer
    │       ├── patterns
    │       └── knowledge-archaeologist
    │
    └── RetrievalPipeline
        └── AgentReview (2 parallel agents)
            ├── analyzer
            └── patterns

HookIntegration (Automatic Memory)
    ├── on_user_prompt → Inject memories
    ├── on_session_stop → Extract learnings
    └── on_task_complete → Extract learnings
```

## Core API

### MemoryCoordinator

**Primary interface for all memory operations.**

```python
from .api_contracts import MemoryCoordinator, StorageRequest, RetrievalQuery

coordinator = get_coordinator()

# Store memory
request = StorageRequest(
    content="REST APIs should use plural resource names",
    memory_type=MemoryType.SEMANTIC,
    agent_id="architect",
    importance=8
)
memory_id = coordinator.store(request)

# Retrieve memories
query = RetrievalQuery(
    memory_type=MemoryType.SEMANTIC,
    min_importance=7,
    limit=5
)
memories = coordinator.retrieve(query)

# Smart retrieval with relevance scoring
context = "Building authentication system"
relevant = coordinator.retrieve_with_review(query, context)
```

### Five Memory Types

#### 1. EPISODIC - What Happened When

Store conversation events, command executions, agent interactions.

```python
StorageRequest(
    content="User asked about authentication implementation",
    memory_type=MemoryType.EPISODIC,
    agent_id="orchestrator",
    metadata={
        "timestamp": datetime.now().isoformat(),
        "participants": ["user", "architect"],
        "topic": "authentication"
    }
)
```

**Use Cases**:

- Conversation history
- Command execution logs
- Agent interaction history
- Event timeline

**Query Example**: "What did we discuss about auth on Dec 1st?"

#### 2. SEMANTIC - Important Learnings

Store patterns, best practices, facts to remember.

```python
StorageRequest(
    content="REST APIs should use plural resource names",
    memory_type=MemoryType.SEMANTIC,
    agent_id="architect",
    importance=8,
    tags=["api-design", "best-practice"]
)
```

**Use Cases**:

- Design patterns
- Best practices
- Anti-patterns
- Domain knowledge

**Query Example**: "What have we learned about error handling?"

#### 3. PROSPECTIVE - Future Intentions

Store TODOs, reminders, follow-up tasks, deferred decisions.

```python
StorageRequest(
    content="TODO: Add rate limiting after MVP",
    memory_type=MemoryType.PROSPECTIVE,
    agent_id="architect",
    metadata={
        "trigger": "after_mvp",
        "deadline": "2026-02-01"
    },
    tags=["todo", "security"]
)
```

**Use Cases**:

- TODO tracking
- Follow-up reminders
- Deferred decisions
- Future improvements

**Query Example**: "What did we say we'd do after fixing the bug?"

#### 4. PROCEDURAL - How To Do Something

Store workflows, procedures, tool usage patterns.

```python
StorageRequest(
    content="""CI Failure Response:
1. Check error pattern
2. Apply template fix
3. Verify locally
4. Push fix""",
    memory_type=MemoryType.PROCEDURAL,
    agent_id="ci-diagnostic",
    importance=9,
    tags=["ci", "workflow"]
)
```

**Use Cases**:

- Workflow definitions
- Tool usage patterns
- Standard procedures
- Troubleshooting guides

**Query Example**: "How do we usually handle CI failures?"

#### 5. WORKING - Active Task Details

Store temporary context for current task (cleared after completion).

```python
StorageRequest(
    content="Implementing JWT auth + refresh flow",
    memory_type=MemoryType.WORKING,
    agent_id="builder",
    importance=5,
    metadata={
        "task_id": "auth-123",
        "current_step": "jwt_implementation"
    }
)

# Clear after task complete
coordinator.clear_working_memory()
```

**Use Cases**:

- Current task state
- Active dependencies
- Temporary debugging context
- In-progress decisions

**Lifecycle**: Clear after task completion

## Storage Pipeline

### Multi-Agent Quality Review

Storage includes automatic quality assessment by 3 parallel agents:

```
Content → [analyzer, patterns, knowledge-archaeologist]
         ↓
      ReviewResult (consensus)
         ↓
   Store if avg_score >4
```

**Review Agents**:

- **analyzer**: Evaluates content significance
- **patterns**: Checks for reusable patterns
- **knowledge-archaeologist**: Assesses long-term value

**Threshold**: Only store if average score >4/10

**Performance**: <400ms for parallel review

### Example

```python
request = StorageRequest(
    content="User prefers dark mode",
    memory_type=MemoryType.SEMANTIC,
    agent_id="ui-agent"
    # No importance specified - agents will score
)

memory_id = coordinator.store(request)

if memory_id:
    print("Stored (agents scored >4)")
else:
    print("Rejected (agents scored <4)")
```

## Retrieval Pipeline

### Two Modes

**Fast Mode** - No agent review:

```python
query = RetrievalQuery(memory_type=MemoryType.SEMANTIC)
memories = coordinator.retrieve(query)  # <50ms
```

**Smart Mode** - With relevance scoring:

```python
context = "Building authentication system"
relevant = coordinator.retrieve_with_review(query, context)  # <300ms
```

### Relevance Scoring

Smart retrieval uses 2 parallel agents to score relevance:

```
Memories + Context → [analyzer, patterns]
                    ↓
                ReviewResult
                    ↓
            Return if score >7
```

**Threshold**: Only return memories with relevance >7/10

**Performance**: <250ms for 10 memories

## Hook Integration

### Automatic Memory Capture

Memory operations triggered by hooks (no user commands needed):

```python
class HookIntegration:

    async def on_user_prompt(self, prompt: str, session_id: str):
        """Inject relevant memories before agent invocation."""
        query = RetrievalQuery(search_text=prompt, limit=5)
        context = f"User prompt: {prompt}"
        return coordinator.retrieve_with_review(query, context)

    async def on_session_stop(self, session_id: str):
        """Extract learnings at session end."""
        # Analyze session for learnings
        # Store important patterns/procedures
        pass

    async def on_task_complete(self, task_id: str, result: dict):
        """Extract learnings after task completion."""
        # Store procedure if successful
        # Store pattern if discovered
        pass
```

### Hook Points

1. **UserPromptSubmit**: Inject relevant memories before agent execution
2. **SessionStop**: Extract and store session learnings
3. **TaskCompletion**: Extract learnings from completed task

## Performance Contracts

All operations have explicit performance guarantees:

| Operation                | Target | Includes                       |
| ------------------------ | ------ | ------------------------------ |
| `store()`                | <500ms | Multi-agent review (3 agents)  |
| `retrieve()`             | <50ms  | Database query only            |
| `retrieve_with_review()` | <300ms | + Relevance scoring (2 agents) |
| `clear_working_memory()` | <50ms  | Batch delete                   |

**Parallel Execution**:

- Agent reviews run in parallel (not sequential)
- 3 agent review: ~400ms (not 1200ms)
- 2 agent review: ~250ms (not 500ms)

## Error Handling

### Graceful Degradation

All operations handle failures gracefully:

```python
try:
    memory_id = coordinator.store(request)
except MemoryError as e:
    print(f"Memory storage failed: {e}")
    memory_id = None

# Always check result
if memory_id:
    # Use memory
    pass
else:
    # Continue without memory
    pass
```

### Error Types

```python
MemoryError       # Base exception
StorageError      # Storage failed
RetrievalError    # Retrieval failed
ReviewError       # Agent review failed
```

## Implementation Guide

### 1. MemoryCoordinator

```python
class MemoryCoordinatorImpl:
    def __init__(self, storage_pipeline, retrieval_pipeline):
        self.storage = storage_pipeline
        self.retrieval = retrieval_pipeline

    def store(self, request: StorageRequest) -> str | None:
        return self.storage.process(request)

    def retrieve(self, query: RetrievalQuery) -> list[MemoryEntry]:
        return self.retrieval.query(query)
```

### 2. StoragePipeline

```python
class StoragePipelineImpl:
    def __init__(self, agent_review, database):
        self.review = agent_review
        self.db = database

    def process(self, request: StorageRequest) -> str | None:
        # Get importance score
        result = self.review.review_importance(
            request.content,
            request.memory_type
        )

        # Store if consensus >4
        if result.should_store:
            return self.db.store(request)
        return None
```

### 3. AgentReview

```python
class AgentReviewImpl:
    def review_importance(self, content, memory_type) -> ReviewResult:
        # Execute 3 agents in parallel
        agents = ["analyzer", "patterns", "knowledge-archaeologist"]

        scores = parallel_execute([
            (agent, score_importance, content, memory_type)
            for agent in agents
        ])

        avg_score = sum(s.score for s in scores) / len(scores)
        return ReviewResult(
            average_score=avg_score,
            should_store=avg_score > 4,
            individual_scores=scores
        )
```

## Testing

### Unit Tests

```python
def test_storage_with_review():
    request = StorageRequest(
        content="Test content",
        memory_type=MemoryType.SEMANTIC,
        agent_id="test"
    )

    memory_id = coordinator.store(request)
    assert memory_id is not None

def test_retrieval_performance():
    query = RetrievalQuery(limit=10)

    start = time.time()
    memories = coordinator.retrieve(query)
    duration = time.time() - start

    assert duration < 0.050  # 50ms contract
```

### Integration Tests

```python
def test_end_to_end_flow():
    # Store
    request = StorageRequest(...)
    memory_id = coordinator.store(request)

    # Retrieve
    query = RetrievalQuery(...)
    memories = coordinator.retrieve(query)

    assert any(m.id == memory_id for m in memories)
```

## Migration from Current System

### Current MemoryType → New MemoryType

```python
# Old system
MemoryType.CONVERSATION → MemoryType.EPISODIC
MemoryType.DECISION     → MemoryType.SEMANTIC
MemoryType.PATTERN      → MemoryType.SEMANTIC
MemoryType.CONTEXT      → MemoryType.WORKING
MemoryType.LEARNING     → MemoryType.SEMANTIC
MemoryType.ARTIFACT     → MemoryType.SEMANTIC
```

### Backward Compatibility

```python
def migrate_memory_type(old_type: str) -> MemoryType:
    mapping = {
        "conversation": MemoryType.EPISODIC,
        "decision": MemoryType.SEMANTIC,
        "pattern": MemoryType.SEMANTIC,
        "context": MemoryType.WORKING,
        "learning": MemoryType.SEMANTIC,
        "artifact": MemoryType.SEMANTIC,
    }
    return mapping.get(old_type, MemoryType.SEMANTIC)
```

## Next Steps

1. **Implement MemoryCoordinator** - Core interface
2. **Implement StoragePipeline** - With agent review
3. **Implement RetrievalPipeline** - Fast + smart modes
4. **Implement AgentReview** - Parallel agent execution
5. **Implement HookIntegration** - Automatic capture
6. **Add tests** - Unit + integration
7. **Performance testing** - Verify contracts
8. **Documentation** - Usage examples

## Files

- `api_contracts.py` - Interface definitions
- `api_examples.py` - Usage examples
- `README.md` - This file

## Questions?

Check the examples in `api_examples.py` for complete usage patterns.

See `api_contracts.py` for detailed interface specifications.

## Philosophy Compliance

✅ **Ruthless Simplicity** - Minimal interfaces, no unnecessary complexity
✅ **Brick & Studs** - Clear boundaries, regeneratable from spec
✅ **Zero-BS** - Every method works or doesn't exist
✅ **Performance** - Explicit contracts, no surprises
✅ **Modularity** - Single responsibility per interface
