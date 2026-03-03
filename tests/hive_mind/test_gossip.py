"""Tests for hive_mind.gossip -- gossip protocol, rounds, and convergence.

Tests the GossipProtocol configuration, gossip round execution, peer
selection with trust weighting, and convergence measurement.
"""

from __future__ import annotations

from amplihack.agents.goal_seeking.hive_mind.gossip import (
    GossipProtocol,
    convergence_check,
    run_gossip_round,
)
from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveFact,
    InMemoryHiveGraph,
)


class TestGossipProtocol:
    """Test GossipProtocol dataclass."""

    def test_defaults(self):
        """GossipProtocol has sensible defaults."""
        gp = GossipProtocol()
        assert gp.top_k == 10
        assert gp.fanout == 2
        assert gp.min_confidence == 0.3

    def test_custom_values(self):
        """GossipProtocol accepts custom values."""
        gp = GossipProtocol(top_k=5, fanout=3, min_confidence=0.5)
        assert gp.top_k == 5
        assert gp.fanout == 3
        assert gp.min_confidence == 0.5


class TestRunGossipRound:
    """Test gossip round execution."""

    def _make_hive(self, hive_id: str, agent_id: str, domain: str = "") -> InMemoryHiveGraph:
        """Helper: create a hive with one agent."""
        hive = InMemoryHiveGraph(hive_id)
        hive.register_agent(agent_id, domain=domain)
        return hive

    def test_gossip_shares_facts(self):
        """Gossip shares top-K facts to peers."""
        source = self._make_hive("source", "agent_s")
        peer = self._make_hive("peer1", "agent_p")

        # Add facts to source
        source.promote_fact(
            "agent_s",
            HiveFact(
                fact_id="f1", content="Important finding A", concept="science", confidence=0.9
            ),
        )
        source.promote_fact(
            "agent_s",
            HiveFact(
                fact_id="f2", content="Important finding B", concept="science", confidence=0.8
            ),
        )

        result = run_gossip_round(source, [peer], GossipProtocol(top_k=5, fanout=1))

        assert "peer1" in result
        assert len(result["peer1"]) == 2

    def test_gossip_skips_duplicates(self):
        """Gossip doesn't share facts the peer already has."""
        source = self._make_hive("source", "agent_s")
        peer = self._make_hive("peer1", "agent_p")

        source.promote_fact(
            "agent_s",
            HiveFact(fact_id="f1", content="Shared fact content", concept="test", confidence=0.9),
        )
        # Peer already has the same content
        peer.promote_fact(
            "agent_p",
            HiveFact(
                fact_id="f_existing", content="Shared fact content", concept="test", confidence=0.8
            ),
        )

        result = run_gossip_round(source, [peer], GossipProtocol(top_k=5, fanout=1))

        assert result["peer1"] == []

    def test_gossip_no_peers(self):
        """Gossip with no peers returns empty."""
        source = self._make_hive("source", "agent_s")
        source.promote_fact(
            "agent_s",
            HiveFact(fact_id="f1", content="test", concept="test", confidence=0.9),
        )

        result = run_gossip_round(source, [])

        assert result == {}

    def test_gossip_no_facts(self):
        """Gossip with no facts returns empty."""
        source = self._make_hive("source", "agent_s")
        peer = self._make_hive("peer1", "agent_p")

        result = run_gossip_round(source, [peer])

        assert result == {}

    def test_gossip_excludes_self(self):
        """Gossip doesn't share with self."""
        source = self._make_hive("source", "agent_s")
        source.promote_fact(
            "agent_s",
            HiveFact(fact_id="f1", content="test data", concept="test", confidence=0.9),
        )

        result = run_gossip_round(source, [source])

        assert result == {}

    def test_gossip_min_confidence_filter(self):
        """Gossip only shares facts above min_confidence."""
        source = self._make_hive("source", "agent_s")
        peer = self._make_hive("peer1", "agent_p")

        source.promote_fact(
            "agent_s",
            HiveFact(fact_id="f1", content="Low confidence fact", concept="test", confidence=0.1),
        )
        source.promote_fact(
            "agent_s",
            HiveFact(fact_id="f2", content="High confidence fact", concept="test", confidence=0.9),
        )

        result = run_gossip_round(source, [peer], GossipProtocol(min_confidence=0.5, fanout=1))

        assert "peer1" in result
        assert len(result["peer1"]) == 1  # Only the high-confidence fact

    def test_gossip_fanout_limits_peers(self):
        """Fanout limits number of peers contacted."""
        source = self._make_hive("source", "agent_s")
        source.promote_fact(
            "agent_s",
            HiveFact(fact_id="f1", content="test fact data", concept="test", confidence=0.9),
        )

        peers = [self._make_hive(f"peer{i}", f"agent{i}") for i in range(5)]

        result = run_gossip_round(source, peers, GossipProtocol(fanout=2))

        assert len(result) == 2  # Only 2 peers contacted

    def test_gossip_tags_include_source(self):
        """Gossip-shared facts include gossip_from tag."""
        source = self._make_hive("source", "agent_s")
        peer = self._make_hive("peer1", "agent_p")

        source.promote_fact(
            "agent_s",
            HiveFact(fact_id="f1", content="Tagged test fact", concept="test", confidence=0.9),
        )

        run_gossip_round(source, [peer], GossipProtocol(fanout=1))

        # Check the fact in the peer has the gossip tag
        peer_facts = peer.query_facts("Tagged test fact", limit=5)
        gossip_facts = [f for f in peer_facts if any("gossip_from:" in t for t in f.tags)]
        assert len(gossip_facts) >= 1


class TestConvergenceCheck:
    """Test convergence measurement."""

    def test_identical_hives_full_convergence(self):
        """Identical knowledge gives convergence 1.0."""
        hive1 = InMemoryHiveGraph("h1")
        hive2 = InMemoryHiveGraph("h2")
        hive1.register_agent("a1")
        hive2.register_agent("a2")

        for i in range(3):
            content = f"Fact number {i}"
            hive1.promote_fact("a1", HiveFact(fact_id=f"f1_{i}", content=content, concept="test"))
            hive2.promote_fact("a2", HiveFact(fact_id=f"f2_{i}", content=content, concept="test"))

        score = convergence_check([hive1, hive2])
        assert score == 1.0

    def test_disjoint_hives_zero_convergence(self):
        """Completely different knowledge gives convergence 0.0."""
        hive1 = InMemoryHiveGraph("h1")
        hive2 = InMemoryHiveGraph("h2")
        hive1.register_agent("a1")
        hive2.register_agent("a2")

        hive1.promote_fact("a1", HiveFact(fact_id="f1", content="Alpha data", concept="test"))
        hive2.promote_fact("a2", HiveFact(fact_id="f2", content="Beta data", concept="test"))

        score = convergence_check([hive1, hive2])
        assert score == 0.0

    def test_partial_overlap(self):
        """Partial overlap gives score between 0 and 1."""
        hive1 = InMemoryHiveGraph("h1")
        hive2 = InMemoryHiveGraph("h2")
        hive1.register_agent("a1")
        hive2.register_agent("a2")

        # Shared fact
        hive1.promote_fact("a1", HiveFact(fact_id="f1", content="Shared knowledge", concept="test"))
        hive2.promote_fact("a2", HiveFact(fact_id="f2", content="Shared knowledge", concept="test"))

        # Unique facts
        hive1.promote_fact("a1", HiveFact(fact_id="f3", content="Only in hive1", concept="test"))
        hive2.promote_fact("a2", HiveFact(fact_id="f4", content="Only in hive2", concept="test"))

        score = convergence_check([hive1, hive2])
        # 1 shared out of 3 total unique = 1/3
        assert abs(score - 1.0 / 3.0) < 1e-6

    def test_empty_hives(self):
        """Empty hives give convergence 0.0."""
        hive1 = InMemoryHiveGraph("h1")
        hive2 = InMemoryHiveGraph("h2")

        score = convergence_check([hive1, hive2])
        assert score == 0.0

    def test_no_hives(self):
        """No hives gives convergence 0.0."""
        score = convergence_check([])
        assert score == 0.0

    def test_single_hive_full_convergence(self):
        """Single hive with facts gives convergence 1.0."""
        hive = InMemoryHiveGraph("h1")
        hive.register_agent("a1")
        hive.promote_fact("a1", HiveFact(fact_id="f1", content="solo fact", concept="test"))

        score = convergence_check([hive])
        assert score == 1.0

    def test_retracted_facts_excluded(self):
        """Retracted facts are excluded from convergence."""
        hive1 = InMemoryHiveGraph("h1")
        hive2 = InMemoryHiveGraph("h2")
        hive1.register_agent("a1")
        hive2.register_agent("a2")

        hive1.promote_fact("a1", HiveFact(fact_id="f1", content="Active fact", concept="test"))
        hive1.promote_fact("a1", HiveFact(fact_id="f2", content="Retracted fact", concept="test"))
        hive1.retract_fact("f2")

        hive2.promote_fact("a2", HiveFact(fact_id="f3", content="Active fact", concept="test"))

        score = convergence_check([hive1, hive2])
        assert score == 1.0
