"""Hive Mind: Distributed knowledge sharing between goal-seeking agents.

Philosophy:
- Content-hash deduplication prevents redundant storage
- Each fact records its source_agent_id for provenance
- Transport-agnostic event bus for inter-agent communication
- Declarative controller for desired-state reconciliation

Production modules (re-exported here):
    HiveGraph, InMemoryHiveGraph: Graph protocol + backends
    BusEvent, EventBus, LocalEventBus, etc.: Transport-agnostic event bus
    AgentNode, HiveCoordinator, DistributedHiveMind: Distributed hive mind
    HiveController, HiveManifest, etc.: Declarative reconciliation controller
"""

import logging as _logging

_logger = _logging.getLogger(__name__)

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
    _logger.debug("event_bus module not available")

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
    _logger.debug("distributed module not available")

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
    _logger.debug("hive_graph module not available")


# DHT-based Distributed Hive Graph (production)
try:
    from .distributed_hive_graph import DistributedHiveGraph

    __all__ += ["DistributedHiveGraph"]
except ImportError:
    _logger.debug("distributed_hive_graph module not available")

# DHT routing and shard storage
try:
    from .dht import DHTRouter, HashRing, ShardFact, ShardStore

    __all__ += ["DHTRouter", "HashRing", "ShardFact", "ShardStore"]
except ImportError:
    _logger.debug("dht module not available")

# Bloom filter for gossip
try:
    from .bloom import BloomFilter

    __all__ += ["BloomFilter"]
except ImportError:
    _logger.debug("bloom module not available")

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
    _logger.debug("controller module not available")
