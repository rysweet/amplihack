# Handoff to Architect Agent - 5-Type Memory System

**From**: API Designer Agent
**To**: Architect Agent
**Date**: 2026-01-11
**Issue**: #1902

## What I've Done

Designed clean, minimal API contracts for the 5-type memory system. All interfaces follow the brick & studs philosophy with explicit performance contracts.

## Files Created

All files in `~/.amplihack/.claude/specs/memory/`:

1. **api_contracts.py** - Complete interface definitions
2. **api_examples.py** - 12 working examples
3. **database_schema.sql** - Database contract with indexes
4. **README.md** - Comprehensive documentation
5. **ARCHITECTURE.md** - Visual diagrams and flows
6. **API_DESIGN_SUMMARY.md** - Executive summary

## Core Interfaces

### 1. MemoryCoordinator (Main Interface)

```python
class MemoryCoordinator(Protocol):
    def store(request: StorageRequest) -> str | None
    def retrieve(query: RetrievalQuery) -> list[MemoryEntry]
    def retrieve_with_review(query, context) -> list[MemoryEntry]
    def delete(memory_id: str) -> bool
    def clear_working_memory() -> int
```

### 2. StoragePipeline

```python
class StoragePipeline(Protocol):
    def process(request: StorageRequest) -> str | None
    def review_importance(content, memory_type) -> ReviewResult
```

### 3. RetrievalPipeline

```python
class RetrievalPipeline(Protocol):
    def query(query: RetrievalQuery) -> list[MemoryEntry]
    def query_with_scoring(query, context) -> list[MemoryEntry]
    def score_relevance(memories, context) -> dict[str, float]
```

### 4. AgentReview

```python
class AgentReview(Protocol):
    def review_importance(content, memory_type) -> ReviewResult
    def review_relevance(memories, context) -> dict[str, ReviewResult]
```

### 5. HookIntegration

```python
class HookIntegration(Protocol):
    async def on_user_prompt(prompt, session_id) -> list[MemoryEntry]
    async def on_session_stop(session_id) -> int
    async def on_task_complete(task_id, result) -> str | None
```

## Five Memory Types

1. **EPISODIC** - What happened when (conversations, events)
2. **SEMANTIC** - Important learnings (patterns, facts)
3. **PROSPECTIVE** - Future intentions (TODOs, reminders)
4. **PROCEDURAL** - How to do something (workflows)
5. **WORKING** - Active task details (temporary)

## Performance Contracts

| Operation              | Target | Notes                   |
| ---------------------- | ------ | ----------------------- |
| store()                | <500ms | Includes 3-agent review |
| retrieve()             | <50ms  | Database only           |
| retrieve_with_review() | <300ms | Includes 2-agent review |
| clear_working_memory() | <50ms  | Batch delete            |

## Multi-Agent Review

### Storage Review (3 agents)

- analyzer
- patterns
- knowledge-archaeologist
- Threshold: Store if avg score >4

### Retrieval Review (2 agents)

- analyzer
- patterns
- Threshold: Return if score >7

## What You Need to Do

### 1. Module Specification

Create detailed specs for each module:

**Module**: `memory.coordinator`

- **Purpose**: Main interface implementation
- **Dependencies**: storage_pipeline, retrieval_pipeline
- **Public API**: Implements MemoryCoordinator protocol
- **Contract**: Performance guarantees maintained

**Module**: `memory.storage_pipeline`

- **Purpose**: Storage with agent review
- **Dependencies**: agent_review, database
- **Public API**: Implements StoragePipeline protocol
- **Contract**: <500ms total time

**Module**: `memory.retrieval_pipeline`

- **Purpose**: Fast + smart retrieval
- **Dependencies**: agent_review, database
- **Public API**: Implements RetrievalPipeline protocol
- **Contract**: <50ms fast, <300ms smart

**Module**: `memory.agent_review`

- **Purpose**: Parallel agent execution
- **Dependencies**: Task tool for agents
- **Public API**: Implements AgentReview protocol
- **Contract**: Parallel execution, not sequential

**Module**: `memory.hook_integration`

- **Purpose**: Automatic memory capture
- **Dependencies**: coordinator, hooks system
- **Public API**: Implements HookIntegration protocol
- **Contract**: Async operations, non-blocking

### 2. Database Schema

The schema is ready in `database_schema.sql`:

- Review table structure
- Validate indexes for performance
- Plan migration from current schema
- Ensure <50ms query performance

### 3. Agent Integration

Plan how to invoke agents in parallel:

- Use existing Task tool
- Execute 3 storage agents in parallel (~400ms)
- Execute 2 retrieval agents in parallel (~250ms)
- Handle agent failures gracefully

### 4. Hook Integration

Design hook integration:

- UserPromptSubmit: When to inject memories
- SessionStop: How to extract learnings
- TaskCompletion: What to capture
- Performance impact on workflows

### 5. Error Handling

Design error handling strategy:

- Graceful degradation (continue without memory)
- Error types (StorageError, RetrievalError, ReviewError)
- Retry logic for transient failures
- Logging for debugging

### 6. Testing Strategy

Plan test coverage:

- Unit tests for each module
- Integration tests for flows
- Performance tests for contracts
- Error handling tests

## Key Design Decisions

1. **SQLite-only initially** - Add graph DBs later if needed
2. **Parallel agent execution** - Critical for performance
3. **Two-stage review** - Storage (thorough) + Retrieval (fast)
4. **Working memory lifecycle** - Clear after task completion
5. **Protocol-based interfaces** - Easy to regenerate/replace

## Philosophy Compliance

✅ **Ruthless Simplicity** - Five types, not twenty
✅ **Brick & Studs** - Clear interfaces, stable contracts
✅ **Zero-BS** - Every method works, no stubs
✅ **Performance First** - Explicit guarantees
✅ **Modular Design** - Single responsibility

## Questions to Answer

1. **Parallel Execution**: How to execute multiple agents in parallel using Task tool?
2. **Hook Timing**: When exactly to inject memories (before prompt, after prompt)?
3. **Session Management**: How to track session lifecycle for automatic capture?
4. **Error Recovery**: What to do if agent review fails (store anyway? reject? retry)?
5. **Token Budget**: How to manage token budget for memory injection?

## Next Steps

1. Review API contracts and examples
2. Create module specifications following brick pattern
3. Design agent invocation strategy
4. Plan hook integration points
5. Design error handling and retry logic
6. Create test specifications
7. Document module boundaries
8. Hand off to Builder agent

## Notes

- All interfaces use Protocol pattern (not abstract base classes)
- Standard library types only in signatures
- Performance contracts are mandatory, not aspirational
- Agent reviews run in parallel, not sequential
- Working memory is temporary by design

## Files to Read

1. Start with `README.md` - Complete documentation
2. Review `api_contracts.py` - Interface specifications
3. Check `api_examples.py` - Usage patterns
4. Study `ARCHITECTURE.md` - System design
5. Review `database_schema.sql` - Database contract

Arr, the API map be complete! Now ye architects need to chart the implementation course and hand off to the builders. Fair winds!

🏴‍☠️
