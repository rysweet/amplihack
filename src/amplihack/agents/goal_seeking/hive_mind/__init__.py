"""Hive Mind: Distributed knowledge sharing between goal-seeking agents.

Philosophy:
- Content-hash deduplication prevents redundant storage
- Each fact records its source_agent_id for provenance
- Transport-agnostic event bus for inter-agent communication
- Declarative controller for desired-state reconciliation

Production modules (re-exported here):
    HiveGraph, InMemoryHiveGraph, PeerHiveGraph: Graph protocol + backends
    BusEvent, EventBus, LocalEventBus, etc.: Transport-agnostic event bus
    AgentNode, HiveCoordinator, DistributedHiveMind: Distributed hive mind
    HiveController, HiveManifest, etc.: Declarative reconciliation controller
"""

__all__: list[str] = []

# Transport-agnostic Event Bus (production)
try:
    from .event_bus import (
        AzureServiceBusEventBus,
        BusEvent,
        EventBus,
        LocalEventBus,
        RedisEventBus,
        create_event_bus,
        make_event,
    )

    __all__ += [
        "BusEvent",
        "EventBus",
        "LocalEventBus",
        "AzureServiceBusEventBus",
        "RedisEventBus",
        "create_event_bus",
        "make_event",
    ]
except ImportError:
    pass

# Distributed Hive Mind (production)
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

# HiveGraph Protocol & InMemory/P2P backends (production)
try:
    from .hive_graph import HiveAgent as HiveGraphAgent
    from .hive_graph import (
        HiveEdge,
        HiveGraph,
        InMemoryHiveGraph,
        create_hive_graph,
    )
    from .hive_graph import HiveFact as HiveGraphFact

    __all__ += [
        "HiveGraph",
        "HiveGraphAgent",
        "HiveGraphFact",
        "HiveEdge",
        "InMemoryHiveGraph",
        "create_hive_graph",
    ]
except ImportError:
    pass

try:
    from .peer_hive import PeerHiveGraph

    __all__ += [
        "PeerHiveGraph",
    ]
except ImportError:
    pass

# Desired-state HiveController (production)
try:
    from .controller import (
        AgentSpec,
        EventBusConfig,
        GatewayConfig,
        GraphStoreConfig,
        HiveController,
        HiveManifest,
        HiveState,
        InMemoryGateway,
        InMemoryGraphStore,
    )

    __all__ += [
        "AgentSpec",
        "EventBusConfig",
        "GatewayConfig",
        "GraphStoreConfig",
        "HiveController",
        "HiveManifest",
        "HiveState",
        "InMemoryGateway",
        "InMemoryGraphStore",
    ]
except ImportError:
    pass
