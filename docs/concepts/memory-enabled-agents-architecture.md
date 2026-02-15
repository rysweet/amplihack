# Memory-Enabled Agents Architecture

System design and technical deep-dive for memory-enabled goal-seeking agents.

---

## Overview

Memory-enabled agents extend amplihack's goal-seeking agents with persistent memory capabilities. This document describes the architecture, component interactions, data flow, and design decisions.

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                         User/CLI                               │
└───────────┬────────────────────────────────────────────────────┘
            │
            │ amplihack goal-agent run my-agent --target ./code
            │
            ▼
┌────────────────────────────────────────────────────────────────┐
│                   Goal Agent Executor                          │
│  - Task parsing and initialization                             │
│  - Multi-turn autonomous iteration                             │
│  - Success criteria evaluation                                 │
└───────────┬────────────────────────────────────────────────────┘
            │
            │ execute_task(description, target)
            │
            ▼
┌────────────────────────────────────────────────────────────────┐
│              Memory Integration Layer                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  BEFORE Execution:                                       │ │
│  │  1. Load relevant past experiences                       │ │
│  │  2. Filter by similarity and confidence                  │ │
│  │  3. Prepare learned patterns for application             │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  DURING Execution:                                       │ │
│  │  1. Apply learned patterns to decisions                  │ │
│  │  2. Track new discoveries                                │ │
│  │  3. Store intermediate experiences                       │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  AFTER Execution:                                        │ │
│  │  1. Store success/failure outcome                        │ │
│  │  2. Recognize new patterns                               │ │
│  │  3. Update confidence scores                             │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────┬────────────────────────────────────────────────────┘
            │
            │ MemoryConnector API
            │
            ▼
┌────────────────────────────────────────────────────────────────┐
│           amplihack-memory-lib (Standalone Package)            │
│                                                                 │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐│
│  │   MemoryConnector       │  │   ExperienceStore            ││
│  │  - store_experience()   │  │  - add()                     ││
│  │  - retrieve_relevant()  │  │  - search()                  ││
│  │  - get_statistics()     │  │  - auto_compress()           ││
│  └────────┬────────────────┘  └──────────┬───────────────────┘│
│           │                               │                     │
│           └───────────┬───────────────────┘                     │
│                       │                                         │
│                       ▼                                         │
│           ┌────────────────────────────┐                        │
│           │   SQLite Storage Backend   │                        │
│           │  - experiences.db          │                        │
│           │  - Full-text search index  │                        │
│           │  - Compression support     │                        │
│           └────────────────────────────┘                        │
│                                                                 │
│  Storage: ~/.amplihack/memory/{agent_name}/                    │
└───────────┬────────────────────────────────────────────────────┘
            │
            │ Validation interface
            │
            ▼
┌────────────────────────────────────────────────────────────────┐
│               gadugi-agentic-test Integration                  │
│  - Test-driven learning validation                             │
│  - Evidence collection for experiences                         │
│  - Success criteria verification                               │
│  - Learning behavior regression tests                          │
└────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### 1. Goal Agent Executor

**Purpose**: Autonomous task execution with multi-turn iteration

**Responsibilities**:

- Parse user's objective and constraints
- Iterate until objective achieved or max iterations
- Evaluate success criteria
- Coordinate with memory layer

**State**: Stateless (no persistence between runs)

**Key Methods**:

```python
class GoalAgent:
    async def execute_task(self, description: str, target: Path) -> Result
    async def iterate_until_complete(self) -> bool
    def evaluate_success_criteria(self) -> bool
```

### 2. Memory Integration Layer

**Purpose**: Glue layer connecting agent logic to memory storage

**Responsibilities**:

- Retrieve relevant experiences before execution
- Filter experiences by confidence and similarity
- Store new experiences during/after execution
- Recognize patterns from multiple experiences
- Update confidence scores based on outcomes

**State**: Per-execution context (not persisted)

**Key Methods**:

```python
class MemoryIntegration:
    def load_relevant_experiences(self, context: str) -> List[Experience]
    def apply_learned_patterns(self, patterns: List[Experience]) -> None
    def store_new_experience(self, exp: Experience) -> str
    def recognize_patterns(self, experiences: List[Experience]) -> List[Experience]
```

### 3. amplihack-memory-lib Package

**Purpose**: Standalone persistent memory storage and retrieval

**Responsibilities**:

- Store experiences in SQLite database
- Retrieve experiences by filters (type, confidence, date)
- Semantic search for relevant experiences
- Memory management (compression, cleanup)
- Statistics and metrics

**State**: Persistent (SQLite database on disk)

**Key Classes**:

- `MemoryConnector`: Main API for memory operations
- `ExperienceStore`: High-level interface with auto-management
- `Experience`: Data class for experience objects
- `ExperienceType`: Enum (SUCCESS, FAILURE, PATTERN, INSIGHT)

### 4. gadugi-agentic-test Validation

**Purpose**: Validate that agents actually learn and improve

**Responsibilities**:

- Test experience storage after execution
- Verify runtime improvement across runs
- Validate pattern recognition accuracy
- Check confidence score progression
- Collect evidence of learning behavior

**State**: Test reports and evidence files

**Key Tests**:

```python
def test_agent_stores_experiences_after_run()
def test_agent_improves_with_memory()
def test_pattern_recognition_across_runs()
def test_confidence_increases_with_validation()
```

---

## Data Flow

### Execution Flow (Single Run)

```
1. User invokes agent
   └─> amplihack goal-agent run doc-analyzer --target ./docs

2. Goal Agent Executor initializes
   ├─> Loads agent definition
   ├─> Parses objective and constraints
   └─> Initializes Memory Integration Layer

3. Memory Integration Layer loads context
   ├─> Calls MemoryConnector.retrieve_relevant(context)
   ├─> Filters by confidence >= min_confidence_to_apply
   ├─> Separates PATTERN and INSIGHT experiences
   └─> Returns relevant_experiences[]

4. Goal Agent executes task
   ├─> Applies learned patterns first
   │   ├─> For each PATTERN with high confidence:
   │   │   ├─> Apply pattern to current task
   │   │   └─> Store SUCCESS experience if pattern works
   │   └─> Track patterns_applied count
   │
   ├─> Performs main analysis
   │   ├─> Analyzes files/code
   │   ├─> Discovers new issues/patterns
   │   └─> Tracks discoveries[]
   │
   └─> Recognizes patterns in discoveries
       ├─> Group similar discoveries
       ├─> Count occurrences
       └─> If count >= pattern_recognition_threshold:
           └─> Create new PATTERN experience

5. Memory Integration Layer stores experiences
   ├─> Store SUCCESS/FAILURE outcome
   ├─> Store new PATTERN experiences
   ├─> Store INSIGHT experiences (if any)
   └─> Update metadata (runtime, counts, etc.)

6. Results returned to user
   └─> Summary: X issues found, Y patterns applied, Z new patterns
```

### Multi-Run Learning Flow

```
Run 1:
  Load: 0 experiences
  Apply: 0 patterns
  Discover: 5 issues (no patterns yet)
  Store: 5 SUCCESS experiences
  Result: Runtime 45s, found 5 issues

Run 2:
  Load: 5 experiences (relevant to current task)
  Apply: 0 patterns (not recognized yet - only 1 occurrence each)
  Discover: 7 issues (3 similar to Run 1)
  Recognize: 3 patterns (occurred in both Run 1 and Run 2)
  Store: 7 SUCCESS + 3 PATTERN experiences
  Result: Runtime 40s, found 7 issues

Run 3:
  Load: 15 experiences (5 + 7 + 3 patterns)
  Apply: 3 patterns (confidence >= 0.7)
    ├─> Pattern 1: Found 2 matches immediately (no analysis needed)
    ├─> Pattern 2: Found 1 match immediately
    └─> Pattern 3: Found 0 matches (pattern doesn't apply here)
  Discover: 4 new issues
  Recognize: 1 new pattern
  Store: 4 SUCCESS + 1 PATTERN + Update confidence on Pattern 1 & 2
  Result: Runtime 25s (44% faster), found 7 issues (3 from patterns + 4 new)

Run 10:
  Load: 80 experiences (patterns, successes, insights)
  Apply: 12 patterns with high confidence
    └─> Immediately check for all known patterns (5s)
  Discover: 1 new issue
  Store: 1 SUCCESS + Update confidence on 12 patterns
  Result: Runtime 18s (60% faster), found 13 issues (12 from patterns + 1 new)
```

**Key Observation**: Learning curve is steep initially (runs 1-5), then plateaus as agent masters the domain.

---

## Storage Schema

### SQLite Database Schema

```sql
-- experiences table
CREATE TABLE experiences (
    experience_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    experience_type TEXT NOT NULL,  -- 'success', 'failure', 'pattern', 'insight'
    context TEXT NOT NULL,
    outcome TEXT NOT NULL,
    confidence REAL NOT NULL,
    timestamp INTEGER NOT NULL,     -- Unix timestamp
    metadata_json TEXT,             -- JSON blob
    tags_json TEXT,                 -- JSON array
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

-- Indexes for fast retrieval
CREATE INDEX idx_agent_name ON experiences(agent_name);
CREATE INDEX idx_experience_type ON experiences(experience_type);
CREATE INDEX idx_timestamp ON experiences(timestamp);
CREATE INDEX idx_confidence ON experiences(confidence);
CREATE INDEX idx_agent_type ON experiences(agent_name, experience_type);

-- Full-text search index
CREATE VIRTUAL TABLE experiences_fts USING fts5(
    experience_id,
    context,
    outcome,
    content=experiences
);
```

### Experience Data Model

```python
@dataclass
class Experience:
    """Represents a single learning experience."""

    experience_id: str              # Unique ID (auto-generated)
    experience_type: ExperienceType # SUCCESS, FAILURE, PATTERN, INSIGHT
    context: str                    # What was happening (max 500 chars)
    outcome: str                    # What resulted (max 1000 chars)
    confidence: float               # 0.0 - 1.0
    timestamp: datetime             # When this occurred
    metadata: Dict[str, Any]        # Additional data
    tags: List[str]                 # Searchable tags
```

**Experience ID Format**: `exp_YYYYMMDD_HHMMSS_{hash}`

Example: `exp_20260214_102315_a7f3c9`

### Metadata Structure

Metadata is flexible JSON, but common fields include:

```json
{
  "runtime_seconds": 45.2,
  "files_processed": 47,
  "issues_found": 5,
  "patterns_applied": 3,
  "patterns_discovered": 2,
  "cache_hits": 12,
  "cache_misses": 35,
  "true_positives": 5,
  "false_positives": 1,
  "false_negatives": 0,
  "target_path": "./docs",
  "agent_version": "1.0.0"
}
```

---

## Memory Management

### Automatic Cleanup

Memory is managed automatically based on configuration:

```yaml
# memory_config.yaml
retention:
  max_age_days: 90 # Delete experiences older than 90 days
  max_experiences: 10000 # Keep max 10,000 experiences
  delete_strategy: oldest_first
```

**Cleanup Process**:

1. Run periodically (on agent startup and every 100 executions)
2. Check if limits exceeded
3. If `max_age_days` exceeded: Delete experiences older than threshold
4. If `max_experiences` exceeded: Delete oldest experiences until under limit
5. Vacuum database to reclaim space

### Compression

Old experiences are compressed to save space:

```yaml
compression:
  enabled: true
  after_days: 30 # Compress experiences older than 30 days
```

**Compression Process**:

1. Experiences older than `after_days` are candidates
2. Metadata JSON is compressed with gzip
3. Original JSON replaced with compressed version
4. Typical compression ratio: 3:1

**Access**: Compressed experiences are automatically decompressed on retrieval (transparent to caller).

---

## Semantic Relevance

### How Relevance is Calculated

When retrieving relevant experiences, similarity is calculated using:

```python
def calculate_relevance(experience: Experience, current_context: str) -> float:
    """
    Calculate relevance score (0.0 - 1.0) for an experience.

    Factors:
    1. Text similarity (TF-IDF or embedding-based)
    2. Experience type (PATTERN and INSIGHT weighted higher)
    3. Confidence (higher confidence = more relevant)
    4. Recency (newer experiences weighted higher)
    """

    # Base similarity using TF-IDF vectorizer
    base_similarity = tfidf_similarity(experience.context, current_context)

    # Type weighting
    type_weight = {
        ExperienceType.PATTERN: 1.5,
        ExperienceType.INSIGHT: 1.3,
        ExperienceType.SUCCESS: 1.0,
        ExperienceType.FAILURE: 0.8
    }[experience.experience_type]

    # Confidence boost
    confidence_factor = experience.confidence

    # Recency boost (decay over 90 days)
    age_days = (datetime.now() - experience.timestamp).days
    recency_factor = max(0.5, 1.0 - (age_days / 90))

    # Combined score
    relevance = base_similarity * type_weight * confidence_factor * recency_factor

    return min(1.0, relevance)  # Cap at 1.0
```

### Example Relevance Calculation

```python
# Current task
current_context = "Analyze Python documentation for missing examples"

# Experience 1
exp1 = Experience(
    experience_type=ExperienceType.PATTERN,
    context="Tutorial files without code examples",
    confidence=0.92,
    timestamp=datetime(2026, 2, 10)  # 4 days ago
)

# Calculation:
# - base_similarity: 0.85 (high text similarity)
# - type_weight: 1.5 (PATTERN)
# - confidence_factor: 0.92
# - recency_factor: 0.96 (recent)
# = 0.85 * 1.5 * 0.92 * 0.96 = 1.13 → capped to 1.0

relevance1 = 1.0  # Highly relevant

# Experience 2
exp2 = Experience(
    experience_type=ExperienceType.SUCCESS,
    context="Fixed security vulnerability in authentication",
    confidence=0.88,
    timestamp=datetime(2026, 1, 15)  # 30 days ago
)

# Calculation:
# - base_similarity: 0.15 (low text similarity)
# - type_weight: 1.0 (SUCCESS)
# - confidence_factor: 0.88
# - recency_factor: 0.67 (older)
# = 0.15 * 1.0 * 0.88 * 0.67 = 0.09

relevance2 = 0.09  # Not relevant
```

---

## Pattern Recognition Algorithm

### Pattern Detection

Patterns are recognized when a situation occurs repeatedly:

```python
def detect_patterns(
    current_discoveries: List[Discovery],
    known_patterns: List[Experience],
    threshold: int = 3
) -> List[Experience]:
    """
    Detect new patterns from current discoveries.

    Args:
        current_discoveries: New discoveries from this run
        known_patterns: Existing known patterns
        threshold: Minimum occurrences to recognize pattern

    Returns:
        List of new PATTERN experiences
    """

    # Track pattern candidates
    pattern_candidates = defaultdict(lambda: {
        "count": 0,
        "examples": [],
        "confidence": 0.0
    })

    # Extract pattern keys from discoveries
    for discovery in current_discoveries:
        pattern_key = extract_pattern_key(discovery)

        pattern_candidates[pattern_key]["count"] += 1
        pattern_candidates[pattern_key]["examples"].append(discovery)

    # Check if any candidates exceed threshold
    new_patterns = []

    for pattern_key, data in pattern_candidates.items():
        if data["count"] >= threshold:
            # Check if already known
            is_known = any(
                p.context == pattern_key
                for p in known_patterns
            )

            if not is_known:
                # Create new pattern
                confidence = min(0.5 + (data["count"] * 0.1), 0.95)

                pattern = Experience(
                    experience_type=ExperienceType.PATTERN,
                    context=pattern_key,
                    outcome=describe_pattern(data),
                    confidence=confidence,
                    timestamp=datetime.now(),
                    metadata={
                        "occurrences": data["count"],
                        "examples": data["examples"][:5]
                    }
                )

                new_patterns.append(pattern)

    return new_patterns
```

### Pattern Key Extraction

Pattern keys are domain-specific identifiers:

```python
# Example: Documentation analyzer
def extract_pattern_key(discovery: Discovery) -> str:
    """Extract pattern identifier from discovery."""

    if discovery.type == "missing_example":
        return "tutorial_missing_example"

    elif discovery.type == "broken_link":
        if "external" in discovery.url:
            return "external_link_broken"
        else:
            return "internal_link_broken"

    elif discovery.type == "unclear_heading":
        return "heading_too_generic"

    else:
        return f"unknown_{discovery.type}"
```

---

## Security Considerations

### Data Privacy

**What is stored**:

- Natural language context descriptions
- Natural language outcomes
- Metadata (metrics, file paths, timestamps)
- NO source code by default
- NO credentials or secrets

**Storage location**: `~/.amplihack/memory/{agent_name}/`

**Permissions**: Owner read/write only (chmod 600)

### Sensitive Data Handling

Agents should NOT store sensitive data in experiences:

```python
# ❌ BAD: Storing actual credential
experience = Experience(
    context="Found password: supersecret123",
    outcome="Should be in env var"
)

# ✓ GOOD: Storing reference only
experience = Experience(
    context="File auth.py line 42: Hardcoded credential found",
    outcome="Flagged for removal",
    metadata={"file": "auth.py", "line": 42}
)
```

### Memory Isolation

Each agent has isolated memory:

- Agent A cannot access Agent B's experiences
- Memory is scoped by `agent_name`
- No cross-agent memory sharing (by design)

**Rationale**: Prevents interference and maintains clear boundaries.

---

## Performance Characteristics

### Storage Performance

| Operation                | Complexity | Time (1K experiences) | Time (10K experiences) |
| ------------------------ | ---------- | --------------------- | ---------------------- |
| `store_experience()`     | O(1)       | < 5ms                 | < 5ms                  |
| `retrieve_experiences()` | O(n)       | < 20ms                | < 50ms                 |
| `retrieve_relevant()`    | O(n log k) | < 50ms                | < 80ms                 |
| `get_statistics()`       | O(1)       | < 2ms                 | < 5ms                  |

### Memory Usage

| Component              | Per-Agent Storage            | Notes                    |
| ---------------------- | ---------------------------- | ------------------------ |
| SQLite database        | 2-10 MB per 1000 experiences | Depends on metadata size |
| Full-text index        | +20% overhead                | For semantic search      |
| Compressed experiences | -70% (3:1 ratio)             | After compression        |

**Typical agent memory**: 5-50 MB after 100 runs

### Runtime Impact

| Phase              | Overhead              | Notes                       |
| ------------------ | --------------------- | --------------------------- |
| Load experiences   | 50-100ms              | One-time at start           |
| Apply patterns     | 10-30ms per pattern   | Linear with pattern count   |
| Store experiences  | 5-10ms per experience | Batched at end              |
| **Total overhead** | **5-10%**             | Offset by performance gains |

**Net effect**: Despite overhead, agents run 40-60% faster after learning due to pattern application.

---

## Design Decisions

### Why Standalone Library?

**Decision**: Package amplihack-memory-lib separately from amplihack

**Rationale**:

1. **Reusability**: Can be used in non-amplihack projects
2. **Versioning**: Independent release cycle
3. **Dependencies**: Minimal deps (Python 3.10+, SQLite only)
4. **Testing**: Easier to test in isolation

### Why SQLite Instead of External DB?

**Decision**: Use embedded SQLite database

**Rationale**:

1. **Zero setup**: No external service required
2. **File-based**: Easy to backup, copy, version control
3. **Fast enough**: Adequate performance for agent use case
4. **Portable**: Works on any platform

**Trade-offs**:

- ❌ No multi-agent concurrent writes (not needed - agents run serially)
- ✓ Simple deployment (no database server)
- ✓ Low resource usage (no background process)

### Why Four Experience Types?

**Decision**: SUCCESS, FAILURE, PATTERN, INSIGHT (not more, not fewer)

**Rationale**:

1. **SUCCESS/FAILURE**: Outcome tracking (what worked/didn't work)
2. **PATTERN**: Reusable knowledge (applies to new situations)
3. **INSIGHT**: High-level principles (guides decision-making)

**Alternatives considered**:

- Single type "EXPERIENCE": ❌ Too generic, harder to filter
- Many types (WARNING, INFO, DEBUG, etc.): ❌ Overcomplicates, unclear semantics

### Why Confidence Scores?

**Decision**: Every experience has confidence score (0.0-1.0)

**Rationale**:

1. **Filtering**: Only apply high-confidence patterns
2. **Learning**: Confidence increases with validation
3. **Uncertainty**: Explicit representation of agent's certainty

**Usage**:

```python
# Only apply patterns with confidence >= 0.7
if pattern.confidence >= 0.7:
    apply_pattern(pattern)
```

---

## Future Enhancements

### Planned Improvements

1. **Cross-Agent Knowledge Transfer**
   - Export experiences from Agent A
   - Import into Agent B
   - Use case: Transfer learnings to new agent

2. **Advanced Similarity Metrics**
   - Embedding-based similarity (currently TF-IDF)
   - Use sentence transformers for better semantic matching
   - Configurable similarity functions

3. **Memory Visualization**
   - Web UI for browsing experiences
   - Graph visualization of pattern relationships
   - Timeline view of learning progression

4. **Federated Learning**
   - Agents share knowledge without sharing data
   - Privacy-preserving knowledge transfer
   - Community pattern libraries

---

## See Also

- **[Memory-Enabled Agents Feature Overview](../features/memory-enabled-agents.md)** - High-level introduction
- **[API Reference](../reference/memory-enabled-agents-api.md)** - Complete technical documentation
- **[Getting Started Tutorial](../tutorials/memory-enabled-agents-getting-started.md)** - Step-by-step guide
- **[Integration Guide](../howto/integrate-memory-into-agents.md)** - Add memory to agents

---

**Architecture Version**: 1.0
**Last Updated**: 2026-02-14
