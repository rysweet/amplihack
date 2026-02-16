"""Goal-seeking agents with PERCEIVE→REASON→ACT→LEARN loop.

Philosophy:
- Single responsibility per module
- Standard library + litellm + amplihack-memory-lib only
- Self-contained and regeneratable
- LLM-powered reasoning for answer synthesis

Public API (the "studs"):
    AgenticLoop: Main PERCEIVE→REASON→ACT→LEARN loop
    ActionExecutor: Tool registry with actions
    MemoryRetriever: Kuzu memory search interface
    WikipediaLearningAgent: Specialized agent for Wikipedia learning
"""

from .action_executor import ActionExecutor
from .agentic_loop import AgenticLoop
from .memory_retrieval import MemoryRetriever
from .wikipedia_learning_agent import WikipediaLearningAgent

__all__ = [
    "AgenticLoop",
    "ActionExecutor",
    "MemoryRetriever",
    "WikipediaLearningAgent",
]
