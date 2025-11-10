"""Neo4j memory system foundation.

Provides container lifecycle management, connection handling,
schema initialization, and configuration for Neo4j-based memory storage.
Also includes code ingestion metadata tracking for codebase identity and versioning.

Public API:
    # Lifecycle
    ensure_neo4j_running(blocking=False) -> bool
    check_neo4j_prerequisites() -> dict
    Neo4jContainerManager

    # Connection
    Neo4jConnector

    # Schema
    SchemaManager

    # Configuration
    get_config() -> Neo4jConfig
    Neo4jConfig

    # Memory Store
    MemoryStore
    AgentMemoryManager

    # Memory Models
    EpisodicMemory, ShortTermMemory, ProceduralMemory,
    DeclarativeMemory, ProspectiveMemory

    # Code Graph Integration
    BlarifyIntegration
    run_blarify

    # Code Ingestion Metadata
    CodebaseIdentifier, CodebaseIdentity, IngestionMetadata,
    IngestionResult, IngestionTracker

    # Documentation Graph Integration
    DocGraphIntegration

    # External Knowledge Integration
    KnowledgeSource, ExternalDoc, APIReference
    ExternalKnowledgeManager
"""

from .agent_memory import AgentMemoryManager
from .code_graph import BlarifyIntegration, run_blarify
from .config import Neo4jConfig, get_config, reset_config
from .connector import CircuitBreaker, CircuitState, Neo4jConnector
from .consolidation import MemoryConsolidator, QualityMetrics, run_consolidation
from .doc_graph import DocGraphIntegration
from .external_knowledge import (
    APIReference,
    ExternalDoc,
    ExternalKnowledgeManager,
    KnowledgeSource,
)
from .identifier import CodebaseIdentifier
from .ingestion_tracker import IngestionTracker
from .lifecycle import (
    ContainerStatus,
    Neo4jContainerManager,
    check_neo4j_prerequisites,
    ensure_neo4j_running,
)
from .memory_store import MemoryStore
from .models import (
    CodebaseIdentity,
    IngestionMetadata,
    IngestionResult,
    IngestionStatus,
)
from .monitoring import (
    HealthMonitor,
    MetricsCollector,
    MonitoredConnector,
    OperationMetric,
    OperationStatus,
    OperationType,
    SystemHealth,
    get_global_metrics,
    log_structured,
)
from .retrieval import (
    GraphTraversal,
    HybridRetrieval,
    IsolationLevel,
    MemoryResult,
    RetrievalContext,
    SimilarityRetrieval,
    TemporalRetrieval,
    retrieve_recent_memories,
    retrieve_similar_memories,
)
from .schema import SchemaManager

__all__ = [
    # Configuration
    "Neo4jConfig",
    "get_config",
    "reset_config",
    # Connection
    "Neo4jConnector",
    "CircuitBreaker",
    "CircuitState",
    # Lifecycle
    "ContainerStatus",
    "Neo4jContainerManager",
    "ensure_neo4j_running",
    "check_neo4j_prerequisites",
    # Schema
    "SchemaManager",
    # Memory Store
    "MemoryStore",
    "AgentMemoryManager",
    # Memory Models
    "MemoryBase",
    "EpisodicMemory",
    "ShortTermMemory",
    "ProceduralMemory",
    "DeclarativeMemory",
    "ProspectiveMemory",
    "memory_from_dict",
    # Code Ingestion Metadata
    "CodebaseIdentifier",
    "CodebaseIdentity",
    "IngestionMetadata",
    "IngestionResult",
    "IngestionStatus",
    "IngestionTracker",
    # Retrieval
    "RetrievalContext",
    "IsolationLevel",
    "MemoryResult",
    "TemporalRetrieval",
    "SimilarityRetrieval",
    "GraphTraversal",
    "HybridRetrieval",
    "retrieve_recent_memories",
    "retrieve_similar_memories",
    # Consolidation
    "QualityMetrics",
    "MemoryConsolidator",
    "run_consolidation",
    # Monitoring
    "OperationType",
    "OperationStatus",
    "OperationMetric",
    "SystemHealth",
    "MetricsCollector",
    "MonitoredConnector",
    "HealthMonitor",
    "get_global_metrics",
    "log_structured",
    # Code Graph Integration
    "BlarifyIntegration",
    "run_blarify",
    # Documentation Graph Integration
    "DocGraphIntegration",
    # External Knowledge Integration
    "KnowledgeSource",
    "ExternalDoc",
    "APIReference",
    "ExternalKnowledgeManager",
]
