# 5-Type Memory System Guide

> [Home](../index.md) > [Memory System](./README.md) > 5-Type Memory Guide

Ahoy! This guide shows ye how amplihack's 5-type memory system works automatically to remember and recall what ye be needin', when ye be needin' it.

## Contents

- [What Is the 5-Type Memory System?](#what-is-the-5-type-memory-system)
- [How It Works Automatically](#how-it-works-automatically)
- [Memory Types Explained](#memory-types-explained)
- [Querying Memories](#querying-memories)
- [Examples by Type](#examples-by-type)
- [Troubleshooting](#troubleshooting)

---

## What Is the 5-Type Memory System?

The 5-type memory system automatically captures and retrieves different kinds of knowledge across your sessions. It mimics how human memory works, storing different types of information in specialized ways.

**Key Features**:

- **Automatic**: Captures memories via hooks (no manual storage needed)
- **Intelligent**: Multi-agent review decides what's worth storing
- **Fast**: SQLite backend with <50ms operations
- **Selective**: Retrieves only relevant memories within token budget
- **Trivial Filtering**: Pre-filters mundane interactions automatically

**The Five Types**:

1. **Episodic** - Specific events and decisions
2. **Semantic** - Facts and concepts
3. **Prospective** - Future intentions and TODOs
4. **Procedural** - How-to knowledge and workflows
5. **Working** - Active context and temporary state

---

## How It Works Automatically

The memory system operates via three hooks that trigger automatically:

### 1. UserPromptSubmit Hook

**Triggers**: Every time you submit a prompt

**Actions**:

- Extracts prospective memories (TODOs, future intentions)
- Stores in working memory for active context
- Runs in background (<50ms impact)

```python
# Example: You say "I need to fix the authentication bug later"
# System extracts: Prospective memory with priority "high"
```

### 2. TodoWriteComplete Hook

**Triggers**: When TodoWrite tool completes a task

**Actions**:

- Captures procedural memory (how task was done)
- Multi-agent review scores importance (0-10)
- Stores if score >= 6 (worth remembering)

```python
# Example: Complete "Add JWT token validation"
# System extracts: Procedural memory of implementation steps
# Agents score: 8/10 (security-critical, store it)
```

### 3. SessionStop Hook

**Triggers**: When your session ends

**Actions**:

- Reviews entire session for episodic and semantic memories
- Consolidates working memory into long-term storage
- Multi-agent scoring decides what persists

```python
# Example: End session after architectural discussion
# System extracts: Episodic (decision to use Redis), Semantic (Redis concepts)
# Agents score each memory independently
```

### Multi-Agent Review Process

Every memory goes through consensus review by 3 specialized agents:

1. **Analyzer Agent**: Scores technical importance
2. **Patterns Agent**: Scores reusability as pattern
3. **Knowledge Archaeologist**: Scores long-term value

**Consensus Rule**: Average score >= 6.0 to store memory

```python
# Example Review:
Memory: "Use bcrypt for password hashing with salt rounds=12"
- Analyzer: 9/10 (security best practice)
- Patterns: 7/10 (common pattern)
- Knowledge Archaeologist: 8/10 (long-term value)
Average: 8.0 → STORE
```

---

## Memory Types Explained

### 1. Episodic Memory

**What**: Specific events, decisions, and experiences from your sessions

**When Stored**: SessionStop hook, after significant decisions

**Example Content**:

- "Decided to use PostgreSQL over MongoDB for transactions"
- "Fixed authentication bug by adding JWT validation"
- "User reported slow query performance in dashboard"

**Retrieval Triggers**:

- Similar technical decisions
- Related problem domains
- References to specific features/components

```python
from amplihack.memory import MemoryCoordinator

coordinator = MemoryCoordinator()

# Query episodic memories
memories = coordinator.retrieve(
    query="authentication decisions",
    memory_types=["episodic"],
    limit=5
)

for memory in memories:
    print(f"{memory.timestamp}: {memory.content}")
# Output:
# 2025-01-10: Decided to use JWT with RS256 signing
# 2025-01-08: Added refresh token rotation for security
```

### 2. Semantic Memory

**What**: Facts, concepts, and general knowledge about your codebase

**When Stored**: SessionStop hook, when learning new concepts

**Example Content**:

- "JWT tokens contain header, payload, and signature"
- "Redis pub/sub pattern used for real-time notifications"
- "API rate limit is 1000 requests per hour"

**Retrieval Triggers**:

- Technical questions about concepts
- Feature implementation requests
- Debugging similar issues

```python
# Query semantic memories
memories = coordinator.retrieve(
    query="JWT token structure",
    memory_types=["semantic"],
    limit=3
)

for memory in memories:
    print(f"Concept: {memory.content}")
# Output:
# Concept: JWT tokens contain header, payload, and signature
# Concept: RS256 uses asymmetric public/private key pairs
```

### 3. Prospective Memory

**What**: Future intentions, TODOs, and planned work

**When Stored**: UserPromptSubmit hook, when you mention future tasks

**Example Content**:

- "TODO: Refactor authentication middleware"
- "Plan to implement rate limiting next sprint"
- "Need to fix memory leak in worker process"

**Retrieval Triggers**:

- Start of new sessions
- Related feature requests
- Planning discussions

```python
# Query prospective memories (active TODOs)
memories = coordinator.retrieve(
    query="pending authentication work",
    memory_types=["prospective"],
    limit=5
)

for memory in memories:
    priority = memory.metadata.get("priority", "medium")
    print(f"[{priority.upper()}] {memory.content}")
# Output:
# [HIGH] Refactor authentication middleware
# [MEDIUM] Add OAuth2 provider support
```

### 4. Procedural Memory

**What**: Step-by-step knowledge of how to do things

**When Stored**: TodoWriteComplete hook, after task completion

**Example Content**:

- "Deploy to production: 1) Run tests, 2) Build Docker image, 3) Tag release, 4) Update k8s manifests"
- "Fix import errors: Check **init**.py exports, verify module paths"
- "Add new API endpoint: Define route, create handler, add validation, write tests"

**Retrieval Triggers**:

- Similar tasks starting
- Workflow questions
- "How do I..." queries

```python
# Query procedural memories (workflows)
memories = coordinator.retrieve(
    query="how to deploy to production",
    memory_types=["procedural"],
    limit=3
)

for memory in memories:
    print(f"Workflow: {memory.content}")
# Output:
# Workflow: Deploy to production: 1) Run tests, 2) Build Docker image...
```

### 5. Working Memory

**What**: Active context and temporary state during current session

**When Stored**: UserPromptSubmit hook, cleared at SessionStop

**Example Content**:

- "Currently debugging authentication flow"
- "Active branch: feature/jwt-tokens"
- "Testing with user ID: test-user-123"

**Retrieval Triggers**:

- Automatic (always included in context)
- Session state queries
- Context reconstruction

```python
# Query working memory (current session only)
memories = coordinator.retrieve(
    query="current work",
    memory_types=["working"],
    limit=10
)

for memory in memories:
    print(f"Active: {memory.content}")
# Output:
# Active: Currently debugging authentication flow
# Active: Active branch: feature/jwt-tokens
```

---

## Querying Memories

### Basic Query

```python
from amplihack.memory import MemoryCoordinator

coordinator = MemoryCoordinator()

# Simple query across all types
memories = coordinator.retrieve(
    query="authentication",
    limit=10
)

for memory in memories:
    print(f"[{memory.type}] {memory.content}")
```

### Type-Specific Query

```python
# Query only episodic and semantic (exclude TODOs and workflows)
memories = coordinator.retrieve(
    query="Redis implementation",
    memory_types=["episodic", "semantic"],
    limit=5
)
```

### Token Budget Management

The system enforces token budgets to prevent context overflow:

```python
# Retrieve with strict token limit
memories = coordinator.retrieve(
    query="microservices architecture",
    max_tokens=2000  # Only return memories fitting in 2000 tokens
)

print(f"Retrieved {len(memories)} memories in {sum(m.token_count for m in memories)} tokens")
# Output: Retrieved 8 memories in 1847 tokens
```

### Time-Based Queries

```python
from datetime import datetime, timedelta

# Get recent procedural memories (last 7 days)
recent_workflows = coordinator.retrieve(
    query="deployment workflows",
    memory_types=["procedural"],
    since=datetime.now() - timedelta(days=7)
)
```

---

## Examples by Type

### Example 1: Episodic - Decision Capture

```python
# Scenario: You make an architectural decision
# User: "Let's use Redis for session storage instead of in-memory"
# Agent: Implements Redis integration

# At SessionStop, system captures:
episodic_memory = {
    "type": "episodic",
    "content": "Decided to use Redis for session storage. Rationale: Scalability across multiple servers, persistence on restart, built-in TTL for sessions.",
    "timestamp": "2025-01-11T14:30:00Z",
    "context": {
        "agents": ["architect", "builder"],
        "related_files": ["src/session/store.py"]
    }
}

# Multi-agent review:
# Analyzer: 9/10 (significant architectural decision)
# Patterns: 8/10 (common pattern worth remembering)
# Knowledge Archaeologist: 9/10 (long-term value)
# Average: 8.7 → STORED
```

### Example 2: Semantic - Concept Learning

```python
# Scenario: You learn about a new concept
# User: "What's the difference between JWT and session cookies?"
# Agent: Explains in detail

# At SessionStop, system captures:
semantic_memory = {
    "type": "semantic",
    "content": "JWT tokens are stateless (contain all user info in token), session cookies are stateful (server stores session data). JWTs better for microservices, sessions better for monoliths.",
    "timestamp": "2025-01-11T15:00:00Z",
    "context": {
        "category": "authentication",
        "keywords": ["jwt", "sessions", "cookies", "stateless"]
    }
}

# Multi-agent review:
# Analyzer: 7/10 (useful technical knowledge)
# Patterns: 6/10 (architectural pattern)
# Knowledge Archaeologist: 8/10 (fundamental concept)
# Average: 7.0 → STORED
```

### Example 3: Prospective - TODO Extraction

```python
# Scenario: You mention future work
# User: "I need to add rate limiting to the API later"

# At UserPromptSubmit, system captures:
prospective_memory = {
    "type": "prospective",
    "content": "Add rate limiting to API endpoints",
    "timestamp": "2025-01-11T16:00:00Z",
    "metadata": {
        "priority": "medium",
        "status": "pending",
        "component": "api"
    }
}

# No multi-agent review (always stored, cleared when completed)
```

### Example 4: Procedural - Workflow Capture

```python
# Scenario: TodoWrite completes deployment task
# Task: "Deploy authentication service to production"
# Steps executed:
# 1. Run test suite
# 2. Build Docker image
# 3. Push to registry
# 4. Update k8s manifests
# 5. Apply with kubectl

# At TodoWriteComplete, system captures:
procedural_memory = {
    "type": "procedural",
    "content": "Deploy authentication service: 1) pytest tests/, 2) docker build -t auth:v1.2, 3) docker push, 4) Update k8s/auth-deployment.yaml, 5) kubectl apply -f k8s/",
    "timestamp": "2025-01-11T17:00:00Z",
    "context": {
        "task_type": "deployment",
        "success": True,
        "duration_minutes": 12
    }
}

# Multi-agent review:
# Analyzer: 8/10 (critical workflow)
# Patterns: 9/10 (highly reusable)
# Knowledge Archaeologist: 7/10 (long-term value)
# Average: 8.0 → STORED
```

### Example 5: Working - Active Context

```python
# Scenario: Active development session
# User: "I'm debugging the auth flow, using test user 'alice@example.com'"

# At UserPromptSubmit, system captures:
working_memory = {
    "type": "working",
    "content": "Debugging authentication flow with test user alice@example.com",
    "timestamp": "2025-01-11T18:00:00Z",
    "metadata": {
        "session_id": "sess_abc123",
        "active": True
    }
}

# At SessionStop, working memory is:
# - Consolidated into episodic if significant
# - Cleared otherwise (temporary context)
```

---

## Troubleshooting

### Memory Not Being Stored

**Symptom**: Expected memories don't appear in queries

**Causes**:

1. **Low agent scores**: Multi-agent review scored < 6.0
2. **Trivial content**: Pre-filter removed mundane interactions
3. **Working memory**: Only active during session, cleared at stop

**Solutions**:

```python
# Check storage pipeline logs
from amplihack.memory import StoragePipeline

pipeline = StoragePipeline()
result = pipeline.store(
    content="Your memory content",
    memory_type="semantic"
)

print(f"Stored: {result.stored}")
print(f"Score: {result.consensus_score}")
print(f"Reason: {result.reason}")
# Output:
# Stored: False
# Score: 4.5
# Reason: Low importance - agents scored 4/10, 5/10, 5/10
```

### Memory Retrieval Too Slow

**Symptom**: Queries take >50ms

**Causes**:

1. **Large result sets**: Retrieving too many memories
2. **No token budget**: Not limiting results
3. **Database index missing**: SQLite needs optimization

**Solutions**:

```python
# Use strict token budget
memories = coordinator.retrieve(
    query="authentication",
    max_tokens=1000,  # Strict limit
    limit=5  # Also limit count
)

# Check query performance
import time
start = time.time()
memories = coordinator.retrieve(query="test")
duration_ms = (time.time() - start) * 1000
print(f"Query took {duration_ms:.2f}ms")
# Target: <50ms for most queries
```

### Duplicate Memories

**Symptom**: Similar memories stored multiple times

**Causes**:

1. **Session overlap**: Multiple sessions storing same event
2. **Missing deduplication**: Similar content not detected

**Solutions**:

```python
# Query with deduplication
memories = coordinator.retrieve(
    query="authentication",
    deduplicate=True,  # Enable similarity detection
    similarity_threshold=0.85  # 85% similarity = duplicate
)
```

### Missing Context in Memories

**Symptom**: Memories lack useful context for retrieval

**Causes**:

1. **Vague queries**: Not enough specificity
2. **Missing metadata**: Context not captured during storage

**Solutions**:

```python
# Use specific queries with context
memories = coordinator.retrieve(
    query="JWT authentication with Redis session storage",
    memory_types=["episodic", "semantic"],
    context_keywords=["redis", "jwt", "sessions"]
)
```

### Memory System Not Activating

**Symptom**: No memories being captured automatically

**Causes**:

1. **Hooks not registered**: Memory hooks not loaded
2. **SQLite connection issue**: Database not accessible
3. **Permissions issue**: Can't write to ~/.amplihack/

**Solutions**:

```bash
# Check hook registration
ls ~/.claude/tools/amplihack/hooks/memory_*.py

# Check database
sqlite3 ~/.amplihack/memory.db ".schema"
# Should show: agent_memories, agent_sessions, memory_types tables

# Check permissions
ls -la ~/.amplihack/
# Should be writable by current user
```

---

## Next Steps

- **Developer Guide**: See [5-Type Memory Developer Guide](./5-TYPE-MEMORY-DEVELOPER.md) for architecture and extension
- **Quick Reference**: See [5-Type Memory Quick Reference](./5-TYPE-MEMORY-QUICKREF.md) for cheat sheet
- **Agent Memory Integration**: See [Agent Memory Integration](../AGENT_MEMORY_INTEGRATION.md) for how agents use memory

---

**Need help?** Check the [Memory System README](./README.md) or [Troubleshooting Guide](../troubleshooting/README.md).
