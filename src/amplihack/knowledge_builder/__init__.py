"""Knowledge Builder package - Socratic method for deep knowledge exploration.

This package implements a knowledge building system that uses the Socratic method
to generate and answer questions about a topic, then generates comprehensive
knowledge artifacts.

Main entry point: KnowledgeBuilder class from orchestrator module.
"""

from amplihack.knowledge_builder.kb_types import (
    Answer,
    KnowledgeGraph,
    KnowledgeTriplet,
    Question,
)
from amplihack.knowledge_builder.orchestrator import KnowledgeBuilder

__all__ = [
    "KnowledgeBuilder",
    "Question",
    "Answer",
    "KnowledgeTriplet",
    "KnowledgeGraph",
]
