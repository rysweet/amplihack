# Module: BeadsMemoryProvider

## Purpose

Bridge between amplihack's MemoryManager and beads issue tracking system. Stores agent memories as beads issues for persistent, git-distributed memory across sessions.

## Contract

### Inputs

- **BeadsAdapter**: Configured adapter for CLI operations
- **workstream**: Workstream identifier (default: "main")
- **Memory data**: Agent ID, content, type, importance, tags

### Outputs

- **Memory IDs**: Unique identifiers for stored memories
- **MemoryEntry lists**: Retrieved memories from beads
- **SessionContext**: Restored session state with memories and ready work

### Side Effects

- **Beads issues created**: Each memory becomes a beads issue
- **Issue labels updated**: Session, agent, memory type labels applied
- **SQLite updates**: Beads cache updated via CLI
- **JSONL writes**: Synced to git after 5-second debounce

## Public API

```python
from typing import List, Optional, Dict, Any
from pathlib import Path
from .adapter import BeadsAdapter
from .models import BeadsIssue, SessionContext, Result, ProviderError
from amplihack.memory.models import MemoryEntry, MemoryType

class BeadsMemoryProvider:
    """Memory provider that stores agent memories as beads issues.

    Philosophy:
    - Implements memory provider protocol
    - Maps memory entries to beads issues bidirectionally
    - Maintains session-based organization via labels
    - Handles session restoration from git-distributed state

    Mapping Strategy:
    - MemoryEntry → BeadsIssue (1:1)
    - session_id → label "session:TIMESTAMP"
    - agent_id → label "agent:NAME"
    - memory_type → label "memory:TYPE" + issue type
    - importance (1-10) → priority (0-4)
    - tags → issue labels
    - content → issue description (markdown)
    - metadata → stored in beads metadata field
    """

    def __init__(
        self,
        adapter: BeadsAdapter,
        workstream: str = "main",
        session_id: Optional[str] = None,
    ):
        """Initialize provider with beads adapter.

        Args:
            adapter: Configured BeadsAdapter
            workstream: Workstream identifier (affects issue prefix)
            session_id: Session identifier (generated if not provided)
        """
        pass

    def store_memory(
        self,
        agent_id: str,
        title: str,
        content: str,
        memory_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        importance: Optional[int] = None,
    ) -> Result[str, ProviderError]:
        """Store memory as beads issue.

        Creates beads issue with:
        - Title: memory title
        - Description: memory content (supports markdown)
        - Type: mapped from memory_type
        - Priority: converted from importance (1-10 → 0-4)
        - Labels: session, agent, memory type, custom tags

        Args:
            agent_id: Agent storing the memory
            title: Brief memory title
            content: Full memory content (markdown supported)
            memory_type: Type of memory (conversation, decision, pattern, etc.)
            metadata: Additional structured data (JSON)
            tags: Custom tags for categorization
            importance: Importance score 1-10

        Returns:
            Result with beads issue ID on success, ProviderError on failure
        """
        pass

    def retrieve_memories(
        self,
        agent_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Result[List[MemoryEntry], ProviderError]:
        """Retrieve memories from beads issues.

        Queries beads with filters and converts issues back to MemoryEntry objects.

        Args:
            agent_id: Filter by agent
            memory_type: Filter by memory type
            tags: Filter by tags (any match)
            session_id: Filter by session (defaults to current session)
            limit: Maximum results

        Returns:
            Result with list of MemoryEntry on success, ProviderError on failure
        """
        pass

    def restore_session(
        self, session_id: str
    ) -> Result[List[MemoryEntry], ProviderError]:
        """Restore all memories from previous session.

        Queries beads for all issues with session label and converts to MemoryEntry.

        Args:
            session_id: Session identifier to restore

        Returns:
            Result with list of MemoryEntry from session, ProviderError on failure
        """
        pass

    def get_session_context(self) -> Result[SessionContext, ProviderError]:
        """Get current session's full context.

        Returns:
            Result with SessionContext containing:
            - All session memories
            - Active agents
            - Open issues
            - Ready work
            - Session metadata
        """
        pass

    def mark_memory_accessed(
        self, memory_id: str
    ) -> Result[bool, ProviderError]:
        """Update memory's last accessed timestamp.

        Updates issue metadata with accessed_at timestamp.

        Args:
            memory_id: Beads issue ID

        Returns:
            Result with True on success, ProviderError on failure
        """
        pass

    def link_memories(
        self, child_id: str, parent_id: str, relationship: str = "related"
    ) -> Result[bool, ProviderError]:
        """Create dependency link between memories.

        Uses beads dependency system to link related memories.

        Args:
            child_id: Dependent memory (beads issue ID)
            parent_id: Parent memory (beads issue ID)
            relationship: Type of relationship (related, blocks, discovered-from)

        Returns:
            Result with True on success, ProviderError on failure
        """
        pass

    def delete_memory(self, memory_id: str) -> Result[bool, ProviderError]:
        """Delete memory (close beads issue).

        Closes the beads issue rather than deleting to preserve audit trail.

        Args:
            memory_id: Beads issue ID

        Returns:
            Result with True on success, ProviderError on failure
        """
        pass

    def search_memories(
        self, query: str, limit: int = 10
    ) -> Result[List[MemoryEntry], ProviderError]:
        """Full-text search across memory content.

        Uses beads' search capabilities to find matching memories.

        Args:
            query: Search terms
            limit: Maximum results

        Returns:
            Result with matching MemoryEntry list, ProviderError on failure
        """
        pass

    # Private methods

    def _issue_to_memory(self, issue: BeadsIssue) -> MemoryEntry:
        """Convert BeadsIssue to MemoryEntry."""
        pass

    def _memory_to_issue_params(
        self,
        agent_id: str,
        title: str,
        content: str,
        memory_type: str,
        metadata: Optional[Dict],
        tags: Optional[List[str]],
        importance: Optional[int],
    ) -> Dict[str, Any]:
        """Convert memory data to beads create_issue parameters."""
        pass

    def _importance_to_priority(self, importance: Optional[int]) -> int:
        """Convert importance (1-10) to beads priority (0-4)."""
        pass

    def _priority_to_importance(self, priority: int) -> int:
        """Convert beads priority (0-4) to importance (1-10)."""
        pass

    def _memory_type_to_issue_type(self, memory_type: str) -> str:
        """Map memory type to beads issue type."""
        pass

    def _issue_type_to_memory_type(self, issue_type: str) -> str:
        """Map beads issue type back to memory type."""
        pass

    def _build_labels(
        self,
        agent_id: str,
        memory_type: str,
        tags: Optional[List[str]],
    ) -> List[str]:
        """Build beads labels from memory attributes."""
        pass

    def _parse_labels(self, labels: List[str]) -> Dict[str, Any]:
        """Parse beads labels back to memory attributes."""
        pass
```

## Dependencies

### External Modules

- `adapter.py`: BeadsAdapter for CLI operations
- `models.py`: BeadsIssue, SessionContext, Result types
- `amplihack.memory.models`: MemoryEntry, MemoryType

### Standard Library

- `typing`: Type hints
- `datetime`: Timestamp handling
- `json`: Metadata serialization
- `uuid`: Memory ID generation (if needed)

## Implementation Notes

### Mapping Tables

```python
# Importance (1-10) → Priority (0-4)
IMPORTANCE_TO_PRIORITY = {
    10: 0, 9: 0,  # Critical
    8: 1, 7: 1,   # High
    6: 2, 5: 2, 4: 2,  # Medium (default)
    3: 3, 2: 3,   # Low
    1: 4,         # Very low
}

# Priority (0-4) → Importance (1-10) - midpoint mapping
PRIORITY_TO_IMPORTANCE = {
    0: 9,   # Critical → 9
    1: 7,   # High → 7
    2: 5,   # Medium → 5 (default)
    3: 3,   # Low → 3
    4: 1,   # Very low → 1
}

# Memory Type → Issue Type
MEMORY_TYPE_MAP = {
    "conversation": "task",
    "decision": "feature",
    "pattern": "chore",
    "context": "task",
    "learning": "chore",
    "artifact": "task",
}

# Reverse mapping
ISSUE_TYPE_MAP = {
    "task": "context",
    "feature": "decision",
    "chore": "learning",
    "bug": "conversation",  # Rarely used for memories
    "epic": "artifact",
}
```

### Label Construction

```python
def _build_labels(
    self,
    agent_id: str,
    memory_type: str,
    tags: Optional[List[str]],
) -> List[str]:
    """Build beads labels from memory attributes.

    Format:
    - session:TIMESTAMP
    - agent:NAME
    - memory:TYPE
    - Custom tags as-is
    """
    labels = [
        f"session:{self.session_id}",
        f"agent:{agent_id}",
        f"memory:{memory_type}",
    ]

    if tags:
        labels.extend(tags)

    return labels

def _parse_labels(self, labels: List[str]) -> Dict[str, Any]:
    """Parse beads labels back to memory attributes.

    Returns:
        {
            "session_id": str,
            "agent_id": str,
            "memory_type": str,
            "custom_tags": List[str],
        }
    """
    parsed = {
        "session_id": None,
        "agent_id": None,
        "memory_type": None,
        "custom_tags": [],
    }

    for label in labels:
        if label.startswith("session:"):
            parsed["session_id"] = label.split(":", 1)[1]
        elif label.startswith("agent:"):
            parsed["agent_id"] = label.split(":", 1)[1]
        elif label.startswith("memory:"):
            parsed["memory_type"] = label.split(":", 1)[1]
        else:
            parsed["custom_tags"].append(label)

    return parsed
```

### Bidirectional Conversion

```python
def _issue_to_memory(self, issue: BeadsIssue) -> MemoryEntry:
    """Convert BeadsIssue to MemoryEntry."""
    label_data = self._parse_labels(issue.labels)

    return MemoryEntry(
        id=issue.id,  # Use beads issue ID as memory ID
        session_id=label_data["session_id"],
        agent_id=label_data["agent_id"],
        memory_type=MemoryType(label_data["memory_type"]),
        title=issue.title,
        content=issue.description,
        metadata={
            "beads_issue_id": issue.id,
            "beads_priority": issue.priority,
            "beads_status": issue.status,
        },
        created_at=issue.created_at,
        accessed_at=issue.updated_at,
        tags=label_data["custom_tags"],
        importance=self._priority_to_importance(issue.priority),
        expires_at=None,  # Beads doesn't support expiration
        parent_id=issue.blockers[0] if issue.blockers else None,
    )

def _memory_to_issue_params(
    self,
    agent_id: str,
    title: str,
    content: str,
    memory_type: str,
    metadata: Optional[Dict],
    tags: Optional[List[str]],
    importance: Optional[int],
) -> Dict[str, Any]:
    """Convert memory data to beads create_issue parameters."""
    return {
        "title": title,
        "description": content,
        "issue_type": self._memory_type_to_issue_type(memory_type),
        "priority": self._importance_to_priority(importance),
        "labels": self._build_labels(agent_id, memory_type, tags),
        "assignee": agent_id,  # Assign to creating agent
    }
```

### Session Restoration

```python
def restore_session(
    self, session_id: str
) -> Result[List[MemoryEntry], ProviderError]:
    """Restore all memories from previous session."""
    # Query beads for all issues with session label
    result = self.adapter.list_issues(
        labels=[f"session:{session_id}"],
    )

    if result.is_err:
        return Result(value=None, error=ProviderError(f"Failed to restore session: {result.error}"))

    issues = result.value

    # Convert issues to memories
    memories = [self._issue_to_memory(issue) for issue in issues]

    # Sort by created_at
    memories.sort(key=lambda m: m.created_at)

    return Result(value=memories, error=None)
```

## Test Requirements

### Unit Tests (60%)

- ✅ Importance ↔ Priority conversion
- ✅ Memory type ↔ Issue type mapping
- ✅ Label construction and parsing
- ✅ Issue → Memory conversion
- ✅ Memory → Issue params conversion
- ✅ Error handling for invalid inputs

### Integration Tests (30%)

- ✅ Store and retrieve memory cycle
- ✅ Session restoration
- ✅ Multi-agent memory storage
- ✅ Memory linking (dependencies)
- ✅ Search functionality
- ✅ Provider failure fallback

### E2E Tests (10%)

- ✅ Full session lifecycle
  1. Store memories from multiple agents
  2. Link related memories
  3. Restore session in new process
  4. Verify all memories and links intact

## Usage Examples

### Basic Memory Storage

```python
from amplihack.beads import BeadsAdapter, BeadsMemoryProvider

adapter = BeadsAdapter()
provider = BeadsMemoryProvider(adapter, workstream="main")

# Store architect's decision
result = provider.store_memory(
    agent_id="architect",
    title="API Design Decision",
    content="Chose REST over GraphQL because...",
    memory_type="decision",
    importance=8,
    tags=["api-design", "architecture"],
)

if result.is_ok:
    memory_id = result.value
    print(f"Stored memory: {memory_id}")
```

### Memory Retrieval

```python
# Retrieve all architect decisions
result = provider.retrieve_memories(
    agent_id="architect",
    memory_type="decision",
    limit=10,
)

if result.is_ok:
    memories = result.value
    for memory in memories:
        print(f"{memory.title} (importance: {memory.importance})")
```

### Session Restoration

```python
# Restore previous session
last_session_id = "session_20251018_143052"
result = provider.restore_session(last_session_id)

if result.is_ok:
    memories = result.value
    print(f"Restored {len(memories)} memories from last session")

    # Group by agent
    by_agent = {}
    for memory in memories:
        by_agent.setdefault(memory.agent_id, []).append(memory)

    for agent_id, agent_memories in by_agent.items():
        print(f"  {agent_id}: {len(agent_memories)} memories")
```

### Memory Linking

```python
# Link implementation to design decision
design_memory_id = "bd-42"
impl_memory_id = "bd-43"

result = provider.link_memories(
    child_id=impl_memory_id,
    parent_id=design_memory_id,
    relationship="discovered-from",
)

if result.is_ok:
    print("Linked implementation to design decision")
```

### Integration with MemoryManager

```python
from amplihack.memory import MemoryManager
from amplihack.beads import BeadsAdapter, BeadsMemoryProvider

# Initialize with beads provider
adapter = BeadsAdapter()
provider = BeadsMemoryProvider(adapter)

memory_manager = MemoryManager(
    session_id="session_20251018_150000",
    provider=provider,  # Optional beads provider
)

# Use MemoryManager as usual - automatically syncs to beads
memory_id = memory_manager.store(
    agent_id="reviewer",
    title="Code Review Feedback",
    content="Found security issue in auth module...",
    memory_type=MemoryType.CONTEXT,
    importance=9,
)

# Memories automatically synced to beads and git
```

## Performance Considerations

- **Batch Operations**: Store multiple memories in sequence, beads debounces JSONL writes
- **Lazy Loading**: Only restore full memory content when accessed
- **Caching**: Beads' SQLite cache makes repeated queries fast
- **Async Operations**: Consider async version for high-throughput scenarios

## Philosophy Compliance

- ✅ **Ruthless Simplicity**: Direct mapping, no complex abstractions
- ✅ **Zero-BS**: All operations work or return explicit errors
- ✅ **Regeneratable**: Clear contract and mapping rules
- ✅ **Bricks & Studs**: Self-contained with clean public API
- ✅ **Provider Pattern**: Extends existing memory system without breaking changes
