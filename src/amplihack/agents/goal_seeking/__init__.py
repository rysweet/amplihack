"""Goal-seeking agents with PERCEIVE->REASON->ACT->LEARN loop.

Philosophy:
- Single responsibility per module
- Standard library + litellm + amplihack-memory-lib + kuzu
- Self-contained and regeneratable
- LLM-powered reasoning for answer synthesis
- Hierarchical memory with Graph RAG for richer knowledge retrieval

Public API (the "studs"):
    AgenticLoop: Main PERCEIVE->REASON->ACT->LEARN loop
    ActionExecutor: Tool registry with actions
    MemoryRetriever: Kuzu memory search interface (original)
    WikipediaLearningAgent: Specialized agent for Wikipedia learning
    HierarchicalMemory: Graph-based hierarchical memory system
    FlatRetrieverAdapter: Backward-compatible adapter for HierarchicalMemory
    GraphRAGRetriever: Graph RAG retriever for knowledge subgraphs
"""

from .action_executor import ActionExecutor
from .agentic_loop import AgenticLoop
from .flat_retriever_adapter import FlatRetrieverAdapter
from .graph_rag_retriever import GraphRAGRetriever
from .hierarchical_memory import (
    HierarchicalMemory,
    KnowledgeEdge,
    KnowledgeNode,
    KnowledgeSubgraph,
    MemoryCategory,
    MemoryClassifier,
)
from .memory_retrieval import MemoryRetriever
from .similarity import compute_similarity, compute_tag_similarity, compute_word_similarity
from .wikipedia_learning_agent import WikipediaLearningAgent

__all__ = [
    "AgenticLoop",
    "ActionExecutor",
    "FlatRetrieverAdapter",
    "GraphRAGRetriever",
    "HierarchicalMemory",
    "KnowledgeEdge",
    "KnowledgeNode",
    "KnowledgeSubgraph",
    "MemoryCategory",
    "MemoryClassifier",
    "MemoryRetriever",
    "WikipediaLearningAgent",
    "compute_similarity",
    "compute_tag_similarity",
    "compute_word_similarity",
]
