# 5-Type Memory System Test Suite

Ahoy! This be the comprehensive test suite fer the 5-type memory system (Issue #1902). All tests written followin' TDD methodology - they'll FAIL until ye implement the actual code!

## Test Organization

Tests follow the 60/30/10 testing pyramid:

- **60% Unit Tests**: Fast, isolated component testing
- **30% Integration Tests**: Multi-component coordination
- **10% E2E Tests**: Complete user-facing flows

## Test Files

### Unit Tests (60%)

#### `tests/unit/memory/test_memory_types.py`

Tests fer the 5 psychological memory types and classification.

**Coverage:**

- ✅ Memory type enums (Episodic, Semantic, Prospective, Procedural, Working)
- ✅ Type-specific schemas and validation
- ✅ Required fields fer each type
- ✅ Memory type classification logic
- ✅ Time-based queries (episodic)
- ✅ Confidence scoring (semantic)
- ✅ Trigger conditions (prospective)
- ✅ Usage tracking and strengthening (procedural)
- ✅ Task lifecycle and clearing (working)

**Key Test Scenarios:**

- Episodic memory requires timestamp and participants
- Semantic memory requires concept and confidence (0.0-1.0)
- Prospective memory requires task and trigger condition
- Procedural memory tracks usage count and strengthens with use
- Working memory clears when task completes
- Automatic classification based on content and context

#### `tests/unit/memory/test_trivial_filter.py`

Tests fer pre-filter logic that rejects low-value content.

**Coverage:**

- ✅ Simple greeting detection
- ✅ Successful command filtering
- ✅ Already-documented content detection
- ✅ Temporary debug output filtering
- ✅ Filter reasons and confidence
- ✅ Custom filter rules
- ✅ Filter statistics tracking
- ✅ Performance (<1ms per item)

**Key Test Scenarios:**

- "Hello" is trivial (simple greeting)
- "ls" with exit code 0 is trivial (successful simple command)
- Content matching docs is trivial (already documented)
- "DEBUG: x=42" is trivial (temporary debug)
- Complex commands are NOT trivial
- Failed commands are NOT trivial (learning opportunity)

#### `tests/unit/memory/test_token_budget.py`

Tests fer token budget enforcement in retrieval.

**Coverage:**

- ✅ Token counting fer different content types
- ✅ Budget allocation and tracking
- ✅ Weighted allocation by relevance
- ✅ Budget enforcement (never exceed)
- ✅ Allocation by memory type priority
- ✅ Utilization tracking and warnings
- ✅ Budget redistribution

**Key Test Scenarios:**

- Budget never exceeded (strict enforcement)
- Higher relevance memories get more tokens
- Recent memories prioritized when relevance equal
- Procedural/semantic get higher allocation
- Zero budget returns empty
- Warnings when approaching limit (90% threshold)

#### `tests/unit/memory/test_storage_pipeline.py`

Tests fer storage pipeline logic.

**Coverage:**

- ✅ StorageRequest validation
- ✅ Agent review scoring (1-10 scale)
- ✅ Quality gate thresholds (default 4.0)
- ✅ Parallel agent invocation
- ✅ Review aggregation and consensus
- ✅ Duplicate content detection
- ✅ Metadata preservation
- ✅ Performance (<500ms requirement)

**Key Test Scenarios:**

- Content above threshold (>4.0) stores successfully
- Content below threshold rejected
- 3 agents invoked in parallel (analyzer, patterns, knowledge-archaeologist)
- Parallel execution ~3x faster than sequential
- Agent failures handled gracefully
- Empty content rejected
- Duplicate content detected and rejected

#### `tests/unit/memory/test_retrieval_pipeline.py`

Tests fer retrieval pipeline logic.

**Coverage:**

- ✅ RetrievalQuery validation
- ✅ Relevance scoring (keyword + semantic)
- ✅ Token budget enforcement
- ✅ Memory type filtering
- ✅ Time range filtering
- ✅ Priority by relevance and recency
- ✅ Context formatting fer injection
- ✅ Performance (<50ms requirement)

**Key Test Scenarios:**

- Exact keyword match scores >0.8 relevance
- Semantic similarity beyond keywords
- Recent memories prioritized
- Procedural/semantic prioritized over episodic
- Zero budget returns empty
- Malformed memories skipped
- Deduplication of similar memories

### Integration Tests (30%)

#### `tests/integration/memory/test_storage_flow.py`

Tests complete storage flow from request to database.

**Coverage:**

- ✅ Request → Agent Review → Quality Gate → Database
- ✅ Trivial filter integration
- ✅ Metadata preservation through pipeline
- ✅ Agent review tracking
- ✅ Parallel vs sequential performance
- ✅ Error handling (agent timeout, DB errors)
- ✅ Multiple memories stored independently

**Key Test Scenarios:**

- High-quality content (avg score >4.0) stores successfully
- Low-quality content (avg score <4.0) rejected
- Trivial filter prevents agent invocation
- Metadata preserved in database
- Agent reviews tracked in metadata
- Parallel execution 2-3x faster than sequential
- Database errors handled gracefully

#### `tests/integration/memory/test_retrieval_flow.py`

Tests complete retrieval flow from query to context formatting.

**Coverage:**

- ✅ Query → Database Search → Relevance Scoring → Budget Enforcement → Formatting
- ✅ Memory type filtering
- ✅ Time range filtering
- ✅ Token budget enforcement
- ✅ Relevance prioritization
- ✅ Context formatting with type labels
- ✅ Performance requirements
- ✅ Error handling

**Key Test Scenarios:**

- Query "CI failures" returns procedural memory as top result
- Memory type filter respected (only returns requested types)
- Time range filter (only last 7 days)
- Token budget strictly enforced (never exceeded)
- Recent memories prioritized over old with same relevance
- Formatted context includes type labels
- Retrieval completes <50ms with 105 memories

#### `tests/integration/memory/test_agent_review.py`

Tests multi-agent review coordination.

**Coverage:**

- ✅ Parallel agent invocation (3 agents)
- ✅ Agent prompt content and context
- ✅ Consensus building from reviews
- ✅ Weighted consensus by confidence
- ✅ Disagreement tracking (variance)
- ✅ Error handling (timeout, failure, malformed)
- ✅ Statistics tracking
- ✅ Performance (<500ms requirement)

**Key Test Scenarios:**

- 3 agents invoked in parallel (analyzer, patterns, knowledge-archaeologist)
- Parallel 3x faster than sequential
- Agents receive content and context
- Consensus average calculated correctly
- Weighted consensus favors high-confidence reviews
- High disagreement = high variance
- Agent timeout handled gracefully
- Agent failure doesn't crash (partial results)

### E2E Tests (10%)

#### `tests/e2e/memory/test_memory_lifecycle.py`

Tests complete memory lifecycle: Store → Retrieve → Clear

**Coverage:**

- ✅ Complete lifecycle with real database
- ✅ Multiple memory types
- ✅ Time-based retrieval
- ✅ Working memory auto-clear on completion
- ✅ Persistence across coordinator instances
- ✅ Quality gate end-to-end
- ✅ Token budget end-to-end
- ✅ Statistics tracking
- ✅ Edge cases (empty, invalid, duplicate, very long)
- ✅ Performance requirements

**Key Test Scenarios:**

- Store → Retrieve → Clear → Verify empty
- Store all 5 memory types, retrieve by type filter
- Time-based retrieval (last 7 days only)
- Working memory cleared when task completes
- Memories persist when coordinator recreated (same DB)
- High-quality content (scores 8-9) stores successfully
- Low-quality content (scores 1-3) rejected
- Token budget strictly enforced
- Zero budget returns empty
- Duplicate content rejected
- Storage <500ms, Retrieval <50ms

#### `tests/e2e/memory/test_hook_integration.py`

Tests automatic memory operations via hooks.

**Coverage:**

- ✅ UserPromptSubmit hook (inject memories)
- ✅ SessionStop hook (extract learnings)
- ✅ TodoWriteComplete hook (extract learnings, clear working)
- ✅ Token budget in hooks
- ✅ Hook performance (<10% overhead)
- ✅ Error handling in hooks
- ✅ Hook configuration and registration

**Key Test Scenarios:**

- UserPromptSubmit injects relevant memories before agent
- Prompt "CI failures" injects procedural memory about CI
- Token budget respected in injection (≤500 tokens)
- Irrelevant prompt does not inject memories
- SessionStop extracts learnings from conversations
- SessionStop stores episodic memories
- Trivial sessions not stored
- TodoWriteComplete extracts procedural learnings
- TodoWriteComplete clears working memory when task completes
- TodoWriteComplete creates prospective memory fer follow-ups
- UserPromptSubmit adds <10% overhead
- SessionStop completes <1s even with 10 conversations
- Hooks handle DB errors without crashing
- Hooks can be disabled via configuration

## Running the Tests

**All tests will FAIL until implementation is complete!** This be TDD, matey! 🏴‍☠️

```bash
# Run all memory tests
pytest tests/unit/memory/ tests/integration/memory/ tests/e2e/memory/ -v

# Run only unit tests (fast)
pytest tests/unit/memory/ -v

# Run only integration tests
pytest tests/integration/memory/ -v

# Run only E2E tests
pytest tests/e2e/memory/ -v

# Run specific test file
pytest tests/unit/memory/test_memory_types.py -v

# Run with coverage
pytest tests/unit/memory/ tests/integration/memory/ tests/e2e/memory/ --cov=amplihack.memory --cov-report=html
```

## Test Pyramid Breakdown

```
Total Tests: ~200 tests

Unit Tests (60%):
- test_memory_types.py: ~40 tests
- test_trivial_filter.py: ~35 tests
- test_token_budget.py: ~30 tests
- test_storage_pipeline.py: ~25 tests
- test_retrieval_pipeline.py: ~30 tests

Integration Tests (30%):
- test_storage_flow.py: ~20 tests
- test_retrieval_flow.py: ~25 tests
- test_agent_review.py: ~15 tests

E2E Tests (10%):
- test_memory_lifecycle.py: ~15 tests
- test_hook_integration.py: ~15 tests
```

## Performance Requirements Tested

All tests validate the following performance requirements:

1. **Storage Pipeline**: <500ms (P95)
   - Tested in: `test_storage_pipeline.py`, `test_storage_flow.py`, `test_memory_lifecycle.py`

2. **Retrieval Pipeline**: <50ms (P95)
   - Tested in: `test_retrieval_pipeline.py`, `test_retrieval_flow.py`, `test_memory_lifecycle.py`

3. **Parallel Agent Review**: <500ms fer 3 agents
   - Tested in: `test_storage_pipeline.py`, `test_agent_review.py`

4. **Trivial Filter**: <1ms per item
   - Tested in: `test_trivial_filter.py`

5. **Hook Overhead**: <10% additional latency
   - Tested in: `test_hook_integration.py`

## Quality Requirements Tested

1. **Storage Quality Gate**: Average score >4.0/10 to store
   - Tested in: `test_storage_pipeline.py`, `test_storage_flow.py`

2. **Retrieval Relevance**: Minimum score >7.0/10 to inject
   - Tested in: `test_retrieval_pipeline.py`, `test_retrieval_flow.py`

3. **Token Budget**: Strict enforcement, never exceed
   - Tested in: `test_token_budget.py`, `test_retrieval_flow.py`, `test_memory_lifecycle.py`

4. **Trivial Filtering**: Pre-filter obvious low-value content
   - Tested in: `test_trivial_filter.py`, `test_storage_flow.py`

5. **Duplicate Detection**: Prevent storing duplicate content
   - Tested in: `test_storage_pipeline.py`, `test_memory_lifecycle.py`

## Success Criteria Coverage

From Issue #1902:

- ✅ **End-to-end memory flows automatically**: Tested in `test_hook_integration.py`
- ✅ **>90% stored memories rated valuable**: Tested via quality gate (threshold 4.0/10)
- ✅ **>80% recalled memories rated relevant**: Tested via retrieval threshold (7.0/10)
- ✅ **User can query memory decisions**: Tested via statistics tracking
- ✅ **<10% performance overhead**: Tested in performance tests
- ✅ **All 5 types working**: Tested in `test_memory_types.py`, `test_memory_lifecycle.py`

## API Contract Validation

All tests validate the following API contracts from api-designer:

```python
# MemoryCoordinator
await coordinator.store(request: StorageRequest) -> str | None
await coordinator.retrieve(query: RetrievalQuery) -> list[MemoryEntry]

# StoragePipeline
await pipeline.store_with_review(content, type, context) -> StorageResult

# RetrievalPipeline
await pipeline.retrieve_relevant(query, types, context, budget) -> RetrievalResult

# AgentReview
await review.review_importance(content, type, context) -> ReviewResult
```

## What's Next?

Once these tests are all PASSIN':

1. **Hook Integration**: Enable memory hooks in production
2. **Performance Tuning**: Optimize to meet <500ms/<50ms targets
3. **Dashboard**: Build memory inspection UI
4. **Analytics**: Track memory quality over time
5. **Cross-Session Learning**: Hierarchical memory fer shared learnings

## Notes

- All tests use mocked Task tool fer agent invocation (consistent, fast)
- Database operations use real SQLite (validates schemas)
- Time-based tests use relative dates (no flaky date assertions)
- Performance tests allow reasonable variance (20% tolerance)
- Error handling tests ensure graceful degradation

Happy testin', ye scallywag! 🏴‍☠️
