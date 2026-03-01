"""Hive Mind: Distributed knowledge sharing between goal-seeking agents.

Philosophy:
- Shared blackboard via Kuzu graph for cross-agent knowledge retrieval
- Event-sourced architecture for temporal reasoning and audit trails
- Gossip protocol for epidemic-style knowledge dissemination
- Content-hash deduplication prevents redundant storage
- Each fact records its source_agent_id for provenance

Public API (the "studs"):
    HiveMemoryStore: Low-level shared fact CRUD on a dedicated Kuzu HiveMemory table
    HiveMemoryBridge: Bridges an agent's local memory to the shared hive
    HiveRetrieval: Retrieval strategy that queries shared memory
    MultiAgentHive: Registry + coordinator for agents participating in the hive
    SharedFact: Dataclass for facts in the shared hive
"""

__all__: list[str] = []

# Shared blackboard module (Experiment 1)
try:
    from .blackboard import (
        HiveMemoryBridge,
        HiveMemoryStore,
        HiveRetrieval,
        MultiAgentHive,
        SharedFact,
    )

    __all__ += [
        "HiveMemoryStore",
        "HiveMemoryBridge",
        "HiveRetrieval",
        "MultiAgentHive",
        "SharedFact",
    ]
except ImportError:
    pass

# Event-sourced module (Experiment 2)
try:
    from .event_sourced import (
        EventLog,
        EventSourcedMemory,
        HiveEvent,
        HiveEventBus,
        HiveOrchestrator,
    )

    __all__ += [
        "EventLog",
        "EventSourcedMemory",
        "HiveEvent",
        "HiveEventBus",
        "HiveOrchestrator",
    ]
except ImportError:
    pass

# Gossip protocol module (Experiment 3)
try:
    from .gossip import (
        GossipFact,
        GossipMemoryAdapter,
        GossipMessage,
        GossipNetwork,
        GossipProtocol,
    )

    __all__ += [
        "GossipFact",
        "GossipMemoryAdapter",
        "GossipMessage",
        "GossipNetwork",
        "GossipProtocol",
    ]
except ImportError:
    pass

# Hierarchical knowledge graph module (Experiment 4)
try:
    from .hierarchical import (
        HierarchicalKnowledgeGraph,
        HiveFact,
        LocalFact,
        PromotionManager,
        PromotionPolicy,
        PullManager,
    )

    __all__ += [
        "HierarchicalKnowledgeGraph",
        "HiveFact",
        "LocalFact",
        "PromotionManager",
        "PromotionPolicy",
        "PullManager",
    ]
except ImportError:
    pass

# Transport-agnostic Event Bus (Experiment 4b)
try:
    from .event_bus import (
        AzureServiceBusEventBus,
        BusEvent,
        EventBus,
        LocalEventBus,
        RedisEventBus,
        create_event_bus,
    )

    __all__ += [
        "BusEvent",
        "EventBus",
        "LocalEventBus",
        "AzureServiceBusEventBus",
        "RedisEventBus",
        "create_event_bus",
    ]
except ImportError:
    pass

# Unified hive mind module (Experiment 5)
try:
    from .unified import (
        HiveMindAgent,
        HiveMindConfig,
        UnifiedHiveMind,
    )

    __all__ += [
        "HiveMindAgent",
        "HiveMindConfig",
        "UnifiedHiveMind",
    ]
except ImportError:
    pass

# Learning Agent Bridge (Experiment 6 - Integration)
try:
    from .learning_agent_bridge import (
        AgentConfig,
        HiveAwareLearningAgent,
        HiveAwareMemoryAdapter,
        HiveBridgeConfig,
        create_hive_swarm,
    )

    __all__ += [
        "AgentConfig",
        "HiveAwareLearningAgent",
        "HiveAwareMemoryAdapter",
        "HiveBridgeConfig",
        "create_hive_swarm",
    ]
except ImportError:
    pass

# Kuzu-backed Hive Mind (Experiment 7 - Real Graph DB)
try:
    from .kuzu_hive import (
        AgentRegistry,
        HiveGateway,
        HiveKuzuSchema,
        KuzuHiveMind,
    )

    __all__ += [
        "AgentRegistry",
        "HiveGateway",
        "HiveKuzuSchema",
        "KuzuHiveMind",
    ]
except ImportError:
    pass

# Distributed Hive Mind (Experiment 8 - True Distributed, Own-DB-Per-Agent)
try:
    from .distributed import (
        AgentNode,
        DistributedHiveMind,
        HiveCoordinator,
    )

    __all__ += [
        "AgentNode",
        "DistributedHiveMind",
        "HiveCoordinator",
    ]
except ImportError:
    pass

# Configurable Deployer (Experiment 9 - Dynamic Lifecycle Management)
try:
    from .deployer import (
        AgentConfig as DeployerAgentConfig,
    )
    from .deployer import (
        DeployMode,
        HiveConfig,
        HiveDeployer,
    )

    __all__ += [
        "DeployerAgentConfig",
        "DeployMode",
        "HiveConfig",
        "HiveDeployer",
    ]
except ImportError:
    pass
