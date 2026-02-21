"""Multi-agent sub-agent architecture for goal-seeking agents.

Philosophy:
- Coordinator + specialist sub-agents decompose monolithic reasoning
- Each sub-agent has a focused system prompt and tool set
- Shared memory instance across all sub-agents
- Backward compatible: single-agent remains the default

Public API:
    MemoryAgent: Specialized retrieval strategy selection
    CoordinatorAgent: Task classification and routing
    MultiAgentLearningAgent: Drop-in replacement for LearningAgent
"""

from __future__ import annotations

from .coordinator import CoordinatorAgent
from .memory_agent import MemoryAgent
from .multi_agent import MultiAgentLearningAgent

__all__ = [
    "CoordinatorAgent",
    "MemoryAgent",
    "MultiAgentLearningAgent",
]
