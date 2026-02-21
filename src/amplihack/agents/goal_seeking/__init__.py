"""Goal-seeking agents with PERCEIVE->REASON->ACT->LEARN loop.

Philosophy:
- Single responsibility per module
- Standard library + litellm + amplihack-memory-lib + kuzu
- Self-contained and regeneratable
- LLM-powered reasoning for answer synthesis
- Hierarchical memory with Graph RAG for richer knowledge retrieval
- CognitiveMemory (6-type) for advanced cognitive capabilities

Public API (the "studs"):
    AgenticLoop: Main PERCEIVE->REASON->ACT->LEARN loop
    ActionExecutor: Tool registry with actions
    MemoryRetriever: Kuzu memory search interface (original)
    LearningAgent: Generic agent for learning from content and answering questions
    WikipediaLearningAgent: Backward-compatible alias for LearningAgent
    HierarchicalMemory: Graph-based hierarchical memory system
    FlatRetrieverAdapter: Backward-compatible adapter for HierarchicalMemory
    CognitiveAdapter: 6-type cognitive memory adapter
    GraphRAGRetriever: Graph RAG retriever for knowledge subgraphs
"""

from .action_executor import ActionExecutor
from .agentic_loop import (
    AgenticLoop,
    ReasoningStep,
    ReasoningTrace,
    RetrievalPlan,
    SufficiencyEvaluation,
)
from .cognitive_adapter import HAS_COGNITIVE_MEMORY, CognitiveAdapter
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
from .sub_agents import (
    AgentSpawner,
    CoordinatorAgent,
    MemoryAgent,
    MultiAgentLearningAgent,
    SpawnedAgent,
    SpecialistType,
    get_sdk_tool_names,
    get_sdk_tools,
    inject_sdk_tools,
)

# Backward compatibility: old name -> new name
WikipediaLearningAgent = LearningAgent

__all__ = [
    "AgentSpawner",
    "AgenticLoop",
    "ActionExecutor",
    "CognitiveAdapter",
    "HAS_COGNITIVE_MEMORY",
    "ReasoningStep",
    "ReasoningTrace",
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
    "CoordinatorAgent",
    "MemoryAgent",
    "MultiAgentLearningAgent",
    "SpawnedAgent",
    "SpecialistType",
    "compute_similarity",
    "compute_tag_similarity",
    "compute_word_similarity",
    "get_sdk_tool_names",
    "get_sdk_tools",
    "inject_sdk_tools",
]
