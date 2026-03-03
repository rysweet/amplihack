"""Outside-in behavioral tests for CRDT, gossip, and fact lifecycle integration.

These tests verify the system from an external consumer's perspective, treating
InMemoryHiveGraph as a black box. No _private attribute access.

Covers 6 behavioral scenarios:
  1. Multi-replica eventual consistency via merge_state
  2. Gossip epidemic propagation across peers
  3. Stale fact confidence decay in queries
  4. Garbage collection of expired facts
  5. Graceful degradation when optional modules are unavailable
  6. Full promote -> gossip -> query-with-decay -> gc lifecycle
"""

from __future__ import annotations

import time

from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveFact,
    InMemoryHiveGraph,
)

# ---------------------------------------------------------------------------
# Scenario 1: Multi-replica eventual consistency via merge_state
# ---------------------------------------------------------------------------


class TestScenario1_ReplicaConvergence:
    """Two hive replicas promote different facts, merge, and both see all facts."""

    def test_divergent_replicas_converge_after_merge(self):
        """Given two replicas with different facts, when merged, both see everything."""
        # Setup: two independent replicas
        replica_a = InMemoryHiveGraph("replica-a")
        replica_a.register_agent("agent-a", domain="physics")

        replica_b = InMemoryHiveGraph("replica-b")
        replica_b.register_agent("agent-b", domain="chemistry")

        # Act: each promotes unique facts
        replica_a.promote_fact(
            "agent-a",
            HiveFact(fact_id="fa1", content="gravity pulls objects down", concept="physics"),
        )
        replica_a.promote_fact(
            "agent-a",
            HiveFact(fact_id="fa2", content="light travels at 300000 km/s", concept="physics"),
        )

        replica_b.promote_fact(
            "agent-b",
            HiveFact(fact_id="fb1", content="water is H2O", concept="chemistry"),
        )

        # Merge in both directions
        replica_a.merge_state(replica_b)
        replica_b.merge_state(replica_a)

        # Assert: both replicas see all 3 facts
        for replica in (replica_a, replica_b):
            assert replica.get_fact("fa1") is not None
            assert replica.get_fact("fa2") is not None
            assert replica.get_fact("fb1") is not None

    def test_trust_scores_converge_to_latest(self):
        """When replicas have different trust for the same agent, merge picks latest."""
        r1 = InMemoryHiveGraph("r1")
        r1.register_agent("shared-agent", trust=0.5)

        r2 = InMemoryHiveGraph("r2")
        r2.register_agent("shared-agent", trust=0.5)

        # r1 updates trust first
        r1.update_trust("shared-agent", 0.8)
        time.sleep(0.02)  # ensure r2's update has a strictly later timestamp
        # r2 updates trust later with different value
        r2.update_trust("shared-agent", 1.5)

        # Merge r2 into r1 -- r2's update is later, should win
        r1.merge_state(r2)
        assert r1.get_agent("shared-agent").trust == 1.5

    def test_merge_is_idempotent(self):
        """Merging the same replica twice produces the same result."""
        h1 = InMemoryHiveGraph("h1")
        h1.register_agent("a1")
        h1.promote_fact("a1", HiveFact(fact_id="f1", content="idempotent test"))

        h2 = InMemoryHiveGraph("h2")
        h2.register_agent("a2")
        h2.promote_fact("a2", HiveFact(fact_id="f2", content="other fact"))

        h1.merge_state(h2)
        count_after_first = h1.get_stats()["fact_count"]

        h1.merge_state(h2)
        count_after_second = h1.get_stats()["fact_count"]

        assert count_after_first == count_after_second


# ---------------------------------------------------------------------------
# Scenario 2: Gossip epidemic propagation
# ---------------------------------------------------------------------------


class TestScenario2_GossipPropagation:
    """Facts promoted on one hive spread to peers via gossip rounds."""

    def test_fact_propagates_to_peer_via_gossip(self):
        """Given a hive with a fact, when gossip runs, peer receives the fact."""
        source = InMemoryHiveGraph("source", enable_gossip=True)
        source.register_agent("researcher", domain="biology")

        peer = InMemoryHiveGraph("peer")
        peer.register_agent("peer-agent", domain="biology")

        # Source promotes a fact
        source.promote_fact(
            "researcher",
            HiveFact(
                fact_id="bio1",
                content="mitochondria is the powerhouse of the cell",
                concept="biology",
                confidence=0.95,
            ),
        )

        # Run gossip
        result = source.run_gossip([peer])

        # Peer should have received the fact
        assert "peer" in result
        peer_facts = peer.query_facts("mitochondria powerhouse cell")
        assert any("mitochondria" in f.content for f in peer_facts)

    def test_auto_gossip_on_promote_shares_with_known_peers(self):
        """When gossip is enabled, promoting a fact auto-shares to registered peers."""
        h = InMemoryHiveGraph("auto-gossip", enable_gossip=True)
        h.register_agent("a1", domain="math")

        peer = InMemoryHiveGraph("peer")
        peer.register_agent("p1", domain="math")

        # Register peer via initial gossip round
        h.run_gossip([peer])

        # Promote a NEW fact -- auto-gossip should share it
        h.promote_fact(
            "a1",
            HiveFact(
                fact_id="math1",
                content="pi is approximately 3.14159",
                confidence=0.99,
            ),
        )

        # Peer should have it without explicit gossip call
        peer_facts = peer.query_facts("pi approximately")
        assert any("pi" in f.content for f in peer_facts)

    def test_gossip_prevents_infinite_loops(self):
        """Facts received via gossip should not trigger re-gossip (no infinite loops)."""
        h1 = InMemoryHiveGraph("h1", enable_gossip=True)
        h1.register_agent("a1")

        h2 = InMemoryHiveGraph("h2", enable_gossip=True)
        h2.register_agent("a2")

        # Register peers both ways
        h1.run_gossip([h2])
        h2.run_gossip([h1])

        # Promote on h1 -- auto-gossips to h2
        h1.promote_fact(
            "a1",
            HiveFact(fact_id="loop-test", content="loop prevention test", confidence=0.9),
        )

        # h2 got the fact via gossip
        h2_facts = h2.query_facts("loop prevention")
        assert any("loop" in f.content for f in h2_facts)

        # Verify no crash from recursive gossip -- the fact should have gossip_from tag
        # which prevents h2 from re-gossiping it back to h1
        h1_facts_before = len(h1.query_facts("loop prevention"))
        # This should not cause infinite recursion
        h2.run_gossip([h1])
        h1_facts_after = len(h1.query_facts("loop prevention"))
        # h1 already has the fact, so count should not increase
        assert h1_facts_after == h1_facts_before

    def test_gossip_skips_duplicate_content(self):
        """Gossip should not re-share facts the peer already has."""
        source = InMemoryHiveGraph("source")
        source.register_agent("a1")
        source.promote_fact(
            "a1",
            HiveFact(fact_id="dup", content="shared knowledge", confidence=0.9),
        )

        peer = InMemoryHiveGraph("peer")
        peer.register_agent("p1")
        # Peer already has the same content
        peer.promote_fact(
            "p1",
            HiveFact(fact_id="dup-peer", content="shared knowledge", confidence=0.9),
        )

        result = source.run_gossip([peer])
        # Gossip should detect duplicate content and skip
        shared = result.get("peer", [])
        assert len(shared) == 0


# ---------------------------------------------------------------------------
# Scenario 3: Stale fact confidence decay
# ---------------------------------------------------------------------------


class TestScenario3_ConfidenceDecay:
    """Old facts lose confidence over time when TTL is enabled."""

    def test_old_facts_have_lower_confidence_than_fresh(self):
        """Given a 10-hour-old fact and a fresh fact, the old one scores lower."""
        hive = InMemoryHiveGraph("decay-test", enable_ttl=True)
        hive.register_agent("a1")

        # Old fact: 10 hours ago
        old_time = time.time() - 36000
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="old",
                content="decaying knowledge about science",
                confidence=0.9,
                created_at=old_time,
            ),
        )

        # Fresh fact: just now
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="fresh",
                content="fresh knowledge about science",
                confidence=0.9,
            ),
        )

        results = hive.query_facts("knowledge science")
        old_fact = next(f for f in results if f.fact_id == "old")
        fresh_fact = next(f for f in results if f.fact_id == "fresh")

        # Old fact should have decayed confidence
        assert old_fact.confidence < fresh_fact.confidence
        assert old_fact.confidence < 0.9

    def test_repeated_queries_do_not_compound_decay(self):
        """Querying twice should not double-decay the confidence."""
        hive = InMemoryHiveGraph("no-compound", enable_ttl=True)
        hive.register_agent("a1")

        old_time = time.time() - 7200  # 2 hours ago
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="stable",
                content="stable decay test fact",
                confidence=0.9,
                created_at=old_time,
            ),
        )

        results1 = hive.query_facts("stable decay test")
        conf1 = next(f for f in results1 if f.fact_id == "stable").confidence

        results2 = hive.query_facts("stable decay test")
        conf2 = next(f for f in results2 if f.fact_id == "stable").confidence

        # Should be approximately the same (tiny difference from time passing)
        assert abs(conf1 - conf2) < 0.001

    def test_no_decay_when_ttl_disabled(self):
        """With TTL disabled, old facts keep their original confidence."""
        hive = InMemoryHiveGraph("no-ttl")
        hive.register_agent("a1")

        old_time = time.time() - 36000
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="old",
                content="undecayed old fact",
                confidence=0.9,
                created_at=old_time,
            ),
        )

        results = hive.query_facts("undecayed old")
        old_fact = next(f for f in results if f.fact_id == "old")
        assert old_fact.confidence == 0.9


# ---------------------------------------------------------------------------
# Scenario 4: Garbage collection of expired facts
# ---------------------------------------------------------------------------


class TestScenario4_GarbageCollection:
    """Expired facts are retracted by gc()."""

    def test_gc_retracts_expired_facts(self):
        """Facts older than 24h are retracted by gc()."""
        hive = InMemoryHiveGraph("gc-test", enable_ttl=True)
        hive.register_agent("a1")

        # Expired: 28 hours ago (over default 24h TTL)
        expired_time = time.time() - 100800
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="expired",
                content="this fact is too old",
                confidence=0.5,
                created_at=expired_time,
            ),
        )

        removed = hive.gc()
        assert "expired" in removed

        # Fact should still exist but be retracted
        fact = hive.get_fact("expired")
        assert fact is not None
        assert fact.status == "retracted"

    def test_gc_keeps_fresh_facts(self):
        """Recent facts survive gc()."""
        hive = InMemoryHiveGraph("gc-keep", enable_ttl=True)
        hive.register_agent("a1")

        hive.promote_fact(
            "a1",
            HiveFact(fact_id="recent", content="this fact is recent", confidence=0.9),
        )

        removed = hive.gc()
        assert "recent" not in removed
        assert hive.get_fact("recent").status == "promoted"

    def test_gc_noop_when_ttl_disabled(self):
        """gc() returns empty list when TTL is not enabled."""
        hive = InMemoryHiveGraph("no-gc")
        hive.register_agent("a1")

        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="f1",
                content="some fact",
                created_at=time.time() - 200000,
            ),
        )

        removed = hive.gc()
        assert removed == []


# ---------------------------------------------------------------------------
# Scenario 5: Graceful degradation
# ---------------------------------------------------------------------------


class TestScenario5_GracefulDegradation:
    """System works without optional CRDT/gossip/lifecycle modules."""

    def test_basic_operations_without_crdt_module(self):
        """Core promote/query/retract works even if CRDT module is unavailable."""
        import amplihack.agents.goal_seeking.hive_mind.hive_graph as hg

        original = hg._HAS_CRDT
        try:
            hg._HAS_CRDT = False
            h = InMemoryHiveGraph("fallback")
            h.register_agent("a1")

            fid = h.promote_fact("a1", HiveFact(fact_id="f1", content="fallback test"))
            assert h.get_fact(fid) is not None

            results = h.query_facts("fallback test")
            assert len(results) >= 1

            h.retract_fact(fid)
            assert h.get_fact(fid).status == "retracted"
        finally:
            hg._HAS_CRDT = original

    def test_merge_state_safe_without_crdt(self):
        """merge_state does not crash when CRDT module is unavailable."""
        import amplihack.agents.goal_seeking.hive_mind.hive_graph as hg

        original = hg._HAS_CRDT
        try:
            hg._HAS_CRDT = False
            h1 = InMemoryHiveGraph("h1")
            h2 = InMemoryHiveGraph("h2")
            # Should not raise
            h1.merge_state(h2)
        finally:
            hg._HAS_CRDT = original

    def test_gossip_returns_empty_without_module(self):
        """run_gossip returns {} when gossip module is unavailable."""
        import amplihack.agents.goal_seeking.hive_mind.hive_graph as hg

        original = hg._HAS_GOSSIP
        try:
            hg._HAS_GOSSIP = False
            h = InMemoryHiveGraph("no-gossip")
            h.register_agent("a1")
            result = h.run_gossip([])
            assert result == {}
        finally:
            hg._HAS_GOSSIP = original

    def test_ttl_disabled_when_lifecycle_unavailable(self):
        """enable_ttl=True falls back to False when lifecycle module is missing."""
        import amplihack.agents.goal_seeking.hive_mind.hive_graph as hg

        original = hg._HAS_LIFECYCLE
        try:
            hg._HAS_LIFECYCLE = False
            h = InMemoryHiveGraph("no-lifecycle", enable_ttl=True)
            # Should have silently disabled TTL
            removed = h.gc()
            assert removed == []
        finally:
            hg._HAS_LIFECYCLE = original


# ---------------------------------------------------------------------------
# Scenario 6: Full end-to-end lifecycle
# ---------------------------------------------------------------------------


class TestScenario6_FullLifecycle:
    """Complete promote -> gossip -> query-with-decay -> gc flow."""

    def test_end_to_end_lifecycle(self):
        """Full lifecycle: promote, gossip to peer, query with decay, gc expired."""
        # Setup: two hives with gossip and TTL
        hive_a = InMemoryHiveGraph("hive-a", enable_gossip=True, enable_ttl=True)
        hive_a.register_agent("scientist", domain="biology")

        hive_b = InMemoryHiveGraph("hive-b", enable_ttl=True)
        hive_b.register_agent("student", domain="biology")

        # Step 1: Promote a high-confidence fact
        hive_a.promote_fact(
            "scientist",
            HiveFact(
                fact_id="bio-fact",
                content="cells contain DNA in the nucleus",
                concept="cell-biology",
                confidence=0.95,
            ),
        )

        # Step 2: Gossip to peer
        gossip_result = hive_a.run_gossip([hive_b])
        assert "hive-b" in gossip_result

        # Step 3: Peer can query the gossipped fact
        peer_results = hive_b.query_facts("DNA nucleus cell")
        assert any("DNA" in f.content for f in peer_results)

        # Step 4: Fresh fact has minimal decay
        source_results = hive_a.query_facts("DNA nucleus cell")
        source_fact = next(f for f in source_results if f.fact_id == "bio-fact")
        assert source_fact.confidence > 0.90  # Minimal decay for fresh fact

        # Step 5: GC does not remove fresh fact
        removed = hive_a.gc()
        assert "bio-fact" not in removed

    def test_expired_fact_full_cycle(self):
        """An old fact decays in queries and gets gc'd."""
        hive = InMemoryHiveGraph("full-cycle", enable_ttl=True)
        hive.register_agent("a1")

        # Promote an expired fact (28 hours old)
        expired_time = time.time() - 100800
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="old-fact",
                content="outdated information about weather",
                confidence=0.8,
                created_at=expired_time,
            ),
        )

        # Query shows decayed confidence
        results = hive.query_facts("outdated weather")
        old = next(f for f in results if f.fact_id == "old-fact")
        assert old.confidence < 0.8  # Decayed

        # GC retracts the expired fact
        removed = hive.gc()
        assert "old-fact" in removed
        assert hive.get_fact("old-fact").status == "retracted"

    def test_merge_then_gossip_full_flow(self):
        """Merge replicas, then gossip the merged state to a third peer."""
        r1 = InMemoryHiveGraph("r1", enable_gossip=True)
        r1.register_agent("a1", domain="cs")
        r1.promote_fact(
            "a1",
            HiveFact(fact_id="cs1", content="quicksort has O(n log n) average", confidence=0.9),
        )

        r2 = InMemoryHiveGraph("r2")
        r2.register_agent("a2", domain="cs")
        r2.promote_fact(
            "a2",
            HiveFact(fact_id="cs2", content="mergesort is stable", confidence=0.85),
        )

        # Merge r2 into r1
        r1.merge_state(r2)
        assert r1.get_fact("cs2") is not None

        # Gossip merged state to a third peer
        r3 = InMemoryHiveGraph("r3")
        r3.register_agent("a3", domain="cs")
        r1.run_gossip([r3])

        # r3 should have at least one of r1's facts
        r3_facts = r3.query_facts("quicksort mergesort sort")
        assert len(r3_facts) >= 1
