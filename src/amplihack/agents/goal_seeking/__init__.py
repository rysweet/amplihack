"""Goal-seeking agents with PERCEIVE->REASON->ACT->LEARN loop.

Philosophy:
- Single responsibility per module
- Standard library + amplihack.llm + amplihack-memory-lib + kuzu
- Self-contained and regeneratable
- LLM-powered reasoning for answer synthesis
- Hierarchical memory with Graph RAG for richer knowledge retrieval
- CognitiveMemory (6-type) for advanced cognitive capabilities

Public API (the "studs"):
    GoalSeekingAgent: Universal agent with OODA loop (observe/orient/decide/act).
        process(input) is the sole public entry point — no learn_from_content()
        or answer_question() methods are exposed.  The agent classifies input
        internally as "store" or "answer" and writes answers to stdout.
        run_ooda_loop(input_source) drives the loop from any InputSource.
    InputSource: Protocol for event-driven input (next() / close()).
    ListInputSource: Wraps a list of strings (single-agent eval).
    ServiceBusInputSource: Wraps Azure Service Bus with blocking receive.
    StdinInputSource: Reads lines from stdin (interactive use).
    AgenticLoop: Main PERCEIVE->REASON->ACT->LEARN loop
    ActionExecutor: Tool registry with actions
    MemoryRetriever: Kuzu memory search interface (original)
    HierarchicalMemory: Graph-based hierarchical memory system
    FlatRetrieverAdapter: Backward-compatible adapter for HierarchicalMemory
    CognitiveAdapter: 6-type cognitive memory adapter
    GraphRAGRetriever: Graph RAG retriever for knowledge subgraphs

Private implementation details (not part of the public API):
    LearningAgent: Absorbed into Memory.store() and GoalSeekingAgent internals.
        Still importable for backward compatibility but not listed in __all__.
        New code should use GoalSeekingAgent.process() or Memory.store() instead.
    WikipediaLearningAgent: Backward-compatible alias for LearningAgent.
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
from .goal_seeking_agent import GoalSeekingAgent
from .graph_rag_retriever import GraphRAGRetriever
from .hierarchical_memory import (
    HierarchicalMemory,
    KnowledgeEdge,
    KnowledgeNode,
    KnowledgeSubgraph,
    MemoryCategory,
    MemoryClassifier,
)
from .input_source import InputSource, ListInputSource, ServiceBusInputSource, StdinInputSource
from .learning_agent import LearningAgent
from .memory_export import export_memory, import_memory
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
    # Primary public API
    "GoalSeekingAgent",
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
    "InputSource",
    "KnowledgeEdge",
    "KnowledgeNode",
    "KnowledgeSubgraph",
    "MemoryCategory",
    "MemoryClassifier",
    "MemoryRetriever",
    "CoordinatorAgent",
    "MemoryAgent",
    "MultiAgentLearningAgent",
    "SpawnedAgent",
    "SpecialistType",
    "compute_similarity",
    "compute_tag_similarity",
    "compute_word_similarity",
    "export_memory",
    "get_sdk_tool_names",
    "get_sdk_tools",
    "import_memory",
    "inject_sdk_tools",
    # Kept for backward compatibility but not part of the public API.
    # New code should use GoalSeekingAgent.process() or Memory.store().
    # LearningAgent and WikipediaLearningAgent are still importable directly.
]
