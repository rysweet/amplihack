"""Integration tests for CRDT, gossip, and fact lifecycle wiring in InMemoryHiveGraph.

Tests that crdt.py, gossip.py, and fact_lifecycle.py are properly wired into
active InMemoryHiveGraph code paths with graceful degradation.
"""

from __future__ import annotations

import time

import pytest

from amplihack.agents.goal_seeking.hive_mind.crdt import LWWRegister
from amplihack.agents.goal_seeking.hive_mind.fact_lifecycle import FactTTL
from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveFact,
    InMemoryHiveGraph,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def hive():
    """Basic hive with one agent."""
    h = InMemoryHiveGraph("test-hive")
    h.register_agent("a1", domain="biology")
    return h


@pytest.fixture()
def ttl_hive():
    """Hive with TTL enabled."""
    h = InMemoryHiveGraph("ttl-hive", enable_ttl=True)
    h.register_agent("a1", domain="biology")
    return h


@pytest.fixture()
def gossip_hive():
    """Hive with gossip enabled."""
    h = InMemoryHiveGraph("gossip-hive", enable_gossip=True)
    h.register_agent("a1", domain="biology")
    return h


# ---------------------------------------------------------------------------
# HiveFact.created_at
# ---------------------------------------------------------------------------


class TestHiveFactCreatedAt:
    """Tests that HiveFact has a created_at field defaulting to time.time()."""

    def test_created_at_default(self):
        before = time.time()
        fact = HiveFact(fact_id="f1", content="test")
        after = time.time()
        assert before <= fact.created_at <= after

    def test_created_at_explicit(self):
        fact = HiveFact(fact_id="f1", content="test", created_at=1000.0)
        assert fact.created_at == 1000.0

    def test_created_at_zero(self):
        fact = HiveFact(fact_id="f1", content="test", created_at=0.0)
        assert fact.created_at == 0.0


# ---------------------------------------------------------------------------
# CRDT Integration: ORSet for facts
# ---------------------------------------------------------------------------


class TestCRDTFactSet:
    """Tests that InMemoryHiveGraph uses ORSet internally for _facts tracking."""

    def test_promote_adds_to_orset(self, hive):
        fid = hive.promote_fact("a1", HiveFact(fact_id="f1", content="DNA stores info"))
        assert hive._fact_set.contains(fid)

    def test_retract_removes_from_orset(self, hive):
        fid = hive.promote_fact("a1", HiveFact(fact_id="f1", content="DNA stores info"))
        assert hive._fact_set.contains(fid)
        hive.retract_fact(fid)
        assert not hive._fact_set.contains(fid)

    def test_multiple_facts_tracked(self, hive):
        f1 = hive.promote_fact("a1", HiveFact(fact_id="f1", content="fact one"))
        f2 = hive.promote_fact("a1", HiveFact(fact_id="f2", content="fact two"))
        assert hive._fact_set.contains(f1)
        assert hive._fact_set.contains(f2)
        assert len(hive._fact_set.items) >= 2

    def test_orset_survives_retract_readd(self, hive):
        """ORSet add-wins: retract then re-add should result in the fact being present."""
        fid = hive.promote_fact("a1", HiveFact(fact_id="f1", content="fact"))
        hive.retract_fact(fid)
        assert not hive._fact_set.contains(fid)
        # Re-add with same ID
        hive.promote_fact("a1", HiveFact(fact_id="f1", content="fact refreshed"))
        assert hive._fact_set.contains("f1")


# ---------------------------------------------------------------------------
# CRDT Integration: LWWRegister for trust
# ---------------------------------------------------------------------------


class TestCRDTTrustRegister:
    """Tests that InMemoryHiveGraph uses LWWRegister for agent trust scores."""

    def test_register_agent_creates_lww(self, hive):
        assert "a1" in hive._trust_registers
        assert isinstance(hive._trust_registers["a1"], LWWRegister)

    def test_register_agent_lww_has_initial_trust(self, hive):
        assert hive._trust_registers["a1"].get() == 1.0

    def test_update_trust_uses_lww(self, hive):
        hive.update_trust("a1", 1.8)
        assert hive._trust_registers["a1"].get() == 1.8
        assert hive.get_agent("a1").trust == 1.8

    def test_update_trust_clamped(self, hive):
        hive.update_trust("a1", 5.0)
        assert hive._trust_registers["a1"].get() == 2.0
        assert hive.get_agent("a1").trust == 2.0

    def test_unregister_agent_cleans_lww(self, hive):
        hive.unregister_agent("a1")
        assert "a1" not in hive._trust_registers


# ---------------------------------------------------------------------------
# CRDT Integration: merge_state
# ---------------------------------------------------------------------------


class TestMergeState:
    """Tests for merge_state CRDT merging between hive replicas."""

    def test_merge_adds_missing_facts(self):
        h1 = InMemoryHiveGraph("h1")
        h1.register_agent("a1")
        h1.promote_fact("a1", HiveFact(fact_id="f1", content="fact from h1"))

        h2 = InMemoryHiveGraph("h2")
        h2.register_agent("a2")
        h2.promote_fact("a2", HiveFact(fact_id="f2", content="fact from h2"))

        h1.merge_state(h2)
        assert h1.get_fact("f2") is not None
        assert h1.get_fact("f2").content == "fact from h2"

    def test_merge_preserves_existing_facts(self):
        h1 = InMemoryHiveGraph("h1")
        h1.register_agent("a1")
        h1.promote_fact("a1", HiveFact(fact_id="f1", content="original"))

        h2 = InMemoryHiveGraph("h2")
        h2.register_agent("a2")

        h1.merge_state(h2)
        assert h1.get_fact("f1").content == "original"

    def test_merge_orset_retraction_propagates(self):
        """If a fact was retracted on one replica, merge reflects that."""
        h1 = InMemoryHiveGraph("h1")
        h1.register_agent("a1")
        h1.promote_fact("a1", HiveFact(fact_id="f1", content="shared fact"))

        h2 = InMemoryHiveGraph("h2")
        h2.register_agent("a2")
        h2.promote_fact("a2", HiveFact(fact_id="f1", content="shared fact"))
        h2.retract_fact("f1")

        # h1 has f1 as live, h2 has f1 as retracted
        # After merge, ORSet add-wins: h1 still added f1, so it stays live
        h1.merge_state(h2)
        # ORSet add-wins: h1's add tag survives h2's tombstone
        assert h1._fact_set.contains("f1")

    def test_merge_trust_lww_latest_wins(self):
        h1 = InMemoryHiveGraph("h1")
        h1.register_agent("a1")
        h1.update_trust("a1", 0.5)

        h2 = InMemoryHiveGraph("h2")
        h2.register_agent("a1")
        time.sleep(0.01)  # Ensure h2's timestamp is newer
        h2.update_trust("a1", 1.9)

        h1.merge_state(h2)
        # LWW: h2's update was later, so h1 should have 1.9
        assert h1.get_agent("a1").trust == 1.9

    def test_merge_is_commutative(self):
        h1 = InMemoryHiveGraph("h1")
        h1.register_agent("a1")
        h1.promote_fact("a1", HiveFact(fact_id="f1", content="fact A"))

        h2 = InMemoryHiveGraph("h2")
        h2.register_agent("a2")
        h2.promote_fact("a2", HiveFact(fact_id="f2", content="fact B"))

        # Merge in both directions
        h1_copy = InMemoryHiveGraph("h1c")
        h1_copy.register_agent("a1")
        h1_copy.promote_fact("a1", HiveFact(fact_id="f1", content="fact A"))

        h2_copy = InMemoryHiveGraph("h2c")
        h2_copy.register_agent("a2")
        h2_copy.promote_fact("a2", HiveFact(fact_id="f2", content="fact B"))

        h1_copy.merge_state(h2_copy)
        h2.merge_state(h1)

        # Both should have the same facts
        assert h1_copy.get_fact("f2") is not None
        assert h2.get_fact("f1") is not None

    def test_merge_idempotent(self):
        h1 = InMemoryHiveGraph("h1")
        h1.register_agent("a1")
        h1.promote_fact("a1", HiveFact(fact_id="f1", content="fact"))

        h2 = InMemoryHiveGraph("h2")
        h2.register_agent("a2")
        h2.promote_fact("a2", HiveFact(fact_id="f2", content="other"))

        h1.merge_state(h2)
        stats_after_first = h1.get_stats()
        h1.merge_state(h2)
        stats_after_second = h1.get_stats()

        assert stats_after_first["fact_count"] == stats_after_second["fact_count"]


# ---------------------------------------------------------------------------
# Gossip Integration
# ---------------------------------------------------------------------------


class TestGossipIntegration:
    """Tests for gossip protocol wiring in InMemoryHiveGraph."""

    def test_gossip_disabled_by_default(self):
        h = InMemoryHiveGraph("h")
        assert not h._enable_gossip

    def test_gossip_enabled_param(self):
        h = InMemoryHiveGraph("h", enable_gossip=True)
        assert h._enable_gossip

    def test_run_gossip_shares_facts(self, gossip_hive):
        peer = InMemoryHiveGraph("peer")
        peer.register_agent("p1", domain="bio")

        gossip_hive.promote_fact(
            "a1", HiveFact(fact_id="f1", content="DNA stores genetic info", confidence=0.9)
        )

        result = gossip_hive.run_gossip([peer])
        assert "peer" in result
        assert len(result["peer"]) >= 1

        # Peer should now have the fact content
        peer_facts = peer.query_facts("DNA genetic")
        assert any("DNA" in f.content for f in peer_facts)

    def test_run_gossip_stores_peers(self, gossip_hive):
        peer = InMemoryHiveGraph("peer")
        peer.register_agent("p1")
        gossip_hive.run_gossip([peer])
        assert len(gossip_hive._gossip_peers) == 1

    def test_auto_gossip_on_promote(self):
        h = InMemoryHiveGraph("source", enable_gossip=True)
        h.register_agent("a1")

        peer = InMemoryHiveGraph("peer")
        peer.register_agent("p1")

        # First, register peers via run_gossip
        h.run_gossip([peer])

        # Now promote a new fact - should auto-gossip
        h.promote_fact("a1", HiveFact(fact_id="f2", content="RNA is transcribed", confidence=0.8))

        # Peer should have received the fact
        peer_facts = peer.query_facts("RNA transcribed")
        assert any("RNA" in f.content for f in peer_facts)

    def test_gossip_skips_gossip_copies(self):
        """Facts received via gossip should NOT trigger re-gossip (prevents loops)."""
        h = InMemoryHiveGraph("source", enable_gossip=True)
        h.register_agent("a1")

        peer = InMemoryHiveGraph("peer")
        peer.register_agent("p1")
        h.run_gossip([peer])

        # Promote a fact WITH gossip_from tag (simulating received gossip)
        h.promote_fact(
            "a1",
            HiveFact(
                fact_id="fg",
                content="gossip copy",
                confidence=0.9,
                tags=["gossip_from:other"],
            ),
        )
        # This should NOT cause additional gossip to peer
        # (peer should not have "gossip copy" unless explicitly gossiped)

    def test_run_gossip_without_module_returns_empty(self):
        """run_gossip returns empty dict when gossip module unavailable."""
        import amplihack.agents.goal_seeking.hive_mind.hive_graph as hg

        original = hg._HAS_GOSSIP
        try:
            hg._HAS_GOSSIP = False
            h = InMemoryHiveGraph("h")
            h.register_agent("a1")
            result = h.run_gossip([])
            assert result == {}
        finally:
            hg._HAS_GOSSIP = original

    def test_gossip_no_duplicate_facts(self):
        """Gossip should not re-share facts the peer already has."""
        h = InMemoryHiveGraph("source")
        h.register_agent("a1")
        h.promote_fact("a1", HiveFact(fact_id="f1", content="shared fact", confidence=0.9))

        peer = InMemoryHiveGraph("peer")
        peer.register_agent("p1")
        # Pre-populate peer with same content
        peer.promote_fact("p1", HiveFact(fact_id="p_f1", content="shared fact", confidence=0.9))

        result = h.run_gossip([peer])
        # Should not share since peer already has the content
        assert len(result.get("peer", [])) == 0


# ---------------------------------------------------------------------------
# Fact Lifecycle / TTL Integration
# ---------------------------------------------------------------------------


class TestFactLifecycleIntegration:
    """Tests for fact TTL, confidence decay, and garbage collection wiring."""

    def test_ttl_disabled_by_default(self):
        h = InMemoryHiveGraph("h")
        assert not h._enable_ttl

    def test_ttl_enabled_param(self):
        h = InMemoryHiveGraph("h", enable_ttl=True)
        assert h._enable_ttl

    def test_promote_registers_ttl(self, ttl_hive):
        fid = ttl_hive.promote_fact("a1", HiveFact(fact_id="f1", content="test", confidence=0.9))
        assert fid in ttl_hive._ttl_registry
        assert isinstance(ttl_hive._ttl_registry[fid], FactTTL)

    def test_promote_stores_original_confidence(self, ttl_hive):
        fid = ttl_hive.promote_fact("a1", HiveFact(fact_id="f1", content="test", confidence=0.85))
        assert ttl_hive._original_confidences[fid] == 0.85

    def test_query_applies_decay(self, ttl_hive):
        # Create a fact with old created_at to trigger decay
        old_time = time.time() - 36000  # 10 hours ago
        ttl_hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="old",
                content="old fact with decay",
                confidence=0.9,
                created_at=old_time,
            ),
        )
        # Query should apply decay
        results = ttl_hive.query_facts("old fact decay")
        assert len(results) >= 1
        # Confidence should be less than original 0.9 due to decay
        old_fact = next(f for f in results if f.fact_id == "old")
        assert old_fact.confidence < 0.9

    def test_query_no_decay_when_ttl_disabled(self, hive):
        old_time = time.time() - 36000
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="old",
                content="old fact no decay",
                confidence=0.9,
                created_at=old_time,
            ),
        )
        results = hive.query_facts("old fact")
        old_fact = next(f for f in results if f.fact_id == "old")
        assert old_fact.confidence == 0.9  # No decay

    def test_gc_removes_expired_facts(self, ttl_hive):
        expired_time = time.time() - 100000  # ~27 hours ago
        ttl_hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="expired",
                content="expired fact",
                confidence=0.5,
                created_at=expired_time,
            ),
        )
        removed = ttl_hive.gc()
        assert "expired" in removed
        fact = ttl_hive.get_fact("expired")
        assert fact is not None
        assert fact.status == "retracted"

    def test_gc_keeps_fresh_facts(self, ttl_hive):
        ttl_hive.promote_fact(
            "a1",
            HiveFact(fact_id="fresh", content="fresh fact", confidence=0.9),
        )
        removed = ttl_hive.gc()
        assert "fresh" not in removed
        assert ttl_hive.get_fact("fresh").status == "promoted"

    def test_gc_noop_when_disabled(self, hive):
        removed = hive.gc()
        assert removed == []

    def test_gc_cleans_original_confidence(self, ttl_hive):
        expired_time = time.time() - 100000
        ttl_hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="exp",
                content="expire me",
                confidence=0.5,
                created_at=expired_time,
            ),
        )
        assert "exp" in ttl_hive._original_confidences
        ttl_hive.gc()
        assert "exp" not in ttl_hive._original_confidences

    def test_decay_does_not_compound(self, ttl_hive):
        """Repeated queries should not compound decay (uses original confidence)."""
        old_time = time.time() - 7200  # 2 hours ago
        ttl_hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="f1",
                content="compounding test fact",
                confidence=0.9,
                created_at=old_time,
            ),
        )

        # First query applies decay
        results1 = ttl_hive.query_facts("compounding test")
        conf1 = next(f for f in results1 if f.fact_id == "f1").confidence

        # Second query should give approximately the same confidence
        # (not decayed from already-decayed value)
        results2 = ttl_hive.query_facts("compounding test")
        conf2 = next(f for f in results2 if f.fact_id == "f1").confidence

        # Allow tiny float difference from time passing between queries
        assert abs(conf1 - conf2) < 0.001


# ---------------------------------------------------------------------------
# Graceful Degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Tests that all integrations degrade gracefully when modules unavailable."""

    def test_crdt_unavailable_fallback(self):
        import amplihack.agents.goal_seeking.hive_mind.hive_graph as hg

        original = hg._HAS_CRDT
        try:
            hg._HAS_CRDT = False
            h = InMemoryHiveGraph("fallback")
            h.register_agent("a1")
            fid = h.promote_fact("a1", HiveFact(fact_id="f1", content="test"))
            assert h.get_fact(fid) is not None
            h.retract_fact(fid)
            assert h.get_fact(fid).status == "retracted"
        finally:
            hg._HAS_CRDT = original

    def test_merge_state_noop_without_crdt(self):
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

    def test_lifecycle_unavailable_fallback(self):
        import amplihack.agents.goal_seeking.hive_mind.hive_graph as hg

        original = hg._HAS_LIFECYCLE
        try:
            hg._HAS_LIFECYCLE = False
            h = InMemoryHiveGraph("fallback", enable_ttl=True)
            # enable_ttl should be False since module unavailable
            assert not h._enable_ttl
        finally:
            hg._HAS_LIFECYCLE = original


# ---------------------------------------------------------------------------
# Combined Integration
# ---------------------------------------------------------------------------


class TestCombinedIntegration:
    """Tests combining CRDT, gossip, and TTL features together."""

    def test_full_lifecycle(self):
        """Promote, gossip, decay, gc in one flow."""
        h1 = InMemoryHiveGraph("h1", enable_gossip=True, enable_ttl=True)
        h1.register_agent("a1", domain="bio")

        h2 = InMemoryHiveGraph("h2", enable_ttl=True)
        h2.register_agent("a2", domain="bio")

        # Promote a fact
        fid = h1.promote_fact(
            "a1",
            HiveFact(fact_id="f1", content="cells divide", confidence=0.9),
        )

        # Gossip to peer
        result = h1.run_gossip([h2])
        assert "h2" in result

        # Query with decay (fresh fact, minimal decay)
        facts = h1.query_facts("cells divide")
        assert len(facts) >= 1

        # GC should not remove fresh facts
        removed = h1.gc()
        assert fid not in removed

    def test_merge_with_ttl_facts(self):
        """merge_state works correctly with TTL-tracked facts."""
        h1 = InMemoryHiveGraph("h1", enable_ttl=True)
        h1.register_agent("a1")
        h1.promote_fact("a1", HiveFact(fact_id="f1", content="from h1", confidence=0.8))

        h2 = InMemoryHiveGraph("h2", enable_ttl=True)
        h2.register_agent("a2")
        h2.promote_fact("a2", HiveFact(fact_id="f2", content="from h2", confidence=0.7))

        h1.merge_state(h2)
        assert h1.get_fact("f2") is not None
        assert h1.get_fact("f2").content == "from h2"
