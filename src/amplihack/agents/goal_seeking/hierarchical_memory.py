"""Hierarchical memory system using Kuzu graph database directly.

Backward compatibility: imports from amplihack-memory-lib if installed,
falls back to local implementation for development without the library.

Public API:
    MemoryCategory: Enum of memory types
    KnowledgeNode: Dataclass for graph nodes
    KnowledgeEdge: Dataclass for graph edges
    KnowledgeSubgraph: Dataclass for subgraph results with to_llm_context()
    MemoryClassifier: Rule-based category classifier
    HierarchicalMemory: Main memory class with store/retrieve/subgraph
"""

from __future__ import annotations

try:
    # Prefer the canonical implementation from amplihack-memory-lib
    from amplihack_memory.hierarchical_memory import (
        HierarchicalMemory,
        KnowledgeEdge,
        KnowledgeNode,
        KnowledgeSubgraph,
        MemoryCategory,
        MemoryClassifier,
    )

    _SOURCE = "amplihack_memory"
except ImportError:
    # Library not installed - use local implementation (for development)
    from ._hierarchical_memory_local import (  # type: ignore[no-redef]
        HierarchicalMemory,
        KnowledgeEdge,
        KnowledgeNode,
        KnowledgeSubgraph,
        MemoryCategory,
        MemoryClassifier,
    )

    _SOURCE = "local"


__all__ = [
    "MemoryCategory",
    "KnowledgeNode",
    "KnowledgeEdge",
    "KnowledgeSubgraph",
    "MemoryClassifier",
    "HierarchicalMemory",
]
