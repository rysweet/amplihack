"""Full pipeline integration test for hive mind with CRDTs, gossip, TTL, and embeddings.

Exercises the complete InMemoryHiveGraph feature set end-to-end:
  1. Creates InMemoryHiveGraph with enable_gossip, enable_ttl, mock embeddings
  2. Two CognitiveAdapters connected to the hive
  3. Agent A stores facts that auto-promote + appear in hive via ORSet
  4. Agent B searches and finds Agent A's facts (cross-agent retrieval)
  5. Gossip round runs successfully
  6. TTL decay reduces confidence over time
  7. gc() removes expired facts
  8. merge_state() merges two hive replicas
"""

from __future__ import annotations

import math
import time

import pytest

from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveFact,
    InMemoryHiveGraph,
)

# ---------------------------------------------------------------------------
# Mock embedding generator (deterministic hash-based vectors)
# ---------------------------------------------------------------------------


class MockEmbeddingGenerator:
    """Produces deterministic 8-dim vectors from text hashing.

    Two texts sharing words will have nonzero cosine similarity.
    """

    def embed(self, text: str) -> list[float]:
        words = text.lower().split()
        vec = [0.0] * 8
        for word in words:
            h = hash(word) & 0xFFFFFFFF
            for i in range(8):
                vec[i] += ((h >> (i * 4)) & 0xF) / 15.0
        # Normalise
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


# ---------------------------------------------------------------------------
# Test: CognitiveAdapter integration (store -> auto-promote -> cross-search)
# ---------------------------------------------------------------------------


class TestCognitiveAdapterHiveIntegration:
    """Agent A stores facts via CognitiveAdapter; Agent B finds them via hive."""

    @pytest.fixture()
    def hive_and_adapters(self, tmp_path):
        """Create a shared hive and two CognitiveAdapters."""
        from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter

        hive = InMemoryHiveGraph(
            "integration-hive",
            embedding_generator=MockEmbeddingGenerator(),
            enable_gossip=True,
            enable_ttl=True,
        )
        hive.register_agent("agent_a", domain="security")
        hive.register_agent("agent_b", domain="infrastructure")

        adapter_a = CognitiveAdapter(
            agent_name="agent_a",
            db_path=tmp_path / "agent_a_db",
            hive_store=hive,
        )
        adapter_b = CognitiveAdapter(
            agent_name="agent_b",
            db_path=tmp_path / "agent_b_db",
            hive_store=hive,
        )

        yield hive, adapter_a, adapter_b

        adapter_a.close()
        adapter_b.close()

    def test_agent_a_store_fact_appears_in_hive(self, hive_and_adapters):
        """Facts stored by Agent A auto-promote into the shared hive."""
        hive, adapter_a, _adapter_b = hive_and_adapters

        adapter_a.store_fact("security", "SSH default port is 22", confidence=0.95)

        # Verify fact exists in the hive via ORSet membership
        hive_facts = hive.query_facts("SSH port 22")
        assert any("SSH" in f.content and "22" in f.content for f in hive_facts)

    def test_agent_b_cross_agent_retrieval(self, hive_and_adapters):
        """Agent B can search and find Agent A's facts via the shared hive."""
        _hive, adapter_a, adapter_b = hive_and_adapters

        adapter_a.store_fact("security", "Firewall blocks port 443 by default")
        adapter_a.store_fact("security", "TLS 1.3 requires certificate validation")

        # Agent B searches — should find Agent A's facts via hive
        results = adapter_b.search("firewall port TLS certificate")
        contents = [r.get("outcome", r.get("content", "")) for r in results]
        assert any("Firewall" in c or "443" in c for c in contents) or any(
            "TLS" in c for c in contents
        ), f"Agent B could not find Agent A facts. Got: {contents}"


# ---------------------------------------------------------------------------
# Test: ORSet fact tracking
# ---------------------------------------------------------------------------


class TestORSetFactTracking:
    """Facts promoted to hive are tracked in the ORSet."""

    def test_promoted_facts_tracked_in_orset(self):
        hive = InMemoryHiveGraph("orset-test", enable_gossip=True, enable_ttl=True)
        hive.register_agent("a1")

        fid = hive.promote_fact(
            "a1",
            HiveFact(fact_id="tracked-1", content="ORSet tracks this fact", confidence=0.9),
        )

        assert hive.get_fact(fid) is not None
        # Verify ORSet contains the fact (via retract->status change)
        assert hive.get_fact(fid).status == "promoted"

    def test_retracted_fact_removed_from_orset(self):
        hive = InMemoryHiveGraph("orset-retract")
        hive.register_agent("a1")

        hive.promote_fact(
            "a1",
            HiveFact(fact_id="to-remove", content="will be retracted"),
        )
        hive.retract_fact("to-remove")

        fact = hive.get_fact("to-remove")
        assert fact.status == "retracted"


# ---------------------------------------------------------------------------
# Test: Gossip round
# ---------------------------------------------------------------------------


class TestGossipRoundIntegration:
    """Gossip round shares facts between hive peers."""

    def test_gossip_shares_facts_to_peer(self):
        source = InMemoryHiveGraph(
            "source",
            embedding_generator=MockEmbeddingGenerator(),
            enable_gossip=True,
        )
        source.register_agent("researcher", domain="biology")
        source.promote_fact(
            "researcher",
            HiveFact(
                fact_id="bio-1",
                content="Photosynthesis converts sunlight to chemical energy",
                concept="biology",
                confidence=0.95,
            ),
        )

        peer = InMemoryHiveGraph(
            "peer",
            embedding_generator=MockEmbeddingGenerator(),
        )
        peer.register_agent("student", domain="biology")

        result = source.run_gossip([peer])

        assert "peer" in result
        peer_facts = peer.query_facts("photosynthesis sunlight energy")
        assert any("Photosynthesis" in f.content for f in peer_facts)

    def test_gossip_returns_shared_fact_ids(self):
        h1 = InMemoryHiveGraph("h1", enable_gossip=True)
        h1.register_agent("a1")
        h1.promote_fact("a1", HiveFact(fact_id="g1", content="gossip test fact", confidence=0.8))

        h2 = InMemoryHiveGraph("h2")
        h2.register_agent("a2")

        result = h1.run_gossip([h2])
        assert isinstance(result, dict)
        assert "h2" in result
        assert len(result["h2"]) >= 1


# ---------------------------------------------------------------------------
# Test: TTL confidence decay
# ---------------------------------------------------------------------------


class TestTTLConfidenceDecay:
    """TTL-enabled hives decay fact confidence over time."""

    def test_old_fact_has_lower_confidence(self):
        hive = InMemoryHiveGraph(
            "ttl-decay",
            embedding_generator=MockEmbeddingGenerator(),
            enable_ttl=True,
        )
        hive.register_agent("a1")

        # 12-hour-old fact
        old_time = time.time() - 43200
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="old-fact",
                content="old information about servers",
                concept="infrastructure",
                confidence=0.9,
                created_at=old_time,
            ),
        )

        # Fresh fact
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="new-fact",
                content="new information about servers",
                concept="infrastructure",
                confidence=0.9,
            ),
        )

        results = hive.query_facts("information servers")
        old = next(f for f in results if f.fact_id == "old-fact")
        new = next(f for f in results if f.fact_id == "new-fact")

        assert old.confidence < new.confidence
        assert old.confidence < 0.9

    def test_decay_does_not_compound_across_queries(self):
        hive = InMemoryHiveGraph("no-compound", enable_ttl=True)
        hive.register_agent("a1")

        old_time = time.time() - 3600  # 1 hour ago
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="stable",
                content="stable confidence test",
                confidence=0.85,
                created_at=old_time,
            ),
        )

        r1 = hive.query_facts("stable confidence")
        c1 = next(f for f in r1 if f.fact_id == "stable").confidence

        r2 = hive.query_facts("stable confidence")
        c2 = next(f for f in r2 if f.fact_id == "stable").confidence

        assert abs(c1 - c2) < 0.001


# ---------------------------------------------------------------------------
# Test: Garbage collection
# ---------------------------------------------------------------------------


class TestGarbageCollection:
    """gc() removes expired facts."""

    def test_gc_removes_expired_facts(self):
        hive = InMemoryHiveGraph("gc-integration", enable_ttl=True)
        hive.register_agent("a1")

        # 30-hour-old fact (exceeds default 24h TTL)
        expired_time = time.time() - 108000
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="expired-1",
                content="this fact has expired",
                confidence=0.5,
                created_at=expired_time,
            ),
        )

        # Fresh fact
        hive.promote_fact(
            "a1",
            HiveFact(fact_id="fresh-1", content="this fact is fresh", confidence=0.9),
        )

        removed = hive.gc()

        assert "expired-1" in removed
        assert "fresh-1" not in removed
        assert hive.get_fact("expired-1").status == "retracted"
        assert hive.get_fact("fresh-1").status == "promoted"

    def test_gc_noop_when_ttl_disabled(self):
        hive = InMemoryHiveGraph("no-ttl")
        hive.register_agent("a1")
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="old",
                content="old but no TTL",
                created_at=time.time() - 200000,
            ),
        )
        assert hive.gc() == []


# ---------------------------------------------------------------------------
# Test: merge_state (CRDT replica convergence)
# ---------------------------------------------------------------------------


class TestMergeState:
    """merge_state() merges two hive replicas via CRDTs."""

    def test_merge_two_replicas(self):
        """Two replicas with unique facts converge after merge."""
        r1 = InMemoryHiveGraph(
            "replica-1",
            embedding_generator=MockEmbeddingGenerator(),
            enable_gossip=True,
            enable_ttl=True,
        )
        r1.register_agent("agent-1", domain="physics")
        r1.promote_fact(
            "agent-1",
            HiveFact(fact_id="r1-f1", content="gravity is 9.8 m/s2", concept="physics"),
        )

        r2 = InMemoryHiveGraph(
            "replica-2",
            embedding_generator=MockEmbeddingGenerator(),
            enable_gossip=True,
            enable_ttl=True,
        )
        r2.register_agent("agent-2", domain="chemistry")
        r2.promote_fact(
            "agent-2",
            HiveFact(fact_id="r2-f1", content="water boils at 100C", concept="chemistry"),
        )

        # Merge in both directions
        r1.merge_state(r2)
        r2.merge_state(r1)

        # Both replicas should see all facts
        for replica in (r1, r2):
            assert replica.get_fact("r1-f1") is not None
            assert replica.get_fact("r2-f1") is not None

    def test_merge_trust_convergence(self):
        """Trust scores converge after merge (last-writer-wins)."""
        r1 = InMemoryHiveGraph("r1")
        r1.register_agent("shared", trust=0.5)

        r2 = InMemoryHiveGraph("r2")
        r2.register_agent("shared", trust=0.5)

        r1.update_trust("shared", 0.7)
        time.sleep(0.02)
        r2.update_trust("shared", 1.2)

        r1.merge_state(r2)
        assert r1.get_agent("shared").trust == 1.2

    def test_merge_is_idempotent(self):
        """Merging the same replica twice produces identical state."""
        r1 = InMemoryHiveGraph("r1")
        r1.register_agent("a1")
        r1.promote_fact("a1", HiveFact(fact_id="f1", content="idempotent"))

        r2 = InMemoryHiveGraph("r2")
        r2.register_agent("a2")
        r2.promote_fact("a2", HiveFact(fact_id="f2", content="other"))

        r1.merge_state(r2)
        count1 = r1.get_stats()["fact_count"]
        r1.merge_state(r2)
        count2 = r1.get_stats()["fact_count"]

        assert count1 == count2


# ---------------------------------------------------------------------------
# Test: Full end-to-end pipeline
# ---------------------------------------------------------------------------


class TestFullPipelineEndToEnd:
    """Complete pipeline: promote -> ORSet -> gossip -> query -> decay -> gc -> merge."""

    def test_complete_lifecycle(self):
        """Full lifecycle exercising all features together."""
        emb = MockEmbeddingGenerator()

        # Two hives with all features enabled
        hive_a = InMemoryHiveGraph(
            "hive-a",
            embedding_generator=emb,
            enable_gossip=True,
            enable_ttl=True,
        )
        hive_a.register_agent("researcher", domain="biology")

        hive_b = InMemoryHiveGraph(
            "hive-b",
            embedding_generator=emb,
            enable_ttl=True,
        )
        hive_b.register_agent("student", domain="biology")

        # 1. Promote facts (tracked by ORSet)
        hive_a.promote_fact(
            "researcher",
            HiveFact(
                fact_id="bio-cell",
                content="cells contain mitochondria for energy",
                concept="biology",
                confidence=0.95,
            ),
        )

        # 2. Gossip to peer
        gossip_result = hive_a.run_gossip([hive_b])
        assert "hive-b" in gossip_result

        # 3. Peer finds the fact via search
        peer_results = hive_b.query_facts("mitochondria energy cells")
        assert any("mitochondria" in f.content for f in peer_results)

        # 4. Add an old fact for TTL decay testing
        old_time = time.time() - 50000  # ~14 hours ago
        hive_a.promote_fact(
            "researcher",
            HiveFact(
                fact_id="old-bio",
                content="old biological observation about proteins",
                concept="biology",
                confidence=0.9,
                created_at=old_time,
            ),
        )

        # 5. Query shows decayed confidence for old fact
        results = hive_a.query_facts("biological observation proteins")
        old_fact = next((f for f in results if f.fact_id == "old-bio"), None)
        assert old_fact is not None
        assert old_fact.confidence < 0.9

        # 6. Add an expired fact for GC testing
        expired_time = time.time() - 100000  # ~28 hours ago
        hive_a.promote_fact(
            "researcher",
            HiveFact(
                fact_id="expired-bio",
                content="very old expired biological data",
                confidence=0.4,
                created_at=expired_time,
            ),
        )
        removed = hive_a.gc()
        assert "expired-bio" in removed
        assert hive_a.get_fact("expired-bio").status == "retracted"

        # 7. Merge two replicas
        hive_a.merge_state(hive_b)
        hive_b.merge_state(hive_a)

        # Both should see the non-expired facts
        for hive in (hive_a, hive_b):
            assert hive.get_fact("bio-cell") is not None
