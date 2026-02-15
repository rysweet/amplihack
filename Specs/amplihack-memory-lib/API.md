# amplihack-memory-lib API Specification v1.0

## Design Philosophy

**Single Responsibility**: This library provides persistent graph-based memory for autonomous agents. Period.

**NOT in scope**: Code graph indexing (that belongs in amplihack, not a standalone library)

## Core API

### 1. MemoryConnector - Database Connection

```python
class MemoryConnector:
    """Kuzu database connection management."""

    def __init__(self, db_path: str | Path | None = None):
        """Initialize connector.

        Args:
            db_path: Path to Kuzu database. Defaults to ./memory.db

        Raises:
            ConnectionError: If database cannot be opened
        """

    def connect(self) -> "MemoryConnector":
        """Open database connection. Returns self for chaining."""

    def close(self) -> None:
        """Close database connection."""

    def __enter__(self) -> "MemoryConnector":
        """Context manager entry."""

    def __exit__(self, *args) -> None:
        """Context manager exit."""

    def verify_connectivity(self) -> bool:
        """Test database connectivity."""
```

### 2. ExperienceStore - Agent Memory Storage

```python
class ExperienceStore:
    """Store and retrieve agent experiences."""

    def __init__(self, connector: MemoryConnector):
        """Initialize store with database connector.

        Args:
            connector: Connected MemoryConnector instance

        Raises:
            ValueError: If connector not connected
        """

    def store(
        self,
        agent_id: str,
        context: str,
        action: str,
        outcome: str,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        importance: int = 5  # 1-10 scale
    ) -> str:
        """Store a new experience.

        Args:
            agent_id: Agent identifier
            context: Situation description
            action: Action taken
            outcome: Result of action
            metadata: Optional structured data
            tags: Optional categorization tags
            importance: Importance score 1-10 (default: 5)

        Returns:
            experience_id: Unique identifier for stored experience

        Raises:
            StorageError: If storage fails
            ValueError: If importance not in 1-10 range
        """

    def retrieve(
        self,
        agent_id: str,
        limit: int = 10,
        min_importance: int = 1,
        tags: list[str] | None = None,
        since: datetime | None = None
    ) -> list[Experience]:
        """Retrieve agent experiences.

        Args:
            agent_id: Agent to query
            limit: Maximum results (default: 10)
            min_importance: Minimum importance score (default: 1)
            tags: Filter by tags (AND logic)
            since: Only experiences after this timestamp

        Returns:
            List of Experience objects, sorted by recency

        Raises:
            QueryError: If query fails
        """

    def find_similar(
        self,
        agent_id: str,
        context: str,
        limit: int = 5
    ) -> list[Experience]:
        """Find experiences with similar context.

        Uses text similarity (not embeddings) via Cypher CONTAINS.

        Args:
            agent_id: Agent to query
            context: Context to match against
            limit: Maximum results (default: 5)

        Returns:
            List of similar experiences, sorted by relevance

        Raises:
            QueryError: If query fails
        """

    def get_stats(self, agent_id: str) -> ExperienceStats:
        """Get statistics for agent's experiences.

        Args:
            agent_id: Agent to query

        Returns:
            ExperienceStats with counts and aggregates
        """
```

### 3. Experience - Data Model

```python
@dataclass
class Experience:
    """Single agent experience record."""

    # Identity
    id: str
    agent_id: str

    # Content
    context: str
    action: str
    outcome: str

    # Metadata
    timestamp: datetime
    importance: int  # 1-10
    tags: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Experience":
        """Create from dictionary."""
```

### 4. ExperienceStats - Statistics Model

```python
@dataclass
class ExperienceStats:
    """Experience statistics for an agent."""

    agent_id: str
    total_count: int
    avg_importance: float
    oldest: datetime
    newest: datetime
    tag_distribution: dict[str, int]  # tag -> count
```

### 5. QueryBuilder - Helper Utilities

```python
class QueryBuilder:
    """Helper for common query patterns."""

    @staticmethod
    def recent_by_tag(
        agent_id: str,
        tag: str,
        days: int = 7,
        limit: int = 10
    ) -> str:
        """Generate Cypher query for recent experiences by tag.

        Returns:
            Cypher query string with parameters
        """

    @staticmethod
    def high_importance(
        agent_id: str,
        min_importance: int = 8,
        limit: int = 10
    ) -> str:
        """Generate query for high-importance experiences."""

    @staticmethod
    def context_contains(
        agent_id: str,
        keywords: list[str],
        limit: int = 10
    ) -> str:
        """Generate query for context keyword matching."""
```

## Error Handling

```python
class MemoryLibError(Exception):
    """Base exception for memory library."""

class ConnectionError(MemoryLibError):
    """Database connection failed."""

class StorageError(MemoryLibError):
    """Experience storage failed."""

class QueryError(MemoryLibError):
    """Query execution failed."""

class ValidationError(MemoryLibError):
    """Input validation failed."""
```

## Usage Examples

### Basic Storage and Retrieval

```python
from amplihack_memory import MemoryConnector, ExperienceStore

# Initialize
with MemoryConnector("./agent_memory.db") as conn:
    store = ExperienceStore(conn)

    # Store experience
    exp_id = store.store(
        agent_id="goal_seeker_1",
        context="User requested file analysis",
        action="Analyzed src/ directory structure",
        outcome="Found 142 Python files, 2 test gaps",
        tags=["analysis", "codebase"],
        importance=7
    )

    # Retrieve recent
    recent = store.retrieve(
        agent_id="goal_seeker_1",
        limit=5
    )

    # Find similar
    similar = store.find_similar(
        agent_id="goal_seeker_1",
        context="User requested file analysis"
    )
```

### Statistics and Monitoring

```python
# Get agent stats
stats = store.get_stats(agent_id="goal_seeker_1")
print(f"Total: {stats.total_count}")
print(f"Avg importance: {stats.avg_importance:.1f}")
print(f"Tags: {stats.tag_distribution}")
```

### Advanced Queries

```python
from amplihack_memory import QueryBuilder

# Recent by tag
query = QueryBuilder.recent_by_tag(
    agent_id="goal_seeker_1",
    tag="analysis",
    days=7
)

# High importance only
query = QueryBuilder.high_importance(
    agent_id="goal_seeker_1",
    min_importance=8
)
```

## Design Decisions

### Why NOT include code graph?

Code graph (CodeFile, CodeClass, CodeFunction) is **domain-specific** to code analysis. A standalone memory library should be **domain-agnostic** - it stores experiences, not code entities.

**Separation of concerns**:

- amplihack-memory-lib: Generic agent memory
- amplihack (main): Code graph indexing as one USE CASE of memory library

### Why text similarity instead of embeddings?

Embeddings require:

- External models (OpenAI, sentence-transformers)
- Dependency bloat
- Complexity

Text similarity via Cypher CONTAINS is:

- Zero dependencies
- Fast (< 50ms)
- Good enough for 80% of use cases

Add embeddings later if needed (v2), not now.

### Why importance score instead of relevance?

- Importance is agent-assigned (explicit)
- Relevance is query-computed (implicit)
- Simpler to implement and understand
- Can compute relevance later from importance + recency

## Migration from amplihack.memory.kuzu

Current amplihack code:

```python
from amplihack.memory.kuzu import KuzuConnector, KuzuCodeGraph

conn = KuzuConnector()
graph = KuzuCodeGraph(conn)
```

New standalone library:

```python
from amplihack_memory import MemoryConnector, ExperienceStore

conn = MemoryConnector()
store = ExperienceStore(conn)
```

**Breaking changes**:

1. KuzuCodeGraph removed (stays in amplihack)
2. Experience schema replaces MemoryEntry
3. Simpler API (fewer types)

**Migration strategy**:

1. Keep current amplihack.memory.kuzu untouched
2. Build amplihack-memory-lib separately
3. Gradual migration as new agents adopt library
4. Deprecation after 6 months
