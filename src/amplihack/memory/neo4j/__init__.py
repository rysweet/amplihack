"""Neo4j memory system foundation.

Provides container lifecycle management, connection handling,
schema initialization, and configuration for Neo4j-based memory storage.

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
"""

from .agent_memory import AgentMemoryManager
from .config import Neo4jConfig, get_config, reset_config
from .connector import Neo4jConnector, CircuitBreaker, CircuitState
from .lifecycle import (
    ContainerStatus,
    Neo4jContainerManager,
    check_neo4j_prerequisites,
    ensure_neo4j_running,
)
from .memory_store import MemoryStore
from .models import (
    DeclarativeMemory,
    EpisodicMemory,
    MemoryBase,
    ProceduralMemory,
    ProspectiveMemory,
    ShortTermMemory,
    memory_from_dict,
)
from .schema import SchemaManager
from .retrieval import (
    RetrievalContext,
    IsolationLevel,
    MemoryResult,
    TemporalRetrieval,
    SimilarityRetrieval,
    GraphTraversal,
    HybridRetrieval,
    retrieve_recent_memories,
    retrieve_similar_memories,
)
from .consolidation import (
    QualityMetrics,
    MemoryConsolidator,
    run_consolidation,
)
from .monitoring import (
    OperationType,
    OperationStatus,
    OperationMetric,
    SystemHealth,
    MetricsCollector,
    MonitoredConnector,
    HealthMonitor,
    get_global_metrics,
    log_structured,
)

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
    # Retrieval (Phase 5)
    "RetrievalContext",
    "IsolationLevel",
    "MemoryResult",
    "TemporalRetrieval",
    "SimilarityRetrieval",
    "GraphTraversal",
    "HybridRetrieval",
    "retrieve_recent_memories",
    "retrieve_similar_memories",
    # Consolidation (Phase 5)
    "QualityMetrics",
    "MemoryConsolidator",
    "run_consolidation",
    # Monitoring (Phase 6)
    "OperationType",
    "OperationStatus",
    "OperationMetric",
    "SystemHealth",
    "MetricsCollector",
    "MonitoredConnector",
    "HealthMonitor",
    "get_global_metrics",
    "log_structured",
]
