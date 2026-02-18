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
    LearningAgent: Generic agent for learning from content and answering questions
    WikipediaLearningAgent: Backward-compatible alias for LearningAgent
    HierarchicalMemory: Graph-based hierarchical memory system
    FlatRetrieverAdapter: Backward-compatible adapter for HierarchicalMemory
    GraphRAGRetriever: Graph RAG retriever for knowledge subgraphs
"""

from .action_executor import ActionExecutor
from .agentic_loop import AgenticLoop, RetrievalPlan, SufficiencyEvaluation
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
from .learning_agent import LearningAgent
from .memory_retrieval import MemoryRetriever
from .similarity import compute_similarity, compute_tag_similarity, compute_word_similarity

# Backward compatibility: old name -> new name
WikipediaLearningAgent = LearningAgent

__all__ = [
    "AgenticLoop",
    "ActionExecutor",
    "RetrievalPlan",
    "SufficiencyEvaluation",
    "FlatRetrieverAdapter",
    "GraphRAGRetriever",
    "HierarchicalMemory",
    "KnowledgeEdge",
    "KnowledgeNode",
    "KnowledgeSubgraph",
    "LearningAgent",
    "MemoryCategory",
    "MemoryClassifier",
    "MemoryRetriever",
    "WikipediaLearningAgent",
    "compute_similarity",
    "compute_tag_similarity",
    "compute_word_similarity",
]
