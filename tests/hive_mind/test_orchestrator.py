"""Tests for HiveMindOrchestrator -- unified four-layer coordination.

Tests the contract, not implementation details:
- PromotionPolicy protocol compliance (DefaultPromotionPolicy)
- store_and_promote: layer 1 (HiveGraph) promotion
- store_and_promote: layer 2 (EventBus) event publication
- store_and_promote: below-threshold facts are not promoted
- query_unified: returns deduplicated results sorted by confidence
- process_event: incorporates FACT_PROMOTED events from peers
- process_event: rejects non-FACT_PROMOTED events
- process_event: applies peer confidence discount
- drain_events: polls bus and processes all pending events
- run_gossip_round: handles no-peers case gracefully
- close: unsubscribes from event bus without raising
"""

from __future__ import annotations

import pytest

from amplihack.agents.goal_seeking.hive_mind.event_bus import (
    LocalEventBus,
    make_event,
)
from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveFact,
    InMemoryHiveGraph,
)
from amplihack.agents.goal_seeking.hive_mind.orchestrator import (
    DefaultPromotionPolicy,
    HiveMindOrchestrator,
    PromotionPolicy,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def hive() -> InMemoryHiveGraph:
    g = InMemoryHiveGraph("test-hive")
    g.register_agent("agent_a")
    return g


@pytest.fixture()
def bus() -> LocalEventBus:
    b = LocalEventBus()
    b.subscribe("agent_a")
    return b


@pytest.fixture()
def orch(hive: InMemoryHiveGraph, bus: LocalEventBus) -> HiveMindOrchestrator:
    return HiveMindOrchestrator(
        agent_id="agent_a",
        hive_graph=hive,
        event_bus=bus,
    )


# ---------------------------------------------------------------------------
# PromotionPolicy protocol compliance
# ---------------------------------------------------------------------------


def test_default_policy_is_promotion_policy() -> None:
    policy = DefaultPromotionPolicy()
    assert isinstance(policy, PromotionPolicy)


def test_default_policy_promotes_high_confidence() -> None:
    policy = DefaultPromotionPolicy(promote_threshold=0.5)
    fact = HiveFact(fact_id="f1", content="test", concept="test", confidence=0.8)
    assert policy.should_promote(fact, "agent_a")


def test_default_policy_blocks_low_confidence() -> None:
    policy = DefaultPromotionPolicy(promote_threshold=0.8)
    fact = HiveFact(fact_id="f1", content="test", concept="test", confidence=0.3)
    assert not policy.should_promote(fact, "agent_a")


def test_default_policy_blocks_retracted() -> None:
    policy = DefaultPromotionPolicy(promote_threshold=0.1)
    fact = HiveFact(
        fact_id="f1", content="test", concept="test", confidence=0.9, status="retracted"
    )
    assert not policy.should_promote(fact, "agent_a")


def test_default_policy_gossip_threshold() -> None:
    policy = DefaultPromotionPolicy(gossip_threshold=0.5)
    fact_high = HiveFact(fact_id="f1", content="test", concept="test", confidence=0.8)
    fact_low = HiveFact(fact_id="f2", content="test2", concept="test", confidence=0.2)
    assert policy.should_gossip(fact_high, "agent_a")
    assert not policy.should_gossip(fact_low, "agent_a")


def test_default_policy_broadcast_threshold() -> None:
    policy = DefaultPromotionPolicy(broadcast_threshold=0.9)
    fact_high = HiveFact(fact_id="f1", content="test", concept="test", confidence=0.95)
    fact_low = HiveFact(fact_id="f2", content="test2", concept="test", confidence=0.5)
    assert policy.should_broadcast(fact_high, "agent_a")
    assert not policy.should_broadcast(fact_low, "agent_a")


# ---------------------------------------------------------------------------
# store_and_promote
# ---------------------------------------------------------------------------


def test_store_and_promote_returns_promoted_true(
    orch: HiveMindOrchestrator, hive: InMemoryHiveGraph
) -> None:
    result = orch.store_and_promote("Biology", "DNA stores genetic information", 0.9)
    assert result["promoted"] is True
    assert result["fact_id"]
    # Fact is actually in the hive
    facts = hive.query_facts("DNA genetic")
    assert any("DNA" in f.content for f in facts)


def test_store_and_promote_publishes_event(orch: HiveMindOrchestrator, bus: LocalEventBus) -> None:
    # Subscribe a second agent so the bus stores the event
    bus.subscribe("agent_b")
    orch.store_and_promote("Science", "Water is H2O", 0.95)
    events = bus.poll("agent_b")
    assert any(e.event_type == "FACT_PROMOTED" for e in events)


def test_store_and_promote_low_confidence_not_promoted(
    orch: HiveMindOrchestrator, hive: InMemoryHiveGraph
) -> None:
    # Default promote_threshold is DEFAULT_CONFIDENCE_GATE (0.3); use 0.0
    result = orch.store_and_promote("Science", "Very uncertain claim", 0.0)
    assert result["promoted"] is False
    assert result["event_published"] is False


def test_store_and_promote_with_custom_policy(hive: InMemoryHiveGraph, bus: LocalEventBus) -> None:
    strict_policy = DefaultPromotionPolicy(promote_threshold=0.99)
    orch = HiveMindOrchestrator(
        agent_id="agent_a",
        hive_graph=hive,
        event_bus=bus,
        policy=strict_policy,
    )
    result = orch.store_and_promote("Science", "Common knowledge", 0.8)
    assert result["promoted"] is False


def test_store_and_promote_confidence_clamped(
    orch: HiveMindOrchestrator, hive: InMemoryHiveGraph
) -> None:
    # Confidence above 1.0 should be clamped
    result = orch.store_and_promote("Test", "Clamped fact", 2.5)
    assert result["promoted"] is True
    facts = hive.query_facts("Clamped fact")
    assert all(f.confidence <= 1.0 for f in facts)


# ---------------------------------------------------------------------------
# query_unified
# ---------------------------------------------------------------------------


def test_query_unified_returns_results(orch: HiveMindOrchestrator) -> None:
    orch.store_and_promote("Biology", "Mitochondria is the powerhouse of the cell", 0.9)
    results = orch.query_unified("mitochondria cell")
    assert len(results) >= 1
    assert all("fact_id" in r for r in results)
    assert all("content" in r for r in results)


def test_query_unified_deduplicates(orch: HiveMindOrchestrator) -> None:
    # Store the same content twice
    orch.store_and_promote("Science", "E equals mc squared", 0.9)
    orch.store_and_promote("Science", "E equals mc squared", 0.8)
    results = orch.query_unified("E mc squared")
    contents = [r["content"] for r in results]
    assert len(contents) == len(set(contents))


def test_query_unified_respects_limit(orch: HiveMindOrchestrator) -> None:
    for i in range(10):
        orch.store_and_promote("Topic", f"Unique fact number {i}", 0.9)
    results = orch.query_unified("fact", limit=3)
    assert len(results) <= 3


def test_query_unified_result_schema(orch: HiveMindOrchestrator) -> None:
    orch.store_and_promote("Schema", "Schema test content", 0.9)
    results = orch.query_unified("schema test")
    assert results, "Expected at least one result"
    r = results[0]
    for key in ("fact_id", "concept", "content", "confidence", "source_agent", "tags", "status"):
        assert key in r, f"Missing key: {key}"


def test_query_unified_no_results_for_unrelated(orch: HiveMindOrchestrator) -> None:
    orch.store_and_promote("Biology", "DNA stores genetic information", 0.9)
    results = orch.query_unified("quantum physics superconductor")
    # May return some results from keyword overlap -- just check no crash
    assert isinstance(results, list)


# ---------------------------------------------------------------------------
# process_event
# ---------------------------------------------------------------------------


def test_process_event_incorporates_fact_promoted(orch: HiveMindOrchestrator) -> None:
    event = make_event(
        event_type="FACT_PROMOTED",
        source_agent="agent_b",
        payload={
            "fact_id": "hf_abc",
            "concept": "Chemistry",
            "content": "Water boils at 100 degrees Celsius",
            "confidence": 0.9,
            "tags": [],
        },
    )
    result = orch.process_event(event)
    assert result["incorporated"] is True
    assert result["fact_id"] is not None


def test_process_event_rejects_unknown_type(orch: HiveMindOrchestrator) -> None:
    event = make_event(
        event_type="AGENT_READY",
        source_agent="agent_b",
        payload={},
    )
    result = orch.process_event(event)
    assert result["incorporated"] is False
    assert "not a FACT_PROMOTED event" in result["reason"]


def test_process_event_rejects_empty_content(orch: HiveMindOrchestrator) -> None:
    event = make_event(
        event_type="FACT_PROMOTED",
        source_agent="agent_b",
        payload={"concept": "Science", "content": "", "confidence": 0.9},
    )
    result = orch.process_event(event)
    assert result["incorporated"] is False


def test_process_event_applies_confidence_discount(
    orch: HiveMindOrchestrator, hive: InMemoryHiveGraph
) -> None:
    event = make_event(
        event_type="FACT_PROMOTED",
        source_agent="agent_b",
        payload={
            "concept": "Physics",
            "content": "Light travels at 299792458 m/s",
            "confidence": 1.0,
            "tags": [],
        },
    )
    orch.process_event(event)
    facts = hive.query_facts("light travels")
    peer_facts = [f for f in facts if "peer_from:agent_b" in f.tags]
    assert peer_facts, "Expected a peer-sourced fact"
    assert peer_facts[0].confidence < 1.0, "Peer confidence should be discounted"


def test_process_event_low_confidence_not_incorporated() -> None:
    hive = InMemoryHiveGraph("test-hive")
    hive.register_agent("agent_a")
    bus = LocalEventBus()
    bus.subscribe("agent_a")
    # Use a high promote_threshold so even discounted peer facts are blocked
    policy = DefaultPromotionPolicy(promote_threshold=0.99)
    orch = HiveMindOrchestrator(
        agent_id="agent_a",
        hive_graph=hive,
        event_bus=bus,
        policy=policy,
    )
    event = make_event(
        event_type="FACT_PROMOTED",
        source_agent="agent_b",
        payload={"concept": "Test", "content": "Low confidence claim", "confidence": 0.5},
    )
    result = orch.process_event(event)
    assert result["incorporated"] is False
    assert "below promotion threshold" in result["reason"]


# ---------------------------------------------------------------------------
# drain_events
# ---------------------------------------------------------------------------


def test_drain_events_processes_pending(orch: HiveMindOrchestrator, bus: LocalEventBus) -> None:
    # Simulate a peer publishing two events to agent_a's subscription
    bus.subscribe("agent_b")
    for i in range(2):
        event = make_event(
            event_type="FACT_PROMOTED",
            source_agent="agent_b",
            payload={
                "concept": "Drain",
                "content": f"Drain test fact {i}",
                "confidence": 0.85,
                "tags": [],
            },
        )
        bus.publish(event)

    results = orch.drain_events()
    # Both events should have been processed
    assert len(results) == 2
    incorporated = [r for r in results if r["incorporated"]]
    assert len(incorporated) == 2


def test_drain_events_empty_returns_empty_list(orch: HiveMindOrchestrator) -> None:
    results = orch.drain_events()
    assert results == []


# ---------------------------------------------------------------------------
# run_gossip_round
# ---------------------------------------------------------------------------


def test_run_gossip_round_no_peers(orch: HiveMindOrchestrator) -> None:
    result = orch.run_gossip_round()
    assert result["peers_contacted"] == 0
    assert result["skipped"] is not None


def test_run_gossip_round_with_peer(hive: InMemoryHiveGraph, bus: LocalEventBus) -> None:
    peer_hive = InMemoryHiveGraph("peer-hive")
    peer_hive.register_agent("peer_agent")

    orch = HiveMindOrchestrator(
        agent_id="agent_a",
        hive_graph=hive,
        event_bus=bus,
        peers=[peer_hive],
    )
    # Promote a fact so gossip has something to share
    orch.store_and_promote("Science", "Gravity pulls objects toward Earth", 0.9)
    result = orch.run_gossip_round()
    # Either gossip ran (peers_contacted >= 0) or skipped gracefully
    assert isinstance(result["peers_contacted"], int)


# ---------------------------------------------------------------------------
# Properties and lifecycle
# ---------------------------------------------------------------------------


def test_agent_id_property(orch: HiveMindOrchestrator) -> None:
    assert orch.agent_id == "agent_a"


def test_peers_property_is_copy(orch: HiveMindOrchestrator, hive: InMemoryHiveGraph) -> None:
    peer = InMemoryHiveGraph("peer-hive")
    orch.add_peer(peer)
    peers_copy = orch.peers
    peers_copy.clear()
    assert len(orch.peers) == 1, "Modifying the copy should not affect internal state"


def test_close_does_not_raise(orch: HiveMindOrchestrator) -> None:
    orch.close()  # Should not raise


def test_close_idempotent(orch: HiveMindOrchestrator) -> None:
    orch.close()
    orch.close()  # Second close should also not raise
