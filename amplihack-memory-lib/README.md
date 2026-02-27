# amplihack-memory-lib

Standalone memory system for goal-seeking agents.

## Installation

```bash
pip install -e .
```

## Quick Start

### CognitiveMemory (6-type cognitive memory)

```python
from amplihack_memory import CognitiveMemory

cm = CognitiveMemory(agent_name="my-agent", db_path="./my_agent_db")

# Sensory: short-lived observations (auto-expire after TTL)
sid = cm.record_sensory("text", "User asked about deployment", ttl_seconds=300)

# Working: bounded task context (auto-evicts lowest relevance at capacity)
cm.push_working("goal", "Deploy to production", task_id="task-1", relevance=0.9)

# Episodic: autobiographical events (consolidatable)
cm.store_episode("Deployed v2.0 successfully", source_label="ci-run")

# Semantic: distilled facts with confidence scores
cm.store_fact("kubernetes", "Pods auto-restart on failure", confidence=0.95)

# Procedural: reusable step-by-step procedures
cm.store_procedure("Deploy", ["Build image", "Push to registry", "Apply manifests"])

# Prospective: future-oriented trigger-action pairs
cm.store_prospective("Monitor CPU", "CPU > 90%", "Scale up replicas", priority=2)

# Check triggers against new content
triggered = cm.check_triggers("Alert: CPU usage at 95%")

# Statistics
stats = cm.get_statistics()  # {'sensory': 1, 'working': 1, ..., 'total': 6}
```

### ExperienceStore (flat experience storage)

```python
from amplihack_memory import MemoryConnector, Experience, ExperienceType

connector = MemoryConnector(agent_name="my-agent")

exp = Experience(
    experience_type=ExperienceType.SUCCESS,
    context="Analyzed codebase structure",
    outcome="Found 47 Python files",
    confidence=0.95
)

exp_id = connector.store_experience(exp)
experiences = connector.retrieve_experiences()
```

## Features

### CognitiveMemory

- **6 Memory Types**: Sensory, working, episodic, semantic, procedural, prospective
- **Kuzu Graph Backend**: Relationship edges between memory types (ATTENDED_TO, DERIVES_FROM, CONSOLIDATES)
- **Agent Isolation**: Each agent sees only its own memories via agent_id filtering
- **Bounded Working Memory**: Auto-evicts lowest-relevance slots at capacity (default 20)
- **Sensory TTL**: Auto-expiring observations with configurable time-to-live
- **Episodic Consolidation**: Batch-consolidate old episodes into summaries (with custom summarizer support)
- **Keyword Search**: Search semantic facts and procedural memories by keyword
- **Prospective Triggers**: Store trigger-action pairs evaluated against future content

### ExperienceStore

- **Flat Experience Storage**: Simple key-value experience records
- **Automatic Cleanup**: Retention policies for age and count limits
- **Pattern Recognition**: Automatic detection of recurring patterns
- **Semantic Search**: TF-IDF based relevance scoring
- **Full-Text Search**: SQLite FTS5 for fast content search
- **Compression**: Automatic compression of old experiences

## Architecture

- **CognitiveMemory**: 6-type cognitive memory backed by Kuzu graph database
- **MemoryConnector**: Database connection and lifecycle management
- **Experience**: Core data model for agent experiences
- **ExperienceStore**: High-level storage and retrieval operations
- **PatternDetector**: Automatic pattern recognition from discoveries
- **SemanticSearchEngine**: Relevance-based experience retrieval

## No Amplihack Dependencies

This library is completely standalone and has no dependencies on the amplihack framework. It uses only:

- `kuzu` for graph database operations
- Python standard library

## Philosophy

- **Ruthlessly Simple**: Minimal API surface, clear contracts
- **Zero-BS Implementation**: No stubs, no placeholders
- **Regeneratable**: Can be rebuilt from specification
