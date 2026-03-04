"""Multi-agent sub-agent architecture for goal-seeking agents.

Philosophy:
- Coordinator + specialist sub-agents decompose monolithic reasoning
- Each sub-agent has a focused system prompt and tool set
- Shared memory instance across all sub-agents
- Backward compatible: single-agent remains the default
- AgentSpawner enables dynamic sub-agent creation at runtime
- ToolInjector provides SDK-specific tool injection

Public API:
    MemoryAgent: Specialized retrieval strategy selection
    CoordinatorAgent: Task classification and routing
    MultiAgentLearningAgent: Drop-in replacement for LearningAgent
    AgentSpawner: Dynamic sub-agent creation for complex tasks
    SpawnedAgent: Dataclass representing a spawned sub-agent
    SpecialistType: Enum of specialist types
    inject_sdk_tools: Inject SDK-specific tools into agents
    get_sdk_tools: Get SDK-specific tool definitions
    get_sdk_tool_names: Get SDK-specific tool names
"""

from __future__ import annotations

from .agent_spawner import AgentSpawner, SpawnedAgent, SpecialistType
from .coordinator import CoordinatorAgent
from .memory_agent import MemoryAgent
from .multi_agent import MultiAgentLearningAgent
from .tool_injector import get_sdk_tool_names, get_sdk_tools, inject_sdk_tools

__all__ = [
    "AgentSpawner",
    "CoordinatorAgent",
    "MemoryAgent",
    "MultiAgentLearningAgent",
    "SpawnedAgent",
    "SpecialistType",
    "get_sdk_tool_names",
    "get_sdk_tools",
    "inject_sdk_tools",
]
