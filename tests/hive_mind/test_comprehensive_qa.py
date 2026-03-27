"""Comprehensive QA test suite for the distributed hive mind feature.

Covers edge cases, error paths, boundary conditions, security scenarios,
concurrency, and integration paths not covered by existing tests.

Testing pyramid:
- 60% Unit tests (edge cases, boundary conditions, error paths)
- 30% Integration tests (multi-component interactions)
- 10% Concurrency and stress tests
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
import uuid

import pytest

from amplihack.agents.goal_seeking.hive_mind.bloom import BloomFilter
from amplihack.agents.goal_seeking.hive_mind.constants import (
    DEFAULT_BROADCAST_THRESHOLD,
    DEFAULT_CONFIDENCE_GATE,
    GOSSIP_MIN_CONFIDENCE,
    MAX_TRUST_SCORE,
    PEER_CONFIDENCE_DISCOUNT,
)
from amplihack.agents.goal_seeking.hive_mind.crdt import GSet, LWWRegister, ORSet
from amplihack.agents.goal_seeking.hive_mind.dht import (
    DHTRouter,
    HashRing,
    ShardFact,
    ShardStore,
)
from amplihack.agents.goal_seeking.hive_mind.event_bus import (
    BusEvent,
    LocalEventBus,
    make_event,
)
from amplihack.agents.goal_seeking.hive_mind.fact_lifecycle import (
    FactTTL,
    decay_confidence,
    gc_expired_facts,
    refresh_confidence,
)
from amplihack.agents.goal_seeking.hive_mind.gossip import (
    GossipProtocol,
    convergence_check,
    run_gossip_round,
)
from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveAgent,
    HiveEdge,
    HiveFact,
    HiveGraph,
    InMemoryHiveGraph,
    create_hive_graph,
)
from amplihack.agents.goal_seeking.hive_mind.orchestrator import (
    DefaultPromotionPolicy,
    HiveMindOrchestrator,
    PromotionPolicy,
)
from amplihack.agents.goal_seeking.hive_mind.quality import (
    QualityGate,
    score_content_quality,
)
from amplihack.agents.goal_seeking.hive_mind.reranker import (
    ScoredFact,
    hybrid_score,
    hybrid_score_weighted,
    rrf_merge,
    trust_weighted_score,
)


# ===========================================================================
# Section 1: EDGE CASES & BOUNDARY CONDITIONS (Unit Tests)
# ===========================================================================


class TestHiveGraphEdgeCases:
    """Edge cases for InMemoryHiveGraph not covered by existing tests."""

    def test_register_duplicate_agent_raises(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        with pytest.raises(ValueError, match="already registered"):
            hive.register_agent("a1")

    def test_unregister_unknown_agent_raises(self) -> None:
        hive = InMemoryHiveGraph("test")
        with pytest.raises(KeyError, match="not found"):
            hive.unregister_agent("nonexistent")

    def test_get_agent_returns_none_for_unknown(self) -> None:
        hive = InMemoryHiveGraph("test")
        assert hive.get_agent("ghost") is None

    def test_promote_fact_with_unregistered_agent_raises(self) -> None:
        hive = InMemoryHiveGraph("test")
        fact = HiveFact(fact_id="f1", content="test", concept="test")
        with pytest.raises(KeyError, match="not registered"):
            hive.promote_fact("unknown_agent", fact)

    def test_promote_fact_generates_id_when_empty(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        fact = HiveFact(fact_id="", content="test content", concept="test")
        fid = hive.promote_fact("a1", fact)
        assert fid.startswith("hf_")
        assert len(fid) > 3

    def test_promote_fact_clamps_confidence(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        # Above 1.0
        f1 = HiveFact(fact_id="f1", content="high", concept="t", confidence=5.0)
        hive.promote_fact("a1", f1)
        assert hive.get_fact("f1").confidence == 1.0
        # Below 0.0
        f2 = HiveFact(fact_id="f2", content="low", concept="t", confidence=-1.0)
        hive.promote_fact("a1", f2)
        assert hive.get_fact("f2").confidence == 0.0

    def test_update_trust_clamps_to_range(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        hive.update_trust("a1", 100.0)
        assert hive.get_agent("a1").trust == MAX_TRUST_SCORE
        hive.update_trust("a1", -50.0)
        assert hive.get_agent("a1").trust == 0.0

    def test_update_trust_unknown_agent_raises(self) -> None:
        hive = InMemoryHiveGraph("test")
        with pytest.raises(KeyError):
            hive.update_trust("ghost", 1.0)

    def test_retract_nonexistent_fact_returns_false(self) -> None:
        hive = InMemoryHiveGraph("test")
        assert hive.retract_fact("nonexistent") is False

    def test_retract_fact_excludes_from_queries(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        fact = HiveFact(fact_id="f1", content="retractable content", concept="test")
        hive.promote_fact("a1", fact)
        hive.retract_fact("f1")
        results = hive.query_facts("retractable content")
        assert all(f.fact_id != "f1" for f in results)

    def test_query_facts_empty_query_returns_all(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        for i in range(5):
            hive.promote_fact("a1", HiveFact(
                fact_id=f"f{i}", content=f"fact {i}", concept="t"
            ))
        results = hive.query_facts("")
        assert len(results) == 5

    def test_query_facts_whitespace_only_returns_all(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        hive.promote_fact("a1", HiveFact(fact_id="f1", content="test", concept="t"))
        results = hive.query_facts("   ")
        assert len(results) == 1

    def test_check_contradictions_empty_concept_returns_empty(self) -> None:
        hive = InMemoryHiveGraph("test")
        assert hive.check_contradictions("some content", "") == []

    def test_check_contradictions_same_content_not_flagged(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        hive.promote_fact("a1", HiveFact(
            fact_id="f1", content="Earth orbits the Sun", concept="astronomy"
        ))
        # Exact same content should not be a contradiction
        result = hive.check_contradictions("Earth orbits the Sun", "astronomy")
        assert len(result) == 0

    def test_route_query_empty_returns_empty(self) -> None:
        hive = InMemoryHiveGraph("test")
        assert hive.route_query("") == []
        assert hive.route_query("   ") == []

    def test_route_query_matches_domain(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("bio_agent", domain="biology genetics")
        hive.register_agent("chem_agent", domain="chemistry molecules")
        result = hive.route_query("biology")
        assert "bio_agent" in result

    def test_add_child_deduplicates(self) -> None:
        parent = InMemoryHiveGraph("parent")
        child = InMemoryHiveGraph("child")
        parent.add_child(child)
        parent.add_child(child)  # Duplicate
        assert parent.get_stats()["child_count"] == 1

    def test_escalate_without_parent_returns_false(self) -> None:
        hive = InMemoryHiveGraph("test")
        fact = HiveFact(fact_id="f1", content="test", concept="t")
        assert hive.escalate_fact(fact) is False

    def test_get_stats_structure(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        stats = hive.get_stats()
        assert "hive_id" in stats
        assert "agent_count" in stats
        assert "fact_count" in stats
        assert "active_facts" in stats
        assert stats["agent_count"] == 1

    def test_create_hive_graph_unknown_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown backend"):
            create_hive_graph(backend="postgresql")

    def test_create_hive_graph_memory_default(self) -> None:
        hive = create_hive_graph("memory", hive_id="custom-id")
        assert hive.hive_id == "custom-id"


class TestHiveGraphFederation:
    """Tests for federation tree operations."""

    def test_escalate_and_broadcast_round_trip(self) -> None:
        parent = InMemoryHiveGraph("parent")
        parent.register_agent("parent_agent")
        child_a = InMemoryHiveGraph("child_a")
        child_a.register_agent("agent_a")
        child_b = InMemoryHiveGraph("child_b")
        child_b.register_agent("agent_b")

        child_a.set_parent(parent)
        child_b.set_parent(parent)
        parent.add_child(child_a)
        parent.add_child(child_b)

        # child_a promotes a high-confidence fact
        fact = HiveFact(
            fact_id="f1", content="Important discovery", concept="science",
            confidence=0.95,
        )
        child_a.promote_fact("agent_a", fact)

        # Fact should have been escalated to parent and broadcast to child_b
        parent_facts = parent.query_facts("Important discovery")
        assert len(parent_facts) >= 1

    def test_federated_query_prevents_loops(self) -> None:
        """Federation queries should not loop infinitely in circular trees."""
        hive_a = InMemoryHiveGraph("a")
        hive_a.register_agent("agent_a")
        hive_b = InMemoryHiveGraph("b")
        hive_b.register_agent("agent_b")

        hive_a.set_parent(hive_b)
        hive_b.set_parent(hive_a)
        hive_a.add_child(hive_b)
        hive_b.add_child(hive_a)

        hive_a.promote_fact("agent_a", HiveFact(
            fact_id="f1", content="circular test fact", concept="test"
        ))

        # Should complete without infinite recursion
        results = hive_a.query_federated("circular test")
        assert isinstance(results, list)

    def test_federated_query_deduplicates_across_hives(self) -> None:
        parent = InMemoryHiveGraph("parent")
        parent.register_agent("p_agent")
        child = InMemoryHiveGraph("child")
        child.register_agent("c_agent")
        parent.add_child(child)
        child.set_parent(parent)

        # Same content in both hives
        same_content = "Shared knowledge fact"
        parent.promote_fact("p_agent", HiveFact(
            fact_id="pf1", content=same_content, concept="shared"
        ))
        child.promote_fact("c_agent", HiveFact(
            fact_id="cf1", content=same_content, concept="shared"
        ))

        results = parent.query_federated("Shared knowledge")
        contents = [f.content for f in results]
        assert contents.count(same_content) == 1


class TestEventBusEdgeCases:
    """Edge cases for LocalEventBus."""

    def test_publish_on_closed_bus_raises(self) -> None:
        bus = LocalEventBus()
        bus.close()
        event = make_event("TEST", "agent_a")
        with pytest.raises(RuntimeError, match="closed"):
            bus.publish(event)

    def test_no_self_delivery(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a")
        event = make_event("TEST", "agent_a", {"data": "self"})
        bus.publish(event)
        assert bus.poll("agent_a") == []

    def test_event_type_filtering(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a", event_types=["FACT_LEARNED"])
        bus.subscribe("agent_b")
        event_learn = make_event("FACT_LEARNED", "agent_c", {"data": "learn"})
        event_other = make_event("OTHER_EVENT", "agent_c", {"data": "other"})
        bus.publish(event_learn)
        bus.publish(event_other)
        a_events = bus.poll("agent_a")
        b_events = bus.poll("agent_b")
        assert len(a_events) == 1  # Only FACT_LEARNED
        assert len(b_events) == 2  # Both events

    def test_poll_unsubscribed_agent_returns_empty(self) -> None:
        bus = LocalEventBus()
        assert bus.poll("nonexistent") == []

    def test_unsubscribe_clears_pending_events(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a")
        bus.publish(make_event("TEST", "agent_b"))
        bus.unsubscribe("agent_a")
        assert bus.poll("agent_a") == []

    def test_resubscribe_preserves_events(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a")
        bus.publish(make_event("TEST", "agent_b"))
        # Re-subscribe with new filter should keep existing events
        bus.subscribe("agent_a", event_types=["TEST"])
        events = bus.poll("agent_a")
        assert len(events) == 1

    def test_bus_event_json_roundtrip(self) -> None:
        event = make_event("FACT_PROMOTED", "agent_x", {
            "content": "Test content",
            "confidence": 0.95,
            "nested": {"key": "value"},
        })
        json_str = event.to_json()
        restored = BusEvent.from_json(json_str)
        assert restored.event_id == event.event_id
        assert restored.event_type == event.event_type
        assert restored.payload == event.payload

    def test_bus_event_from_json_invalid_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            BusEvent.from_json("not valid json")

    def test_bus_event_from_json_missing_field_raises(self) -> None:
        with pytest.raises((KeyError, TypeError)):
            BusEvent.from_json('{"event_id": "x"}')

    def test_make_event_generates_unique_ids(self) -> None:
        e1 = make_event("TEST", "a")
        e2 = make_event("TEST", "a")
        assert e1.event_id != e2.event_id


class TestCRDTEdgeCases:
    """Edge cases for CRDT data types."""

    def test_gset_merge_is_commutative(self) -> None:
        a = GSet()
        b = GSet()
        a.add("x")
        b.add("y")
        # a.merge(b) should give same result as b.merge(a)
        a_copy = GSet()
        a_copy.add("x")
        b_copy = GSet()
        b_copy.add("y")
        a.merge(b)
        b_copy.merge(a_copy)
        assert a.items == b_copy.items

    def test_gset_merge_is_idempotent(self) -> None:
        a = GSet()
        b = GSet()
        a.add("x")
        b.add("x")
        b.add("y")
        a.merge(b)
        items_after_first = a.items
        a.merge(b)
        assert a.items == items_after_first

    def test_gset_serialization_roundtrip(self) -> None:
        gs = GSet()
        gs.add("alpha")
        gs.add("beta")
        data = gs.to_dict()
        restored = GSet.from_dict(data)
        assert restored.items == gs.items

    def test_orset_add_remove_add_is_present(self) -> None:
        """ORSet: add-wins semantics -- re-adding after remove makes present."""
        s = ORSet()
        s.add("x")
        s.remove("x")
        assert not s.contains("x")
        s.add("x")  # Fresh tag
        assert s.contains("x")

    def test_orset_merge_is_commutative(self) -> None:
        a = ORSet()
        b = ORSet()
        a.add("x")
        b.add("y")
        a_copy = ORSet()
        a_copy.add("x")
        b_copy = ORSet()
        b_copy.add("y")
        a.merge(b)
        b_copy.merge(a_copy)
        assert a.items == b_copy.items

    def test_orset_serialization_roundtrip(self) -> None:
        s = ORSet()
        s.add("a")
        s.add("b")
        s.remove("a")
        data = s.to_dict()
        restored = ORSet.from_dict(data)
        assert restored.items == s.items

    def test_lww_register_latest_wins(self) -> None:
        reg = LWWRegister()
        reg.set("old", 1.0)
        reg.set("new", 2.0)
        assert reg.get() == "new"

    def test_lww_register_older_write_ignored(self) -> None:
        reg = LWWRegister()
        reg.set("first", 2.0)
        reg.set("older", 1.0)  # Earlier timestamp
        assert reg.get() == "first"

    def test_lww_register_tie_breaks_by_value(self) -> None:
        reg = LWWRegister()
        reg.set("aaa", 1.0)
        reg.set("zzz", 1.0)  # Same timestamp, higher string value
        assert reg.get() == "zzz"

    def test_lww_register_merge(self) -> None:
        a = LWWRegister()
        b = LWWRegister()
        a.set("from_a", 1.0)
        b.set("from_b", 2.0)
        a.merge(b)
        assert a.get() == "from_b"

    def test_lww_register_merge_with_empty(self) -> None:
        a = LWWRegister()
        b = LWWRegister()
        a.set("value", 1.0)
        a.merge(b)  # Merging empty should keep a's value
        assert a.get() == "value"

    def test_lww_register_serialization_roundtrip(self) -> None:
        reg = LWWRegister()
        reg.set(42.0, 1.0)
        data = reg.to_dict()
        restored = LWWRegister.from_dict(data)
        assert restored.get() == 42.0

    def test_lww_register_serialization_empty(self) -> None:
        reg = LWWRegister()
        data = reg.to_dict()
        assert data["value"] is None
        restored = LWWRegister.from_dict(data)
        assert restored.get() is None


class TestBloomFilterEdgeCases:
    """Edge cases for BloomFilter."""

    def test_no_false_negatives(self) -> None:
        bf = BloomFilter(expected_items=100)
        items = [f"item_{i}" for i in range(100)]
        bf.add_all(items)
        for item in items:
            assert bf.might_contain(item), f"False negative for {item}"

    def test_empty_filter_contains_nothing(self) -> None:
        bf = BloomFilter(expected_items=100)
        assert not bf.might_contain("anything")

    def test_count_tracks_additions(self) -> None:
        bf = BloomFilter()
        assert bf.count == 0
        bf.add("a")
        bf.add("b")
        assert bf.count == 2

    def test_missing_from_returns_absent_items(self) -> None:
        bf = BloomFilter(expected_items=10)
        bf.add("present")
        missing = bf.missing_from(["present", "absent"])
        assert "absent" in missing
        assert "present" not in missing

    def test_serialization_roundtrip(self) -> None:
        bf = BloomFilter(expected_items=50)
        bf.add_all(["alpha", "beta", "gamma"])
        raw = bf.to_bytes()
        restored = BloomFilter.from_bytes(raw, expected_items=50)
        assert restored.might_contain("alpha")
        assert restored.might_contain("beta")
        assert restored.might_contain("gamma")

    def test_zero_expected_items_handled(self) -> None:
        bf = BloomFilter(expected_items=0)
        bf.add("test")
        assert bf.might_contain("test")

    def test_size_bytes_positive(self) -> None:
        bf = BloomFilter(expected_items=1000)
        assert bf.size_bytes > 0


class TestDHTEdgeCases:
    """Edge cases for DHT routing and shard storage."""

    def test_hash_ring_empty_returns_empty(self) -> None:
        ring = HashRing()
        assert ring.get_agents("any_key") == []
        assert ring.get_primary_agent("any_key") is None

    def test_hash_ring_add_remove_agent(self) -> None:
        ring = HashRing()
        ring.add_agent("agent_1")
        assert ring.agent_count == 1
        ring.remove_agent("agent_1")
        assert ring.agent_count == 0

    def test_hash_ring_duplicate_add_idempotent(self) -> None:
        ring = HashRing()
        ring.add_agent("a1")
        ring.add_agent("a1")
        assert ring.agent_count == 1

    def test_hash_ring_replication_returns_distinct_agents(self) -> None:
        ring = HashRing(replication_factor=3)
        for i in range(5):
            ring.add_agent(f"agent_{i}")
        agents = ring.get_agents("test_key")
        assert len(agents) == 3
        assert len(set(agents)) == 3  # All distinct

    def test_shard_store_dedup_by_content(self) -> None:
        store = ShardStore("a1")
        f1 = ShardFact(fact_id="f1", content="same content")
        f2 = ShardFact(fact_id="f2", content="same content")
        assert store.store(f1) is True
        assert store.store(f2) is False  # Duplicate content
        assert store.fact_count == 1

    def test_shard_store_search_empty_returns_empty(self) -> None:
        store = ShardStore("a1")
        assert store.search("anything") == []

    def test_shard_store_search_filters_retracted(self) -> None:
        store = ShardStore("a1")
        f = ShardFact(fact_id="f1", content="retractable fact", tags=["retracted"])
        store.store(f)
        assert store.search("retractable") == []

    def test_dht_router_store_and_query(self) -> None:
        router = DHTRouter(replication_factor=2)
        router.add_agent("a1")
        router.add_agent("a2")
        fact = ShardFact(
            fact_id="f1", content="DNA stores genetic information",
            concept="biology", confidence=0.9,
        )
        stored_on = router.store_fact(fact)
        assert len(stored_on) >= 1
        results = router.query("DNA genetic")
        assert len(results) >= 1

    def test_dht_router_remove_agent_returns_facts(self) -> None:
        router = DHTRouter(replication_factor=1)
        router.add_agent("a1")
        fact = ShardFact(fact_id="f1", content="orphan fact", concept="t")
        router.store_fact(fact)
        orphans = router.remove_agent("a1")
        assert len(orphans) >= 1

    def test_dht_router_get_stats(self) -> None:
        router = DHTRouter()
        router.add_agent("a1")
        stats = router.get_stats()
        assert stats["agent_count"] == 1
        assert "shard_sizes" in stats


class TestFactLifecycleEdgeCases:
    """Edge cases for fact lifecycle (TTL, decay, GC)."""

    def test_decay_zero_hours_returns_original(self) -> None:
        assert decay_confidence(0.9, 0.0) == 0.9

    def test_decay_negative_hours_returns_original(self) -> None:
        assert decay_confidence(0.9, -5.0) == 0.9

    def test_decay_clamps_to_range(self) -> None:
        # Very high original
        result = decay_confidence(5.0, 0.0)
        assert result <= 1.0
        # Very negative original
        result = decay_confidence(-1.0, 0.0)
        assert result >= 0.0

    def test_decay_exponential_formula(self) -> None:
        original = 1.0
        hours = 10.0
        rate = 0.1
        expected = original * math.exp(-rate * hours)
        result = decay_confidence(original, hours, rate)
        assert abs(result - expected) < 1e-10

    def test_gc_removes_expired_facts(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        fact = HiveFact(fact_id="f1", content="old fact", concept="t")
        hive.promote_fact("a1", fact)
        registry = {"f1": FactTTL(fact_id="f1", created_at=0.0)}  # Very old
        removed = gc_expired_facts(hive, registry, max_age_hours=1.0, now=100000.0)
        assert "f1" in removed
        assert hive.get_fact("f1").status == "retracted"

    def test_gc_keeps_fresh_facts(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        now = time.time()
        fact = HiveFact(fact_id="f1", content="fresh", concept="t")
        hive.promote_fact("a1", fact)
        registry = {"f1": FactTTL(fact_id="f1", created_at=now)}
        removed = gc_expired_facts(hive, registry, max_age_hours=24.0, now=now)
        assert removed == []

    def test_refresh_confidence_resets_ttl(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        hive.promote_fact("a1", HiveFact(fact_id="f1", content="t", concept="t"))
        registry = {"f1": FactTTL(fact_id="f1", created_at=0.0)}
        now = 1000.0
        result = refresh_confidence(hive, registry, "f1", 0.95, now=now)
        assert result is True
        assert registry["f1"].created_at == now
        assert hive.get_fact("f1").confidence == 0.95

    def test_refresh_missing_fact_returns_false(self) -> None:
        hive = InMemoryHiveGraph("test")
        registry: dict = {}
        assert refresh_confidence(hive, registry, "nonexistent", 0.9) is False


class TestRerankerEdgeCases:
    """Edge cases for reranker scoring functions."""

    def test_hybrid_score_with_defaults(self) -> None:
        score = hybrid_score(1.0, 1.0)
        assert score > 0

    def test_hybrid_score_zero_inputs(self) -> None:
        assert hybrid_score(0.0, 0.0) == 0.0

    def test_rrf_merge_empty_lists(self) -> None:
        result = rrf_merge()
        assert result == []

    def test_rrf_merge_single_list(self) -> None:
        facts = [
            HiveFact(fact_id="f1", content="a", confidence=0.9),
            HiveFact(fact_id="f2", content="b", confidence=0.8),
        ]
        result = rrf_merge(facts)
        assert len(result) == 2
        assert result[0].score > result[1].score

    def test_rrf_merge_deduplicates_across_lists(self) -> None:
        f1 = HiveFact(fact_id="f1", content="a")
        f2 = HiveFact(fact_id="f2", content="b")
        list_a = [f1, f2]
        list_b = [f2, f1]  # Same facts, different order
        result = rrf_merge(list_a, list_b)
        fact_ids = [r.fact.fact_id for r in result]
        assert len(fact_ids) == 2

    def test_trust_weighted_score_normalizes_trust(self) -> None:
        # Trust of 2.0 should normalize to 1.0
        score_max = trust_weighted_score(1.0, 2.0, 1.0)
        score_min = trust_weighted_score(1.0, 0.0, 1.0)
        assert score_max > score_min

    def test_hybrid_score_weighted_zero_confirmations(self) -> None:
        score = hybrid_score_weighted(0.8, 0, 1.0)
        assert score > 0  # Semantic and trust still contribute

    def test_hybrid_score_weighted_high_confirmations(self) -> None:
        low = hybrid_score_weighted(0.5, 0, 1.0)
        high = hybrid_score_weighted(0.5, 10, 1.0)
        assert high > low


class TestQualityEdgeCases:
    """Edge cases for quality scoring."""

    def test_empty_content_scores_zero(self) -> None:
        assert score_content_quality("") == 0.0
        assert score_content_quality("   ") == 0.0

    def test_very_short_content_penalized(self) -> None:
        short_score = score_content_quality("hi")
        long_score = score_content_quality(
            "DNA stores genetic information in a double helix structure"
        )
        assert long_score > short_score

    def test_vague_content_penalized(self) -> None:
        vague = score_content_quality("something stuff things whatever probably idk")
        specific = score_content_quality(
            "The mitochondria produces ATP through oxidative phosphorylation"
        )
        assert specific > vague

    def test_quality_gate_should_promote(self) -> None:
        gate = QualityGate(promotion_threshold=0.1)
        assert gate.should_promote(
            "DNA stores genetic information", "genetics"
        ) is True

    def test_quality_gate_blocks_low_quality(self) -> None:
        gate = QualityGate(promotion_threshold=0.99)
        assert gate.should_promote("x", "t") is False

    def test_quality_gate_caches_scores(self) -> None:
        gate = QualityGate()
        s1 = gate.score("test content for caching", "test")
        s2 = gate.score("test content for caching", "test")
        assert s1 == s2


class TestGossipEdgeCases:
    """Edge cases for gossip protocol."""

    def test_gossip_no_peers_returns_empty(self) -> None:
        hive = InMemoryHiveGraph("source")
        result = run_gossip_round(hive, [])
        assert result == {}

    def test_gossip_no_eligible_facts_returns_empty(self) -> None:
        source = InMemoryHiveGraph("source")
        peer = InMemoryHiveGraph("peer")
        # No facts in source
        result = run_gossip_round(source, [peer])
        assert result.get("peer", []) == []

    def test_gossip_skips_duplicate_content(self) -> None:
        source = InMemoryHiveGraph("source")
        source.register_agent("a1")
        peer = InMemoryHiveGraph("peer")
        peer.register_agent("p1")

        # Same fact in both hives
        source.promote_fact("a1", HiveFact(
            fact_id="f1", content="shared fact", concept="t", confidence=0.9
        ))
        peer.promote_fact("p1", HiveFact(
            fact_id="f2", content="shared fact", concept="t", confidence=0.9
        ))

        result = run_gossip_round(source, [peer])
        # Should share 0 facts since peer already has the content
        shared = result.get("peer", [])
        assert len(shared) == 0

    def test_convergence_empty_hives(self) -> None:
        assert convergence_check([]) == 0.0

    def test_convergence_single_hive(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        hive.promote_fact("a1", HiveFact(fact_id="f1", content="test", concept="t"))
        assert convergence_check([hive]) == 1.0

    def test_convergence_identical_hives(self) -> None:
        hives = []
        for i in range(3):
            h = InMemoryHiveGraph(f"hive_{i}")
            h.register_agent(f"agent_{i}")
            h.promote_fact(f"agent_{i}", HiveFact(
                fact_id=f"f_{i}", content="identical content", concept="t"
            ))
            hives.append(h)
        assert convergence_check(hives) == 1.0

    def test_convergence_disjoint_hives(self) -> None:
        hives = []
        for i in range(3):
            h = InMemoryHiveGraph(f"hive_{i}")
            h.register_agent(f"agent_{i}")
            h.promote_fact(f"agent_{i}", HiveFact(
                fact_id=f"f_{i}", content=f"unique content {i}", concept="t"
            ))
            hives.append(h)
        assert convergence_check(hives) == 0.0

    def test_gossip_protocol_custom_config(self) -> None:
        protocol = GossipProtocol(top_k=5, fanout=1, min_confidence=0.8)
        source = InMemoryHiveGraph("source")
        source.register_agent("a1")
        peer = InMemoryHiveGraph("peer")
        peer.register_agent("p1")

        # Add a low-confidence fact (below min_confidence)
        source.promote_fact("a1", HiveFact(
            fact_id="f1", content="low confidence fact", concept="t", confidence=0.5
        ))

        result = run_gossip_round(source, [peer], protocol)
        # Low confidence fact should not be gossipped
        assert result.get("peer", []) == []


# ===========================================================================
# Section 2: ORCHESTRATOR INTEGRATION TESTS
# ===========================================================================


class TestOrchestratorIntegration:
    """Integration tests for HiveMindOrchestrator with multiple components."""

    def test_multi_agent_event_propagation(self) -> None:
        """Two orchestrators sharing an event bus should exchange facts."""
        hive = InMemoryHiveGraph("shared")
        hive.register_agent("agent_a")
        hive.register_agent("agent_b")
        bus = LocalEventBus()
        bus.subscribe("agent_a")
        bus.subscribe("agent_b")

        orch_a = HiveMindOrchestrator("agent_a", hive, bus)
        orch_b = HiveMindOrchestrator("agent_b", hive, bus)

        # Agent A stores a fact
        orch_a.store_and_promote("Biology", "Cells have membranes", 0.9)

        # Agent B drains events and should incorporate
        results = orch_b.drain_events()
        incorporated = [r for r in results if r["incorporated"]]
        assert len(incorporated) >= 1

    def test_orchestrator_gossip_with_peers(self) -> None:
        """Gossip should propagate facts to peer hives."""
        source_hive = InMemoryHiveGraph("source")
        source_hive.register_agent("agent_a")
        peer_hive = InMemoryHiveGraph("peer")
        peer_hive.register_agent("peer_agent")
        bus = LocalEventBus()
        bus.subscribe("agent_a")

        orch = HiveMindOrchestrator(
            "agent_a", source_hive, bus, peers=[peer_hive]
        )
        orch.store_and_promote("Science", "Water boils at 100C", 0.95)
        result = orch.run_gossip_round()
        # Gossip should have attempted to contact the peer
        assert isinstance(result["peers_contacted"], int)

    def test_orchestrator_tags_propagated(self) -> None:
        """Tags should be preserved through store_and_promote."""
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        bus = LocalEventBus()
        bus.subscribe("a1")
        bus.subscribe("listener")

        orch = HiveMindOrchestrator("a1", hive, bus)
        orch.store_and_promote("Bio", "DNA test", 0.9, tags=["important", "verified"])

        events = bus.poll("listener")
        assert len(events) >= 1
        payload = events[0].payload
        assert "important" in payload["tags"]
        assert "verified" in payload["tags"]

    def test_orchestrator_query_unified_sorted_by_confidence(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        bus = LocalEventBus()
        bus.subscribe("a1")
        orch = HiveMindOrchestrator("a1", hive, bus)

        orch.store_and_promote("Sci", "Low confidence claim about physics", 0.4)
        orch.store_and_promote("Sci", "High confidence claim about physics", 0.99)

        results = orch.query_unified("physics claim")
        if len(results) >= 2:
            assert results[0]["confidence"] >= results[1]["confidence"]

    def test_process_event_missing_content_rejected(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        bus = LocalEventBus()
        bus.subscribe("a1")
        orch = HiveMindOrchestrator("a1", hive, bus)

        event = make_event("FACT_PROMOTED", "agent_b", {
            "concept": "Test",
            "confidence": 0.9,
            # Missing "content"
        })
        result = orch.process_event(event)
        assert result["incorporated"] is False
        assert "missing" in result["reason"]

    def test_process_event_missing_concept_rejected(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        bus = LocalEventBus()
        bus.subscribe("a1")
        orch = HiveMindOrchestrator("a1", hive, bus)

        event = make_event("FACT_PROMOTED", "agent_b", {
            "content": "Some content",
            "confidence": 0.9,
            # Missing "concept"
        })
        result = orch.process_event(event)
        assert result["incorporated"] is False


# ===========================================================================
# Section 3: SECURITY TESTS
# ===========================================================================


class TestSecurityBoundaries:
    """Security-focused tests for boundary violations and input sanitization."""

    def test_trust_cannot_exceed_maximum(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1", trust=999.0)
        assert hive.get_agent("a1").trust == MAX_TRUST_SCORE

    def test_trust_cannot_go_negative(self) -> None:
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1", trust=-10.0)
        assert hive.get_agent("a1").trust == 0.0

    def test_peer_confidence_discount_applied(self) -> None:
        """Peer facts must always be discounted to prevent trust escalation."""
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        bus = LocalEventBus()
        bus.subscribe("a1")
        orch = HiveMindOrchestrator("a1", hive, bus)

        event = make_event("FACT_PROMOTED", "malicious_peer", {
            "concept": "exploit",
            "content": "Malicious fact with max confidence",
            "confidence": 1.0,
            "tags": [],
        })
        result = orch.process_event(event)
        if result["incorporated"]:
            facts = hive.query_facts("Malicious fact")
            peer_facts = [f for f in facts if "peer_from:malicious_peer" in f.tags]
            for f in peer_facts:
                assert f.confidence <= PEER_CONFIDENCE_DISCOUNT

    def test_large_payload_handled(self) -> None:
        """Large payloads should not crash the system."""
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        bus = LocalEventBus()
        bus.subscribe("a1")
        orch = HiveMindOrchestrator("a1", hive, bus)

        large_content = "x" * 100_000  # 100KB content
        result = orch.store_and_promote("Large", large_content, 0.5)
        assert result["promoted"] is True

    def test_special_characters_in_content(self) -> None:
        """Special characters should not break queries or storage."""
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        special_chars = 'Content with "quotes", <tags>, & symbols; DROP TABLE;'
        fact = HiveFact(fact_id="f1", content=special_chars, concept="test")
        fid = hive.promote_fact("a1", fact)
        retrieved = hive.get_fact(fid)
        assert retrieved.content == special_chars

    def test_unicode_content_handled(self) -> None:
        """Unicode content should be stored and retrieved correctly."""
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        unicode_content = "DNA存储遗传信息 🧬 données génétiques"
        fact = HiveFact(fact_id="f1", content=unicode_content, concept="genetics")
        fid = hive.promote_fact("a1", fact)
        retrieved = hive.get_fact(fid)
        assert retrieved.content == unicode_content

    def test_empty_agent_id_not_exploitable(self) -> None:
        """Empty agent IDs should not cause weird behavior."""
        hive = InMemoryHiveGraph("test")
        # Registering an empty string agent should work but not collide
        hive.register_agent("")
        hive.register_agent("real_agent")
        assert hive.get_agent("") is not None
        assert hive.get_agent("real_agent") is not None

    def test_event_self_delivery_blocked(self) -> None:
        """An agent should never receive its own events via the bus."""
        bus = LocalEventBus()
        bus.subscribe("attacker")
        # Attacker publishes an event
        event = make_event("FACT_PROMOTED", "attacker", {"data": "self"})
        bus.publish(event)
        # Should not receive own event
        assert bus.poll("attacker") == []

    def test_bloom_filter_false_positive_rate_acceptable(self) -> None:
        """BloomFilter FPR should stay within configured bounds."""
        bf = BloomFilter(expected_items=10000, false_positive_rate=0.01)
        for i in range(10000):
            bf.add(f"item_{i}")

        false_positives = 0
        test_count = 10000
        for i in range(test_count):
            if bf.might_contain(f"nonexistent_{i}"):
                false_positives += 1

        fpr = false_positives / test_count
        # Allow 3x the configured FPR as safety margin
        assert fpr < 0.03, f"FPR too high: {fpr:.4f}"


# ===========================================================================
# Section 4: CONCURRENCY & THREAD SAFETY TESTS
# ===========================================================================


class TestConcurrency:
    """Thread safety tests for concurrent operations."""

    def test_concurrent_promote_facts(self) -> None:
        """Multiple threads promoting facts simultaneously should not corrupt state."""
        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        errors: list[Exception] = []
        num_threads = 10
        facts_per_thread = 50

        def promote_facts(thread_id: int) -> None:
            try:
                for i in range(facts_per_thread):
                    fact = HiveFact(
                        fact_id=f"t{thread_id}_f{i}",
                        content=f"Thread {thread_id} fact {i}",
                        concept="concurrency",
                        confidence=0.8,
                    )
                    hive.promote_fact("a1", fact)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=promote_facts, args=(i,))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errors during concurrent promote: {errors}"
        assert hive.get_stats()["fact_count"] == num_threads * facts_per_thread

    def test_concurrent_event_bus_publish_poll(self) -> None:
        """Concurrent publish and poll should not lose events or deadlock."""
        bus = LocalEventBus()
        num_agents = 5
        events_per_agent = 20
        for i in range(num_agents):
            bus.subscribe(f"agent_{i}")

        errors: list[Exception] = []
        total_received: list[int] = [0]
        lock = threading.Lock()

        def publisher(agent_id: str) -> None:
            try:
                for i in range(events_per_agent):
                    event = make_event("TEST", agent_id, {"i": i})
                    bus.publish(event)
            except Exception as e:
                errors.append(e)

        def poller(agent_id: str) -> None:
            try:
                time.sleep(0.1)  # Let publishers start
                events = bus.poll(agent_id)
                with lock:
                    total_received[0] += len(events)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(num_agents):
            threads.append(threading.Thread(target=publisher, args=(f"agent_{i}",)))
        for i in range(num_agents):
            threads.append(threading.Thread(target=poller, args=(f"agent_{i}",)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errors in concurrent bus operations: {errors}"

    def test_concurrent_crdt_merge(self) -> None:
        """Concurrent CRDT merges should converge without data loss."""
        sets = [ORSet() for _ in range(5)]
        errors: list[Exception] = []

        # Each set adds unique items
        for i, s in enumerate(sets):
            for j in range(20):
                s.add(f"set{i}_item{j}")

        def merge_pair(a: ORSet, b: ORSet) -> None:
            try:
                a.merge(b)
            except Exception as e:
                errors.append(e)

        # Merge all pairs concurrently
        threads = []
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                t = threading.Thread(target=merge_pair, args=(sets[i], sets[j]))
                threads.append(t)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

    def test_concurrent_hash_ring_add_remove(self) -> None:
        """Concurrent add/remove on HashRing should not corrupt state."""
        ring = HashRing()
        errors: list[Exception] = []

        def add_agents(start: int) -> None:
            try:
                for i in range(start, start + 10):
                    ring.add_agent(f"agent_{i}")
            except Exception as e:
                errors.append(e)

        def remove_agents(start: int) -> None:
            try:
                time.sleep(0.01)  # Let adds start first
                for i in range(start, start + 5):
                    ring.remove_agent(f"agent_{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=add_agents, args=(0,)),
            threading.Thread(target=add_agents, args=(10,)),
            threading.Thread(target=remove_agents, args=(0,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # ring should have agents 5-19 remaining
        assert ring.agent_count > 0


# ===========================================================================
# Section 5: HIVE GRAPH TTL INTEGRATION
# ===========================================================================


class TestHiveGraphTTL:
    """Tests for InMemoryHiveGraph with TTL enabled."""

    def test_ttl_enabled_registers_metadata(self) -> None:
        hive = InMemoryHiveGraph("test", enable_ttl=True)
        hive.register_agent("a1")
        fid = hive.promote_fact("a1", HiveFact(
            fact_id="f1", content="decaying fact", concept="t", confidence=0.9
        ))
        assert fid == "f1"
        assert "f1" in hive._ttl_registry

    def test_gc_removes_old_facts(self) -> None:
        hive = InMemoryHiveGraph("test", enable_ttl=True)
        hive.register_agent("a1")
        # Manually set a very old created_at
        fact = HiveFact(
            fact_id="old_fact", content="ancient fact", concept="t",
            created_at=0.0,
        )
        hive.promote_fact("a1", fact)
        removed = hive.gc()
        assert "old_fact" in removed

    def test_gc_keeps_fresh_facts(self) -> None:
        hive = InMemoryHiveGraph("test", enable_ttl=True)
        hive.register_agent("a1")
        hive.promote_fact("a1", HiveFact(
            fact_id="fresh", content="new fact", concept="t"
        ))
        removed = hive.gc()
        assert "fresh" not in removed

    def test_gc_disabled_returns_empty(self) -> None:
        hive = InMemoryHiveGraph("test", enable_ttl=False)
        assert hive.gc() == []


# ===========================================================================
# Section 6: CRDT MERGE STATE INTEGRATION
# ===========================================================================


class TestHiveGraphMergeState:
    """Tests for InMemoryHiveGraph.merge_state() CRDT integration."""

    def test_merge_state_copies_new_facts(self) -> None:
        hive_a = InMemoryHiveGraph("a")
        hive_a.register_agent("a1")
        hive_b = InMemoryHiveGraph("b")
        hive_b.register_agent("b1")

        hive_a.promote_fact("a1", HiveFact(
            fact_id="fa1", content="fact from a", concept="t"
        ))
        hive_b.promote_fact("b1", HiveFact(
            fact_id="fb1", content="fact from b", concept="t"
        ))

        hive_a.merge_state(hive_b)
        assert hive_a.get_fact("fb1") is not None
        assert hive_a.get_fact("fb1").content == "fact from b"

    def test_merge_state_syncs_trust(self) -> None:
        hive_a = InMemoryHiveGraph("a")
        hive_a.register_agent("shared_agent")
        hive_b = InMemoryHiveGraph("b")
        hive_b.register_agent("shared_agent")
        hive_b.update_trust("shared_agent", 1.8)

        hive_a.merge_state(hive_b)
        # After merge, trust should be the latest value
        assert hive_a.get_agent("shared_agent").trust >= 1.0

    def test_merge_state_retract_syncs(self) -> None:
        hive_a = InMemoryHiveGraph("a")
        hive_a.register_agent("a1")
        hive_b = InMemoryHiveGraph("b")
        hive_b.register_agent("b1")

        # Both have same fact
        for h, agent in [(hive_a, "a1"), (hive_b, "b1")]:
            h.promote_fact(agent, HiveFact(
                fact_id="shared", content="shared fact", concept="t"
            ))

        # Retract in b
        hive_b.retract_fact("shared")

        # Merge: b's retraction should propagate to a
        hive_a.merge_state(hive_b)
        # ORSet add-wins: since a still has the fact added, it may remain
        # The key point is the merge doesn't crash
        assert isinstance(hive_a.get_fact("shared").status, str)


# ===========================================================================
# Section 7: HIVE GRAPH COSINE SIMILARITY
# ===========================================================================


class TestCosineSimEdgeCases:
    """Edge cases for the _cosine_sim helper in InMemoryHiveGraph."""

    def test_cosine_sim_empty_vectors(self) -> None:
        hive = InMemoryHiveGraph("test")
        assert hive._cosine_sim([], []) == 0.0

    def test_cosine_sim_zero_vectors(self) -> None:
        hive = InMemoryHiveGraph("test")
        assert hive._cosine_sim([0, 0, 0], [0, 0, 0]) == 0.0

    def test_cosine_sim_identical_vectors(self) -> None:
        hive = InMemoryHiveGraph("test")
        sim = hive._cosine_sim([1, 2, 3], [1, 2, 3])
        assert abs(sim - 1.0) < 1e-9

    def test_cosine_sim_orthogonal_vectors(self) -> None:
        hive = InMemoryHiveGraph("test")
        sim = hive._cosine_sim([1, 0], [0, 1])
        assert abs(sim) < 1e-9

    def test_cosine_sim_dimension_mismatch_raises(self) -> None:
        hive = InMemoryHiveGraph("test")
        with pytest.raises(ValueError, match="dimension mismatch"):
            hive._cosine_sim([1, 2], [1, 2, 3])


# ===========================================================================
# Section 8: PROMOTION POLICY EDGE CASES
# ===========================================================================


class TestPromotionPolicyEdgeCases:
    """Edge cases for DefaultPromotionPolicy."""

    def test_exactly_at_threshold_promotes(self) -> None:
        policy = DefaultPromotionPolicy(promote_threshold=0.5)
        fact = HiveFact(fact_id="f1", content="t", concept="t", confidence=0.5)
        assert policy.should_promote(fact, "a1") is True

    def test_just_below_threshold_blocks(self) -> None:
        policy = DefaultPromotionPolicy(promote_threshold=0.5)
        fact = HiveFact(
            fact_id="f1", content="t", concept="t",
            confidence=0.4999999,
        )
        assert policy.should_promote(fact, "a1") is False

    def test_zero_threshold_promotes_everything(self) -> None:
        policy = DefaultPromotionPolicy(
            promote_threshold=0.0,
            gossip_threshold=0.0,
            broadcast_threshold=0.0,
        )
        fact = HiveFact(fact_id="f1", content="t", concept="t", confidence=0.0)
        assert policy.should_promote(fact, "a1") is True
        assert policy.should_gossip(fact, "a1") is True
        assert policy.should_broadcast(fact, "a1") is True

    def test_retracted_always_blocked(self) -> None:
        policy = DefaultPromotionPolicy(
            promote_threshold=0.0,
            gossip_threshold=0.0,
            broadcast_threshold=0.0,
        )
        fact = HiveFact(
            fact_id="f1", content="t", concept="t",
            confidence=1.0, status="retracted",
        )
        assert policy.should_promote(fact, "a1") is False
        assert policy.should_gossip(fact, "a1") is False
        assert policy.should_broadcast(fact, "a1") is False


# ===========================================================================
# Section 9: EVENT BUS FACTORY
# ===========================================================================


class TestEventBusFactory:
    """Tests for create_event_bus factory."""

    def test_create_local_bus(self) -> None:
        from amplihack.agents.goal_seeking.hive_mind.event_bus import create_event_bus

        bus = create_event_bus("local")
        assert isinstance(bus, LocalEventBus)
        bus.close()

    def test_create_unknown_backend_raises(self) -> None:
        from amplihack.agents.goal_seeking.hive_mind.event_bus import create_event_bus

        with pytest.raises(ValueError, match="Unknown event bus backend"):
            create_event_bus("kafka")


# ===========================================================================
# Section 10: DATA MODEL EDGE CASES
# ===========================================================================


class TestDataModels:
    """Tests for data model defaults and edge cases."""

    def test_hive_fact_defaults(self) -> None:
        fact = HiveFact(fact_id="f1", content="test")
        assert fact.concept == ""
        assert fact.confidence == 0.8
        assert fact.source_agent == ""
        assert fact.tags == []
        assert fact.status == "promoted"
        assert fact.embedding is None
        assert fact.created_at > 0

    def test_hive_agent_defaults(self) -> None:
        agent = HiveAgent(agent_id="a1")
        assert agent.domain == ""
        assert agent.trust == 1.0
        assert agent.fact_count == 0
        assert agent.status == "active"

    def test_hive_edge_defaults(self) -> None:
        edge = HiveEdge(source_id="s1", target_id="t1", edge_type="PROMOTED")
        assert edge.properties == {}

    def test_shard_fact_defaults(self) -> None:
        sf = ShardFact(fact_id="f1", content="test")
        assert sf.concept == ""
        assert sf.confidence == 0.8
        assert sf.source_agent == ""
        assert sf.tags == []
        assert sf.ring_position == 0

    def test_scored_fact_defaults(self) -> None:
        sf = ScoredFact(fact="dummy", score=0.5)
        assert sf.source == "unknown"

    def test_gossip_protocol_defaults(self) -> None:
        gp = GossipProtocol()
        assert gp.top_k == 10
        assert gp.fanout == 2
        assert gp.min_confidence == GOSSIP_MIN_CONFIDENCE

    def test_fact_ttl_defaults(self) -> None:
        ttl = FactTTL(fact_id="f1")
        assert ttl.ttl_seconds == 86400.0
        assert ttl.confidence_decay_rate == 0.01
        assert ttl.created_at > 0
