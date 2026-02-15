# amplihack-memory-lib

Standalone memory system for goal-seeking agents.

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from amplihack_memory import MemoryConnector, Experience, ExperienceType

# Initialize memory for an agent
connector = MemoryConnector(agent_name="my-agent")

# Store an experience
exp = Experience(
    experience_type=ExperienceType.SUCCESS,
    context="Analyzed codebase structure",
    outcome="Found 47 Python files",
    confidence=0.95
)

exp_id = connector.store_experience(exp)

# Retrieve experiences
experiences = connector.retrieve_experiences()
```

## Features

- **Agent Memory Isolation**: Each agent has isolated memory storage
- **Automatic Cleanup**: Retention policies for age and count limits
- **Pattern Recognition**: Automatic detection of recurring patterns
- **Semantic Search**: TF-IDF based relevance scoring
- **Full-Text Search**: SQLite FTS5 for fast content search
- **Compression**: Automatic compression of old experiences

## Architecture

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
