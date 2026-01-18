# 5-Type Memory System Architecture

Clean, minimal architecture following the brick & studs philosophy.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      MemoryCoordinator                          │
│                    (Main Interface - "Stud")                    │
│                                                                 │
│  store(request) → <500ms with review                           │
│  retrieve(query) → <50ms without review                        │
│  retrieve_with_review(query, context) → <300ms                 │
│  delete(memory_id)                                             │
│  clear_working_memory()                                        │
└─────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌──────────────────────┐          ┌──────────────────────┐
│  StoragePipeline     │          │  RetrievalPipeline   │
│                      │          │                      │
│  process()           │          │  query()             │
│  review_importance() │          │  query_with_scoring()│
│                      │          │  score_relevance()   │
└──────────────────────┘          └──────────────────────┘
         │                                    │
         ▼                                    ▼
┌──────────────────────────────────────────────────────┐
│              AgentReview                             │
│         (Parallel Agent Executor)                    │
│                                                      │
│  Storage Review (3 agents, <400ms)                  │
│    ├─ analyzer                                      │
│    ├─ patterns                                      │
│    └─ knowledge-archaeologist                       │
│                                                      │
│  Retrieval Review (2 agents, <250ms)                │
│    ├─ analyzer                                      │
│    └─ patterns                                      │
└──────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│              SQLite Database                         │
│                                                      │
│  Tables:                                            │
│    • memory_entries (5 types)                       │
│    • sessions                                       │
│    • session_agents                                 │
│    • review_history                                 │
│                                                      │
│  Indexes: Optimized for <50ms queries              │
│  FTS5: Full-text search                            │
│  Views: Common query patterns                      │
└──────────────────────────────────────────────────────┘
```

## Hook Integration

```
┌──────────────────────────────────────────────────────────┐
│                  HookIntegration                         │
│               (Automatic Memory)                         │
└──────────────────────────────────────────────────────────┘
         │
         ├─── UserPromptSubmit Hook
         │    └─> Inject relevant memories (<300ms)
         │        ├─ Query by prompt keywords
         │        ├─ Score relevance (2 agents)
         │        └─ Return top 5 memories
         │
         ├─── SessionStop Hook
         │    └─> Extract learnings (<1000ms)
         │        ├─ Analyze session transcript
         │        ├─ Identify patterns/procedures
         │        └─ Store important learnings
         │
         └─── TaskCompletion Hook
              └─> Extract task learnings (<500ms)
                  ├─ Analyze task result
                  ├─ Extract procedure if successful
                  └─ Store for future reference
```

## Five Memory Types

```
┌─────────────────────────────────────────────────────────────┐
│                      Memory Types                           │
│                                                             │
│  1. EPISODIC ─────────────────────────────────────────┐   │
│     What happened when                                 │   │
│     • Conversations                                    │   │
│     • Command executions                               │   │
│     • Agent interactions                               │   │
│     • Event timeline                                   │   │
│     Example: "What did we discuss about auth?"        │   │
│                                                         │   │
│  2. SEMANTIC ─────────────────────────────────────────┐│   │
│     Important learnings                                ││   │
│     • Patterns discovered                              ││   │
│     • Best practices                                   ││   │
│     • Anti-patterns                                    ││   │
│     • Domain facts                                     ││   │
│     Example: "What did we learn about APIs?"          ││   │
│                                                         ││   │
│  3. PROSPECTIVE ─────────────────────────────────────┐││   │
│     Future intentions                                  │││   │
│     • TODOs                                            │││   │
│     • Reminders                                        │││   │
│     • Follow-up tasks                                  │││   │
│     • Deferred decisions                               │││   │
│     Example: "What should we do after MVP?"           │││   │
│                                                         │││   │
│  4. PROCEDURAL ──────────────────────────────────────┐│││   │
│     How to do something                                ││││   │
│     • Workflows learned                                ││││   │
│     • Tool usage patterns                              ││││   │
│     • Standard procedures                              ││││   │
│     • Troubleshooting guides                           ││││   │
│     Example: "How do we handle CI failures?"          ││││   │
│                                                         ││││   │
│  5. WORKING ─────────────────────────────────────────┐││││   │
│     Active task details (temporary)                    ││││   │
│     • Current task state                               ││││   │
│     • Active dependencies                              ││││   │
│     • Temporary context                                ││││   │
│     • In-progress decisions                            ││││   │
│     Lifecycle: Cleared after task completion          ││││   │
└─────────────────────────────────────────────────────────────┘
```

## Storage Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Storage Request                          │
│                                                             │
│  content: "REST APIs should use plural names"              │
│  memory_type: SEMANTIC                                     │
│  agent_id: "architect"                                     │
│  importance: 8 (or None for auto-scoring)                 │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               AgentReview.review_importance()               │
│                  (Parallel Execution)                       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  analyzer    │  │  patterns    │  │knowledge-    │   │
│  │              │  │              │  │archaeologist │   │
│  │  Score: 8    │  │  Score: 7    │  │  Score: 9    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                             │
│  Average Score: 8.0                                        │
│  Should Store: True (>4)                                   │
│                                                             │
│  Duration: ~400ms (parallel)                               │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                Store in Database                            │
│                                                             │
│  INSERT INTO memory_entries (...)                          │
│  INSERT INTO review_history (...)                          │
│                                                             │
│  Duration: ~50ms                                            │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Return Memory ID                            │
│                                                             │
│  Total Duration: <500ms                                     │
└─────────────────────────────────────────────────────────────┘
```

## Retrieval Pipeline Flow

### Fast Mode (No Agent Review)

```
┌─────────────────────────────────────────────────────────────┐
│                  Retrieval Query                            │
│                                                             │
│  memory_type: SEMANTIC                                     │
│  min_importance: 7                                         │
│  tags: ["api-design"]                                      │
│  limit: 5                                                  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               Query Database (Fast)                         │
│                                                             │
│  SELECT * FROM memory_entries                              │
│  WHERE memory_type = 'semantic'                            │
│    AND importance >= 7                                     │
│    AND tags LIKE '%"api-design"%'                          │
│  ORDER BY importance DESC                                  │
│  LIMIT 5;                                                  │
│                                                             │
│  Uses: idx_type_importance index                           │
│  Duration: <50ms                                            │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Return Memories                                │
│                                                             │
│  Total Duration: <50ms                                      │
└─────────────────────────────────────────────────────────────┘
```

### Smart Mode (With Relevance Scoring)

```
┌─────────────────────────────────────────────────────────────┐
│              Retrieval Query + Context                      │
│                                                             │
│  query: RetrievalQuery(...)                                │
│  context: "Building authentication with JWT"               │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          Query Database (Broad Query)                       │
│                                                             │
│  Retrieve 20 candidate memories                            │
│  Duration: <50ms                                            │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│        AgentReview.review_relevance()                       │
│           (Parallel Execution)                              │
│                                                             │
│  For each memory:                                          │
│  ┌──────────────┐      ┌──────────────┐                  │
│  │  analyzer    │      │  patterns    │                  │
│  │              │      │              │                  │
│  │  Score: 8    │      │  Score: 9    │                  │
│  └──────────────┘      └──────────────┘                  │
│                                                             │
│  Average Score: 8.5                                        │
│  Include: True (>7)                                        │
│                                                             │
│  Duration: ~250ms for 20 memories                          │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Filter by Relevance Score                           │
│                                                             │
│  Keep only memories with score >7                          │
│  Sort by score DESC                                        │
│  Return top results                                        │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            Return Relevant Memories                         │
│                                                             │
│  Total Duration: <300ms                                     │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

```
┌────────────────────────────────────────────────────────────┐
│                   memory_entries                           │
├────────────────────────────────────────────────────────────┤
│  id               TEXT PRIMARY KEY                         │
│  session_id       TEXT NOT NULL                            │
│  agent_id         TEXT NOT NULL                            │
│  memory_type      TEXT (episodic|semantic|prospective|    │
│                        procedural|working)                 │
│  title            TEXT NOT NULL                            │
│  content          TEXT NOT NULL                            │
│  metadata         TEXT (JSON)                              │
│  importance       INTEGER (1-10)                           │
│  tags             TEXT (JSON array)                        │
│  created_at       TEXT                                     │
│  accessed_at      TEXT                                     │
│  expires_at       TEXT (NULL for permanent)                │
│  parent_id        TEXT (for hierarchy)                     │
└────────────────────────────────────────────────────────────┘
                         │
                         │ Indexes (for <50ms queries):
                         ├─ idx_memory_type
                         ├─ idx_agent_id
                         ├─ idx_importance
                         ├─ idx_type_importance (compound)
                         ├─ idx_type_agent (compound)
                         └─ memory_fts (full-text search)

┌────────────────────────────────────────────────────────────┐
│                   review_history                           │
├────────────────────────────────────────────────────────────┤
│  id               TEXT PRIMARY KEY                         │
│  memory_id        TEXT (NULL if rejected)                  │
│  content_hash     TEXT (deduplication)                     │
│  memory_type      TEXT                                     │
│  average_score    REAL                                     │
│  should_store     BOOLEAN                                  │
│  agent_scores     TEXT (JSON array)                        │
│  reviewed_at      TEXT                                     │
│  review_duration_ms INTEGER                                │
└────────────────────────────────────────────────────────────┘
```

## Performance Characteristics

```
┌─────────────────────────────────────────────────────────────┐
│                  Performance Contracts                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Storage Pipeline:                                         │
│    ├─ Agent review (3 agents, parallel): ~400ms           │
│    ├─ Database insert: ~50ms                              │
│    └─ Total: <500ms ✓                                     │
│                                                             │
│  Fast Retrieval:                                           │
│    ├─ Database query (with indexes): <50ms ✓              │
│    └─ No agent review                                     │
│                                                             │
│  Smart Retrieval:                                          │
│    ├─ Database query: ~50ms                               │
│    ├─ Agent review (2 agents, parallel): ~250ms           │
│    └─ Total: <300ms ✓                                     │
│                                                             │
│  Working Memory Clear:                                     │
│    └─ Batch delete: <50ms ✓                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Module Structure (Brick & Studs)

```
.claude/specs/memory/
├── api_contracts.py         # Interface definitions (the "studs")
├── api_examples.py          # Usage examples
├── database_schema.sql      # Database contract
├── README.md               # Complete documentation
├── ARCHITECTURE.md         # This file
└── API_DESIGN_SUMMARY.md   # Summary for architect

Future implementation:
src/amplihack/memory/
├── coordinator.py           # MemoryCoordinator implementation
├── storage_pipeline.py      # StoragePipeline implementation
├── retrieval_pipeline.py    # RetrievalPipeline implementation
├── agent_review.py          # AgentReview implementation
├── hook_integration.py      # HookIntegration implementation
├── database.py             # Database backend
└── tests/
    ├── test_coordinator.py
    ├── test_storage.py
    ├── test_retrieval.py
    └── test_performance.py
```

## Key Design Decisions

### 1. Five Memory Types (Not Six)

**Psychology-based classification**:

- EPISODIC - Events (temporal)
- SEMANTIC - Knowledge (timeless)
- PROSPECTIVE - Intentions (future)
- PROCEDURAL - Skills (how-to)
- WORKING - Active context (temporary)

### 2. Two-Stage Review

**Storage Review** (3 agents, thorough):

- Only store valuable content (score >4)
- Prevent trivial content pollution

**Retrieval Review** (2 agents, fast):

- Only return relevant content (score >7)
- Respect token budget

### 3. Parallel Agent Execution

**Not Sequential**:

- 3 agents × 150ms = 450ms (sequential) ❌
- 3 agents in parallel = ~400ms ✓

**Implementation**: Use task parallelism

### 4. Working Memory Lifecycle

**Temporary by design**:

- Cleared after task completion
- Lower importance (≤5)
- Expires after 7 days if not cleared

### 5. SQLite-Only Initially

**Start simple**:

- SQLite meets all requirements
- Neo4j/Kùzu can be added later
- Don't build what you don't need yet

## Philosophy Compliance

✅ **Ruthless Simplicity**

- Five types (not twenty)
- Two modes (fast/smart)
- Clean interfaces

✅ **Brick & Studs**

- Clear boundaries
- Stable contracts
- Regeneratable

✅ **Zero-BS**

- Every method works
- Explicit contracts
- No placeholders

✅ **Performance First**

- Explicit guarantees
- Parallel execution
- Strategic indexing

Arr, the architecture be as clear as the Caribbean sea on a calm day!
