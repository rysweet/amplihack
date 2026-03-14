"""DistributedHiveGraph — DHT-sharded implementation of HiveGraph protocol.

Each agent owns a shard of the fact space. Facts are distributed via
consistent hashing. Queries route to relevant shard owners instead of
scanning all agents. Gossip protocol ensures eventual consistency.

This replaces InMemoryHiveGraph for large-scale (100+ agent) deployments
where the centralized approach causes memory exhaustion.

Architecture:
    ┌──────────────────────────────────────┐
    │       Consistent Hash Ring (DHT)      │
    │  Facts hashed → stored on shard owner │
    └──┬──────────┬──────────┬─────────┬───┘
       │          │          │         │
    Agent 0    Agent 1    Agent 2    Agent N
    (shard)    (shard)    (shard)    (shard)

    Gossip: bloom filter exchange → pull missing facts
    Query: DHT lookup → fan-out to K agents → RRF merge

Philosophy:
- Agent-centric: each agent holds only its shard
- O(F/N) memory per agent instead of O(F) total
- O(K) query fan-out instead of O(N)
- Reuses existing CRDT, RRF, and embedding infrastructure
- Drop-in replacement for InMemoryHiveGraph protocol
- Dependency injection for shard transport — agent code is transport-agnostic

Public API:
    ShardTransport: Protocol for pluggable shard routing
    LocalShardTransport: In-process transport backed by DHTRouter
    ServiceBusShardTransport: Azure Service Bus transport with correlation_id
    DistributedHiveGraph: HiveGraph protocol implementation using DHT
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import logging
import random
import threading
import uuid
from typing import Any, Protocol, runtime_checkable

from .bloom import BloomFilter
from .constants import (
    BROADCAST_TAG_PREFIX,
    DEFAULT_BROADCAST_THRESHOLD,
    DEFAULT_TRUST_SCORE,
    FACT_ID_HEX_LENGTH,
    MAX_TRUST_SCORE,
)
from .dht import DEFAULT_REPLICATION_FACTOR, DHTRouter, ShardFact
from .hive_graph import HiveAgent, HiveEdge, HiveFact

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ShardTransport Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ShardTransport(Protocol):
    """Protocol for pluggable shard routing.

    Implementations route query_shard and store_on_shard operations to the
    appropriate shard — in-process (LocalShardTransport) or over the network
    (ServiceBusShardTransport). DistributedHiveGraph delegates all shard I/O
    to the injected transport; it never branches on transport type.
    """

    def query_shard(self, agent_id: str, query: str, limit: int) -> list[ShardFact]:
        """Query a specific agent's shard and return matching ShardFacts."""
        ...

    def store_on_shard(self, agent_id: str, fact: ShardFact) -> None:
        """Store a fact on a specific agent's shard."""
        ...


# ---------------------------------------------------------------------------
# LocalShardTransport — in-process, backed by DHTRouter
# ---------------------------------------------------------------------------


class LocalShardTransport:
    """In-process shard transport that directly accesses DHTRouter shards.

    No serialisation, no network — all shard I/O happens in the same process.
    This is the default transport for local evaluation and testing.

    Args:
        router: The DHTRouter whose ShardStores this transport accesses.
    """

    def __init__(self, router: DHTRouter) -> None:
        self._router = router

    def query_shard(self, agent_id: str, query: str, limit: int) -> list[ShardFact]:
        """Search a specific agent's shard directly."""
        shard = self._router.get_shard(agent_id)
        if shard is None:
            return []
        return shard.search(query, limit=limit)

    def store_on_shard(self, agent_id: str, fact: ShardFact) -> None:
        """Store a fact in a specific agent's shard directly."""
        shard = self._router.get_shard(agent_id)
        if shard is None:
            return
        # Mirror DHTRouter.store_fact: propagate embedding_generator if set
        gen = self._router._embedding_generator
        if gen is not None and shard._embedding_generator is None:
            shard.set_embedding_generator(gen)
        shard.store(fact)


# ---------------------------------------------------------------------------
# ServiceBusShardTransport — Azure Service Bus (or LocalEventBus stand-in)
# ---------------------------------------------------------------------------


class ServiceBusShardTransport:
    """Shard transport that routes cross-shard operations via an event bus.

    Uses SHARD_QUERY / SHARD_RESPONSE for reads and SHARD_STORE for writes.
    Local shard access (agent_id == self._agent_id) bypasses the bus for
    efficiency.

    The transport must be bound to a DistributedHiveGraph via bind_local()
    before handle_shard_query() can respond to incoming queries.
    DistributedHiveGraph.__init__ calls bind_local(self) automatically when
    a ServiceBusShardTransport is injected.

    Args:
        event_bus: Any EventBus implementation (AzureServiceBusEventBus or
                   LocalEventBus for testing).
        agent_id: This agent's own ID — determines which shard is "local".
        timeout: Seconds to wait for a SHARD_RESPONSE (default 5.0).
    """

    def __init__(self, event_bus: Any, agent_id: str, timeout: float = 5.0) -> None:
        self._bus = event_bus
        self._agent_id = agent_id
        self._timeout = timeout
        # Pending cross-shard queries: correlation_id → (done_event, facts_list)
        self._pending: dict[str, tuple[threading.Event, list]] = {}
        self._pending_lock = threading.Lock()
        self._local_graph: Any = None  # Bound by DistributedHiveGraph.__init__

    def bind_local(self, graph: Any) -> None:
        """Bind the DistributedHiveGraph that owns this transport's local shard."""
        self._local_graph = graph

    # -- ShardTransport protocol ---------------------------------------------

    def query_shard(self, agent_id: str, query: str, limit: int) -> list[ShardFact]:
        """Query a shard — local bypass for own shard, bus round-trip for remote."""
        if agent_id == self._agent_id and self._local_graph is not None:
            shard = self._local_graph._router.get_shard(agent_id)
            if shard is None:
                return []
            return shard.search(query, limit=limit)

        # Remote query: publish SHARD_QUERY and wait for SHARD_RESPONSE
        correlation_id = uuid.uuid4().hex
        done = threading.Event()
        results: list[dict] = []
        with self._pending_lock:
            self._pending[correlation_id] = (done, results)

        try:
            from .event_bus import make_event

            query_event = make_event(
                event_type="SHARD_QUERY",
                source_agent=self._agent_id,
                payload={
                    "query": query,
                    "limit": limit,
                    "correlation_id": correlation_id,
                    "target_agent": agent_id,
                },
            )
            self._bus.publish(query_event)
            done.wait(timeout=self._timeout)
        finally:
            with self._pending_lock:
                self._pending.pop(correlation_id, None)

        return [
            ShardFact(
                fact_id=f.get("fact_id", ""),
                content=f.get("content", ""),
                concept=f.get("concept", ""),
                confidence=f.get("confidence", 0.8),
                source_agent=f.get("source_agent", ""),
                tags=f.get("tags", []),
            )
            for f in results
            if f.get("content")
        ]

    def store_on_shard(self, agent_id: str, fact: ShardFact) -> None:
        """Store a fact — local bypass for own shard, SHARD_STORE for remote."""
        if agent_id == self._agent_id and self._local_graph is not None:
            shard = self._local_graph._router.get_shard(agent_id)
            if shard is None:
                return
            gen = self._local_graph._router._embedding_generator
            if gen is not None and shard._embedding_generator is None:
                shard.set_embedding_generator(gen)
            shard.store(fact)
            return

        # Remote store: publish SHARD_STORE
        from .event_bus import make_event

        store_event = make_event(
            event_type="SHARD_STORE",
            source_agent=self._agent_id,
            payload={
                "target_agent": agent_id,
                "fact": {
                    "fact_id": fact.fact_id,
                    "content": fact.content,
                    "concept": fact.concept,
                    "confidence": fact.confidence,
                    "source_agent": fact.source_agent,
                    "tags": list(fact.tags),
                },
            },
        )
        self._bus.publish(store_event)

    def handle_shard_store(self, event: Any) -> None:
        """Store a replicated fact from an incoming SHARD_STORE event.

        Called from the background shard-query listener thread when a peer
        agent broadcasts a fact for replication. Stores the fact in this
        agent's local shard so cross-shard queries are not needed later.

        target_agent filter: only store if this event targets us or has no
        target (broadcast). Avoids double-processing.
        """
        if self._local_graph is None:
            return
        payload = getattr(event, "payload", None) or {}
        target_agent = payload.get("target_agent", "")
        if target_agent and target_agent != self._agent_id:
            return
        fact_dict = payload.get("fact", {})
        if not fact_dict.get("content"):
            return

        shard = self._local_graph._router.get_shard(self._agent_id)
        if shard is None:
            return
        gen = self._local_graph._router._embedding_generator
        if gen is not None and shard._embedding_generator is None:
            shard.set_embedding_generator(gen)

        replica = ShardFact(
            fact_id=fact_dict.get("fact_id", ""),
            content=fact_dict.get("content", ""),
            concept=fact_dict.get("concept", ""),
            confidence=fact_dict.get("confidence", 0.8),
            source_agent=fact_dict.get("source_agent", event.source_agent),
            tags=fact_dict.get("tags", []),
        )
        stored = shard.store(replica)
        logger.debug(
            "Agent %s stored replicated fact from %s (stored=%s, content=%.40s)",
            self._agent_id,
            event.source_agent,
            stored,
            replica.content,
        )

    # -- Listener-side handlers (called by background thread) ----------------

    def handle_shard_query(self, event: Any, agent: Any = None) -> None:
        """Respond to an incoming SHARD_QUERY with a SHARD_RESPONSE.

        Searches ONLY this agent's own local shard — never fans out via query_facts.
        Calling query_facts here would cause recursive SHARD_QUERY loops since
        query_facts itself publishes SHARD_QUERY events to all other agents.

        If ``agent`` is provided and has a ``memory.search()`` method, searches
        via the full CognitiveAdapter path (n-gram overlap, reranking, semantic
        matching) instead of the primitive ShardStore.search(). This makes
        cross-shard retrieval quality equal to local retrieval.

        target_agent filter: ignores queries not addressed to this agent.
        Without this filter all agents respond to every SHARD_QUERY, causing
        wrong-agent responses to arrive first on Azure Service Bus and the
        correct agent's facts to be dropped after pending[correlation_id] is
        removed (root cause of the 49% vs 90% eval gap).
        """
        if self._local_graph is None:
            return
        payload = getattr(event, "payload", None) or {}
        query = payload.get("query", "")
        limit = payload.get("limit", 20)
        correlation_id = payload.get("correlation_id", "")
        target_agent = payload.get("target_agent", "")
        # Only respond if this query targets us (or has no target — broadcast)
        if target_agent and target_agent != self._agent_id:
            return
        if not query or not correlation_id:
            return

        # Prefer CognitiveAdapter search (full quality) over raw ShardStore
        facts_payload = _search_for_shard_response(
            query=query,
            limit=limit,
            agent=agent,
            local_graph=self._local_graph,
            agent_id=self._agent_id,
        )
        try:
            from .event_bus import make_event

            response = make_event(
                event_type="SHARD_RESPONSE",
                source_agent=self._agent_id,
                payload={
                    "correlation_id": correlation_id,
                    "facts": facts_payload,
                },
            )
            self._bus.publish(response)
            logger.debug(
                "Agent %s responded to SHARD_QUERY correlation=%s with %d facts",
                self._agent_id,
                correlation_id,
                len(facts_payload),
            )
        except Exception:
            logger.debug("Failed to publish SHARD_RESPONSE", exc_info=True)

    def handle_shard_response(self, event: Any) -> None:
        """Collect a SHARD_RESPONSE and wake the waiting query_shard() call.

        Called from the background shard-query listener thread. Signals the
        threading.Event so the blocked query_shard() returns without sleep.
        """
        payload = getattr(event, "payload", None) or {}
        correlation_id = payload.get("correlation_id", "")
        if not correlation_id:
            return
        with self._pending_lock:
            pending = self._pending.get(correlation_id)
        if pending:
            done_event, results = pending
            results.extend(payload.get("facts", []))
            done_event.set()
            logger.debug(
                "Agent %s received SHARD_RESPONSE correlation=%s (%d facts)",
                self._agent_id,
                correlation_id,
                len(payload.get("facts", [])),
            )


# ---------------------------------------------------------------------------
# Shared helper: search for SHARD_RESPONSE facts (used by both transports)
# ---------------------------------------------------------------------------


def _search_for_shard_response(
    query: str,
    limit: int,
    agent: Any,
    local_graph: Any,
    agent_id: str,
) -> list[dict]:
    """Return a list of fact dicts for inclusion in a SHARD_RESPONSE.

    Uses agent.memory.search_local() (CognitiveAdapter LOCAL-ONLY path) to
    avoid recursive SHARD_QUERY storms.  Falls back to direct ShardStore.search()
    if the agent is None or raises an exception.

    CRITICAL: Must NEVER call agent.memory.search() here — that triggers
    _search_hive() → query_facts() → SHARD_QUERY to all agents → each agent
    calls _search_for_shard_response() again → infinite recursion.

    CognitiveAdapter.search_local() returns dicts with ``outcome``/``context``/
    ``confidence`` keys (not objects).  ShardFact objects use ``content``/
    ``concept`` attributes.  Both are handled here so the SHARD_RESPONSE
    always carries the actual fact text.
    """
    # CognitiveAdapter LOCAL-ONLY path: n-gram + reranking, NO hive search
    if agent is not None and hasattr(agent, "memory") and hasattr(agent.memory, "search_local"):
        try:
            mem_results = agent.memory.search_local(query, limit=limit)
            facts = []
            for f in mem_results:
                if isinstance(f, dict):
                    # CognitiveAdapter returns dicts: outcome/context/confidence keys
                    content = f.get("outcome") or f.get("content", "")
                    if not content:
                        continue
                    facts.append(
                        {
                            "fact_id": f.get("experience_id", ""),
                            "content": content,
                            "concept": f.get("context") or f.get("concept", ""),
                            "confidence": float(f.get("confidence", 0.8)),
                            "source_agent": agent_id,
                            "tags": list(f.get("tags", [])),
                        }
                    )
                else:
                    # ShardFact or similar object with .content attribute
                    content = getattr(f, "content", "")
                    if not content:
                        continue
                    facts.append(
                        {
                            "fact_id": getattr(f, "fact_id", ""),
                            "content": content,
                            "concept": getattr(f, "concept", ""),
                            "confidence": float(getattr(f, "confidence", 0.8)),
                            "source_agent": getattr(f, "source_agent", agent_id),
                            "tags": list(getattr(f, "tags", [])),
                        }
                    )
            return facts
        except Exception:
            logger.debug(
                "CognitiveAdapter search failed for %s, falling back to shard",
                agent_id,
                exc_info=True,
            )

    # Fallback: raw ShardStore search (primitive keyword tokenisation)
    shard = local_graph._router.get_shard(agent_id)
    if not shard:
        return []
    shard_facts = shard.search(query, limit=limit)
    hive_facts = [local_graph._shard_to_hive_fact(sf) for sf in shard_facts]
    return [
        {
            "fact_id": f.fact_id,
            "content": f.content,
            "concept": f.concept,
            "confidence": f.confidence,
            "source_agent": f.source_agent,
            "tags": list(getattr(f, "tags", [])),
        }
        for f in hive_facts
    ]


# ---------------------------------------------------------------------------
# EventHubsShardTransport — Azure Event Hubs (partition-key routing)
# ---------------------------------------------------------------------------


class EventHubsShardTransport:
    """Shard transport routing cross-shard operations via Azure Event Hubs.

    Uses partition-key routing for delivery:
    - SHARD_QUERY published with ``partition_key=target_agent`` so all queries
      for a given agent consistently land on the same partition.
    - SHARD_RESPONSE published with ``partition_key=requesting_agent`` so
      responses route back to the querying agent's partition.

    Each agent has a dedicated consumer group (``cg-{agent_id}``) that reads
    from all partitions and filters by ``target_agent`` in the event body.
    A background receive thread fills an internal mailbox; ``poll()`` drains
    it for the ``_shard_query_listener``.

    Correlation via ``correlation_id + threading.Event`` — same pattern as
    ``ServiceBusShardTransport``.

    ``handle_shard_query`` uses ``agent.memory.search_local()`` (CognitiveAdapter
    LOCAL-ONLY search) when an agent instance is provided, falling back to raw
    ShardStore search.  Must NEVER use ``agent.memory.search()`` — that triggers
    recursive SHARD_QUERY storms via ``_search_hive()`` → ``query_facts()``.

    Args:
        connection_string: Event Hubs namespace connection string.
        eventhub_name: Name of the Event Hub (e.g. ``hive-shards``).
        agent_id: This agent's own ID — determines which events to handle.
        consumer_group: Consumer group name (default: ``cg-{agent_id}``).
        timeout: Seconds to wait for SHARD_RESPONSE (default 5.0).
        _start_receiving: Set False to skip the background receive thread
            (useful for unit tests that drive the mailbox directly).
    """

    def __init__(
        self,
        connection_string: str,
        eventhub_name: str,
        agent_id: str,
        consumer_group: str | None = None,
        timeout: float = 5.0,
        _start_receiving: bool = True,
    ) -> None:
        self._agent_id = agent_id
        self._timeout = timeout
        self._connection_string = connection_string
        self._eventhub_name = eventhub_name
        self._consumer_group = consumer_group or f"cg-{agent_id}"
        self._local_graph: Any = None
        self._local_agent: Any = None  # Bound via bind_agent() for LOCAL queries

        # Partition routing: each agent reads from a deterministic partition
        # (agent_index % num_partitions) to avoid consumer-group load-balancer
        # competition when multiple agents share a consumer group.
        self._num_partitions: int | None = None

        # Pending cross-shard queries: correlation_id → (done_event, facts_list)
        self._pending: dict[str, tuple[threading.Event, list]] = {}
        self._pending_lock = threading.Lock()

        # Persistent producer — lazy-initialized, reused across all _publish()
        # calls to avoid ~1.5s AMQP connection setup per publish.
        self._producer: Any = None
        self._producer_lock = threading.Lock()

        # Mailbox: events targeted at this agent (filled by _receive_loop)
        self._mailbox: list[Any] = []
        self._mailbox_lock = threading.Lock()
        self._mailbox_ready = threading.Event()

        # Background receive thread
        self._shutdown = threading.Event()
        self._recv_thread = threading.Thread(
            target=self._receive_loop,
            daemon=True,
            name=f"eh-recv-{agent_id}",
        )
        if _start_receiving:
            self._recv_thread.start()

    def bind_local(self, graph: Any) -> None:
        """Bind the DistributedHiveGraph that owns this transport's local shard."""
        self._local_graph = graph

    def bind_agent(self, agent: Any) -> None:
        """Bind the GoalSeekingAgent for high-quality LOCAL shard queries.

        When set, LOCAL shard queries in query_shard() use
        _search_for_shard_response() (CognitiveAdapter n-gram + reranking)
        instead of primitive ShardStore.search().
        """
        self._local_agent = agent

    # -- Partition routing ---------------------------------------------------

    @staticmethod
    def _agent_index(agent_id: str) -> int:
        """Extract numeric index from 'agent-N' format."""
        try:
            return int(agent_id.rsplit("-", 1)[-1])
        except (ValueError, IndexError):
            return abs(hash(agent_id))

    def _get_num_partitions(self) -> int:
        """Get partition count (cached). Falls back to 32 if query fails."""
        if self._num_partitions is not None:
            return self._num_partitions
        try:
            from azure.eventhub import EventHubConsumerClient  # type: ignore

            c = EventHubConsumerClient.from_connection_string(
                self._connection_string,
                consumer_group=self._consumer_group,
                eventhub_name=self._eventhub_name,
            )
            pids = c.get_partition_ids()
            c.close()
            self._num_partitions = len(pids)
        except Exception:
            self._num_partitions = 32
        return self._num_partitions

    def _target_partition(self, agent_id: str) -> str:
        """Deterministic partition for an agent: agent_index % num_partitions."""
        return str(self._agent_index(agent_id) % self._get_num_partitions())

    # -- Background receive loop ---------------------------------------------

    def _receive_loop(self) -> None:
        """Receive Event Hubs events into the mailbox (runs in background thread).

        SHARD_RESPONSE events are handled INLINE (not via mailbox) to eliminate
        the latency of waiting for _shard_query_listener to poll. This wakes
        the blocked query_shard() call immediately when the response arrives.
        """
        import json

        try:
            from azure.eventhub import EventHubConsumerClient  # type: ignore[import-unresolved]
        except ImportError:
            logger.error(
                "azure-eventhub not installed — EventHubsShardTransport cannot receive events"
            )
            return

        def _on_event(partition_context: Any, event: Any) -> None:
            if event is None or self._shutdown.is_set():
                return
            try:
                data = json.loads(event.body_as_str())
                event_type = data.get("event_type", "")
                payload = data.get("payload", {})
                target = payload.get("target_agent", "")
                correlation_id = payload.get("correlation_id", "")

                # SHARD_RESPONSE: handle inline — wake query_shard() immediately
                # instead of going through mailbox → poll → handle_shard_response.
                if event_type == "SHARD_RESPONSE":
                    with self._pending_lock:
                        pending = self._pending.get(correlation_id)
                    if pending:
                        done_event, results = pending
                        results.extend(payload.get("facts", []))
                        done_event.set()
                        logger.info(
                            "Agent %s received SHARD_RESPONSE correlation=%s (%d facts) [inline]",
                            self._agent_id,
                            correlation_id,
                            len(payload.get("facts", [])),
                        )
                    partition_context.update_checkpoint(event)
                    return

                # Other events: filter by target, route to mailbox
                if target and target != self._agent_id:
                    partition_context.update_checkpoint(event)
                    return

                from .event_bus import BusEvent

                bus_evt = BusEvent(
                    event_id=data.get("event_id", uuid.uuid4().hex),
                    event_type=event_type,
                    source_agent=data.get("source_agent", ""),
                    timestamp=data.get("timestamp", 0.0),
                    payload=payload,
                )
                with self._mailbox_lock:
                    self._mailbox.append(bus_evt)
                self._mailbox_ready.set()
                partition_context.update_checkpoint(event)
            except Exception:
                logger.debug("EH receive error for %s", self._agent_id, exc_info=True)

        consumer = EventHubConsumerClient.from_connection_string(
            self._connection_string,
            consumer_group=self._consumer_group,
            eventhub_name=self._eventhub_name,
        )
        try:
            # Use explicit partition_id to avoid consumer-group load-balancer
            # competition. When multiple agents share a consumer group, the
            # load balancer distributes partitions, so each agent only sees
            # events on its assigned partitions. By specifying partition_id,
            # each agent reads exactly its own partition deterministically.
            my_partition = self._target_partition(self._agent_id)
            logger.info(
                "Agent %s receiving from partition %s (cg=%s)",
                self._agent_id,
                my_partition,
                self._consumer_group,
            )
            consumer.receive(
                on_event=_on_event,
                partition_id=my_partition,
                starting_position="@latest",
            )
        except Exception:
            if not self._shutdown.is_set():
                logger.warning("EH consumer exited for %s", self._agent_id, exc_info=True)
        finally:
            try:
                consumer.close()
            except Exception:
                pass

    # -- Poll interface (used by _shard_query_listener) ----------------------

    def poll(self, agent_id: str) -> list[Any]:
        """Drain pending events from the mailbox (blocks up to 5 s for new events).

        Compatible with ``EventBus.poll()`` so ``_shard_query_listener`` can use
        the same polling loop regardless of transport type.
        """
        self._mailbox_ready.wait(timeout=5.0)
        self._mailbox_ready.clear()
        with self._mailbox_lock:
            items = list(self._mailbox)
            self._mailbox.clear()
        return items

    # -- Internal publish helper ---------------------------------------------

    def _publish(self, payload: dict[str, Any], partition_key: str | None = None) -> None:
        """Publish a JSON event to the Event Hub using a persistent producer.

        Reuses a single EventHubProducerClient across all publish calls to
        avoid ~1.5s AMQP connection setup per publish. Thread-safe via lock.

        When ``partition_key`` is an agent name (e.g. "agent-5"), the event is
        routed to that agent's deterministic partition_id instead of relying on
        Event Hubs' partition_key hash (which is opaque and unpredictable).
        """
        import json

        try:
            from azure.eventhub import (  # type: ignore[import-untyped]
                EventData,
                EventHubProducerClient,
            )
        except ImportError:
            logger.error("azure-eventhub not installed — cannot publish to Event Hubs")
            return

        event_type = payload.get("event_type", "?")
        target = (payload.get("payload") or {}).get("target_agent", "")

        # Convert agent-name partition_key to explicit partition_id
        route_partition_id: str | None = None
        if partition_key and partition_key.startswith("agent-"):
            route_partition_id = self._target_partition(partition_key)

        with self._producer_lock:
            try:
                if self._producer is None:
                    self._producer = EventHubProducerClient.from_connection_string(
                        self._connection_string, eventhub_name=self._eventhub_name
                    )
                kwargs: dict[str, Any] = {}
                if route_partition_id is not None:
                    kwargs["partition_id"] = route_partition_id
                elif partition_key:
                    kwargs["partition_key"] = partition_key
                batch = self._producer.create_batch(**kwargs)
                batch.add(EventData(json.dumps(payload)))
                self._producer.send_batch(batch)
            except Exception:
                logger.warning(
                    "Agent %s failed to publish %s, resetting producer",
                    self._agent_id,
                    event_type,
                    exc_info=True,
                )
                try:
                    if self._producer is not None:
                        self._producer.close()
                except Exception:
                    pass
                self._producer = None
                return
            logger.info(
                "Agent %s published %s → %s (hub=%s, partition=%s)",
                self._agent_id,
                event_type,
                target or partition_key or "broadcast",
                self._eventhub_name,
                route_partition_id or "key:" + (partition_key or "none"),
            )

    # -- ShardTransport protocol ---------------------------------------------

    def query_shard(self, agent_id: str, query: str, limit: int) -> list[ShardFact]:
        """Query a shard — local bypass for own shard, EH round-trip for remote."""
        if agent_id == self._agent_id and self._local_graph is not None:
            # Use CognitiveAdapter search (n-gram + reranking) for LOCAL shard
            # when available — same quality as REMOTE shards get via
            # handle_shard_query() → _search_for_shard_response().
            if self._local_agent is not None:
                fact_dicts = _search_for_shard_response(
                    query=query,
                    limit=limit,
                    agent=self._local_agent,
                    local_graph=self._local_graph,
                    agent_id=agent_id,
                )
                logger.info(
                    "Agent %s queried LOCAL shard (CognitiveAdapter) → %d facts",
                    self._agent_id,
                    len(fact_dicts),
                )
                # Convert dicts back to ShardFact for uniform return type
                return [
                    ShardFact(
                        fact_id=d.get("fact_id", ""),
                        content=d.get("content", ""),
                        concept=d.get("concept", ""),
                        confidence=d.get("confidence", 0.8),
                        source_agent=d.get("source_agent", agent_id),
                        tags=d.get("tags", []),
                    )
                    for d in fact_dicts
                ]
            # Fallback: raw ShardStore search (no agent bound)
            shard = self._local_graph._router.get_shard(agent_id)
            if shard is None:
                return []
            local_results = shard.search(query, limit=limit)
            logger.info(
                "Agent %s queried LOCAL shard (raw) → %d facts",
                self._agent_id,
                len(local_results),
            )
            return local_results

        # Remote query: publish SHARD_QUERY and wait for SHARD_RESPONSE
        correlation_id = uuid.uuid4().hex
        done = threading.Event()
        results: list[dict] = []
        with self._pending_lock:
            self._pending[correlation_id] = (done, results)

        try:
            import time

            logger.info(
                "Agent %s sending SHARD_QUERY → %s (query=%.60s, correlation=%s)",
                self._agent_id,
                agent_id,
                query,
                correlation_id[:12],
            )
            self._publish(
                {
                    "event_id": uuid.uuid4().hex,
                    "event_type": "SHARD_QUERY",
                    "source_agent": self._agent_id,
                    "timestamp": time.time(),
                    "payload": {
                        "query": query,
                        "limit": limit,
                        "correlation_id": correlation_id,
                        "target_agent": agent_id,
                    },
                },
                partition_key=agent_id,
            )
            got_response = done.wait(timeout=self._timeout)
            if got_response:
                logger.info(
                    "Agent %s got SHARD_RESPONSE from %s (%d facts, correlation=%s)",
                    self._agent_id,
                    agent_id,
                    len(results),
                    correlation_id[:12],
                )
            else:
                logger.warning(
                    "Agent %s SHARD_QUERY to %s TIMED OUT after %.1fs (correlation=%s)",
                    self._agent_id,
                    agent_id,
                    self._timeout,
                    correlation_id[:12],
                )
        finally:
            with self._pending_lock:
                self._pending.pop(correlation_id, None)

        return [
            ShardFact(
                fact_id=f.get("fact_id", ""),
                content=f.get("content", ""),
                concept=f.get("concept", ""),
                confidence=f.get("confidence", 0.8),
                source_agent=f.get("source_agent", ""),
                tags=f.get("tags", []),
            )
            for f in results
            if f.get("content")
        ]

    def store_on_shard(self, agent_id: str, fact: ShardFact) -> None:
        """Store a fact — local bypass for own shard, SHARD_STORE via EH for remote."""
        if agent_id == self._agent_id and self._local_graph is not None:
            shard = self._local_graph._router.get_shard(agent_id)
            if shard is None:
                return
            gen = self._local_graph._router._embedding_generator
            if gen is not None and shard._embedding_generator is None:
                shard.set_embedding_generator(gen)
            shard.store(fact)
            return

        import time

        self._publish(
            {
                "event_id": uuid.uuid4().hex,
                "event_type": "SHARD_STORE",
                "source_agent": self._agent_id,
                "timestamp": time.time(),
                "payload": {
                    "target_agent": agent_id,
                    "fact": {
                        "fact_id": fact.fact_id,
                        "content": fact.content,
                        "concept": fact.concept,
                        "confidence": fact.confidence,
                        "source_agent": fact.source_agent,
                        "tags": list(fact.tags),
                    },
                },
            },
            partition_key=agent_id,
        )

    # -- Listener-side handlers (called by background thread via poll()) -----

    def handle_shard_query(self, event: Any, agent: Any = None) -> None:
        """Respond to SHARD_QUERY using CognitiveAdapter or local shard search.

        If ``agent`` is provided and has a ``memory.search()`` method, searches
        via the full CognitiveAdapter path instead of raw ShardStore.search().
        Publishes SHARD_RESPONSE with ``partition_key=requesting_agent`` so the
        response routes directly to the querying agent's partition.
        """
        if self._local_graph is None:
            return
        payload = getattr(event, "payload", None) or {}
        query = payload.get("query", "")
        limit = payload.get("limit", 20)
        correlation_id = payload.get("correlation_id", "")
        target_agent = payload.get("target_agent", "")
        if target_agent and target_agent != self._agent_id:
            return
        if not query or not correlation_id:
            return

        source_agent = getattr(event, "source_agent", "")
        logger.info(
            "Agent %s handling SHARD_QUERY from %s (query=%.60s, correlation=%s)",
            self._agent_id,
            source_agent,
            query,
            correlation_id[:12],
        )

        facts_payload = _search_for_shard_response(
            query=query,
            limit=limit,
            agent=agent,
            local_graph=self._local_graph,
            agent_id=self._agent_id,
        )
        import time

        self._publish(
            {
                "event_id": uuid.uuid4().hex,
                "event_type": "SHARD_RESPONSE",
                "source_agent": self._agent_id,
                "timestamp": time.time(),
                "payload": {
                    "correlation_id": correlation_id,
                    "facts": facts_payload,
                },
            },
            partition_key=source_agent,
        )
        logger.info(
            "Agent %s responded to SHARD_QUERY correlation=%s with %d facts → %s",
            self._agent_id,
            correlation_id[:12],
            len(facts_payload),
            source_agent,
        )

    def handle_shard_response(self, event: Any) -> None:
        """Wake the pending query_shard() call when SHARD_RESPONSE arrives.

        NOTE: With the inline _on_event optimization, most SHARD_RESPONSEs are
        handled directly in _receive_loop and never reach this method. This is
        kept as a fallback for non-EH transports that still route via mailbox.
        """
        payload = getattr(event, "payload", None) or {}
        correlation_id = payload.get("correlation_id", "")
        if not correlation_id:
            return
        with self._pending_lock:
            pending = self._pending.get(correlation_id)
        if pending:
            done_event, results = pending
            results.extend(payload.get("facts", []))
            done_event.set()
            logger.info(
                "Agent %s received SHARD_RESPONSE correlation=%s (%d facts) [mailbox]",
                self._agent_id,
                correlation_id[:12],
                len(payload.get("facts", [])),
            )

    def handle_shard_store(self, event: Any) -> None:
        """Store a replicated fact from SHARD_STORE in the local shard."""
        if self._local_graph is None:
            return
        payload = getattr(event, "payload", None) or {}
        target_agent = payload.get("target_agent", "")
        if target_agent and target_agent != self._agent_id:
            return
        fact_dict = payload.get("fact", {})
        if not fact_dict.get("content"):
            return

        shard = self._local_graph._router.get_shard(self._agent_id)
        if shard is None:
            return
        gen = self._local_graph._router._embedding_generator
        if gen is not None and shard._embedding_generator is None:
            shard.set_embedding_generator(gen)

        replica = ShardFact(
            fact_id=fact_dict.get("fact_id", ""),
            content=fact_dict.get("content", ""),
            concept=fact_dict.get("concept", ""),
            confidence=fact_dict.get("confidence", 0.8),
            source_agent=fact_dict.get("source_agent", getattr(event, "source_agent", "")),
            tags=fact_dict.get("tags", []),
        )
        stored = shard.store(replica)
        logger.debug(
            "Agent %s (EH) stored replicated fact from %s (stored=%s, content=%.40s)",
            self._agent_id,
            getattr(event, "source_agent", "?"),
            stored,
            replica.content,
        )

    def close(self) -> None:
        """Shut down the background receive thread and persistent producer."""
        self._shutdown.set()
        self._mailbox_ready.set()  # Unblock any waiting poll() call
        with self._producer_lock:
            if self._producer is not None:
                try:
                    self._producer.close()
                except Exception:
                    pass
                self._producer = None


# ---------------------------------------------------------------------------
# DistributedHiveGraph
# ---------------------------------------------------------------------------


class DistributedHiveGraph:
    """DHT-sharded hive graph for large-scale multi-agent knowledge sharing.

    Implements the same interface as InMemoryHiveGraph but distributes
    facts across agent shards via consistent hashing. No single agent
    holds all facts. Queries fan out to K relevant agents, not all N.

    Shard routing is delegated to an injected ShardTransport, making the
    graph transport-agnostic. Agent code is identical whether routing is
    in-process (LocalShardTransport) or over Azure Service Bus
    (ServiceBusShardTransport).

    Args:
        hive_id: Unique identifier for this hive
        replication_factor: Number of copies per fact (default 3)
        query_fanout: Max agents to query per request (default 5)
        embedding_generator: Optional embedding model for semantic routing
        enable_gossip: Enable bloom filter gossip for convergence
        broadcast_threshold: Confidence threshold for auto-broadcast (default 0.9)
        transport: ShardTransport instance. If None, creates LocalShardTransport
                   wrapping a new DHTRouter (backward-compatible default).
    """

    def __init__(
        self,
        hive_id: str = "",
        replication_factor: int = DEFAULT_REPLICATION_FACTOR,
        query_fanout: int = 5,
        embedding_generator: Any = None,
        enable_gossip: bool = True,
        enable_ttl: bool = False,
        broadcast_threshold: float = DEFAULT_BROADCAST_THRESHOLD,
        transport: ShardTransport | None = None,
    ):
        self._hive_id = hive_id or uuid.uuid4().hex[:12]
        self._lock = threading.Lock()

        # DHT router handles ring topology and query routing decisions
        self._router = DHTRouter(
            replication_factor=replication_factor,
            query_fanout=query_fanout,
        )
        if embedding_generator:
            self._router.set_embedding_generator(embedding_generator)

        # Agent registry (lightweight metadata, not full DBs)
        self._agents: dict[str, HiveAgent] = {}

        # Edge storage (graph relationships)
        self._edges: dict[str, list[HiveEdge]] = {}

        # Bloom filters for gossip
        self._bloom_filters: dict[str, BloomFilter] = {}  # agent_id → bloom
        self._enable_gossip = enable_gossip

        # Federation (parent/child relationships)
        self._parent: DistributedHiveGraph | None = None
        self._children: list[DistributedHiveGraph] = []

        self._broadcast_threshold = broadcast_threshold
        self._embedding_generator = embedding_generator

        # Fact counter for stats
        self._total_promotes = 0

        # Shard transport — injected or defaulting to local in-process routing
        self._transport: Any = (
            transport if transport is not None else LocalShardTransport(self._router)
        )
        # Allow the transport to call back into this graph for local shard access
        if hasattr(self._transport, "bind_local"):
            self._transport.bind_local(self)

    # -- HiveGraph protocol: identity -----------------------------------------

    @property
    def hive_id(self) -> str:
        return self._hive_id

    # -- HiveGraph protocol: agent registry -----------------------------------

    def register_agent(
        self,
        agent_id: str,
        domain: str = "",
        trust: float = DEFAULT_TRUST_SCORE,
    ) -> None:
        """Register an agent in the hive and add to DHT ring."""
        with self._lock:
            self._agents[agent_id] = HiveAgent(agent_id=agent_id, domain=domain, trust=trust)
            self._bloom_filters[agent_id] = BloomFilter(expected_items=500)
        self._router.add_agent(agent_id)
        logger.debug("Registered agent %s in hive %s", agent_id, self._hive_id)

    def unregister_agent(self, agent_id: str) -> None:
        """Remove agent from hive. Redistributes its shard facts."""
        orphaned = self._router.remove_agent(agent_id)
        with self._lock:
            self._agents.pop(agent_id, None)
            self._bloom_filters.pop(agent_id, None)

        # Redistribute orphaned facts
        for fact in orphaned:
            self._router.store_fact(fact)

    def get_agent(self, agent_id: str) -> HiveAgent | None:
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> list[HiveAgent]:
        with self._lock:
            return list(self._agents.values())

    def update_trust(self, agent_id: str, trust: float) -> None:
        clamped = max(0.0, min(trust, MAX_TRUST_SCORE))
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent:
                agent.trust = clamped

    # -- HiveGraph protocol: fact management ----------------------------------

    def promote_fact(self, agent_id: str, fact: HiveFact) -> str:
        """Promote a fact into the distributed hive.

        In distributed mode each agent IS the shard owner for facts it learns.
        Storage is always local to the promoting agent — the DHT ring is used
        only for query routing (fan-out), not for storage routing.

        This avoids the lost-write problem where ServiceBusShardTransport would
        publish a SHARD_STORE event to a remote agent that may not handle it.
        """
        # Generate fact_id if not set
        if not fact.fact_id:
            fact.fact_id = uuid.uuid4().hex[:FACT_ID_HEX_LENGTH]

        fact.source_agent = fact.source_agent or agent_id

        # Convert to shard fact
        shard_fact = ShardFact(
            fact_id=fact.fact_id,
            content=fact.content,
            concept=fact.concept,
            confidence=fact.confidence,
            source_agent=fact.source_agent,
            tags=list(fact.tags),
            created_at=fact.created_at,
        )

        # Store locally in the promoting agent's own shard (pure DHT sharding:
        # each agent owns O(F/N) facts; cross-shard queries via CognitiveAdapter
        # provide retrieval quality equal to local search without full replication).
        shard_fact.ring_position = 0  # Not used for routing here
        self._transport.store_on_shard(agent_id, shard_fact)

        # Update bloom filter and counters for the local shard only
        with self._lock:
            if agent_id in self._bloom_filters:
                self._bloom_filters[agent_id].add(fact.fact_id)
            source = self._agents.get(agent_id)
            if source:
                source.fact_count += 1
            self._total_promotes += 1

        # Federation: escalate high-confidence facts to parent
        if (
            self._parent
            and fact.confidence >= self._broadcast_threshold
            and not any(t.startswith(BROADCAST_TAG_PREFIX) for t in fact.tags)
        ):
            self._escalate_to_parent(fact)

        return fact.fact_id

    def get_fact(self, fact_id: str) -> HiveFact | None:
        """Retrieve a fact by ID. Searches all shards (O(N) worst case)."""
        for agent_id in self._router.get_all_agents():
            shard = self._router.get_shard(agent_id)
            if shard:
                sf = shard.get(fact_id)
                if sf:
                    return self._shard_to_hive_fact(sf)
        return None

    def query_facts(self, query: str, limit: int = 20) -> list[HiveFact]:
        """Query the distributed hive for matching facts.

        Determines target shards via DHT routing, then fans out to each shard
        in parallel -- reduces total latency from N*timeout to max(timeout).
        Each query_shard call is independent; results are merged and deduped.
        """
        import time as _time

        _qf_start = _time.monotonic()
        targets = self._router.select_query_targets(query)

        try:
            from .tracing import trace_log

            trace_log(
                "query_facts",
                "fan-out to %d targets for: %.80s",
                len(targets),
                query[:80],
            )
        except ImportError:
            pass

        seen: set[str] = set()
        results: list[ShardFact] = []
        _responded = 0
        _timed_out = 0
        _failed = 0

        # Parallel fan-out: query all shards concurrently instead of sequentially.
        # With ServiceBus transport this reduces N*SB_latency to max(SB_latency).
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(targets))) as pool:
            futures = {
                pool.submit(self._transport.query_shard, agent_id, query, limit): agent_id
                for agent_id in targets
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    shard_results = future.result()
                    if shard_results:
                        _responded += 1
                    for fact in shard_results:
                        # Deduplicate by content hash (mirrors DHTRouter.query)
                        h = hashlib.md5(fact.content.encode()).hexdigest()
                        if h not in seen:
                            seen.add(h)
                            results.append(fact)
                except Exception:
                    _failed += 1
                    logger.debug("Shard query failed for agent %s", futures[future], exc_info=True)

        _qf_elapsed = _time.monotonic() - _qf_start
        try:
            from .tracing import trace_log

            trace_log(
                "query_facts",
                "targets=%d responded=%d failed=%d unique_facts=%d elapsed=%.2fs",
                len(targets),
                _responded,
                _failed,
                len(results),
                _qf_elapsed,
            )
        except ImportError:
            pass

        # Re-rank: terms with digits (IDs, versions) weighted 5x; bigram bonus
        import itertools

        q_lower = query.lower()
        q_words = [w.strip("?.,!;:'\"()[]") for w in q_lower.split() if w.strip("?.,!;:'\"()[]")]
        q_bigrams = set(itertools.pairwise(q_words))
        _stop = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "what",
            "how",
            "does",
            "do",
            "and",
            "or",
            "of",
            "in",
            "to",
            "for",
            "with",
            "on",
            "at",
            "by",
            "from",
            "that",
            "this",
            "it",
        }
        search_terms = {w for w in q_words if w not in _stop and len(w) > 1} or set(q_words)

        def _relevance(f: ShardFact) -> float:
            c_lower = f.content.lower()
            c_words = c_lower.split()
            hits = sum(
                (5.0 if any(ch.isdigit() for ch in t) else 1.0)
                for t in search_terms
                if t in c_lower
            )
            bigram_bonus = sum(0.3 for bg in q_bigrams if bg in set(itertools.pairwise(c_words)))
            return hits + bigram_bonus + f.confidence * 0.01

        results.sort(key=_relevance, reverse=True)
        return [self._shard_to_hive_fact(sf) for sf in results[:limit]]

    def retract_fact(self, fact_id: str) -> bool:
        """Retract a fact across all shards holding a replica. Returns True if found."""
        retracted = False
        for agent_id in self._router.get_all_agents():
            shard = self._router.get_shard(agent_id)
            if shard:
                sf = shard.get(fact_id)
                if sf:
                    sf.tags.append("retracted")
                    retracted = True
        return retracted

    # -- HiveGraph protocol: graph edges --------------------------------------

    def add_edge(self, edge: HiveEdge) -> None:
        with self._lock:
            self._edges.setdefault(edge.source_id, []).append(edge)

    def get_edges(self, node_id: str, edge_type: str | None = None) -> list[HiveEdge]:
        with self._lock:
            edges = self._edges.get(node_id, [])
            if edge_type:
                return [e for e in edges if e.edge_type == edge_type]
            return list(edges)

    # -- HiveGraph protocol: contradiction detection --------------------------

    def check_contradictions(self, content: str, concept: str = "") -> list[HiveFact]:
        """Check for contradicting facts across shards."""
        if concept:
            candidates = self.query_facts(concept, limit=50)
        else:
            candidates = self.query_facts(content, limit=50)

        content_words = set(content.lower().split())
        contradictions = []
        for fact in candidates:
            if fact.content == content:
                continue
            fact_words = set(fact.content.lower().split())
            overlap = len(content_words & fact_words) / max(1, len(content_words | fact_words))
            if overlap > 0.4 and fact.content != content:
                contradictions.append(fact)

        return contradictions

    # -- HiveGraph protocol: expertise routing --------------------------------

    def route_query(self, query: str) -> list[str]:
        """Find agent IDs with expertise relevant to query."""
        query_words = set(query.lower().split())
        scored: list[tuple[float, HiveAgent]] = []

        with self._lock:
            for agent in self._agents.values():
                if not agent.domain:
                    continue
                domain_words = set(agent.domain.lower().split())
                overlap = len(query_words & domain_words)
                if overlap > 0:
                    scored.append((overlap, agent))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [a.agent_id for _, a in scored]

    # -- Federation -----------------------------------------------------------

    def set_parent(self, parent: DistributedHiveGraph) -> None:
        self._parent = parent

    def add_child(self, child: DistributedHiveGraph) -> None:
        self._children.append(child)

    def escalate_fact(self, fact: HiveFact) -> bool:
        """Escalate a fact to the parent hive. Returns True if parent exists."""
        if not self._parent:
            return False
        self._escalate_to_parent(fact)
        return True

    def broadcast_fact(self, fact: HiveFact) -> int:
        """Promote a fact to all child hives. Returns count of children promoted to."""
        count = 0
        for child in self._children:
            relay_id = f"__relay_{self._hive_id}__"
            if not child.get_agent(relay_id):
                child.register_agent(relay_id, domain="relay")
            promoted = HiveFact(
                fact_id=uuid.uuid4().hex[:FACT_ID_HEX_LENGTH],
                content=fact.content,
                concept=fact.concept,
                confidence=fact.confidence,
                source_agent=relay_id,
                tags=[*fact.tags, f"{BROADCAST_TAG_PREFIX}{self._hive_id}"],
                created_at=fact.created_at,
            )
            child.promote_fact(relay_id, promoted)
            count += 1
        return count

    def _escalate_to_parent(self, fact: HiveFact) -> None:
        """Escalate a high-confidence fact to the parent hive."""
        if not self._parent:
            return
        relay_id = f"__relay_{self._hive_id}__"
        if not self._parent.get_agent(relay_id):
            self._parent.register_agent(relay_id, domain="relay")

        escalated = HiveFact(
            fact_id=uuid.uuid4().hex[:FACT_ID_HEX_LENGTH],
            content=fact.content,
            concept=fact.concept,
            confidence=fact.confidence,
            source_agent=relay_id,
            tags=[*fact.tags, f"escalated_from:{self._hive_id}"],
            created_at=fact.created_at,
        )
        self._parent.promote_fact(relay_id, escalated)

    def query_federated(
        self,
        query: str,
        limit: int = 20,
        _visited: set[str] | None = None,
    ) -> list[HiveFact]:
        """Query this hive and all children, merge via RRF.

        Prevents cycles via _visited set.
        """
        if _visited is None:
            _visited = set()
        if self._hive_id in _visited:
            return []
        _visited.add(self._hive_id)

        # Local results
        local = self.query_facts(query, limit=limit)

        # Recurse into children
        child_results: list[HiveFact] = []
        for child in self._children:
            child_facts = child.query_federated(query, limit=limit, _visited=_visited)
            child_results.extend(child_facts)

        # Merge and deduplicate
        all_facts = local + child_results
        seen: set[str] = set()
        deduped: list[HiveFact] = []
        for f in all_facts:
            key = f.content
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        # Sort by confidence + relevance
        query_words = set(query.lower().split())
        deduped.sort(
            key=lambda f: (
                sum(1 for w in query_words if w in f.content.lower()) + f.confidence * 0.01
            ),
            reverse=True,
        )

        return deduped[:limit]

    # -- Gossip ---------------------------------------------------------------

    def run_gossip_round(self) -> dict[str, int]:
        """Run a gossip round using bloom filter exchange.

        Each agent exchanges bloom filters with random peers.
        Pulls facts that are missing from its shard.
        Returns dict of agent_id → facts received.
        """
        if not self._enable_gossip:
            return {}

        agents = self._router.get_all_agents()
        if len(agents) < 2:
            return {}

        received: dict[str, int] = {}
        fanout = min(2, len(agents) - 1)

        for agent_id in agents:
            shard = self._router.get_shard(agent_id)
            if not shard:
                continue

            # Select random peers
            peers = [a for a in agents if a != agent_id]
            selected = random.sample(peers, min(fanout, len(peers)))

            facts_received = 0
            for peer_id in selected:
                peer_shard = self._router.get_shard(peer_id)
                if not peer_shard:
                    continue

                # Get peer's fact IDs
                peer_fact_ids = peer_shard.get_all_fact_ids()

                # Check which we're missing via bloom filter
                with self._lock:
                    my_bloom = self._bloom_filters.get(agent_id)
                if my_bloom is None:
                    continue

                missing_ids = my_bloom.missing_from(list(peer_fact_ids))

                # Pull missing facts
                for fid in missing_ids:
                    peer_fact = peer_shard.get(fid)
                    if peer_fact:
                        # Store replica in our shard
                        replica = ShardFact(
                            fact_id=peer_fact.fact_id,
                            content=peer_fact.content,
                            concept=peer_fact.concept,
                            confidence=peer_fact.confidence * 0.9,  # Discount
                            source_agent=peer_fact.source_agent,
                            tags=[*peer_fact.tags, f"gossip_from:{peer_id}"],
                            created_at=peer_fact.created_at,
                        )
                        if shard.store(replica):
                            facts_received += 1
                            my_bloom.add(fid)

            if facts_received > 0:
                received[agent_id] = facts_received

        total = sum(received.values())
        if total > 0:
            logger.info(
                "Gossip round: %d facts propagated to %d agents",
                total,
                len(received),
            )

        return received

    def convergence_score(self) -> float:
        """Measure knowledge convergence across all shards.

        Returns fraction of unique facts present on ALL agents.
        0.0 = no overlap, 1.0 = every agent has every fact.
        """
        agents = self._router.get_all_agents()
        if len(agents) < 2:
            return 1.0

        # Collect all unique content hashes
        all_hashes: set[str] = set()
        per_agent: dict[str, set[str]] = {}

        for agent_id in agents:
            shard = self._router.get_shard(agent_id)
            if shard:
                hashes = shard.get_content_hashes()
                per_agent[agent_id] = hashes
                all_hashes |= hashes

        if not all_hashes:
            return 1.0

        # Count facts present on ALL agents
        common = set.intersection(*per_agent.values()) if per_agent else set()
        return len(common) / len(all_hashes)

    # -- Stats & lifecycle ----------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get hive statistics."""
        dht_stats = self._router.get_stats()
        return {
            "hive_id": self._hive_id,
            "type": "distributed",
            "agent_count": len(self._agents),
            "fact_count": dht_stats["total_facts"],
            "total_promotes": self._total_promotes,
            "replication_factor": dht_stats["replication_factor"],
            "avg_shard_size": dht_stats["avg_shard_size"],
            "shard_sizes": dht_stats["shard_sizes"],
            "has_parent": self._parent is not None,
            "child_count": len(self._children),
            "edge_count": sum(len(v) for v in self._edges.values()),
            "gossip_enabled": self._enable_gossip,
        }

    def close(self) -> None:
        """Release resources."""
        # All in-memory, nothing to close

    def gc(self) -> int:
        """Garbage collect expired facts. Returns count removed."""
        return 0  # TTL not implemented for distributed version yet

    # -- Helpers --------------------------------------------------------------

    @staticmethod
    def _shard_to_hive_fact(sf: ShardFact) -> HiveFact:
        """Convert a ShardFact to a HiveFact for protocol compatibility."""
        return HiveFact(
            fact_id=sf.fact_id,
            content=sf.content,
            concept=sf.concept,
            confidence=sf.confidence,
            source_agent=sf.source_agent,
            tags=sf.tags,
            created_at=sf.created_at,
        )

    # -- merge_state (CRDT compat) -------------------------------------------

    def merge_state(self, other: DistributedHiveGraph) -> None:
        """Merge facts from another hive (CRDT-style add-wins)."""
        for agent_id in other._router.get_all_agents():
            shard = other._router.get_shard(agent_id)
            if not shard:
                continue
            for fact in shard.get_all_facts():
                self._router.store_fact(fact)


__all__ = [
    "DistributedHiveGraph",
    "EventHubsShardTransport",
    "LocalShardTransport",
    "ServiceBusShardTransport",
    "ShardTransport",
]
