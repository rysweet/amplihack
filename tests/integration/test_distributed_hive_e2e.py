"""End-to-end integration test for DHT-based distributed hive sharding (issue #3034).

Validates the full data flow using proper DHT sharding (not replication):
  Agent-0 promotes facts to its local DistributedHiveGraph shard
  -> Agent-0 shard is queryable via SHARD_QUERY/SHARD_RESPONSE protocol
  -> Agent-1 sends SHARD_QUERY to LocalEventBus
  -> Agent-0's ServiceBusShardTransport responds with SHARD_RESPONSE
  -> Agent-1 receives cross-shard facts without replication

Key property: each agent stores only its DHT-assigned shard (O(F/N) per agent),
not all facts replicated to every agent (O(F) per agent).

All tests run locally with no Azure, no LLM, no network.
Uses LocalEventBus as a stand-in for AzureServiceBusEventBus.

DI pattern: ServiceBusShardTransport injected into DistributedHiveGraph.
Agent code is transport-agnostic — GoalSeekingAgent receives DistributedHiveGraph
directly as hive_store with no wrapper classes.
"""

from __future__ import annotations

import importlib.util
import tempfile
import threading
import time
import uuid
from pathlib import Path

import pytest

from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter
from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent
from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
    DistributedHiveGraph,
    ServiceBusShardTransport,
)
from amplihack.agents.goal_seeking.hive_mind.event_bus import (
    LocalEventBus,
    make_event,
)
from amplihack.agents.goal_seeking.hive_mind.hive_graph import HiveFact

# Load _shard_query_listener from the deploy entrypoint
_ENTRYPOINT_PATH = (
    Path(__file__).resolve().parents[2] / "deploy" / "azure_hive" / "agent_entrypoint.py"
)
_spec = importlib.util.spec_from_file_location("agent_entrypoint", _ENTRYPOINT_PATH)
assert _spec is not None and _spec.loader is not None
_entrypoint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_entrypoint)
_shard_query_listener = _entrypoint._shard_query_listener


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def two_shard_cluster():
    """Two agents each with ServiceBusShardTransport + DistributedHiveGraph and a shared bus.

    DI pattern: transport is injected into graph; graph passed directly as hive_store.
    """
    bus = LocalEventBus()

    # Agent-0: owns its DHT shard
    sb_transport_0 = ServiceBusShardTransport(event_bus=bus, agent_id="agent-0")
    dht_0 = DistributedHiveGraph(
        hive_id="shard-agent-0", enable_gossip=False, transport=sb_transport_0
    )
    dht_0.register_agent("agent-0")
    bus.subscribe("agent-0")

    # Agent-1: owns its DHT shard
    sb_transport_1 = ServiceBusShardTransport(event_bus=bus, agent_id="agent-1")
    dht_1 = DistributedHiveGraph(
        hive_id="shard-agent-1", enable_gossip=False, transport=sb_transport_1
    )
    dht_1.register_agent("agent-1")
    bus.subscribe("agent-1")

    yield {
        "bus": bus,
        "dht_0": dht_0,
        "dht_1": dht_1,
        "transport_0": sb_transport_0,
        "transport_1": sb_transport_1,
    }

    bus.close()


# ---------------------------------------------------------------------------
# Phase 1: Core data flow — DHT sharding, not replication
# ---------------------------------------------------------------------------


class TestDHTShardDataFlow:
    """Verify facts stay in their shard and are retrieved via cross-shard query."""

    def test_promote_fact_stores_locally_no_replication(self, two_shard_cluster):
        """promote_fact stores in local shard only — no FACT_PROMOTED event published."""
        dht_0 = two_shard_cluster["dht_0"]
        dht_1 = two_shard_cluster["dht_1"]
        bus = two_shard_cluster["bus"]

        fact = _make_fact("Mitochondria are the powerhouse of the cell", "biology", "agent-0")
        dht_0.promote_fact("agent-0", fact)

        # Fact stored in agent-0's shard
        facts_0 = dht_0.query_facts("mitochondria")
        assert any("Mitochondria" in f.content for f in facts_0)

        # NOT in agent-1's shard (no replication)
        facts_1 = dht_1.query_facts("mitochondria")
        assert len(facts_1) == 0

        # No event published to bus (local bypass — no SHARD_STORE broadcast)
        bus_events = bus.poll("agent-1")
        assert bus_events == [], "Local store must not broadcast facts via bus"

    def test_total_storage_equals_facts_promoted(self, two_shard_cluster):
        """With two shards, total stored facts == promoted facts (no replication)."""
        dht_0 = two_shard_cluster["dht_0"]
        dht_1 = two_shard_cluster["dht_1"]

        # Each agent promotes one fact to its own shard
        dht_0.promote_fact("agent-0", _make_fact("Alpha fact", "alpha", "agent-0"))
        dht_1.promote_fact("agent-1", _make_fact("Beta fact", "beta", "agent-1"))

        total_0 = dht_0.get_stats()["fact_count"]
        total_1 = dht_1.get_stats()["fact_count"]

        # Each shard has its own fact (DHT may route to either, but total = 2)
        assert total_0 + total_1 == 2, (
            f"Expected 2 facts total (no replication), got {total_0 + total_1}"
        )

    def test_cross_shard_query_via_shard_query_protocol(self, two_shard_cluster):
        """agent-1 can retrieve agent-0's facts via SHARD_QUERY/SHARD_RESPONSE."""
        dht_0 = two_shard_cluster["dht_0"]
        transport_0 = two_shard_cluster["transport_0"]
        bus = two_shard_cluster["bus"]

        # Agent-0 promotes a fact
        dht_0.promote_fact(
            "agent-0",
            _make_fact("Sarah Chen was born on March 15, 1992", "people", "agent-0"),
        )

        # Agent-1 asks via SHARD_QUERY
        correlation_id = uuid.uuid4().hex
        query_event = make_event(
            event_type="SHARD_QUERY",
            source_agent="agent-1",
            payload={"query": "Sarah Chen", "limit": 5, "correlation_id": correlation_id},
        )
        bus.publish(query_event)

        # Agent-0 processes the SHARD_QUERY and responds via its transport
        for event in bus.poll("agent-0"):
            if event.event_type == "SHARD_QUERY":
                transport_0.handle_shard_query(event)

        # Agent-1 receives SHARD_RESPONSE
        response_facts: list[dict] = []
        for event in bus.poll("agent-1"):
            if (
                event.event_type == "SHARD_RESPONSE"
                and event.payload.get("correlation_id") == correlation_id
            ):
                response_facts.extend(event.payload.get("facts", []))

        texts = [f["content"] for f in response_facts]
        assert any("Sarah Chen" in t or "March 15" in t for t in texts), (
            f"Cross-shard query did not return expected facts. Got: {texts}"
        )

    def test_shard_response_wakes_pending_query_event(self, two_shard_cluster):
        """SHARD_RESPONSE fires threading.Event without sleep — event-driven."""
        dht_0 = two_shard_cluster["dht_0"]
        transport_0 = two_shard_cluster["transport_0"]
        transport_1 = two_shard_cluster["transport_1"]
        bus = two_shard_cluster["bus"]

        dht_0.promote_fact(
            "agent-0", _make_fact("The speed of light is 299792458 m/s", "physics", "agent-0")
        )

        # Set up pending query with threading.Event in transport_1
        correlation_id = uuid.uuid4().hex
        done = threading.Event()
        results: list[dict] = []
        with transport_1._pending_lock:
            transport_1._pending[correlation_id] = (done, results)

        # Simulate SHARD_RESPONSE arriving from agent-0
        query_event = make_event(
            event_type="SHARD_QUERY",
            source_agent="agent-1",
            payload={"query": "speed light", "limit": 5, "correlation_id": correlation_id},
        )
        bus.publish(query_event)
        for event in bus.poll("agent-0"):
            if event.event_type == "SHARD_QUERY":
                transport_0.handle_shard_query(event)

        # Now agent-1 receives the SHARD_RESPONSE
        for event in bus.poll("agent-1"):
            if event.event_type == "SHARD_RESPONSE":
                transport_1.handle_shard_response(event)

        # threading.Event should be set without any sleep
        assert done.is_set(), "Pending query done_event was not set by SHARD_RESPONSE"
        assert any("299792458" in r.get("content", "") for r in results), (
            f"Cross-shard facts not in results. Got: {results}"
        )


# ---------------------------------------------------------------------------
# Phase 2: CognitiveAdapter integration with DistributedHiveGraph (DI)
# ---------------------------------------------------------------------------


class TestCognitiveAdapterWithShardedHive:
    """Verify CognitiveAdapter.search() works with DistributedHiveGraph directly."""

    def test_search_returns_local_shard_facts(self, two_shard_cluster):
        """Local shard facts are returned by CognitiveAdapter.search()."""
        dht_1 = two_shard_cluster["dht_1"]

        dht_1.promote_fact(
            "agent-1",
            _make_fact("Chloroplasts contain chlorophyll", "biology", "agent-1"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Pass DistributedHiveGraph directly as hive_store — no wrapper
            adapter = CognitiveAdapter(
                agent_name="agent-1",
                db_path=Path(tmpdir) / "agent-1",
                hive_store=dht_1,
                quality_threshold=0.0,
                confidence_gate=0.0,
            )

            results = adapter.search("chloroplasts chlorophyll")
            contents = [r.get("outcome", "") for r in results]
            assert any(
                "chloroplast" in c.lower() or "chlorophyll" in c.lower() for c in contents
            ), f"Local shard fact missing from search results: {contents}"


# ---------------------------------------------------------------------------
# Phase 3: GoalSeekingAgent orient() surfaces local shard facts
# ---------------------------------------------------------------------------


class TestOrientSurfacesLocalShardFacts:
    """Verify orient() returns facts from the local DHT shard."""

    def test_orient_includes_local_shard_facts_in_context(self, two_shard_cluster):
        dht_1 = two_shard_cluster["dht_1"]

        dht_1.promote_fact(
            "agent-1",
            _make_fact("Sarah Chen was born on March 15, 1992", "people", "agent-1"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Pass DistributedHiveGraph directly as hive_store — no wrapper
            agent = GoalSeekingAgent(
                agent_name="agent-1",
                storage_path=Path(tmpdir),
                use_hierarchical=True,
                hive_store=dht_1,
            )

            agent.observe("When was Sarah Chen born?")
            context = agent.orient()

            facts = context.get("facts", [])
            fact_text = " ".join(str(f) for f in facts)

            assert "Sarah Chen" in fact_text or "March 15" in fact_text or "1992" in fact_text, (
                f"orient() did not surface local shard fact about Sarah Chen. Got facts: {facts}"
            )


# ---------------------------------------------------------------------------
# Phase 4: Background _shard_query_listener handles queries event-driven
# ---------------------------------------------------------------------------


class TestShardQueryListenerThread:
    """Verify the _shard_query_listener background thread handles queries without sleep."""

    def test_listener_responds_to_shard_query(self, two_shard_cluster):
        """_shard_query_listener responds to SHARD_QUERY from peer agents."""
        dht_0 = two_shard_cluster["dht_0"]
        transport_0 = two_shard_cluster["transport_0"]
        bus = two_shard_cluster["bus"]

        dht_0.promote_fact(
            "agent-0",
            _make_fact("DNA carries genetic information", "biology", "agent-0"),
        )

        shutdown = threading.Event()
        # _shard_query_listener now takes (transport, agent_id, bus, shutdown)
        listener = threading.Thread(
            target=_shard_query_listener,
            args=(transport_0, "agent-0", bus, shutdown),
            daemon=True,
            name="test-shard-listener",
        )
        listener.start()

        try:
            # Send SHARD_QUERY from agent-1
            correlation_id = uuid.uuid4().hex
            query_event = make_event(
                event_type="SHARD_QUERY",
                source_agent="agent-1",
                payload={"query": "genetic DNA", "limit": 5, "correlation_id": correlation_id},
            )
            bus.publish(query_event)

            # Wait for SHARD_RESPONSE in agent-1's mailbox (event-driven wait)
            deadline = time.time() + 2.0
            response_facts: list[dict] = []
            while time.time() < deadline and not response_facts:
                for event in bus.poll("agent-1"):
                    if (
                        event.event_type == "SHARD_RESPONSE"
                        and event.payload.get("correlation_id") == correlation_id
                    ):
                        response_facts.extend(event.payload.get("facts", []))
                if not response_facts:
                    time.sleep(0.01)  # Thread yielding only, not a timing assumption

            texts = [f["content"] for f in response_facts]
            assert any("DNA" in t or "genetic" in t for t in texts), (
                f"_shard_query_listener did not respond with correct facts. Got: {texts}"
            )
        finally:
            shutdown.set()
            listener.join(timeout=2.0)

    def test_listener_exits_on_shutdown(self, two_shard_cluster):
        """_shard_query_listener exits cleanly when shutdown_event is set."""
        transport_0 = two_shard_cluster["transport_0"]
        bus = two_shard_cluster["bus"]

        shutdown = threading.Event()
        listener = threading.Thread(
            target=_shard_query_listener,
            args=(transport_0, "agent-0", bus, shutdown),
            daemon=True,
        )
        listener.start()

        shutdown.set()
        listener.join(timeout=2.0)
        assert not listener.is_alive(), "_shard_query_listener did not exit after shutdown"


# ---------------------------------------------------------------------------
# Phase 5: 5-agent cluster — production-topology repro (issue #3034)
# ---------------------------------------------------------------------------


@pytest.fixture()
def five_agent_cluster():
    """Five agents each with ServiceBusShardTransport + shared LocalEventBus.

    Mirrors the production topology from _init_dht_hive: ALL agents are
    registered on EACH agent's DHT ring so the ring topology is shared.
    Only the local agent's ShardStore receives stored facts (Bug 1 fix).
    Queries fan out to ALL agents via SHARD_QUERY/SHARD_RESPONSE (Bug 2 fix).
    """
    bus = LocalEventBus()
    agent_names = [f"agent-{i}" for i in range(5)]

    dhts: dict[str, DistributedHiveGraph] = {}
    transports: dict[str, ServiceBusShardTransport] = {}

    for name in agent_names:
        bus.subscribe(name)
        transport = ServiceBusShardTransport(event_bus=bus, agent_id=name, timeout=3.0)
        dht = DistributedHiveGraph(
            hive_id=f"shard-{name}", enable_gossip=False, transport=transport
        )
        # Mirror _init_dht_hive: register ALL agents on every ring
        for peer in agent_names:
            dht.register_agent(peer)
        dhts[name] = dht
        transports[name] = transport

    yield {"bus": bus, "dhts": dhts, "transports": transports, "agent_names": agent_names}

    bus.close()


class TestFiveAgentCluster:
    """5-agent production-topology repro: cross-shard queries work after both fixes."""

    def test_promote_fact_stores_locally_not_remote_shard(self, five_agent_cluster):
        """Bug 1 fix: fact promoted by agent-0 stays in agent-0's local shard."""
        dhts = five_agent_cluster["dhts"]

        dhts["agent-0"].promote_fact(
            "agent-0",
            _make_fact("Sarah Chen was born on March 15, 1992", "people", "agent-0"),
        )

        # Fact is in agent-0's own shard
        facts_0 = dhts["agent-0"].query_facts("Sarah Chen")
        assert any("Sarah Chen" in f.content for f in facts_0), (
            f"agent-0's local shard should hold the promoted fact. Got: {[f.content for f in facts_0]}"
        )

    def test_agent1_queries_agent0_facts_via_shard_query_protocol(self, five_agent_cluster):
        """agent-1 retrieves facts stored by agent-0 via SHARD_QUERY/SHARD_RESPONSE."""
        dhts = five_agent_cluster["dhts"]
        transports = five_agent_cluster["transports"]
        bus = five_agent_cluster["bus"]
        agent_names = five_agent_cluster["agent_names"]

        # agent-0 promotes a fact (stored locally in agent-0's shard — Bug 1 fix)
        dhts["agent-0"].promote_fact(
            "agent-0",
            _make_fact("Sarah Chen was born on March 15, 1992", "people", "agent-0"),
        )

        # Start shard listeners for all agents except agent-1 (the querier)
        shutdown = threading.Event()
        listeners = []
        for name in agent_names:
            if name == "agent-1":
                continue
            t = threading.Thread(
                target=_shard_query_listener,
                args=(transports[name], name, bus, shutdown),
                daemon=True,
                name=f"shard-{name}",
            )
            t.start()
            listeners.append(t)

        try:
            # agent-1 queries via its own DHT — Bug 2 fix fans out to all agents
            # Start a listener thread for agent-1's SHARD_RESPONSE collection
            def agent1_response_listener():
                while not shutdown.is_set():
                    for event in bus.poll("agent-1"):
                        if event.event_type == "SHARD_RESPONSE":
                            transports["agent-1"].handle_shard_response(event)
                    time.sleep(0.005)

            t1 = threading.Thread(target=agent1_response_listener, daemon=True)
            t1.start()
            listeners.append(t1)

            # query_facts fans out SHARD_QUERY to all agents (Bug 2 fix)
            results = dhts["agent-1"].query_facts("Sarah Chen", limit=10)

            texts = [f.content for f in results]
            assert any("Sarah Chen" in t or "March 15" in t for t in texts), (
                f"agent-1 did not retrieve agent-0's fact via cross-shard query. Got: {texts}"
            )
        finally:
            shutdown.set()
            for t in listeners:
                t.join(timeout=2.0)

    def test_all_agents_can_retrieve_any_fact(self, five_agent_cluster):
        """Each agent can retrieve facts stored by any other agent."""
        dhts = five_agent_cluster["dhts"]
        transports = five_agent_cluster["transports"]
        bus = five_agent_cluster["bus"]
        agent_names = five_agent_cluster["agent_names"]

        # Each agent promotes a unique fact
        facts_by_agent = {
            "agent-0": "Alpha subject learned by agent zero",
            "agent-2": "Gamma subject learned by agent two",
            "agent-4": "Epsilon subject learned by agent four",
        }
        for agent_id, content in facts_by_agent.items():
            dhts[agent_id].promote_fact(
                agent_id,
                _make_fact(content, "test", agent_id),
            )

        # Start listeners for all agents
        shutdown = threading.Event()
        listeners = []
        for name in agent_names:
            transport = transports[name]

            def make_listener(t, n):
                def loop():
                    while not shutdown.is_set():
                        for event in bus.poll(n):
                            if event.event_type == "SHARD_QUERY":
                                t.handle_shard_query(event)
                            elif event.event_type == "SHARD_RESPONSE":
                                t.handle_shard_response(event)
                        time.sleep(0.005)

                return loop

            thread = threading.Thread(
                target=make_listener(transport, name), daemon=True, name=f"listener-{name}"
            )
            thread.start()
            listeners.append(thread)

        try:
            # agent-1 (which has no facts) queries for each stored fact
            for agent_id, content in facts_by_agent.items():
                query_word = content.split()[0]
                results = dhts["agent-1"].query_facts(query_word, limit=5)
                texts = [f.content for f in results]
                assert any(content in t for t in texts), (
                    f"agent-1 could not retrieve '{content}' stored by {agent_id}. Got: {texts}"
                )
        finally:
            shutdown.set()
            for t in listeners:
                t.join(timeout=2.0)

    def test_target_agent_filter_prevents_wrong_agent_response(self, five_agent_cluster):
        """Fix: handle_shard_query must ignore SHARD_QUERY not targeting this agent.

        Without the target_agent filter all agents respond to every SHARD_QUERY.
        On Azure Service Bus (Standard SKU) a wrong agent's empty response can
        arrive first, wake done.wait(), and cause the correct agent's facts to
        be dropped after pending[correlation_id] is removed.

        This test sends a SHARD_QUERY targeting agent-0 and verifies that agents
        1-4 do NOT publish a SHARD_RESPONSE for it.
        """
        transports = five_agent_cluster["transports"]
        bus = five_agent_cluster["bus"]

        # Send a SHARD_QUERY explicitly targeting agent-0
        correlation_id = uuid.uuid4().hex
        query_event = make_event(
            event_type="SHARD_QUERY",
            source_agent="agent-1",
            payload={
                "query": "test query",
                "limit": 5,
                "correlation_id": correlation_id,
                "target_agent": "agent-0",  # ← only agent-0 should respond
            },
        )
        bus.publish(query_event)

        # Drain SHARD_QUERY from agents 1-4's mailboxes and call handle_shard_query
        response_count = 0
        for agent_id in ["agent-1", "agent-2", "agent-3", "agent-4"]:
            for event in bus.poll(agent_id):
                if event.event_type == "SHARD_QUERY":
                    transports[agent_id].handle_shard_query(event)

        # Collect SHARD_RESPONSE events from agent-1's mailbox
        # (responses from agents 2-4 would go to agent-1 since it sent the query)
        import time as _time

        _time.sleep(0.05)  # allow any spurious publishes to arrive
        for event in bus.poll("agent-1"):
            if (
                event.event_type == "SHARD_RESPONSE"
                and event.payload.get("correlation_id") == correlation_id
            ):
                response_count += 1

        assert response_count == 0, (
            f"Non-targeted agents must NOT respond to SHARD_QUERY. "
            f"Got {response_count} spurious SHARD_RESPONSE(s) from agents 1-4."
        )

    def test_total_facts_equals_promoted_no_replication(self, five_agent_cluster):
        """Bug 1 fix: total facts across all shards == number promoted (no duplication)."""
        dhts = five_agent_cluster["dhts"]

        for i in range(5):
            dhts[f"agent-{i}"].promote_fact(
                f"agent-{i}",
                _make_fact(f"Unique fact number {i} from agent {i}", "test", f"agent-{i}"),
            )

        # Each agent's DHT counts facts in its own local shard only
        # (remote agents' shards are empty stubs in other agents' DHTs)
        total = sum(dhts[f"agent-{i}"].get_stats()["fact_count"] for i in range(5))

        # With Bug 1 fix: each agent stores locally → 5 facts total across local shards
        # Without fix: DHT would route to remote agents losing facts or doubling them
        assert total == 5, f"Expected 5 facts total (one per agent, no replication), got {total}"


# ---------------------------------------------------------------------------
# Phase 6: Full GoalSeekingAgent orient() cross-agent fact retrieval
# ---------------------------------------------------------------------------


class TestGoalSeekingAgentOrientCrossAgent:
    """Criterion 6: agent-1's orient() surfaces facts stored by agent-0 via cross-shard query."""

    def test_orient_surfaces_cross_agent_facts(self, five_agent_cluster):
        """Full GoalSeekingAgent orient() path: agent-1 orient() retrieves agent-0's facts.

        This validates the complete stack:
          GoalSeekingAgent.orient()
            -> CognitiveAdapter.search() -> _search_hive()
            -> DistributedHiveGraph.query_facts()
            -> DHTRouter._select_query_targets() fans out to all agents (Bug 2 fix)
            -> SHARD_QUERY sent to agent-0 via ServiceBusShardTransport
            -> agent-0 shard listener responds with SHARD_RESPONSE
            -> agent-1 collects SHARD_RESPONSE and returns facts
        """
        dhts = five_agent_cluster["dhts"]
        transports = five_agent_cluster["transports"]
        bus = five_agent_cluster["bus"]
        agent_names = five_agent_cluster["agent_names"]

        # agent-0 promotes a fact (stored locally via Bug 1 fix)
        dhts["agent-0"].promote_fact(
            "agent-0",
            _make_fact("Marie Curie discovered radium in 1898", "science", "agent-0"),
        )

        # Start shard listeners for all agents (including agent-0 which holds the fact)
        shutdown = threading.Event()
        listeners = []
        for name in agent_names:
            transport = transports[name]
            agent_name = name

            def make_loop(t, n, sb):
                def loop():
                    while not sb.is_set():
                        for event in bus.poll(n):
                            if event.event_type == "SHARD_QUERY":
                                t.handle_shard_query(event)
                            elif event.event_type == "SHARD_RESPONSE":
                                t.handle_shard_response(event)
                        time.sleep(0.005)

                return loop

            thread = threading.Thread(
                target=make_loop(transport, agent_name, shutdown),
                daemon=True,
                name=f"listener-{agent_name}",
            )
            thread.start()
            listeners.append(thread)

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create GoalSeekingAgent for agent-1 using its distributed hive as hive_store
                agent = GoalSeekingAgent(
                    agent_name="agent-1",
                    storage_path=Path(tmpdir),
                    use_hierarchical=True,
                    hive_store=dhts["agent-1"],
                )

                agent.observe("Who discovered radium?")
                context = agent.orient()

                facts = context.get("facts", [])
                fact_text = " ".join(str(f) for f in facts)

                assert "Marie Curie" in fact_text or "radium" in fact_text or "1898" in fact_text, (
                    f"agent-1 orient() did not surface agent-0's fact about Marie Curie. "
                    f"Got facts: {facts}"
                )
        finally:
            shutdown.set()
            for t in listeners:
                t.join(timeout=2.0)


# ---------------------------------------------------------------------------
# Phase 7: SHARD_STORE replication — every agent holds all facts
# ---------------------------------------------------------------------------


@pytest.fixture()
def two_shard_cluster_all_peers():
    """Two agents with cross-registration so replication can occur.

    Each agent registers BOTH agents so promote_fact broadcasts SHARD_STORE
    to peers. This mirrors the production _init_dht_hive() which registers
    all N agents on each DHT.
    """
    bus = LocalEventBus()

    sb_transport_0 = ServiceBusShardTransport(event_bus=bus, agent_id="agent-0")
    dht_0 = DistributedHiveGraph(
        hive_id="shard-agent-0", enable_gossip=False, transport=sb_transport_0
    )
    dht_0.register_agent("agent-0")
    dht_0.register_agent("agent-1")
    bus.subscribe("agent-0")

    sb_transport_1 = ServiceBusShardTransport(event_bus=bus, agent_id="agent-1")
    dht_1 = DistributedHiveGraph(
        hive_id="shard-agent-1", enable_gossip=False, transport=sb_transport_1
    )
    dht_1.register_agent("agent-0")
    dht_1.register_agent("agent-1")
    bus.subscribe("agent-1")

    yield {
        "bus": bus,
        "dht_0": dht_0,
        "dht_1": dht_1,
        "transport_0": sb_transport_0,
        "transport_1": sb_transport_1,
    }

    bus.close()


class TestShardStoreReplication:
    """Verify SHARD_STORE transport protocol: handle_shard_store persists replicated facts.

    Note: promote_fact no longer broadcasts SHARD_STORE events to peers (pure DHT
    sharding — commit e2da57e9 reverted).  Cross-shard retrieval quality is achieved
    via CognitiveAdapter.search() in handle_shard_query instead.  These tests verify
    that the SHARD_STORE handler itself still works correctly for transports that
    explicitly call store_on_shard() on a remote peer (e.g. for manual replication).
    """

    def test_promote_does_not_broadcast_shard_store_to_peers(self, two_shard_cluster_all_peers):
        """promote_fact stores locally only — no SHARD_STORE broadcast (pure DHT sharding)."""
        dht_0 = two_shard_cluster_all_peers["dht_0"]
        bus = two_shard_cluster_all_peers["bus"]

        fact = _make_fact("Sarah Chen was born on March 15", "people", "agent-0")
        dht_0.promote_fact("agent-0", fact)

        # No SHARD_STORE events should be published (pure DHT sharding)
        events = bus.poll("agent-1")
        shard_store_events = [e for e in events if e.event_type == "SHARD_STORE"]
        assert len(shard_store_events) == 0, (
            f"promote_fact should not broadcast SHARD_STORE after revert of e2da57e9, "
            f"got: {[e.event_type for e in events]}"
        )

    def test_handle_shard_store_persists_replica(self, two_shard_cluster_all_peers):
        """handle_shard_store stores a replicated fact in agent-1's local shard."""
        transport_1 = two_shard_cluster_all_peers["transport_1"]
        bus = two_shard_cluster_all_peers["bus"]

        # Manually publish a SHARD_STORE event (as a transport would do)
        store_event = make_event(
            event_type="SHARD_STORE",
            source_agent="agent-0",
            payload={
                "target_agent": "agent-1",
                "fact": {
                    "fact_id": "test-fact-id",
                    "content": "Sarah Chen was born on March 15",
                    "concept": "people",
                    "confidence": 0.9,
                    "source_agent": "agent-0",
                    "tags": ["people"],
                },
            },
        )
        bus.publish(store_event)

        # Process the SHARD_STORE event
        events = bus.poll("agent-1")
        for event in events:
            if event.event_type == "SHARD_STORE":
                transport_1.handle_shard_store(event)

        # Verify via transport_1's local_graph shard
        local_graph = transport_1._local_graph
        assert local_graph is not None
        shard = local_graph._router.get_shard("agent-1")
        assert shard is not None, "agent-1 shard missing from its own DHT router"
        facts = shard.search("sarah chen")
        assert any("Sarah Chen" in f.content for f in facts), (
            f"Replicated fact not found in agent-1's shard after handle_shard_store. "
            f"Shard has {shard.fact_count} facts."
        )


# ---------------------------------------------------------------------------
# Phase 8: CognitiveAdapter cross-shard retrieval via handle_shard_query
# ---------------------------------------------------------------------------


class TestCognitiveAdapterCrossShardRetrieval:
    """Verify that _shard_query_listener passes agent to handle_shard_query
    so cross-shard queries use CognitiveAdapter.search() instead of raw ShardStore.
    """

    def test_handle_shard_query_uses_agent_memory_search(self, two_shard_cluster):
        """handle_shard_query with agent uses agent.memory.search() (CognitiveAdapter path)."""
        transport_0 = two_shard_cluster["transport_0"]
        bus = two_shard_cluster["bus"]

        # Create a mock agent whose memory.search() returns a known result
        search_called_with: list[str] = []

        class _MockMemory:
            def search(self, query, limit=20):
                search_called_with.append(query)
                return [
                    type(
                        "Fact",
                        (),
                        {
                            "fact_id": "ca-fact",
                            "content": "CognitiveAdapter result: Sarah Chen born March 15",
                            "concept": "people",
                            "confidence": 0.95,
                            "source_agent": "agent-0",
                            "tags": [],
                        },
                    )()
                ]

        class _MockAgent:
            memory = _MockMemory()

        mock_agent = _MockAgent()
        correlation_id = uuid.uuid4().hex
        query_event = make_event(
            event_type="SHARD_QUERY",
            source_agent="agent-1",
            payload={
                "query": "Sarah Chen",
                "limit": 5,
                "correlation_id": correlation_id,
                "target_agent": "agent-0",
            },
        )
        bus.publish(query_event)

        # Process via handle_shard_query with agent
        for event in bus.poll("agent-0"):
            if event.event_type == "SHARD_QUERY":
                transport_0.handle_shard_query(event, agent=mock_agent)

        assert search_called_with, "agent.memory.search() was never called"
        assert search_called_with[0] == "Sarah Chen"

        # Verify SHARD_RESPONSE contains CognitiveAdapter result
        response_facts: list[dict] = []
        for event in bus.poll("agent-1"):
            if (
                event.event_type == "SHARD_RESPONSE"
                and event.payload.get("correlation_id") == correlation_id
            ):
                response_facts.extend(event.payload.get("facts", []))

        texts = [f["content"] for f in response_facts]
        assert any("CognitiveAdapter" in t for t in texts), (
            f"CognitiveAdapter result missing from SHARD_RESPONSE. Got: {texts}"
        )

    def test_shard_query_listener_passes_agent_to_handle_shard_query(self, two_shard_cluster):
        """_shard_query_listener passes the agent instance to handle_shard_query."""
        transport_0 = two_shard_cluster["transport_0"]
        bus = two_shard_cluster["bus"]

        search_calls: list[str] = []

        class _MockMemory:
            def search(self, query, limit=20):
                search_calls.append(query)
                return [
                    type(
                        "F",
                        (),
                        {
                            "fact_id": "f1",
                            "content": "Lars Eriksson plays hockey",
                            "concept": "sports",
                            "confidence": 0.9,
                            "source_agent": "agent-0",
                            "tags": [],
                        },
                    )()
                ]

        class _MockAgent:
            memory = _MockMemory()

        mock_agent = _MockAgent()
        shutdown = threading.Event()

        listener_0 = threading.Thread(
            target=_shard_query_listener,
            args=(transport_0, "agent-0", bus, shutdown, mock_agent),
            daemon=True,
        )
        listener_0.start()

        try:
            # Agent-1 sends a SHARD_QUERY targeting agent-0
            correlation_id = uuid.uuid4().hex
            query_event = make_event(
                event_type="SHARD_QUERY",
                source_agent="agent-1",
                payload={
                    "query": "Lars Eriksson",
                    "limit": 5,
                    "correlation_id": correlation_id,
                    "target_agent": "agent-0",
                },
            )
            bus.publish(query_event)

            # Wait for the listener to process the event
            deadline = time.time() + 3.0
            while time.time() < deadline and not search_calls:
                time.sleep(0.05)

            assert search_calls, "agent.memory.search() not called by listener thread"

            # Verify response came back
            response_facts: list[dict] = []
            for event in bus.poll("agent-1"):
                if (
                    event.event_type == "SHARD_RESPONSE"
                    and event.payload.get("correlation_id") == correlation_id
                ):
                    response_facts.extend(event.payload.get("facts", []))

            texts = [f["content"] for f in response_facts]
            assert any("Lars Eriksson" in t for t in texts), (
                f"CognitiveAdapter result missing from cross-shard response. Got: {texts}"
            )
        finally:
            shutdown.set()
            listener_0.join(timeout=2.0)
