"""Multi-agent configuration templates for generated goal agents.

Provides YAML configs and code snippets for multi-agent packaging:
- Coordinator config (task classification and strategy routing)
- Memory agent config (retrieval specialist)
- Spawner config (dynamic sub-agent creation)
"""

from __future__ import annotations


def get_coordinator_yaml(agent_name: str) -> str:
    """
    Generate coordinator YAML config for multi-agent setup.

    The coordinator classifies incoming tasks and routes them
    to the appropriate strategy/sub-agent.

    Args:
        agent_name: Name of the parent agent

    Returns:
        YAML configuration string
    """
    return f"""# Coordinator Configuration for {agent_name}
# Routes tasks to appropriate sub-agents based on classification

role: task_classifier
agent_name: "{agent_name}"

strategies:
  - entity_centric
  - temporal
  - aggregation
  - full_text
  - simple_all
  - two_phase

classification:
  # Map intent patterns to strategies
  routing:
    entity_lookup: entity_centric
    temporal_query: temporal
    count_or_aggregate: aggregation
    keyword_search: full_text
    comprehensive: simple_all
    multi_step: two_phase

  # Default strategy when classification is uncertain
  default_strategy: simple_all

  # Confidence threshold for strategy selection
  confidence_threshold: 0.6
"""


def get_memory_agent_yaml(agent_name: str) -> str:
    """
    Generate memory agent YAML config for multi-agent setup.

    The memory agent specializes in retrieval and fact management.

    Args:
        agent_name: Name of the parent agent

    Returns:
        YAML configuration string
    """
    return f"""# Memory Agent Configuration for {agent_name}
# Specializes in knowledge retrieval and fact management

role: retrieval_specialist
agent_name: "{agent_name}"

max_facts: 300
summarization_threshold: 1000

retrieval:
  # Search strategies in priority order
  strategies:
    - semantic_search
    - keyword_match
    - recency_weighted

  # Maximum results per query
  max_results: 20

  # Minimum relevance score (0-1)
  min_relevance: 0.3

memory_sharing:
  # Allow sub-agents to read from shared memory
  read_access: true
  # Allow sub-agents to write to shared memory
  write_access: false
  # Shared memory namespace
  namespace: "{agent_name}-shared"
"""


def get_spawner_yaml(
    agent_name: str,
    enable_spawning: bool = True,
    max_concurrent: int = 3,
    timeout: int = 60,
) -> str:
    """
    Generate spawner YAML config for dynamic sub-agent creation.

    The spawner creates specialist sub-agents on demand.

    Args:
        agent_name: Name of the parent agent
        enable_spawning: Whether spawning is enabled
        max_concurrent: Maximum concurrent sub-agents
        timeout: Timeout in seconds for sub-agent execution

    Returns:
        YAML configuration string
    """
    return f"""# Spawner Configuration for {agent_name}
# Manages dynamic creation of specialist sub-agents

enabled: {"true" if enable_spawning else "false"}
agent_name: "{agent_name}"

specialist_types:
  - retrieval
  - analysis
  - synthesis
  - code_generation
  - research

max_concurrent: {max_concurrent}
timeout: {timeout}

lifecycle:
  # Auto-cleanup idle sub-agents
  auto_cleanup: true
  idle_timeout: 30

  # Resource limits per sub-agent
  max_memory_mb: 512
  max_tokens_per_turn: 4096
"""


def get_multi_agent_init_code(agent_name: str) -> str:
    """
    Generate Python initialization code for multi-agent setup.

    Args:
        agent_name: Name of the parent agent

    Returns:
        Python code string
    """
    return f'''
# Multi-Agent Initialization for {agent_name}
import yaml
from pathlib import Path

def load_sub_agent_configs(base_dir: Path | None = None) -> dict:
    """Load all sub-agent configurations from the sub_agents directory."""
    if base_dir is None:
        base_dir = Path(__file__).parent / "sub_agents"

    configs = {{}}
    if not base_dir.exists():
        return configs

    for config_file in base_dir.glob("*.yaml"):
        with open(config_file) as f:
            configs[config_file.stem] = yaml.safe_load(f)

    return configs


def get_coordinator_config(base_dir: Path | None = None) -> dict:
    """Load coordinator configuration."""
    configs = load_sub_agent_configs(base_dir)
    return configs.get("coordinator", {{}})


def get_memory_agent_config(base_dir: Path | None = None) -> dict:
    """Load memory agent configuration."""
    configs = load_sub_agent_configs(base_dir)
    return configs.get("memory_agent", {{}})


def get_spawner_config(base_dir: Path | None = None) -> dict:
    """Load spawner configuration."""
    configs = load_sub_agent_configs(base_dir)
    return configs.get("spawner", {{}})
'''


def get_multi_agent_readme_section(agent_name: str) -> str:
    """
    Generate README section for multi-agent architecture.

    Args:
        agent_name: Name of the parent agent

    Returns:
        Markdown string
    """
    return f"""
## Multi-Agent Architecture

This agent uses a multi-agent architecture for improved task handling.

### Sub-Agents

| Agent | Role | Config |
|-------|------|--------|
| Coordinator | Task classification and strategy routing | `sub_agents/coordinator.yaml` |
| Memory Agent | Knowledge retrieval and fact management | `sub_agents/memory_agent.yaml` |
| Spawner | Dynamic specialist creation | `sub_agents/spawner.yaml` |

### How It Works

1. **Task Classification**: The coordinator analyzes incoming tasks and selects
   the best strategy (entity-centric, temporal, aggregation, etc.)
2. **Memory Management**: The memory agent handles retrieval from the shared
   knowledge base with configurable strategies
3. **Dynamic Spawning**: When specialized expertise is needed, the spawner
   creates temporary sub-agents (retrieval, analysis, synthesis, etc.)

### Configuration

Sub-agent configs are in `sub_agents/`:

```bash
sub_agents/
  coordinator.yaml    # Task routing strategies
  memory_agent.yaml   # Retrieval settings
  spawner.yaml        # Spawning rules and limits
```

Edit these YAML files to customize behavior. All config is externalized --
no hardcoded behavior in the agent code.
"""
