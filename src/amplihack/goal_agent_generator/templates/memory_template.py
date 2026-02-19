"""Memory initialization template for generated goal agents.

Provides code to inject memory capabilities into generated agents.
"""


def get_memory_initialization_code(agent_name: str, storage_path: str = "./memory") -> str:
    """
    Generate memory initialization code for a goal agent.

    Args:
        agent_name: Name of the agent (used for memory namespace)
        storage_path: Path for memory storage (relative to agent directory)

    Returns:
        Python code string for memory initialization
    """
    return f'''
# Memory Initialization
from pathlib import Path
from amplihack_memory import MemoryConnector, ExperienceStore, Experience, ExperienceType

# Initialize memory connector
memory_storage = Path(__file__).parent / "{storage_path}"
memory_connector = MemoryConnector(
    agent_name="{agent_name}",
    storage_path=memory_storage,
)

# Initialize experience store
experience_store = ExperienceStore(
    agent_name="{agent_name}",
    storage_path=memory_storage,
    max_experiences=1000,
    auto_compress=True,
)

# Helper functions for memory operations
def store_success(context: str, outcome: str, confidence: float = 0.9) -> str:
    """Store a successful experience."""
    exp = Experience(
        experience_type=ExperienceType.SUCCESS,
        context=context,
        outcome=outcome,
        confidence=confidence,
    )
    return memory_connector.store_experience(exp)

def store_failure(context: str, outcome: str, confidence: float = 0.9) -> str:
    """Store a failure experience."""
    exp = Experience(
        experience_type=ExperienceType.FAILURE,
        context=context,
        outcome=outcome,
        confidence=confidence,
    )
    return memory_connector.store_experience(exp)

def store_pattern(context: str, outcome: str, confidence: float = 0.85) -> str:
    """Store a pattern observation."""
    exp = Experience(
        experience_type=ExperienceType.PATTERN,
        context=context,
        outcome=outcome,
        confidence=confidence,
    )
    return memory_connector.store_experience(exp)

def store_insight(context: str, outcome: str, confidence: float = 0.8) -> str:
    """Store an insight."""
    exp = Experience(
        experience_type=ExperienceType.INSIGHT,
        context=context,
        outcome=outcome,
        confidence=confidence,
    )
    return memory_connector.store_experience(exp)

def recall_relevant(query: str, limit: int = 5) -> list[Experience]:
    """Search for relevant past experiences."""
    return experience_store.search(query, limit=limit)

def cleanup_memory():
    """Close memory connections."""
    memory_connector.close()
    experience_store.connector.close()
'''


def get_memory_config_yaml(agent_name: str) -> str:
    """
    Generate memory configuration YAML for a goal agent.

    Args:
        agent_name: Name of the agent

    Returns:
        YAML configuration string
    """
    return f"""# Memory Configuration for {agent_name}

memory:
  enabled: true
  agent_name: "{agent_name}"
  storage_path: "./memory"

  # Experience store settings
  max_experiences: 1000
  auto_compress: true
  retention_days: 90

  # Search settings
  semantic_search:
    enabled: true
    min_similarity: 0.5

  # Pattern recognition
  pattern_recognition:
    enabled: true
    min_frequency: 3
    confidence_threshold: 0.7
"""


def get_memory_readme_section() -> str:
    """
    Generate README section documenting memory capabilities.

    Returns:
        Markdown documentation string
    """
    return """
## Memory & Learning

This agent includes built-in memory capabilities using the amplihack-memory-lib.

### Memory Features

- **Experience Storage**: Automatically stores successes, failures, patterns, and insights
- **Semantic Search**: Find relevant past experiences using natural language queries
- **Pattern Recognition**: Detect recurring patterns across experiences
- **Auto-Compression**: Manages memory size with configurable retention policies

### Memory Functions

The agent provides these helper functions:

```python
# Store experiences
store_success(context, outcome, confidence=0.9)
store_failure(context, outcome, confidence=0.9)
store_pattern(context, outcome, confidence=0.85)
store_insight(context, outcome, confidence=0.8)

# Recall experiences
recall_relevant(query, limit=5)  # Returns list[Experience]

# Cleanup
cleanup_memory()  # Close connections when done
```

### Example Usage

```python
# During execution, store what you learn
store_success(
    context="Processed CSV file with 10k rows",
    outcome="Successfully extracted and validated data",
    confidence=0.95
)

# Before similar tasks, recall relevant experiences
past_experiences = recall_relevant("CSV processing")
for exp in past_experiences:
    print(f"Previously: {exp.context} -> {exp.outcome}")
```

### Memory Storage

Experiences are stored in `./memory/` directory:
- `memory_db.sqlite` - SQLite database for structured storage
- Automatic cleanup of old experiences based on retention policy
- Configurable in `memory_config.yaml`
"""
