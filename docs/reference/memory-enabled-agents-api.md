# Memory-Enabled Agents API Reference

Complete technical documentation for the amplihack-memory-lib package.

---

## Overview

The `amplihack-memory-lib` package provides persistent memory capabilities for goal-seeking agents. It enables agents to store, retrieve, and learn from past experiences across multiple execution sessions.

**Package**: `amplihack-memory-lib`
**Module**: `amplihack_memory`
**Minimum Python**: 3.10+
**Storage Backend**: SQLite (file-based, no external dependencies)

---

## Installation

```bash
pip install amplihack-memory-lib
```

### Optional Dependencies

```bash
# For advanced analytics
pip install amplihack-memory-lib[analytics]

# For visualization tools
pip install amplihack-memory-lib[viz]

# All extras
pip install amplihack-memory-lib[all]
```

---

## Core Classes

### MemoryConnector

Main interface for memory operations.

```python
from amplihack_memory import MemoryConnector

connector = MemoryConnector(agent_name="doc-analyzer")
```

#### Constructor

```python
MemoryConnector(
    agent_name: str,
    storage_path: Optional[Path] = None,
    max_memory_mb: int = 100,
    enable_compression: bool = True
)
```

**Parameters**:

- `agent_name` (str): Unique identifier for the agent
- `storage_path` (Path, optional): Custom storage location. Default: `~/.amplihack/memory/{agent_name}/`
- `max_memory_mb` (int): Maximum memory storage size in MB. Default: 100
- `enable_compression` (bool): Enable experience compression. Default: True

**Example**:

```python
# Default configuration
connector = MemoryConnector("security-scanner")

# Custom storage location
connector = MemoryConnector(
    agent_name="bug-predictor",
    storage_path=Path("/var/amplihack/memory"),
    max_memory_mb=250
)
```

#### Methods

##### `store_experience()`

Store a new experience in memory.

```python
connector.store_experience(experience: Experience) -> str
```

**Parameters**:

- `experience` (Experience): Experience object to store

**Returns**: `str` - Unique experience ID

**Example**:

```python
from amplihack_memory import Experience, ExperienceType
from datetime import datetime

exp = Experience(
    experience_type=ExperienceType.SUCCESS,
    context="Analyzed 47 files for broken links",
    outcome="Found 5 broken external links",
    confidence=0.92,
    timestamp=datetime.now(),
    metadata={"files_processed": 47, "runtime_ms": 1250}
)

exp_id = connector.store_experience(exp)
print(f"Stored: {exp_id}")
# Output: Stored: exp_20260214_102315_a7f3c9
```

##### `retrieve_experiences()`

Retrieve experiences matching criteria.

```python
connector.retrieve_experiences(
    experience_type: Optional[ExperienceType] = None,
    min_confidence: float = 0.0,
    limit: int = 100,
    since: Optional[datetime] = None
) -> List[Experience]
```

**Parameters**:

- `experience_type` (ExperienceType, optional): Filter by type
- `min_confidence` (float): Minimum confidence threshold (0.0-1.0). Default: 0.0
- `limit` (int): Maximum number of experiences to return. Default: 100
- `since` (datetime, optional): Only return experiences after this timestamp

**Returns**: `List[Experience]` - Matching experiences, ordered by timestamp (newest first)

**Example**:

```python
# Get all high-confidence patterns
patterns = connector.retrieve_experiences(
    experience_type=ExperienceType.PATTERN,
    min_confidence=0.8,
    limit=50
)

print(f"Found {len(patterns)} high-confidence patterns")
for pattern in patterns:
    print(f"  - {pattern.context} (confidence: {pattern.confidence})")

# Output:
# Found 8 high-confidence patterns
#   - external_link_dead (confidence: 0.95)
#   - tutorial_no_example (confidence: 0.87)
```

##### `retrieve_relevant()`

Retrieve experiences relevant to current context using semantic similarity.

```python
connector.retrieve_relevant(
    current_context: str,
    top_k: int = 10,
    min_similarity: float = 0.7
) -> List[Experience]
```

**Parameters**:

- `current_context` (str): Description of current task/situation
- `top_k` (int): Number of most relevant experiences to return. Default: 10
- `min_similarity` (float): Minimum similarity threshold (0.0-1.0). Default: 0.7

**Returns**: `List[Experience]` - Relevant experiences ordered by similarity score

**Example**:

```python
context = "Analyzing Python documentation for code examples"

relevant = connector.retrieve_relevant(
    current_context=context,
    top_k=5,
    min_similarity=0.75
)

for exp in relevant:
    print(f"Similarity: {exp.metadata.get('similarity_score'):.2f}")
    print(f"Context: {exp.context}")
    print()

# Output:
# Similarity: 0.89
# Context: tutorial_no_example pattern in Python guides
#
# Similarity: 0.82
# Context: Missing runnable examples in API documentation
```

##### `get_statistics()`

Get memory usage and learning statistics.

```python
connector.get_statistics() -> Dict[str, Any]
```

**Returns**: Dictionary with statistics:

- `total_experiences` (int): Total stored experiences
- `by_type` (Dict[ExperienceType, int]): Count per experience type
- `storage_size_kb` (float): Storage size in KB
- `oldest_experience` (datetime): Timestamp of oldest experience
- `newest_experience` (datetime): Timestamp of newest experience
- `average_confidence` (float): Average confidence across all experiences

**Example**:

```python
stats = connector.get_statistics()

print(f"Total experiences: {stats['total_experiences']}")
print(f"Storage: {stats['storage_size_kb']:.1f} KB")
print(f"Average confidence: {stats['average_confidence']:.2f}")
print("\nBy type:")
for exp_type, count in stats['by_type'].items():
    print(f"  {exp_type.value}: {count}")

# Output:
# Total experiences: 42
# Storage: 156.3 KB
# Average confidence: 0.84
#
# By type:
#   success: 15
#   failure: 8
#   pattern: 14
#   insight: 5
```

##### `clear()`

Clear all stored experiences for this agent.

```python
connector.clear() -> int
```

**Returns**: `int` - Number of experiences deleted

**Example**:

```python
count = connector.clear()
print(f"Deleted {count} experiences")
# Output: Deleted 42 experiences
```

---

### ExperienceStore

High-level storage interface with automatic memory management.

```python
from amplihack_memory import ExperienceStore

store = ExperienceStore(
    agent_name="performance-optimizer",
    auto_compress=True,
    max_age_days=90
)
```

#### Constructor

```python
ExperienceStore(
    agent_name: str,
    storage_path: Optional[Path] = None,
    auto_compress: bool = True,
    max_age_days: Optional[int] = None,
    max_experiences: Optional[int] = None
)
```

**Parameters**:

- `agent_name` (str): Unique identifier for the agent
- `storage_path` (Path, optional): Custom storage location
- `auto_compress` (bool): Automatically compress old experiences. Default: True
- `max_age_days` (int, optional): Delete experiences older than this (days). Default: None (keep forever)
- `max_experiences` (int, optional): Maximum experiences to keep. Delete oldest when exceeded. Default: None (unlimited)

**Example**:

```python
# Keep only last 90 days, max 1000 experiences
store = ExperienceStore(
    agent_name="code-reviewer",
    max_age_days=90,
    max_experiences=1000,
    auto_compress=True
)
```

#### Methods

##### `add()`

Add an experience with automatic management.

```python
store.add(experience: Experience) -> str
```

Automatically handles:

- Compression of old experiences
- Deletion of experiences exceeding age/count limits
- Duplicate detection

**Parameters**:

- `experience` (Experience): Experience to store

**Returns**: `str` - Experience ID

**Example**:

```python
exp = Experience(
    experience_type=ExperienceType.INSIGHT,
    context="Refactoring reduces complexity better than comments",
    outcome="Applied to 3 files, complexity reduced by 40%",
    confidence=0.88,
    timestamp=datetime.now()
)

exp_id = store.add(exp)
```

##### `search()`

Search experiences with advanced filtering.

```python
store.search(
    query: str,
    experience_type: Optional[ExperienceType] = None,
    min_confidence: float = 0.0,
    limit: int = 50
) -> List[Experience]
```

**Parameters**:

- `query` (str): Search query (matches context and outcome fields)
- `experience_type` (ExperienceType, optional): Filter by type
- `min_confidence` (float): Minimum confidence threshold
- `limit` (int): Maximum results

**Returns**: `List[Experience]` - Matching experiences ordered by relevance

**Example**:

```python
# Find all experiences related to "performance"
results = store.search(
    query="performance optimization",
    min_confidence=0.75,
    limit=20
)

for exp in results:
    print(f"{exp.experience_type.value}: {exp.context}")
```

---

### Experience

Data class representing a single learning experience.

```python
from amplihack_memory import Experience, ExperienceType
from datetime import datetime

exp = Experience(
    experience_type=ExperienceType.SUCCESS,
    context="Description of situation",
    outcome="What happened",
    confidence=0.85,
    timestamp=datetime.now(),
    metadata={"key": "value"}
)
```

#### Attributes

```python
@dataclass
class Experience:
    experience_id: str              # Unique identifier (auto-generated)
    experience_type: ExperienceType # Type of experience
    context: str                    # Situation description
    outcome: str                    # What happened/learned
    confidence: float               # Confidence score (0.0-1.0)
    timestamp: datetime             # When this occurred
    metadata: Dict[str, Any]        # Additional structured data
    tags: List[str]                 # Searchable tags
```

**Field Descriptions**:

- `experience_id`: Automatically generated unique identifier (format: `exp_YYYYMMDD_HHMMSS_hash`)
- `experience_type`: One of SUCCESS, FAILURE, PATTERN, or INSIGHT
- `context`: Natural language description of the situation (max 500 chars)
- `outcome`: What resulted or was learned (max 1000 chars)
- `confidence`: How confident the agent is in this experience (0.0 = no confidence, 1.0 = absolute confidence)
- `timestamp`: When the experience occurred (auto-set to now if not provided)
- `metadata`: Dictionary for structured data (e.g., metrics, file paths, counts)
- `tags`: List of searchable tags for categorization

**Example**:

```python
exp = Experience(
    experience_type=ExperienceType.PATTERN,
    context="Documentation files with 'tutorial' in name often lack code examples",
    outcome="Pattern recognized across 12 files in 3 projects",
    confidence=0.91,
    timestamp=datetime.now(),
    metadata={
        "files_matched": 12,
        "projects": ["project-a", "project-b", "project-c"],
        "false_positives": 1
    },
    tags=["documentation", "tutorials", "quality"]
)
```

---

### ExperienceType

Enumeration of experience types.

```python
from amplihack_memory import ExperienceType

class ExperienceType(Enum):
    SUCCESS = "success"   # Successful action or decision
    FAILURE = "failure"   # Failed action (for learning)
    PATTERN = "pattern"   # Recognized pattern
    INSIGHT = "insight"   # High-level insight or principle
```

**When to Use Each Type**:

| Type        | Use When                            | Example                                                               |
| ----------- | ----------------------------------- | --------------------------------------------------------------------- |
| **SUCCESS** | Action achieved desired outcome     | "Fixed broken link by updating URL to current location"               |
| **FAILURE** | Action failed but provides learning | "Attempted to parse Markdown with regex, resulted in broken tables"   |
| **PATTERN** | Recurring situation recognized      | "Tutorial files without 'example' heading usually lack runnable code" |
| **INSIGHT** | High-level understanding gained     | "Clear examples reduce support requests by 60%"                       |

---

## CLI Commands

The amplihack-memory-lib package includes CLI commands for memory management.

### `amplihack memory query`

Query agent memory.

```bash
amplihack memory query <agent-name> [OPTIONS]
```

**Options**:

- `--type [success|failure|pattern|insight]` - Filter by experience type
- `--min-confidence FLOAT` - Minimum confidence threshold (0.0-1.0)
- `--since DATETIME` - Only show experiences after this date
- `--limit INT` - Maximum number of results (default: 100)
- `--format [text|json|table]` - Output format (default: table)

**Examples**:

```bash
# Show all patterns with confidence > 0.8
amplihack memory query doc-analyzer --type pattern --min-confidence 0.8

# Export all experiences as JSON
amplihack memory query doc-analyzer --format json > experiences.json

# Show recent experiences (last 7 days)
amplihack memory query doc-analyzer --since "7 days ago" --limit 50
```

### `amplihack memory metrics`

View learning metrics.

```bash
amplihack memory metrics <agent-name> [OPTIONS]
```

**Options**:

- `--window DAYS` - Time window for metrics (default: 30)
- `--format [text|json]` - Output format (default: text)

**Example**:

```bash
amplihack memory metrics doc-analyzer --window 7
```

**Output**:

```
Agent: doc-analyzer
Time Window: Last 7 days
Runs: 5

Learning Metrics:
- Pattern recognition rate: 78% (increasing)
- Average runtime improvement: 45% faster than first run
- Confidence growth: +18% average across patterns
- New patterns discovered: 3

Memory Usage:
- Total experiences: 67
- Storage size: 201.5 KB
- Compression ratio: 3.2:1
```

### `amplihack memory clear`

Clear agent memory.

```bash
amplihack memory clear <agent-name> [OPTIONS]
```

**Options**:

- `--older-than DAYS` - Only delete experiences older than this
- `--type [success|failure|pattern|insight]` - Only delete specific type
- `--yes` - Skip confirmation prompt

**Examples**:

```bash
# Clear all memory (with confirmation)
amplihack memory clear doc-analyzer

# Delete experiences older than 90 days
amplihack memory clear doc-analyzer --older-than 90 --yes

# Delete only failures
amplihack memory clear doc-analyzer --type failure --yes
```

---

## Integration with Goal Agents

### Enabling Memory in Agent Definition

Add memory configuration to agent definition:

```yaml
# agents/my-agent/memory_config.yaml
memory:
  enabled: true
  connector_class: MemoryConnector
  storage_path: null # Use default

  # Experience types this agent uses
  experience_types:
    - success
    - failure
    - pattern
    - insight

  # Memory management
  max_memory_mb: 100
  max_age_days: 90
  auto_compress: true

  # Learning configuration
  learning:
    min_confidence_to_apply: 0.7 # Only apply patterns with confidence >= 0.7
    pattern_recognition_threshold: 3 # Recognize pattern after 3 occurrences
```

### Agent Memory Integration Points

Agents integrate memory at three key points:

```python
# 1. BEFORE task execution - Retrieve relevant experiences
async def execute_task(self, task: Task) -> Result:
    # Load relevant past experiences
    relevant_experiences = self.memory.retrieve_relevant(
        current_context=task.description,
        top_k=10,
        min_similarity=0.7
    )

    # Apply learned patterns
    for exp in relevant_experiences:
        if exp.experience_type == ExperienceType.PATTERN:
            self.apply_pattern(exp)

    # 2. DURING execution - Store intermediate experiences
    result = await self.perform_task(task)

    if result.discovered_pattern:
        self.memory.store_experience(Experience(
            experience_type=ExperienceType.PATTERN,
            context=result.pattern_context,
            outcome=result.pattern_description,
            confidence=result.pattern_confidence
        ))

    # 3. AFTER execution - Store outcome
    self.memory.store_experience(Experience(
        experience_type=ExperienceType.SUCCESS if result.success else ExperienceType.FAILURE,
        context=f"Task: {task.description}",
        outcome=result.summary,
        confidence=result.confidence,
        metadata=result.metrics
    ))

    return result
```

---

## Advanced Usage

### Custom Similarity Metrics

Define custom similarity functions for context matching:

```python
from amplihack_memory import MemoryConnector, Experience

def custom_similarity(exp: Experience, context: str) -> float:
    """
    Custom similarity metric that weighs recent experiences higher.
    """
    from datetime import datetime, timedelta

    # Base similarity (0.0-1.0)
    base_sim = calculate_text_similarity(exp.context, context)

    # Recency boost (newer experiences weighted higher)
    age_days = (datetime.now() - exp.timestamp).days
    recency_factor = max(0.5, 1.0 - (age_days / 90))

    # Confidence boost
    confidence_factor = exp.confidence

    return base_sim * recency_factor * confidence_factor

# Use custom similarity
connector = MemoryConnector("my-agent")
connector.set_similarity_function(custom_similarity)
```

### Batch Operations

Efficiently store multiple experiences:

```python
experiences = []

for file in files_analyzed:
    if file.has_issue:
        experiences.append(Experience(
            experience_type=ExperienceType.PATTERN,
            context=f"Issue in {file.type} file: {file.issue_type}",
            outcome=file.issue_description,
            confidence=0.85
        ))

# Batch store (more efficient than individual stores)
connector.store_batch(experiences)
```

### Memory Export/Import

```python
# Export agent memory
connector = MemoryConnector("doc-analyzer")
exported_data = connector.export_memory()

with open("memory_backup.json", "w") as f:
    json.dump(exported_data, f, indent=2)

# Import to another agent
connector2 = MemoryConnector("doc-analyzer-v2")
with open("memory_backup.json", "r") as f:
    imported_data = json.load(f)

connector2.import_memory(imported_data)
```

---

## Configuration Reference

### Memory Configuration File

Complete `memory_config.yaml` reference:

```yaml
# Memory system configuration
memory:
  # Enable/disable memory system
  enabled: true

  # Storage configuration
  storage:
    # Storage backend (currently only 'sqlite' supported)
    backend: sqlite

    # Storage location (null = default: ~/.amplihack/memory/{agent_name})
    path: null

    # Maximum storage size in MB
    max_size_mb: 100

    # Enable compression for old experiences
    compression:
      enabled: true
      # Compress experiences older than this (days)
      after_days: 30

  # Experience types this agent can create
  experience_types:
    - success
    - failure
    - pattern
    - insight

  # Retention policy
  retention:
    # Delete experiences older than this (days, null = keep forever)
    max_age_days: 90

    # Maximum number of experiences to keep (null = unlimited)
    max_experiences: 10000

    # When max_experiences reached, delete oldest first
    delete_strategy: oldest_first

  # Learning configuration
  learning:
    # Minimum confidence to apply a learned pattern
    min_confidence_to_apply: 0.7

    # Number of occurrences before recognizing a pattern
    pattern_recognition_threshold: 3

    # Similarity threshold for relevant experience retrieval
    similarity_threshold: 0.7

    # Maximum number of relevant experiences to retrieve
    max_relevant_experiences: 10

  # Performance tuning
  performance:
    # Cache frequently accessed experiences in memory
    enable_caching: true

    # Cache size (number of experiences)
    cache_size: 100

    # Background cleanup (compress and delete old experiences)
    enable_background_cleanup: true
```

---

## Error Handling

### Common Exceptions

```python
from amplihack_memory.exceptions import (
    MemoryStorageError,
    ExperienceNotFoundError,
    MemoryQuotaExceededError,
    InvalidExperienceError
)

# Storage errors
try:
    connector.store_experience(exp)
except MemoryStorageError as e:
    print(f"Storage failed: {e}")
    # Handle: check disk space, permissions

# Experience not found
try:
    exp = connector.get_experience("exp_id_123")
except ExperienceNotFoundError as e:
    print(f"Experience not found: {e}")
    # Handle: ID may be incorrect or experience deleted

# Quota exceeded
try:
    connector.store_experience(exp)
except MemoryQuotaExceededError as e:
    print(f"Memory quota exceeded: {e}")
    # Handle: clear old experiences or increase quota
    connector.clear_old_experiences(older_than_days=30)
    connector.store_experience(exp)

# Invalid experience
try:
    exp = Experience(
        experience_type=ExperienceType.SUCCESS,
        context="",  # Empty context not allowed
        outcome="Result"
    )
    connector.store_experience(exp)
except InvalidExperienceError as e:
    print(f"Invalid experience: {e}")
    # Handle: validate experience before storing
```

---

## Performance Considerations

### Storage Performance

| Operation                | Complexity | Typical Time                  |
| ------------------------ | ---------- | ----------------------------- |
| `store_experience()`     | O(1)       | < 5ms                         |
| `retrieve_experiences()` | O(n)       | < 20ms for 1000 experiences   |
| `retrieve_relevant()`    | O(n log k) | < 50ms for 1000 experiences   |
| `get_statistics()`       | O(1)       | < 2ms                         |
| `clear()`                | O(n)       | < 100ms for 10000 experiences |

### Memory Usage

- **Per Experience**: ~2-5 KB (uncompressed)
- **With Compression**: ~0.5-1.5 KB (3:1 ratio)
- **Index Overhead**: ~10-20% of total storage

### Optimization Tips

```python
# 1. Use batch operations
connector.store_batch(experiences)  # Faster than multiple store_experience()

# 2. Enable caching
connector = MemoryConnector(
    agent_name="my-agent",
    enable_caching=True,
    cache_size=200  # Cache top 200 most accessed experiences
)

# 3. Limit retrieval size
experiences = connector.retrieve_experiences(limit=50)  # Don't retrieve more than needed

# 4. Use specific queries
# Bad: retrieve all then filter
all_exps = connector.retrieve_experiences()
patterns = [e for e in all_exps if e.experience_type == ExperienceType.PATTERN]

# Good: filter at retrieval
patterns = connector.retrieve_experiences(experience_type=ExperienceType.PATTERN)

# 5. Enable compression for long-running agents
connector = MemoryConnector(agent_name="long-runner", enable_compression=True)
```

---

## Thread Safety

The MemoryConnector class is **thread-safe** for concurrent operations:

```python
from concurrent.futures import ThreadPoolExecutor
from amplihack_memory import MemoryConnector

connector = MemoryConnector("concurrent-agent")

def process_and_store(task):
    # Multiple threads can safely store experiences
    exp = process_task(task)
    connector.store_experience(exp)

with ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(process_and_store, tasks)
```

**Note**: Each agent should have its own MemoryConnector instance. Do not share a single connector across multiple agents.

---

## Migration Guide

### From In-Memory to Persistent Memory

If you have an existing agent with in-memory experience tracking:

```python
# Old: In-memory only
class MyAgent:
    def __init__(self):
        self.experiences = []  # Lost when agent stops

    def learn(self, exp):
        self.experiences.append(exp)

# New: Persistent memory
from amplihack_memory import MemoryConnector

class MyAgent:
    def __init__(self):
        self.memory = MemoryConnector(agent_name="my-agent")

    def learn(self, exp):
        self.memory.store_experience(exp)  # Persists across runs
```

### From Legacy Memory Format

Migration script for legacy memory formats:

```python
from amplihack_memory import MemoryConnector, Experience, ExperienceType
import json

def migrate_legacy_memory(legacy_file: str, agent_name: str):
    """Migrate from legacy JSON format to new memory system."""

    connector = MemoryConnector(agent_name)

    with open(legacy_file, 'r') as f:
        legacy_data = json.load(f)

    for item in legacy_data['experiences']:
        exp = Experience(
            experience_type=ExperienceType(item['type']),
            context=item['context'],
            outcome=item['result'],
            confidence=item.get('confidence', 0.5),
            timestamp=datetime.fromisoformat(item['timestamp']),
            metadata=item.get('metadata', {})
        )
        connector.store_experience(exp)

    print(f"Migrated {len(legacy_data['experiences'])} experiences")

# Run migration
migrate_legacy_memory("old_memory.json", "my-agent")
```

---

## See Also

- **[Getting Started Tutorial](../tutorials/memory-enabled-agents-getting-started.md)** - Step-by-step guide
- **[How to Integrate Memory](../howto/integrate-memory-into-agents.md)** - Add memory to existing agents
- **[Memory-Enabled Agents Feature Overview](../features/memory-enabled-agents.md)** - High-level architecture
- **[Troubleshooting Memory Issues](../troubleshooting/memory-enabled-agents.md)** - Common problems and solutions

---

**API Version**: 1.0.0
**Last Updated**: 2026-02-14
