"""Templates for goal agent generation."""

from .memory_template import get_memory_initialization_code
from .multi_agent_template import (
    get_coordinator_yaml,
    get_memory_agent_yaml,
    get_multi_agent_init_code,
    get_multi_agent_readme_section,
    get_spawner_yaml,
)

__all__ = [
    "get_memory_initialization_code",
    "get_coordinator_yaml",
    "get_memory_agent_yaml",
    "get_spawner_yaml",
    "get_multi_agent_init_code",
    "get_multi_agent_readme_section",
]
