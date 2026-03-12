"""Integration test: DHT shard cross-agent query round-trip.

Validates the SHARD_QUERY/SHARD_RESPONSE event-driven protocol using
LocalEventBus.  Each agent has its own DistributedHiveGraph shard.
No sleep or poll intervals — facts are dispatched synchronously using
LocalEventBus mailbox semantics.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
    DistributedHiveGraph,
    ServiceBusShardTransport,
    _search_for_shard_response,
)
from amplihack.agents.goal_seeking.hive_mind.event_bus import LocalEventBus, make_event
from amplihack.agents.goal_seeking.hive_mind.hive_graph import HiveFact


def _make_fact(content: str, concept: str, agent_id: str, confidence: float = 0.9) -> HiveFact:
    return HiveFact(
        fact_id="",
        content=content,
        concept=concept,
        confidence=confidence,
        source_agent=agent_id,
        tags=[concept],
        created_at=time.time(),
    )


def _sync_cross_shard_query(
    requester_id: str,
    query: str,
    shards: dict[str, DistributedHiveGraph],
    bus: LocalEventBus,
    limit: int = 10,
) -> list[dict]:
    """Synchronous cross-shard query via SHARD_QUERY/SHARD_RESPONSE protocol.

    Publishes SHARD_QUERY, each peer processes it synchronously and publishes
    SHARD_RESPONSE, then requester collects all responses.  No sleep needed.
    """
    correlation_id = uuid.uuid4().hex
    agent_names = list(shards.keys())

    # Publish SHARD_QUERY (delivered to all peers, not to requester itself)
    query_event = make_event(
        event_type="SHARD_QUERY",
        source_agent=requester_id,
        payload={"query": query, "limit": limit, "correlation_id": correlation_id},
    )
    bus.publish(query_event)

    # Each peer shard drains mailbox and publishes SHARD_RESPONSE
    for agent_id in agent_names:
        if agent_id == requester_id:
            continue
        for event in bus.poll(agent_id):
            if event.event_type == "SHARD_QUERY":
                facts = shards[agent_id].query_facts(
                    event.payload["query"], limit=event.payload.get("limit", limit)
                )
                response = make_event(
                    event_type="SHARD_RESPONSE",
                    source_agent=agent_id,
                    payload={
                        "correlation_id": event.payload["correlation_id"],
                        "facts": [
                            {"content": f.content, "confidence": f.confidence} for f in facts
                        ],
                    },
                )
                bus.publish(response)

    # Requester collects all SHARD_RESPONSE events
    results: list[dict] = []
    for event in bus.poll(requester_id):
        if (
            event.event_type == "SHARD_RESPONSE"
            and event.payload.get("correlation_id") == correlation_id
        ):
            results.extend(event.payload.get("facts", []))

    # Include requester's own local shard
    local_facts = shards[requester_id].query_facts(query, limit=limit)
    results.extend({"content": f.content, "confidence": f.confidence} for f in local_facts)

    return results


class TestDHTShardCrossQuery:
    """Cross-shard query round-trip via event-driven protocol."""

    def setup_method(self):
        self.bus = LocalEventBus()
        self.shards: dict[str, DistributedHiveGraph] = {}
        for name in ["agent-0", "agent-1", "agent-2"]:
            shard = DistributedHiveGraph(hive_id=f"shard-{name}", enable_gossip=False)
            shard.register_agent(name)
            self.shards[name] = shard
            self.bus.subscribe(name)

    def teardown_method(self):
        self.bus.close()

    def test_agent1_gets_agent0_facts_via_shard_query(self):
        """agent-1 querying content agent-0 learned returns correct facts."""
        # agent-0 learns its content
        fact = _make_fact("Paris is the capital of France", "geography", "agent-0")
        self.shards["agent-0"].promote_fact("agent-0", fact)

        # agent-1 knows nothing about geography
        agent1_local = self.shards["agent-1"].query_facts("capital France", limit=10)
        assert len(agent1_local) == 0, "agent-1 should have no local geography facts"

        # Cross-shard query: agent-1 asks about agent-0's content via event bus
        results = _sync_cross_shard_query(
            requester_id="agent-1",
            query="capital France",
            shards=self.shards,
            bus=self.bus,
        )

        texts = [r["content"] for r in results]
        assert any("Paris" in t or "capital" in t for t in texts), (
            f"Expected Paris/capital in results, got: {texts}"
        )

    def test_each_agent_owns_only_its_partition(self):
        """With replication_factor=1, total stored == total promoted (no replication).

        DHT routes each fact to exactly one shard based on content hash.
        The combined storage across all shards equals the total facts promoted.
        """
        # Use replication_factor=1 so each fact goes to exactly one shard
        shards_rf1: dict[str, DistributedHiveGraph] = {}
        bus2 = LocalEventBus()
        for name in ["agent-0", "agent-1", "agent-2"]:
            shard = DistributedHiveGraph(
                hive_id=f"shard-rf1-{name}",
                replication_factor=1,
                enable_gossip=False,
            )
            shard.register_agent(name)
            shards_rf1[name] = shard
            bus2.subscribe(name)

        facts_to_promote = [
            ("Water boils at 100 degrees Celsius", "science", "agent-0"),
            ("The speed of light is 299792 km/s", "science", "agent-1"),
            ("DNA is a double helix structure", "science", "agent-2"),
        ]

        for content, concept, agent_id in facts_to_promote:
            fact = _make_fact(content, concept, agent_id)
            shards_rf1[agent_id].promote_fact(agent_id, fact)

        # Total facts across shards == number of facts promoted (no replication)
        total = sum(s.get_stats()["fact_count"] for s in shards_rf1.values())
        assert total == len(facts_to_promote), (
            f"Expected {len(facts_to_promote)} total with replication_factor=1, got {total}"
        )

        # All facts retrievable via cross-shard query
        for content, _, _ in facts_to_promote:
            results = _sync_cross_shard_query(
                requester_id="agent-0",
                query=content.split()[0],
                shards=shards_rf1,
                bus=bus2,
                limit=10,
            )
            found = any(content in r["content"] for r in results)
            assert found, f"Cross-shard query did not find: {content}"

        bus2.close()

    def test_shard_query_event_protocol(self):
        """SHARD_QUERY event is delivered and SHARD_RESPONSE is returned."""
        fact = _make_fact("Gravity accelerates at 9.8 m/s²", "physics", "agent-2")
        self.shards["agent-2"].promote_fact("agent-2", fact)

        # agent-0 queries using SHARD_QUERY/SHARD_RESPONSE protocol
        results = _sync_cross_shard_query(
            requester_id="agent-0",
            query="gravity acceleration",
            shards=self.shards,
            bus=self.bus,
        )

        texts = [r["content"] for r in results]
        assert any("9.8" in t or "ravit" in t for t in texts), (
            f"Expected gravity fact in results, got: {texts}"
        )

    def test_no_cross_contamination_between_queries(self):
        """Separate SHARD_QUERY events with different correlation IDs don't mix."""
        self.shards["agent-0"].promote_fact(
            "agent-0", _make_fact("Alpha fact about dogs", "animals", "agent-0")
        )
        self.shards["agent-1"].promote_fact(
            "agent-1", _make_fact("Beta fact about cats", "animals", "agent-1")
        )

        results_a = _sync_cross_shard_query("agent-2", "dogs", self.shards, self.bus)
        results_b = _sync_cross_shard_query("agent-2", "cats", self.shards, self.bus)

        texts_a = [r["content"] for r in results_a]
        texts_b = [r["content"] for r in results_b]

        assert any("dog" in t.lower() for t in texts_a), "Query A should find dog facts"
        assert any("cat" in t.lower() for t in texts_b), "Query B should find cat facts"

    def test_threaded_shard_query_listener(self):
        """ServiceBusShardTransport background thread handles SHARD_QUERY without sleep."""
        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            ServiceBusShardTransport,
        )

        # Build a DistributedHiveGraph with ServiceBusShardTransport (DI pattern)
        bus2 = LocalEventBus()
        bus2.subscribe("agent-0")
        bus2.subscribe("requester")

        sb_transport = ServiceBusShardTransport(event_bus=bus2, agent_id="agent-0")
        dht = DistributedHiveGraph(
            hive_id="shard-agent-0-threaded",
            enable_gossip=False,
            transport=sb_transport,
        )
        dht.register_agent("agent-0")
        dht.promote_fact(
            "agent-0",
            _make_fact("The Eiffel Tower is in Paris", "landmarks", "agent-0"),
        )

        shutdown = threading.Event()

        # Start a shard listener that processes events with a tiny poll loop
        def listener_loop():
            while not shutdown.is_set():
                events = bus2.poll("agent-0")
                for event in events:
                    if event.event_type == "SHARD_QUERY":
                        sb_transport.handle_shard_query(event)
                    elif event.event_type == "SHARD_RESPONSE":
                        sb_transport.handle_shard_response(event)
                # Minimal yield — not a timing assumption, just cooperative multitasking
                time.sleep(0.005)

        listener = threading.Thread(target=listener_loop, daemon=True)
        listener.start()

        try:
            # Send SHARD_QUERY from "requester"
            correlation_id = uuid.uuid4().hex
            query_event = make_event(
                event_type="SHARD_QUERY",
                source_agent="requester",
                payload={"query": "Eiffel Tower", "limit": 5, "correlation_id": correlation_id},
            )
            bus2.publish(query_event)

            # Wait for SHARD_RESPONSE to arrive in requester's mailbox
            deadline = time.time() + 2.0
            response_facts: list[dict] = []
            while time.time() < deadline:
                events = bus2.poll("requester")
                for event in events:
                    if (
                        event.event_type == "SHARD_RESPONSE"
                        and event.payload.get("correlation_id") == correlation_id
                    ):
                        response_facts.extend(event.payload.get("facts", []))
                if response_facts:
                    break
                time.sleep(0.01)

            texts = [f["content"] for f in response_facts]
            assert any("Eiffel" in t or "Paris" in t for t in texts), (
                f"Expected Eiffel/Paris in threaded response, got: {texts}"
            )
        finally:
            shutdown.set()
            listener.join(timeout=1.0)
            bus2.close()


class TestServiceBusShardTransport:
    """Verify ServiceBusShardTransport using LocalEventBus as stand-in."""

    def test_query_shard_local_bypass(self):
        """query_shard on own agent_id queries local shard without bus round-trip."""
        bus = LocalEventBus()
        bus.subscribe("agent-0")

        sb_transport = ServiceBusShardTransport(event_bus=bus, agent_id="agent-0")
        dht = DistributedHiveGraph(
            hive_id="test-local-bypass", enable_gossip=False, transport=sb_transport
        )
        dht.register_agent("agent-0")
        dht.promote_fact(
            "agent-0", _make_fact("Python is a programming language", "tech", "agent-0")
        )

        # Query via transport directly — should use local bypass
        results = sb_transport.query_shard("agent-0", "Python programming", limit=5)
        assert any("Python" in f.content for f in results), (
            f"Local bypass query did not return expected fact. Got: {[f.content for f in results]}"
        )
        # No SHARD_QUERY published to bus
        assert bus.poll("agent-0") == [], "Local bypass must not publish SHARD_QUERY"
        bus.close()

    def test_store_on_shard_local_bypass(self):
        """store_on_shard on own agent_id stores locally without publishing SHARD_STORE."""
        from amplihack.agents.goal_seeking.hive_mind.dht import ShardFact

        bus = LocalEventBus()
        bus.subscribe("agent-0")
        bus.subscribe("observer")

        sb_transport = ServiceBusShardTransport(event_bus=bus, agent_id="agent-0")
        dht = DistributedHiveGraph(
            hive_id="test-store-bypass", enable_gossip=False, transport=sb_transport
        )
        dht.register_agent("agent-0")

        fact = ShardFact(
            fact_id="sf-001",
            content="Rust is memory-safe",
            concept="tech",
            confidence=0.9,
            source_agent="agent-0",
        )
        sb_transport.store_on_shard("agent-0", fact)

        # Fact is in the local shard
        shard = dht._router.get_shard("agent-0")
        assert shard is not None
        stored = shard.get("sf-001")
        assert stored is not None and "Rust" in stored.content

        # No SHARD_STORE published
        assert bus.poll("observer") == [], "Local store must not publish SHARD_STORE"
        bus.close()

    def test_handle_shard_query_publishes_response(self):
        """handle_shard_query looks up local facts and publishes SHARD_RESPONSE."""
        bus = LocalEventBus()
        bus.subscribe("agent-0")
        bus.subscribe("requester")

        sb_transport = ServiceBusShardTransport(event_bus=bus, agent_id="agent-0")
        dht = DistributedHiveGraph(
            hive_id="test-handle-query", enable_gossip=False, transport=sb_transport
        )
        dht.register_agent("agent-0")
        dht.promote_fact("agent-0", _make_fact("The Louvre is in Paris", "landmarks", "agent-0"))

        # Simulate incoming SHARD_QUERY
        correlation_id = uuid.uuid4().hex
        query_event = make_event(
            event_type="SHARD_QUERY",
            source_agent="requester",
            payload={"query": "Louvre Paris", "limit": 5, "correlation_id": correlation_id},
        )
        # agent-0 receives and handles it
        sb_transport.handle_shard_query(query_event)

        # requester should have a SHARD_RESPONSE in its mailbox
        responses = [e for e in bus.poll("requester") if e.event_type == "SHARD_RESPONSE"]
        assert len(responses) == 1
        assert responses[0].payload["correlation_id"] == correlation_id
        facts = responses[0].payload["facts"]
        assert any("Louvre" in f["content"] or "Paris" in f["content"] for f in facts), (
            f"SHARD_RESPONSE did not contain expected facts: {facts}"
        )
        bus.close()

    def test_handle_shard_response_wakes_pending_query(self):
        """handle_shard_response sets threading.Event for pending query_shard call."""
        bus = LocalEventBus()
        bus.subscribe("agent-1")

        sb_transport = ServiceBusShardTransport(event_bus=bus, agent_id="agent-1")

        # Register a pending correlation
        correlation_id = uuid.uuid4().hex
        done = threading.Event()
        results: list[dict] = []
        with sb_transport._pending_lock:
            sb_transport._pending[correlation_id] = (done, results)

        # Simulate incoming SHARD_RESPONSE
        response_event = make_event(
            event_type="SHARD_RESPONSE",
            source_agent="agent-0",
            payload={
                "correlation_id": correlation_id,
                "facts": [{"content": "Speed of light is 299792 km/s", "confidence": 0.95}],
            },
        )
        sb_transport.handle_shard_response(response_event)

        assert done.is_set(), "threading.Event must be set by handle_shard_response"
        assert len(results) == 1
        assert "299792" in results[0]["content"]
        bus.close()

    def test_remote_query_via_bus_round_trip(self):
        """query_shard for a remote agent sends SHARD_QUERY and collects SHARD_RESPONSE."""
        bus = LocalEventBus()
        bus.subscribe("agent-0")
        bus.subscribe("agent-1")

        # agent-0: owns facts
        sb_transport_0 = ServiceBusShardTransport(event_bus=bus, agent_id="agent-0")
        dht_0 = DistributedHiveGraph(
            hive_id="shard-a0", enable_gossip=False, transport=sb_transport_0
        )
        dht_0.register_agent("agent-0")
        dht_0.promote_fact(
            "agent-0", _make_fact("The Colosseum is in Rome", "landmarks", "agent-0")
        )

        # agent-1: querier with its own transport
        sb_transport_1 = ServiceBusShardTransport(event_bus=bus, agent_id="agent-1", timeout=2.0)
        dht_1 = DistributedHiveGraph(
            hive_id="shard-a1", enable_gossip=False, transport=sb_transport_1
        )
        dht_1.register_agent("agent-1")

        shutdown = threading.Event()

        # Background listener for agent-0 — handles incoming SHARD_QUERY
        def agent0_listener():
            while not shutdown.is_set():
                for event in bus.poll("agent-0"):
                    if event.event_type == "SHARD_QUERY":
                        sb_transport_0.handle_shard_query(event)
                    elif event.event_type == "SHARD_RESPONSE":
                        sb_transport_0.handle_shard_response(event)
                time.sleep(0.005)

        # Background listener for agent-1 — collects SHARD_RESPONSE
        def agent1_listener():
            while not shutdown.is_set():
                for event in bus.poll("agent-1"):
                    if event.event_type == "SHARD_RESPONSE":
                        sb_transport_1.handle_shard_response(event)
                time.sleep(0.005)

        t0 = threading.Thread(target=agent0_listener, daemon=True)
        t1 = threading.Thread(target=agent1_listener, daemon=True)
        t0.start()
        t1.start()

        try:
            # agent-1 queries agent-0's shard remotely
            results = sb_transport_1.query_shard("agent-0", "Colosseum Rome", limit=5)
            texts = [f.content for f in results]
            assert any("Colosseum" in t or "Rome" in t for t in texts), (
                f"Remote shard query did not return expected facts. Got: {texts}"
            )
        finally:
            shutdown.set()
            t0.join(timeout=1.0)
            t1.join(timeout=1.0)
            bus.close()


# ---------------------------------------------------------------------------
# Unit tests for Bug 1 fix (promote_fact stores locally) and
# Bug 2 fix (_select_query_targets fans out to all agents in distributed mode)
# ---------------------------------------------------------------------------


class TestPromoteFactStoresLocally:
    """Bug 1 fix: promote_fact always stores in the promoting agent's own shard."""

    def test_single_agent_ring_stores_locally(self):
        """With one agent on the ring, fact stays in that agent's shard."""
        dht = DistributedHiveGraph(hive_id="test-single", enable_gossip=False)
        dht.register_agent("agent-0")

        fact = _make_fact("Water boils at 100C", "science", "agent-0")
        dht.promote_fact("agent-0", fact)

        results = dht.query_facts("water boils")
        assert any("100" in f.content for f in results), (
            f"Fact not found in single-agent ring. Got: {[f.content for f in results]}"
        )

    def test_multiagent_ring_stores_in_promoting_agent_shard(self):
        """With 5 agents on the ring, fact stays in the promoting agent's shard.

        This is the Bug 1 fix: before the fix, DHT would route to a hash-determined
        owner which could be any of the 5 agents. After the fix, the fact is always
        in the promoting agent's own shard regardless of DHT hash.
        """
        # Single DHT with all 5 agents registered (mirrors _init_dht_hive setup)
        dht = DistributedHiveGraph(hive_id="test-multi", enable_gossip=False)
        for i in range(5):
            dht.register_agent(f"agent-{i}")

        fact = _make_fact("Photosynthesis converts light to energy", "biology", "agent-2")
        dht.promote_fact("agent-2", fact)

        # The fact must be in agent-2's shard specifically
        shard = dht._router.get_shard("agent-2")
        assert shard is not None
        all_facts = shard.get_all_facts()
        assert any("Photosynthesis" in f.content for f in all_facts), (
            "Bug 1: fact not in promoting agent's shard. "
            f"Shard contents: {[f.content for f in all_facts]}"
        )

    def test_promote_fact_does_not_broadcast_shard_store(self):
        """promote_fact stores locally only — no SHARD_STORE broadcast (pure DHT sharding).

        Commit e2da57e9 (full replication) reverted. Cross-shard retrieval quality
        is now achieved via CognitiveAdapter.search() in handle_shard_query instead.
        """
        bus = LocalEventBus()
        bus.subscribe("agent-0")
        bus.subscribe("agent-1")
        bus.subscribe("agent-2")

        transport = ServiceBusShardTransport(event_bus=bus, agent_id="agent-0")
        dht = DistributedHiveGraph(
            hive_id="test-no-replication", enable_gossip=False, transport=transport
        )
        for i in range(3):
            dht.register_agent(f"agent-{i}")

        fact = _make_fact("Mars is the fourth planet", "astronomy", "agent-0")
        dht.promote_fact("agent-0", fact)

        # No SHARD_STORE events should be published to peers (pure DHT sharding)
        for sub in ["agent-1", "agent-2"]:
            events = bus.poll(sub)
            store_events = [e for e in events if e.event_type == "SHARD_STORE"]
            assert len(store_events) == 0, (
                f"promote_fact should NOT broadcast SHARD_STORE after revert of e2da57e9, "
                f"got events to {sub}: {[e.event_type for e in events]}"
            )
        bus.close()


class TestDHTSelectQueryTargetsFix:
    """Bug 2 fix: _select_query_targets returns all agents in distributed mode."""

    def test_returns_all_agents_when_some_shards_empty(self):
        """When only some shards are non-empty, all agents are returned for fan-out."""
        from amplihack.agents.goal_seeking.hive_mind.dht import DHTRouter

        router = DHTRouter(replication_factor=3, query_fanout=5)
        for i in range(5):
            router.add_agent(f"agent-{i}")

        # Only agent-0 has facts
        shard_0 = router.get_shard("agent-0")
        from amplihack.agents.goal_seeking.hive_mind.dht import ShardFact

        shard_0.store(
            ShardFact(
                fact_id="f1",
                content="Test fact in agent-0",
                concept="test",
                source_agent="agent-0",
            )
        )

        targets = router.select_query_targets("Test fact")
        assert set(targets) == {f"agent-{i}" for i in range(5)}, (
            f"Bug 2: expected all 5 agents for fan-out, got: {targets}"
        )

    def test_returns_only_nonempty_when_all_populated(self):
        """In-process mode: when ALL shards have facts, return only non-empty (optimization)."""
        from amplihack.agents.goal_seeking.hive_mind.dht import DHTRouter, ShardFact

        router = DHTRouter(replication_factor=3, query_fanout=5)
        for i in range(3):
            router.add_agent(f"agent-{i}")

        # All agents have facts
        for i in range(3):
            shard = router.get_shard(f"agent-{i}")
            shard.store(
                ShardFact(
                    fact_id=f"f{i}",
                    content=f"Fact {i} content",
                    concept="test",
                    source_agent=f"agent-{i}",
                )
            )

        targets = router.select_query_targets("Fact content")
        # All 3 agents have non-empty local shards → local shortcut applies
        assert len(targets) == 3, f"Expected 3 targets (all populated), got: {targets}"

    def test_distributed_mode_agent1_returns_all_agents_even_with_own_facts(self):
        """Bug 2 fix: agent-1's DHT returns all agents even when agent-1 has local facts.

        Before fix: 'local_targets and len(self._shards) == len(all_agents)' triggered
        when agent-1 had some local facts and all ShardStores existed, returning only
        agent-1's shard and missing remote facts from other agents.
        """
        from amplihack.agents.goal_seeking.hive_mind.dht import DHTRouter, ShardFact

        router = DHTRouter(replication_factor=3, query_fanout=5)
        for i in range(5):
            router.add_agent(f"agent-{i}")

        # Only agent-1 has facts locally (simulates distributed mode where
        # other agents' shards are empty stubs, real facts on remote machines)
        shard_1 = router.get_shard("agent-1")
        shard_1.store(
            ShardFact(
                fact_id="local-fact",
                content="Local fact in agent-1",
                concept="test",
                source_agent="agent-1",
            )
        )

        targets = router.select_query_targets("local fact")
        # Must include ALL 5 agents (not just agent-1) so remote shards are queried
        assert set(targets) == {f"agent-{i}" for i in range(5)}, (
            f"Bug 2: only returned {targets}, missing remote agents"
        )


# ---------------------------------------------------------------------------
# EventHubsShardTransport — local unit tests (no Azure connection needed)
# ---------------------------------------------------------------------------


class TestEventHubsShardTransportLocal:
    """Unit tests for EventHubsShardTransport logic using _start_receiving=False.

    Tests drive the internal mailbox directly, bypassing the background receive
    thread so no azure-eventhub connection is required.
    """

    def _make_transport(self, agent_id: str) -> Any:
        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            EventHubsShardTransport,
        )

        return EventHubsShardTransport(
            connection_string="Endpoint=sb://fake.servicebus.windows.net/;...",
            eventhub_name="hive-shards-test",
            agent_id=agent_id,
            _start_receiving=False,  # Skip background thread — drive mailbox directly
        )

    def test_query_shard_local_bypass(self):
        """query_shard on own agent_id queries local shard without publishing events."""
        transport = self._make_transport("agent-0")
        dht = DistributedHiveGraph(
            hive_id="eh-local-bypass", enable_gossip=False, transport=transport
        )
        dht.register_agent("agent-0")
        dht.promote_fact(
            "agent-0",
            _make_fact("Event Hubs is reliable", "azure", "agent-0"),
        )

        results = transport.query_shard("agent-0", "event hubs", limit=5)
        assert any("Event Hubs" in f.content for f in results), (
            f"Local bypass query returned no results: {[f.content for f in results]}"
        )

    def test_handle_shard_query_falls_back_to_shard_when_no_agent(self):
        """handle_shard_query without agent falls back to direct ShardStore search."""
        from amplihack.agents.goal_seeking.hive_mind.event_bus import BusEvent

        transport = self._make_transport("agent-0")
        dht = DistributedHiveGraph(hive_id="eh-fallback", enable_gossip=False, transport=transport)
        dht.register_agent("agent-0")
        dht.promote_fact(
            "agent-0",
            _make_fact("Canberra is the capital of Australia", "geography", "agent-0"),
        )

        correlation_id = uuid.uuid4().hex
        query_event = BusEvent(
            event_id=uuid.uuid4().hex,
            event_type="SHARD_QUERY",
            source_agent="agent-1",
            timestamp=time.time(),
            payload={
                "query": "Canberra Australia",
                "limit": 5,
                "correlation_id": correlation_id,
                "target_agent": "agent-0",
            },
        )

        # Capture published events by patching _publish
        published: list[dict] = []
        transport._publish = lambda payload, partition_key=None: published.append(payload)

        transport.handle_shard_query(query_event)  # No agent — falls back to shard

        response_events = [p for p in published if p.get("event_type") == "SHARD_RESPONSE"]
        assert len(response_events) == 1
        facts = response_events[0]["payload"]["facts"]
        assert any("Canberra" in f["content"] for f in facts), (
            f"Fallback shard search did not return Canberra: {facts}"
        )

    def test_handle_shard_query_uses_cognitive_adapter_when_agent_provided(self):
        """handle_shard_query with agent uses agent.memory.search_local() (LOCAL-ONLY path)."""
        from amplihack.agents.goal_seeking.hive_mind.event_bus import BusEvent

        transport = self._make_transport("agent-0")
        DistributedHiveGraph(hive_id="eh-ca", enable_gossip=False, transport=transport)

        search_calls: list[str] = []

        class _MockMemory:
            def search_local(self, query, limit=20):
                search_calls.append(query)
                return [
                    type(
                        "F",
                        (),
                        {
                            "fact_id": "ca-1",
                            "content": "CognitiveAdapter: quantum entanglement explanation",
                            "concept": "physics",
                            "confidence": 0.95,
                            "source_agent": "agent-0",
                            "tags": [],
                        },
                    )()
                ]

        class _MockAgent:
            memory = _MockMemory()

        correlation_id = uuid.uuid4().hex
        query_event = BusEvent(
            event_id=uuid.uuid4().hex,
            event_type="SHARD_QUERY",
            source_agent="agent-1",
            timestamp=time.time(),
            payload={
                "query": "quantum entanglement",
                "limit": 5,
                "correlation_id": correlation_id,
                "target_agent": "agent-0",
            },
        )

        published: list[dict] = []
        transport._publish = lambda payload, partition_key=None: published.append(payload)
        transport._local_graph = type(
            "G",
            (),
            {"_router": type("R", (), {"get_shard": lambda self, aid: None})()},
        )()

        transport.handle_shard_query(query_event, agent=_MockAgent())

        assert search_calls, "agent.memory.search_local() was not called"
        assert search_calls[0] == "quantum entanglement"
        response_events = [p for p in published if p.get("event_type") == "SHARD_RESPONSE"]
        assert len(response_events) == 1
        facts = response_events[0]["payload"]["facts"]
        assert any("CognitiveAdapter" in f["content"] for f in facts), (
            f"CognitiveAdapter result missing from EH SHARD_RESPONSE: {facts}"
        )

    def test_handle_shard_query_cognitive_adapter_dict_format(self):
        """handle_shard_query correctly handles CognitiveAdapter dict results.

        CognitiveAdapter.search() returns dicts with ``outcome``/``context``/
        ``confidence`` keys.  Previously getattr(f, 'content', '') on a dict
        returned '' causing ALL results to be filtered, producing empty
        SHARD_RESPONSE and ~50% eval score vs 90%+ single-agent.
        """
        from amplihack.agents.goal_seeking.hive_mind.event_bus import BusEvent

        transport = self._make_transport("agent-0")
        DistributedHiveGraph(hive_id="eh-ca-dict", enable_gossip=False, transport=transport)

        class _MockMemory:
            def search_local(self, query, limit=20):
                # Real CognitiveAdapter returns dicts with outcome/context/confidence
                return [
                    {
                        "experience_id": "ca-dict-1",
                        "outcome": "Sarah Chen was born on March 15 1992",
                        "context": "Personal Information",
                        "confidence": 0.92,
                        "timestamp": "",
                        "tags": ["birthday", "person"],
                        "metadata": {},
                    }
                ]

        class _MockAgent:
            memory = _MockMemory()

        correlation_id = uuid.uuid4().hex
        query_event = BusEvent(
            event_id=uuid.uuid4().hex,
            event_type="SHARD_QUERY",
            source_agent="agent-1",
            timestamp=time.time(),
            payload={
                "query": "Sarah Chen birthday",
                "limit": 5,
                "correlation_id": correlation_id,
                "target_agent": "agent-0",
            },
        )

        published: list[dict] = []
        transport._publish = lambda payload, partition_key=None: published.append(payload)
        transport._local_graph = type(
            "G",
            (),
            {"_router": type("R", (), {"get_shard": lambda self, aid: None})()},
        )()

        transport.handle_shard_query(query_event, agent=_MockAgent())

        response_events = [p for p in published if p.get("event_type") == "SHARD_RESPONSE"]
        assert response_events, "No SHARD_RESPONSE published"
        facts = response_events[0].get("payload", {}).get("facts", [])
        assert facts, (
            "SHARD_RESPONSE has empty facts — dict results from CognitiveAdapter "
            "are being dropped (regression in _search_for_shard_response)"
        )
        texts = [f["content"] for f in facts]
        assert any("Sarah Chen" in t for t in texts), (
            f"Expected 'Sarah Chen' fact in SHARD_RESPONSE, got: {texts}"
        )

    def test_handle_shard_response_wakes_pending_query(self):
        """handle_shard_response sets the pending threading.Event."""
        from amplihack.agents.goal_seeking.hive_mind.event_bus import BusEvent

        transport = self._make_transport("agent-1")

        correlation_id = uuid.uuid4().hex
        done = threading.Event()
        results: list[dict] = []
        with transport._pending_lock:
            transport._pending[correlation_id] = (done, results)

        response_event = BusEvent(
            event_id=uuid.uuid4().hex,
            event_type="SHARD_RESPONSE",
            source_agent="agent-0",
            timestamp=time.time(),
            payload={
                "correlation_id": correlation_id,
                "facts": [{"content": "EH response fact", "confidence": 0.9}],
            },
        )
        transport.handle_shard_response(response_event)

        assert done.is_set(), "threading.Event must be set by handle_shard_response"
        assert any("EH response fact" in r.get("content", "") for r in results)

    def test_poll_drains_mailbox(self):
        """poll() returns events added to the mailbox and resets mailbox_ready."""
        from amplihack.agents.goal_seeking.hive_mind.event_bus import BusEvent

        transport = self._make_transport("agent-0")

        # Manually inject an event into the mailbox
        fake_event = BusEvent(
            event_id="test",
            event_type="SHARD_QUERY",
            source_agent="agent-1",
            timestamp=time.time(),
            payload={"query": "test", "limit": 5, "correlation_id": "abc"},
        )
        with transport._mailbox_lock:
            transport._mailbox.append(fake_event)
        transport._mailbox_ready.set()

        events = transport.poll("agent-0")
        assert len(events) == 1
        assert events[0].event_type == "SHARD_QUERY"

        # Mailbox should be empty now
        assert transport._mailbox == []


# ---------------------------------------------------------------------------
# CognitiveAdapter cross-shard retrieval via ServiceBusShardTransport
# ---------------------------------------------------------------------------


class TestServiceBusShardTransportCognitiveAdapter:
    """Verify handle_shard_query uses CognitiveAdapter when agent is provided."""

    def test_handle_shard_query_with_agent_uses_memory_search(self):
        """handle_shard_query with agent uses agent.memory.search_local() not ShardStore."""
        bus = LocalEventBus()
        bus.subscribe("agent-0")
        bus.subscribe("agent-1")

        sb_transport = ServiceBusShardTransport(event_bus=bus, agent_id="agent-0")
        dht = DistributedHiveGraph(
            hive_id="sb-ca-test", enable_gossip=False, transport=sb_transport
        )
        dht.register_agent("agent-0")

        search_calls: list[str] = []

        class _MockMemory:
            def search_local(self, query, limit=20):
                search_calls.append(query)
                return [
                    type(
                        "F",
                        (),
                        {
                            "fact_id": "sb-ca-1",
                            "content": "CognitiveAdapter: Sahara is in Africa",
                            "concept": "geography",
                            "confidence": 0.92,
                            "source_agent": "agent-0",
                            "tags": [],
                        },
                    )()
                ]

        class _MockAgent:
            memory = _MockMemory()

        correlation_id = uuid.uuid4().hex
        query_event = make_event(
            event_type="SHARD_QUERY",
            source_agent="agent-1",
            payload={
                "query": "Sahara Africa",
                "limit": 5,
                "correlation_id": correlation_id,
                "target_agent": "agent-0",
            },
        )
        bus.publish(query_event)

        for event in bus.poll("agent-0"):
            if event.event_type == "SHARD_QUERY":
                sb_transport.handle_shard_query(event, agent=_MockAgent())

        assert search_calls, "agent.memory.search_local() was not called"
        response_facts: list[dict] = []
        for event in bus.poll("agent-1"):
            if (
                event.event_type == "SHARD_RESPONSE"
                and event.payload.get("correlation_id") == correlation_id
            ):
                response_facts.extend(event.payload.get("facts", []))

        texts = [f["content"] for f in response_facts]
        assert any("CognitiveAdapter" in t for t in texts), (
            f"CognitiveAdapter result missing from SB SHARD_RESPONSE: {texts}"
        )
        bus.close()


# ---------------------------------------------------------------------------
# Direct _search_for_shard_response unit tests
# ---------------------------------------------------------------------------


class TestSearchForShardResponse:
    """Verify _search_for_shard_response uses CognitiveAdapter when agent is provided."""

    def test_shard_query_uses_cognitive_adapter_when_agent_provided(self):
        """With a mock agent, _search_for_shard_response returns CognitiveAdapter results."""
        cognitive_results = [
            {
                "outcome": "test fact",
                "context": "test concept",
                "confidence": 0.9,
                "experience_id": "test-id",
                "tags": [],
            }
        ]

        class _MockMemory:
            def search_local(self, query: str, limit: int = 20) -> list[dict]:
                return cognitive_results

        class _MockAgent:
            memory = _MockMemory()

        local_graph = DistributedHiveGraph(hive_id="shard-ca-unit", enable_gossip=False)
        local_graph.register_agent("agent-0")
        # Promote a shard fact so ShardStore fallback would return something different
        local_graph.promote_fact(
            "agent-0",
            _make_fact("shard store fallback fact", "fallback", "agent-0"),
        )

        facts = _search_for_shard_response(
            query="test query",
            limit=5,
            agent=_MockAgent(),
            local_graph=local_graph,
            agent_id="agent-0",
        )

        assert len(facts) == 1
        assert facts[0]["content"] == "test fact"
        assert facts[0]["concept"] == "test concept"
        assert facts[0]["confidence"] == 0.9
        assert facts[0]["fact_id"] == "test-id"
        assert facts[0]["source_agent"] == "agent-0"

    def test_shard_query_falls_back_to_shard_store_when_no_agent(self):
        """With agent=None, _search_for_shard_response falls back to ShardStore."""
        local_graph = DistributedHiveGraph(hive_id="shard-fb-unit", enable_gossip=False)
        local_graph.register_agent("agent-0")
        local_graph.promote_fact(
            "agent-0",
            _make_fact("fallback shard fact about dogs", "animals", "agent-0"),
        )

        facts = _search_for_shard_response(
            query="dogs",
            limit=5,
            agent=None,
            local_graph=local_graph,
            agent_id="agent-0",
        )

        assert len(facts) >= 1
        texts = [f["content"] for f in facts]
        assert any("dogs" in t for t in texts), (
            f"ShardStore fallback should find 'dogs' fact, got: {texts}"
        )
