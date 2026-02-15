# Usage Examples for amplihack-memory-lib

## Example 1: Basic Goal-Seeking Agent

```python
from amplihack_memory import MemoryConnector, ExperienceStore

class GoalSeekingAgent:
    def __init__(self, agent_id: str, memory_db: str = "./agent_memory.db"):
        self.agent_id = agent_id
        self.connector = MemoryConnector(memory_db)
        self.store = None

    def start(self):
        """Initialize memory connection."""
        self.connector.connect()
        self.store = ExperienceStore(self.connector)

    def stop(self):
        """Close memory connection."""
        self.connector.close()

    def remember(self, context: str, action: str, outcome: str, importance: int = 5):
        """Store an experience."""
        return self.store.store(
            agent_id=self.agent_id,
            context=context,
            action=action,
            outcome=outcome,
            importance=importance
        )

    def recall_similar(self, context: str, limit: int = 3):
        """Find similar past experiences."""
        return self.store.find_similar(
            agent_id=self.agent_id,
            context=context,
            limit=limit
        )

    def get_recent(self, limit: int = 10):
        """Get recent experiences."""
        return self.store.retrieve(
            agent_id=self.agent_id,
            limit=limit
        )


# Usage
agent = GoalSeekingAgent("analyzer_01")
agent.start()

# Store experience
agent.remember(
    context="User asked to analyze Python codebase",
    action="Scanned src/ directory, found 142 .py files",
    outcome="Identified 2 test coverage gaps in auth module",
    importance=8
)

# Later, when facing similar situation
similar = agent.recall_similar("User asked to analyze codebase")
for exp in similar:
    print(f"Previously: {exp.action} -> {exp.outcome}")

agent.stop()
```

## Example 2: Context Manager Pattern

```python
from amplihack_memory import MemoryConnector, ExperienceStore

def analyze_codebase(agent_id: str, codebase_path: str):
    with MemoryConnector("./memory.db") as conn:
        store = ExperienceStore(conn)

        # Check if we've analyzed this before
        similar = store.find_similar(
            agent_id=agent_id,
            context=f"Analyze {codebase_path}"
        )

        if similar:
            print(f"Found {len(similar)} similar past analyses")
            # Use past experience to optimize current analysis
            for exp in similar:
                print(f"  - {exp.outcome}")

        # Perform analysis
        result = perform_analysis(codebase_path)

        # Store experience
        store.store(
            agent_id=agent_id,
            context=f"Analyze {codebase_path}",
            action="Ran static analysis tools, checked test coverage",
            outcome=result,
            tags=["analysis", "codebase"],
            importance=7
        )

        return result
```

## Example 3: Learning from High-Value Experiences

```python
from amplihack_memory import MemoryConnector, ExperienceStore
from datetime import datetime, timedelta

def learn_best_practices(agent_id: str):
    """Extract lessons from high-importance experiences."""

    with MemoryConnector() as conn:
        store = ExperienceStore(conn)

        # Get high-importance experiences from last 30 days
        since = datetime.now() - timedelta(days=30)

        high_value = store.retrieve(
            agent_id=agent_id,
            min_importance=8,
            since=since,
            limit=50
        )

        # Analyze patterns
        patterns = {}
        for exp in high_value:
            # Group by context patterns
            context_key = exp.context.split()[0]  # First word
            if context_key not in patterns:
                patterns[context_key] = []
            patterns[context_key].append({
                "action": exp.action,
                "outcome": exp.outcome,
                "importance": exp.importance
            })

        # Store learned patterns
        for context, experiences in patterns.items():
            avg_importance = sum(e["importance"] for e in experiences) / len(experiences)
            if avg_importance >= 8:
                store.store(
                    agent_id=agent_id,
                    context=f"Pattern: {context} situations",
                    action=f"Analyzed {len(experiences)} high-value experiences",
                    outcome=f"Best approach: {experiences[0]['action']}",
                    tags=["learning", "pattern"],
                    importance=9
                )

        return patterns
```

## Example 4: Multi-Agent Coordination

```python
from amplihack_memory import MemoryConnector, ExperienceStore

class AgentTeam:
    def __init__(self, team_id: str, agent_ids: list[str]):
        self.team_id = team_id
        self.agent_ids = agent_ids
        self.connector = MemoryConnector(f"./team_{team_id}.db")

    def share_experience(self, from_agent: str, experience_summary: str):
        """Share experience across team."""
        with self.connector as conn:
            store = ExperienceStore(conn)

            # Each agent stores the shared experience
            for agent_id in self.agent_ids:
                if agent_id != from_agent:
                    store.store(
                        agent_id=agent_id,
                        context=f"Shared by {from_agent}",
                        action="Received team knowledge",
                        outcome=experience_summary,
                        tags=["team", "shared"],
                        importance=6
                    )

    def get_team_insights(self, context: str):
        """Get insights from all agents."""
        all_insights = []

        with self.connector as conn:
            store = ExperienceStore(conn)

            for agent_id in self.agent_ids:
                insights = store.find_similar(
                    agent_id=agent_id,
                    context=context,
                    limit=3
                )
                all_insights.extend(insights)

        # Deduplicate and rank by importance
        unique = {exp.id: exp for exp in all_insights}
        ranked = sorted(
            unique.values(),
            key=lambda x: x.importance,
            reverse=True
        )

        return ranked[:10]  # Top 10 insights
```

## Example 5: Experience Statistics and Monitoring

```python
from amplihack_memory import MemoryConnector, ExperienceStore

def monitor_agent_performance(agent_id: str):
    """Monitor agent's memory and learning."""

    with MemoryConnector() as conn:
        store = ExperienceStore(conn)

        stats = store.get_stats(agent_id)

        print(f"Agent: {agent_id}")
        print(f"Total experiences: {stats.total_count}")
        print(f"Average importance: {stats.avg_importance:.1f}/10")
        print(f"Active since: {stats.oldest}")
        print(f"Last activity: {stats.newest}")
        print("\nTag distribution:")
        for tag, count in sorted(
            stats.tag_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(f"  {tag}: {count}")

        # Check for learning progress
        recent = store.retrieve(
            agent_id=agent_id,
            limit=100
        )

        # Calculate trend in importance scores
        recent_avg = sum(e.importance for e in recent[:20]) / 20
        older_avg = sum(e.importance for e in recent[-20:]) / 20

        if recent_avg > older_avg:
            print(f"\n✓ Learning trend: +{recent_avg - older_avg:.1f}")
        else:
            print(f"\n⚠ Learning trend: {recent_avg - older_avg:.1f}")
```

## Example 6: Error Handling

```python
from amplihack_memory import (
    MemoryConnector,
    ExperienceStore,
    ConnectionError,
    StorageError,
    ValidationError
)

def robust_agent_memory(agent_id: str):
    """Demonstrate proper error handling."""

    try:
        # Connection errors
        conn = MemoryConnector("/invalid/path/memory.db")
        conn.connect()
    except ConnectionError as e:
        print(f"Connection failed: {e}")
        # Fallback: use in-memory or default location
        conn = MemoryConnector()  # Uses default path
        conn.connect()

    try:
        store = ExperienceStore(conn)

        # Validation errors
        store.store(
            agent_id=agent_id,
            context="Test",
            action="Test",
            outcome="Test",
            importance=15  # Invalid: must be 1-10
        )
    except ValidationError as e:
        print(f"Validation error: {e}")
        # Correct the input
        store.store(
            agent_id=agent_id,
            context="Test",
            action="Test",
            outcome="Test",
            importance=10
        )

    try:
        # Storage errors (disk full, permissions, etc.)
        for i in range(1000000):
            store.store(
                agent_id=agent_id,
                context=f"Test {i}",
                action="Test",
                outcome="Test"
            )
    except StorageError as e:
        print(f"Storage error: {e}")
        # Handle: retry, cleanup old data, alert user

    finally:
        conn.close()
```

## Example 7: Migration from amplihack.memory.kuzu

```python
# OLD CODE (amplihack.memory.kuzu)
from amplihack.memory.kuzu import KuzuConnector, KuzuBackend
from amplihack.memory.models import MemoryEntry, MemoryType

conn = KuzuConnector()
conn.connect()
backend = KuzuBackend(conn)

memory = MemoryEntry(
    id="123",
    session_id="session1",
    agent_id="agent1",
    memory_type=MemoryType.EPISODIC,
    title="Test",
    content="Test content",
    metadata={},
    created_at=datetime.now(),
    accessed_at=datetime.now()
)
backend.store_memory(memory)


# NEW CODE (amplihack-memory-lib)
from amplihack_memory import MemoryConnector, ExperienceStore

with MemoryConnector() as conn:
    store = ExperienceStore(conn)

    exp_id = store.store(
        agent_id="agent1",
        context="Test situation",
        action="Test action",
        outcome="Test content",
        metadata={},
        importance=5
    )
```

**Key differences**:

1. Simpler API (no session_id, memory_type)
2. Experience-focused (context/action/outcome instead of title/content)
3. Context manager support (automatic cleanup)
4. Importance replaces complex memory types

## Performance Tips

### 1. Batch Operations

```python
# BAD: Multiple connections
for experience in experiences:
    with MemoryConnector() as conn:
        store = ExperienceStore(conn)
        store.store(...)

# GOOD: Single connection
with MemoryConnector() as conn:
    store = ExperienceStore(conn)
    for experience in experiences:
        store.store(...)
```

### 2. Limit Results

```python
# BAD: Retrieve everything
all_experiences = store.retrieve(agent_id="agent1", limit=999999)

# GOOD: Paginate
page_size = 100
experiences = store.retrieve(agent_id="agent1", limit=page_size)
```

### 3. Filter Early

```python
# BAD: Filter in Python
all_exp = store.retrieve(agent_id="agent1", limit=1000)
important = [e for e in all_exp if e.importance >= 8]

# GOOD: Filter in database
important = store.retrieve(
    agent_id="agent1",
    min_importance=8,
    limit=100
)
```

## Testing Patterns

```python
import pytest
from amplihack_memory import MemoryConnector, ExperienceStore

@pytest.fixture
def memory_store(tmp_path):
    """Provide isolated memory store for testing."""
    db_path = tmp_path / "test_memory.db"
    with MemoryConnector(db_path) as conn:
        yield ExperienceStore(conn)

def test_store_retrieve(memory_store):
    """Test basic storage and retrieval."""
    exp_id = memory_store.store(
        agent_id="test_agent",
        context="Test context",
        action="Test action",
        outcome="Test outcome"
    )

    experiences = memory_store.retrieve(agent_id="test_agent")
    assert len(experiences) == 1
    assert experiences[0].id == exp_id
```
