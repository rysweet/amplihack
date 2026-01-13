# 5-Type Memory System - Developer Guide

> [Home](../index.md) > [Memory System](./README.md) > Developer Guide

This developer guide explains the architecture, implementation, and extension points of the 5-type memory system.

## Contents

- [Architecture Overview](#architecture-overview)
- [Module Structure](#module-structure)
- [Core Components](#core-components)
- [Hook Integration](#hook-integration)
- [Extending the System](#extending-the-system)
- [API Reference](#api-reference)
- [Integration Patterns](#integration-patterns)

---

## Architecture Overview

### System Layers

```
┌─────────────────────────────────────────────────────┐
│                 Claude Code Hooks                    │
│  (UserPromptSubmit, TodoWriteComplete, SessionStop) │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│              Memory Coordinator                      │
│         (Orchestrates storage/retrieval)             │
└────────┬───────────────────────────┬────────────────┘
         │                           │
         ▼                           ▼
┌────────────────────┐    ┌──────────────────────────┐
│  Storage Pipeline  │    │   Retrieval Pipeline     │
│  - Extract memory  │    │   - Score relevance      │
│  - Agent review    │    │   - Token budget         │
│  - Consensus score │    │   - Deduplication        │
└────────┬───────────┘    └───────────┬──────────────┘
         │                            │
         └──────────┬─────────────────┘
                    ▼
         ┌─────────────────────┐
         │   SQLite Backend    │
         │  ~/.amplihack/      │
         │    memory.db        │
         └─────────────────────┘
```

### Data Flow

**Storage Flow**:
1. Hook triggers (UserPromptSubmit, TodoWriteComplete, SessionStop)
2. MemoryCoordinator.store() called with content + type
3. StoragePipeline extracts structured memory
4. AgentReview runs 3 agents in parallel
5. Consensus score calculated (average >= 6.0)
6. If approved, memory written to SQLite
7. Background operation (<50ms total)

**Retrieval Flow**:
1. User query or agent request
2. MemoryCoordinator.retrieve() called with query + filters
3. RetrievalPipeline searches SQLite (indexed search)
4. AgentReview scores relevance (2 agents: analyzer, patterns)
5. Results ranked by relevance score
6. Token budget enforced (trim if needed)
7. Deduplication applied if enabled
8. Return ordered list of memories

---

## Module Structure

```
.claude/tools/amplihack/memory/
├── __init__.py              # Public API exports
├── coordinator.py           # MemoryCoordinator (main interface)
├── storage_pipeline.py      # StoragePipeline (storage logic)
├── retrieval_pipeline.py    # RetrievalPipeline (retrieval logic)
├── agent_review.py          # AgentReview (multi-agent consensus)
├── memory_types.py          # MemoryType enum and schemas
├── sqlite_backend.py        # SQLiteBackend (database operations)
├── trivial_filter.py        # TrivialFilter (pre-filtering)
└── tests/
    ├── test_coordinator.py
    ├── test_storage.py
    ├── test_retrieval.py
    └── test_agent_review.py

.claude/tools/amplihack/hooks/
├── memory_prompt_hook.py    # UserPromptSubmit hook
├── memory_todo_hook.py      # TodoWriteComplete hook
└── memory_session_hook.py   # SessionStop hook
```

### Module Boundaries

Each module is a self-contained "brick" following amplihack philosophy:

- **Coordinator**: Public API, orchestrates pipelines
- **StoragePipeline**: Extract + review + store logic
- **RetrievalPipeline**: Search + score + rank logic
- **AgentReview**: Multi-agent consensus scoring
- **SQLiteBackend**: Database operations only
- **Hooks**: Integration with Claude Code events

---

## Core Components

### MemoryCoordinator

**Purpose**: Main interface for storing and retrieving memories

**Public API**:
```python
from amplihack.memory import MemoryCoordinator

coordinator = MemoryCoordinator()

# Store memory
result = coordinator.store(
    content="Decided to use Redis for sessions",
    memory_type="episodic",
    metadata={"component": "authentication"}
)

# Retrieve memories
memories = coordinator.retrieve(
    query="authentication decisions",
    memory_types=["episodic", "semantic"],
    limit=10,
    max_tokens=2000
)

# Get statistics
stats = coordinator.stats()
print(f"Total memories: {stats.total_count}")
print(f"By type: {stats.by_type}")
```

**Implementation**:
```python
# coordinator.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from .storage_pipeline import StoragePipeline
from .retrieval_pipeline import RetrievalPipeline
from .memory_types import MemoryType, Memory

@dataclass
class StoreResult:
    stored: bool
    memory_id: Optional[str]
    consensus_score: float
    reason: str

class MemoryCoordinator:
    """Main interface for 5-type memory system"""

    def __init__(self, db_path: Optional[str] = None):
        self.storage = StoragePipeline(db_path)
        self.retrieval = RetrievalPipeline(db_path)

    def store(
        self,
        content: str,
        memory_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> StoreResult:
        """Store memory with multi-agent review"""
        return self.storage.store(content, memory_type, metadata, context)

    def retrieve(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
        max_tokens: Optional[int] = None,
        since: Optional[datetime] = None,
        deduplicate: bool = False,
        similarity_threshold: float = 0.85
    ) -> List[Memory]:
        """Retrieve relevant memories"""
        return self.retrieval.retrieve(
            query=query,
            memory_types=memory_types,
            limit=limit,
            max_tokens=max_tokens,
            since=since,
            deduplicate=deduplicate,
            similarity_threshold=similarity_threshold
        )
```

### StoragePipeline

**Purpose**: Extract, review, and store memories with consensus

**Key Methods**:
```python
# storage_pipeline.py
from .agent_review import AgentReview
from .trivial_filter import TrivialFilter
from .sqlite_backend import SQLiteBackend
from .memory_types import MemoryType, Memory

class StoragePipeline:
    """Storage pipeline with multi-agent review"""

    def __init__(self, db_path: Optional[str] = None):
        self.agent_review = AgentReview()
        self.trivial_filter = TrivialFilter()
        self.backend = SQLiteBackend(db_path)
        self.consensus_threshold = 6.0

    def store(
        self,
        content: str,
        memory_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> StoreResult:
        """Store memory with multi-agent review"""

        # Pre-filter trivial content
        if self.trivial_filter.is_trivial(content):
            return StoreResult(
                stored=False,
                memory_id=None,
                consensus_score=0.0,
                reason="Trivial content filtered"
            )

        # Extract structured memory
        memory = self._extract_memory(content, memory_type, metadata, context)

        # Multi-agent review
        review_result = self.agent_review.review_storage(memory)

        # Check consensus threshold
        if review_result.consensus_score < self.consensus_threshold:
            return StoreResult(
                stored=False,
                memory_id=None,
                consensus_score=review_result.consensus_score,
                reason=f"Below threshold: {review_result.agent_scores}"
            )

        # Store in database
        memory_id = self.backend.insert_memory(memory)

        return StoreResult(
            stored=True,
            memory_id=memory_id,
            consensus_score=review_result.consensus_score,
            reason="Stored successfully"
        )

    def _extract_memory(
        self,
        content: str,
        memory_type: str,
        metadata: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> Memory:
        """Extract structured memory from raw content"""
        # Implementation: Parse content, extract keywords, classify
        pass
```

### RetrievalPipeline

**Purpose**: Search, score, and rank memories by relevance

**Key Methods**:
```python
# retrieval_pipeline.py
from typing import List, Optional
from datetime import datetime
from .agent_review import AgentReview
from .sqlite_backend import SQLiteBackend
from .memory_types import Memory

class RetrievalPipeline:
    """Retrieval pipeline with relevance scoring"""

    def __init__(self, db_path: Optional[str] = None):
        self.agent_review = AgentReview()
        self.backend = SQLiteBackend(db_path)

    def retrieve(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
        max_tokens: Optional[int] = None,
        since: Optional[datetime] = None,
        deduplicate: bool = False,
        similarity_threshold: float = 0.85
    ) -> List[Memory]:
        """Retrieve relevant memories"""

        # Search database (indexed FTS5 search)
        candidates = self.backend.search_memories(
            query=query,
            memory_types=memory_types,
            since=since,
            limit=limit * 3  # Get more candidates for scoring
        )

        # Score relevance with agents
        scored_memories = []
        for memory in candidates:
            score = self.agent_review.score_relevance(memory, query)
            scored_memories.append((memory, score))

        # Sort by relevance score (descending)
        scored_memories.sort(key=lambda x: x[1], reverse=True)

        # Apply limit
        results = [m for m, _ in scored_memories[:limit]]

        # Enforce token budget if specified
        if max_tokens:
            results = self._enforce_token_budget(results, max_tokens)

        # Deduplicate if enabled
        if deduplicate:
            results = self._deduplicate(results, similarity_threshold)

        return results

    def _enforce_token_budget(
        self,
        memories: List[Memory],
        max_tokens: int
    ) -> List[Memory]:
        """Trim memories to fit within token budget"""
        total_tokens = 0
        filtered = []
        for memory in memories:
            if total_tokens + memory.token_count <= max_tokens:
                filtered.append(memory)
                total_tokens += memory.token_count
            else:
                break
        return filtered
```

### AgentReview

**Purpose**: Multi-agent consensus scoring for storage and retrieval

**Key Methods**:
```python
# agent_review.py
from dataclasses import dataclass
from typing import Dict, List
from .memory_types import Memory

@dataclass
class ReviewResult:
    consensus_score: float
    agent_scores: Dict[str, float]
    reasons: Dict[str, str]

class AgentReview:
    """Multi-agent consensus review"""

    STORAGE_AGENTS = ["analyzer", "patterns", "knowledge-archaeologist"]
    RETRIEVAL_AGENTS = ["analyzer", "patterns"]

    def review_storage(self, memory: Memory) -> ReviewResult:
        """Review memory for storage (3 agents)"""
        scores = {}
        reasons = {}

        # Run agents in parallel
        for agent_type in self.STORAGE_AGENTS:
            score, reason = self._score_storage(memory, agent_type)
            scores[agent_type] = score
            reasons[agent_type] = reason

        # Calculate consensus (average)
        consensus = sum(scores.values()) / len(scores)

        return ReviewResult(
            consensus_score=consensus,
            agent_scores=scores,
            reasons=reasons
        )

    def score_relevance(self, memory: Memory, query: str) -> float:
        """Score memory relevance to query (2 agents)"""
        scores = []

        for agent_type in self.RETRIEVAL_AGENTS:
            score = self._score_relevance(memory, query, agent_type)
            scores.append(score)

        # Return average relevance score
        return sum(scores) / len(scores)

    def _score_storage(self, memory: Memory, agent_type: str) -> tuple[float, str]:
        """Score memory importance for storage (0-10)"""
        # Implementation: Invoke agent with scoring prompt
        pass

    def _score_relevance(self, memory: Memory, query: str, agent_type: str) -> float:
        """Score memory relevance to query (0.0-1.0)"""
        # Implementation: Invoke agent with relevance prompt
        pass
```

---

## Hook Integration

### Hook Architecture

Hooks trigger automatically at specific Claude Code events:

```python
# memory_prompt_hook.py
from amplihack.memory import MemoryCoordinator

def on_user_prompt_submit(prompt: str, context: dict) -> None:
    """Hook: UserPromptSubmit - Extract prospective memories"""
    coordinator = MemoryCoordinator()

    # Extract TODOs and future intentions
    if any(keyword in prompt.lower() for keyword in ["todo", "later", "need to", "plan to"]):
        coordinator.store(
            content=prompt,
            memory_type="prospective",
            metadata={"priority": _extract_priority(prompt)},
            context=context
        )

    # Store in working memory for active context
    coordinator.store(
        content=prompt,
        memory_type="working",
        metadata={"session_id": context.get("session_id")},
        context=context
    )
```

```python
# memory_todo_hook.py
def on_todo_write_complete(todo_item: dict, context: dict) -> None:
    """Hook: TodoWriteComplete - Capture procedural memory"""
    coordinator = MemoryCoordinator()

    if todo_item["status"] == "completed":
        # Extract workflow steps
        workflow = _extract_workflow(todo_item)

        coordinator.store(
            content=workflow,
            memory_type="procedural",
            metadata={
                "task_type": todo_item.get("task_type"),
                "success": True,
                "duration_minutes": todo_item.get("duration")
            },
            context=context
        )
```

```python
# memory_session_hook.py
def on_session_stop(session_data: dict) -> None:
    """Hook: SessionStop - Review session for episodic/semantic memories"""
    coordinator = MemoryCoordinator()

    # Extract significant events (episodic)
    for event in _extract_significant_events(session_data):
        coordinator.store(
            content=event["description"],
            memory_type="episodic",
            metadata={"decision_type": event["type"]},
            context=session_data
        )

    # Extract learned concepts (semantic)
    for concept in _extract_concepts(session_data):
        coordinator.store(
            content=concept["description"],
            memory_type="semantic",
            metadata={"category": concept["category"]},
            context=session_data
        )

    # Consolidate working memory
    _consolidate_working_memory(coordinator, session_data)
```

---

## Extending the System

### Adding a New Memory Type

**Step 1**: Define the memory type

```python
# memory_types.py
from enum import Enum

class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROSPECTIVE = "prospective"
    PROCEDURAL = "procedural"
    WORKING = "working"
    # NEW: Add your type
    SOCIAL = "social"  # Example: social interactions and relationships
```

**Step 2**: Add extraction logic

```python
# storage_pipeline.py
def _extract_memory(self, content: str, memory_type: str, ...) -> Memory:
    if memory_type == MemoryType.SOCIAL:
        return self._extract_social_memory(content, metadata, context)
    # ... existing types
```

**Step 3**: Add retrieval scoring

```python
# agent_review.py
def _score_storage(self, memory: Memory, agent_type: str) -> tuple[float, str]:
    if memory.type == MemoryType.SOCIAL:
        # Custom scoring logic for social memories
        return self._score_social_memory(memory, agent_type)
```

**Step 4**: Update documentation

Add your new type to the user guide and quick reference.

### Adding a New Review Agent

**Step 1**: Define agent in AgentReview

```python
# agent_review.py
class AgentReview:
    STORAGE_AGENTS = [
        "analyzer",
        "patterns",
        "knowledge-archaeologist",
        "security"  # NEW: Add security reviewer
    ]
```

**Step 2**: Implement scoring logic

```python
def _score_storage(self, memory: Memory, agent_type: str) -> tuple[float, str]:
    if agent_type == "security":
        return self._score_security(memory)
    # ... existing agents

def _score_security(self, memory: Memory) -> tuple[float, str]:
    """Score security relevance of memory"""
    security_keywords = ["auth", "password", "token", "encryption", "vulnerability"]

    score = 5.0  # Base score
    if any(kw in memory.content.lower() for kw in security_keywords):
        score += 3.0

    reason = f"Security relevance score based on keywords"
    return score, reason
```

### Custom Retrieval Strategies

**Example**: Time-weighted retrieval (recent memories preferred)

```python
# custom_retrieval.py
from datetime import datetime, timedelta
from amplihack.memory import MemoryCoordinator

class TimeWeightedRetrieval:
    """Retrieval strategy favoring recent memories"""

    def __init__(self):
        self.coordinator = MemoryCoordinator()

    def retrieve_time_weighted(
        self,
        query: str,
        recency_weight: float = 0.3,
        limit: int = 10
    ):
        """Retrieve with time-weighted scoring"""

        # Get candidates
        memories = self.coordinator.retrieve(
            query=query,
            limit=limit * 2  # Get more for re-ranking
        )

        # Re-score with time weighting
        now = datetime.now()
        scored = []
        for memory in memories:
            age_days = (now - memory.timestamp).days
            recency_score = 1.0 / (1.0 + age_days * 0.1)

            # Combine relevance + recency
            final_score = (
                memory.relevance_score * (1 - recency_weight) +
                recency_score * recency_weight
            )
            scored.append((memory, final_score))

        # Sort and return top N
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:limit]]
```

---

## API Reference

### MemoryCoordinator

**Constructor**:
```python
MemoryCoordinator(db_path: Optional[str] = None)
```

**Methods**:

```python
store(
    content: str,
    memory_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None
) -> StoreResult
```
Store memory with multi-agent review.

```python
retrieve(
    query: str,
    memory_types: Optional[List[str]] = None,
    limit: int = 10,
    max_tokens: Optional[int] = None,
    since: Optional[datetime] = None,
    deduplicate: bool = False,
    similarity_threshold: float = 0.85
) -> List[Memory]
```
Retrieve relevant memories with scoring.

```python
stats() -> MemoryStats
```
Get memory system statistics.

```python
delete_memory(memory_id: str) -> bool
```
Delete specific memory by ID.

```python
clear_working_memory(session_id: str) -> int
```
Clear working memory for session (returns count deleted).

### Memory Data Class

```python
@dataclass
class Memory:
    id: str
    type: MemoryType
    content: str
    timestamp: datetime
    token_count: int
    metadata: Dict[str, Any]
    context: Dict[str, Any]
    relevance_score: Optional[float] = None
```

### StoreResult Data Class

```python
@dataclass
class StoreResult:
    stored: bool
    memory_id: Optional[str]
    consensus_score: float
    reason: str
```

---

## Integration Patterns

### Pattern 1: Background Storage in Agent

```python
# In specialized agent
from amplihack.memory import MemoryCoordinator

class BuilderAgent:
    def __init__(self):
        self.memory = MemoryCoordinator()

    def implement_feature(self, spec: dict):
        # ... implementation logic ...

        # Store procedural memory in background
        self.memory.store(
            content=f"Implemented {spec['name']}: {self._extract_steps()}",
            memory_type="procedural",
            metadata={"feature": spec["name"], "success": True}
        )
```

### Pattern 2: Context-Aware Retrieval

```python
# Retrieve memories relevant to current task
class ArchitectAgent:
    def design_solution(self, requirements: str):
        # Get relevant past decisions
        past_decisions = self.memory.retrieve(
            query=requirements,
            memory_types=["episodic", "semantic"],
            limit=5,
            max_tokens=1000
        )

        # Use past decisions to inform design
        context = "\n".join([m.content for m in past_decisions])
        design = self._generate_design(requirements, context)

        return design
```

### Pattern 3: Prospective Memory Reminders

```python
# Check for pending TODOs at session start
def on_session_start():
    coordinator = MemoryCoordinator()

    pending_todos = coordinator.retrieve(
        query="",  # Empty query to get all
        memory_types=["prospective"],
        limit=10
    )

    if pending_todos:
        print("Arrr! Ye have pending tasks, matey:")
        for todo in pending_todos:
            priority = todo.metadata.get("priority", "medium")
            print(f"  [{priority.upper()}] {todo.content}")
```

### Pattern 4: Session Memory Consolidation

```python
# At SessionStop, consolidate working memory
def consolidate_session_memory(session_id: str):
    coordinator = MemoryCoordinator()

    # Get all working memory for session
    working = coordinator.retrieve(
        query="",
        memory_types=["working"],
        limit=100  # Get all working memories
    )

    # Filter to this session
    session_working = [
        m for m in working
        if m.metadata.get("session_id") == session_id
    ]

    # Identify significant patterns
    significant = _identify_significant_patterns(session_working)

    # Promote to long-term memory
    for pattern in significant:
        coordinator.store(
            content=pattern["description"],
            memory_type="semantic",
            metadata={"promoted_from": "working"}
        )

    # Clear working memory
    coordinator.clear_working_memory(session_id)
```

---

## Performance Considerations

### Target Metrics

- **Storage**: <50ms per memory (background operation)
- **Retrieval**: <50ms for queries returning <10 memories
- **Agent Review**: 3-5 seconds for storage, 1-2 seconds for retrieval
- **Database Size**: <10MB for 10,000 memories

### Optimization Strategies

**1. Indexed Search**:
```sql
-- SQLite FTS5 index for fast text search
CREATE VIRTUAL TABLE memories_fts USING fts5(
    content,
    metadata,
    tokenize='porter unicode61'
);
```

**2. Background Storage**:
```python
# Don't block user interaction
import asyncio

async def store_async(coordinator, content, memory_type):
    await asyncio.to_thread(coordinator.store, content, memory_type)

# Usage in hooks
asyncio.create_task(store_async(coordinator, prompt, "working"))
```

**3. Batch Retrieval**:
```python
# Retrieve multiple queries efficiently
def batch_retrieve(queries: List[str]) -> Dict[str, List[Memory]]:
    results = {}
    # Single database connection
    with coordinator.backend.connection() as conn:
        for query in queries:
            results[query] = coordinator.retrieve(query)
    return results
```

---

## Testing

### Unit Tests

```python
# tests/test_storage.py
import pytest
from amplihack.memory import StoragePipeline, MemoryType

def test_storage_above_threshold():
    pipeline = StoragePipeline(":memory:")  # In-memory SQLite

    result = pipeline.store(
        content="Decided to use PostgreSQL for transactions",
        memory_type=MemoryType.EPISODIC
    )

    assert result.stored is True
    assert result.consensus_score >= 6.0
    assert result.memory_id is not None

def test_storage_below_threshold():
    pipeline = StoragePipeline(":memory:")

    result = pipeline.store(
        content="Hi there",  # Trivial content
        memory_type=MemoryType.WORKING
    )

    assert result.stored is False
    assert "trivial" in result.reason.lower()
```

### Integration Tests

```python
# tests/test_integration.py
def test_end_to_end_memory_flow():
    coordinator = MemoryCoordinator(":memory:")

    # Store memory
    store_result = coordinator.store(
        content="Implemented JWT authentication with RS256",
        memory_type="procedural"
    )
    assert store_result.stored

    # Retrieve memory
    memories = coordinator.retrieve(
        query="JWT authentication",
        limit=5
    )
    assert len(memories) > 0
    assert "JWT" in memories[0].content
```

---

## Next Steps

- **User Guide**: See [5-Type Memory Guide](./5-TYPE-MEMORY-GUIDE.md) for usage examples
- **Quick Reference**: See [5-Type Memory Quick Reference](./5-TYPE-MEMORY-QUICKREF.md) for cheat sheet
- **Philosophy**: See [PHILOSOPHY.md](../../.claude/context/PHILOSOPHY.md) for design principles

---

**Questions?** Check the [Memory System README](./README.md) or create an issue on GitHub.
