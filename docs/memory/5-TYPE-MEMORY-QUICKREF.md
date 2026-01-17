# 5-Type Memory System - Quick Reference

> [Home](../index.md) > [Memory System](./README.md) > Quick Reference

One-page cheat sheet for the 5-type memory system. Print this and keep it handy!

---

## Memory Types at a Glance

| Type            | What                        | When Stored       | Example                                   |
| --------------- | --------------------------- | ----------------- | ----------------------------------------- |
| **Episodic**    | Specific events & decisions | SessionStop       | "Decided to use Redis for sessions"       |
| **Semantic**    | Facts & concepts            | SessionStop       | "JWT contains header, payload, signature" |
| **Prospective** | TODOs & future work         | UserPromptSubmit  | "Add rate limiting to API"                |
| **Procedural**  | How-to workflows            | TodoWriteComplete | "Deploy: 1) Test, 2) Build, 3) Push"      |
| **Working**     | Active context              | UserPromptSubmit  | "Currently debugging auth flow"           |

---

## Quick Start

```python
from amplihack.memory import MemoryCoordinator

coordinator = MemoryCoordinator()

# Store a memory
coordinator.store(
    content="Use bcrypt for password hashing",
    memory_type="semantic"
)

# Retrieve memories
memories = coordinator.retrieve(
    query="password security",
    limit=5
)
```

---

## Common Queries

### Get Recent Decisions

```python
memories = coordinator.retrieve(
    query="architectural decisions",
    memory_types=["episodic"],
    limit=10
)
```

### Find Workflows

```python
memories = coordinator.retrieve(
    query="deployment process",
    memory_types=["procedural"],
    limit=5
)
```

### Check Pending TODOs

```python
todos = coordinator.retrieve(
    query="",  # Empty = all
    memory_types=["prospective"],
    limit=20
)
```

### Learn About Concepts

```python
concepts = coordinator.retrieve(
    query="JWT authentication",
    memory_types=["semantic"],
    limit=5
)
```

### Get Recent Context

```python
recent = coordinator.retrieve(
    query="last 7 days",
    since=datetime.now() - timedelta(days=7),
    limit=10
)
```

---

## Memory Type Decision Tree

```
What are you capturing?
│
├─ A specific decision or event?
│  └─> EPISODIC
│
├─ A fact or concept you learned?
│  └─> SEMANTIC
│
├─ Something to do in the future?
│  └─> PROSPECTIVE
│
├─ Steps to accomplish a task?
│  └─> PROCEDURAL
│
└─ Temporary context for current session?
   └─> WORKING
```

---

## Storage Parameters

```python
coordinator.store(
    content="...",              # REQUIRED: Memory content
    memory_type="episodic",     # REQUIRED: Type (see table above)
    metadata={                  # OPTIONAL: Additional data
        "priority": "high",
        "component": "auth"
    },
    context={                   # OPTIONAL: Contextual info
        "session_id": "...",
        "agent": "architect"
    }
)
```

---

## Retrieval Parameters

```python
coordinator.retrieve(
    query="...",                # Query text
    memory_types=["episodic"],  # Filter by type (default: all)
    limit=10,                   # Max results (default: 10)
    max_tokens=2000,            # Token budget (default: none)
    since=datetime(...),        # Only after date (default: all time)
    deduplicate=True,           # Remove similar (default: False)
    similarity_threshold=0.85   # Similarity % (default: 0.85)
)
```

---

## Hooks (Automatic Triggers)

| Hook                  | When              | What Happens                                        |
| --------------------- | ----------------- | --------------------------------------------------- |
| **UserPromptSubmit**  | You submit prompt | Extract prospective + working memory                |
| **TodoWriteComplete** | Task completes    | Capture procedural memory (if score >= 6)           |
| **SessionStop**       | Session ends      | Review for episodic + semantic, consolidate working |

---

## Multi-Agent Review Scoring

### Storage Review (3 agents)

```
Analyzer           → Scores technical importance (0-10)
Patterns           → Scores reusability as pattern (0-10)
Knowledge Arch.    → Scores long-term value (0-10)
                     ─────────────────────────────
                     Average >= 6.0 → STORE
```

### Retrieval Scoring (2 agents)

```
Analyzer           → Scores relevance to query (0.0-1.0)
Patterns           → Scores pattern match (0.0-1.0)
                     ──────────────────────────────
                     Average = Relevance Score
```

---

## Performance Targets

| Operation | Target | Actual (Avg)                     |
| --------- | ------ | -------------------------------- |
| Storage   | <50ms  | 2-3ms (DB) + 3-5s (agent review) |
| Retrieval | <50ms  | 5-10ms (search) + 1-2s (scoring) |
| Database  | <10MB  | ~1MB per 10,000 memories         |

---

## Common Patterns

### Pattern: Agent Uses Past Decisions

```python
class ArchitectAgent:
    def design(self, requirements):
        # Get relevant past decisions
        past = coordinator.retrieve(
            query=requirements,
            memory_types=["episodic"],
            limit=5
        )
        # Use for context
        return self.generate_design(requirements, past)
```

### Pattern: Session Start TODOs

```python
def on_session_start():
    todos = coordinator.retrieve(
        query="",
        memory_types=["prospective"],
        limit=10
    )
    print("Pending tasks:")
    for todo in todos:
        print(f"  - {todo.content}")
```

### Pattern: Time-Weighted Retrieval

```python
# Prefer recent memories
recent = coordinator.retrieve(
    query="authentication",
    since=datetime.now() - timedelta(days=7),
    limit=5
)
older = coordinator.retrieve(
    query="authentication",
    since=datetime.now() - timedelta(days=30),
    limit=5
)
combined = recent + older[:3]  # 5 recent + 3 older
```

---

## Troubleshooting

### Memory Not Stored

**Check**: Agent review scores

```python
result = coordinator.store(content, type)
print(f"Stored: {result.stored}")
print(f"Score: {result.consensus_score}")
print(f"Reason: {result.reason}")
```

**Solution**: Content might be trivial or scored too low (<6.0)

---

### Retrieval Too Slow

**Check**: Query is too broad or returning too many results

```python
# Add token budget
memories = coordinator.retrieve(
    query="...",
    max_tokens=1000,  # Strict limit
    limit=5
)
```

**Solution**: Use more specific queries, limit results

---

### Duplicate Memories

**Check**: Deduplication disabled

```python
memories = coordinator.retrieve(
    query="...",
    deduplicate=True,              # Enable
    similarity_threshold=0.85      # Adjust threshold
)
```

**Solution**: Enable deduplication with appropriate threshold

---

### Missing Context

**Check**: Query is too vague

```python
# BAD: Too vague
memories = coordinator.retrieve(query="auth")

# GOOD: Specific with context
memories = coordinator.retrieve(
    query="JWT authentication with Redis session storage",
    memory_types=["episodic", "semantic"]
)
```

**Solution**: Use specific queries with relevant memory types

---

## Configuration

### Database Location

Default: `~/.amplihack/memory.db`

Custom:

```python
coordinator = MemoryCoordinator(
    db_path="/path/to/custom/memory.db"
)
```

### Consensus Threshold

Default: 6.0 (out of 10)

Custom:

```python
coordinator.storage.consensus_threshold = 7.0  # More strict
```

### Token Budget Default

Default: None (unlimited)

Custom:

```python
# Set global default
coordinator.retrieval.default_max_tokens = 2000
```

---

## Example Workflows

### Workflow 1: Capture Decision

```python
# At SessionStop (automatic)
coordinator.store(
    content="Decided to use PostgreSQL over MongoDB for ACID guarantees",
    memory_type="episodic",
    metadata={"decision_type": "database", "component": "backend"}
)
```

### Workflow 2: Learn Concept

```python
# At SessionStop (automatic)
coordinator.store(
    content="ACID: Atomicity, Consistency, Isolation, Durability",
    memory_type="semantic",
    metadata={"category": "database", "importance": "high"}
)
```

### Workflow 3: Plan Future Work

```python
# At UserPromptSubmit (automatic)
coordinator.store(
    content="Add database migration for user preferences table",
    memory_type="prospective",
    metadata={"priority": "high", "component": "backend"}
)
```

### Workflow 4: Document Workflow

```python
# At TodoWriteComplete (automatic)
coordinator.store(
    content="Database migration: 1) Create migration file, 2) Write up/down, 3) Test locally, 4) Deploy to staging, 5) Deploy to prod",
    memory_type="procedural",
    metadata={"task_type": "migration", "success": True}
)
```

### Workflow 5: Track Active Context

```python
# At UserPromptSubmit (automatic)
coordinator.store(
    content="Debugging slow query in user dashboard analytics",
    memory_type="working",
    metadata={"session_id": "sess_123", "component": "analytics"}
)
```

---

## API Summary

### MemoryCoordinator Methods

| Method                   | Purpose        | Returns        |
| ------------------------ | -------------- | -------------- |
| `store()`                | Store memory   | `StoreResult`  |
| `retrieve()`             | Get memories   | `List[Memory]` |
| `stats()`                | Get statistics | `MemoryStats`  |
| `delete_memory()`        | Delete by ID   | `bool`         |
| `clear_working_memory()` | Clear session  | `int` (count)  |

### Memory Object

```python
memory.id              # str: Unique ID
memory.type            # MemoryType: Type enum
memory.content         # str: Memory content
memory.timestamp       # datetime: When stored
memory.token_count     # int: Token count
memory.metadata        # dict: Additional data
memory.context         # dict: Contextual info
memory.relevance_score # float: Relevance (if retrieved)
```

### StoreResult Object

```python
result.stored           # bool: Was stored?
result.memory_id        # str: Memory ID (if stored)
result.consensus_score  # float: Agent consensus (0-10)
result.reason           # str: Why stored/rejected
```

---

## Further Reading

- **User Guide**: [5-Type Memory Guide](./5-TYPE-MEMORY-GUIDE.md) - Complete usage guide
- **Developer Guide**: [Developer Guide](./5-TYPE-MEMORY-DEVELOPER.md) - Architecture and extension
- **Memory System**: [Memory README](./README.md) - All memory documentation

---

**Pro Tip**: Bookmark this page and use Ctrl+F to quickly find what you need!
