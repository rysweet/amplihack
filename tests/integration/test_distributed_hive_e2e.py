"""End-to-end integration test for DHT-based distributed hive sharding (issue #3034).

Validates the full data flow using proper DHT sharding (not replication):
  Agent-0 promotes facts to its local DistributedHiveGraph shard
  -> Agent-0 shard is queryable via SHARD_QUERY/SHARD_RESPONSE protocol
  -> Agent-1 sends SHARD_QUERY to LocalEventBus
  -> Agent-0's ShardQueryListener responds with SHARD_RESPONSE
  -> Agent-1 receives cross-shard facts without replication

Key property: each agent stores only its DHT-assigned shard (O(F/N) per agent),
not all facts replicated to every agent (O(F) per agent).

All tests run locally with no Azure, no LLM, no network.
Uses LocalEventBus as a stand-in for AzureServiceBusEventBus.
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
from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import DistributedHiveGraph
from amplihack.agents.goal_seeking.hive_mind.event_bus import (
    LocalEventBus,
    make_event,
)
from amplihack.agents.goal_seeking.hive_mind.hive_graph import HiveFact

# Load ShardedHiveStore and _shard_query_listener from the deploy entrypoint
_ENTRYPOINT_PATH = (
    Path(__file__).resolve().parents[2] / "deploy" / "azure_hive" / "agent_entrypoint.py"
)
_spec = importlib.util.spec_from_file_location("agent_entrypoint", _ENTRYPOINT_PATH)
assert _spec is not None and _spec.loader is not None
_entrypoint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_entrypoint)
ShardedHiveStore = _entrypoint.ShardedHiveStore
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
    """Two agents each with their own DistributedHiveGraph shard and a shared LocalEventBus."""
    bus = LocalEventBus()

    # Agent-0: owns its DHT shard
    dht_0 = DistributedHiveGraph(hive_id="shard-agent-0", enable_gossip=False)
    dht_0.register_agent("agent-0")
    bus.subscribe("agent-0")
    store_0 = ShardedHiveStore(dht_0, bus, "agent-0")

    # Agent-1: owns its DHT shard
    dht_1 = DistributedHiveGraph(hive_id="shard-agent-1", enable_gossip=False)
    dht_1.register_agent("agent-1")
    bus.subscribe("agent-1")
    store_1 = ShardedHiveStore(dht_1, bus, "agent-1")

    yield {
        "bus": bus,
        "dht_0": dht_0,
        "dht_1": dht_1,
        "store_0": store_0,
        "store_1": store_1,
    }

    bus.close()


# ---------------------------------------------------------------------------
# Phase 1: Core data flow — DHT sharding, not replication
# ---------------------------------------------------------------------------


class TestDHTShardDataFlow:
    """Verify facts stay in their shard and are retrieved via cross-shard query."""

    def test_promote_fact_stores_locally_no_replication(self, two_shard_cluster):
        """promote_fact stores in local shard only — no FACT_PROMOTED event published."""
        store_0 = two_shard_cluster["store_0"]
        dht_0 = two_shard_cluster["dht_0"]
        dht_1 = two_shard_cluster["dht_1"]
        bus = two_shard_cluster["bus"]

        fact = _make_fact("Mitochondria are the powerhouse of the cell", "biology", "agent-0")
        store_0.promote_fact("agent-0", fact)

        # Fact stored in agent-0's shard
        facts_0 = dht_0.query_facts("mitochondria")
        assert any("Mitochondria" in f.content for f in facts_0)

        # NOT in agent-1's shard (no replication)
        facts_1 = dht_1.query_facts("mitochondria")
        assert len(facts_1) == 0

        # No event published to bus (no FACT_PROMOTED broadcast)
        bus_events = bus.poll("agent-1")
        assert bus_events == [], "ShardedHiveStore must not broadcast facts"

    def test_total_storage_equals_facts_promoted(self, two_shard_cluster):
        """With two shards, total stored facts == promoted facts (no replication)."""
        store_0 = two_shard_cluster["store_0"]
        store_1 = two_shard_cluster["store_1"]
        dht_0 = two_shard_cluster["dht_0"]
        dht_1 = two_shard_cluster["dht_1"]

        # Each agent promotes one fact to its own shard
        store_0.promote_fact("agent-0", _make_fact("Alpha fact", "alpha", "agent-0"))
        store_1.promote_fact("agent-1", _make_fact("Beta fact", "beta", "agent-1"))

        total_0 = dht_0.get_stats()["fact_count"]
        total_1 = dht_1.get_stats()["fact_count"]

        # Each shard has its own fact (DHT may route to either, but total = 2)
        assert total_0 + total_1 == 2, (
            f"Expected 2 facts total (no replication), got {total_0 + total_1}"
        )

    def test_cross_shard_query_via_shard_query_protocol(self, two_shard_cluster):
        """agent-1 can retrieve agent-0's facts via SHARD_QUERY/SHARD_RESPONSE."""
        store_0 = two_shard_cluster["store_0"]
        bus = two_shard_cluster["bus"]

        # Agent-0 promotes a fact
        store_0.promote_fact(
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

        # Agent-0 processes the SHARD_QUERY and responds
        for event in bus.poll("agent-0"):
            if event.event_type == "SHARD_QUERY":
                store_0.handle_shard_query(event)

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
        store_1 = two_shard_cluster["store_1"]
        store_0 = two_shard_cluster["store_0"]
        bus = two_shard_cluster["bus"]

        store_0.promote_fact(
            "agent-0", _make_fact("The speed of light is 299792458 m/s", "physics", "agent-0")
        )

        # Set up pending query with threading.Event
        correlation_id = uuid.uuid4().hex
        done = threading.Event()
        results: list[dict] = []
        with store_1._pending_lock:
            store_1._pending[correlation_id] = (done, results)

        # Simulate SHARD_RESPONSE arriving from agent-0
        query_event = make_event(
            event_type="SHARD_QUERY",
            source_agent="agent-1",
            payload={"query": "speed light", "limit": 5, "correlation_id": correlation_id},
        )
        bus.publish(query_event)
        for event in bus.poll("agent-0"):
            if event.event_type == "SHARD_QUERY":
                store_0.handle_shard_query(event)

        # Now agent-1 receives the SHARD_RESPONSE
        for event in bus.poll("agent-1"):
            if event.event_type == "SHARD_RESPONSE":
                store_1.handle_shard_response(event)

        # threading.Event should be set without any sleep
        assert done.is_set(), "Pending query done_event was not set by SHARD_RESPONSE"
        assert any("299792458" in r.get("content", "") for r in results), (
            f"Cross-shard facts not in results. Got: {results}"
        )


# ---------------------------------------------------------------------------
# Phase 2: CognitiveAdapter integration with ShardedHiveStore
# ---------------------------------------------------------------------------


class TestCognitiveAdapterWithShardedHive:
    """Verify CognitiveAdapter.search() works with ShardedHiveStore."""

    def test_search_returns_local_shard_facts(self, two_shard_cluster):
        """Local shard facts are returned by CognitiveAdapter.search()."""
        store_1 = two_shard_cluster["store_1"]

        store_1.promote_fact(
            "agent-1",
            _make_fact("Chloroplasts contain chlorophyll", "biology", "agent-1"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = CognitiveAdapter(
                agent_name="agent-1",
                db_path=Path(tmpdir) / "agent-1",
                hive_store=store_1,
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
        store_1 = two_shard_cluster["store_1"]

        store_1.promote_fact(
            "agent-1",
            _make_fact("Sarah Chen was born on March 15, 1992", "people", "agent-1"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = GoalSeekingAgent(
                agent_name="agent-1",
                storage_path=Path(tmpdir),
                use_hierarchical=True,
                hive_store=store_1,
            )

            agent.observe("When was Sarah Chen born?")
            context = agent.orient()

            facts = context.get("facts", [])
            fact_text = " ".join(str(f) for f in facts)

            assert "Sarah Chen" in fact_text or "March 15" in fact_text or "1992" in fact_text, (
                f"orient() did not surface local shard fact about Sarah Chen. Got facts: {facts}"
            )


# ---------------------------------------------------------------------------
# Phase 4: Background ShardQueryListener handles queries event-driven
# ---------------------------------------------------------------------------


class TestShardQueryListenerThread:
    """Verify the ShardQueryListener background thread handles queries without sleep."""

    def test_listener_responds_to_shard_query(self, two_shard_cluster):
        """ShardQueryListener responds to SHARD_QUERY from peer agents."""
        store_0 = two_shard_cluster["store_0"]
        bus = two_shard_cluster["bus"]

        store_0.promote_fact(
            "agent-0",
            _make_fact("DNA carries genetic information", "biology", "agent-0"),
        )

        shutdown = threading.Event()
        listener = threading.Thread(
            target=_shard_query_listener,
            args=(store_0, "agent-0", bus, shutdown),
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
                f"ShardQueryListener did not respond with correct facts. Got: {texts}"
            )
        finally:
            shutdown.set()
            listener.join(timeout=2.0)

    def test_listener_exits_on_shutdown(self, two_shard_cluster):
        """ShardQueryListener exits cleanly when shutdown_event is set."""
        store_0 = two_shard_cluster["store_0"]
        bus = two_shard_cluster["bus"]

        shutdown = threading.Event()
        listener = threading.Thread(
            target=_shard_query_listener,
            args=(store_0, "agent-0", bus, shutdown),
            daemon=True,
        )
        listener.start()

        shutdown.set()
        listener.join(timeout=2.0)
        assert not listener.is_alive(), "ShardQueryListener did not exit after shutdown"
